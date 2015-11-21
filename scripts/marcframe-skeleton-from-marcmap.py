from __future__ import unicode_literals, print_function
from collections import OrderedDict, namedtuple
import json
import sys


MARC_TYPES = 'bib', 'auth', 'hold'

content_name_map = {
    'Books': 'Text',
    'Book': 'Text',
    'Maps': 'Cartography',
    'Map': 'Cartography',
    'Music': 'Audio',
    'Serials': 'Serial',
    'Computer': 'Digital'
}

carrier_name_map = {
    'ComputerFile': 'Electronic',
    'ProjectedGraphic': 'ProjectedImage',
    'NonprojectedGraphic': 'StillImage',
    'MotionPicture': 'MovingImage',
}

propname_map = {
    'item': 'additionalCarrierType',
    'format': 'additionalType',
    'type': 'holdingType',
}

fixprop_typerefs = {
    '000': [
        'typeOfRecord',
        'bibLevel',
    ],
    '007': [
        'mapMaterial',
        'computerMaterial',
        'globeMaterial',
        'tacMaterial',
        'projGraphMaterial',
        'microformMaterial',
        'nonProjMaterial',
        'motionPicMaterial',
        'kitMaterial',
        'notatedMusicMaterial',
        'remoteSensImageMaterial', #'soundKindOfMaterial',
        'soundMaterial',
        'textMaterial',
        'videoMaterial'
    ],
    '008': [
        'booksContents', #'booksItem', 'booksLiteraryForm' (subjectref), 'booksBiography',
        'computerTypeOfFile',
            #'mapsItem', #'mapsMaterial', # TODO: c.f. 007.mapMaterial
        #'mixedItem',
        #'musicItem', #'musicMatter', 'musicTransposition',
        'serialsTypeOfSerial', #'serialsItem',
        'visualMaterial', #'visualItem',
    ],
    '006': [
        'booksContents',
        'computerTypeOfFile',
        'serialsTypeOfSerial',
        'visualMaterial',
    ]
}
# TODO: literaryForm => genre (same as 655)


common_columns = {
    '008': {"[0:6]", "[6:7]", "[7:11]", "[11:15]", "[15:18]", "[35:38]", "[38:39]", "[39:40]"}
}

# TODO: make and use separate BOOLEAN-map for non-computable boolean types
canonical_coll_id_map = {
  "ReproductionType": ["ComputerFileAspectType", "SoundAspectType", "MicroformAspectType", "MotionPicAspectType", "ProjGraphAspectType", "NonProjAspectType", "GlobeAspectType", "MapAspectType"],
  "AudienceType": ["ComputerAudienceType", "MusicAudienceType", "VisualAudienceType", "BooksAudienceType"],
  "FilmBaseType": ["MotionPicBaseType", "MicroformBaseType"],
  "ColorType": ["MapColorType", "GlobeColorType"],
  "HeadingType": ["BOOLEAN", "HeadingSeriesType", "HeadingMainType", "HeadingSubjectType"],
  "IndexType": ["MapsIndexType", "BooksIndexType"],
  "ItemType": ["SerialsItemType", "VisualItemType", "MusicItemType", "MapsItemType", "MixedItemType"],
  "MediumType": ["MotionPicMediumType", "ProjGraphMediumType", "VideoMediumType"],
  "PolarityType": ["MicroformPosNegType", "MapPosNegType"],
  "MotionPicConfigurationOrVideoPlaybackType": ["MotionPicConfigurationType", "VideoPlaybackType"],
  "NonProjectedType": ["NonProjSecondaryType", "NonProjPrimaryType"],
  "ColorType": ["ProjGraphColorType", "NonProjColorType"],
  "ReproductionType": ["GlobeReproductionType", "MapReproductionType"],
  "ConferencePublicationType": ["BOOLEAN", "SerialsConfPubType", "BooksConfPubType"],
  "GovernmentPublicationType": ["SerialsGovtPubType", "ComputerGovtPubType", "BooksGovtPubType", "VisualGovtPubType", "MapsGovtPubType"],
  "SoundType": ["ProjGraphSoundType", "MotionPicSoundType", "VideoSoundType"]
}

get_canonical_coll_id = {alias: key
    for key, aliases in canonical_coll_id_map.items()
        for alias in aliases}.get

TOKEN_MAPS = OrderedDict()

ENUM_DEFS = OrderedDict()

