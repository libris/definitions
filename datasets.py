import os
import re
from rdflib import Graph, ConjunctiveGraph, RDF, Namespace
from lxltools.datacompiler import Compiler, w3c_dtz_to_ms, last_modified_ms
from lxltools.contextmaker import make_context, add_overlay
from urllib.parse import urljoin


NS_PREF_ORDER = (
        'bf2 bflc bf madsrdf skos dc dctype prov sdo bibo foaf void ldp '
        'owl rdfs rdf xsd edtf').split()

SCRA = Namespace("http://purl.org/net/schemarama#")

BASE = "https://id.kb.se/"

SCRIPT_DIR = os.path.dirname(__file__) or '.'


def decorate(items, template):
    def decorator(item):
        for k, tplt in template.items():
            item[k] = tplt.format(**item)
        return item
    return list(map(decorator, items))


def to_camel_case(label):
    return "".join((s[0].upper() if i else s[0].lower()) + s[1:]
            for (i, s) in enumerate(re.split(r'[\s,.-]', label)) if s)


def _get_repo_version():
    try:
        with os.popen(
                '(cd {} && git describe --tags)'.format(SCRIPT_DIR)
                ) as pipe:
            return pipe.read().rstrip()
    except:
        return None


compiler = Compiler(base_dir=SCRIPT_DIR,
                    dataset_id=BASE + 'dataset/definitions',
                    created='2013-10-17T14:07:48.000Z',
                    tool_id=BASE + 'generator/definitions',
                    context='sys/context/base.jsonld',
                    record_thing_link='mainEntity',
                    system_base_iri='',
                    union='definitions.jsonld.lines')


def _insert_record(graph, created_ms, dataset_id):
    entity = graph[0]
    record = {'@type': 'Record'}
    record[compiler.record_thing_link] = {'@id': entity['@id']}
    graph.insert(0, record)
    record['@id'] = compiler.generate_record_id(created_ms, entity['@id'])
    record['inDataset'] = [{'@id': compiler.dataset_id}, {'@id': dataset_id}]


#@compiler.dataset
#def datasets():
#    graph = Graph().parse(compiler.path('source/index.ttl'), format='turtle')
#    return to_jsonld(graph, (None, None), { "@language": "sv"})


@compiler.handler
def vocab():
    vocab_base = BASE + 'vocab/'

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

    #cg = ConjunctiveGraph()
    #cg.parse(str(compiler.path('source/vocab/display.jsonld')), format='json-ld')
    #graph += cg

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
    for default_pfx, uri in defaulted.items():
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

    lib_context = make_context(graph, vocab_base, NS_PREF_ORDER)
    add_overlay(lib_context, compiler.load_json('sys/context/kbv.jsonld'))
    lib_context['@graph'] = [{'@id': BASE + 'vocab/context'}]
    _insert_record(lib_context['@graph'], vocab_created_ms, vocab_ds_url)

    display = compiler.load_json('source/vocab/display.jsonld')
    _insert_record(display['@graph'], vocab_created_ms, vocab_ds_url)

    compiler.write(data, "vocab")
    compiler.write(lib_context, 'vocab/context')
    compiler.write(display, 'vocab/display')


@compiler.handler
def contexts():
    contexts_ds_url = urljoin(compiler.dataset_id, 'sys/context')

    docpath = compiler.path('sys/context/kbv.jsonld')
    uripath = BASE + 'sys/context/kbv'
    _write_context_record(compiler, docpath, uripath, contexts_ds_url)

    root = compiler.path('')
    for docpath in compiler.path('sys/context').glob('target/*.jsonld'):
        uripath = BASE + str(docpath.relative_to(root).with_suffix(''))
        _write_context_record(compiler, docpath, uripath, contexts_ds_url)


def _write_context_record(compiler, filepath, uripath, ds_url):
    ctx_data = compiler.load_json(filepath)
    ctx_created_ms = w3c_dtz_to_ms(ctx_data.pop('created'))
    ctx_data['@graph'] = [{"@id": uripath, "@type": "jsonld:Context"}]
    _insert_record(ctx_data['@graph'], ctx_created_ms, ds_url)
    assert uripath.startswith(BASE)
    compiler.write(ctx_data, uripath.replace(BASE, ''))


@compiler.dataset
def enums():
    graph = Graph()
    rq = compiler.path('source/marc/construct-enums.rq').read_text('utf-8')
    graph += Graph().query(rq).graph

    return "/marc/", "2014-01-23T10:34:17.981Z", graph


