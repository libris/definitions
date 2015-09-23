# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
from collections import OrderedDict
import re
import json

from flask import request, Response, render_template, redirect, abort, url_for, send_file
from flask import Blueprint, current_app
from flask.helpers import NotFound
from werkzeug.contrib.cache import SimpleCache

from lddb.storage import Storage, DEFAULT_LIMIT
from util.ld import (Graph, RDF, Vocab, View, CONTEXT, ID, TYPE, GRAPH,
        REVERSE, as_iterable, autoframe)
from .conneg import Negotiator


BASE_URI = "http://id.kb.se/"

ui_defs = {
    REVERSE: {'label': "Saker som länkar hit"},
    ID: {'label': "URI"},
    TYPE: {'label': "Typ"},
    'SEE_ALL': {'label': "Se alla"},
}

app = Blueprint('thingview', __name__)

@app.record
def setup_app(setup_state):
    config = setup_state.app.config

    global cache
    cache = SimpleCache()

    global storage
    storage = Storage('lddb',
            config['DBNAME'], config.get('DBHOST', '127.0.0.1'),
            config.get('DBUSER'), config.get('DBPASSWORD'))

    global vocab
    vocab = Vocab("def/terms.ttl", lang='sv')

    global ldview
    ldview = View(vocab, storage)

    global jsonld_context_file
    jsonld_context_file = config['JSONLD_CONTEXT_FILE']

    view_context = {
        'ID': ID,'TYPE': TYPE, 'REVERSE': REVERSE,
        'vocab': vocab,
        'ldview': ldview,
        'ui': ui_defs,
        'page_limit': 400
    }
    app.context_processor(lambda: view_context)


negotiator = Negotiator()

@negotiator.add('text/html', 'html')
@negotiator.add('application/xhtml+xml', 'xhtml')
def render_html(path, data):
    def data_url(suffix):
        if path == '/find':
            return url_for('thingview.find', suffix=suffix, **request.args)
        elif path == '/some':
            return url_for('thingview.some', suffix=suffix, **request.args)
        else:
            return url_for('thingview.thingview', path=path, suffix=suffix)

    return render_template('thing.html', path=path, thing=data, data_url=data_url)

@negotiator.add('application/ld+json', 'jsonld')
def render_jsonld(path, data):
    data[CONTEXT] = '/context.jsonld'
    return _to_json(data)

@negotiator.add('application/json', 'json')
@negotiator.add('text/json')
def render_jsonld(path, data):
    return _to_json(data)

@negotiator.add('text/turtle', 'ttl')
def render_ttl(path, data):
    return _to_graph(data).serialize(format='turtle')

@negotiator.add('application/rdf+xml', 'rdf')
@negotiator.add('text/xml', 'xml')
def render_xml(path, data):
    return _to_graph(data).serialize(format='pretty-xml')


def _to_json(data):
    return json.dumps(data, indent=2, sort_keys=True,
            separators=(',', ': '), ensure_ascii=False).encode('utf-8')

def _to_graph(data):
    return Graph().parse(data=json.dumps(data), base=BASE_URI,
            format='json-ld', context=jsonld_context_file)


@app.route('/context.jsonld')
def jsonld_context():
    return send_file(jsonld_context_file, mimetype='application/ld+json')


@app.route('/<path:path>/data')
@app.route('/<path:path>/data.<suffix>')
@app.route('/<path:path>')
def thingview(path, suffix=None):
    try:
        return current_app.send_static_file(path)
    except NotFound:
        print 'not found', path
        pass

    item_id = path if path.startswith(
            ('/', 'http:', 'https:')) else '/' + path

    thing = ldview.get_record_data(item_id)
    if thing:
        return rendered_response(path, suffix, thing)
    else:
        record_ids = ldview.find_record_ids(item_id)
        if record_ids: #and len(record_ids) == 1:
            return redirect(to_data_path(record_ids[0], suffix), 303)
        see_path = ldview.find_same_as(item_id)
        if see_path:
            return redirect(to_data_path(see_path, suffix), 302)
        else:
            return abort(404)

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

