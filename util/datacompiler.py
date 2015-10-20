from __future__ import unicode_literals, print_function
__metaclass__ = type
from os import makedirs, path as Path
import sys
import re
import json
import csv
from collections import OrderedDict

from rdflib import Graph, RDF
from rdflib_jsonld.serializer import from_rdf


class Compiler:

    def __init__(self):
        self.datasets = {}
        self.cachedir = None

    def dataset(self, func):
        self.datasets[func.__name__] = func
        return func

    def configure(self, outdir, cachedir=None, onefile=False):
        self.outdir = outdir
        self.cachedir = cachedir
        if onefile:
            union_fpath = Path.join(self.outdir, 'definitions.jsonld.lines')
            _ensure_fpath(union_fpath)
            self.union_file = open(union_fpath, 'w')
        else:
            self.union_file = None

    def run(self, names):
        try:
            self._compile_datasets(names)
        finally:
            if self.union_file:
                self.union_file.close()

    def _compile_datasets(self, names):
        for name in names:
            if len(names) > 1:
                print("Dataset:", name)
            basepath, data = self.datasets[name]()
            self.write(data, name)
            context, resultset = partition_dataset(basepath, data)
            for key, node in resultset.items():
                # TODO: add source
                node = to_desc_form(node, '/dataset/%s' % name, source=None)
                if self.union_file:
                    print(json.dumps(node), file=self.union_file)
                self.write(node, key)
            print()

    def write(self, node, name):
        result = _serialize(node)
        if result:
            outfile = Path.join(self.outdir, "%s.jsonld" % name)
            print("Writing:", outfile)
            _ensure_fpath(outfile)
            with open(outfile, 'w') as fp:
                fp.write(result)
        else:
            print("No data")

    def deref(self, iri):
        return self.cached_rdf(iri).resource(iri)

    def cached_rdf(self, fpath):
        source = Graph()
        http = 'http://'
        if not self.cachedir:
            print("No cache directory configured", file=sys.stderr)
        elif fpath.startswith(http):
            remotepath = fpath
            fpath = Path.join(self.cachedir, remotepath[len(http):]) + '.ttl'
            if not Path.isfile(fpath):
                _ensure_fpath(fpath)
                source.parse(remotepath)
                source.serialize(fpath, format='turtle')
                return source
            else:
                return source.parse(fpath, format='turtle')
        return source.parse(fpath)


def _serialize(data):
    if isinstance(data, (list, dict)):
        data = json.dumps(data, indent=2, sort_keys=True,
                separators=(',', ': '), ensure_ascii=False)
    if isinstance(data, unicode):
        data = data.encode('utf-8')
    return data

def _ensure_fpath(fpath):
    fdir = Path.dirname(fpath)
    if not Path.isdir(fdir):
        makedirs(fdir)


def filter_graph(source, propspaces, oftype=None):
    propspaces = tuple(map(unicode, propspaces))
    okspace = lambda t: any(t.startswith(ns) for ns in propspaces)
    selected = set(source[:RDF.type:oftype]) if oftype else None

    graph = Graph()
    for s, p, o in source:
        if selected and s not in selected:
            continue
        if not okspace(p) or p == RDF.type and oftype and o != oftype:
            continue
        graph.add((s, p, o))

    return graph


def extend(data, extradata, lang, keys=('label', 'prefLabel', 'comment'),
        term_source=None, iri_template=None, addtype=None, relation=None,
        key_term='notation'):
    extras = load_data(extradata)
    index = {node[key_term]: node for node in data['@graph']}
    for key, item in extras.items():
        iri = None
        if iri_template:
            term = item.pop('term', None)
            if not term and term_source:
                term = to_camel_case(item[term_source])
            if term:
                iri = iri_template.format(term=term)
        node = index.get(key)
        if not node:
            if iri:
                node = index[key] = {}
                if addtype:
                    node['@type'] = addtype
                node[key_term] = key
            else:
                continue
        for key in keys:
            item_key = "%s_%s" % (key, lang) if lang else key
            if item_key in item:
                node[key] = item[item_key]
        if not iri and iri_template:
            iri = iri_template.format(**node)
        if iri:
            node['@id'], orig_iri = iri, node.get('@id')
            if relation and orig_iri:
                node[relation] = orig_iri


def load_data(fpath, encoding='utf-8'):
    csv_dialect = ('excel' if fpath.endswith('.csv')
            else 'excel-tab' if fpath.endswith('.tsv')
            else None)
    if csv_dialect:
        with open(fpath, 'rb') as fp:
            reader = csv.DictReader(fp, dialect=csv_dialect)
            return {item.pop('code'):
                        {k: v.decode(encoding).strip()
                            for (k, v) in item.items() if v}
                    for item in reader}
    else:
        with open(fpath) as fp:
            return json.load(fp)


def to_camel_case(label):
    return "".join((s[0].upper() if i else s[0].lower()) + s[1:]
            for (i, s) in enumerate(re.split(r'[\s,.-]', label)) if s)


def to_jsonld(source, contextref, contextobj=None):
    contexturi, contextpath = contextref
    context = [contextpath, contextobj] if contextobj else contextpath
    data = from_rdf(source, context_data=context)
    data['@context'] = [contexturi, contextobj] if contextobj else contexturi

    # customize to a convenient shape (within the bounds of JSON-LD)
    base = contextobj.get('@base')
    to_embed = {}
    refs = {}
    for node in data['@graph']:
        nodeid = node['@id']
        if base and nodeid.startswith(base):
            node['@id'] = nodeid[len(base)-1:]
        elif nodeid.startswith('_:'):
            to_embed[nodeid] = node
            continue
    for idref, obj in refs.items():
        obj.update(to_embed[idref])
        #del obj['@id']

    return data


def partition_dataset(base, data):
    resultset = OrderedDict()
    for node in data.pop('@graph'):
        nodeid = node['@id']
        # TODO: Absence caused by mismatch between external id and local mapping
        if not nodeid:
            print("Missing id for:", node)
            continue
        if not nodeid.startswith(base):
            print("Missing mapping of <%s> under base <%s>" % (nodeid, base))
            continue
        rel_path = nodeid[1:]
        resultset[rel_path] = node
    return data.get('@context'), resultset


def to_desc_form(node, dataset=None, source=None):
    item = node.pop('about', None)
    if item:
        node['about'] = {'@id': item['@id']}
    if dataset:
        node['inDataset'] = dataset
    if source:
        node['wasDerivedFrom'] = source
    descriptions = {'entry': node}
    if item:
        descriptions['items'] = [item]
    quoted = []
    for vs in node.values():
        vs = vs if isinstance(vs, list) else [vs]
        for v in vs:
            if isinstance(v, dict) and '@id' in v:
                quoted.append({'@graph': {'@id': v['@id']}})
    # TODO: move addition of 'quoted' objects to (decorated) storage?
    # ... actually move this entire 'descriptions' structure...
    # ... let storage accept a single resource or named graph
    # (with optional, "nested" quotes), and extract links (and sameAs)
    if quoted:
        descriptions.setdefault('quoted', []).extend(quoted)

    return {'descriptions': descriptions}
