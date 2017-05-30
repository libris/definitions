import json
from itertools import chain


def digest_marcframe(marcframe):
    digest_fixedfields(marcframe)
    for part in ['patterns', 'bib', 'auth', 'hold']:
        pass


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
            prop = col_dfn.get('link') or col_dfn.get('addLink')
            tokenmap = col_dfn.get('tokenMap')
            if not prop or not tokenmap:
                continue
            if col_key.startswith('['):
                bot, ceil = map(int, col_key[1:-1].split(':'))
                col_key = str(bot) if ceil == bot + 1 else '{}_{}'.format(bot, ceil - 1)

            marcsource = 'marc:{part}/{tag}/{col_key}'.format(**vars())
            yield (prop, basename, tokenmap, marcsource)

    colprops = {}
    for prop, basename, tokenmap, marcsource in chain(
            parse_fixed('bib', '000'),
            parse_fixed_by_section('bib', '006'),
            parse_fixed_by_section('bib', '007'),
            parse_fixed_by_section('bib', '008'),
            parse_fixed('auth', '000'),
            parse_fixed('hold', '000'),
            parse_fixed('hold', '008'),
            ):
        colprops.setdefault((prop, basename, tokenmap), []).append(marcsource)

    prev = None
    for colprop in sorted(colprops):
        prop, basename, tokenmap = colprop
        if prev and prop != prev and not (':' in prev and ':' in prop):
            print()
        prev = prop
        if ':' not in prop:
            prop = ':' + prop
        basename = ':' + basename if basename else 'UNDEF'
        marcsources = ', '.join(colprops[colprop])
        print("        ({prop}\t{basename}\tmarc:{tokenmap}) # {marcsources}".format(**vars()))


if __name__ == '__main__':
    import sys, os
    args = sys.argv[1:]
    source = args.pop(0) if args else '../whelk-core/src/main/resources/ext/marcframe.json'

    with open(source) as fp:
        marcframe = json.load(fp)

    digest_marcframe(marcframe)
