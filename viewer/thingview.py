# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
import glob
import itertools
import json
from operator import itemgetter
from flask import Blueprint, request, Response, render_template, redirect, abort
from util.ld import Graph, RDF, Vocab, ID, TYPE, REV
from util.db import DB
from .conneg import Negotiator


BASE_URI = "http://id.kb.se/"

ui_defs = {
    REV: {
        'label': "Saker som länkar hit"
    }
}

app = Blueprint('thingview', __name__)

@app.record
def setup_app(setup_state):
    # TODO: use config
    #setup_state.app.config['SOME_KEY']

    global vocab
    vocab = Vocab("def/terms.ttl", lang='sv')

    vocab.index.update({
        '@id': {ID: ID, 'label': "URI"},
        '@type': {ID: RDF.type, 'label': "Typ"}
    })

    global db
    db = DB(vocab, "cache/db", *glob.glob("build/*/"))

    ld_context = {
        'ID': ID,'TYPE': TYPE, 'REV': REV,
        'vocab': vocab,
        'db': db,
        'ui': ui_defs,
    }
    app.context_processor(lambda: ld_context)


@app.route('/list/', defaults={'chunk': 10000})
@app.route('/list/<int:chunk>')
def listview(chunk):
    typegetter = itemgetter(TYPE)
    items = db.index.values()[:chunk]
    type_groups = itertools.groupby(sorted(items, key=typegetter), typegetter)
    return render_template('list.html', item_groups_by_type=type_groups)

@app.route('/def/terms/<term>')
def termview(term):
    return redirect('/vocabview#' + term, 303)


negotiator = Negotiator()

@app.route('/<path:path>/data')
@app.route('/<path:path>/data.<suffix>')
def thingview(path, suffix=None):
    if not path.startswith(('/', 'http:', 'https:')):
        path = '/' + path
    if path in db.same_as:
        return redirect(db.same_as[path] + '/', 302)
    thing = db.get_item(path)
    if not thing:
        return abort(404)

    mimetype, render = negotiator.negotiate(request, suffix)
    if not render:
        return abort(406)

    result = render(path, thing)
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
            format='json-ld', context="build/lib-context.jsonld")