def to_data_path(path, suffix):
    if suffix:
        return '%s/data.%s' % (path, suffix)
    else:
        return path


@app.route('/find')
@app.route('/find.<suffix>')
def find(suffix=None):
    #s = request.args.get('s')
    p = request.args.get('p')
    o = request.args.get('o')
    value = request.args.get('value')
    #language = request.args.get('language')
    #datatype = request.args.get('datatype')
    q = request.args.get('q')
    limit, offset = _get_limit_offset(request.args)

    #items = ldview.find(p, o, value, q, limit, offset)
    records = []
    if p:
        if o:
            records = storage.find_by_relation(p, o, limit, offset)
        elif value:
            records = storage.find_by_value(p, value, limit, offset)
        elif q:
            records = storage.find_by_query(p, q, limit, offset)
    elif o:
        records = storage.find_by_quotation(o, limit, offset)
    items = [ldview.get_decorated_data(rec) for rec in records]

    def ref(link): return {ID: link}

    page_params = {'p': p, 'o': o, 'value': value, 'q': q, 'limit': limit}
    results = OrderedDict({'@type': 'PagedCollection'})
    results['@id'] = url_for('.find', offset=offset, **page_params)
    results['itemsPerPage'] = limit
    results['firstPage'] = ref(url_for('.find', **page_params))

    #'totalItems' ...
    #'lastPage' ...
    if offset:
        prev_offset = offset - limit
        if prev_offset <= 0:
            prev_offset = None
        results['previousPage'] = ref(url_for('.find', offset=prev_offset, **page_params))
    if len(items) == limit:
        next_offset = offset + limit if offset else limit
        results['nextPage'] = ref(url_for('.find', offset=next_offset, **page_params))
    # hydra:member
    results['items'] = items

    return rendered_response('/find', suffix, results)

def _get_limit_offset(args):
    limit = args.get('limit')
    offset = args.get('offset')
    if limit and limit.isdigit():
        limit = int(limit)
    if offset and offset.isdigit():
        offset = int(offset)
    return storage.get_real_limit(limit), offset


@app.route('/some')
@app.route('/some.<suffix>')
def some(suffix=None):
    kws = dict(request.args)
    rtype = kws.pop('type', None)
    q = kws.pop('q', None)
    if q:
        q = " ".join(q)
        #parts = _tokenize(q)
    maybe = {}
    if rtype:
        rtype = rtype[0]
        maybe['@type'] = rtype
    if q:
        maybe['label'] = q
    if kws:
        maybe.update({k: v[0] for k, v in kws.items()})

    def pick_thing(rec):
        data = rec.data['descriptions']
        entry = data['entry']
        for item in [entry] + data.get('items', []):
            if rtype in as_iterable(item[TYPE]):
                return item
        return entry

    maybes  = [
        #ldview.get_decorated_data(rec)
        pick_thing(rec)
        for rec in storage.find_by_example(maybe)
    ]
    if not maybes:
        return abort(404)

    some_id = '%s?%s' % (request.path, request.query_string)
    item = {
        "@id": some_id,
        "@type": "Ambiguity",
        "label": q or ",".join(maybe.values()),
        "maybe": maybes
    }
    graph = [item] + ldview._get_references_to(item)
    data = autoframe({GRAPH: graph}, some_id)
    return rendered_response('/some', suffix, data)

def _tokenize(stuff):
    """
    >>> print(_tokenize("One, Any (1911-)"))
    1911 any one
    """
    return sorted(set(
        re.sub(r'\W(?u)', '', part.lower(), flags=re.UNICODE)
        for part in stuff.split(" ")))


@app.route('/list/')
def listview():
    type_count = cache.get('type_count')
    if type_count is None:
        type_count = ldview.get_type_count()
        cache.set('type_count', type_count, timeout=5 * 60) # seconds
    return render_template('list.html', type_count=type_count)


@app.route('/def/terms/<term>')
def termview(term):
    return redirect('/vocabview#' + term, 303)