#compositionTypeMap = OUT['compositionTypeMap'] = OrderedDict()
#contentTypeMap = OUT['contentTypeMap'] = OrderedDict()

EnumCollection = namedtuple('EnumCollection', 'ref_key, map_key, id, items')

class Continue(Exception): pass


PROCESSED_ENUMS = {}

def build_enums(marc_type):

    enum_map = PROCESSED_ENUMS[marc_type] = {}
    enum_collections = []

    for dfn_ref_key, valuemap in MARCMAP[marc_type]['fixprops'].items():
        enumcoll, tokenmap_key = _make_enumcollection(marc_type, dfn_ref_key, valuemap)
        enum_map[tokenmap_key] = enum_map[enumcoll.map_key] = enumcoll
        enum_collections.append((enumcoll, dfn_ref_key))

    for enumcoll, dfn_ref_key in enum_collections:

        if MAKE_VOCAB:
            coll_def = add_enum_collection_def(enumcoll)

        overwriting = enumcoll.map_key in TOKEN_MAPS
        #if enumcoll.map_key in TOKEN_MAPS: continue
        tokenmap = TOKEN_MAPS.setdefault(enumcoll.map_key, {})

        for key, dfn in enumcoll.items.items():
            try:
                type_id = get_enum_id(key, dfn)
            except Continue:
                continue

            if MAKE_VOCAB and type_id:
                add_enum_def(coll_def['@id'], type_id, dfn_ref_key, dfn, key)

            if overwriting:
                assert tokenmap.get(key, type_id) == type_id, "%s: %s missing in %r" % (
                        key, type_id, tokenmap)

            existing_type_id = tokenmap.get(key, type_id)
            if existing_type_id is not None and existing_type_id != type_id:
                print("tokenMap mismatch in %s for key %s: %s != %s"
                        % (dfn_ref_key, key, type_id, tokenmap[key]), file=sys.stderr)
            else:
                tokenmap[key] = type_id


TMAP_HASHES = {} # to reuse repeated tokenmap

def _make_enumcollection(marc_type, dfn_ref_key, valuemap):
    # TODO: clear out unwanted values *first* (see get_enum_id)
    items = OrderedDict(sorted((k.lower(), v) for k, v in valuemap.items()))
    tokenmap_key = marc_type + '-' + dfn_ref_key
    # reuse repeated tokenmaps
    canonical_tokenmap_key = TMAP_HASHES.setdefault(
            json.dumps(items, sort_keys=True), tokenmap_key)

    coll_id = _make_collection_id(dfn_ref_key)
    first_similar_coll_id = _make_collection_id(canonical_tokenmap_key.rsplit('-')[-1])

    canonical_coll_id = get_canonical_coll_id(coll_id)
    if canonical_coll_id:
        assert coll_id in canonical_coll_id_map[canonical_coll_id]
        assert first_similar_coll_id in canonical_coll_id_map[canonical_coll_id]
    else:
        canonical_coll_id = first_similar_coll_id

    if marc_type != 'bib' and 'bib-'+dfn_ref_key in TMAP_HASHES.values() and not canonical_tokenmap_key.startswith('bib-'):
        # NOTE: avoid conflating coll_def, prepend coll_id with 'Authority' or 'Holding'
        #print(canonical_tokenmap_key, tokenmap_key)
        pfx = {'auth': 'Authority', 'hold': 'Holding'}[marc_type]
        canonical_coll_id = pfx + canonical_coll_id
        coll_id = pfx + coll_id

    if canonical_tokenmap_key != tokenmap_key:
        #print("choosing {} over {}".format(canonical_tokenmap_key, tokenmap_key))
        if MAKE_VOCAB:
            for cid in [coll_id, first_similar_coll_id]:
                if cid == canonical_coll_id:
                    continue
                ENUM_DEFS.setdefault(canonical_coll_id, {"@id": canonical_coll_id}
                        ).setdefault('sameAs', []).append({"@id": cid})

    off_key = _find_boolean_off_key(valuemap)
    # TODO: if off_key, type as boolean and define boolean property (w/o tokenMap)
    #if key == off_key:
    #    print('off key:', key, dfn)
    # TODO: also, detect and type numeric (and possibly numeric range) types

    return EnumCollection(dfn_ref_key, canonical_tokenmap_key, canonical_coll_id, items), tokenmap_key

