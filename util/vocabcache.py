import os
import sys
import urllib2
from rdflib import Graph, OWL

def load_imports(cachedir, graph, vocab_url_map={}):
    impgraph = Graph()
    if not os.path.isdir(cachedir):
        os.makedirs(cachedir)
    for vocab in graph.objects(None, OWL.imports):
        fpath = os.path.join(cachedir, urllib2.quote(vocab, safe="")) + '.ttl'
        if os.path.exists(fpath):
            impgraph.parse(fpath, format='turtle')
        else:
            vocab_url = vocab_url_map.get(str(vocab), vocab)
            print >>sys.stderr, "Fetching", vocab_url, "to", fpath
            g = Graph().parse(vocab_url)
            with open(fpath, 'w') as f:
                g.serialize(f, format='turtle')
            impgraph += g
    return impgraph
