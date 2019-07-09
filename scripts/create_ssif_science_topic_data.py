# -*- coding: UTF-8 -*-
from __future__ import print_function, unicode_literals
import csv
import json
import sys


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
        label_sv = columns[-2]
        label_en = columns[-1]
        item = {
            '@id': code,
            '@type': 'Topic',
            'prefLabelByLang': {'sv': label_sv, 'en': label_en}
        }

        while tree and len(tree[-1]) >= len(code):
            tree.pop()

        if tree and code.startswith(tree[-1]):
            item['broader'] = {'@id': tree[-1]}

        if not tree or len(tree[-1]) < len(code):
            tree.append(code)

        items.append(item)

    return {
        "@context": {
          "@vocab": "https://id.kb.se/vocab/",
          "prefLabelByLang": {"@id": "prefLabel", "@container": "@language"},
          "@base": "https://id.kb.se/term/ssif/"
        },
        "@graph": items
    }


def read_csv_items(fpath, skip_first=True, skip_comment=False,
        csv_dialect='excel-tab', size=0):
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

    print(json.dumps(data, indent=2, ensure_ascii=False,
                     separators=(',', ': ')))
