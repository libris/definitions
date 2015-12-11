# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
from rdflib import *
from rdflib.resource import Resource


L = Namespace("http://w3id.org/libris/logic/")

def add_magic_properties(vocab, data):
    for rclass, mprop in vocab.resource(L.magicProperty).subject_objects():
        #print rclass.qname()
        for s in data.resource(rclass.identifier).subjects(RDF.type):
            result_prop = mprop.value(L.resultProperty).identifier
            use_link = mprop.value(L.useLink)
            value = expand_template(
                    s.value(use_link.identifier) if use_link else s,
                    mprop.value(L.template))
            #print "<%s>" % s, value
            s.add(result_prop, Literal(value))

def expand_template(s, tplt):
    if isinstance(tplt, Resource):
        if any(tplt.objects(RDF.first)):
            parts = list(tplt.items())
            first = parts[0]
            ctrl = first.identifier if isinstance(first, Resource) else None
            if ctrl == L['if']:
                if expand_template(s, parts[1]):
                    return expand_template(s, parts[2])
                elif len(parts) > 3:
                    return expand_template(s, parts[3])
            elif ctrl == L['and']:
                return all(expand_template(s, part) for part in parts[1:])
            elif ctrl == L['or']:
                for part in parts[1:]:
                    v = expand_template(s, part)
                    if v:
                        return v
            else:
                join = ""
                if ctrl == L['join']:
                    join, parts = parts[1], parts[2:]
                return join.join(filter(None, (expand_template(s, part) for part in parts)))
        else:
            return s.value(tplt.identifier)
    else:
        return tplt


if __name__ == '__main__':
    import sys
    from os import path as P
    from rdflib.util import guess_format

    args = sys.argv[:]
    script = args.pop(0)
    fpath = args.pop(0) if args else P.join(P.dirname(script), "../def/terms.ttl")
    vocab = Graph().parse(fpath, format=guess_format(fpath))

    T = Namespace("http://libris.kb.se/def/terms#")
    BASE = Namespace("http://example.org/")

    data = Graph().parse(data="""
            prefix : <{T}>
            base <{BASE}>

            </person/someone/entry> a :PersonTerm;
                :focus [ a :Person;
                        :name "Some One";
                        :personTitle "X" ] .

            </person/somebody/entry> a :PersonTerm;
                :focus [ a :Person;
                        :name "Some Body";
                        :givenName "Some"; :familyName "Body";
                        :birthYear "1901" ] .

            </person/someother/entry> a :PersonTerm;
                :focus [ a :Person;
                        :givenName "Some"; :familyName "Other";
                        :numeration "XI"; :personTitle "Y";
                        :birthYear "1902" ] .

            </person/nobody/entry> a :PersonTerm;
                :focus [ a :Person;
                        :givenName "No"; :familyName "Body";
                        :birthYear "1903"; :deathYear "2001" ] .

            </person/noother/entry> a :PersonTerm;
                :focus [ a :Person;
                        :givenName "No"; :familyName "Other";
                        :personTitle "Z";
                        :deathYear "2001" ] .

    """.format(**vars()), format='turtle')

    add_magic_properties(vocab, data)

    assert len(Graph().parse(data="""
            prefix : <{T}>
            base <{BASE}>
            </person/someone/entry> :prefLabel "Some One (X)" .
            </person/somebody/entry> :prefLabel "Body, Some 1901-" .
            </person/someother/entry> :prefLabel "Other, Some XI (Y) 1902-" .
            </person/nobody/entry> :prefLabel "Body, No 1903-2001" .
            </person/noother/entry> :prefLabel "Other, No (Z) -2001" .
            """.format(**vars()), format='turtle') - data) == 0

    data.serialize(sys.stdout, format='turtle')

