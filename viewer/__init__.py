import json
from rdflib import *
from rdflib.namespace import SKOS
from util import vocabcache

DC = Namespace("http://purl.org/dc/terms/")
VANN = Namespace("http://purl.org/vocab/vann/")
VS = Namespace("http://www.w3.org/2003/06/sw-vocab-status/ns#")
SCHEMA = Namespace("http://schema.org/")


from flask import Flask, render_template


class MyFlask(Flask):
    jinja_options = dict(Flask.jinja_options,
            variable_start_string='${', variable_end_string='}',
            line_statement_prefix='%')

app = MyFlask(__name__, static_url_path='', static_folder='static')

#app.config.from_pyfile('config.cfg')

@app.context_processor
def global_view_variables():
    ns = globals()
    ns.update(__builtins__)
    ns['union'] = lambda *args: reduce(lambda a, b: a | b, args)
    return ns


@app.route('/')
def index():
    return render_template('index.html', **vars())


@app.route('/vocabview/')
def vocabview():

    graph = Graph().parse("def/terms.ttl", format='turtle')
    vocabcachedir = "cache/vocab-cache"
    extgraph = vocabcache.load_imports(vocabcachedir, graph,
            {str(SCHEMA): "http://schema.org/docs/schema_org_rdfa.html"})


    def getrestrictions(rclass):
        for c in rclass.objects(RDFS.subClassOf):
            rtype = c.value(RDF.type)
            if rtype and rtype.identifier == OWL.Restriction:
                yield c

    def label(obj, lang='sv'):
        label = None
        for label in obj.objects(RDFS.label):
            if label.language == lang:
                return label
        return label

    def link(obj):
        if ':' in obj.qname() and not any(obj.objects(None)):
            return obj.identifier
        return '#' + obj.qname()

    def listclass(o):
        return 'ext' if ':' in o.qname() else ''

    return render_template('vocab.html', **vars())


@app.route('/marcframeview/')
def marcframeview():

    marcframe_path = "etc/marcframe.json"
    with open(marcframe_path) as fp:
        marcframe = json.load(fp)

    MARC_CATEGORIES = 'bib', 'auth', 'hold'

    def marc_categories():
        for cat in MARC_CATEGORIES:
            yield cat, marcframe[cat]

    def fields(catdfn):
        for tag, dfn in sorted(catdfn.items()):
            if tag.isdigit() and dfn:
                kind = ('fixed' if any(k for k in dfn if k[0] == '[' and ':' in k)
                        else 'field' if any(k for k in dfn if k[0] == '$')
                        else 'control')
                yield tag, kind, dfn

    def codes(dfn):
        for code, subdfn in sorted(dfn.items()):
            if code.startswith('$') and subdfn:
                yield code, subdfn

    return render_template('marcframeview.html', **vars())
