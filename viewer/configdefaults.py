from __future__ import unicode_literals
from os import path as P

DEBUG=False

ENVIRONMENT = 'UNKNOWN'
VERSION = 'UNKNOWN'

DBHOST='127.0.0.1'
DBNAME='definitions'
DBUSER=None
DBPASSWORD=None

ESHOST='127.0.0.1'
ES_INDEX = DBNAME
ES_SNIFF_ON_START=True

# TODO: Move relative cache location to instance directory (or application storage)
CACHE_DIR = P.join(P.dirname(__file__), "..", "cache")
#GRAPH_CACHE = P.join(CACHE_DIR, "graph-cache")

VOCAB_IRI = "https://id.kb.se/vocab/"
LANG = "sv"

# TODO: read this from live XL system instead (as soon as that is possible)
MARCFRAME_SOURCE = "https://raw.githubusercontent.com/libris/librisxl/develop/converters/src/main/resources/ext/marcframe.json"
