# -*- coding: UTF-8 -*-
from __future__ import unicode_literals, print_function, division
__metaclass__ = type

from collections import OrderedDict
import re
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

HEADING_MAP = {
    'HUVUDTABELL': 'MAIN',
    'Sammandrag': 'MAIN',
    'HJÄLPTABELLER': 'HELP',
    'APPENDIX': None,
    'LOKAL UTBYGGNAD': None
}


class TableHandler:

    def __init__(self):
        self.maintable = []
        self.helptable = []
        self._index = {}
        self._stack = [{'code': '', 'narrower': self.maintable}]

    def handle_row(self, section, level, parts):
        if section == 'MAIN':
            self.handle_main_row(level, parts)
        elif section == 'HELP':
            self.handle_help_row(level, parts)

    def handle_main_row(self, level, parts):
        node = self._make_node(parts)

        code = node['code']
        current = self._stack[-1]

        if node['@type'] == 'Element':
            current.setdefault('element', []).append(node)
            return
        elif not level and not len(code) == 1:
            return

        if len(code) > len(current['code']):
            if code.startswith(current['code']):
                current.setdefault('narrower', []).append(node)
                self._stack.append(node)
        else:
            while len(self._stack) > 1:
                self._stack.pop()
                current = self._stack[-1]
                if code.startswith(current['code']):
                    break

            self._stack[-1].setdefault('narrower', []).append(node)
            if len(code) < len(current['code']):
                self._stack[-1] = node
            else:
                self._stack.append(node)

    def handle_help_row(self, level, parts):
        # 1. else skip
        # A. GeographicElement
        # B. ContentGenreElement
        # C. TemporalElement
        # D. MonographicElemet
        # E. ContentFormElement
        # F. LanguageElement
        # G. MediaElement if startswith('/'); AudienceElement if startswith(',')
        # H. 
        pass

    def get_results(self):
        return self.maintable + self.helptable

    def _make_node(self, parts):
        code = parts[0]
        label = parts[1]

        is_collection = '--' in code
        is_element = not code[0].isalpha()

        node = None # TODO: USE self._index.get(code) OR merge in final step
        if not node:
            node = OrderedDict()
            if code[0].isalpha():
                self._index[code] = node
        else:
            assert node['label'] == label, "%r != %r" % (
                    (node['code'], node['label']), (code, label))

        current = self._stack[-1]

        if is_collection:
            node['@type'] = 'Collection'
        elif is_element:
            node['@type'] = 'Element'
        else:
            node['@type'] = 'Classification'
        node['@id'] = current['@id'] + code if is_element else "sab:%s" % code
        node['code'] = code
        node['label'] = label

        if len(parts) > 2:
            node['comment'] = parts[2]

        return node


def error_correct(parts):
    if parts[0] == 'z':
        return
    if parts[0] == 'Macao':
        return
    if parts[0:2] == ['D', 'Filosofi: allmänt']:
        return
    if parts[0:2] == ['H', 'Skönlitteratur: samlingar']:
        return
    if parts[0:2] == ['N', 'Geografi']:
        return
    if parts[0] == 'Hit' and parts[1].startswith(' '):
        return
    if parts[0] == 'Hi' and not parts[1].startswith('Italiensk'):
        return
    if parts[0] in 'Ele' and parts[1].startswith('ctro '):
        return
    if parts[0] in 'Elec' and parts[1].startswith('tro '):
        return
    if parts[0] == 'Ex' and parts[1].startswith(': '):
        return
    if parts[0] == 'Xxa' and parts[1].startswith(' används inte'):
        return
    if parts[1].startswith(' kan'):
        return
    if parts[0] == 'I' and parts[1] in ['nternet', 'nteractive whiteboards']:
        return

    if parts[0] == ':' and re.match(r'^[a-z]+$', parts[1]):
        return [parts[0] + parts[1]] + parts[2:]

    if parts[1] == '--':
        first, rest = parts[2].split(' ', 1)
        return [parts[0] + parts[1] + first, rest] + parts[3:]

    if parts[0:2] == ['Ib.23', 'Ib.26']:
        return ['%s--%s' % (parts[0], parts[1]), parts[2]]

    if parts[0:2] == ['K.23', 'K.26']:
        return ['%s--%s' % (parts[0], parts[1]), parts[2]]

    if parts[0:2] == ['Uh', 'e'] and parts[2].startswith(('f ', 'g ')):
        return [parts[0] + parts[1] + parts[2][0], parts[2][2:]]

    if re.match(r'[A-Z][a-z]*$', parts[0]) and \
            re.match(r'[a-z][a-z0-9.]*$', parts[1]):
        return [parts[0] + parts[1], parts[2]]

    if re.match(r'^[a-z]+--\w+$', parts[1]):
        return [parts[0] + parts[1] + parts[2][0], parts[2][1:]]

    return parts


def get_doc(fpath, zpath='word/document.xml'):
    zfile = ZipFile(fpath)
    with zfile.open(zpath) as f:
        return etree.parse(f)


def extract_sab(doc, debug=False):
    ns = dict(namespaces=NS)
    indent = ''

    thandler = TableHandler()

    in_section = None

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

        if not (style == 'Rubrik1'
                or (len(parts) > 1 and ' ' not in parts[0])):
            continue

        if debug and (next_indent != indent or style == 'Rubrik1'):
            print()
        indent = next_indent

        if len(parts) == 1:
            assert not indent
            in_section = HEADING_MAP.get(parts[0], in_section)
            if debug:
                print("#", parts[0].encode('utf-8'))
        else:
            if len(parts) > 2:
                parts[2] = ' '.join(parts[2:])
                del parts[3:]

            try:
                parts = error_correct(parts)
            except IndexError:
                pass
            if not parts:
                continue

            thandler.handle_row(in_section, indent, parts)

            if debug:
                print(indent, sep='', end='')
                print(('%s =' % parts[0]).encode('utf-8'),
                        *[s.encode('utf-8') for s in parts[1:]],
                        sep='\t')

    return thandler.get_results()


if __name__ == '__main__':
    import sys
    args = sys.argv[:]
    script = args.pop(0)
    if not args:
        print("Usage: {} DOCX_FILE".format(script))

    debug = False
    if '-d' in args:
        args.remove('-d')
        debug = True

    fpath = args.pop(0)

    results = extract_sab(get_doc(fpath), debug=debug)
    import json
    print(json.dumps(results, indent=2, ensure_ascii=False).encode('utf-8'))
