import argparse
import csv
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlparse, urljoin, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http import HTTPStatus

from rdflib import ConjunctiveGraph, Graph, URIRef

from . import timeutil
from . import ldutil
from . import lxlslug


MAX_CACHE = 60 * 60

CACHE_SPAQRL_BASE = 'urn:x-cache:sparql:'


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
        self.no_records = False

    def main(self):
        argp = argparse.ArgumentParser(
                description="Available datasets: " + ", ".join(self.datasets),
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        arg = argp.add_argument
        arg('-s', '--system-base-iri', type=str, default=None, help="System base IRI")
        arg('-d', '--dataset-iri', type=str, default=None, help="Union dataset IRI")
        arg('-o', '--outdir', type=str, default=self.path("build"), help="Output directory")
        arg('-c', '--cache', type=str, default="cache", help="Cache directory")
        arg('-l', '--lines', action='store_true',
                help="Output a single file with one JSON-LD document per line")
        arg('-u', '--union-file', type=str, help="Output union file with one JSON-LD document per line")
        arg('-R', '--no-records', action='store_true', help="Do not add Record descriptions")
        arg('datasets', metavar='DATASET', nargs='*')

        args = argp.parse_args()
        if not args.datasets and args.outdir:
            args.datasets = list(self.datasets)

        if args.dataset_iri:
            self.dataset_id = args.dataset_iri

        use_union = args.lines or args.union_file
        if args.union_file:
            self.union = args.union_file

        self._configure(args.outdir, args.cache, args.system_base_iri, use_union, args.no_records)
        self._run(args.datasets)

    def _configure(self, outdir, cachedir=None, system_base_iri=None, use_union=False, no_records=False):
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

        self.no_records = no_records

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
        return ldutil.to_jsonld(graph,
                         "../" + self.context,
                         self.load_json(self.context))

    def _compile_datasets(self, names):
        self._create_dataset_description(self.dataset_id,
                timeutil.w3c_dtz_to_ms(self.created))

        for name in names:
            if name not in self.datasets:
                print(f"Skipping dataset: {name} (not defined in {self.dataset_id})",
                      file=sys.stderr)
                continue

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

        ds_created_ms = timeutil.w3c_dtz_to_ms(created_time)
        ds_modified_ms = last_modified_ms(self.current_ds_resources)

        if isinstance(data, Graph):
            data = self.to_jsonld(data)

        ds_url = urljoin(self.dataset_id, name)
        self._create_dataset_description(ds_url, ds_created_ms, ds_modified_ms)

        base_id = urljoin(self.dataset_id, base)

        for node in data['@graph']:
            nodeid = node.get('@id')
            if not nodeid:
                print("Missing id for:", node)
                continue
            if not nodeid.startswith(base_id):
                print(f"Missing mapping of <{nodeid}> under base <{base_id}>")
                continue

            created_ms = ds_created_ms + _faux_offset(node['@id'])
            modified_ms = None
            fpath = urlparse(nodeid).path[1:]

            if self.no_records:
                self.write(node, fpath)
                continue

            meta = node.pop('meta', None)
            if meta:
                if 'created' in meta:
                    created_ms = timeutil.w3c_dtz_to_ms(meta.pop('created'))
                if 'modified' in meta:
                    modified_ms = timeutil.w3c_dtz_to_ms(meta.pop('modified'))

                assert not meta, f'meta {meta} was not exhausted'

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

        ds_path = urlparse(ds_url).path[1:]

        if self.no_records:
            # TODO: with-record-less data, the dataset description is given as
            # additional source data to XL LDImporter. The routine is not yet
            # set whether that should add/update the DS description (which
            # seems reasonable).
            return

        desc = self._to_node_description(ds, created_ms, modified_ms,
                datasets={self.dataset_id, ds_url})

        record = desc['@graph'][0]
        if self.tool_id:
            record['generationProcess'] = {'@id': self.tool_id}

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
        record['created'] = timeutil.to_w3c_dtz(created_ms)
        if modified_ms is not None:
            record['modified'] = timeutil.to_w3c_dtz(modified_ms)
        if datasets:
            record['inDataset'] = [{'@id': ds} for ds in datasets]

        items = [record, node]

        return {'@graph': items}

    def generate_record_id(self, created_ms, node_id):
        # FIXME: backwards_form=created_ms < 2015
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

    def is_cachable(self, ref):
        return ref.startswith(('http:', 'https:', CACHE_SPAQRL_BASE))

    def get_cached_path(self, url):
        fpath = self.cachedir / quote(url.replace(CACHE_SPAQRL_BASE, 'sparql/'), safe="")
        print(url, fpath)
        return fpath

    def cache_url(self, url, maxcache=MAX_CACHE):
        path = self.get_cached_path(url)
        mtime = path.stat().st_mtime if path.exists() else None

        if mtime and timeutil.nowstamp() < mtime + maxcache:
            print(f'Using cached URL: {url}')
            return path

        print(f'Fetching URL: {url}')
        req = Request(url)
        if mtime:
            req.add_header('If-Modified-Since', timeutil.to_http_date(mtime))

        try:
            r = urlopen(req)
        except HTTPError as e:
            if e.status in {HTTPStatus.NOT_MODIFIED,
                            HTTPStatus.INTERNAL_SERVER_ERROR,
                            HTTPStatus.BAD_GATEWAY,
                            HTTPStatus.SERVICE_UNAVAILABLE,
                            HTTPStatus.GATEWAY_TIMEOUT}:
                print(f'Got HTTP {e.status} {e.reason}, using cached URL: {url}')
                return path

            raise e

        with path.open('wb') as fp:
            while True:
                chunk = r.read(1024 * 8)
                if not chunk: break
                fp.write(chunk)

        return path

    def cached_rdf(self, fpath, construct=None, graph=None):
        source = Graph()
        if not self.cachedir:
            print("No cache directory configured", file=sys.stderr)
        elif construct:
            fpath = self.get_cached_path(fpath + '.ttl')
            if not fpath.is_file():
                with self.path(construct).open() as fp:
                    try:
                        res = (graph or Graph()).query(fp.read())
                        fpath.parent.mkdir(parents=True, exist_ok=True)
                        res.serialize(str(fpath), format='turtle')
                        source.parse(str(fpath), format='turtle')
                    except Exception as e:
                        print(f'Failed to cache {fpath}: {e}', file=sys.stderr)
            else:
                source.parse(str(fpath), format='turtle')
            return source

        elif self.is_cachable(fpath):
            remotepath = fpath
            fpath = self.get_cached_path(fpath + '.ttl')
            print(f'Using cached {fpath} for {remotepath}', file=sys.stderr)
            if not fpath.is_file():
                fpath.parent.mkdir(parents=True, exist_ok=True)
                try:
                    # At least rdaregistry is *very* picky about what is asked for,
                    # so we'll tell them explicitly using `format`.
                    format = 'nt' if remotepath.endswith('.nt') else None
                    source.parse(remotepath, format=format)
                except Exception as e:
                    print(f'Failed on remote path {remotepath}', file=sys.stderr)
                    raise e
                source.serialize(str(fpath), format='turtle')
                return source
            else:
                return source.parse(str(fpath), format='turtle')

        fmt = 'nt' if fpath.endswith('.nt') else None
        source.parse(str(fpath), format=fmt)

        return source

    def load_json(self, fpathref):
        fpath = self.path(fpathref)
        with fpath.open() as fp:
            data = json.load(fp)

            # Rudimentary context import handling to reduce repetition locally
            ctx = data.get('@context')
            if ctx and '@import' in ctx:
                imported = self.load_json(fpath.parent / ctx.pop('@import'))
                impctx = imported.get('@context')
                assert isinstance(impctx, dict), "Only handling imports of simple contexts"
                for k, v in impctx.items():
                    assert k not in ctx, f"Redefinition of imported {k} in {fpath}"
                    ctx.setdefault(k, v)

            return data

    def read_csv(self, fpath, **kws):
        return _read_csv(self.path(fpath), **kws)

    def construct(self, sources, query=None):
        return _construct(self, sources, query)


def last_modified_ms(fpaths):
    time_stamps = [f.stat().st_mtime for f in fpaths]
    last_modified_s = max(time_stamps)
    return last_modified_s * 1000


def tracked_path_type(resources):
    pathtype = type(Path())  # usually PosixPath

    class TrackedPath(pathtype):
        @classmethod
        def _from_parsed_parts(cls, *args, **kwargs):
            path = super()._from_parsed_parts(*args, **kwargs)
            if path.is_file():
                resources.add(path)
            return path

    methodname = TrackedPath._from_parsed_parts.__name__

    assert hasattr(pathtype, methodname), (
        f"Expected pathlib implementation to have a `{methodname}`"
    )

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
        if isinstance(sourcedfn, str):
            sourcedfn = {'source': sourcedfn}

        source = sourcedfn.get('source', [])
        graph = dataset.get_context(URIRef(sourcedfn.get('dataset') or source))
        if isinstance(source, (dict, list)):
            # TODO: was currently unused, and not yet supported in the data-driven form.
            #context_data = sourcedfn['context']
            #if not isinstance(context_data, list):
            #    context_data = compiler.load_json(context_data )['@context']
            #context_data = [compiler.load_json(ctx)['@context']
            #                if isinstance(ctx, str) else ctx
            #                for ctx in context_data]
            #ldutil.to_rdf(source, graph, context_data=context_data)
            graph += _construct(compiler, source, sourcedfn.get('query'))
        elif isinstance(source, Graph):
            graph += source
        elif compiler.is_cachable(source):
            graph += compiler.cached_rdf(source, sourcedfn.get('query'), sourcedfn.get('graph'))
        else:
            sourcepath = compiler.path(source)
            assert sourcepath.is_file(), (source, source.startswith(('http:', 'https:')))
            fmt = 'nt' if source.endswith('.nt') else 'turtle'
            graph += Graph().parse(str(sourcepath), format=fmt)

    if not query:
        return graph

    with compiler.path(query).open() as fp:
        querytext = fp.read()
        if re.search(r'\bCONSTRUCT\b', querytext, re.I):
            result = dataset.query(querytext)
        else:
            dataset.update(querytext)
            result = dataset
        g = Graph()
        for spo in result:
            g.add(spo)
        return g