def _make_collection_id(dfn_ref_key):
    coll_id = dfn_ref_key[0].upper() + dfn_ref_key[1:] + 'Type'
    return coll_id

def get_enum_id(key, dfn):
    if 'id' in dfn:
        # TODO: move id generation from legwcy config code here (to fix at least "'s" => "S")?
        v = dfn['id']
        subname, plural_name = to_name(v)
    else:
        subname = dfn['label_sv']
        if ' [' in subname:
            subname, comment = subname.split(' [', 1)
            if comment[-1] == ']':
                comment = comment[:-1]

        for char, repl in [(' (', '-'), (' ', '_'), ('/', '-')]:
            subname = subname.replace(char, repl)
        for badchar in ',()':
            subname = subname.replace(badchar, '')

    if key in ('_', '|', '||', '|||') and any(t in subname
            for t in ('No', 'Ej', 'Inge', 'Uppgift_saknas')):
        raise Continue

    if subname.replace('Obsolete', '') in {
            'Unknown',
            'Other', 'NotApplicable',
            'Unspecified', 'Undefined'}:
        type_id = None
    else:
        type_id = subname

    # TODO: use Obsolete to mark enum or entire collection as deprecated

    if type_id and type_id.endswith('Obsolete') and len(type_id) > 8 and type_id[-9] not in ('/', '-'):
        type_id = type_id[:-8] + '-Obsolete'

    return type_id

def _find_boolean_off_key(valuemap):
    if valuemap and len(valuemap) == 2:
        items = [(k, (v.get('id') or v.get('label_en', '')).lower() if v else '_')
                    for (k, v) in valuemap.items()]
        for off_index, (k, v) in enumerate(items):
            if v.startswith('no'):
                on_k, on_v = items[not off_index]
                if True:# v.endswith(on_v.replace('present', '')):
                    #assert k == '0' and on_k == '1'
                    return k
                break

def to_name(name):
    name = name[0].upper() + name[1:]
    plural_name = None
    if name == 'Theses':
        pural_name = name
        name = 'Thesis'
    elif 'And' in name:
        name = 'Or'.join(s[0:-1] if s.endswith('s') else s
                for s in name.split('And'))
    elif name[0].isdigit() \
            or name.startswith(('Missing', 'Mixed', 'Multiple')) \
            or name.endswith(('Access', 'Atlas', 'Arms', 'Blues',
                'BubblesBlisters', 'Canvas', 'Characteristics', 'Contents',
                'ExceedsThreeCharacters', 'Glass', 'Series', 'Statistics',
                'Previous')):
        pass
    elif name.endswith('ies'):
        pural_name = name
        name = name[0:-3] + 'y'
    elif name in {'Indexes', 'LecturesSpeeches', 'Marches', 'Masses', 'Rushes',
                  'Speeches', 'Waltzes', }:
        pural_name = name
        name = name[0:-2]
    elif name.endswith('s'):
        name = name[0:-1]
    return name, plural_name


def add_enum_collection_def(enumcoll):
    coll_id = enumcoll.id
    #assert coll_id not in ENUM_DEFS, "Collection duplicate: %s" % coll_id
    coll_predef = ENUM_DEFS.get(coll_id)
    same_as = coll_predef['sameAs'] if coll_predef else []
    coll_def = ENUM_DEFS[coll_id] = {
        "@id": coll_id,
        "@type": ["CollectionClass"],
        "subClassOf": ["EnumeratedTerm"],
        #"inScheme": "",
        #"notation": coll_id,
        "sameAs": same_as
        #"inRangeOf": propname
    }
    return coll_def

def add_enum_def(coll_id, type_id, dfn_ref_key, dfn, key):
    #assert type_id not in ENUM_DEFS
    assert type_id != coll_id, "Same as collection: %s" % type_id

    in_coll = ENUM_DEFS[type_id]['inCollection'] if type_id in ENUM_DEFS else []

    if not any(r['@id'] == coll_id for r in in_coll):
        in_coll.append({"@id": coll_id})

    dest = ENUM_DEFS[type_id] = {
        "@id": type_id, "@type": in_coll,
        "sameAs": {"@id": "%s-%s" % (dfn_ref_key, key)},
        "notation": key,
        "inCollection": in_coll
    }
    add_labels(dfn, dest)


