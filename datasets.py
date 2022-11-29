import os
import shutil

from lxltools.datacompiler import Compiler
import syscore
import common
import docs

SCRIPT_DIR = os.path.dirname(__file__) or '.'
BASE = "https://id.kb.se/"

compiler = Compiler(base_dir=SCRIPT_DIR,
                    dataset_id=BASE + 'dataset/definitions',
                    created='2013-10-17T14:07:48.000Z',
                    tool_id=BASE + 'generator/definitions',
                    context='sys/context/base.jsonld',
                    record_thing_link='mainEntity',
                    system_base_iri='',
                    union='definitions.jsonld.lines')

if __name__ == '__main__':
    compiler.main()
    syscore.compiler.main()
    common.compiler.main()
    docs.compiler.main()

    out_dir = compiler.outdir
    with (out_dir / compiler.union).open('ab') as defs_f:
        for mod in [syscore, common, docs]:
            with (out_dir / mod.compiler.union).open('rb') as f:
                shutil.copyfileobj(f, defs_f)
