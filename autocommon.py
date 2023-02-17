import os
from rdflib import Graph
from lxltools.datacompiler import Compiler

BASE = "https://id.kb.se/"

SCRIPT_DIR = os.path.dirname(__file__) or '.'


def datasets_to_compiler(description_path):
    compiler = Compiler(base_dir=SCRIPT_DIR,
                        dataset_id=BASE + 'dataset/common',
                        created='2013-10-17T14:07:48.000Z',
                        tool_id=BASE + 'generator/datasetcompiler',
                        context='sys/context/base.jsonld',
                        record_thing_link='mainEntity',
                        system_base_iri='',
                        union='common.jsonld.lines')

    g = Graph().parse(compiler.path(description_path), format='turtle')
    data = compiler.to_jsonld(g)
    for ds in data['@graph']:
        if ds.get('@type') != 'Dataset' or 'uriSpace' not in ds:
            continue
        compiler.dataset(make_handler(compiler, ds))

    return compiler


def make_handler(compiler, ds):
    def dataset_handler():
        source = digest_source_data(ds['sourceData'])
        if len(src := source['source']) == 1 and 'query' in src[0]:
            source = src[0]

        graph = compiler.construct(
            sources=source.get('source', []),
            query=source.get('query')
        )

        ztime = ds['created']['@value'].replace('+00:00', 'Z')
        return ds.get('uriSpace'), ztime, graph

    dataset_handler.__name__ = ds['@id'].rsplit('/', 1)[-1]

    return dataset_handler


def digest_source_data(src):
    source = {}
    unhandled = False

    if 'dataQuery' in src:
        assert 'query' not in source
        source['query'] = src['dataQuery']['uri']
    elif '@id' in src:
        assert 'source' not in source
        source['source'] = str(src['@id']) # TODO: bug in rdflib; URIRef in the json-ld
    elif 'uri' in src:
        instruct = 'result' if 'sourceData' in src else 'source'
        assert instruct not in source
        source[instruct] = src['uri']
    else:
        unhandled = True

    if 'representationOf' in src:
        instruct = 'dataset'
        assert instruct not in source
        source[instruct] = src['representationOf']['@id']
        unhandled = False

    for part in aslist(src.get('sourceData')):
        source.setdefault('source', []).append(digest_source_data(part))
        unhandled = False

    assert not unhandled

    return source


def aslist(o):
    return o if isinstance(o, list) else [] if o is None else [o]


if __name__ == '__main__':
    ds_desc_file = 'source/datasets/idkbse.ttl'
    datasets_to_compiler(ds_desc_file).main()
