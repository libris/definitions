# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
__metaclass__ = type

from rdflib import Graph, URIRef, Namespace, RDF, RDFS, OWL
ID, TYPE, REV = '@id', '@type', '@reverse'

SDO = Namespace("http://schema.org/")


class Vocab:

    def __init__(self, vocab_source, vocab_uri=None, lang='en'):
        self.index = {}
        label_key_items = []

        g = Graph().parse(vocab_source, format='turtle')
        default_ns = g.store.namespace('')
        if not vocab_uri and (default_ns, RDF.type, OWL.Ontology) in g:
            vocab_uri = default_ns

        get_key = lambda s: s.replace(vocab_uri, '')

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

            label_distance = path_distance(g, s,
                RDFS.subPropertyOf | OWL.equivalentProperty, BASE_LABEL)
            if label_distance is not None:
                label_key_items.append((label_distance, key))

        self.label_keys = [key for ldist, key in sorted(label_key_items, reverse=True)]

    def sortedkeys(self, item):
        itypes = item.get(TYPE) or []
        if not isinstance(itypes, list):
            itypes = [itypes]
        typeprops = set()
        for itype in itypes:
            typedfn = self.index.get(itype)
            if typedfn:
                typeprops.update(typedfn.get('properties', []))

        def keykey(key):
            classdistance = 0 if typeprops and key in typeprops else 1
            if key.startswith('@'):
                importance_index = 0
            else:
                try:
                    importance_index = self.label_keys.index(key)
                except ValueError:
                    importance_index = len(self.label_keys)
            is_link = self.index[key].get(TYPE) == ID
            return (importance_index, is_link, classdistance, key)

        return sorted((key for key in item if key in self.index), key=keykey)

    def labelgetter(self, item):
        for lkey in self.label_keys:
            label = item.get(lkey)
            if label:
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


if __name__ == '__main__':
    import doctest
    doctest.testmod()
