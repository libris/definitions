import csv
import json
import re
import sys
from urllib.parse import quote

KBV = "https://id.kb.se/vocab/"
# SKOS = "http://www.w3.org/2004/02/skos/core#"
SAB_BASE = "https://id.kb.se/term/kssb/{0}"
DDC_BASE = None  # "http://dewey.info/class/{0}/"
LANG = 'sv'

hint_link_map = {
    #'#H': SKOS+'closeMatch',
    #'#G': SKOS+'closeMatch',
    #'#M': inverseOf SKOS+'closeMatch',
    '#1': 'exactMatch',
    '#2': 'broadMatch',
    '#3': 'narrowMatch',
    '#4': 'closeMatch',
    'DDK22': 'relatedMatch',  # TODO
}


def create_data(ddc_map_fpath, sab_codes_fpath):
    rmap = {}
    if sab_codes_fpath:
        create_sab_skos_data(rmap, sab_codes_fpath)
    create_sab_ddc_data(rmap, ddc_map_fpath)
    return {
        "@context": {
            "@vocab": KBV,
            "@base": SAB_BASE.format(""),
            "prefLabel": {"@language": LANG},
        },
        "@graph": list(rmap.values()),
    }


def to_uri(base, code):
    slug = quote(code.encode('utf-8'), safe='')  # TODO: safe=':(),' (as in generated sab?)
    return base.format(slug)


def create_sab_skos_data(rmap, fpath):
    label_map = {}
    pending_broader = []

    for i, (code, label) in enumerate(read_csv_items(fpath)):
        uri = to_uri(SAB_BASE, code)
        r = rmap[uri] = {
            "@id": uri,
            "@type": "Concept",
            "notation": code,
            "prefLabel": label,
        }
        label_map[label] = uri
        if ': ' in label:
            pending_broader.append((r, label.rsplit(': ', 1)[0]))

    for r, broader_label in pending_broader:
        broader_uri = label_map.get(broader_label)
        if broader_uri:
            r.setdefault("broader", []).append({"@id": broader_uri})


def create_sab_ddc_data(rmap, fpath):
    for number, sab_code, ddc_code, hint in read_csv_items(
        fpath, skip_comment=True, size=4
    ):
        hint = re.split(r'\s+|\w(?=#)', hint)[-1].strip()
        link = hint_link_map.get(hint)
        if not link:
            print("No link map for", hint, file=sys.stderr)
            continue
        uri = to_uri("{}", sab_code)
        rmap.setdefault(uri, {"@id": uri}).setdefault(link, []).append(
            {
                "@id": to_uri(DDC_BASE, ddc_code)
            } if DDC_BASE else {
                "@type": "ClassificationDdc",
                "code": ddc_code
            }
        )


def read_csv_items(
    fpath,
    skip_first=True,
    skip_comment=False,
    csv_dialect='excel-tab',
    encoding='latin-1',
    size=0,
):
    with open(fpath, 'rt', encoding=encoding) as fp:
        reader = csv.reader(fp, csv_dialect)
        if skip_first is True:
            next(reader)
        for row in reader:
            if not row or skip_comment and row[0].startswith('#'):
                continue
            cols = [col.strip() for col in row]
            if size and len(cols) > size:
                cols = cols[0:size]
            yield cols


if __name__ == '__main__':
    args = sys.argv[1:]
    ddc_map_fpath = args.pop(0)
    sab_codes_fpath = args.pop(0) if args else None

    data = create_data(ddc_map_fpath, sab_codes_fpath)
    s = json.dumps(
        data, indent=2, separators=(',', ': '), sort_keys=True, ensure_ascii=False
    )
    print(s)
