from flask import Blueprint, render_template, redirect
from rdflib import Graph, URIRef, Literal, BNode, RDF, RDFS, OWL
from rdflib.resource import Resource
from rdflib.namespace import SKOS, Namespace, ClosedNamespace
from util.graphcache import GraphCache, vocab_source_map


DC = Namespace("http://purl.org/dc/terms/")
VANN = Namespace("http://purl.org/vocab/vann/")
VS = Namespace("http://www.w3.org/2003/06/sw-vocab-status/ns#")
SCHEMA = Namespace("http://schema.org/")

rdfutils = {name: obj for name, obj in globals().items()
                if isinstance(obj, (Namespace, ClosedNamespace))
                    or obj in (URIRef, Literal, BNode)}

app = Blueprint('vocabview', __name__)

app.context_processor(lambda: rdfutils)

@app.record
def setup_app(setup_state):
    config = setup_state.app.config
    global LANG
    LANG = config['LANG']

    graphcache = GraphCache(config['GRAPH_CACHE'])
    ns_mgr = Graph().parse(config['JSONLD_CONTEXT_FILE'],
            format='json-ld').namespace_manager
    ns_mgr.bind("", config['VOCAB_IRI'])

    global get_vocab_graph
    def get_vocab_graph():
        graph = None
        for path in config['VOCAB_SOURCES'][:1]:
            lgraph = graphcache.load(path)
            if not graph:
                graph = lgraph
                graph.namespace_manager = ns_mgr
            else:
                graph += lgraph
        for url in graph.objects(None, OWL.imports):
            graphcache.load(vocab_source_map.get(str(url), url))
        extgraph = graphcache.graph
        graphcache.graph.namespace_manager = ns_mgr
        return graph


@app.route('/vocab/')
def vocabview():
    graph = get_vocab_graph()

    def get_classes(graph):
        return [graph.resource(cid) for cid in sorted(
                set((graph.subjects(RDF.type, RDFS.Class)))
                | set((graph.subjects(RDF.type, OWL.Class))))
            if isinstance(cid, URIRef)]

    def get_properties(graph):
        return map(graph.resource, sorted(
            set(graph.subjects(RDF.type, RDF.Property))
            | set(graph.subjects(RDF.type, OWL.ObjectProperty))
            | set(graph.subjects(RDF.type, OWL.DatatypeProperty))))

    def getrestrictions(rclass):
        for c in rclass.objects(RDFS.subClassOf):
            rtype = c.value(RDF.type)
            if rtype and rtype.identifier == OWL.Restriction:
                yield c

    def value(obj, prop, lang=None):
        lang = lang or LANG
        label = None
        for label in obj.objects(prop):
            if label.language == lang:
                return label
        return label

    def label(obj, lang=None):
        lang = lang or LANG
        return value(obj, RDFS.label, lang)
        label = None
        for label in obj.objects(RDFS.label):
            if label.language == lang:
                return label
        return label

    def find_references(items):
        for o in items:
            ref = o.identifier if isinstance(o, Resource) else o
            if isinstance(ref, URIRef):
                yield o

    def link(obj):
        if ':' in obj.qname() and not any(obj.objects(None)):
            return obj.identifier
        return '#' + obj.qname()

    def listclass(o):
        return 'ext' if ':' in o.qname() else 'loc'

    return render_template('vocab.html', **vars())
