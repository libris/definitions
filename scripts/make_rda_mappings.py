from rdflib import *
from rdflib.namespace import *
import sys

BF2 = Namespace('http://id.loc.gov/ontologies/bibframe/')

ID = Namespace('https://id.kb.se/rda/')

RDAContentType = URIRef('http://rdaregistry.info/termList/RDAContentType/')
RDAMediaType = URIRef('http://rdaregistry.info/termList/RDAMediaType/')
RDACarrierType = URIRef('http://rdaregistry.info/termList/RDACarrierType/')
RDAIssuanceType = URIRef('http://rdaregistry.info/termList/ModeIssue/')


g2 = Graph()
g2.namespace_manager.bind('owl', OWL)
g2.namespace_manager.bind('bf2', BF2)
g2.namespace_manager.bind('rdacontent', RDAContentType)
g2.namespace_manager.bind('rdamedia', RDAMediaType)
g2.namespace_manager.bind('rdacarrier', RDACarrierType)
g2.namespace_manager.bind('rdaissuance', RDAIssuanceType)
g2.namespace_manager.bind('kbrda', ID)

def make_mappings(rda_type_scheme, rtype):
    data_url = rda_type_scheme[:-1] + '.ttl'
    g = Graph().parse(data_url, format='turtle')
    for s in g.subjects(SKOS.inScheme, rda_type_scheme):
        for p, l in g.preferredLabel(s, 'en'):
            symbol = l.title().replace(' ', '')
            uri = ID[symbol]
            g2.add((uri, RDF.type, OWL.Class))
            g2.add((uri, RDF.type, rtype))
            g2.add((uri, RDFS.subClassOf, rtype)) # TODO: either type or subClassOf...
            g2.add((uri, OWL.sameAs, s))

    return g


content_g = make_mappings(RDAContentType, BF2.Content)

#for content_id in g2.subjects(RDF.type, BF2.Content):
#    symbol = unicode(content_id).rsplit('/', 1)[-1]
#    print symbol, BF2[symbol]

media_g = make_mappings(RDAMediaType, BF2.Media)

carrier_g = make_mappings(RDACarrierType, BF2.Carrier)

for top in carrier_g.objects(RDACarrierType, SKOS.hasTopConcept):
    for top_id in g2.subjects(OWL.sameAs, top):
        break
    assert unicode(top_id).endswith('Carriers')
    #g2.remove((top_id, None, None))
    media_id = URIRef(unicode(top_id).replace('Carriers', ''))
    g2.add((top_id, OWL.sameAs, media_id))
    if (media_id, None, None) in g2:
        for narrower in carrier_g.subjects(SKOS.broader, top):
            for specific_carrier in g2.subjects(OWL.sameAs, narrower):
                g2.add((specific_carrier, RDFS.subClassOf, media_id))

make_mappings(RDAIssuanceType, BF2.Issuance)


g2.serialize(sys.stdout, format='turtle')
