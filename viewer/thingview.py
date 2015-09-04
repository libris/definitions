# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
import glob
import json
from operator import itemgetter

from flask import request, Response, render_template, redirect, abort
from flask import Blueprint, current_app
from flask.helpers import NotFound

from lddb.storage import Storage
from util.ld import Graph, RDF, Vocab, View, ID, TYPE, REVERSE
from .conneg import Negotiator


BASE_URI = "http://id.kb.se/"

ui_defs = {
    REVERSE: {'label': "Saker som länkar hit"},
    ID: {'label': "URI"},
    TYPE: {'label': "Typ"}
}

app = Blueprint('thingview', __name__)

@app.record
def setup_app(setup_state):
    config = setup_state.app.config

    storage = Storage('lddb',
            config['DBNAME'], config.get('DBHOST', '127.0.0.1'),
            config.get('DBUSER'), config.get('DBPASSWORD'))

    global vocab
    vocab = Vocab("def/terms.ttl", lang='sv')

    global ldview
    ldview = View(vocab, storage)

    global jsonld_context
    jsonld_context = "build/lib-context.jsonld"

    view_context = {
        'ID': ID,'TYPE': TYPE, 'REVERSE': REVERSE,
        'vocab': vocab,
        'ldview': ldview,
        'ui': ui_defs,
    }
    app.context_processor(lambda: view_context)


@app.route('/list/', defaults={'chunk': 1000})
@app.route('/list/<int:chunk>')
def listview(chunk):
    typekeylabel = lambda (t, items): vocab.index.get(t, {'label': t})['label']
    type_groups = sorted(((itype, sorted(items[:chunk], key=vocab.labelgetter))
        for itype, items in ldview.types.iteritems()), key=typekeylabel)
    return render_template('list.html', item_groups_by_type=type_groups)

@app.route('/def/terms/<term>')
def termview(term):
    return redirect('/vocabview#' + term, 303)


negotiator = Negotiator()

def to_data_path(path, suffix):
    if suffix:
        return '%s/data.%s' % (path, suffix)
    else:
        return path


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

    if not thing:
        record_ids = ldview.find_record_ids(item_id)
        if record_ids: #and len(record_ids) == 1:
            return redirect(to_data_path(record_ids[0], suffix), 303)

        see_path = ldview.find_same_as(item_id)
        if see_path:
            return redirect(to_data_path(see_path, suffix), 302)
        else:
            return abort(404)

    mimetype, render = negotiator.negotiate(request, suffix)
    if not render:
        return abort(406)

    result = render(path, thing)
    mimetype = mimetype + '; charset=UTF-8' # technically redundant, but for e.g. JSONView
    return Response(result, mimetype=mimetype) if isinstance(
            result, bytes) else result

@negotiator.add('text/html', 'html')
@negotiator.add('application/xhtml+xml', 'xhtml')
def render_html(path, data):
    return render_template('thing.html', path=path, thing=data)

@negotiator.add('application/ld+json', 'jsonld')
@negotiator.add('application/json', 'json')
@negotiator.add('text/json')
def render_jsonld(path, data):
    return json.dumps(data, indent=2, sort_keys=True,
            separators=(',', ': '), ensure_ascii=False).encode('utf-8')

@negotiator.add('text/turtle', 'ttl')
def render_ttl(path, data):
    return to_graph(data).serialize(format='turtle')

@negotiator.add('application/rdf+xml', 'rdf')
@negotiator.add('text/xml', 'xml')
def render_xml(path, data):
    return to_graph(data).serialize(format='pretty-xml')

def to_graph(data):
    return Graph().parse(data=json.dumps(data), base=BASE_URI,
            format='json-ld', context=jsonld_context)
