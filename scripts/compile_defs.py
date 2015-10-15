from __future__ import unicode_literals, print_function
from os import makedirs, path as P
import sys
import re
import json
import csv
from glob import glob
from collections import namedtuple, OrderedDict
from rdflib import Graph, URIRef, Namespace, RDF, RDFS, OWL
from rdflib.namespace import SKOS, DCTERMS
from rdflib_jsonld.serializer import from_rdf


scriptpath = lambda pth: P.join(P.dirname(__file__), pth)


BASE = "http://id.kb.se/"


# TODO:
# - use the same context for all datasets (no @language or only use @container: @language)
# - explicitly link each record to it's parent dataset record
# - explicitly link each record to its logical source (or just the parent dataset record?)
# - do not add 'quoted' here but in loader (see TODO below)

datasets = {}
def dataset(func):
    datasets[func.__name__] = func
    return func


@dataset
def terms():
    source = Graph()
    #./datatools/scripts/vocab-from-marcframe.py
    #           ext-libris/src/main/resources/marcframe.json
    #           datatools/def/terms.ttl
    #           bibframe.ttl schema_org_rdfa.ttl dcterms.rdfs bibo.owl dbpedia_ontology.ttl
    for part in [scriptpath('../def/terms.ttl')]:
        source.parse(part, format='turtle')
    return "/def/terms/", to_jsonld(source, "owl", {"@base": BASE})


#@dataset
#def datasets():
#    source = Graph().parse(scriptpath('../def/index.ttl'), format='turtle')
#    return to_jsonld(source, None, { "@language": "sv"})


@dataset
def schemes():
    source = Graph().parse(scriptpath('../def/schemes.ttl'), format='turtle')
    return "/scheme/", to_jsonld(source, "skos", {"@base": BASE, "@language": "sv"})


@dataset
def relators():
    source = cached_rdf('http://id.loc.gov/vocabulary/relators')
    source = filter_graph(source, (RDF, RDFS, OWL, SKOS, DCTERMS),
            oftype=OWL.ObjectProperty)

    data = to_jsonld(source, "owl", {"@base": BASE})

    extend(data, 'funktionskoder.tsv', 'sv',
            term_source='label_en', iri_template="/relator/{term}",
            addtype='ObjectProperty',
            relation='equivalentProperty')

    return "/relator/", data


@dataset
def languages():
    source = cached_rdf('http://id.loc.gov/vocabulary/iso639-2')

    ISO639_1Lang = URIRef("http://id.loc.gov/vocabulary/iso639-1/iso639-1_Language")

    items = {}

    code_pairs = {
        unicode(lang_concept.value(SKOS.notation)): (lang_concept, None)
        for lang_concept in source.resource(SKOS.Concept).subjects(RDF.type)
    }

    extras = load_data(scriptpath('../source/spraakkoder.tsv'))

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

            langdef = deref(lang_concept.identifier)
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


@dataset
def countries():
    source = cached_rdf('http://id.loc.gov/vocabulary/countries')
    source = filter_graph(source, (RDF, RDFS, OWL, SKOS, DCTERMS),
            oftype=SKOS.Concept)

    SDO = Namespace("http://schema.org/")

    for concept in source.resource(SKOS.Concept).subjects(RDF.type):
        concept.remove(RDF.type, None)
        concept.add(RDF.type, SDO.Country)

    data = to_jsonld(source, "skos", {"@base": BASE, "@language": "sv"})

    extend(data, 'landskoder.tsv', 'sv',
            iri_template="/country/{notation}",
            relation='exactMatch')

    return "/country/", data


@dataset
def nationalities():
    source = scriptpath('../source/nationalitetskoder.tsv')
    items = load_data(source, encoding='latin-1')
    for code, item in items.items():
        item['@id'] = "/nationality/%s" % code
        item['@type'] = 'Nationality'
        item['prefLabel'] = item.pop('prefLabel_sv')
    data = {"@graph": items.values()}
    return "/nationality/", data


