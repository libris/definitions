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
from os import path
from datetime import datetime

from rdflib import ConjunctiveGraph, Graph, RDF, URIRef
from rdflib_jsonld.serializer import from_rdf
from rdflib_jsonld.parser import to_rdf

from . import lxlslug


class Compiler:

    def __init__(self,
                 base_dir=None,
                 dataset_id=None,
                 tool_id=None,
                 created=None,
                 context=None,
                 record_thing_link='mainEntity',
                 system_base_iri=None,
                 union='all.jsonld.lines'):
        self.datasets = {}
        self.base_dir = Path(base_dir)
        self.dataset_id = dataset_id
        self.tool_id = tool_id
        self.created = created
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

        self._create_dataset_description(self.dataset_id,
                w3c_dtz_to_ms(self.created))
        for name in names:
            build, as_dataset = self.datasets[name]
            if len(names) > 1:
                print("Dataset:", name)
            if as_dataset:
                self._compile_dataset(name, build)
            else:
                build()
        print()

    def _compile_dataset(self, name, func):
        base, created_time, data = func()

        created_ms = w3c_dtz_to_ms(created_time)
        modified_ms = self.last_modified_ms(func)

        if isinstance(data, Graph):
            data = self.to_jsonld(data)

        ds_url = urljoin(self.dataset_id, name)
        self._create_dataset_description(ds_url, created_ms, modified_ms)

        base_id = urljoin(self.dataset_id, base)

        for node in data['@graph']:
            nodeid = node.get('@id')
            if not nodeid:
                print("Missing id for:", node)
                continue
            if not nodeid.startswith(base_id):
                print("Missing mapping of <%s> under base <%s>" % (nodeid, base_id))
                continue

            fpath = urlparse(nodeid).path[1:]
            desc = self._to_node_description(node,
                    created_ms + _faux_offset(node['@id']),
                    datasets=[self.dataset_id, ds_url])
            self.write(desc, fpath)

    def _create_dataset_description(self, ds_url, created_ms, modified_ms=None, label=None):
        if not label:
            label = ds_url.rsplit('/', 1)[-1]
        ds = {
            '@id': ds_url,
            '@type': 'Dataset',
            'label': label
        }
        desc = self._to_node_description(ds, created_ms, modified_ms,
                datasets={self.dataset_id, ds_url})

        record = desc['@graph'][0]
        if self.tool_id:
            record['generationProcess'] = {'@id': self.tool_id}

        ds_path = urlparse(ds_url).path[1:]

        self.write(desc, ds_path)

    def _to_node_description(self, node, created_ms,
            modified_ms=None, datasets=None):
        assert self.record_thing_link not in node

        node_id = node['@id']

        record = OrderedDict()
        record['@type'] = 'Record'
        record['@id'] = self.generate_record_id(created_ms, node_id)
        record[self.record_thing_link] = {'@id': node_id}

        # Add provenance
        record['created'] = to_w3c_dtz(created_ms)
        if modified_ms is not None:
            record['modified'] = to_w3c_dtz(modified_ms)
        if datasets:
            record['inDataset'] = [{'@id': ds} for ds in datasets]

        items = [record, node]

        return {'@graph': items}

    def last_modified_ms(self, func):
        fpaths = self._generating_resources(func)
        time_stamps = [path.getmtime(file) for file in fpaths]
        last_modified_s = max(time_stamps)
        return last_modified_s * 1000

    def _generating_resources(self, func):
        func_consts = func.__code__.co_consts
        resources = set()
        for i, c in enumerate(func_consts):
            if isinstance(c, str):
                pth = self.path(c)
                if path.isfile(pth):
                    resources.add(pth)
                elif path.isdir(pth):
                    # We expect a dir to be followed by a filename wildcard pattern used with glob
                    if '/*.' in func_consts[i + 1]:
                        files_from_dir = pth.glob(func_consts[i + 1])
                        for f in files_from_dir:
                            resources.add(f)
        return resources

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


def w3c_dtz_to_ms(ztime):
    assert ztime.endswith('Z')
    ztime, ms = ztime.rsplit('.', 1)
    if ms.endswith('Z'):
        ms = ms[:-1]
    return int(time.mktime(time.strptime(ztime,
                                         "%Y-%m-%dT%H:%M:%S"))
               * 1000 + int(ms))


def to_w3c_dtz(ms):
    return datetime.fromtimestamp(ms / 1000).isoformat()[:-3] + 'Z'


def _faux_offset(s):
    return sum(ord(c) * ((i+1) ** 2)  for i, c in enumerate(s))


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
