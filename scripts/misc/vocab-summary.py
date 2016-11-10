from __future__ import unicode_literals, print_function, division
from rdflib import *


ABS = Namespace("http://bibframe.org/model-abstract/")
SCHEMA = Namespace("http://schema.org/")


def print_vocab(g, show_equivs=False):
    global otherclasses, otherprops, SHOW_EQUIVS
    SHOW_EQUIVS = show_equivs

    otherclasses = reduce(set.__or__, (set(g.subjects(RDF.type, t))
        for t in [RDFS.Class, OWL.Class]))

    otherprops = reduce(set.__or__, (set(g.subjects(RDF.type, t))
        for t in [RDF.Property, OWL.ObjectProperty, OWL.DatatypeProperty]))

    prefixes = set()
    terms = otherclasses | otherprops
    if SHOW_EQUIVS:
        for term in list(terms):
            for equiv in g.objects(term,
                    OWL.equivalentProperty | OWL.equivalentClass):
                terms.add(equiv)

    for term in terms:
        if not isinstance(term, URIRef):
            continue
        qname = g.qname(term)
        if ':' not in qname:
            qname = ':%s' % qname
        pfx, name = qname.split(':')
        ns = unicode(term)[:-len(name)]
        if pfx in prefixes:
            continue
        prefixes.add(pfx)
        print("prefix %s: <%s>" % (pfx, ns))
    print()

    print_class(g.resource(RDFS.Resource))

    for c in sorted(otherclasses):
        if any(o for o in g.objects(c, RDFS.subClassOf)
                if o not in {RDFS.Resource, OWL.Thing}
                and not isinstance(o, BNode)
                and not _ns(g, c) == _ns(g, o)):
            continue
        print_class(g.resource(c))

    if otherprops:
        print("# Any")
        for p in sorted(otherprops):
            print_propsum("   ", g.resource(p), None)


def print_class(c, superclasses=set()):
    if not isinstance(c.identifier, URIRef):
        return

    indent = "    " * len(superclasses)
    subnote = "/ " if superclasses else ""
    superclasses = superclasses | {c}
    otherclasses.discard(c.identifier)
    note = c.value(ABS.marcField) or ""
    if SHOW_EQUIVS:
        note += ", ".join(equiv.qname()
                for equiv in c.objects(OWL.equivalentClass)
                if isinstance(c.identifier, URIRef))

    print(indent + subnote + c.qname() + (" # " + note if note else ""))

    props = sorted(c.subjects(RDFS.domain|SCHEMA.domainIncludes))
    for prop in props:
        #if any(prop.objects(RDFS.subPropertyOf)):
        #    continue
        otherprops.discard(prop.identifier)
        print_propsum(indent + "   ", prop)

        print_subproperties(prop, c, indent + "       ")
    for subc in sorted(c.subjects(RDFS.subClassOf)):
        if subc in superclasses:
            print(indent, "<=", subc.qname())
            continue
        print_class(subc, superclasses)
    if props:
        print()


def print_subproperties(prop, domain, indent):
    for subprop in sorted(prop.subjects(RDFS.subPropertyOf)):
        otherprops.discard(subprop.identifier)
        print_propsum(indent, subprop, domain)
        print_subproperties(subprop, domain, indent + "    ")


def print_propsum(indent, prop, domain=None):
    if isinstance(prop.identifier, BNode):
        return

    lbl = prop.qname()

    if domain:
        subpropdomains = sorted(prop.objects(RDFS.domain|SCHEMA.domainIncludes))
        if subpropdomains and subpropdomains != [domain]:
            lbl += " of " + ", ".join(spd.qname() for spd in subpropdomains)

    ranges = tuple(prop.objects(RDFS.range|SCHEMA.rangeIncludes))
    if ranges:
        lbl += " => " + ", ".join(_fix_bf_range(prop.graph, rc).qname()
                for rc in ranges if isinstance(rc.identifier, URIRef))

    note = prop.value(ABS.marcField) or ""
    if SHOW_EQUIVS:
        note += ", ".join(equiv.qname()
                for equiv in prop.objects(OWL.equivalentProperty)
                if isinstance(prop.identifier, URIRef))
    if note:
        lbl += " # " + note

    print(indent, lbl)


def _ns(g, o):
    return g.qname(o).partition(':')


def _fix_bf_range(g, rc):
    if isinstance(rc, Literal):
        return g.resource(rc.datatype)
    return rc


if __name__ == '__main__':
    from rdflib.util import guess_format
    import argparse

    argp = argparse.ArgumentParser()
    argp.add_argument('-v', '--show-equivalents', action='store_true', default=False)
    argp.add_argument('sources', metavar='SOURCE', nargs='+')
    args = argp.parse_args()

    g = ConjunctiveGraph()
    for src in args.sources:
        fmt = 'json-ld' if src.endswith('.jsonld') else guess_format(src)
        g.parse(src, format=fmt)

    print_vocab(g, args.show_equivalents)
