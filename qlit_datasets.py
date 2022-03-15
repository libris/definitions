from lxltools.datacompiler import Compiler
import os

SCRIPT_DIR = os.path.dirname(__file__) or '.'
BASE = 'https://queerlit.dh.gu.se/qlit/0.2/'


compiler = Compiler(base_dir=SCRIPT_DIR,
        dataset_id=BASE,
        context='sys/context/base.jsonld',
        record_thing_link='mainEntity',
        system_base_iri="",
        union='qlit.jsonld.lines',
        created="2022-03-10T15:00:00.000Z")


@compiler.dataset
def qlit():
    graph = _construct_qlit_data()
    return "/qlit", "2022-03-10T15:00:00.000Z", graph


def _construct_qlit_data():
    graph = compiler.construct(sources=[
        {'source': 'https://queerlit.dh.gu.se/qlit/0.2/'}
    ],
        query="source/construct-qlit.rq")

    return graph


if __name__ == '__main__':
    compiler.main()
