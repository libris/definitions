"""
Convert RDA term lists in Box Notes to JSON-LD

1. Download all lists from a given Box folder (here "Värdevokabulär") as a ZIP file.
2. Run this script (pipe or redirect output as desired):
        $ python scripts/rdabox2jsonld.py cache/Värdevokabulär.zip

"""
from urllib.parse import quote
from zipfile import ZipFile
import json
import re
import sys


def convert(doc, rtype):
    items = []
    for block in doc['content']:
        if block['type'] == 'table':
            skipped_first_row = False
            for row in block['content']:
                if not skipped_first_row:
                    skipped_first_row = True
                    continue

                cells = row['content']

                if content := cells[0]['content'][0].get('content'):
                    label_en = content[0]['text']
                else:
                    continue

                ref = None
                if content := find_with_content(cells[0]['content'])[-1].get('content'):
                    for mark in content[0]['marks']:
                        ref = mark['attrs'].get('href')
                        if ref:
                            break

                definition_en = None
                if content := cells[1]['content'][0].get('content'):
                    definition_en = content[0]['text']

                label_sv = None
                if content := cells[2]['content'][0].get('content'):
                    label_sv = content[0].get('text')

                definition_sv = None
                if content := cells[3]['content'][0].get('content'):
                    definition_sv = content[0]['text']

                matches = []
                linkcells = set()
                for cell in cells[4:]:
                    for p in cell['content']:
                        if content := p.get('content'):
                            for block in [p] + content:
                                for mark in block.get('marks', []):
                                    if mark['type'] == 'link':
                                        matches.append({'@id': mark['attrs']['href']})
                                        linkcells.add(id(cell))

                notes = []
                for cell in cells[4:]:
                    if id(cell) in linkcells:
                        continue
                    for p in cell['content']:
                        if content := p.get('content'):
                            notes.append(clean(content[0]['text']))

                id_label = clean(label_en) or clean(label_sv)
                r_id = quote(id_label.title().replace(' ', ''))
                item = {
                    "@id": r_id,
                    "@type": rtype,
                    "prefLabel_en": clean(label_en),
                    "prefLabel_sv": clean(label_sv),
                    "definition_en": clean(definition_en),
                    "definition_sv": clean(definition_sv),
                    "exactMatch": {"@id": ref} if ref else None,
                    "closeMatch": matches,
                    "note": notes
                }
                items.append(item)

    return {item['@id']: item for item in items}


def find_with_content(items):
    return [item for item in items if 'content' in item]


def to_type(fname):
    fname = fname.rsplit('/')[-1].rsplit('.')[0]
    return re.sub(r'\W', '', fname.title().replace(' ', ''))


def clean(s):
    if s is None:
        return None

    s = s.replace(chr(160), ' ').strip()
    if not s:
        return None

    return s[0].upper() + s[1:]


def main():
    result_map = {}

    def convert_and_add_results(source, fname):
        if not (doc := source.get('doc')) or 'content' not in doc:
            return

        results = convert(doc, to_type(fname))
        for key, item in results.items():
            if dup := result_map.get(key):
                print(
                    '#',
                    f"Duplicate on {key}:",
                    dup['@type'],
                    "and",
                    item['@type'],
                    file=sys.stderr
                )
        result_map.update(results)

    for fname in sys.argv[1:]:
        if fname.endswith('.zip'):
            with ZipFile(fname) as zipfile:
                for zfname in zipfile.namelist():
                    with zipfile.open(zfname) as zf:
                        source = json.load(zf)
                    convert_and_add_results(source, zfname)
        else:
            with open(fname) as f:
                source = json.load(f)
            convert_and_add_results(source, fname)

    doc = {
        "@context": {
            "@vocab": "https://id.kb.se/vocab/",
            "@base": "https://id.kb.se/term/rda/",
            "prefLabel_sv": {"@id": "prefLabel", "@language": "sv"},
            "prefLabel_en": {"@id": "prefLabel", "@language": "en"},
            "definition_sv": {"@id": "definition", "@language": "sv"},
            "definition_en": {"@id": "definition", "@language": "en"}
        },
        "@graph": list(result_map.values())
    }

    print(json.dumps(doc, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
