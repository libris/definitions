#!/usr/bin/env python
from rdflib import *
from os import path as P
import sys

g = Graph()
for uri in """
    http://rdaregistry.info/Elements/a.ttl
    http://rdaregistry.info/Elements/c.ttl
    http://rdaregistry.info/Elements/w.ttl
    http://rdaregistry.info/Elements/e.ttl
    http://rdaregistry.info/Elements/m.ttl
    http://rdaregistry.info/Elements/i.ttl
    http://rdaregistry.info/Elements/z.ttl
    """.split():
    g.parse(uri, format='turtle')

with open(P.join(P.dirname(__file__), 'make-lexical-rda.rq')) as fp:
    res = g.query(fp)

res.serialize(sys.stdout, format='turtle')
