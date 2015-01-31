import os
import sys
import urllib2
from rdflib import ConjunctiveGraph


class GraphCache(object):

    def __init__(self, cachedir):
        self.graph = ConjunctiveGraph()
        self.cachedir = cachedir
        if not os.path.isdir(cachedir):
            os.makedirs(cachedir)

    def update(self, urls):
        for url in urls:
            if any(self.graph.triples((None, None, None), context=url)):
                continue
            fpath = os.path.join(self.cachedir, urllib2.quote(url, safe="")) + '.ttl'
            if os.path.exists(fpath):
                self.graph.parse(fpath, format='turtle', publicID=url)
            else:
                print >>sys.stderr, "Fetching", url, "to", fpath
                graph = self.graph.parse(url,
                        format='rdfa' if fpath.endswith('html') else None)
                with open(fpath, 'w') as f:
                    graph.serialize(f, format='turtle')