def process_marcmap(OUT, marc_type):
    section = OUT[marc_type] = OrderedDict()

    prevtag, outf = None, None
    for tag, field in sorted(MARCMAP[marc_type].items()):
        if not tag.isdigit():
            continue
        prevf, outf = outf, OrderedDict()
        section[tag] = outf
        subfields = field.get('subfield')
        subtypes = None
        if MAKE_VOCAB:
            outf['@type'] = 'skos:Collection'
            field_id = '%s-%s' % (marc_type, tag)
            outf['@id'] = field_id
            outf['notation'] = tag
            outf['marcType'] = marc_type

        fixmaps = field.get('fixmaps')
        if fixmaps:
            process_fixmaps(marc_type, tag, fixmaps, outf)

        elif not subfields:
            outf['addProperty'] = field['id']

        else:
            for ind_key in ('ind1', 'ind2'):
                ind = field.get(ind_key)
                if not ind:
                    continue
                ind_keys = sorted(k for k in ind if k != '_')
                if ind_keys:
                    outf[ind_key.replace('ind', 'i')] = {}
            for code, subfield in subfields.items():
                code = code.lower()
                sid = subfield.get('id') or ""
                if sid.endswith('Obsolete'):
                    outf['obsolete'] = True
                    sid = sid[0:-8]
                if (code, sid) in [('6', 'linkage'), ('8', 'fieldLinkAndSequenceNumber')]:
                    continue
                subf = outf['$' + code] = OrderedDict()
                repeatable = subfield.get('repeatable', False)
                p_key = 'addProperty' if repeatable else 'property'
                if sid or not MAKE_VOCAB:
                    subf[p_key] = sid
                if MAKE_VOCAB:
                    subf['@type'] = 'rdf:Property'
                    subf['@id'] = '%s-%s-%s' % (marc_type, tag, code)
                    subf['notation'] = code
                    subf['repeatable'] = repeatable
                    add_labels(subfield, subf)
            if len(outf.keys()) > 1 and outf == prevf:
                section[tag] = {'inherit': prevtag}
        if 'repeatable' in field:
            outf['repeatable'] = field['repeatable']
        if MAKE_VOCAB:
            add_labels(field, outf)
        prevtag = tag

    field_index = {}
    for tag, field in OUT[marc_type].items():
        if not any(k.startswith('$') for k in field):
            continue
        def hash_dict(d):
            return tuple((k, hash_dict(v) if isinstance(v, dict) else v)
                    for k, v in d.items())
        fieldhash = hash_dict(field)
        if fieldhash in field_index:
            field.clear()
            field['inherits'] = field_index[fieldhash]
        else:
            field_index[fieldhash] = tag


