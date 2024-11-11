import sys

from rdflib import BNode, OWL, RDF, Dataset, Graph, Namespace, URIRef
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID

SPEC = Namespace('https://libris.kb.se/sys/spec/')


def reason(graph: Graph) -> None:
    if '--reasonable' in sys.argv[1:]:
        import reasonable  # type: ignore[import-untyped]

        r = reasonable.PyReasoner()
        r.from_graph(graph)
        for triple in r.reason():
            graph.add(triple)

        return

    from owlrl import DeductiveClosure  # type: ignore[import-untyped]
    from owlrl.OWLRL import OWLRL_Semantics  # type: ignore[import-untyped]
    
    DeductiveClosure(
        OWLRL_Semantics,
        improved_datatypes=True,
        rdfs_closure=True,
        axiomatic_triples=True,
        datatype_axioms=True,
    ).expand(graph)


def drop_too_much(graph: Graph) -> None:
    if len(graph) > 400 and (None, OWL.equivalentClass, None) in graph:
        # A bit too much for OWL-RL (on a laptop in 2024); drop non-relevant axioms...
        graph.update(
            '''delete { ?s ?p ?o } where {
            ?s ?p ?o
            filter(?p not in (rdfs:subPropertyOf,
                                owl:inverseOf,
                                owl:propertyChainAxiom,
                                rdf:first, rdf:rest))
        }'''
        )


def build_tests(ds: Dataset, tbox: Graph, base_uri: str) -> tuple:
    tests: dict = {}
    variants = {'cmp', 'exp', 'cmp-ext', 'exp-ext', 'neg'}

    cmps = tbox | Graph()
    exps = tbox | Graph()
    cmp_exts = tbox | Graph()
    exp_exts = tbox | Graph()

    for g in ds.graphs():
        if g.identifier == DATASET_DEFAULT_GRAPH_ID:
            continue

        s = str(g.identifier).removeprefix(base_uri)
        if '/' not in s:
            continue

        name, leaf = s.rsplit('/', 1)
        if leaf in variants:
            tests.setdefault(name, {})[leaf] = g
            match leaf:
                case 'cmp':
                    cmps |= g
                case 'exp':
                    exps |= g
                case 'cmp-ext':
                    cmp_exts |= g
                case 'exp-ext':
                    exp_exts |= g

    reason(cmps)
    reason(exps)
    reason(cmp_exts)
    reason(exp_exts)

    return tests, cmps, exps, cmp_exts, exp_exts


def test_contained_in(knowledge, subgraph):
    ok = True
    diffing = Graph()
    none_blank = lambda t: None if isinstance(t, BNode) else t
    for spo in subgraph:
        s, p, o = spo
        # TODO: too smushed; may give false positives; use C14N instead...
        if (none_blank(s), p, none_blank(o)) not in knowledge:
            ok = False
            diffing.add(spo)

    diffing.namespace_manager = knowledge.namespace_manager

    return ok, diffing


def run_tests(ds: Dataset, tbox: Graph, base_uri: str) -> bool:
    tests, cmps, exps, cmp_exts, exp_exts = build_tests(ds, tbox, base_uri)

    total = 0
    passed = 0

    for name, graphs in tests.items():
        for variant, contained_in_variant, knowledge in [
            ('cmp', 'exp', exps),
            ('exp', 'cmp', cmps),
            ('cmp-ext', 'exp-ext', exp_exts),
            ('exp-ext', 'cmp-ext', cmp_exts),
        ]:
            if variant not in graphs:
                continue

            if contained_in_variant not in graphs:
                continue

            subgraph = graphs[variant]
            ok, diffing = test_contained_in(knowledge, subgraph)
            total += 1
            if ok:
                passed += 1
            label = f"<{name}/{contained_in_variant}> implies <{name}/{variant}>"
            report(label, ok, diffing, base_uri)

        if 'exp-neg' in graphs:
            neg = graphs['exp-neg']
            total += 1
            ok = True
            for spo in neg:
                if spo in exps:
                    ok = False
            if ok:
                passed += 1
            report(name, ok, neg, base_uri, "negative")

    print()
    print(f"Passed {passed} of {total} tests.")

    if failed := total - passed:
        print(f"Failed {failed}.")
        return False

    return True


def report(name: str, ok: bool, diffing: Graph, base_uri: str, note="") -> None:
    note = f" [{note}]" if note else ""
    if not ok:
        print()
    status = "OK" if ok else "FAIL"
    print(f"{status}\t{name}{note}")
    if not ok and len(diffing) > 0:
        ttl = diffing.serialize(format='turtle', publicID=base_uri)
        print(ttl.split('\n\n', 1)[1])


def main():
    sources = [
        '../../source/vocab/concepts.ttl',
        '../../source/vocab/newtypes/classes.ttl',
        '../../source/vocab/newtypes/rdamatches.ttl',
        '../../source/vocab/newtypes/genreforms.ttl',
        'cache/saogf.ttl',
    ]

    base_uri = "http://libris.kb.se/sys/examples/typenormalization/"
    tbox = Graph()
    for source in sources:
        graph = Graph().parse(source, publicID=base_uri)
        drop_too_much(graph)
        tbox |= graph

    ds = Dataset(default_union=False)
    ds.parse('examples.trig', publicID=base_uri)

    if not run_tests(ds, tbox, base_uri):
        sys.exit(1)


if __name__ == '__main__':
    main()
