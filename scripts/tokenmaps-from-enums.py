from __future__ import unicode_literals, print_function
from collections import OrderedDict
import json
from rdflib import *
from rdflib.util import guess_format
from rdflib.namespace import SKOS


import sys
fpath = sys.argv[1]


SDO = Namespace("http://schema.org/")
MAP = Namespace("http://id.kb.se/marc/")

cg = ConjunctiveGraph()
cg.parse(sys.stdin if fpath == '-' else fpath, format=guess_format(fpath), publicID="source/")

def dump(data):
    print(json.dumps(data, indent=2, sort_keys=True, separators=(',', ': ')))


#uri_map = {}
#for coll in sorted(cg.resource(MAP.CollectionClass).subjects(RDF.type)):
#    for dfn in coll.subjects(RDF.type):
#        for alias in dfn.objects(OWL.sameAs):
#            if dfn.identifier == SDO.False:
#                continue
#            uri_map[alias.identifier] = dfn.identifier
#dump(uri_map)
#exit()


# NOTE: this approach is abandoned, tokens with multiple types may have multiple notations
token_maps = {}
for coll in sorted(cg.resource(MAP.CollectionClass).subjects(RDF.type)):
    map_key = coll.qname()
    #map_key = coll.value(SKOS.notation)
    #map_key = map_key[0].lower() + map_key[1:]
    token_map = token_maps[map_key] = {}
    members = list(coll.subjects(RDF.type))
    for dfn in members:
        dup = 1
        for token_key in dfn.objects(SKOS.notation):
            if token_key in token_map:
                dup += 1
                token_key = token_key +'-'+ str(dup)
            token_map[token_key] = False if dfn[OWL.sameAs:SDO.False] \
                    else dfn.identifier.replace('http://id.kb.se/marc/', 'marc:')
    #if coll[RDFS.subClassOf:MAP.Boolean]:
    #    token_map['__bool__'] = True
dump(token_maps)


#marcframe = {}
#for fieldprop, marc_type in cg.resource(MAP.marcType).subject_objects():
#    assert unicode(marc_type) in {'bib', 'auth', 'hold'}
#    field = marcframe.setdefault(marc_type, {})[fieldprop.value(SKOS.notation)] = {}
#    field['repeatable'] = fieldprop.value(MAP.repeatable).toPython()
#    for subprop in fieldprop.subjects(RDFS.domain):
#        subfield = field['$' + subprop.value(SKOS.notation)] = {}
#        repeatable = subprop.value(MAP.repeatable)
#        subfield['repeatable'] = repeatable.toPython()
#        prop = subprop.value(OWL.sameAs)
#        if prop:
#            key = prop.identifier.replace(MAP, '')
#            subfield['addProperty' if repeatable else 'property'] = key
#dump(marcframe)
