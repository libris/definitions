import re
from collections import OrderedDict
import json

enums = json.load(open('source/enums.jsonld'))

collection_sets = set()
coll_values = {}

for item in enums.get('@graph') or enums['enumDefs'].values():
    colls = item.get('inCollection')
    if colls:
        for c in colls:
            coll_values.setdefault(c['@id'], []).append(item['@id'])
        collection_sets.add(tuple(sorted(c['@id'] for c in colls)))

value_sets = {}

for cset in collection_sets:
    for c in cset:
        name = c
        members = set(coll_values[c])
        value_sets.setdefault(tuple(sorted(members)), set()).add(name)

def common_key(terms):
    prev = set()
    keys = []
    for term in terms:
        key = term.rsplit('/', 1)[-1]
        keys.append(key)
        parts = set(re.findall(r'[A-Z][^A-Z]*', term))
        candidates = prev & parts if prev else parts
        if not candidates:
            candidates = parts | prev
        prev = candidates
    return "Or".join(keys) if len(candidates) > 1 else next(iter(candidates))

equivs = OrderedDict()
for values, equiv_colls in value_sets.items():
    if len(equiv_colls) > 1:
        equivs[common_key(equiv_colls)] =\
                [{'values': values}] + \
                list(equiv_colls)

def dump(data):
    print(json.dumps(data, indent=2, sort_keys=True, separators=(',', ': ')))

print "# Equivalent collections:"
dump(equivs)

print "# Map:"
cmap = {}
for key, paths in equivs.items():
    cmap[key] = [path.rsplit('/', 1)[-1] for path in paths if isinstance(path, unicode)]
dump(cmap)
