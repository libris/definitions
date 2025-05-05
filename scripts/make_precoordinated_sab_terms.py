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

        code, count, sample = row

        # NOTE: skipping the long tail of usages less than...
        if count.isnumeric() and int(count) < 20:
            break

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

            if part.startswith('.'):
                assert first
                part = first[0] + part

            if part not in sabcodes:
                lit_transl_to_sv_code = 'Hce'
                if part.startswith(lit_transl_to_sv_code):
                    tolang = part.removeprefix(lit_transl_to_sv_code)
                    if tolang in sablangcodes:
                        altcode = 'H' + tolang
                        if altcode in sabcodes and part not in compositebases:
                            altcode_sv = f"{altcode}=c"
                            print(dedent(f"""
                            <{qc(part)}> a :Classification ;
                                :exactMatch <{qc(altcode_sv)}> ;
                                :code "{part}" ;  # "{altcode_sv}"^^:SABEduCode ;
                                :broader <Hce>, <{qc(altcode)}>, <{qc('=c')}> ;
                                :inScheme </term/kssb> ."""))
                            compositebases.add(part)
                            parts.append(part)
                            continue

                unknown.append(part)
                break
            else:
                parts.append(part)
        else:
            broader = ', '.join(f"<{qc(part)}>" for part in parts)
            if 'z ' not in code and cleancode not in sabcodes:
                altcode = code.replace(' ', '')
                if cleancode != altcode:
                    sameas = f' owl:sameAs <{qc(altcode)}> ;'
                    altcode = f';  # "{code}"^^:SABAltCode '
                else:
                    sameas = ''
                    altcode = ''

                print(dedent(f"""
                <{qc(cleancode)}> a :Classification ;{sameas}
                    :code "{cleancode}" {altcode};
                    :broader {broader} ;
                    :inScheme </term/kssb> ."""))

        if unknown:
            print(code, "|".join(unknown), count, f"<{sample}>", sep='\t', file=sys.stderr)