def process_fixmaps(marc_type, tag, fixmaps, outf):
    enum_map = PROCESSED_ENUMS[marc_type]
    tokenTypeMap = OrderedDict()

    for fixmap in fixmaps:
        #content_type = None
        orig_type_name = None
        type_name = None
        if len(fixmaps) > 1:
            if tag == '008':
                pass #rt_bl_map = outf.setdefault('recTypeBibLevelMap', OrderedDict())
            else:
                outf['addLink'] = 'hasFormat' if tag == '007' else 'hasPart'
                outf['[0:1]'] = {
                    'addProperty': '@type',
                    'tokenMap': tokenTypeMap,
                }
                outf['tokenTypeMap'] = '[0:1]'

            orig_type_name =  fixmap['name'].split(tag + '_')[1]
            type_name = fixmap.get('term') or orig_type_name
            if tag in ('006', '008'):
                type_name = content_name_map.get(type_name, type_name)
            elif tag in ('007'):
                type_name = carrier_name_map.get(type_name, type_name)

            fm = outf[type_name] = OrderedDict()
            if MAKE_VOCAB:
                fm['@type'] = 'owl:Class'
                add_labels(fixmap, fm)

            if tag == '008':
                pass
                #for combo in fixmap['matchRecTypeBibLevel']:
                #    rt_bl_map[combo] = type_name
                #    rt, bl = combo
                #    subtype_name = fixprop_to_name(fixprops, 'typeOfRecord', rt)
                #    if not subtype_name:
                #        continue
                #    comp_name = fixprop_to_name(fixprops, 'bibLevel', bl)
                #    if not comp_name:
                #        continue
                #
                #    #is_serial = type_name == 'Serial'
                #    #if comp_name == 'MonographItem' or is_serial:
                #    #    content_type = contentTypeMap.setdefault(type_name, OrderedDict())
                #    #    subtypes = content_type.setdefault('subclasses', OrderedDict())
                #    #    if is_serial:
                #    #        subtype_name += 'Serial'
                #    #    typedef = subtypes[subtype_name] = OrderedDict()
                #    #    typedef['typeOfRecord'] = rt
                #    #else:
                #    #    comp_type = compositionTypeMap.setdefault(comp_name, OrderedDict())
                #    #    comp_type['bibLevel'] = bl
                #    #    parts = comp_type.setdefault('partRange', set())
                #    #    parts.add(type_name)
                #    #    parts.add(subtype_name)

            else:
                for k in fixmap['matchKeys']:
                    tokenTypeMap[k] = type_name
        else:
            fm = outf

        real_fm = fm
        for col in fixmap['columns']:
            off, length = col['offset'], col['length']
            key = (#str(off) if length == 1 else
                    '[%s:%s]' % (off, off+length))
            if key in common_columns.get(tag, ()):
                # IMPROVE: verify expected props?
                fm = outf
            else:
                fm = real_fm

            dfn_ref_key = col.get('propRef')
            if not dfn_ref_key:
                continue
            if orig_type_name == 'ComputerFile':
                orig_type_name = 'Computer'
            if orig_type_name and dfn_ref_key.title().startswith(orig_type_name):
                new_propname = dfn_ref_key[len(orig_type_name):]
                new_propname = new_propname[0].lower() + new_propname[1:]
                #print(new_propname, '<-', dfn_ref_key)
            else:
                new_propname = None

            fm[key] = col_dfn = OrderedDict()
            propname = new_propname or dfn_ref_key or col.get('propId')
            if propname in propname_map:
                propname = propname_map[propname]

            domainname = 'Record' if tag == '000' else None
            if dfn_ref_key in fixprop_typerefs.get(tag):
                if tag == '007':
                    propname = 'carrierType'
                    repeat = True
                elif tag in ('006', '008'):
                    propname = 'contentType'
                    repeat = True
            else:
                repeat = False

            if MAKE_VOCAB:
                add_labels(col, col_dfn)

            enumcoll = enum_map.get(marc_type + '-' + dfn_ref_key)

            if domainname:
                col_dfn['domainEntity'] = domainname

            is_link = length < 3
            if is_link:
                col_dfn['addLink' if repeat else 'link'] = propname
                col_dfn['uriTemplate'] = "{_}"
            else:
                if propname or not MAKE_VOCAB:
                    col_dfn['addProperty' if repeat else 'property'] = propname

            if enumcoll:

                if MAKE_VOCAB:
                    colpropid = '%s-%s-%s' % (marc_type, tag, key)
                    #if colpropid in ENUM_DEFS: print(colpropid)
                    prop_dfn = {'@id': propname, '@type': 'owl:ObjectProperty'}
                    prop_dfn['schema:rangeIncludes'] = {'@id': enumcoll.id}
                    add_labels(col, prop_dfn)
                    ENUM_DEFS[colpropid] = prop_dfn

                    coll_dfn = ENUM_DEFS[enumcoll.id]
                    add_labels(col, coll_dfn)
                    if type_name:
                        prop_dfn['schema:domainIncludes'] = {'@id': 'v:' + type_name}
                        # NOTE: means "enumeration only applicable if type of
                        # thing linking to it is of this type"
                        coll_dfn.setdefault('broadMatch', []).append('v:' + type_name)

                    # TODO: represent broadMatch and
                    # domainIncludes+rangeIncludes combos as anonymous
                    # subproperties, like:
                    #   :contentType a owl:ObjectProperty;
                    #       :combinations [
                    #               :prefLabel "Type of Continuing Resource"@en;
                    #               rdfs:domain v:Serial; rdfs:range :SerialsTypeOfSerialType
                    #           ], [
                    #               :prefLabel "Type of Material"@en;
                    #               rdfs:domain v:Visual; rdfs:range :VisualMaterialType
                    #           ].

                # TODO: check type of tokenmap (boolean, numeric (or fixed like here))
                items = enumcoll.items.items()
                TOKEN_MAPS[enumcoll.map_key] = OrderedDict(items)
                if len(items) == 1 and items[0][0] != 'u':
                    col_dfn['fixedDefault'] = items[0][0]

                #else:
                col_dfn['tokenMap' if is_link else 'patternMap'] = enumcoll.map_key


