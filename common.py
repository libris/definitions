import os

from lxltools.datacompiler import Compiler

compiler = Compiler(
    base_dir=os.path.dirname(__file__),
    datasets_description="source/datasets/idkbse.ttl",
    dataset_id="https://id.kb.se/dataset/common",
    created="2013-10-17T14:07:48.000Z",
    tool_id="https://id.kb.se/generator/datasetcompiler",
    context="sys/context/base.jsonld",
    system_base_iri="",
    union="common.jsonld.lines",
    last_backwards_id_time="2022-10-14T16:26:16Z"
)

if __name__ == "__main__":
    compiler.main()
