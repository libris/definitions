"""
Just a throw-away script for making a reduced example vocabulary from
the core vocabulary and some supplied example usage data.
"""

from __future__ import unicode_literals, print_function
import json
from rdflib import Graph, BNode
from rdflib.namespace import OWL, RDF, RDFS, SKOS
from os import path as P
import sys


args = sys.argv[1:]
if len(args) < 2:
    print("Usage: SCRIPT DATA_FILE CONTEXT_FILE", file=sys.stderr)
    exit(1)
fpath = args.pop(0)
ctx = args.pop(0)


# Load the core vocabulary located nearby...
vocpath = P.join(P.dirname(__file__), '../def/terms.ttl')
vocab = Graph().parse(vocpath, format='turtle')


# Get "real" vocab uri and use instead of example vocab
for s in vocab.subjects(RDF.type, OWL.Ontology):
    vocab_uri = unicode(s)
    break

with open(ctx) as fp:
    ctx = json.load(fp)['@context']
    ctx['@vocab'] = vocab_uri


# Collect used predicates and types
terms = set()
examples = Graph().parse(fpath, format="json-ld", context=ctx)
for p, o in examples.predicate_objects():
    if p == RDF.type:
        terms.add(o)
        terms |= set(o for o in vocab.objects(o, (OWL.equivalentClass | RDFS.subClassOf)*'+')
                if not isinstance(o, BNode))
    else:
        terms.add(p)
        terms |= set(o for o in vocab.objects(p, (OWL.equivalentProperty | RDFS.subPropertyOf)*'+')
                if not isinstance(o, BNode))


# Gather used parts described with a limited selection of classes and predicates
parts = Graph()
parts.namespace_manager = vocab.namespace_manager

textprops = {RDFS.label, RDFS.comment,
         SKOS.prefLabel, SKOS.altLabel, SKOS.definition, SKOS.note}
props = {RDFS.subPropertyOf, RDFS.subClassOf,
         OWL.equivalentProperty, OWL.equivalentClass} | {
         RDFS.domain, RDFS.range
         } | textprops
types = {OWL.Class, OWL.DatatypeProperty, OWL.ObjectProperty, OWL.Restriction, RDFS.Datatype}
for t in terms:
    for p, o in vocab.predicate_objects(t):
        if p in props or p == RDF.type and o in types:
            parts.add((t,p, o))

missing = sorted(parts.qname(t) for t in (terms - set(parts.subjects())))
if missing:
    print("# Missing:", ", ".join(missing), file=sys.stderr)


# Make a nice compact context for the output model
ctx = {}
for t in props | types:
    key = vocab.qname(t).split(':')[-1]
    if t in textprops:
        ctx[key + 'ByLang'] = {"@id": unicode(t), "@container": "@language"}
    ctx[key] = unicode(t)
for pfx, ns in vocab.namespaces():
    ctx[pfx if pfx else '@vocab'] = ns

jstr = parts.serialize(format='json-ld', context=ctx, sort_keys=True)

# Then clean it up further...
model = json.loads(jstr)
model['@graph'].sort(key=lambda it: it['@id'])
model['@context'] = "/sys/context.jsonld"
s = json.dumps(model, indent=2, separators=(',', ': '), sort_keys=True, ensure_ascii=False)

for pfx, ns in vocab.namespaces():
    s = s.replace(ns, pfx + ':' if pfx else '')

import re
s = re.sub(r'{\s+(\S+: "[^"]*")\s+}', r'{\1}', s)
s = re.sub(r'\[\s+([^,]+?),\s+([^,]+?)\s+\]', r'[\1, \2]', s)
s = re.sub(r'{\s+([^,]+?),\s+([^,]+?)\s+}', r'{\1, \2}', s)

print(s.encode('utf-8'))
