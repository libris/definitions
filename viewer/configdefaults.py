from __future__ import unicode_literals
from os import path as P

DEBUG=False

ENVIRONMENT = 'UNKNOWN'

DBHOST='127.0.0.1'
DBNAME='definitions'
DBUSER=None
DBPASSWORD=None

ESHOST='127.0.0.1'
ES_INDEX = DBNAME
ES_SNIFF_ON_START=True

VOCAB_IRI = "https://id.kb.se/vocab/"
LANG = "sv"

# TODO: Move relative locations below to application-defined storage when
# separating viewer instance from definitions data.
BASE_DIR = P.join(P.dirname(__file__), "..")
GRAPH_CACHE = P.join(BASE_DIR, "cache/graph-cache")
VOCAB_SOURCES=[P.join(BASE_DIR, "build/vocab.jsonld"), "http://www.w3.org/2004/02/skos/core#"]
JSONLD_CONTEXT_FILE=P.join(BASE_DIR, "build/lib-context.jsonld")
MARCFRAME_SOURCE=P.join(BASE_DIR, "cache/ext/marcframe.json")
