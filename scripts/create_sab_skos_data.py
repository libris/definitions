# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
import csv
import json
import re
import sys
import urllib


SKOS = "http://www.w3.org/2004/02/skos/core#"
SAB_BASE = "https://id.kb.se/def/scheme/sab/{0}"
DDC_BASE = "http://dewey.info/class/{0}/"
LANG = 'sv'

hint_link_map = {
    #'#H': SKOS+'closeMatch',
    #'#G': SKOS+'closeMatch',
    #'#M': inverseOf SKOS+'closeMatch',
    '#1': SKOS+'exactMatch',
    '#2': SKOS+'broadMatch',
    '#3': SKOS+'narrowMatch',
    '#4': SKOS+'closeMatch',
    'DDK22': SKOS+'relatedMatch', # TODO
}

def create_data(sab_codes_fpath, ddc_map_fpath, limit):
    rmap = {}
    create_sab_skos_data(rmap, sab_codes_fpath, limit=limit)
    create_sab_ddc_data(rmap, ddc_map_fpath)
    return {
        "@context": {
            "@vocab": SKOS,
            "prefLabel": {"@language": LANG}
        },
        "@graph": rmap.values()
    }

def to_uri(base, code):
    slug = urllib.quote(code.encode('utf-8'), safe=b':(),')
    return base.format(slug)

def create_sab_skos_data(rmap, fpath, limit=0):
    label_map = {}
    pending_broader = []

    for i, (code, label) in enumerate(read_csv_items(fpath)):
        uri = to_uri(SAB_BASE, code)
        r = rmap[uri] = {
            "@id": uri,
            "@type": "Concept",
            "notation": code,
            "prefLabel": label
        }
        label_map[label] = uri
        if ': ' in label:
            pending_broader.append((r, label.rsplit(': ', 1)[0]))
        if limit and i > limit:
            break

    for r, broader_label in pending_broader:
        broader_uri = label_map.get(broader_label)
        if broader_uri:
            r.setdefault("broader", []).append({"@id": broader_uri})

def create_sab_ddc_data(rmap, fpath):
    for number, sab_code, ddc_code, hint in read_csv_items(
            fpath, skip_comment=True, coding='utf-8', size=4):
        hint = re.split(r'\s+|\w(?=#)', hint)[-1].strip()
        link = hint_link_map.get(hint)
        if not link:
            print >> sys.stderr, "No link map for", hint.encode('utf-8')
            continue
        uri = to_uri(SAB_BASE, sab_code)
        rmap.setdefault(uri, {"@id": uri}).setdefault(link, []).append(
                {"@id": to_uri(DDC_BASE, ddc_code)})

def read_csv_items(fpath, skip_first=True, skip_comment=False,
        csv_dialect='excel-tab', coding='latin-1', size=0):
    with open(fpath, 'rb') as fp:
        reader = csv.reader(fp, csv_dialect)
        if skip_first is True:
            reader.next()
        for row in reader:
            if not row or skip_comment and row[0].startswith(b'#'):
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

    data = create_data(sab_codes_fpath, ddc_map_fpath, limit)
    print json.dumps(data,
            indent=2, separators=(',', ': '), sort_keys=True, ensure_ascii=False
            ).encode('utf-8')
