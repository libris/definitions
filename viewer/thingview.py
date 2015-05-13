# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
import glob
import itertools
from operator import itemgetter
from flask import Blueprint, render_template, redirect, abort
from util.ld import RDF, Vocab, ID, TYPE, REV
from util.db import DB

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

@app.route('/list/', defaults=dict(chunk=10000))
@app.route('/list/<int:chunk>')
def listview(chunk):
    typegetter = itemgetter(TYPE)
    items = db.index.values()[:chunk]
    type_groups = itertools.groupby(sorted(items, key=typegetter), typegetter)
    return render_template('list.html', item_groups_by_type=type_groups)

@app.route('/<path:path>/data.html')
def thingview(path):
    if not path.startswith(('/', 'http:', 'https:')):
        path = '/' + path
    if path in db.same_as:
        return redirect(db.same_as[path] + '/', 302)
    thing = db.get_item(path)
    if not thing:
        return abort(404)
    return render_template('thing.html', thing=thing)

@app.route('/def/terms/<term>')
def termview(term):
    return redirect('/vocabview#' + term, 303)
