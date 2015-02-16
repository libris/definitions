import os
import sys
import urllib2
import logging
from rdflib import ConjunctiveGraph
from rdflib.parser import create_input_source
from rdflib.util import guess_format


logger = logging.getLogger(__name__)


vocab_source_map = {
    "http://schema.org/": "http://schema.org/docs/schema_org_rdfa.html"
}


class GraphCache(object):

    def __init__(self, cachedir):
        self.graph = ConjunctiveGraph()
        self.mtime_map = {}
        self.cachedir = cachedir
        if not os.path.isdir(cachedir):
            os.makedirs(cachedir)

    def load(self, url):
        if os.path.isfile(url):
            context_id = create_input_source(url).getPublicId()
            last_vocab_mtime = self.mtime_map.get(url)
            vocab_mtime = os.stat(url).st_mtime
            if not last_vocab_mtime or last_vocab_mtime < vocab_mtime:
                logger.debug("Parse file: '%s'", url)
                self.mtime_map[url] = vocab_mtime
                return self.graph.parse(url, format=guess_format(url))
        else:
            context_id = url

        if any(self.graph.triples((None, None, None), context=context_id)):
            logger.debug("Using context <%s>" % context_id)
            return self.graph.get_context(context_id)

        cache_path = os.path.join(self.cachedir, urllib2.quote(url, safe="")) + '.ttl'
        if os.path.exists(cache_path):
            logger.debug("Load local copy of <%s> from '%s'", context_id, cache_path)
            return self.graph.parse(cache_path, format='turtle', publicID=context_id)
        else:
            logger.debug("Fetching <%s> to '%s'", context_id, cache_path)
            graph = self.graph.parse(url,
                    format='rdfa' if url.endswith('html') else None)
            with open(cache_path, 'w') as f:
                graph.serialize(f, format='turtle')
            return graph