@dataset
def enums():
    data = load_data(scriptpath('../source/enums.jsonld'))
    return "/def/enum/", {
            '@context': data['@context'],
            '@graph': data['enumDefs'].values()
        }


##
# Data shape utils

def filter_graph(source, propspaces, oftype=None):
    propspaces = tuple(map(unicode, propspaces))
    okspace = lambda t: any(t.startswith(ns) for ns in propspaces)
    selected = set(source[:RDF.type:oftype]) if oftype else None

    graph = Graph()
    for s, p, o in source:
        if selected and s not in selected:
            continue
        if not okspace(p) or p == RDF.type and oftype and o != oftype:
            continue
        graph.add((s, p, o))

    return graph


def extend(data, extradata, lang, keys=('label', 'prefLabel', 'comment'),
        term_source=None, iri_template=None, addtype=None, relation=None,
        key_term='notation'):
    fpath = scriptpath('../source/%s' % extradata)
    extras = load_data(fpath)
    index = {node[key_term]: node for node in data['@graph']}
    for key, item in extras.items():
        iri = None
        if iri_template:
            term = item.pop('term', None)
            if not term and term_source:
                term = to_camel_case(item[term_source])
            if term:
                iri = iri_template.format(term=term)
        node = index.get(key)
        if not node:
            if iri:
                node = index[key] = {}
                if addtype:
                    node['@type'] = addtype
                node[key_term] = key
            else:
                continue
        for key in keys:
            item_key = "%s_%s" % (key, lang) if lang else key
            if item_key in item:
                node[key] = item[item_key]
        if not iri and iri_template:
            iri = iri_template.format(**node)
        if iri:
            node['@id'], orig_iri = iri, node.get('@id')
            if relation and orig_iri:
                node[relation] = orig_iri

def to_camel_case(label):
    return "".join((s[0].upper() if i else s[0].lower()) + s[1:]
            for (i, s) in enumerate(re.split(r'[\s,.-]', label)) if s)


def to_jsonld(source, contextref, contextobj=None):
    contextpath = scriptpath("../sys/context/%s.jsonld" % contextref)
    contexturi = "../sys/context/%s.jsonld" % contextref
    context = [contextpath, contextobj] if contextobj else contextpath
    data = from_rdf(source, context_data=context)
    data['@context'] = [contexturi, contextobj] if contextobj else contexturi

    # customize to a convenient shape (within the bounds of JSON-LD)
    base = contextobj.get('@base')
    to_embed = {}
    refs = {}
    for node in data['@graph']:
        nodeid = node['@id']
        if base and nodeid.startswith(base):
            node['@id'] = nodeid[len(base)-1:]
        elif nodeid.startswith('_:'):
            to_embed[nodeid] = node
            continue
    for idref, obj in refs.items():
        obj.update(to_embed[idref])
        #del obj['@id']

    return data


def partition_dataset(base, data):
    resultset = OrderedDict()
    for node in data.pop('@graph'):
        nodeid = node['@id']
        # TODO: Absence caused by mismatch between external id and local mapping
        if not nodeid:
            print("Missing id for:", node)
            continue
        if not nodeid.startswith(base):
            print("Missing mapping of <%s> under base <%s>" % (nodeid, base))
            continue
        rel_path = nodeid[1:]
        resultset[rel_path] = node
    return data.get('@context'), resultset


def _to_desc_form(node, dataset=None, source=None):
    item = node.pop('about', None)
    if item:
        node['about'] = {'@id': item['@id']}
    if dataset:
        node['inDataset'] = dataset
    if source:
        node['wasDerivedFrom'] = source
    descriptions = {'entry': node}
    if item:
        descriptions['items'] = [item]
    quoted = []
    for vs in node.values():
        vs = vs if isinstance(vs, list) else [vs]
        for v in vs:
            if isinstance(v, dict) and '@id' in v:
                quoted.append({'@graph': {'@id': v['@id']}})
    # TODO: move addition of 'quoted' objects to (decorated) storage?
    # ... actually move this entire 'descriptions' structure...
    # ... let storage accept a single resource or named graph
    # (with optional, "nested" quotes), and extract links (and sameAs)
    if quoted:
        descriptions.setdefault('quoted', []).extend(quoted)

    return {'descriptions': descriptions}


