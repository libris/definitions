from __future__ import unicode_literals, print_function
__metaclass__ = type
if bytes is not str:
    unicode = str

import argparse
from collections import OrderedDict
try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path
try:
    from urllib.parse import urlparse, urljoin, quote
    from urllib.request import urlopen
except ImportError:
    from urlparse import urlparse, urljoin
    from urllib2 import quote, urlopen
import sys
import json
import csv
import time

from rdflib import ConjunctiveGraph, Graph, RDF, URIRef
from rdflib_jsonld.serializer import from_rdf
from rdflib_jsonld.parser import to_rdf

from . import lxlslug


class Compiler:

    def __init__(self,
                 base_dir=None,
                 dataset_id=None,
                 context=None,
                 record_thing_link='mainEntity',
                 system_base_iri=None,
                 union='all.jsonld.lines'):
        self.datasets = {}
        self.base_dir = Path(base_dir)
        self.dataset_id = dataset_id
        self.system_base_iri = system_base_iri
        self.record_thing_link = record_thing_link
        self.context = context
        self.cachedir = None
        self.union = union

    def main(self):
        argp = argparse.ArgumentParser(
                description="Available datasets: " + ", ".join(self.datasets),
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        arg = argp.add_argument
        arg('-s', '--system-base-iri', type=str, default=None, help="System base IRI")
        arg('-o', '--outdir', type=str, default=self.path("build"), help="Output directory")
        arg('-c', '--cache', type=str, default=self.path("cache"), help="Cache directory")
        arg('-l', '--lines', action='store_true',
                help="Output a single file with one JSON-LD document per line")
        arg('datasets', metavar='DATASET', nargs='*')

        args = argp.parse_args()
        if not args.datasets and args.outdir:
            args.datasets = list(self.datasets)

        self._configure(args.outdir, args.cache, args.system_base_iri, use_union=args.lines)
        self._run(args.datasets)

    def _configure(self, outdir, cachedir=None, system_base_iri=None, use_union=False):
        if system_base_iri:
            self.system_base_iri = system_base_iri
        self.outdir = Path(outdir)
        self.cachedir = cachedir
        if use_union:
            union_fpath = self.outdir / self.union
            union_fpath.parent.mkdir(parents=True, exist_ok=True)
            self.union_file = union_fpath.open('wt', encoding='utf-8')
        else:
            self.union_file = None

    def _run(self, names):
        try:
            self._compile_datasets(names)
        finally:
            if self.union_file:
                self.union_file.close()

    def dataset(self, func):
        self.datasets[func.__name__] = func, True
        return func

    def handler(self, func):
        self.datasets[func.__name__] = func, False
        return func

    def path(self, pth):
        return self.base_dir / pth

    def to_jsonld(self, graph):
        return _to_jsonld(graph,
                         "../" + self.context,
                         self.load_json(self.context))

    def _compile_datasets(self, names):
        for name in names:
            build, as_dataset = self.datasets[name]
            if len(names) > 1:
                print("Dataset:", name)
            result = build()
            if as_dataset:
                base, created_time, data = result

                created_ms = self.ztime_to_millis(created_time)

                if isinstance(data, Graph):
                    data = self.to_jsonld(data)

                context, resultset = _partition_dataset(urljoin(self.dataset_id, base), data)

                for key, node in resultset.items():
                    node = self._to_node_description(node,
                            created_ms,
                            dataset=self.dataset_id,
                            source='/dataset/%s' % name)
                    self.write(node, key)
            print()

    def _to_node_description(self, node, datasource_created_ms, dataset=None, source=None):
        assert self.record_thing_link not in node

        def faux_offset(s):
            return sum(ord(c) * ((i+1) ** 2)  for i, c in enumerate(s))

        node_id = node['@id']
        created_ms = datasource_created_ms + faux_offset(node_id)

        record = OrderedDict()
        record['@type'] = 'Record'
        record['@id'] = self.generate_record_id(created_ms, node_id)
        record[self.record_thing_link] = {'@id': node_id}

        # Add provenance
        # TODO: overhaul these? E.g. mainEntity with timestamp and 'datasource'.
        #print(dataset, source)
        #record['created'] = date_created
        #record['modified'] = date_modified
        #if datasource:
        #    record['datasource'] = {'@id': datasource}

        items = [record, node]

        return {'@graph': items}

    def ztime_to_millis(self, ztime):
        assert ztime.endswith('Z')
        ztime, ms = ztime.rsplit('.', 1)
        if ms.endswith('Z'):
            ms = ms[:-1]
        return int(time.mktime(time.strptime(ztime,
                                             "%Y-%m-%dT%H:%M:%S"))
                   * 1000 + int(ms))

    def generate_record_id(self, created_ms, node_id):
        slug = lxlslug.librisencode(created_ms, lxlslug.checksum(node_id))
        return urljoin(self.system_base_iri, slug)

    def write(self, node, name):
        node_id = node.get('@id')
        if node_id:
            assert not node_id.startswith('_:')
        if self.union_file:
            line = json.dumps(node)
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            print(line, file=self.union_file)
        # TODO: else: # don't write both to union_file and separate file
        pretty_repr = _serialize(node)
        if pretty_repr:
            outfile = self.outdir / ("%s.jsonld" % name)
            print("Writing:", outfile)
            outfile.parent.mkdir(parents=True, exist_ok=True)
            with outfile.open('wb') as fp:
                fp.write(pretty_repr)
        else:
            print("No data")

    def get_cached_path(self, url):
        return self.cachedir / quote(url, safe="")

    def cache_url(self, url):
        path = self.get_cached_path(url)
        if not path.exists():
            with path.open('wb') as fp:
                r = urlopen(url)
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
            fpath = self.cachedir / (remotepath[len(http):] + '.ttl')
            if not fpath.is_file():
                fpath.parent.mkdir(parents=True, exist_ok=True)
                source.parse(remotepath)
                source.serialize(str(fpath), format='turtle')
                return source
            else:
                return source.parse(str(fpath), format='turtle')
        source.parse(str(fpath))
        return source

    def load_json(self, fpath):
        with self.path(fpath).open() as fp:
            return json.load(fp)

    def read_csv(self, fpath, **kws):
        return _read_csv(self.path(fpath), **kws)

    def construct(self, sources, query=None):
        return _construct(self, sources, query)


def _serialize(data):
    if isinstance(data, (list, dict)):
        data = json.dumps(data, indent=2, sort_keys=True,
                separators=(',', ': '), ensure_ascii=False)
    if isinstance(data, unicode):
        data = data.encode('utf-8')
    return data


CSV_FORMATS = {'.csv': 'excel', '.tsv': 'excel-tab'}

def _read_csv(fpath, encoding='utf-8'):
    csv_dialect = CSV_FORMATS.get(fpath.suffix)
    assert csv_dialect
    if unicode is str:
        opened = fpath.open('rt', encoding=encoding)
        decode = lambda v: v
    else:
        opened = fpath.open('rb')
        decode = lambda v: v.decode(encoding)
    with opened as fp:
        reader = csv.DictReader(fp, dialect=csv_dialect)
        for item in reader:
            yield {k: decode(v.strip()) for (k, v) in item.items() if v}


def _construct(compiler, sources, query=None):
    dataset = ConjunctiveGraph()
    if not isinstance(sources, list):
        sources = [sources]
    for sourcedfn in sources:
        source = sourcedfn['source']
        graph = dataset.get_context(URIRef(sourcedfn.get('dataset') or source))
        if isinstance(source, (dict, list)):
            context_data = sourcedfn['context']
            if not isinstance(context_data, list):
                context_data = compiler.load_json(context_data )['@context']
            context_data = [compiler.load_json(ctx)['@context']
                            if isinstance(ctx, unicode) else ctx
                            for ctx in context_data]
            to_rdf(source, graph, context_data=context_data)
        elif isinstance(source, Graph):
            graph += source
        else:
            graph += compiler.cached_rdf(source)
    if not query:
        return graph
    with compiler.path(query).open() as fp:
        result = dataset.query(fp.read())
    g = Graph()
    for spo in result:
        g.add(spo)
    return g


def _to_jsonld(source, context_uri, contextobj):
    data = from_rdf(source, context_data=contextobj)
    data['@context'] = context_uri
    _embed_singly_referenced_bnodes(data)
    _expand_ids(data['@graph'], contextobj['@context'])
    return data


def _expand_ids(obj, pfx_map):
    """
    Ensure @id values are in expanded form (i.e. full URIs).
    """
    if isinstance(obj, list):
        for item in obj:
            _expand_ids(item, pfx_map)
    elif isinstance(obj, dict):
        node_id = obj.get('@id')
        if node_id:
            pfx, colon, leaf = node_id.partition(':')
            ns = pfx_map.get(pfx)
            if ns:
                obj['@id'] = node_id.replace(pfx + ':', ns, 1)
        for value in obj.values():
            _expand_ids(value, pfx_map)


def _embed_singly_referenced_bnodes(data):
    graph_index = {item['@id']: item for item in data.pop('@graph')}
    bnode_refs = {}

    def collect_refs(node):
        for values in node.values():
            if not isinstance(values, list):
                values = [values]
            for value in values:
                if isinstance(value, dict):
                    if value.get('@id', '').startswith('_:'):
                        bnode_refs.setdefault(value['@id'], []).append(value)
                    collect_refs(value)

    for node in graph_index.values():
        collect_refs(node)

    for refid, refs in bnode_refs.items():
        if len(refs) == 1:
            refs[0].update(graph_index.pop(refid))
            refs[0].pop('@id')

    data['@graph'] = sorted(graph_index.values(), key=lambda node: node['@id'])


def _partition_dataset(base, data):
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
        rel_path = urlparse(nodeid).path[1:]
        resultset[rel_path] = node
    return data.get('@context'), resultset
