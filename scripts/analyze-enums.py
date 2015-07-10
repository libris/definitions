import json

enums = json.load(open('source/enums.jsonld'))

collection_sets = set()
coll_values = {}

for item in enums['enumDefs'].values():
    colls = item.get('inCollection')
    if colls and len(colls) > 2:
        #print "\n    ".join(c['@id'] for c in [item] + colls)
        #print
        for c in colls:
            coll_values.setdefault(c['@id'], []).append(item['@id'])
        collection_sets.add(tuple(sorted(c['@id'] for c in colls)))

value_sets = {}

for cset in collection_sets:
    #prev_members = None
    for c in cset:
        name = c.replace('/collection/marc/', '')
        members = set(coll_values[c])
        value_sets.setdefault(tuple(sorted(members)), set()).add(name)
        #print name,
        #if prev_members and members == prev_members:
        #    print '(same)',
        #prev_members = members
    #print

print "# Equivalent collections:"
for equiv_colls in value_sets.values():
    if len(equiv_colls) > 1:
        print ", ".join(equiv_colls)
