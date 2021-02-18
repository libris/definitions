import datetime
from lxltools.datacompiler import Compiler
import os

SCRIPT_DIR = os.path.dirname(__file__) or '.'
BASE = 'https://libris.kb.se/'

compiler = Compiler(base_dir=SCRIPT_DIR,
        dataset_id=BASE + 'library/',
        #context='build/vocab/context.jsonld',
        context='source/vocab-overlay.jsonld',
        record_thing_link='mainEntity',
        system_base_iri="",
        union='libraries.jsonld.lines',
        created=datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()[:-6] + 'Z') # Beware, Compiler() demands UTC but treats as local time. Potential source of time bugs!

@compiler.dataset
def libraries():
    libraries = fetch_libraries(
            'https://bibdb.libris.kb.se/api?sigel=*&level=&libris_reg=True'
            ) + fetch_libraries(
            'https://bibdb.libris.kb.se/api?sigel=*&level=&libris_reg=&org_type=bibliography')
    bidb_context = 'https://bibdb.libris.kb.se/libdb/static/meta/context.jsonld'
    graph = compiler.construct(sources=[
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
    return "/", "2019-03-14T15:31:17.000Z", graph


def fetch_libraries(start_url):
    url = start_url
    result = []

    start = 0
    batch = 200
    while True:
        print('Fetching %s' % url)
        data = compiler.load_json(compiler.cache_url(url))
        libraries = data['libraries']
        if libraries:
            result += libraries
            start += batch
            url = start_url + '&start=%s' % start
        else:
            break

    return result


if __name__ == '__main__':
    compiler.main()
