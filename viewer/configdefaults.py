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

VOCAB_IRI = "https://id.kb.se/vocab/"
LANG = "sv"

# TODO: Move relative cache location to instance directory (or application storage)
BASE_DIR = P.join(P.dirname(__file__), "..")
CACHE_DIR = P.join(BASE_DIR, "cache")
#GRAPH_CACHE = P.join(CACHE_DIR, "graph-cache")
MARCFRAME_SOURCE = P.join(BASE_DIR, "cache/ext/marcframe.json")
