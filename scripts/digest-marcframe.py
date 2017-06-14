from __future__ import unicode_literals, print_function
try: str, bytes = unicode, str
except: pass
import json
from itertools import chain


def digest_marcframe(marcframe):
    print('    VALUES (?property ?class ?enumclass) {')
    digest_fixedfields(marcframe)
    print('    }')
    print()

    print('    VALUES (?property ?class ?enumclass) {')
    for part in ['patterns', 'bib', 'auth', 'hold']:
        digest_fields(marcframe, part)
    print('    }')


def digest_fixedfields(marcframe):

    def parse_fixed_by_section(part, tag):
        for basename, coldefs in marcframe[part][tag].items():
            if basename.startswith('TODO') or not basename[0].isupper():
                continue
            yield from _parse_coldefs(part, tag, coldefs, basename)

    def parse_fixed(part, tag):
        yield from _parse_coldefs(part, tag, marcframe[part][tag])

    def _parse_coldefs(part, tag, coldefs, basename=None):
        if isinstance(coldefs, str):
            return
        for col_key, col_dfn in coldefs.items():
            if not isinstance(col_dfn, dict):
                continue
            link = col_dfn.get('link') or col_dfn.get('addLink')
            tokenmap = col_dfn.get('tokenMap')
            if not link or not tokenmap:
                continue
            if col_key.startswith('['):
                bot, ceil = map(int, col_key[1:-1].split(':'))
                col_key = str(bot) if ceil == bot + 1 else '{}_{}'.format(bot, ceil - 1)

            marcsource = 'marc:{part}/{tag}/{col_key}'.format(**vars())
            yield (link, basename, tokenmap, marcsource)

    colprops = {}
    for link, basename, tokenmap, marcsource in chain(
            parse_fixed('bib', '000'),
            parse_fixed_by_section('bib', '006'),
            parse_fixed_by_section('bib', '007'),
            parse_fixed_by_section('bib', '008'),
            parse_fixed('auth', '000'),
            parse_fixed('hold', '000'),
            parse_fixed('hold', '008'),
            ):
        colprops.setdefault((link, basename, tokenmap), []).append(marcsource)

    prev = None
    for colprop in sorted(colprops):
        link, basename, tokenmap = colprop
        if prev and link != prev and not (':' in prev and ':' in link):
            print()
        prev = link
        if ':' not in link:
            link = ':' + link
        basename = ':' + basename if basename else 'UNDEF'
        marcsources = ', '.join(colprops[colprop])
        print("        ({link}\t{basename}\tmarc:{tokenmap}) # {marcsources}".format(**vars()))


def digest_fields(marcframe, part):
    defs = marcframe[part]
    for key, dfn in defs.items():
        if not key.isdigit():
            continue # TODO: parse patterns!
    #dfn.get('match')
    link = dfn.get('link') or dfn.get('addLink')
    prop = dfn.get('property') or dfn.get('addProperty')
    rtype = dfn.get('resourceType')
    domain = 'UNDEF'
    marcsources = ', '.join([]) # TODO
    print("        ({domain}\t{link}\t{rtype}) # {marcsources}".format(**vars()))


if __name__ == '__main__':
    import sys, os
    args = sys.argv[1:]
    source = args.pop(0) if args else '../whelk-core/src/main/resources/ext/marcframe.json'

    with open(source) as fp:
        marcframe = json.load(fp)

    digest_marcframe(marcframe)
