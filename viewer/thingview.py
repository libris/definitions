# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
from rdflib import RDF, RDFS
from flask import Blueprint, render_template

app = Blueprint('thingview', __name__)

ID, TYPE, REV = '@id', '@type', '@reverse'

vocab = {
    '@type': {
        ID: RDF.type,
        'curie': 'rdf:type',
        'label': "Typ"
    },
    'Thing': {
        ID: 'Thing',
        'curie': 'Thing owl:Thing',
        'label': 'Sak'
    },
    'label': {
        ID: RDFS.label,
        'curie': 'rdfs:label name',
        'label': "Etikett"
    },
    'seeAlso': {
        ID: RDFS.seeAlso,
        'curie': 'rdfs:seeAlso',
        'label': "Se även"
    }
}

db = {
    'something': {
        ID: 'something',
        TYPE: 'Thing',
        'label': 'Something'
    },
    'other': {
        ID: 'other',
        TYPE: 'Thing',
        'label': 'Other',
    }
}
db['something']['seeAlso'] = db['other']
db['other'][REV] = {'seeAlso': [{k: v for k, v in db['something'].items() if k != 'seeAlso'}]}

ui_defs = {
    REV: {
        'label': "Saker som länkar hit"
    }
}

ld_context = {'ID': ID,'TYPE': TYPE, 'REV': REV, 'vocab': vocab, 'ui': ui_defs}
app.context_processor(lambda: ld_context)

@app.route('/page/<path:path>')
def thingview(path):
    thing = db[path]
    return render_template('thing.html', thing=thing)
