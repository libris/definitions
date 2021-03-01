import argparse
import csv
import json
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urljoin, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http import HTTPStatus

from rdflib import ConjunctiveGraph, Graph, RDF, URIRef
from rdflib_jsonld.serializer import from_rdf
from rdflib_jsonld.parser import to_rdf

from . import lxlslug


MAX_CACHE = 60 * 60


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
        self.current_ds_resources = set()
        self.base_dir = tracked_path_type(self.current_ds_resources)(base_dir)
        self.dataset_id = dataset_id
        self.tool_id = tool_id
        self.created = created
        self.system_base_iri = system_base_iri
        self.record_thing_link = record_thing_link
        self.context = context
        self.cachedir = None
        self.union = union
        self.current_ds_file = None

    def main(self):
        argp = argparse.ArgumentParser(
                description="Available datasets: " + ", ".join(self.datasets),
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        arg = argp.add_argument
        arg('-s', '--system-base-iri', type=str, default=None, help="System base IRI")
        arg('-o', '--outdir', type=str, default=self.path("build"), help="Output directory")
        arg('-c', '--cache', type=str, default="cache", help="Cache directory")
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
        self.cachedir = tracked_path_type(self.current_ds_resources)(cachedir)
        if use_union:
            union_fpath = self.outdir / self.union
            union_fpath.parent.mkdir(parents=True, exist_ok=True)
            self.union_file = union_fpath.open('wt', encoding='utf-8')
            print("Writing dataset lines to file:", self.union_file.name)
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
            ds_fpath = self.outdir / '{}.json.lines'.format(name)
            ds_fpath.parent.mkdir(parents=True, exist_ok=True)
            with ds_fpath.open('wt', encoding='utf-8') as ds_file:
                self.current_ds_file = ds_file
                print("Writing dataset lines to file:", self.current_ds_file.name)
                result = build()
                if as_dataset:
                    self._compile_dataset(name, result)
                self.current_ds_file = None
            self.current_ds_resources.clear()
        print()

    def _compile_dataset(self, name, result):
        base, created_time, data = result

        created_ms = w3c_dtz_to_ms(created_time)
        modified_ms = last_modified_ms(self.current_ds_resources)

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
                print(f"Missing mapping of <{nodeid}> under base <{base_id}>")
                continue

            created_ms = created_ms + _faux_offset(node['@id'])
            modified_ms = None

            meta = node.pop('meta', None)
            if meta:
                if 'created' in meta:
                    created_ms = w3c_dtz_to_ms(meta.pop('created'))
                if 'modified' in meta:
                    modified_ms = w3c_dtz_to_ms(meta.pop('modified'))

                assert not meta, f'meta {meta} was not exhausted'

            fpath = urlparse(nodeid).path[1:]
            desc = self._to_node_description(
                    node,
                    created_ms,
                    modified_ms,
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

    def generate_record_id(self, created_ms, node_id):
        slug = lxlslug.librisencode(created_ms, lxlslug.checksum(node_id))
        return urljoin(self.system_base_iri, slug)

    def write(self, node, name):
        node_id = node.get('@id')
        if node_id:
            assert not node_id.startswith('_:')
        if self.union_file or self.current_ds_file:
            line = json.dumps(node)
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            if self.union_file:
                print(line, file=self.union_file)
            if self.current_ds_file:
                print(line, file=self.current_ds_file)
        # TODO: else: # don't write both to union_file and separate file
        pretty_repr = _serialize(node)
        if pretty_repr:
            outfile = self.outdir / f'{name}.jsonld'
            print("Writing:", outfile)
            outfile.parent.mkdir(parents=True, exist_ok=True)
            with outfile.open('wb') as fp:
                fp.write(pretty_repr)
        else:
            print("No data")

    def get_cached_path(self, url):
        return self.cachedir / quote(url, safe="")

    def cache_url(self, url, maxcache=MAX_CACHE):
        path = self.get_cached_path(url)
        mtime = path.stat().st_mtime if path.exists() else None

        if mtime and datetime.now().timestamp() < mtime + maxcache:
            print(f'Using cached URL: {url}')
            return path

        print(f'Fetching URL: {url}')
        req = Request(url)
        if mtime:
            req.add_header('If-Modified-Since', to_http_date(mtime))

        try:
            r = urlopen(req)
        except HTTPError as e:
            if e.status in {HTTPStatus.NOT_MODIFIED,
                            HTTPStatus.INTERNAL_SERVER_ERROR,
                            HTTPStatus.BAD_GATEWAY,
                            HTTPStatus.SERVICE_UNAVAILABLE,
                            HTTPStatus.GATEWAY_TIMEOUT}:
                print(f'{HTTPStatus(e.status)}, using cached URL: {url}')
                return path

            raise e

        with path.open('wb') as fp:
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
    try:  # fromisoformat is new in Python 3.7
        return int(datetime.fromisoformat(ztime.replace('Z', '+00:00'))
                   .timestamp() * 1000)
    except AttributeError:  # fallback can be removed when we rely on Py 3.7+
        ztime = ztime[:-1]  # drop 'Z'
        if '.' not in ztime:
            ztime += '.000'  # add millisecs to comply with format
        ztime += '+0000'  # strptime-compliant UTC timezone format
        return int(datetime.strptime(ztime, '%Y-%m-%dT%H:%M:%S.%f%z')
                   .timestamp() * 1000)


def to_w3c_dtz(ms):
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def to_http_date(s):
    return datetime.utcfromtimestamp(s).strftime('%a, %d %b %Y %H:%M:%S GMT')


def last_modified_ms(fpaths):
    time_stamps = [f.stat().st_mtime for f in fpaths]
    last_modified_s = max(time_stamps)
    return last_modified_s * 1000


def tracked_path_type(resources):
    class TrackedPath(type(Path())):
        def _init(self, *args, **kwargs):
            super()._init(*args, **kwargs)
            if self.is_file():
                resources.add(self)

    return TrackedPath


def _faux_offset(s):
    return sum(ord(c) * ((i+1) ** 2)  for i, c in enumerate(s))


def _serialize(data):
    if isinstance(data, (list, dict)):
        data = json.dumps(data, indent=2, sort_keys=True,
                separators=(',', ': '), ensure_ascii=False)
    if isinstance(data, str):
        data = data.encode('utf-8')
    return data


CSV_FORMATS = {'.csv': 'excel', '.tsv': 'excel-tab'}

def _read_csv(fpath, encoding='utf-8'):
    csv_dialect = CSV_FORMATS.get(fpath.suffix)
    assert csv_dialect
    with fpath.open('rt', encoding=encoding) as fp:
        reader = csv.DictReader(fp, dialect=csv_dialect)
        for item in reader:
            yield {k: v.strip() for (k, v) in item.items() if v}


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
                            if isinstance(ctx, str) else ctx
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
