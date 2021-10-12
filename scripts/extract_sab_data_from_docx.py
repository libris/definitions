# -*- coding: UTF-8 -*-
import sys

from collections import OrderedDict
import re
from zipfile import ZipFile
import json
from lxml import etree
from urllib.parse import quote


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
        self._current_coll = None

    def handle_row(self, section, level, parts):
        if section == 'MAIN':
            self.handle_main_row(level, parts)
        elif section == 'HELP':
            self.handle_help_row(level, parts)

    def handle_main_row(self, level, parts):
        current = self._stack[-1]
        node = self._make_node(parts, current=current)
        code = node['code']

        if node['@type'].endswith('Element'):
            current.setdefault('element', []).append(node)
            return
        elif not level and not len(code) == 1:
            return

        if node['@type'].endswith('Collection'):
            self._current_coll = [ node['@id'] ] + code.split('--')
            # NOTE: we "incorrectly" link the collection to the parent
            # classification, instead of:
            #return
        elif self._current_coll:
            # FIXME: _current_coll needs to be like _stack ...
            coll_id, coll_start, coll_end = self._current_coll
            if (len(code) == len(coll_start) and
                    code >= coll_start and code <= coll_end):
                node['inCollection'] = {'@id': coll_id}

        if len(code) > len(current['code']):
            # "Deeper" Collection nodes got lost otherwise (see FIXME though)
            if node['@type'].endswith('Collection'):
                self.helptable.append(node)
            elif code.startswith(current['code']):
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
        if not len(parts) > 1 or len(parts[0]) == 1:
            return

        element_type = self._get_element_type(parts[0])
        if not element_type:
            return

        elem = self._make_node(parts, element_type)
        self.maintable.append(elem)

    def get_results(self):
        return self.maintable + self.helptable

    def _make_node(self, parts, element_type=None, current=None):
        code = parts[0]
        label = parts[1]

        is_collection = '--' in code
        element_type = element_type or self._get_element_type(code)

        node = None # TODO: USE self._index.get(code) OR merge in final step
        if not node:
            node = OrderedDict()
            if code[0].isalpha():
                self._index[code] = node
        else:
            assert node['label'] == label, "%r != %r" % (
                    (node['code'], node['label']), (code, label))

        if is_collection:
            node['@type'] = 'Collection'
        elif element_type:
            node['@type'] = element_type
        else:
            node['@type'] = 'Classification'

        node_id = "sab:%s" % quote(code.encode('utf-8'), safe=b'')

        # NOTE: Many local elements are similar to their top-level element, but
        # far from all (and special '.0' elements are always locally unique).
        if current and element_type:
            if code[0:2] != '.0':
                node['broader'] = {'@id': node_id}
            node_id = current['@id'] + code

        node['@id'] = node_id
        node['code'] = code
        node['label'] = label

        if len(parts) > 2:
            node['comment'] = parts[2]

        # TODO: Really create additional Elements, or add alias ID and itemPortion?
        # (... Or only use in SAB-code parsing code?)
        if not is_collection and len(code) > 1:

            if re.match(r'^F[åb-z]\w*$', code): # Fb--Få
                aux_elem = self._make_node(['=' + code[1:], parts[1]])
                node.setdefault('related', []).append(aux_elem)

            # TODO: if 'H', add relation to 'F' + code[1:] ?

            elif code.startswith('N'):
                aux_elem = self._make_node(['-' + code[1:], parts[1]])
                node.setdefault('related', []).append(aux_elem)

            # TODO: if 'J', 'K' or 'M', add relation to 'N' + code[1:] ?

        return node

    def _get_element_type(self, code):
        c = code[0]
        if c.isalpha():
            return None
        if code[0:2] == '.0':
            return 'Element'
        code_type_map = {
             '-': 'GeographicElement',
             ':': 'ContentGenreElement', # can be any Classification code.lower()
             '.': 'TemporalElement',
             #'z': 'MonographicElemet',
             '(': 'ContentFormElement',
             '=': 'LanguageElement',
             '/': 'MediaElement',
             ',': 'AudienceElement',
        }
        return code_type_map.get(c)


def error_correct(parts):
    code = parts[0]

    if code == '\u201c':
        return
    if code == 'z':
        return
    if code == 'Macao':
        return
    if len(code) > 1 and code[1] == '\xa0':
        return
    if code == '(' and parts[-1][-1] == ')':
        return # IMPROVE: add as comment to previous node
    if parts[0:2] == ['D', 'Filosofi: allmänt']:
        return
    if parts[0:2] == ['H', 'Skönlitteratur: samlingar']:
        return
    if parts[0:2] == ['N', 'Geografi']:
        return
    if code == '1990' and parts[1] == " ":
        return
    if code == 'Hit' and parts[1].startswith(' '):
        return
    if code == 'Hi' and not parts[1].startswith('Italiensk'):
        return
    if code in 'Ele' and parts[1].startswith('ctro '):
        return
    if code in 'Elec' and parts[1].startswith('tro '):
        return
    if code == 'Ex' and parts[1].startswith(': '):
        return
    if code == 'Xxa' and parts[1].startswith(' används inte'):
        return
    if parts[1].startswith(' kan'):
        return
    if code == 'I' and parts[1] in ['nternet', 'nteractive whiteboards']:
        return

    if code == '(' and re.match(r'^[a-z]+$', parts[1]):
        return [code + parts[1]] + parts[2:]

    if code == ':' and re.match(r'^[a-z]+$', parts[1]):
        return [code + parts[1]] + parts[2:]

    if parts[1] == '--':
        first, rest = parts[2].split(' ', 1)
        return [code + parts[1] + first, rest] + parts[3:]

    if parts[0:2] == ['Ib.23', 'Ib.26']:
        return ['%s--%s' % (code, parts[1]), parts[2]]

    if parts[0:2] == ['K.23', 'K.26']:
        return ['%s--%s' % (code, parts[1]), parts[2]]

    if parts[0:2] == ['Uh', 'e'] and parts[2].startswith(('f ', 'g ')):
        return [code + parts[1] + parts[2][0], parts[2][2:]]

    if (re.match(r'[A-Z][a-z]*$', code) and
            re.match(r'[a-z][a-z0-9.]*$', parts[1])):
        return [code + parts[1], parts[2]]

    if re.match(r'^[a-z]+--\w+$', parts[1]):
        last_part, text= parts[2].split(' ', 1)
        return [code + parts[1] + last_part, text]

    if parts[1] == ' ' and len(parts) > 2:
        return [code] + parts[2:]

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
                print("#", parts[0])
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
                print(('%s =' % parts[0]), *parts[1:], sep='\t')

    return thandler.get_results()


if __name__ == '__main__':
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

    print(json.dumps(results, indent=2, ensure_ascii=False))
