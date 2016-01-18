# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
__metaclass__ = type

from collections import OrderedDict, namedtuple

from rdflib import Graph, Literal, URIRef, Namespace, RDF, RDFS, OWL

from lddb.ld.keys import *
from lddb.ld.frame import autoframe


SDO = Namespace("http://schema.org/")
VS = Namespace("http://www.w3.org/2003/06/sw-vocab-status/ns#")


# TODO: VocabView?
class Vocab:

    def __init__(self, vocab_graph, vocab_uri, lang='en'):
        self.index = {}
        self.unstable_keys = set()
        self.lang = lang

        label_key_items = []

        g = vocab_graph
        default_ns = g.store.namespace('')

        get_key = lambda s: s.replace(vocab_uri, '')

        PREF_LABEL = URIRef(vocab_uri + 'prefLabel')
        BASE_LABEL = URIRef(vocab_uri + 'label')

        for s in set(g.subjects()):
            if not isinstance(s, URIRef):
                continue
            if not s.startswith(vocab_uri):
                continue

            key = get_key(s)

            label = None
            for label in g.objects(s, RDFS.label):
                if label.language == lang:
                    break
            if label:
                label = unicode(label)

            for domain in g.objects(s, RDFS.domain | SDO.domainIncludes):
                domain_key = get_key(domain)
                self.index.setdefault(domain_key, {}).setdefault(
                        'properties', []).append(key)

            term = {ID: unicode(s),'label': label, 'curie': key}

            if (s, RDF.type, OWL.ObjectProperty) in g:
                term[TYPE] = ID

            self.index.setdefault(key, {}).update(term)

            if (s, VS.term_status, Literal('unstable')) in g:
                self.unstable_keys.add(key)

            def distance_to(prop):
                return path_distance(g, s,
                    RDFS.subPropertyOf | OWL.equivalentProperty, prop)

            label_distance = distance_to(BASE_LABEL)

            if label_distance is not None:
                preflabel_distance = distance_to(PREF_LABEL)
                order = (preflabel_distance
                         if preflabel_distance is not None else -1,
                         label_distance)
                label_key_items.append((order, key))

        self.label_keys = [key for ldist, key in sorted(label_key_items, reverse=True)]

        self.partof_keys = ['inScheme', 'isDefinedBy', 'inCollection', 'inDataset']
        # TODO: generate vocab-json for label keys, sorting etc.
        #import pprint
        #pprint.pprint(self.index)

    def sortedkeys(self, item):
        # TODO: groups:
        #   - main: labels, descriptions, type-close links, notes
        #   - provenance: dates, publication, ...
        #   - for pages/records:
        #       - administrativa: created, updated
        #       - structural navigation: prev, next, alternate formats
        typeprops = set()
        for itype in as_iterable(item.get(TYPE)):
            typedfn = self.index.get(itype)
            if typedfn:
                typeprops.update(typedfn.get('properties', []))

        def keykey(key):
            is_kw = key.startswith('@')
            is_unstable = key in self.unstable_keys
            try:
                label_number = self.label_keys.index(key)
            except ValueError:
                label_number = len(self.label_keys)
            try:
                partof_number = self.partof_keys.index(key)
            except ValueError:
                partof_number = len(self.partof_keys)
            is_link = self.index[key].get(TYPE) == ID
            classdistance = 0 if typeprops and key in typeprops else 1
            return (is_kw,
                    partof_number,
                    label_number,
                    is_link,
                    classdistance,
                    key)

        # Changing language containers to simple values...
        # TODO:
        # - either support containers by properly using the context
        # - or optimize this rewriting
        # - or do not allow this form (remove from base context)
        for key in item:
            if key.endswith('ByLang'):
                v = item.pop(key).get(self.lang)
                newk = key[:-len('ByLang')]
                item[newk] = v

        return sorted((key for key in item
            if key in self.index
            and key not in self.unstable_keys), key=keykey)

    def get_label_for(self, item):
        focus = item.get('focus')
        if focus:
            label = self.construct_label(focus)
            if label:
                return label
        if 'prefLabel' not in item: # ComplexTerm in types
            termparts = item.get('termParts', [])
            if termparts:
                return " - ".join(self.labelgetter(bit) for bit in termparts)
        return self.labelgetter(item)

    def construct_label(self, item):
        has = item.__contains__
        v = lambda k: " ".join(as_iterable(item.get(k, '')))
        vs = lambda *ks: [v(k) for k in ks if has(k)]

        types = set(as_iterable(item.get(TYPE)))

        if types & {'UniformWork', 'CreativeWork'}:
            label = self.labelgetter(item)
            attr = item.get('attributedTo')
            if attr:
                attr_label = self.construct_label(attr)
                if attr_label:
                    label = "%s (%s)" % (label, attr_label)
            return label

        if types & {'Person', 'Persona', 'Family', 'Organization', 'Meeting'}:
            return " ".join([
                    v('name') or ", ".join(vs('familyName', 'givenName')),
                    v('numeration'),
                    "(%s)" % v('personTitle') if has('personTitle') else "",
                    "%s-%s" % (v('birthYear'), v('deathYear'))
                    if (has('birthYear') or has('deathYear')) else ""])

    def labelgetter(self, item):
        for lkey in self.label_keys:
            label = item.get(lkey)
            if label:
                if isinstance(label, list):
                    return label[0]
                return label
        return ""


