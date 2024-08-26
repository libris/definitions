from rdflib import Graph, Namespace
from owlrl import DeductiveClosure  # type: ignore[import-untyped]
from owlrl.OWLRL import OWLRL_Semantics  # type: ignore[import-untyped]

SPEC = Namespace('https://libris.kb.se/sys/spec/')


def reason(*sources: str) -> Graph:
    graph = Graph()
    graph.parse(axioms_file_path)
    graph.parse(tests_file_path, publicID=base_uri)

    DeductiveClosure(
        OWLRL_Semantics,
        improved_datatypes=True,
        rdfs_closure=True,
        axiomatic_triples=True,
        datatype_axioms=True,
    ).expand(graph)

    return graph


def run_tests(graph: Graph, base_uri: str):
    for subject, query_literal in sorted(graph.subject_objects(SPEC.query)):
        query = str(query_literal)
        result = graph.query(f'BASE <{base_uri}> {query}')
        status = "OK" if result.askAnswer else "FAIL"
        s = str(subject).removeprefix(base_uri)
        print(status, f"<{s}>", query, sep="\t")


if __name__ == '__main__':
    import sys

    base_uri = "http://libris.kb.se/sys/examples/typenormalization/"
    axioms_file_path = 'categories.ttl'
    tests_file_path = 'examples.ttl'

    graph = reason(axioms_file_path, tests_file_path)

    if '-d' in sys.argv[1:]:
        print('#' * 72)
        print(graph.serialize(format='turtle'))
        print('#' * 72)

    run_tests(graph, base_uri)
