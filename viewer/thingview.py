from rdflib import RDFS
from flask import Blueprint, render_template

app = Blueprint('thingview', __name__)

ID, TYPE = '@id', '@type'

vocab = {
    'label': {
        ID: RDFS.label,
        'curie': 'rdfs:label name',
        'label': "Etikett"
    }
}

ld_context = {'ID': ID,'TYPE': TYPE, 'vocab': vocab}

app.context_processor(lambda: ld_context)

@app.route('/view/<path:path>')
def thingview(path):
    thing = {
        ID: path,
        TYPE: 'Thing',
        'label': 'Nothing'
    }
    return render_template('thing.html', thing=thing)
