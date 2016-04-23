from __future__ import unicode_literals, print_function, division
from rdflib import *


ABS = Namespace("http://bibframe.org/model-abstract/")

def print_vocab(g):
    global otherclasses, otherprops
    otherclasses = reduce(set.__or__, (set(g.subjects(RDF.type, t))
        for t in [RDFS.Class, OWL.Class]))
    otherprops = reduce(set.__or__, (set(g.subjects(RDF.type, t))
        for t in [RDF.Property, OWL.ObjectProperty, OWL.DatatypeProperty]))
    print_class(g.resource(RDFS.Resource))
    for c in sorted(otherclasses):
        if any(o for o in g.objects(c, RDFS.subClassOf)
                if o != RDFS.Resource
                and not isinstance(o, BNode)
                and not _ns(g, c) == _ns(g, o)):
            continue
        print_class(g.resource(c))
    if otherprops:
        print("_:Other")
        for p in sorted(otherprops):
            print_propsum(g.resource(p), None, "   ")

def print_class(c, superclasses=set()):
    indent = "    " * len(superclasses)
    subnote = "/ " if superclasses else ""
    superclasses = superclasses | {c}
    otherclasses.discard(c.identifier)
    marc = c.value(ABS.marcField)
    print(indent + subnote + c.qname() + (" # " + marc if marc else ""))
    props = sorted(c.subjects(RDFS.domain))
    for prop in props:
        #if any(prop.objects(RDFS.subPropertyOf)):
        #    continue
        otherprops.discard(prop.identifier)
        lbl = prop.qname()
        ranges = tuple(prop.objects(RDFS.range))
        if ranges:
            lbl += " => " + ", ".join(_fix_bf_range(c.graph, rc).qname()
                    for rc in ranges)
        marc = prop.value(ABS.marcField)
        if marc:
            lbl += " # " + marc
        print(indent + "    " + lbl)
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
        print_propsum(subprop, domain, indent)
        print_subproperties(subprop, domain, indent + "    ")

def print_propsum(subprop, domain, indent):
    lbl = subprop.qname()
    subpropdomains = sorted(subprop.objects(RDFS.domain))
    if subpropdomains and subpropdomains != [domain]:
        lbl += " of " + ", ".join(spd.qname() for spd in subpropdomains)
    marc = subprop.value(ABS.marcField)
    if marc:
        lbl += " # " + marc
    print(indent, lbl)

def _ns(g, o):
    return g.qname(o).partition(':')

def _fix_bf_range(g, rc):
    if isinstance(rc, Literal):
        return g.resource(rc.datatype)
    return rc


if __name__ == '__main__':
    from sys import argv
    g = Graph()
    for src in argv[1:]:
        g.parse(src, format="turtle")
    print_vocab(g)
