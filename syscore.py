import os
from rdflib import Graph, RDF, Namespace
from lxltools.datacompiler import Compiler, last_modified_ms
from lxltools.timeutil import w3c_dtz_to_ms
from urllib.parse import urljoin


SCRA = Namespace("http://purl.org/net/schemarama#")

LIBRIS_BASE = "https://libris.kb.se/"

ID_BASE = "https://id.kb.se/"

SCRIPT_DIR = os.path.dirname(__file__) or '.'


def _get_repo_version():
    try:
        with os.popen(
                '(cd {} && git describe --tags)'.format(SCRIPT_DIR)
                ) as pipe:
            return pipe.read().rstrip()
    except:
        return None


compiler = Compiler(base_dir=SCRIPT_DIR,
                    dataset_id=LIBRIS_BASE + 'dataset/syscore',
                    created='2022-11-19T13:09:35.010Z',
                    tool_id=ID_BASE + 'generator/syscorecompiler',
                    context='sys/context/base.jsonld',
                    record_thing_link='mainEntity',
                    system_base_iri='',
                    union='syscore.jsonld.lines')


@compiler.handler
def contexts():
    contexts_ds_url = urljoin(compiler.dataset_id, 'sys/context')

    context_alias = ID_BASE + 'vocab/context'

    docpath = compiler.path('sys/context/kbv.jsonld')
    uripath = ID_BASE + 'sys/context/kbv'
    _write_context_record(compiler, docpath, uripath, contexts_ds_url, context_alias)

    root = compiler.path('')
    for docpath in compiler.path('sys/context').glob('target/*.jsonld'):
        uripath = ID_BASE + str(docpath.relative_to(root).with_suffix(''))
        _write_context_record(compiler, docpath, uripath, contexts_ds_url)


@compiler.handler
def vocab():
    vocab_base = ID_BASE + 'vocab/'

    graph = compiler.construct(sources=[
            {
                'source': Graph().parse(str(compiler.path('source/vocab/bf-map.ttl')), format='turtle'),
                'dataset': '?'
            },
            {"source": "http://id.loc.gov/ontologies/bibframe/"}
        ],
        query="source/vocab/bf-to-kbv-base.rq")

    for part in compiler.path('source/vocab').glob('**/*.ttl'):
        try:
            graph.parse(str(part), format='turtle')
        except:
            print(f"Error in file: {part}")
            raise

    graph.update(compiler.path('source/vocab/update.rq').read_text('utf-8'))
    graph.update(compiler.path('source/vocab/updateResource.rq').read_text('utf-8'))

    rq = compiler.path('source/vocab/construct-enum-restrictions.rq').read_text('utf-8')
    graph += Graph().query(rq).graph

    rq = compiler.path('source/vocab/check-bases.rq').read_text('utf-8')
    checks = graph.query(rq).graph
    for check, msg in checks.subject_objects(SCRA.message):
        print("{}: {}".format(
            graph.qname(checks.value(check, RDF.type)).split(':')[-1],
            msg.format(*[imp.n3() for imp in
                checks.collection(checks.value(check, SCRA.implicated))])
            ))

    for part in compiler.path('source/marc').glob('**/*.ttl'):
        graph.parse(str(part), format='turtle')

    graph.parse(str(compiler.path('source/swepub/vocab.ttl')), format='turtle')

    # Clean up generated prefixes
    preferred = {}
    defaulted = {}
    for pfx, uri in graph.store.namespaces():
        if pfx.startswith('default'):
            defaulted[uri] = pfx
        else:
            preferred[uri] = pfx
    # TODO: Remove?
    for uri, default_pfx in defaulted.items():
        if uri in preferred:
            graph.namespace_manager.bind(preferred[uri], uri, override=True)

    data = compiler.to_jsonld(graph)
    del data['@context']

    # Put /vocab/* first (ensures that /marc/* comes after)
    data['@graph'] = sorted(data['@graph'], key=lambda node:
            (not node.get('@id', '').startswith(vocab_base), node.get('@id')))

    vocab_created_ms = w3c_dtz_to_ms("2013-12-31T23:00:00.000Z")

    vocab_ds_url = urljoin(compiler.dataset_id, 'vocab')
    vocab_modified_ms = last_modified_ms(compiler.current_ds_resources)
    compiler._create_dataset_description(vocab_ds_url, vocab_created_ms, vocab_modified_ms)

    _insert_record(data['@graph'], vocab_created_ms, vocab_ds_url)
    vocab_node = data['@graph'][1]
    version = _get_repo_version()
    if version:
        vocab_node['version'] = version

    display = compiler.load_json('source/vocab/display.jsonld')
    _insert_record(display['@graph'], vocab_created_ms, vocab_ds_url)

    compiler.write(data, "vocab")
    compiler.write(display, 'vocab/display')


@compiler.handler
def apps():
    apps = compiler.load_json('source/apps.jsonld')
    created_ms = w3c_dtz_to_ms("2022-11-18T15:19:35.001Z")
    ds_url = urljoin(compiler.dataset_id, 'sys/apps')
    for app in apps['@graph']:
        slug = app['@id']
        descriptions = [app]
        _insert_record(descriptions, created_ms, ds_url)
        compiler.write({'@graph': descriptions}, slug)


def _insert_record(graph, created_ms, dataset_id):
    entity = graph[0]
    record = {'@type': 'SystemRecord'}
    record[compiler.record_thing_link] = {'@id': entity['@id']}
    graph.insert(0, record)
    record['@id'] = compiler.generate_record_id(created_ms, entity['@id'])
    record['inDataset'] = [{'@id': compiler.dataset_id}, {'@id': dataset_id}]


def _write_context_record(compiler, filepath, uripath, ds_url, alias=None):
    ctx_data = compiler.load_json(filepath)
    ctx_created_ms = w3c_dtz_to_ms(ctx_data.pop('created'))

    ctx_data['@graph'] = [{"@id": uripath, "@type": "jsonld:Context"}]
    _insert_record(ctx_data['@graph'], ctx_created_ms, ds_url)
    if alias:
        ctx_data['@graph'][0]['sameAs'] = [{'@id': alias}]

    assert uripath.startswith(ID_BASE)
    compiler.write(ctx_data, uripath.replace(ID_BASE, ''))


if __name__ == '__main__':
    compiler.main()