#def fixprop_to_name(fixprops, propname, key):
#    dfn = fixprops[propname].get(key)
#    if dfn and 'id' in dfn:
#        return to_name(dfn['id'])[0]
#    else:
#        return None


def add_labels(src, dest):
    sv = src.get('label_sv')
    en = src.get('label_en')
    #if sv or en:
    #    lang = dest['prefLabel'] = {}
    #    if sv: lang['sv'] = sv
    #    if en: lang['en'] = en
    if sv:
        dest['prefLabel'] = sv
    if en:
        dest['prefLabel_en'] = en


if __name__ == '__main__':
    args = sys.argv[1:]
    fpath = args.pop(0) if args else "legacy/marcmap.json"
    with open(fpath) as f:
        MARCMAP = json.load(f)

    ONLYENUMS = '--enums' in args
    MAKE_VOCAB = ONLYENUMS or '--vocab' in args

    OUT = OrderedDict()

    if MAKE_VOCAB:
        import string
        terms = {
            "@base": "http://id.kb.se/ns/marc/",
            "v": "http://id.kb.se/vocab/",
            "inCollection": {"@reverse": "skos:member"},
            "prefLabel": {"@language": "sv"},
            "prefLabel_en": {"@id": "prefLabel", "@language": "en"},
            "tokenMaps": None,
            "domain": {"@id": "rdfs:domain", "@type": "@vocab"},
            "range": {"@id": "rdfs:range", "@type": "@vocab"},
            "inRangeOf": {"@reverse": "rdfs:range", "@type": "@vocab"},
            "subClassOf": {"@id": "rdfs:subClassOf", "@type": "@vocab"},
            "broadMatch": {"@id": "skos:broadMatch", "@type": "@id"},
            "bib": None if ONLYENUMS else {"@id": "@graph", "@container": "@index"},
            "auth": None if ONLYENUMS else {"@id": "@graph", "@container": "@index"},
            "hold": None if ONLYENUMS else {"@id": "@graph", "@container": "@index"},
            'uriTemplate': None,
            #"tokenMap": None,
            "link": {"@id": "sameAs", "@type": "@vocab"},
            "addLink": {"@id": "sameAs", "@type": "@vocab"},
            "property": {"@id": "sameAs", "@type": "@vocab"},
            "addProperty": {"@id": "sameAs", "@type": "@vocab"},
            "inScheme": {"@type": "@id"},
            "marcType": {"@id": "inScheme", "@type": "@id"},
            "@vocab": "http://id.kb.se/ns/marc/",
            #'i1': None,
            #'i2': None,
        }
        terms.update({'$' + k: 'skos:member' for k in string.digits + string.ascii_lowercase})
        OUT["@context"] = ["../sys/context/base.jsonld", terms]
        OUT['@graph'] = []
    #else:
    OUT['tokenMaps'] = TOKEN_MAPS

    for marc_type in MARC_TYPES:
        build_enums(marc_type)

    for marc_type in MARC_TYPES:
        process_marcmap(OUT, marc_type)

    # cleanup
    for enum in ENUM_DEFS.values():
        for k, v in enum.items():
            if not v:
                del enum[k]
    if ENUM_DEFS:
        ENUM_DEFS['CollectionClass'] = {
            "@id": "CollectionClass", "@type": "owl:Class",
            "subClassOf": ["owl:Class", "skos:Collection"]
        }
        ENUM_DEFS['EnumeratedTerm'] = {
            "@id": "EnumeratedTerm", "@type": "owl:Class",
            "subClassOf": ["skos:Concept", "schema:Enumeration"]
        }
        OUT['@graph'].append({"@id": "enums", "@graph": ENUM_DEFS.values()})

    ## sanity check..
    #prevranges = None
    #for k, v in compositionTypeMap.items():
    #    ranges = v['partRange']
    #    if prevranges and ranges - prevranges:
    #        print("differs", k)
    #    else:
    #        assert any(r in contentTypeMap for r in ranges)
    #        v.pop('partRange')
    #    prevranges = ranges

    class SetEncoder(json.JSONEncoder):
        def default(self, obj):
            return list(obj) if isinstance(obj, set) else super(SetEncoder, self).default(obj)

    print(json.dumps(OUT,
            cls=SetEncoder,
            indent=2,
            ensure_ascii=False,
            separators=(',', ': ')
            ).encode('utf-8'))
