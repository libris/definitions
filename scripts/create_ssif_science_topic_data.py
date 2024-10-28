# -*- coding: UTF-8 -*-
import csv
import json
import re
import sys
from collections import namedtuple
from urllib.parse import urljoin

KB_SCHEME = "https://id.kb.se/term/ssif"
UKA_SCHEME = "https://begrepp.uka.se/SSIF"


Row = namedtuple("Row", "code_2025, label_2025, label_en, code_2011, label_2011, change_type, comment, on_removal_see")


def create_data(fpath):
    items = []
    tree = []

    scheme_2025 = '2025' in fpath
    concept_scheme =  UKA_SCHEME if scheme_2025 else KB_SCHEME

    collect_included = False

    def _iri(code: str) -> str:
        return urljoin(f"{concept_scheme}/", code)

    for columns in read_csv_items(fpath):
        if not scheme_2025:
            for col in columns:
                if col.strip().isdigit():
                    code = str(col)
                    break
            else:
                continue
            row = Row(code, columns[-2], columns[-1], *(None,)*5)
        else:
            row = Row(*columns)

        if 'här ingår:' in row.label_2025.strip().lower():
            collect_included = True
            continue

        code = row.code_2025

        if not code or not code.isdigit():
            if collect_included:
                narrower = items[-1].setdefault('narrower', [])
                narrower.append(
                    {
                        "@type": "Concept",
                        "prefLabelByLang": {"sv": row.label_2025, "en": row.label_en}
                    }
                )

            if row.on_removal_see:
                item = {
                    "@id": _iri(row.code_2011),
                    "@type": "Classification",
                    "code": row.code_2011,
                    "label": row.label_2011,
                }
                items.append(item)
                item['isReplacedBy'] = [
                    {"@id": _iri(othercode.strip())}
                    for othercode in row.on_removal_see.split(',')
                ]

            continue

        collect_included = False

        label_sv, altlabel_sv, comment_sv = _parse_value(row.label_2025)
        label_en, altlabel_en, comment_en = _parse_value(row.label_en)

        item = {
            '@id': _iri(code),
            '@type': 'Classification',
            'inScheme': {'@id': concept_scheme},
            'code': code,
            'prefLabelByLang': {'sv': label_sv, 'en': label_en},
        }

        for prop, value, lang in [
            ('altLabelByLang', altlabel_sv, 'sv'),
            ('commentByLang', comment_sv, 'sv'),
            ('altLabelByLang', altlabel_en, 'en'),
            ('commentByLang', comment_en, 'en'),
        ]:
            if value:
                bylang = item.setdefault(prop, {})
                bylang[lang] = value

        while tree and len(tree[-1]) >= len(code):
            tree.pop()

        if tree and code.startswith(tree[-1]):
            item['broader'] = {'@id': _iri(tree[-1])}

        if row.change_type:
            #"Nytt ämne"
            #"Ny kod"
            #"Bytt benämning"
            ##
            #"Sammanslagning av ämnen"
            #"Uppdelning av ämne"
            #"Bytt forskningsämnesgrupp"
            #"Uppdelning av ämne, bytt forskningsämnesgrupp"
            #"Bytt forskningsämnesgrupp, Uppdelning av ämne"
            #"Annan"

            if row.label_2011 and row.label_2011  != label_sv:
                item['hiddenLabelByLang'] = {"sv": row.label_2011}

            item['scopeNoteByLang'] = {"sv": row.change_type}

        if row.comment:
            item['historyNoteByLang'] = {"sv": row.comment}

        if not tree or len(tree[-1]) < len(code):
            tree.append(code)

        items.append(item)

    return {
        "@context": {
            "@vocab": "https://id.kb.se/vocab/",
            "prefLabelByLang": {"@id": "prefLabel", "@container": "@language"},
            "altLabelByLang": {"@id": "altLabel", "@container": "@language"},
            "commentByLang": {"@id": "comment", "@container": "@language"},
            "hiddenLabelByLang": {"@id": "hiddenLabel", "@container": "@language"},
            "scopeNoteByLang": {"@id": "scopeNote", "@container": "@language"},
            "historyNoteByLang": {"@id": "historyNote", "@container": "@language"},
        },
        "@graph": items,
    }


def _parse_value(s: str) -> tuple[str, str | None, str | None]:
    s = s.replace('\xa0', ' ')

    if '(' not in s:
        return s, None, None

    label, rest = s.split('(', 1)
    label = label.strip()
    altlabel: str | None = ''
    comment: str | None = ''

    if ') (' in rest:
        altlabel, comment = rest.split(') (', 1)
        altlabel = altlabel.strip()
        comment = comment.strip()
        if comment.endswith(')'):
            comment = comment[:-1]
    else:
        altlabel = rest
        if altlabel.endswith(')'):
            altlabel = altlabel[:-1]

    if ' ' in altlabel:
        parts = [p for p in altlabel.split(' ') if p.strip()]
        if len(parts) > 2 or not parts[0].islower() and parts[1].islower():
            altlabel, comment = None, altlabel

    return label, altlabel or None, comment or None


def read_csv_items(
    fpath, skip_first=True, skip_comment=False, csv_dialect='excel-tab', size=0
):
    with open(fpath, 'rt') as fp:
        reader = csv.reader(fp, csv_dialect)
        if skip_first is True:
            next(reader)
        for row in reader:
            if not row or skip_comment and row[0].startswith(b'#'):
                continue
            cols = [col.strip() for col in row]
            if size and len(cols) > size:
                cols = cols[0:size]
            yield cols


if __name__ == '__main__':
    args = sys.argv[1:]
    fpath = args.pop(0)

    data = create_data(fpath)

    s = json.dumps(data, indent=2, ensure_ascii=False, separators=(',', ': '))
    s = re.sub(r'{\s+(\S+: "[^"]*")\s+}', r'{\1}', s)
    print(s)
