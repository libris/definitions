import os
from rdflib import Graph
from lxltools.datacompiler import Compiler
from urllib.parse import urljoin


BASE = "https://id.kb.se/"

SCRIPT_DIR = os.path.dirname(__file__) or '.'


def aslist(o):
    return o if isinstance(o, list) else [] if o is None else [o]


compiler = Compiler(base_dir=SCRIPT_DIR,
                    dataset_id=BASE + 'dataset/common',
                    created='2013-10-17T14:07:48.000Z',
                    tool_id=BASE + 'generator/datasetcompiler',
                    context='sys/context/base.jsonld',
                    record_thing_link='mainEntity',
                    system_base_iri='',
                    union='datasets.jsonld.lines')


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
                'source': Graph().parse(str(compiler.path('source/rda-terms.ttl')), format='turtle'),
                'dataset': BASE + 'dataset/rdaterms'
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
def relators():
    graph = compiler.construct(sources=[
        {
            "source": Graph().parse(str(compiler.path('source/relators.ttl')), format='turtle'),
            "dataset": BASE + "dataset/relators",
        },
        {
            "source": "http://id.loc.gov/vocabulary/relators"
        },
        {
            "source": "http://finto.fi/rest/v1/mts/data",
            "dataset": "http://urn.fi/URN:NBN:fi:au:mts:"
        },
        {
            "source": "http://d-nb.info/standards/elementset/gnd"
        },
        {
            "source": "sparql/bnf-roles",
            "construct": "source/remote/construct-bnf-roles.rq"
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

    languages = Graph().parse(str(compiler.path('source/languages.ttl')), format='turtle')

    graph = compiler.construct(sources=[
            {
                "source": languages,
                "dataset": BASE + "dataset/languages"
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
    countries = Graph().parse(str(compiler.path('source/countries.ttl')), format='turtle')

    graph = compiler.construct(sources=[
            {
                "source": countries,
                "dataset": BASE + "dataset/countries"
            },
            {
                "source": "http://id.loc.gov/vocabulary/countries"
            }
        ],
        query="source/construct-countries.rq")

    return "/country/", "2014-02-01T12:21:14.008Z", graph


if __name__ == '__main__':
    compiler.main()
