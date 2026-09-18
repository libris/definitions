# This create Turtle data with all found precoordinated terms in Libris, by
# processing a SPARQL result of all uses. It then parses the SAB codes, to
# check if they can be constructed from known "atoms" (which are loaded first).
# It also lists all unknown components on stderr.
from urllib.parse import quote, unquote
import csv
import gzip
import re
import sys
from textwrap import dedent

from sabcodeparser import parse_sab_code


def attempt_lang_composite(part: str, parts: list[str]) -> bool:
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

    if altlang in sablangcodes:
        altcode = 'H' + altlang
        if altcode in sabcodes and part not in compositebases:

            lang_fromto = SPECIAL_LANG_CODES.get(hcode_transl_to_or_from_code)
            if lang_fromto:
                altcode_fromto = altcode + lang_fromto
                trailing =  f", <{qc(lang_fromto)}>"
            else:
                altcode_fromto = None
                trailing = ""

            print(dedent(f"""
            <{qc(part)}> a :Classification ;""" + (f"""
                :exactMatch <{qc(altcode_fromto)}> ;""" if altcode_fromto else "") + f"""
                :code "{part}" ;""" + (f'  # "{altcode_fromto}"^^:SABEduCode ;' if altcode_fromto else "") + f"""
                :broader <{hcode_transl_to_or_from_code}>, <{qc(altcode)}>{trailing} ;
                :inScheme </term/kssb> ."""))

            compositebases.add(part)
            parts.append(part)
        else:
            altlang = None

    if altlang:
        return True
    elif part == first and part.startswith("X"):
        combo = reconstruct_combo("X", part, sabcodes)
        if combo:
            parts += combo
            return True
    elif part == first and part.startswith("Y"):
        combo = reconstruct_combo("Y", part, sabcodes)
        if combo:
            parts += combo
            return True

    if part in compositebases:
        parts.append(part)
        return True
    else:
        return False


def reconstruct_combo(letter, part, sabcodes) -> tuple[str] | None:
    for i in range(len(first), 0, -1):
        base_part = first[:i]
        if base_part in sabcodes:
            combo_part = letter + first[i:]
            if combo_part in sabcodes:
                return base_part, combo_part
    return None


EXPECTED_SAB_SIZE = 7000
LONG_TAIL_MIN = 20

SPECIAL_LANG_CODES = {
    'Hce': '=c',
    'Hcc': None,
}

qc = lambda c: quote(c, safe='')

sabterms = sys.argv[1]

sabcodes: set[str] = set()
sablangcodes: set[str] = set()

with open(sabterms) as f:
    for l in f:
        for slug in re.findall('^<([^>]+)>', l):
            break
        else:
            continue

        code = unquote(slug)

        if '--' in code:
            continue

        if code.startswith('='):
            assert 'LanguageSubdivision' in l
            sablangcodes.add(code[1:])

        sabcodes.add(code)

assert len(sabcodes) > EXPECTED_SAB_SIZE

usagefpath = sys.argv[2]

compositebases: set[str] = set()


print("""\
prefix owl: <http://www.w3.org/2002/07/owl#>
prefix : <https://id.kb.se/vocab/>
base <https://id.kb.se/term/kssb/>""")

with gzip.open(usagefpath, "rt") as f:
    reader = csv.reader(f, 'excel-tab')  # type: ignore

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

        unknown = []

        first = None
        cleancode = ""
        parts = []

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

                if attempt_lang_composite(part, parts):
                    continue
                else:
                    unknown.append(part)
                    break
            else:
                parts.append(part)
        else:
            if len(parts) < 2 and (not parts or any(parts[0].startswith(code) for code in SPECIAL_LANG_CODES)):
                continue

            if 'z ' not in code and cleancode not in sabcodes:
                altcode = code.replace(' ', '')
                if cleancode != altcode:
                    sameas = f' owl:sameAs <{qc(altcode)}> ;'
                    altcode = f';  # "{code}"^^:SABAltCode '
                else:
                    sameas = ''
                    altcode = ''

                part_ref = ' '.join(f"<{qc(part)}>" for part in parts)
                print(dedent(f"""
                <{qc(cleancode)}> a :Classification ;{sameas}
                    :code "{cleancode}" {altcode};
                    :termComponentList ( {part_ref} ) ;
                    :inScheme </term/kssb> ."""))

        if unknown:
            print(code, "|".join(unknown), count, sample, sep='\t', file=sys.stderr)
