# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
import logging
import json
from rdflib import RDF, RDFS, Graph, URIRef
from flask import Blueprint, render_template, redirect


ID, TYPE, REV = '@id', '@type', '@reverse'

vocab = {
    '@id': {
        ID: ID,
        'label': "URI"
    },
    '@type': {
        ID: RDF.type,
        'label': "Typ"
    }
}

def load_vocab(vocab_source, vocab_uri):
    global vocab
    g = Graph().parse(vocab_source, format='turtle')
    for s in g.subjects():
        if not isinstance(s, URIRef):
            continue
        if not s.startswith(vocab_uri):
            continue
        key = s.replace(vocab_uri, '')
        label = key
        for label in g.objects(s, RDFS.label):
            if label.language == 'sv':
                break
        if label:
            label = unicode(label)
        term = {ID: unicode(s),'label': label, 'curie': key}
        vocab[key] = term


db = {}
items = []

label_keys = ['prefLabel', 'uniformTitle', 'title', 'name', 'label']

def load_db(db_source):
    global db, items

    import os
    if not os.path.exists(db_source):
        logging.warn("DB source %s does not exist", db_source)
        return

    for l in open(db_source):
        data = json.loads(l)
        data.pop('_marcUncompleted', None)
        item = data.pop('about')
        item['describedBy'] = data
        if item[ID] not in db:
            items.append(item)
        db[item[ID]] = item
        for l_key in label_keys:
            if l_key in item:
                item['label'] = item[l_key]
                break
        if 'sameAs' in item:
            for ref in item.get('sameAs'):
                if ID in ref:
                    db[ref[ID]] = item

    chip_keys = [ID, TYPE] + label_keys
    for other in items:
        chip = {k: v for k, v in other.items() if k in chip_keys}
        for link, refs in other.items():
            if link == 'sameAs':
                continue
            if not isinstance(refs, list):
                refs = [refs]
            for ref in refs:
                if isinstance(ref, dict) and ID in ref:
                    item = db.get(ref[ID])
                    if not item:
                        continue
                    item.setdefault(REV, {}).setdefault(link, []).append(chip)


ui_defs = {
    REV: {
        'label': "Saker som länkar hit"
    }
}


app = Blueprint('thingview', __name__)

ld_context = {'ID': ID,'TYPE': TYPE, 'REV': REV, 'vocab': vocab, 'ui': ui_defs}
app.context_processor(lambda: ld_context)

@app.record
def setup_app(setup_state):
    # TODO: use config
    #setup_state.app.config['SOME_KEY']
    load_vocab("def/terms.ttl", "http://libris.kb.se/def/terms#")
    load_db("cache/db")

@app.route('/list/')
def listview():
    return render_template('list.html', db=db)

@app.route('/page/<path:path>')
def thingview(path):
    if not path.startswith(('/', 'http:', 'https:')):
        path = '/' + path
    thing = db[path]
    return render_template('thing.html', thing=thing)

@app.route('/def/terms/<term>')
def termview(term):
    return redirect('/vocabview#' + term, 303)