##
# Data load utils

def load_data(fpath, encoding='utf-8'):
    csv_dialect = ('excel' if fpath.endswith('.csv')
            else 'excel-tab' if fpath.endswith('.tsv')
            else None)
    if csv_dialect:
        with open(fpath, 'rb') as fp:
            reader = csv.DictReader(fp, dialect=csv_dialect)
            return {item.pop('code'):
                        {k: v.decode(encoding).strip()
                            for (k, v) in item.items() if v}
                    for item in reader}
    else:
        with open(fpath) as fp:
            return json.load(fp)


CACHEDIR = None

def deref(iri):
    return cached_rdf(iri).resource(iri)

def cached_rdf(fpath):
    source = Graph()
    http = 'http://'
    if not CACHEDIR:
        print("No cache directory configured", file=sys.stderr)
    elif fpath.startswith(http):
        remotepath = fpath
        fpath = P.join(CACHEDIR, remotepath[len(http):]) + '.ttl'
        if not P.isfile(fpath):
            _ensure_fpath(fpath)
            source.parse(remotepath)
            source.serialize(fpath, format='turtle')
            return source
        else:
            return source.parse(fpath, format='turtle')
    return source.parse(fpath)


##
# Data write utils

def compile_defs(names, outdir, cache, onefile=False):
    global CACHEDIR
    if cache:
        CACHEDIR = cache
    if onefile:
        union_fpath = P.join(outdir, 'definitions.jsonld.lines')
        _ensure_fpath(union_fpath)
        union_file = open(union_fpath, 'w')
    else:
        union_file = None
    try:
        _compile_defs_files(names, outdir, union_file)
    finally:
        if union_file:
            union_file.close()

def _compile_defs_files(names, outdir, union_file):
    for name in names:
        if len(names) > 1:
            print("Dataset:", name)
        basepath, data = datasets[name]()
        _output(name, data, outdir)
        context, resultset = partition_dataset(basepath, data)
        for key, node in resultset.items():
            # TODO: add source
            node = _to_desc_form(node, '/dataset/%s' % name, source=None)
            if union_file:
                print(json.dumps(node), file=union_file)
            _output(key, node, outdir)
        print()

def _output(name, node, outdir):
    result = _serialize(node)
    if result:
        outfile = P.join(outdir, "%s.jsonld" % name)
        print("Writing:", outfile)
        _ensure_fpath(outfile)
        with open(outfile, 'w') as fp:
            fp.write(result)
    else:
        print("No data")

def _serialize(data):
    if isinstance(data, (list, dict)):
        data = json.dumps(data, indent=2, sort_keys=True,
                separators=(',', ': '), ensure_ascii=False)
    if isinstance(data, unicode):
        data = data.encode('utf-8')
    return data

def _ensure_fpath(fpath):
    fdir = P.dirname(fpath)
    if not P.isdir(fdir):
        makedirs(fdir)


if __name__ == '__main__':
    import argparse

    argp = argparse.ArgumentParser(
            description="Available datasets: " + ", ".join(datasets),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg = argp.add_argument
    arg('-o', '--outdir', type=str, default="build", help="Output directory")
    arg('-c', '--cache', type=str, default="cache", help="Cache directory")
    arg('-l', '--lines', action='store_true',
            help="Output a single file with one JSON-LD document per line")
    arg('datasets', metavar='DATASET', nargs='*')

    args = argp.parse_args()
    if not args.datasets and args.outdir:
        args.datasets = list(datasets)

    compile_defs(args.datasets, args.outdir, args.cache, onefile=args.lines)
