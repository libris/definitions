# -*- coding: UTF-8 -*-
import csv
import json
import re
import sys
from collections import namedtuple
from difflib import SequenceMatcher
from urllib.parse import urljoin

KB_SCHEME = "https://id.kb.se/term/ssif"
UKA_SCHEME = "https://begrepp.uka.se/SSIF"
SKOS_IRI = "http://www.w3.org/2004/02/skos/core#"
KBV_IRI = "https://id.kb.se/vocab/"


Row = namedtuple(
    "Row",
    "code_2025, label_2025, label_en, code_2011, label_2011, change_type, comment, on_removal_see",
)


SHARED_CONTEXT = {
    "prefLabelByLang": {"@id": "prefLabel", "@container": "@language"},
    "altLabelByLang": {"@id": "altLabel", "@container": "@language"},
    "commentByLang": {"@id": "comment", "@container": "@language"},
    "hiddenLabelByLang": {"@id": "hiddenLabel", "@container": "@language"},
    "scopeNoteByLang": {"@id": "scopeNote", "@container": "@language"},
    "historyNoteByLang": {"@id": "historyNote", "@container": "@language"},
}


def create_data(fpath: str, simple_skos=True, use_annots=True) -> dict:
    item_map: dict = {}
    tree: list = []

    scheme_2025 = '2025' in fpath

    if simple_skos and scheme_2025:
        concept_scheme = UKA_SCHEME
        term_type = "Concept"
        context = SHARED_CONTEXT | {
            "@vocab": SKOS_IRI,
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "dct": "http://purl.org/dc/terms/",
            "ratio": "rdf:value",
            "commentByLang": {"@id": "dct:comment", "@container": "@language"},
            "isReplacedBy": "dct:isReplacedBy",
        }
    elif scheme_2025:
        concept_scheme = UKA_SCHEME
        term_type = "Classification"
        context = SHARED_CONTEXT | {"@vocab": KBV_IRI}
    else:
        concept_scheme = KB_SCHEME
        term_type = "Classification"
        context = SHARED_CONTEXT | {"@vocab": KBV_IRI}

    collect_included = False

    last_item = None

    def add_item(item):
        nonlocal last_item
        item_id = item["@id"]
        if item_id in item_map:
            given = item_map[item_id]
            given_rel = given["isReplacedBy"]
            related = item.setdefault("related", [])
            related += given_rel
        item_map[item_id] = item
        last_item = item

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
            row = Row(code, columns[-2], columns[-1], *(None,) * 5)
        else:
            row = Row(*columns)

        if 'här ingår:' in row.label_2025.strip().lower():
            collect_included = True
            continue

        code = row.code_2025

        on_removal_see_links = [
            {"@id": _iri(othercode)}
            for see in row.on_removal_see.split(',')
            if (othercode := see.strip())
        ]

        if not code or not code.isdigit():
            if collect_included:
                assert last_item
                narrower: dict = {"@type": "Concept"}
                preflabel = {lang: value
                    for lang, value in [
                        ("sv", row.label_2025),
                        ("en", row.label_en),
                    ] if value
                }

                hiddenlabel = {"sv": row.label_2011} if row.label_2011 else None
                if preflabel:
                    narrower["prefLabelByLang"] = preflabel
                if hiddenlabel:
                    narrower["hiddenLabelByLang"] = hiddenlabel
                if preflabel or hiddenlabel:
                    last_item.setdefault('narrower', []).append(narrower)

            if row.on_removal_see:
                add_item(
                    {
                        "@id": _iri(row.code_2011),
                        "@type": term_type,
                        "code": row.code_2011,
                        "hiddenLabel": row.label_2011,
                        "isReplacedBy": on_removal_see_links,
                    }
                )

            continue

        collect_included = False

        label_sv, altlabel_sv, comment_sv = _parse_value(row.label_2025)
        label_en, altlabel_en, comment_en = _parse_value(row.label_en)

        item_id = _iri(code)
        item: dict = {
            '@id': item_id,
            '@type': term_type,
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
                bylang: dict = item.setdefault(prop, {})
                bylang[lang] = value

        while tree and len(tree[-1]) >= len(code):
            tree.pop()

        if tree and code.startswith(tree[-1]):
            item['broader'] = {'@id': _iri(tree[-1])}

        if row.change_type:
            handled = False
            annot = (
                {"@annotation": {"commentByLang": {"sv": row.change_type}}}
                if use_annots
                else {}
            )

            if row.change_type in {"Ny kod", "Bytt forskningsämnesgrupp"}:
                handled = True
                add_item(
                    {
                        "@id": _iri(row.code_2011),
                        "@type": term_type,
                        "code": row.code_2011,
                        "hiddenLabelByLang": {"sv": row.label_2011},
                        "isReplacedBy": [{"@id": item_id, **annot}],
                    }
                )

            if row.change_type == "Sammanslagning av ämnen":
                # TODO: find those isReplacedBy this, and annotate that with this change.
                handled = False

            if row.change_type in {
                "Bytt forskningsämnesgrupp, Uppdelning av ämne",
                "Uppdelning av ämne",
                "Uppdelning av ämne, bytt forskningsämnesgrupp",
            }:
                handled = True
                replaced_id = _iri(row.code_2011)
                if replaced_id not in item_map:
                    add_item(
                        {
                            "@id": replaced_id,
                            "@type": term_type,
                            "code": row.code_2011,
                            "hiddenLabelByLang": {"sv": row.label_2011},
                            "isReplacedBy": [],
                        }
                    )
                replacements: list[dict] = item_map[replaced_id]["isReplacedBy"]

                # Use explicit replacements if given, otherwise use current item.
                if on_removal_see_links and not any(
                    ref["@id"] == item_id for ref in on_removal_see_links
                ):
                    replacements += [
                        ref for ref in on_removal_see_links if ref["@id"] != replaced_id
                    ]
                else:
                    replacements.append({"@id": item_id})

                for repl in replacements:
                    if "@annotation" not in repl:
                        repl.update(annot)

            if row.label_2011 and row.label_2011 != label_sv:
                if not handled:
                    assert row.change_type in {
                        "Annan",
                        "Bytt benämning",
                        "Sammanslagning av ämnen",
                    }, row
                    item["hiddenLabelByLang"] = {"sv": row.label_2011}
            elif not handled:
                assert row.change_type in {
                    "Annan",
                    "Nytt ämne",
                    "Sammanslagning av ämnen",
                }, row.change_type

            # TODO: also historyNoteByLang (reify with date; same as isReplacedBy annot)
            item["scopeNoteByLang"] = {"sv": row.change_type}

        if row.comment:
            item["historyNoteByLang"] = {"sv": row.comment}

        if not tree or len(tree[-1]) < len(code):
            tree.append(code)

        add_item(item)

    for item in item_map.values():
        _add_replacement_matches(item, item_map, use_annots)

    return {
        "@context": context,
        "@graph": list(item_map.values()),
    }


def _add_replacement_matches(
    item: dict, item_map: dict[str, dict], use_annots=False
) -> None:
    if 'hiddenLabelByLang' not in item:
        return

    closematches: list[dict] = []
    narrowmatches: list[dict] = []

    item_label_sv = item['hiddenLabelByLang']['sv']
    for repl_ref in item.get('isReplacedBy', []):
        repl = item_map[repl_ref["@id"]]
        if not item['code'].startswith(repl['broader']["@id"].rsplit('/', 1)[-1]):
            continue

        repl_label_sv = repl['prefLabelByLang']['sv']
        ratio = likeness_ratio(item_label_sv, repl_label_sv)
        if 0 < ratio < 1:
            ref = {"@id": repl["@id"]}
            if use_annots:
                ref["@annotation"] = {"ratio": ratio}
            (closematches if ratio > 0.8 else narrowmatches).append(ref)

    if closematches:
        item['closeMatch'] = closematches
    if narrowmatches:
        item['narrowMatch'] = narrowmatches


def likeness_ratio(a: str, b: str) -> float:
    sm = SequenceMatcher(None, a, b)
    return sm.ratio()


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
    import argparse

    argp = argparse.ArgumentParser()
    argp.add_argument('-s', '--skos', action='store_true', default=False)
    argp.add_argument('-a', '--annotations', action='store_true', default=False)
    argp.add_argument('fpath', metavar='FILE_PATH')
    args = argp.parse_args()

    data = create_data(args.fpath, args.skos, args.annotations)

    s = json.dumps(data, indent=2, ensure_ascii=False, separators=(',', ': '))
    s = re.sub(r'{\s+(\S+: "[^"]*")\s+}', r'{\1}', s)
    print(s)
