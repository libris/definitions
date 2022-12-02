import os
import markdown
from lxltools.datacompiler import Compiler

BASE = "https://id.kb.se/"

SCRIPT_DIR = os.path.dirname(__file__) or '.'

compiler = Compiler(base_dir=SCRIPT_DIR,
                    dataset_id=BASE + 'dataset/docs',
                    created='2016-04-15T14:42:00.000Z',
                    tool_id=BASE + 'generator/docsbuilder',
                    context='sys/context/base.jsonld',
                    record_thing_link='mainEntity',
                    system_base_iri='',
                    union='docs.jsonld.lines')


@compiler.dataset
def id_docs():
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
