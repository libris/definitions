# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
import csv
import re
import sys
from rdflib import *
from rdflib.namespace import SKOS
import urllib


SAB = Namespace("http://id.kb.se/def/scheme/sab/")
DDC = Namespace("http://dewey.info/class/")
LANG = 'sv'

hint_link_map = {
    #'#H': SKOS.closeMatch,
    #'#G': SKOS.closeMatch,
    #'#M': ~SKOS.closeMatch,
    '#1': SKOS.exactMatch,
    '#2': SKOS.broadMatch,
    '#3': SKOS.narrowMatch,
    '#4': SKOS.closeMatch,
    'DDK22': SKOS.relatedMatch, # TODO
}

def to_uri(scheme, code):
    return scheme[urllib.quote(code.encode('utf-8'), safe=b':(),')]


def create_sab_skos_data(graph, fpath, limit=0):
    label_map = {}
    pending_broader = []

    for i, (code, label) in enumerate(read_csv_items(fpath)):
        uri = to_uri(SAB, code)
        r = graph.resource(uri)
        r.add(RDF.type, SKOS.Concept)
        r.add(SKOS.notation, Literal(code))
        r.add(SKOS.prefLabel, Literal(label, lang=LANG))
        label_map[label] = uri
        if ': ' in label:
            pending_broader.append((r, label.rsplit(': ', 1)[0]))
        if limit and i > limit:
            break

    for r, broader_label in pending_broader:
        broader_uri = label_map.get(broader_label)
        if broader_uri:
            r.add(SKOS.broader, broader_uri)


def create_sab_ddc_data(graph, fpath, limit=0):
    for number, sab_code, ddc_code, hint in read_csv_items(
            fpath, skip_comment=True, coding='utf-8', size=4):
        hint = re.split(r'\s+|\w(?=#)', hint)[-1].strip()
        link = hint_link_map.get(hint)
        if not link:
            print >> sys.stderr, "No link map for", hint.encode('utf-8')
            continue
        r = graph.resource(to_uri(SAB, sab_code))
        r.add(link, to_uri(DDC, ddc_code))


def read_csv_items(fpath, skip_first=True, skip_comment=False,
        csv_dialect='excel-tab', coding='latin-1', size=0):
    with open(fpath, 'rb') as fp:
        reader = csv.reader(fp, csv_dialect)
        if skip_first is True:
            reader.next()
        for row in reader:
            if not row or skip_comment and row[0][0] == '#':
                continue
            cols = [col.strip().decode(coding) for col in row]
            if size and len(cols) > size:
                cols = cols[0:size]
            yield cols


if __name__ == '__main__':
    args = sys.argv[1:]
    sab_codes_fpath = args.pop(0)
    ddc_map_fpath = args.pop(0)
    limit = int(args.pop(0)) if args else 0

    graph = Graph()
    graph.namespace_manager.bind('skos', SKOS)
    create_sab_skos_data(graph, sab_codes_fpath, limit=limit)
    create_sab_ddc_data(graph, ddc_map_fpath, limit=limit)
    graph.serialize(sys.stdout, format='turtle')
