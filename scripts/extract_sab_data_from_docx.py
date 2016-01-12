from __future__ import unicode_literals, print_function
from zipfile import ZipFile
from lxml import etree


NS = {'w': "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

INDENT_MAP = {
    'Titel': '',
    'Rubrik1': '',
    'Rubrik2': ' ' * 4,
    'Rubrik3': ' ' * 8,
    'Rubrik4': ' ' * 12,
}

def get_doc(fpath, zpath='word/document.xml'):
    zfile = ZipFile(fpath)
    with zfile.open(zpath) as f:
        return etree.parse(f)

def extract_sab(doc):
    ns = dict(namespaces=NS)
    indent = ''
    for el in doc.xpath('//w:p', **ns):

        for style in el.xpath('w:pPr/w:pStyle/@w:val', **ns):
            break
        else:
            style = None

        next_indent = INDENT_MAP.get(style, indent)

        parts = []
        for el in el.xpath('w:r/w:t', **ns):
            parts.append(el.text)

        if not parts:
            continue

        if style == 'Rubrik1' \
                or (len(parts) > 1 and ' ' not in parts[0]):

            if next_indent != indent or style == 'Rubrik1':
                print()
            indent = next_indent

            print(indent, sep='', end='')
            if len(parts) > 1:
                parts[0] = '%s =' % parts[0]
                if len(parts) > 2:
                    for i in range(2, len(parts)):
                        parts[i] = '#( %s )' % parts[i]
            else:
                print("# ", end='')
            print(*[s.encode('utf-8') for s in parts], sep='\t')


if __name__ == '__main__':
    import sys
    args = sys.argv[:]
    script = args.pop(0)
    if not args:
        print("Usage: {} DOCX_FILE".format(script))

    fpath = args.pop(0)

    extract_sab(get_doc(fpath))
