from flask import Blueprint, render_template
from rdflib import Graph, URIRef, Literal, BNode, RDF, RDFS, OWL
from rdflib.namespace import SKOS, Namespace, ClosedNamespace
from util.graphcache import GraphCache


DC = Namespace("http://purl.org/dc/terms/")
VANN = Namespace("http://purl.org/vocab/vann/")
VS = Namespace("http://www.w3.org/2003/06/sw-vocab-status/ns#")
SCHEMA = Namespace("http://schema.org/")

rdfutils = {name: obj for name, obj in globals().items()
                if isinstance(obj, (Namespace, ClosedNamespace))
                    or obj in (URIRef, Literal, BNode)}

graphcache = GraphCache("cache/graph-cache")

app = Blueprint('vocabview', __name__)

app.context_processor(lambda: rdfutils)

@app.route('/vocabview/')
def vocabview():

    graph = Graph().parse("def/terms.ttl", format='turtle')
    graphcache.update(
            ("http://schema.org/docs/schema_org_rdfa.html" if str(url) ==
                str(SCHEMA) else url)
            for url in graph.objects(None, OWL.imports))
    extgraph = graphcache.graph

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
