from __future__ import unicode_literals, print_function
from zipfile import ZipFile
from lxml import etree

def get_doc(fpath, zpath='word/document.xml'):
    zfile = ZipFile(fpath)
    with zfile.open(zpath) as f:
        return etree.parse(f)

def extract_sab(doc):
    ns = dict(namespaces={
            'w': "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            })
    for el in doc.xpath('//w:p', **ns):
        parts = []
        for el in el.xpath('w:r/w:t', **ns):
            parts.append(el.text)
        if parts:
            if len(parts) > 1 and ' ' not in parts[0]:
                print(*[s.encode('utf-8') for s in parts])

if __name__ == '__main__':
    import sys
    args = sys.argv[:]
    script = args.pop(0)
    if not args:
        print("Usage: {} DOCX_FILE".format(script))
    fpath = args.pop(0)

    extract_sab(get_doc(fpath))
