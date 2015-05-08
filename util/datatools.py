# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
import logging
import os
import json
from rdflib import Graph, URIRef, Namespace, RDF, RDFS


logger = logging.getLogger(__name__)

ID, TYPE, REV = '@id', '@type', '@reverse'


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


def load_vocab(vocab_source, vocab_uri, lang):
    vocab = {}
    label_keys = []

    BASE_LABEL = URIRef(vocab_uri + 'label')
    g = Graph().parse(vocab_source, format='turtle')
    for s in set(g.subjects()):
        if not isinstance(s, URIRef):
            continue
        if not s.startswith(vocab_uri):
            continue
        key = s.replace(vocab_uri, '')
        label = key
        for label in g.objects(s, RDFS.label):
            if label.language == lang:
                break
        if label:
            label = unicode(label)
        term = {ID: unicode(s),'label': label, 'curie': key}
        vocab[key] = term
        label_distance = path_distance(g, s, RDFS.subPropertyOf, BASE_LABEL)
        if label_distance is not None:
            label_keys.append((label_distance, key))
    label_keys = [key for ldist, key in sorted(label_keys, reverse=True)]

    return vocab, label_keys


def load_db(db_source, label_keys):
    db = {}
    same_as = {}

    if not os.path.exists(db_source):
        logger.warn("DB source %s does not exist", db_source)
        return

    for l in open(db_source):
        data = json.loads(l)
        data.pop('_marcUncompleted', None)
        item = data.pop('about')
        item['describedBy'] = data
        db[item[ID]] = item
        for l_key in label_keys:
            if l_key in item:
                item['label'] = item[l_key]
                break
        if 'sameAs' in item:
            for ref in item.get('sameAs'):
                if ID in ref:
                    same_as[ref[ID]] = item[ID]

    chip_keys = [ID, TYPE] + label_keys
    for other in db.values():
        chip = {k: v for k, v in other.items() if k in chip_keys}
        for link, refs in other.items():
            if link == 'sameAs':
                continue
            if not isinstance(refs, list):
                refs = [refs]
            for ref in refs:
                if isinstance(ref, dict) and ID in ref:
                    item = db.get(ref[ID])
                    if not item:
                        continue
                    item.setdefault(REV, {}).setdefault(link, []).append(chip)

    return db, same_as


if __name__ == '__main__':
    import doctest
    doctest.testmod()
