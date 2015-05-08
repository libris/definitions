# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
from flask import Blueprint, render_template, redirect
from util.datatools import RDF, load_vocab, load_db, ID, TYPE, REV

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

    global vocab, label_keys
    vocab, label_keys = load_vocab(
            "def/terms.ttl", "http://libris.kb.se/def/terms#", 'sv')

    vocab.update({
        '@id': {ID: ID, 'label': "URI"},
        '@type': {ID: RDF.type, 'label': "Typ"}
    })

    global db, same_as
    db, same_as = load_db("cache/db", label_keys)

    ld_context = {
        'ID': ID,'TYPE': TYPE, 'REV': REV,
        'vocab': vocab,
        'ui': ui_defs,
        'labelgetter': lambda o: o.get('label', o['@id'])
    }
    app.context_processor(lambda: ld_context)

@app.route('/list/')
def listview():
    return render_template('list.html', db=db)

@app.route('/page/<path:path>')
def thingview(path):
    if not path.startswith(('/', 'http:', 'https:')):
        path = '/' + path
    if path in same_as:
        return redirect('/page' + same_as[path], 302)
    thing = db[path]
    return render_template('thing.html', thing=thing)

@app.route('/def/terms/<term>')
def termview(term):
    return redirect('/vocabview#' + term, 303)
