from __future__ import unicode_literals, print_function
__metaclass__ = type
from collections import OrderedDict
from os import makedirs, path as Path
import urllib2
import sys
import json
import csv

from rdflib import ConjunctiveGraph, Graph, RDF, URIRef
from rdflib_jsonld.serializer import from_rdf
from rdflib_jsonld.parser import to_rdf


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

    def get_cached_path(self, url):
        return Path.join(self.cachedir, urllib2.quote(url, safe=""))

    def cache_url(self, url):
        path = self.get_cached_path(url)
        if not Path.exists(path):
            with open(path, 'wb') as fp:
                r = urllib2.urlopen(url)
                while True:
                    chunk = r.read(1024 * 8)
                    if not chunk: break
                    fp.write(chunk)
        return path

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
        source.parse(fpath)
        return source


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


def load_json(fpath):
    with open(fpath) as fp:
        return json.load(fp)


def read_csv(fpath, encoding='utf-8'):
    csv_dialect = ('excel' if fpath.endswith('.csv')
            else 'excel-tab' if fpath.endswith('.tsv')
            else None)
    assert csv_dialect
    with open(fpath, 'rb') as fp:
        reader = csv.DictReader(fp, dialect=csv_dialect)
        for item in reader:
            yield {k: v.decode(encoding).strip()
                            for (k, v) in item.items() if v}


def decorate(items, template):
    def decorator(item):
        for k, tplt in template.items():
            item[k] = tplt.format(**item)
        return item
    return map(decorator, items)


def construct(load_rdf, sources, query):
    dataset = ConjunctiveGraph()
    for sourcedfn in sources:
        source = sourcedfn['source']
        graph = dataset.get_context(URIRef(sourcedfn.get('dataset') or source))
        if isinstance(source, (dict, list)):
            to_rdf(source, graph, context_data=sourcedfn['context'])
        elif isinstance(source, Graph):
            graph += source
        else:
            graph += load_rdf(source)
    with open(query) as fp:
        result = dataset.query(fp.read())
    g = Graph()
    for spo in result:
        g.add(spo)
    return g


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