class View:

    def __init__(self, vocab, storage, elastic, es_index):
        self.vocab = vocab
        self.storage = storage
        self.elastic = elastic
        self.es_index = es_index
        self.rev_limit = 4000
        self.chip_keys = {ID, TYPE, 'focus', 'mainEntity', 'sameAs'} | set(self.vocab.label_keys)
        self.reserved_parameters = ['q', 'limit', 'offset', 'p', 'o', 'value']

    def get_record_data(self, item_id):
        record = self.storage.get_record(item_id)
        return record.data if record else None

    def find_record_ids(self, item_id):
        record_ids = self.storage.find_record_ids(item_id)
        return list(record_ids)

    def find_same_as(self, item_id):
        # TODO: only get identifier
        records = self.storage.find_by_relation('sameAs', item_id, limit=1)
        if records:
            return records[0].identifier

    def get_search_results(self, req_args, make_find_url, base_uri=None):
        #s = req_args.get('s')
        p = req_args.get('p')
        o = req_args.get('o')
        value = req_args.get('value')
        #language = req_args.get('language')
        #datatype = req_args.get('datatype')
        q = req_args.get('q')
        limit, offset = self._get_limit_offset(req_args)
        if not isinstance(offset, (int, long)):
            offset = 0

        total = None
        records = []
        items = []
        page_params = {'p': p, 'o': o, 'value': value, 'q': q, 'limit': limit}

        # TODO: unify find_by_relation and find_by_example, support the latter form here too
        if p:
            if o:
                records = self.storage.find_by_relation(p, o, limit, offset)
            elif value:
                records = self.storage.find_by_value(p, value, limit, offset)
            elif q:
                records = self.storage.find_by_query(p, q, limit, offset)
        elif o:
            records = self.storage.find_by_quotation(o, limit, offset)
        elif q and not p:
            # Search in elastic

            musts = [
                {"query_string": { "query": "{0}".format(q) }}
            ]

            for param, paramvalue in req_args.items():
                if param.startswith('_') or param in self.reserved_parameters:
                    continue
                musts.append({"match": {param: paramvalue}})
                page_params.setdefault(param, []).append(paramvalue)

            dsl = {
                "query": {
                    "bool": {
                        "must": musts,
                        "should": [
                            {"prefix" : {"@id": base_uri}},
                            {"prefix" : {"sameAs.@id": base_uri}}
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
            # TODO: only ask ES for chip properties instead of post-processing
            results = self.elastic.search(body=dsl, size=limit, from_=offset,
                             index=self.es_index).get('hits')
            total = results.get('total')
            items = [self.to_chip(r.get('_source')) for r in
                     results.get('hits')]

        for rec in records:
            chip = self.to_chip(self.get_decorated_data(rec.data, include_quoted=False))
            items.append(chip)


        def ref(link): return {ID: link}

        results = OrderedDict({'@type': 'PagedCollection'})
        results['@id'] = make_find_url(offset=offset, **page_params)
        results['itemsPerPage'] = limit
        #if total is not None:
        results['itemOffset'] = offset
        results['totalItems'] = total
        results['firstPage'] = ref(make_find_url(**page_params))
        results['query'] = q
        results['value'] = value
        #'lastPage' ...
        if offset:
            prev_offset = offset - limit
            if prev_offset <= 0:
                prev_offset = None
            results['previousPage'] = ref(make_find_url(offset=prev_offset, **page_params))
        if len(items) == limit:
            next_offset = offset + limit if offset else limit
            results['nextPage'] = ref(make_find_url(offset=next_offset, **page_params))
        # hydra:member
        results['items'] = items

        return results

    def _get_limit_offset(self, args):
        limit = args.get('limit')
        offset = args.get('offset')
        if limit and limit.isdigit():
            limit = int(limit)
        if offset and offset.isdigit():
            offset = int(offset)
        return self.storage.get_real_limit(limit), offset

    def get_type_count(self):
        pairs = [(self.vocab.index[rtype], count)
                for rtype, count in self.storage.get_type_count()
                if isinstance(rtype, str)
                if rtype in self.vocab.index]
        pairs.sort(key=lambda pair: pair[0]['label'])
        return pairs

    def get_index_aggregate(self, base_uri):
        dsl = {
            "size": 0,
            "query" : {
                "bool": {
                    "should": [
                        {"prefix" : {"@id": base_uri}},
                        {"prefix" : {"sameAs.@id": base_uri}}
                    ]
                }
            },
            "aggs": {
                "inScheme.@id": {
                    "terms": {
                        "field": "inScheme.@id",
                        #"size": 1000
                    },
                    "aggs": {
                        "@type": {
                            "terms": {
                                "field": "@type",
                                #"size": 1000
                            }
                        }
                    }
                }
            }
        }
        results = self.elastic.search(body=dsl, size=dsl['size'],
                index=self.es_index)

        def lookup(item_id):
            data = self.get_record_data(item_id)
            return get_descriptions(data).entry if data else None

        for path, agg in results['aggregations'].items():
            for bucket in agg['buckets']:
                item_id = bucket['key']
                bucket['resource'] = lookup(item_id)
                for bucket2 in bucket['@type']['buckets']:
                    bucket2['resource'] = self.vocab.index[bucket2['key']]

        return {TYPE: 'WebSite', ID: base_uri, 'statistics': results}

    def get_decorated_data(self, data, add_references=False, include_quoted=True):
        entry, other, quoted = get_descriptions(data)

        main_item = entry if entry else other.pop(0) if other else None
        main_id = main_item.get(ID) if main_item else None

        items = []
        if entry:
            items.append(entry)
            # TODO: fix this in source and/or handle in view
            #if 'prefLabel_en' in entry and 'prefLabel' not in entry:
            #    entry['prefLabel'] = entry['prefLabel_en']
        if other:
            items += other

        if quoted and include_quoted:
            unquoted = [dict(ngraph[GRAPH], quotedFromGraph={ID: ngraph.get(ID)})
                    for ngraph in quoted]
            items += unquoted

        framed = autoframe({GRAPH: items}, main_id)
        if framed:
            refs = self._get_references_to(main_item) if add_references else []
            # NOTE: workaround for autoframing frailties
            refs = [ref for ref in refs if ref[ID] != main_id]
            framed.update(autoframe({GRAPH: [{ID: main_id}] + refs}, main_id))
            return framed
        else:
            return data


    def getlabel(self, item):
        # TODO: get and cache chip for item (unless already quotedFrom)...
        return self.vocab.get_label_for(item) or ",".join(v for k, v in item.items()
                if k[0] != '@' and isinstance(v, unicode)) or item[ID]
                #or getlabel(self.get_chip(item[ID]))

    def to_chip(self, item, *keep_refs):
        return {k: v for k, v in item.items()
                if k in self.chip_keys or has_ref(v, *keep_refs)}

    def _get_references_to(self, item):
        references = []
        # TODO: send choice of id:s to find_by_quotation?
        same_as = item.get('sameAs') if item else None
        item_id = item[ID]
        quoted_id = same_as[0].get(ID) if same_as else item_id

        for quoting in self.storage.find_by_quotation(quoted_id, limit=200):
            qdesc = get_descriptions(quoting.data)

            _fix_refs(item_id, quoted_id, qdesc)
            references.append(self.to_chip(qdesc.entry, item_id, quoted_id))
            for it in qdesc.items:
                references.append(self.to_chip(it, item_id, quoted_id))

        return references


Descriptions = namedtuple('Descriptions', 'entry, items, quoted')

def get_descriptions(data):
    if 'descriptions' in data:
        return Descriptions(**data['descriptions'])
    elif GRAPH in data:
        items, quoted = [], []
        for item in data[GRAPH]:
            if GRAPH in item:
                quoted.append(item)
            else:
                items.append(item)
        entry = items.pop(0)
        return Descriptions(entry, items, quoted)
    else:
        return Descriptions(data, [], [])

# FIXME: quoted id:s are temporary and should be replaced with canonical id (or
# *at least* sameAs id) in stored data
def _fix_refs(real_id, ref_id, descriptions):
    entry, items, quoted = descriptions
    alias_map = {}
    for quote in quoted:
        item = quote[GRAPH]
        alias = item[ID]
        if alias == ref_id:
            alias_map[alias] = real_id
        else:
            for same_as in as_iterable(item.get('sameAs')):
                if same_as[ID] == ref_id:
                    alias_map[alias] = real_id

    _fix_ref(entry, alias_map)
    for item in items:
        _fix_ref(item, alias_map)

def _fix_ref(item, alias_map):
    for vs in item.values():
        for v in as_iterable(vs):
            if isinstance(v, dict):
                mapped = alias_map.get(v.get(ID))
                if mapped:
                    v[ID] = mapped


def as_iterable(vs):
    """
    >>> list(as_iterable(None))
    []
    >>> list(as_iterable([1]))
    [1]
    >>> list(as_iterable(1))
    [1]
    """
    if vs is None:
        return
    if isinstance(vs, list):
        for v in vs:
            yield v
    else:
        yield vs

def has_ref(vs, *refs):
    """
    >>> has_ref({ID: '/item'}, '/item')
    True
    >>> has_ref({ID: '/other'}, '/item')
    False
    >>> has_ref({ID: '/other'}, '/item', '/other')
    True
    >>> has_ref([{ID: '/item'}], '/item')
    True
    """
    for v in as_iterable(vs):
        if isinstance(v, dict) and v.get(ID) in refs:
            return True
    return False

def path_distance(g, s, p, base):
    """
    >>> ns = Namespace("urn:x-ns:")
    >>> g = Graph()
    >>> subpropof = RDFS.subPropertyOf
    >>> g.add((ns.name, subpropof, ns.label))
    >>> g.add((ns.title, subpropof, ns.name))
    >>> g.add((ns.notation, subpropof, ns.title))
    >>> g.add((ns.notation, subpropof, ns.name))

    >>> path_distance(g, ns.comment, subpropof, ns.label)
    >>> path_distance(g, ns.label, subpropof, ns.label)
    0
    >>> path_distance(g, ns.name, subpropof, ns.label)
    1
    >>> path_distance(g, ns.title, subpropof, ns.label)
    2
    >>> path_distance(g, ns.notation, subpropof, ns.label)
    2
    """
    if s == base:
        return 0
    def find_path(s, distance=1):
        shortest = None
        for o in g.objects(s, p):
            if o == base:
                return distance
            else:
                candidate = find_path(o, distance+1)
                if shortest is None or (candidate is not None
                        and candidate < shortest):
                    shortest = candidate
        return shortest
    return find_path(s)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