@compiler.dataset
def rdaterms():
    # NOTE: see also examples/mappings/rda-bf2-types.ttl for possibiliy of
    # extending our type system (instead).
    graph = compiler.construct(sources=[
            {
                "source": list(compiler.read_csv('source/rdamap.tsv')),
                "context": "source/rdamap-context.jsonld"
            },

            {'source': 'http://rdaregistry.info/termList/RDAContentType.nt'},
            {'source': 'http://id.loc.gov/vocabulary/contentTypes'},

            {'source': 'http://rdaregistry.info/termList/RDAMediaType.nt'},
            {'source': 'http://id.loc.gov/vocabulary/mediaTypes'},

            {'source': 'http://rdaregistry.info/termList/RDACarrierType.nt'},
            {'source': 'http://id.loc.gov/vocabulary/carriers'},

            #{'source': 'http://rdaregistry.info/termList/ModeIssue'},
            #{'source': 'http://id.loc.gov/vocabulary/issuance.skos.rdf'},

        ],
        query="source/construct-rda-terms.rq")

    return "/term/rda/", "2018-05-16T06:18:01.337Z", graph


@compiler.dataset
def enumterms():
    graph = Graph().parse(str(compiler.path('source/kbv-enums.ttl')), format='turtle')

    return "/term/enum/", "2018-05-29T12:36:01.337Z", graph

@compiler.dataset
def materials():
    graph = compiler.construct(sources=[
        {
            "source": Graph().parse(str(compiler.path('source/materials.ttl')), format='turtle'),
            "dataset": BASE + "dataset/materials"
        },
        {
            "source": "http://rdaregistry.info/termList/RDAMaterial.nt"
        },
        {
            "source": "sparql/aat-materials",
            "construct": "source/remote/construct-aat-materials.rq",
        }
    ],
        query="source/construct-materials.rq")

    return "/material/", "2021-12-07T21:28:01.123Z", graph

@compiler.dataset
def musnotationterms():
    graph = compiler.construct(sources=[
        {
            "source": Graph().parse(str(compiler.path('source/musicnotation.ttl')), format='turtle'),
            "dataset": BASE + "dataset/musnotationterms"
        },
        {
            "source": "http://rdaregistry.info/termList/MusNotation.nt"
        }
    ],
        query="source/construct-musnotationsterms.rq")

    return "/term/rda/musnotation/", "2021-05-21T23:59:01.337Z", graph


@compiler.dataset
def tacnotationterms():
    graph = compiler.construct(sources=[
        {
            "source": Graph().parse(str(compiler.path('source/tactilenotation.ttl')), format='turtle'),
            "dataset": BASE + "dataset/tacnotationterms"
        },
        {
            "source": "http://rdaregistry.info/termList/TacNotation.nt"
        }
    ],
        query="source/construct-tacnotationterms.rq")

    return "/term/rda/tacnotation/", "2021-05-21T23:59:10.456Z", graph

#NOTE: More suitable name might be needed if usage is broader than digital representations
@compiler.dataset
def reprterms():
    graph = Graph().parse(str(compiler.path('source/repr-terms.ttl')), format='turtle')

    return "/term/repr/", "2021-02-22T10:32:01.337Z", graph

@compiler.dataset
def encodingFormatterms():
    graph = Graph().parse(str(compiler.path('source/encodingFormat-terms.ttl')), format='turtle')

    return "/encodingFormat/", "2021-03-04T10:12:09.921Z", graph

@compiler.dataset
def bibdbterms():
    graph = ConjunctiveGraph()
    # graph = Graph()
    for part in compiler.path('source/bibdb').glob('**/*.ttl'):
        graph.parse(str(part), format='turtle')

    return "/term/bibdb/", "2021-09-20T08:13:50.570Z", graph

@compiler.dataset
def swepubterms():
    graph = Graph()
    for part in compiler.path('source/swepub').glob('**/*.ttl'):
        if part.stem == 'vocab':
            continue
        graph.parse(str(part), format='turtle')

    graph.update(compiler.path('source/swepub/update.rq').read_text('utf-8'))

    return "/term/swepub/", "2018-05-29T12:36:01.337Z", graph


@compiler.dataset
def policies():
    graph = Graph().parse(str(compiler.path('source/policies.ttl')), format='turtle')

    return "/policy/", "2021-11-18T11:48:51Z", graph


@compiler.dataset
def containers():
    graph = Graph().parse(str(compiler.path('source/containers.ttl')), format='turtle')

    return "/term/", "2019-07-11T13:04:17.964Z", graph


@compiler.dataset
def generators():
    graph = Graph().parse(str(compiler.path('source/generators.ttl')), format='turtle')

    return "/generator/", "2018-04-25T18:55:14.723Z", graph


@compiler.dataset
def schemes():
    graph = Graph().parse(str(compiler.path('source/schemes.ttl')), format='turtle')

    return "/", "2014-02-01T20:00:01.766Z", graph


