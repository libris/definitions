# This create Turtle data with all found precoordinated terms in Libris, by
# processing a SPARQL result of all uses. It then parses the SAB codes, to
# check if they can be constructed from known "atoms" (which are loaded first).
# It also lists all unknown components on stderr.
from collections.abc import Iterator
from urllib.parse import quote, unquote
import csv
import gzip
import json
import re
import sys

from sabcodeparser import parse_sab_code


def qc(c: str) -> str:
    return quote(c, safe='')


MIN_EXPECTED_SAB_SIZE = 7000
LONG_TAIL_MIN = 20


def write_precoordinated_sab_terms(
    reader: Iterator[list[str]],
    sabcodes: set[str],
    sablangcodes: set[str],
    mapping_index: dict[str, dict]
) -> None:

    compositebases: set[str] = set()

    print(json.dumps({"@context": {
        "@vocab": "https://id.kb.se/vocab/",
        "@base": "https://id.kb.se/term/kssb/"
    }}))

    for i, row in enumerate(reader):
        if i == 0 and row == ("cls", "count", "sample"):
            continue

        code, versions, count, sample, maxyear = row

        # NOTE: skipping the long tail of usages less than...
        if count.isnumeric() and int(count) < LONG_TAIL_MIN:
            break

        if re.search(r'\\u[0-9A-F]{4}', code):
            code = code.encode().decode('unicode-escape')

        if code in sabcodes:
            continue

        # TODO: write json lines instead!
        description, unknown = create_sab_description(
            code, sabcodes, sablangcodes, compositebases
        )
        if description:
            if mapping := mapping_index.get(description['@id']):
                del mapping['@id']
                description |= mapping
            print(json.dumps(description))

        if unknown:
            print(code, "|".join(unknown), count, sample, sep='\t', file=sys.stderr)


def create_sab_description(
    code: str,
    sabcodes: set[str],
    sablangcodes: set[str],
    compositebases: set[str],
) -> tuple[dict | None, list]:
    first = None
    cleancode = ""
    parts: list[str] = []

    unknown = []

    # NOTE: Don't precoordinate uses of MediaSubdivision
    # (Already filtered in statistics query.)
    #if re.search(r'/[A-Z]+', code):
    #    continue

    for part in parse_sab_code(code):
        if not first:
            first = part

        if part.startswith('z '):
            continue

        cleancode += part

        if part.startswith(('.', '(')):
            assert first
            for i in range(len(first), 0, -1):
                controlled_part = first[:i] + part
                if controlled_part in sabcodes:
                    part = controlled_part
                    break

        if part not in sabcodes:
            lang_desc, success = attempt_lang_composite(
                first, part, parts, sabcodes, sablangcodes, compositebases
            )
            if success:
                if lang_desc:
                    print(json.dumps(lang_desc))
                continue
            else:
                unknown.append(part)
                break
        else:
            parts.append(part)
    else:
        if len(parts) < 2 and (not parts or any(parts[0].startswith(code) for code in SPECIAL_LANG_CODES)):
            return None, unknown

        if 'z ' not in code and cleancode not in sabcodes:
            altcode = code.replace(' ', '')
            if cleancode != altcode:
                extras = {
                    "sameAs": {"@id": qc(altcode)}
                    # "altCode": code
                }
            else:
                extras = {}

            part_refs = [{"@id": qc(part)} for part in parts]
            return {
                "@id": qc(cleancode),
                "@type": "Classification",
                "code": cleancode,
                "termComponentList": {"@list": part_refs},
                "inScheme": {"@id": "/term/kssb"}
            } | extras, unknown

    return None, unknown


SPECIAL_LANG_CODES = {
    'Hce': '=c',  # Utländsk skönlitteratur i svensk översättning
    'Hcc': None,  # Svensk skönlitteratur på främmande språk
}


def attempt_lang_composite(
    first: str,
    part: str,
    parts: list[str],
    sabcodes: set[str],
    sablangcodes: set[str],
    compositebases: set[str],
) -> tuple[dict | None, bool]:
    # TODO: Specify below rules with doctests:
    #  Examples:
    # - Heej => He + Hj
    # - Hccj => Hcc + Hj
    # - (Hsg)e(ma) => Hsg + Hma
    # - (Hcc)(uc) => Hcc + Huc
    for hcode_transl_to_or_from_code in SPECIAL_LANG_CODES:
        if part.startswith(hcode_transl_to_or_from_code):
            altlang = part.removeprefix(hcode_transl_to_or_from_code)
            break
    else:
        altlang = None
        hcode_transl_to_or_from_code = None
        if m := re.match(r'^(H[a-zåäö]*)e([a-zåäö]+)$', part):
            hcode_transl_to_or_from_code = m.group(1)
            altlang = m.group(2)

    description: dict | None = None

    if altlang in sablangcodes:
        altcode = 'H' + altlang
        if altcode in sabcodes and part not in compositebases:

            components = [
                {"@id": hcode_transl_to_or_from_code},
                {"@id": qc(altcode)},
            ]

            lang_fromto = SPECIAL_LANG_CODES.get(hcode_transl_to_or_from_code or "")
            if lang_fromto:
                altcode_fromto = altcode + lang_fromto
                #components.append({"@id": qc(lang_fromto)})
            else:
                altcode_fromto = None

            description = {
                "@id": qc(part),
                "@type": "Classification",
                "code": part, # "{altcode_fromto}"^^:SABEduCode
                "termComponentList": {"@list": components},
                "inScheme": {"@id": "/term/kssb"}
            }

            if altcode_fromto:
                description["exactMatch"] = {"@id": qc(altcode_fromto)}

            compositebases.add(part)
            parts.append(part)
        else:
            altlang = None

    if altlang:
        return description, True
    elif part == first and part.startswith("X"):
        combo = reconstruct_combo("X", first, part, sabcodes)
        if combo:
            parts += combo
            return description, True
    elif part == first and part.startswith("Y"):
        combo = reconstruct_combo("Y", first, part, sabcodes)
        if combo:
            parts += combo
            return description, True

    if part in compositebases:
        parts.append(part)
        return description, True
    else:
        return description, False


def reconstruct_combo(letter: str, first: str, part: str, sabcodes: set[str]) -> tuple[str, str] | None:
    for i in range(len(first), 0, -1):
        base_part = first[:i]
        if base_part in sabcodes:
            combo_part = letter + first[i:]
            if combo_part in sabcodes:
                return base_part, combo_part
    return None


def main() -> None:
    args = sys.argv[1:]

    usagefpath = args.pop(0)
    sabterms = args.pop(0)
    added_mappings = args.pop(0) if args else None

    sabcodes: set[str] = set()
    sablangcodes: set[str] = set()

    with open(sabterms) as f:
        sabdata = json.load(f)
        for term in sabdata['@graph']:
            code = term['code']
            ttype = term['@type']
            if ttype == 'TermCollection':
                continue
            if ttype == 'LanguageSubdivision':
                sablangcodes.add(code[1:])
            sabcodes.add(code)

    assert len(sabcodes) > MIN_EXPECTED_SAB_SIZE

    mapping_index = {}
    if added_mappings:
        with open(added_mappings) as f:
            mappings = json.load(f)
            if '@graph' in mappings:
                mapping_index = {
                    item['@id']: item
                    for item in mappings['@graph']
                    if '@id' in item
                }

    with gzip.open(usagefpath, "rt") as f:
        reader = csv.reader(f, 'excel-tab')  # type: ignore
        write_precoordinated_sab_terms(reader, sabcodes, sablangcodes, mapping_index)


if __name__ == '__main__':
    main()
