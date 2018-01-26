from __future__ import unicode_literals, print_function
from rdflib import ConjunctiveGraph
from rdflib.util import guess_format


def run_query(source, query_file, context=None):
    graph = ConjunctiveGraph()
    fmt = ('json-ld' if source.endswith('.jsonld') else
            guess_format(source))
    graph.parse(source, format=fmt, context=context)
    with open(query_file) as fp:
        query_text = fp.read().decode('utf-8')
    result = graph.query(query_text)
    for row in result:
        print('\t'.join(t.n3() if t else 'UNDEF' for t in row).encode('utf-8'))


if __name__ == '__main__':
    from sys import argv
    args = argv[1:]
    source = args.pop(0)
    query_file = args.pop(0)
    context = 'build/vocab/context.jsonld'
    run_query(source, query_file, context)
