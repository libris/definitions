# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
__metaclass__ = type

from rdflib import Graph, Literal, URIRef, Namespace, RDF, RDFS, OWL
from rdflib.resource import Resource

from lddb.ld.keys import ID, TYPE
from . import as_iterable


SDO = Namespace("http://schema.org/")
VS = Namespace("http://www.w3.org/2003/06/sw-vocab-status/ns#")


class VocabUtil:

    def __init__(self, graph, lang):
        self.graph = graph
        self.lang = lang
        self.resource = graph.resource

        vocabs = list(set(graph.subjects(RDF.type, OWL.Ontology))
                    | set(graph.objects(RDFS.isDefinedBy)))
        self.vocabs = vocabs
        self.vocab = graph.resource(vocabs[0])
        self.properties = self._get_properties()
        self.classes = self._get_classes()

    def _get_classes(self):
        return [self.graph.resource(cid) for cid in sorted(
                set((self.graph.subjects(RDF.type, RDFS.Class)))
                | set((self.graph.subjects(RDF.type, OWL.Class))))
            if isinstance(cid, URIRef)]

    def _get_properties(self):
        return map(self.graph.resource, sorted(
            set(self.graph.subjects(RDF.type, RDF.Property))
            | set(self.graph.subjects(RDF.type, OWL.ObjectProperty))
            | set(self.graph.subjects(RDF.type, OWL.DatatypeProperty))))

    def getrestrictions(self, rclass):
        for c in rclass.objects(RDFS.subClassOf):
            rtype = c.value(RDF.type)
            if rtype and rtype.identifier == OWL.Restriction:
                yield c

    def value(self, obj, prop, lang=None):
        lang = lang or self.lang
        label = None
        for label in obj.objects(prop):
            if label.language == lang:
                return label
        return label

    def label(self, obj, lang=None):
        lang = lang or self.lang
        return self.value(obj, RDFS.label, lang)
        label = None
        for label in obj.objects(RDFS.label):
            if label.language == lang:
                return label
        return label

    def find_references(self, items):
        for o in items:
            ref = o.identifier if isinstance(o, Resource) else o
            if isinstance(ref, URIRef):
                yield o


class VocabView:

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
            if not label:
                for label in as_iterable(item.get(lkey + 'ByLang')):
                    label = label.get(self.lang)
                    if label:
                        break
            if label:
                if isinstance(label, list):
                    return label[0]
                return label
        return ""


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
