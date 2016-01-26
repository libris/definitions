# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
import re
import json
from urlparse import urlparse, urljoin
from os import makedirs, path as P

from flask import request, Response, render_template, redirect, abort, url_for, send_file
from flask import Blueprint, current_app
from flask.helpers import NotFound
from werkzeug.urls import url_quote

from rdflib import Graph, ConjunctiveGraph
from rdflib import URIRef, RDF, RDFS, OWL
from rdflib.namespace import SKOS, DCTERMS, Namespace, ClosedNamespace

from elasticsearch import Elasticsearch

from lxltools.lddb.storage import Storage
from lxltools.util import as_iterable
from lxltools.graphcache import GraphCache, vocab_source_map
from lxltools.vocabview import VocabView, VocabUtil
from lxltools.dataview import DataView, CONTEXT, GRAPH, ID, TYPE, REVERSE

from .conneg import Negotiator


VANN = Namespace("http://purl.org/vocab/vann/")
VS = Namespace("http://www.w3.org/2003/06/sw-vocab-status/ns#")
SCHEMA = Namespace("http://schema.org/")


IDKBSE = "https://id.kb.se/"
LIBRIS = "https://libris.kb.se/"
DOMAIN_BASE_MAP = {
    'localhost': IDKBSE,
    '127.0.0.1': LIBRIS,
    'id.local.dev': IDKBSE,
    'libris.local.dev': LIBRIS,
    'id-dev.kb.se':  IDKBSE,
    'id-stg.kb.se':  IDKBSE,
    'id.kb.se':  IDKBSE,
    'libris.kb.se': LIBRIS,
}

def _get_base_uri(url=None):
    url = url or request.url
    domain = urlparse(url).netloc.split(':', 1)[0]
    return DOMAIN_BASE_MAP.get(domain)

def _get_served_uri(url, path):
    # TODO: why is Flask unquoting url and path values?
    url = url_quote(url)
    path = url_quote(path)
    mapped_base_uri = _get_base_uri(url)
    if mapped_base_uri:
        return urljoin(mapped_base_uri, path)
    else:
        return url


def view_url(uri):
    if uri.startswith('/'):
        return uri
        #if '?' in uri: # implies other views, see data_url below
        #    raise NotImplementedError
        #return url_for('thingview.thingview', path=uri[1:], suffix='html')
    url_base = _get_base_uri(uri)
    if url_base == _get_base_uri(request.url):
        return urlparse(uri).path
    elif url_base:
        return urljoin(url_base, urlparse(uri).path)
    else:
        return uri

def canonical_uri(thing):
    base = _get_base_uri()
    thing_id = thing.get(ID) or ""
    if not thing_id.startswith(base):
        for same in thing.get('sameAs', []):
            same_id = same.get(ID)
            if same_id and same_id.startswith(base):
                return same_id
    return thing_id

ui_defs = {
    REVERSE: {'label': "Saker som länkar hit"},
    ID: {'label': "URI"},
    TYPE: {'label': "Typ"},
    'SEARCH_RESULTS': {'label': "Sökresultat"},
    'SEE_ALL': {'label': "Se alla"},
}


app = Blueprint('thingview', __name__)

@app.record
def setup_app(setup_state):
    global LANG
    global load_vocab_graph
    global ldview

    config = setup_state.app.config

    storage = Storage('lddb',
            config['DBNAME'], config.get('DBHOST', '127.0.0.1'),
            config.get('DBUSER'), config.get('DBPASSWORD'))

    elastic = Elasticsearch(config['ESHOST'],
            sniff_on_start=config.get('ES_SNIFF_ON_START', True),
            sniff_on_connection_fail=True, sniff_timeout=60,
            sniffer_timeout=300, timeout=10)

    LANG = config['LANG']

    vocab_uri = config['VOCAB_IRI']

    #ns_mgr = Graph().parse('sys/context/base.jsonld',
    #        format='json-ld').namespace_manager
    #ns_mgr.bind("", vocab_uri)

    #graphcache = GraphCache(config['GRAPH_CACHE'])
    #graphcache.graph.namespace_manager = ns_mgr

    cachedir = config['CACHE_DIR']
    if not P.isdir(cachedir):
        makedirs(cachedir)

    def load_vocab_graph():
        global jsonld_context_data

        jsonld_context_data = storage.get_record(vocab_uri + 'context').data[GRAPH][0]

        #vocabgraph = graphcache.load(config['VOCAB_SOURCE'])
        vocab_items = sum((record.data[GRAPH] for record in
                       storage.find_by_quotation(vocab_uri, limit=4096)),
                       storage.get_record(vocab_uri).data[GRAPH])
        vocabdata = json.dumps(vocab_items, indent=2)
        vocabgraph = Graph().parse(
                data=vocabdata,
                context=jsonld_context_data,
                format='json-ld')
        #vocabgraph.namespace_manager = ns_mgr
        vocabgraph.namespace_manager.bind("", vocab_uri)

        # TODO: load base vocabularies for labels, inheritance here,
        # or in vocab build step?
        #for url in vocabgraph.objects(None, OWL.imports):
        #    graphcache.load(vocab_source_map.get(str(url), url))

        return vocabgraph

    vocab = VocabView(load_vocab_graph(), vocab_uri, lang=LANG)

    ldview = DataView(vocab, storage, elastic, config['ES_INDEX'])

    view_context = {
        'ID': ID,'TYPE': TYPE, 'REVERSE': REVERSE,
        'vocab': vocab,
        'ldview': ldview,
        'ui': ui_defs,
        'lang': vocab.lang,
        'page_limit': 50,
        'canonical_uri': canonical_uri,
        'view_url': view_url,
        'url_quote': url_quote,
    }
    app.context_processor(lambda: view_context)


