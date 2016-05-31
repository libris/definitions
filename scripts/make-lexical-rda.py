#!/usr/bin/env python
from rdflib import Graph
from os import path as P
import sys

RDA_SOURCE_NAMES = ['a', 'c', 'w', 'e', 'm', 'i', 'z']

g = Graph()

for name in RDA_SOURCE_NAMES:
    g.parse("http://rdaregistry.info/Elements/{}.ttl".format(name), format='turtle')

with open(P.join(P.dirname(__file__), 'make-lexical-rda.rq')) as fp:
    res = g.query(fp)

for name in RDA_SOURCE_NAMES:
    res.graph.namespace_manager.bind(name,
            "http://rdaregistry.info/Elements/{}/".format(name))

res.graph.serialize(sys.stdout, format='turtle')
