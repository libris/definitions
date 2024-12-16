import re
import sys

# Note: sync with ../../librisxl/whelktool/scripts/2024/sab/main.groovy


def parse_sab_code(code):
    # TODO: starts with any r'[a-z]+'?
    if code.startswith('u'):
        code = code[1:] + ',u'

    chunks = [''] + re.split(r'(z.*|\(\w+\)|[,/=:.-])', code)
    it = iter(chunks)
    for a, b in zip(it, it):
        yield a.strip() + b.strip()


if __name__ == '__main__':

    TEST = '''
    Aabr(p)
    Aabs-c:b(p)
    Hc.02(s),u
    Hc. 02 (s), u
    He.01=c
    Niz
    G.096z Sociologi
    Hc.02(s),uz Is this valid?
    0cc.001,u.06z Centerpartiet (Kronobergs län)
    Aalz Leiserson, William Morris
    Fsgzf
    Gdcazf
    Emze
    Gfzf
    Qafbag-c(p)
    uHc
    uHce
    '''

    if '-t' in sys.argv[1:]:
        for code in (c for x in TEST.split('\n') if (c := x.strip())):
            print(code)
            parts = parse_sab_code(code)
            print(*parts, sep='\t')
            print()
        exit()

    incodes = (
        row.split('\t')[0] for line in sys.stdin if (row := line.strip())
    )
    if '-u' in sys.argv[1:]:
        codes = set()
        for code in incodes:
            for part in parse_sab_code(code):
                codes.add(part)
        for code in sorted(codes):
            print(code)
    else:
        for code in incodes:
            print(code, list(parse_sab_code(code)))
