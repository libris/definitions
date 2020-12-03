from __future__ import unicode_literals, print_function
if bytes is not str:
    unicode = str

import json
from rdflib import ConjunctiveGraph, URIRef, RDF, RDFS, OWL, XSD
from rdflib.util import guess_format, SUFFIX_FORMAT_MAP
from rdflib.resource import Resource

Resource.id = Resource.identifier
SUFFIX_FORMAT_MAP['jsonld'] = 'json-ld'


DEFAULT_NS_PREF_ORDER = (
        'bf2 bf madsrdf skos dc dctype prov sdo bibo foaf void'
        'owl rdfs rdf xsd edtf').split()

CLASS_TYPES = {RDFS.Class, OWL.Class, RDFS.Datatype}
PROP_TYPES = {RDF.Property, OWL.ObjectProperty, OWL.DatatypeProperty}


def make_context(graph, dest_vocab,
                 ns_pref_order=DEFAULT_NS_PREF_ORDER, use_sub=False):
    terms = set()
    for s in graph.subjects():
        if not isinstance(s, URIRef):
            continue
        r = graph.resource(s)
        in_source_vocab = True  # TODO: provide source and target vocab(s)
        if in_source_vocab:
            terms.add(r)
    if dest_vocab.isalnum():
        dest_vocab = graph.store.namespace(dest_vocab)
    prefixes = set()
    defs = {}
    for term in terms:
        dfn = termdef(term, ns_pref_order, use_sub)
        # TODO: if SDO.rangeIncludes RDF.langString:
        #  key + 'ByLang': {"@id": key, "@container": "@language"}
        if dfn:
            curie = dfn.get('@reverse') or dfn['@id'] \
                    if isinstance(dfn, dict) else dfn
            if ':' in curie:
                pfx = curie.split(':', 1)[0]
                prefixes.add(pfx)
            key = _key(term)
            if key != dfn:
                defs[key] = dfn
    ns = {}
    for pfx, iri in graph.namespaces():
        if pfx in prefixes:
            ns[pfx] = unicode(iri)
        elif pfx == "":
            ns["@vocab"] = iri
    if dest_vocab:
        ns["@vocab"] = dest_vocab
    return {"@context": [ns, defs]}


def termdef(term, ns_pref_order=None, use_sub=False):
    types = set(o.id for o in term.objects(RDF.type))
    is_class = types & CLASS_TYPES
    is_prop = types & PROP_TYPES

    if not is_class and not is_prop:
        return None

    predicates = [OWL.sameAs]

    if is_class:
        predicates.append(OWL.equivalentClass)
        if use_sub:
            predicates.append(RDFS.subClassOf)
    else:
        predicates.append(OWL.equivalentProperty)
        if use_sub:
            predicates.append(RDFS.subPropertyOf)

    for pred in predicates:
        mapped = get_preferred(term, pred, ns_pref_order)
        if mapped:
            target_term = mapped
            break
    else:
        target_term = None

    curie = _key(target_term or term)
    if is_class:
        return curie

    islist = False
    datatype = None
    for range_type in term.objects(RDFS.range):
        if range_type.id:
            if range_type.id.startswith(XSD):
                datatype = range_type
                break
            elif range_type.id == RDF.List:
                islist = True
                break

    if datatype:
        datatype = datatype.qname()
    elif OWL.DatatypeProperty in types:
        datatype = False
    else:
        datatype = None

    if types & {RDF.Property, OWL.FunctionalProperty}:
        container = None
    elif islist:
        container = "@list"
    # IMPROVE: elif OWL.ObjectProperty in types:
    #    container = "@set"
    else:
        container = None

    if datatype or container:
        dfn = {"@id": curie}
        if datatype:
            dfn["@type"] = datatype
        elif datatype is False:
            dfn["@language"] = None
        if container:
            dfn["@container"] = container
        return dfn
    else:
        return curie


def get_preferred(term, pred, ns_pref_order=None):
    ns_pref_order = ns_pref_order or []
    current, current_index = None, len(ns_pref_order)
    candidate = None
    relateds = list(term.objects(pred))
    term_pfx = _pfx(term)
    for related in relateds:
        pfx = _pfx(related)
        if pfx == term_pfx or pfx not in ns_pref_order:
            continue
        candidate = related
        try:
            index = ns_pref_order.index(pfx)
            if index <= current_index:
                current, current_index = related, index
        except ValueError:
            pass
    return current or candidate


def _key(term):
    dest_vocab = term.graph.store.namespace("")
    termstr = unicode(term)
    if termstr.startswith(dest_vocab):
        return termstr[len(dest_vocab):]
    else:
        return unicode(term.qname())


def _pfx(term):
    qname = term.qname()
    return qname.split(':', 1)[0] if ':' in qname else ""


def add_overlay(context, overlay):
    ns, defs = context['@context']
    overlay = overlay.get('@context') or overlay
    for term, dfn in overlay.items():
        if isinstance(dfn, unicode) and dfn.endswith(('/', '#', ':', '?')):
            assert term not in ns or ns[term] == dfn
            ns[term] = dfn
        elif term in defs:
            v = defs[term]
            if v == dfn:
                continue
            if isinstance(v, unicode):
                v = defs[term] = {'@id': v}
            if isinstance(dfn, dict):
                v.update(kv for kv in dfn.items() if kv[0] != '@id')
            else:
                assert isinstance(dfn, unicode)
                # TODO: assert v['@id'] == compacted(dfn) and skip check below
                if '/' not in dfn:
                    v['@id'] = dfn
        else:
            defs[term] = dfn


if __name__ == '__main__':
    import sys
    args = sys.argv[1:]

    fpath = args.pop(0)
    overlay_fpath = args.pop(0) if args else None
    dest_vocab = args.pop(0) if args else None
    if '--sub' in args:
        args.remove('--sub')
        use_sub = True
    else:
        use_sub = False
    ns_pref_order = args if args else DEFAULT_NS_PREF_ORDER

    graph = ConjunctiveGraph()
    graph.parse(fpath, format=guess_format(fpath))

    context = make_context(graph, dest_vocab, ns_pref_order, use_sub)
    if overlay_fpath:
        with open(overlay_fpath) as fp:
            overlay = json.load(fp)
        add_overlay(context, overlay)

    s = json.dumps(context, sort_keys=True, indent=2, separators=(',', ': '),
                   ensure_ascii=False).encode('utf-8')
    print(s)
