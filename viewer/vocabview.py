from flask import Blueprint, render_template
from rdflib import Graph, URIRef, Literal, BNode, RDF, RDFS, OWL
from rdflib.namespace import SKOS, Namespace, ClosedNamespace
from util.graphcache import GraphCache, vocab_source_map


DC = Namespace("http://purl.org/dc/terms/")
VANN = Namespace("http://purl.org/vocab/vann/")
VS = Namespace("http://www.w3.org/2003/06/sw-vocab-status/ns#")
SCHEMA = Namespace("http://schema.org/")

rdfutils = {name: obj for name, obj in globals().items()
                if isinstance(obj, (Namespace, ClosedNamespace))
                    or obj in (URIRef, Literal, BNode)}

vocab_paths = ["def/terms.ttl", "sys/app/help.jsonld"]
graphcache = GraphCache("cache/graph-cache")
ns_mgr = None

app = Blueprint('vocabview', __name__)

app.context_processor(lambda: rdfutils)

@app.route('/vocabview/')
def vocabview():
    global ns_mgr
    graph = None
    for path in vocab_paths:
        lgraph = graphcache.load(path)
        if not graph:
            graph = lgraph
            if ns_mgr:
                graph.namespace_manager = ns_mgr
            else:
                ns_mgr = graph.namespace_manager
        else:
            graph += lgraph
    for url in graph.objects(None, OWL.imports):
        graphcache.load(vocab_source_map.get(url, url))
    extgraph = graphcache.graph

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
