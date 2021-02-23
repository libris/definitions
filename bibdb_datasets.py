import datetime
from lxltools.datacompiler import Compiler
import os


SCRIPT_DIR = os.path.dirname(__file__) or '.'
BASE = 'https://libris.kb.se/'


compiler = Compiler(base_dir=SCRIPT_DIR,
        dataset_id=BASE + 'dataset/bibdb',
        context='source/vocab-overlay.jsonld',
        record_thing_link='mainEntity',
        system_base_iri="",
        union='libraries.jsonld.lines',
        created="2019-03-14T15:00:00.000Z")


@compiler.dataset
def libraries():
    graph = _construct_bibdb_data('sigel=*&level=&libris_reg=True&org_type=library')
    return "/library", "2019-03-14T15:31:17.000Z", graph


@compiler.dataset
def bibliographies():
    graph = _construct_bibdb_data('sigel=*&level=&libris_reg=&org_type=bibliography')
    return "/bibliography", "2019-03-14T19:32:20.000Z", graph


def _construct_bibdb_data(query):
    libraries = _fetch_libraries(f'https://bibdb.libris.kb.se/api?{query}')
    bidb_context = 'https://bibdb.libris.kb.se/libdb/static/meta/context.jsonld'
    return compiler.construct(sources=[
            {
                "source": libraries,
                "dataset": BASE + "dataset/libraries",
                "context": [
                    compiler.load_json(compiler.cache_url(bidb_context)),
                    {"@base": "http://bibdb.libris.kb.se/"}
                ]
            }
        ],
        query="source/construct-libraries.rq")


def _fetch_libraries(start_url):
    url = start_url
    result = []

    start = 0
    batch = 200
    while True:
        data = compiler.load_json(compiler.cache_url(url))
        libraries = data['libraries']
        if libraries:
            result += libraries
            start += batch
            url = f'{start_url}&start={start}'
        else:
            break

    return result


if __name__ == '__main__':
    compiler.main()