@compiler.dataset
def relators():

    def relitem(item):
        item['@id'] = item.get('term') or to_camel_case(item['label_en'].strip())
        item['sameAs'] = {'@id': item['code']}
        return item

    # TODO: retrieve finnish label from link/id (finto.fi)
    # TODO: link to german & french RDA terms
    graph = compiler.construct(sources=[
            {
                "source": list(map(relitem, compiler.read_csv('source/funktionskoder.tsv'))),
                "dataset": BASE + "dataset/relators",
                "context": ["sys/context/ns.jsonld", {
                    "@base": BASE + "relator/",
                    "@vocab": "https://id.kb.se/vocab/",
                    "code": "skos:notation",
                    "label_sv": {"@id": "skos:prefLabel", "@language": "sv"},
                    "altlabel_sv": {"@id": "skos:altLabel", "@language": "sv"},
                    "label_en": {"@id": "skos:prefLabel", "@language": "en"},
                    "label_de": {"@id": "skos:prefLabel", "@language": "de"},
                    "altlabel_de": {"@id": "skos:altLabel", "@language": "de"},
                    "label_fi": {"@id": "skos:prefLabel", "@language": "fi"},
                    "label_is": {"@id": "skos:prefLabel", "@language": "is"},
                    "label_fr": {"@id": "skos:prefLabel", "@language": "fr"},
                    "urn_de": {"@id": "skos:exactMatch", "@type": "@vocab"},
                    "urn_fi": {"@id": "skos:exactMatch", "@type": "@vocab"},
                    "hidden_label": "skos:hiddenLabel",
                    "comment_sv": {"@id": "rdfs:comment", "@language": "sv"},
                    "term": "rdfs:label",
                    "sameAs": "owl:sameAs",
                    "domain": {"@id": "rdfs:domain", "@type": "@vocab"},
                    "rda_app_i_1_en": {"@id": "skos:altLabel", "@language": "en"},
                    "rda_app_i_2_en": {"@id": "skos:altLabel", "@language": "en"},
                    "rda_app_i_3_en": {"@id": "skos:altLabel", "@language": "en"},
                }]
            },
            {
                "source": "http://id.loc.gov/vocabulary/relators"
            }
        ],
        query="source/construct-relators.rq")

    return "/relator/", "2014-02-01T16:29:12.378Z", graph


@compiler.dataset
def languages():
    loclanggraph = Graph()
    loclanggraph.parse(
            str(compiler.cache_url('http://id.loc.gov/vocabulary/iso639-1.nt')),
            format='nt')
    loclanggraph.parse(
            str(compiler.cache_url('http://id.loc.gov/vocabulary/iso639-2.nt')),
            format='nt')

    languages = decorate(compiler.read_csv('source/spraakkoder.tsv'),
        {"@id": BASE + "language/{code}"})

    graph = compiler.construct(sources=[
            {
                "source": languages,
                "dataset": BASE + "dataset/languages",
                "context": "source/table-context.jsonld"
            },
            {
                "source": loclanggraph,
                "dataset": "http://id.loc.gov/vocabulary/languages"
            }
        ],
        query="source/construct-languages.rq")

    return "/language/", "2014-08-01T07:56:51.110Z", graph


@compiler.dataset
def countries():
    graph = compiler.construct(sources=[
            {
                "source": decorate(compiler.read_csv('source/landskoder.tsv'),
                    {"@id": BASE + "country/{code}"}),
                "dataset": BASE + "dataset/countries",
                # TODO: fix rdflib_jsonld so urls in external contexts are loaded
                "context": "source/table-context.jsonld"
            },
            {
                "source": "http://id.loc.gov/vocabulary/countries"
            }
        ],
        query="source/construct-countries.rq")

    return "/country/", "2014-02-01T12:21:14.008Z", graph


@compiler.dataset
def nationalities():
    return "/nationality/", "2014-02-01T13:08:56.596Z", compiler.construct({
            "source": decorate(
                compiler.read_csv('source/nationalitetskoder.tsv'),
                {"@id": BASE + "nationality/{code}", "@type": 'Nationality'}),
            "context": [
                "sys/context/base.jsonld",
                {"label_sv": {"@id": "skos:prefLabel", "@language": "sv"}},
                {"altLabel_sv": {"@id": "skos:altLabel", "@language": "sv"}},
                {"label_en": {"@id": "skos:prefLabel", "@language": "en"}},
                {"comment_sv": {"@id": "rdfs:comment", "@language": "sv"}}
            ]
        })


@compiler.dataset
def docs():
    import markdown
    docs = []
    sourcepath = compiler.path('source')
    for fpath in (sourcepath / 'doc').glob('**/*.mkd'):
        text = fpath.read_text('utf-8')
        html = markdown.markdown(text)
        doc_id = (str(fpath.relative_to(sourcepath))
                  .replace(os.sep, '/')
                  .replace('.mkd', ''))
        doc_id, dot, lang = doc_id.partition('.')
        doc = {
            "@type": "Article",
            "@id": BASE + doc_id,
            "articleBody": html
        }
        h1end = html.find('</h1>')
        if h1end > -1:
            doc['title'] = html[len('<h1>'):h1end]
        if lang:
            doc['language'] = {"langTag": lang},
        docs.append(doc)

    return "/doc", "2016-04-15T14:43:38.072Z", {
        "@context": "../sys/context/base.jsonld",
        "@graph": docs
    }


if __name__ == '__main__':
    compiler.main()
