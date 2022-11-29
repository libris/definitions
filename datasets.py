import shutil

import syscore
import common
import docs

if __name__ == '__main__':
    syscore.compiler.main()
    common.compiler.main()
    docs.compiler.main()

    out_dir = syscore.compiler.outdir
    with (out_dir / 'definitions.jsonld.lines').open('wb') as defs_f:
        for mod in [syscore, common, docs]:
            with (out_dir / mod.compiler.union).open('rb') as f:
                shutil.copyfileobj(f, defs_f)
