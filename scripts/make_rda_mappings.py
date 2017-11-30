from rdflib import *
from rdflib.namespace import *


BF2 = Namespace('http://id.loc.gov/ontologies/bibframe/')
MADSRDF = Namespace('http://www.loc.gov/mads/rdf/v1#')

ID = Namespace('https://id.kb.se/rda/')

RDAContentType = URIRef('http://rdaregistry.info/termList/RDAContentType')
LCContentType = URIRef('http://id.loc.gov/vocabulary/contentTypes')

RDAMediaType = URIRef('http://rdaregistry.info/termList/RDAMediaType')
LCMediaType = URIRef('http://id.loc.gov/vocabulary/mediaTypes')

RDACarrierType = URIRef('http://rdaregistry.info/termList/RDACarrierType')
LCCarrierType = URIRef('http://id.loc.gov/vocabulary/carriers')

RDAIssuanceType = URIRef('http://rdaregistry.info/termList/ModeIssue')
LCIssuanceType = URIRef('http://id.loc.gov/vocabulary/issuance')

LANGS = ('en', 'sv')


def make_rda_mappings():
    g2 = Graph()
    g2.namespace_manager.bind('owl', OWL)
    g2.namespace_manager.bind('bf2', BF2)
    g2.namespace_manager.bind('rdacontent', RDAContentType)
    g2.namespace_manager.bind('rdamedia', RDAMediaType)
    g2.namespace_manager.bind('rdacarrier', RDACarrierType)
    g2.namespace_manager.bind('rdaissuance', RDAIssuanceType)
    g2.namespace_manager.bind('kbrda', ID)

    content_g = _make_mappings(g2, RDAContentType, LCContentType, BF2.Content)

    media_g = _make_mappings(g2, RDAMediaType, LCMediaType, BF2.Media)

    carrier_g = _make_mappings(g2, RDACarrierType, LCCarrierType, BF2.Carrier)

    for top in carrier_g.objects(RDACarrierType, SKOS.hasTopConcept):
        for top_id in g2.subjects(OWL.sameAs, top):
            break
        assert unicode(top_id).endswith('Carriers(Deprecated)'), top_id
        g2.remove((top_id, None, None))
        # Redundant now; see comment just below.
        media_id = URIRef(unicode(top_id).replace('Carriers(Deprecated)', ''))
        if unicode(media_id).endswith('ProjectedImage') and (media_id, None, None) not in g2:
            media_id = URIRef(unicode(media_id).replace('ProjectedImage', 'Projected'))
        #g2.add((top_id, OWL.sameAs, media_id))
        # NOTE: Before deprecation in RDA, it was possible to follow broader links
        # from specific carriers to base carrier terms which were equatable to one
        # of the media terms. These broader links are now missing. The loop below
        # thus doesn't execute anymore (no broader link is present in the RDA
        # source data.)
        # (e.g. kbrda:ComputerChipCartridge rdfs:subClassOf kbrda:Computer .)
        if (media_id, None, None) in g2:
            for narrower in carrier_g.subjects(SKOS.broader, top):
                for specific_carrier in g2.subjects(OWL.sameAs, narrower):
                    g2.add((specific_carrier, RDFS.subClassOf, media_id))

    # Just a crude string matching to get the carrier < media relations...
    carriers = set(g2.subjects(RDF.type, BF2.Carrier))
    medias = set(unicode(media) for media in g2.subjects(RDF.type, BF2.Media))
    for media in medias:
        for carrier in carriers:
            if unicode(carrier).startswith(media):
                g2.add((carrier, RDFS.subClassOf, URIRef(media)))

    _make_mappings(g2, RDAIssuanceType, LCIssuanceType, BF2.Issuance)

    return g2


def _make_mappings(g2, rda_type_scheme, lc_type_scheme, rtype):
    data_url = str(rda_type_scheme) + '.ttl'
    g = Graph().parse(data_url, format='turtle')
    g.parse(lc_type_scheme)
    for s in g.subjects(SKOS.inScheme, rda_type_scheme):
        for p, preflabel_en in g.preferredLabel(s, 'en'):
            symbol = preflabel_en.title().replace(' ', '')

            uri = ID[symbol]
            g2.add((uri, RDF.type, OWL.Class))
            g2.add((uri, RDF.type, rtype))

            # TODO: either type or subClassOf...
            # g2.add((uri, RDFS.subClassOf, rtype))

            g2.add((uri, OWL.sameAs, s))
            for p2 in (SKOS.definition, SKOS.prefLabel, SKOS.scopeNote):
                for l in g.objects(s, p2):
                    if l.language in LANGS:
                        g2.add((uri, p2, l))

            for lc_def in g.subjects(SKOS.prefLabel, Literal(unicode(preflabel_en))):
                if (lc_def, RDF.type, MADSRDF.Authority) in g:
                    lc_code = unicode(lc_def).rsplit('/', 1)[-1]
                    g2.add((uri, BF2.code, Literal(lc_code)))
                    g2.add((uri, OWL.sameAs, lc_def))

    return g


if __name__ == '__main__':
    import sys

    g = make_rda_mappings()
    g.serialize(sys.stdout, format='turtle')
