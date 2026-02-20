from rdflib import Graph
from rdflib.plugins.serializers.jsonld import from_rdf
from rdflib.plugins.parsers.jsonld import to_rdf


def to_jsonld(source: Graph, context_uri: str, contextobj) -> dict:
    data = from_rdf(source, context_data=contextobj)
    assert isinstance(data, dict)
    if '@graph' not in data:
        data = {'@graph': [data]}

    data['@context'] = context_uri
    _embed_singly_referenced_bnodes(data)
    _expand_ids(data['@graph'], contextobj['@context'])

    return data


def _expand_ids(obj, pfx_map):
    """
    Ensure @id values are in expanded form (i.e. full URIs).
    """
    if isinstance(obj, list):
        for item in obj:
            _expand_ids(item, pfx_map)
    elif isinstance(obj, dict):
        node_id = obj.get('@id')
        if node_id:
            pfx, colon, leaf = node_id.partition(':')
            ns = pfx_map.get(pfx)
            if ns:
                obj['@id'] = node_id.replace(pfx + ':', ns, 1)
        for value in obj.values():
            _expand_ids(value, pfx_map)


def _embed_singly_referenced_bnodes(data):
    graph_index = {item['@id']: item for item in data.pop('@graph')}
    bnode_refs = {}

    def collect_refs(node):
        for values in node.values():
            if not isinstance(values, list):
                values = [values]
            for value in values:
                if isinstance(value, dict):
                    if value.get('@id', '').startswith('_:'):
                        bnode_refs.setdefault(value['@id'], []).append(value)
                    collect_refs(value)

    for node in graph_index.values():
        collect_refs(node)

    for refid, refs in bnode_refs.items():
        if len(refs) == 1:
            refs[0].update(graph_index.pop(refid))
            refs[0].pop('@id')

    data['@graph'] = sorted(graph_index.values(), key=lambda node: node['@id'])
