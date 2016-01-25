# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
__metaclass__ = type

from collections import OrderedDict, namedtuple

from . import as_iterable
from lddb.ld.keys import *
from lddb.ld.frame import autoframe


MAX_LIMIT = 4000
DEFAULT_LIMIT = 200


class DataView:

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
        return self.get_real_limit(limit), offset

    def get_real_limit(self, limit):
        return DEFAULT_LIMIT if limit is None or limit > MAX_LIMIT else limit

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
                        #"inCollection.@id": {
                        #    "terms": {
                        #        "field": "inCollection.@id",
                        #        #"size": 1000
                        #    }
                        #},
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
                #for subkey in ['@type', 'inCollection.@id']:
                #    if subkey not in bucket:
                #        continue
                #    for bucket2 in bucket[subkey]['buckets']:
                #        key = bucket2['key']
                #        bucket2['resource'] = self.vocab.index.get(key) or lookup(key)

        return {TYPE: 'WebSite', ID: base_uri, 'statistics': results}

    def find_ambiguity(self, request):
        kws = dict(request.args)
        rtype = kws.pop('type', None)
        q = kws.pop('q', None)
        if q:
            q = " ".join(q)
            #parts = _tokenize(q)
        example = {}
        if rtype:
            rtype = rtype[0]
            example['@type'] = rtype
        if q:
            example['label'] = q
        if kws:
            example.update({k: v[0] for k, v in kws.items()})

        def pick_thing(rec):
            for item in rec.data[GRAPH]:
                if rtype in as_iterable(item[TYPE]):
                    return item

        maybes  = [pick_thing(rec) #self.get_decorated_data(rec)
                   for rec in self.storage.find_by_example(example,
                           limit=MAX_LIMIT)]

        some_id = '%s?%s' % (request.path, request.query_string)
        item = {
            "@id": some_id,
            "@type": "Ambiguity",
            "label": q or ",".join(example.values()),
            "maybe": maybes
        }

        references = self._get_references_to(item)

        if not maybes and not references:
            return None

        return {GRAPH: [item] + references}

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
                if k in self.chip_keys or k.endswith('ByLang')
                   or has_ref(v, *keep_refs)}

    def _get_references_to(self, item):
        item_id = item[ID]
        # TODO: send choice of id:s to find_by_quotation?
        ids = [item_id]
        same_as = item.get('sameAs')
        if same_as:
            ids.append(same_as[0].get(ID))

        references = []
        for quoted_id in ids:
            if references:
                break
            for quoting in self.storage.find_by_quotation(quoted_id, limit=200):
                qdesc = get_descriptions(quoting.data)
                if quoted_id != item_id:
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


def _tokenize(stuff):
    """
    >>> print(_tokenize("One, Any (1911-)"))
    1911 any one
    """
    return sorted(set(
        re.sub(r'\W(?u)', '', part.lower(), flags=re.UNICODE)
        for part in stuff.split(" ")))