@app.route('/context.jsonld')
def jsonld_context():
    return Response(json.dumps(jsonld_context_data),
            mimetype='application/ld+json; charset=UTF-8')

@app.route('/<path:path>/data')
@app.route('/<path:path>/data.<suffix>')
@app.route('/<path:path>')
def thingview(path, suffix=None):
    try:
        return current_app.send_static_file(path)
    except (NotFound, UnicodeEncodeError) as e:
        pass

    item_id = _get_served_uri(request.url, path)

    thing = ldview.get_record_data(item_id)
    if thing:
        #canonical = thing[ID]
        #if canonocal != item_id:
        #    return redirect(_to_data_path(see_path, suffix), 302)
        return rendered_response(path, suffix, thing)
    else:
        record_ids = ldview.find_record_ids(item_id)
        if record_ids: #and len(record_ids) == 1:
            return redirect(_to_data_path(record_ids[0], suffix), 303)
        #else:
        return abort(404)

def _to_data_path(path, suffix):
    return '%s/data.%s' % (path, suffix) if suffix else path

@app.route('/find')
@app.route('/find.<suffix>')
def find(suffix=None):
    make_find_url = lambda **kws: url_for('.find', **kws)
    results = ldview.get_search_results(request.args, make_find_url,
            _get_base_uri(request.url))
    return rendered_response('/find', suffix, results)

@app.route('/some')
@app.route('/some.<suffix>')
def some(suffix=None):
    ambiguity = ldview.find_ambiguity(request)
    if not ambiguity:
        return abort(404)
    return rendered_response('/some', suffix, ambiguity)

@app.route('/')
@app.route('/data.<suffix>')
def datasetview(suffix=None):
    results = ldview.get_index_aggregate(_get_base_uri(request.url))
    return rendered_response('/', suffix, results)

#@app.route('/vocab/<term>')
#def vocab_term(term):
#    return redirect('/vocab/#' + term, 303)

rdfns = {name: obj for name, obj in globals().items()
                if isinstance(obj, (Namespace, ClosedNamespace))}

app.context_processor(lambda: rdfns)

@app.route('/vocab/')
def vocabview():
    voc = VocabUtil(load_vocab_graph(), LANG)

    def link(obj):
        if ':' in obj.qname() and not any(obj.objects(None)):
            return obj.identifier
        return '#' + obj.qname()

    def listclass(o):
        return 'ext' if ':' in o.qname() else 'loc'

    return render_template('vocab.html',
            URIRef=URIRef, **vars())


def rendered_response(path, suffix, thing):
    mimetype, render = negotiator.negotiate(request, suffix)
    if not render:
        return abort(406)
    result = render(path, thing)
    charset = 'charset=UTF-8' # technically redundant, but for e.g. JSONView
    resp = Response(result, mimetype=mimetype +'; '+ charset) if isinstance(
            result, bytes) else result
    if mimetype == 'application/json':
        context_link = '</context.jsonld>; rel="http://www.w3.org/ns/json-ld#context"'
        resp.headers['Link'] = context_link
    return resp


TYPE_TEMPLATES = {'website', 'pagedcollection'}

negotiator = Negotiator()

@negotiator.add('text/html', 'html')
@negotiator.add('application/xhtml+xml', 'xhtml')
def render_html(path, data):
    data = ldview.get_decorated_data(data, True)

    def data_url(suffix):
        if path == '/find':
            return url_for('thingview.find', suffix=suffix, **request.args)
        elif path == '/some':
            return url_for('thingview.some', suffix=suffix, **request.args)
        else:
            return url_for('thingview.thingview', path=path, suffix=suffix)

    return render_template(_get_template_for(data),
            path=path, thing=data, data_url=data_url)

@negotiator.add('application/json', 'json')
@negotiator.add('text/json')
def render_json(path, data):
    data = ldview.get_decorated_data(data, True)
    return _to_json(data)

@negotiator.add('application/ld+json', 'jsonld')
def render_jsonld(path, data):
    data[CONTEXT] = '/context.jsonld'
    return _to_json(data)

@negotiator.add('text/turtle', 'ttl')
@negotiator.add('text/n3', 'n3') # older: text/rdf+n3, application/n3
def render_ttl(path, data):
    return _to_graph(data).serialize(format='turtle')

@negotiator.add('text/trig', 'trig')
def render_trig(path, data):
    return _to_graph(data).serialize(format='trig')

@negotiator.add('application/rdf+xml', 'rdf')
@negotiator.add('text/xml', 'xml')
def render_xml(path, data):
    return _to_graph(data).serialize(format='pretty-xml')

def _to_json(data):
    return json.dumps(data, indent=2, sort_keys=True,
            separators=(',', ': '), ensure_ascii=False).encode('utf-8')

def _to_graph(data, base=None):
    cg = ConjunctiveGraph()
    cg.parse(data=json.dumps(data), base=base or IDKBSE,
                format='json-ld', context=jsonld_context_data)
    return cg

def _get_template_for(data):
    for rtype in as_iterable(data.get(TYPE)):
        template_key = rtype.lower()
        if template_key in TYPE_TEMPLATES:
            return '%s.html' % template_key
    return 'thing.html'
