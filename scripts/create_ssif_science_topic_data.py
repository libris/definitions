# -*- coding: UTF-8 -*-
import csv
import json
import re
import sys
from urllib.parse import urljoin

SCHEME = "https://id.kb.se/term/ssif"
BASE = f"{SCHEME}/"


def create_data(fpath):
    items = []
    tree = []
    for columns in read_csv_items(fpath):
        for col in columns:
            if col.strip().isdigit():
                code = str(col)
                break
        else:
            continue

        label_sv, altlabel_sv, comment_sv = _parse_value(columns[-2])
        label_en, altlabel_en, comment_en = _parse_value(columns[-1])

        item = {
            '@id': _iri(code),
            '@type': 'Classification',
            'inScheme': {'@id': SCHEME},
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

        if not tree or len(tree[-1]) < len(code):
            tree.append(code)

        items.append(item)

    return {
        "@context": {
            "@vocab": "https://id.kb.se/vocab/",
            "prefLabelByLang": {"@id": "prefLabel", "@container": "@language"},
            "altLabelByLang": {"@id": "altLabel", "@container": "@language"},
            "commentByLang": {"@id": "comment", "@container": "@language"},
        },
        "@graph": items,
    }


def _iri(code: str) -> str:
    return urljoin(BASE, code)


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
