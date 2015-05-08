# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
from flask import Blueprint, render_template, redirect
from util.datatools import RDF, Vocab, DB, ID, TYPE, REV

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
    vocab = Vocab(
            "def/terms.ttl", "http://libris.kb.se/def/terms#", 'sv')

    vocab.index.update({
        '@id': {ID: ID, 'label': "URI"},
        '@type': {ID: RDF.type, 'label': "Typ"}
    })

    global db
    db = DB("cache/db", vocab)

    ld_context = {
        'ID': ID,'TYPE': TYPE, 'REV': REV,
        'vocab': vocab,
        'db': db,
        'ui': ui_defs,
    }
    app.context_processor(lambda: ld_context)

@app.route('/list/')
def listview():
    return render_template('list.html')

@app.route('/page/<path:path>')
def thingview(path):
    if not path.startswith(('/', 'http:', 'https:')):
        path = '/' + path
    if path in db.same_as:
        return redirect('/page' + db.same_as[path], 302)
    thing = db.index[path]
    return render_template('thing.html', thing=thing)

@app.route('/def/terms/<term>')
def termview(term):
    return redirect('/vocabview#' + term, 303)
