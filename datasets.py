# -*- coding: UTF-8 -*-
from __future__ import unicode_literals, print_function
import os.path as Path
from glob import glob
from rdflib import Graph, URIRef, Namespace, RDF, RDFS, OWL
from rdflib.namespace import SKOS, DCTERMS
from util.datacompiler import Compiler, filter_graph, extend, load_data, to_jsonld
from util.contextmaker import DEFAULT_NS_PREF_ORDER, make_context, add_overlay


# TODO:
# - use the same context for all datasets (no @language or only use @container: @language)
# - explicitly link each record to it's parent dataset record
# - explicitly link each record to its logical source (or just the parent dataset record?)
# - do not add 'quoted' here but in loader (see TODO below)


BASE = "http://id.kb.se/"

scriptpath = lambda pth: Path.join(Path.dirname(__file__), pth)

compiler = Compiler()

def contextref(name):
    path = "sys/context/%s.jsonld" % name
    return "../" + path, scriptpath(path)

# NOTE: this step is currently part of the source maintenance, used to sync
# with "unstable" marcframe mappings. I plan to inverse parts of this flow
# to generate token-maps (used by marcframe processors) from these vocab
# and enum sources instead.
#def prep_vocab_data(): pass
#    python scripts/vocab-from-marcframe.py
#           ext-libris/src/main/resources/marcframe.json build/vocab.ttl
#           > build/vocab-generated-source-1.ttl


@compiler.dataset
def vocab():
    source = Graph()

    for part in glob(scriptpath('source/vocab/*.ttl')):
        source.parse(part, format='turtle')

    with open(scriptpath('source/vocab/update.rq')) as fp:
        source.update(fp.read())

    lib_context = make_context(source, BASE + 'vocab/', DEFAULT_NS_PREF_ORDER)
    add_overlay(lib_context, load_data(scriptpath('source/vocab-overlay.jsonld')))
    compiler.write(lib_context, 'lib-context')

    return "/vocab/", to_jsonld(source, contextref("owl"), {"@base": BASE})


@compiler.dataset
def enums():
    data = load_data(scriptpath('source/enums.jsonld'))
    return "/enum/", {
            '@context': data['@context'],
            '@graph': data.get('@graph') or data['enumDefs'].values()
        }


#@compiler.dataset
#def datasets():
#    source = Graph().parse(scriptpath('source/index.ttl'), format='turtle')
#    return to_jsonld(source, (None, None), { "@language": "sv"})


@compiler.dataset
def schemes():
    source = Graph().parse(scriptpath('source/schemes.ttl'), format='turtle')
    return "/scheme/", to_jsonld(source, contextref("skos"),
            {"@base": BASE, "@language": "sv"})


@compiler.dataset
def relators():
    source = compiler.cached_rdf('http://id.loc.gov/vocabulary/relators')
    source = filter_graph(source, (RDF, RDFS, OWL, SKOS, DCTERMS),
            oftype=OWL.ObjectProperty)

    data = to_jsonld(source, contextref("owl"), {"@base": BASE})

    extend(data, scriptpath('source/funktionskoder.tsv'), 'sv',
            term_source='label_en', iri_template="/relator/{term}",
            addtype='ObjectProperty',
            relation='equivalentProperty')

    return "/relator/", data


@compiler.dataset
def languages():
    source = compiler.cached_rdf('http://id.loc.gov/vocabulary/iso639-2')

    ISO639_1Lang = URIRef("http://id.loc.gov/vocabulary/iso639-1/iso639-1_Language")

    items = {}

    code_pairs = {
        unicode(lang_concept.value(SKOS.notation)): (lang_concept, None)
        for lang_concept in source.resource(SKOS.Concept).subjects(RDF.type)
    }

    extras = load_data(scriptpath('source/spraakkoder.tsv'))

    for code, extra in extras.items():
        pair = code_pairs.get(code)
        lang_concept = pair[0] if pair else None
        code_pairs[code] = (lang_concept, extra)

    for code, (lang_concept, extra) in code_pairs.items():
        node = items[code] = {
            '@id': "/language/%s" % code,
            '@type': 'Language',
            'notation': code,
            'langCode': code
        }

        if lang_concept:
            node['matches'] = lang_concept.identifier

            langdef = compiler.deref(lang_concept.identifier)
            for variant in langdef[SKOS.exactMatch]:
                if variant.graph[variant.identifier : RDF.type : ISO639_1Lang]:
                    iso639_1 = variant.value(SKOS.notation)
                    node['langTag'] = iso639_1

            for label in lang_concept[SKOS.prefLabel]:
                if label.language == 'en':
                    node['prefLabel_en'] = unicode(label)
                    break

        if extra:
            node['prefLabel'] = extra['prefLabel_sv']

    data = {
        '@context': [
            "/sys/context/skos.jsonld",
            {"@base": BASE, "@language": "sv"}
        ],
        '@graph': items.values()
    }

    return "/language/", data


@compiler.dataset
def countries():
    source = compiler.cached_rdf('http://id.loc.gov/vocabulary/countries')
    source = filter_graph(source, (RDF, RDFS, OWL, SKOS, DCTERMS),
            oftype=SKOS.Concept)

    SDO = Namespace("http://schema.org/")

    for concept in source.resource(SKOS.Concept).subjects(RDF.type):
        concept.remove(RDF.type, None)
        concept.add(RDF.type, SDO.Country)

    data = to_jsonld(source, contextref("skos"), {"@base": BASE, "@language": "sv"})

    extend(data, scriptpath('source/landskoder.tsv'), 'sv',
            iri_template="/country/{notation}",
            relation='exactMatch')

    return "/country/", data


@compiler.dataset
def nationalities():
    source = scriptpath('source/nationalitetskoder.tsv')
    items = load_data(source, encoding='latin-1')
    for code, item in items.items():
        item['@id'] = "/nationality/%s" % code
        item['@type'] = 'Nationality'
        item['prefLabel'] = item.pop('prefLabel_sv')
    data = {"@graph": items.values()}
    return "/nationality/", data


if __name__ == '__main__':
    import argparse

    argp = argparse.ArgumentParser(
            description="Available datasets: " + ", ".join(compiler.datasets),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg = argp.add_argument
    arg('-o', '--outdir', type=str, default="build", help="Output directory")
    arg('-c', '--cache', type=str, default="cache", help="Cache directory")
    arg('-l', '--lines', action='store_true',
            help="Output a single file with one JSON-LD document per line")
    arg('datasets', metavar='DATASET', nargs='*')

    args = argp.parse_args()
    if not args.datasets and args.outdir:
        args.datasets = list(compiler.datasets)

    compiler.configure(args.outdir, args.cache, onefile=args.lines)
    compiler.run(args.datasets)
