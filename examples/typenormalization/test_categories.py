import sys

from rdflib import Graph, Namespace, OWL
from owlrl import DeductiveClosure  # type: ignore[import-untyped]
from owlrl.OWLRL import OWLRL_Semantics  # type: ignore[import-untyped]

SPEC = Namespace('https://libris.kb.se/sys/spec/')


def reason(sources: list[str], base_uri: str) -> Graph:
    graph = Graph()
    for source in sources:
        subgraph = Graph().parse(source, publicID=base_uri)

        if len(subgraph) > 400 and (None, OWL.equivalentClass, None) in subgraph:
            # Too much for OWL-RL (on a laptop in 2024); drop non-relevant axioms...
            subgraph.update('''delete { ?s ?p ?o } where {
                ?s ?p ?o
                filter(?p not in (rdfs:subPropertyOf,
                                  owl:inverseOf,
                                  owl:propertyChainAxiom,
                                  rdf:first, rdf:rest))
            }''')

        graph |= subgraph
        for pfx, ns in subgraph.namespace_manager.namespaces():
            graph.namespace_manager.bind(pfx, ns)

    DeductiveClosure(
        OWLRL_Semantics,
        improved_datatypes=True,
        rdfs_closure=True,
        axiomatic_triples=True,
        datatype_axioms=True,
    ).expand(graph)

    return graph


def run_tests(graph: Graph, base_uri: str) -> bool:
    total = 0
    passed = 0

    for subject, query_literal in sorted(graph.subject_objects(SPEC.query)):
        query = str(query_literal)
        result = graph.query(f'BASE <{base_uri}> {query}')

        total += 1

        if result.askAnswer:
            status = "OK"
            passed += 1
        else:
            status = "FAIL"

        s = str(subject).removeprefix(base_uri)
        print(status, f"<{s}>", query, sep="\t")

    print()
    print(f"Passed {passed} of {total} tests.")

    if failed := total - passed:
        print(f"Failed {failed}.")
        return False

    return True


def main():
    sources = [
        '../../source/vocab/concepts.ttl',
        'classes.ttl',
        'rdamatches.ttl',
        'genreforms.ttl',
        'cache/saogf.ttl',
        'examples.ttl',
    ]

    base_uri = "http://libris.kb.se/sys/examples/typenormalization/"

    graph = reason(sources, base_uri=base_uri)

    if '-d' in sys.argv[1:]:
        print('#' * 72)
        print(graph.serialize(format='turtle'))
        print('#' * 72)

    if not run_tests(graph, base_uri):
        sys.exit(1)


if __name__ == '__main__':
    main()
