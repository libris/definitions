from __future__ import unicode_literals, print_function, division
if str is bytes:
    str = unicode
from functools import reduce
from rdflib import *

# Monkey!
_orig_qname = Graph.qname
def _qname(self, uri):
    try:
        v = _orig_qname(self, uri)
        return ':%s' % v if ':' not in v else v
    except:
        return uri.n3()
Graph.qname = _qname


ABS = Namespace("http://bibframe.org/model-abstract/")
SCHEMA = Namespace("http://schema.org/")
PTG = Namespace("http://protege.stanford.edu/plugins/owl/protege#")

assert str(SDO) == "https://schema.org/"

DOMAIN = RDFS.domain | SCHEMA.domainIncludes | SDO.domainIncludes
RANGE = RDFS.range | SCHEMA.rangeIncludes | SDO.rangeIncludes


def print_vocab(g, show_equivs=False, only_classes=False):
    global otherclasses, otherprops, SHOW_EQUIVS, ONLY_CLASSES
    SHOW_EQUIVS = show_equivs
    ONLY_CLASSES = only_classes

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
        ns = str(term)[:-len(name)]
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

    if c.value(PTG.abstract):
        note += (" " if note else "") + "[ABSTRACT]"

    if SHOW_EQUIVS:
        equivs = ", ".join(equiv.qname()
                for equiv in c.objects(OWL.equivalentClass)
                if isinstance(c.identifier, URIRef))
        if equivs:
            note += (" " if note else "") + "== " + equivs

    other_types = [other.qname() for other in c.objects(RDF.type)
                   if other.identifier not in {OWL.Class, RDFS.Class}]

    other_type_decl = (" a " + ", ".join(other_types)) if other_types else ""
    note_comment = " # " + note if note else ""
    print(indent + subnote + c.qname() + other_type_decl + note_comment)

    # Properties
    props = sorted(c.subjects(DOMAIN))
    for prop in props:
        #if any(prop.objects(RDFS.subPropertyOf)):
        #    continue
        otherprops.discard(prop.identifier)
        print_propsum(indent + "   ", prop)

        print_subproperties(prop, c, indent + "       ")

    # Restrictions
    restrictions_by_property = {}

    for subc in sorted(c.objects(RDFS.subClassOf)):
        if any(t for t in subc.objects(RDF.type) if t.identifier == OWL.Restriction):
            propname = subc.value(OWL.onProperty).qname()
            restrs = restrictions_by_property.setdefault(propname, [])

            all_from = ["All(%s)" % repr_class(rc) for rc in
                        subc.objects(OWL.allValuesFrom)]
            if all_from:
                restrs.append(all_from)

            some_from = ["Some(%s)" % rc.qname() for rc in
                         subc.objects(OWL.someValuesFrom)]
            if some_from:
                restrs.append(some_from)

            if subc.value(OWL.cardinality):
                restrs.append([str(subc.value(OWL.cardinality))])

            if subc.value(OWL.minCardinality):
                restrs.append([f"{(subc.value(OWL.minCardinality))}.."])

            if subc.value(OWL.maxCardinality):
                restrs.append([f"..{(subc.value(OWL.maxCardinality))}"])

    for propname, restrs in restrictions_by_property.items():
        restr_repr = " & ".join(sorted(", ".join(restr) for restr in restrs))
        print(indent + "   ", "@", propname, "=>", restr_repr)

    # Instances
    for inst in sorted(c.subjects(RDF.type)):
        if isinstance(inst.identifier, URIRef):
            print(indent + "   ", "::", inst.qname())

    # Subclass Tree
    for subc in sorted(c.subjects(RDFS.subClassOf)):
        if subc in superclasses:
            print(indent + "   ", "<=", subc.qname())
            continue
        print_class(subc, superclasses)

    if props:
        print()


def print_subproperties(prop, domain, indent):
    if ONLY_CLASSES:
        return
    for subprop in sorted(prop.subjects(RDFS.subPropertyOf)):
        otherprops.discard(subprop.identifier)
        print_propsum(indent, subprop, domain)
        print_subproperties(subprop, domain, indent + "    ")


def print_propsum(indent, prop, domain=None):
    if ONLY_CLASSES:
        return

    if isinstance(prop.identifier, BNode):
        return

    lbl = prop.qname()

    if domain:
        subpropdomains = sorted(prop.objects(DOMAIN))
        if subpropdomains and subpropdomains != [domain]:
            lbl += " of " + ", ".join(spd.qname() for spd in subpropdomains)

    ranges = tuple(prop.objects(RANGE))
    if ranges:
        lbl += " => " + ", ".join(
            repr_class(_fix_bf_range(prop.graph, rc))
            for rc in ranges
        )

    note = prop.value(ABS.marcField) or ""
    if SHOW_EQUIVS:
        equivs = ", ".join(equiv.qname()
                for equiv in prop.objects(OWL.equivalentProperty)
                if isinstance(prop.identifier, URIRef))
        if equivs:
            note += (" " if note else "") + "== " + equivs
    if note:
        lbl += " # " + note

    print(indent, lbl)


def repr_class(rc):
    if rc.value(OWL.unionOf):
        return ' | '.join(repr_class(x) for x in rc.value(OWL.unionOf).items())
    return rc.qname()


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
    argp.add_argument('-t', '--only-classes', action='store_true', default=False)
    argp.add_argument('sources', metavar='SOURCE', nargs='+')
    argp.add_argument('-c', '--context', metavar='CONTEXT')
    args = argp.parse_args()

    g = ConjunctiveGraph()
    for src in args.sources:
        if src.endswith('.jsonld'):
            g.parse(src, format='json-ld', context=args.context)
        else:
            g.parse(src, format=guess_format(src))

    print_vocab(g, args.show_equivalents, args.only_classes)
