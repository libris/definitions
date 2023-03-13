#!/usr/bin/env python3
import sys

from rdflib import ConjunctiveGraph
from rdflib.plugin import Parser, register

register("text/html", Parser, "pyRdfa.rdflibparsers", "RDFaParser")

queryfile, *infiles = sys.argv[1:]

cg = ConjunctiveGraph()
for infile in infiles:
    cg.parse(infile)

with open(queryfile) as f:
    res = cg.query(f.read())

res.graph.namespace_manager = cg.namespace_manager
res.serialize(sys.stdout.buffer, format='turtle')
