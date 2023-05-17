from __future__ import annotations
import json
import re
import sys

ID = "@id"
TYPE = "@type"
VALUE = "@value"
GRAPH = "@graph"

FORM_RE = re.compile(r'(\w+)-(\w+)-t-(\w+)(?:-(?:(\w+)-)?([xm]0-.+))?')
COMBINATIONS = [
    ('el', 'Grek', 'x0-btj'),
    ('grc', 'Grek', 'x0-skr-1980'),
    ('mn', 'Cyrl', 'x0-lessing'),

    ('be', 'Cyrl', 'm0-iso-1968'),
    ('bg', 'Cyrl', 'm0-iso-1968'),
    ('mk', 'Cyrl', 'm0-iso-1968'),
    ('ru', 'Cyrl', 'm0-iso-1968'),
    ('sr', 'Cyrl', 'm0-iso-1968'),
    ('uk', 'Cyrl', 'm0-iso-1968'),
    
    ('be', 'Cyrl', 'm0-iso-1995'),
    ('bg', 'Cyrl', 'm0-iso-1995'),
    ('kk', 'Cyrl', 'm0-iso-1995'),
    ('mk', 'Cyrl', 'm0-iso-1995'),
    ('ru', 'Cyrl', 'm0-iso-1995'),
    ('sr', 'Cyrl', 'm0-iso-1995'),
    ('uk', 'Cyrl', 'm0-iso-1995'),

    ('am', 'Ethi', 'm0-alaloc'),
    ('ar', 'Arab', 'm0-alaloc'),
    ('as', 'Beng', 'm0-alaloc'),
    ('az', 'Arab', 'm0-alaloc'),
    ('az', 'Cyrl', 'm0-alaloc'),
    ('bo', 'Tibt', 'm0-alaloc'),
    ('ban', 'Bali', 'm0-alaloc'),
    ('btk', 'Batk', 'm0-alaloc'),
    ('chr', 'Cher', 'm0-alaloc'),
    ('chu', 'Cyrs', 'm0-alaloc'),
    ('cop', 'Copt', 'm0-alaloc'),
    ('dv', 'Thaa', 'm0-alaloc'),
    ('fa', 'Arab', 'm0-alaloc'),
    ('gu', 'Gujr', 'm0-alaloc'),
    ('he', 'Hebr', 'm0-alaloc'),
    ('hi', 'Deva', 'm0-alaloc'),
    ('hy', 'Armn', 'm0-alaloc'),
    ('iu', 'Cans', 'm0-alaloc'),
    ('jrb', 'Hebr', 'm0-alaloc'),
    ('jv', 'Java', 'm0-alaloc'),
    ('kir', 'Cyrl', 'm0-alaloc'),
    ('km', 'Khmr', 'm0-alaloc'),
    ('kn', 'Knda', 'm0-alaloc'),
    ('ko', 'Hang', 'm0-alaloc'),
    ('ks', 'Arab', 'm0-alaloc'),
    ('ku', 'Cyrl', 'm0-alaloc'),
    ('ku', 'Arab', 'm0-alaloc'),
    ('lad', 'Hebr', 'm0-alaloc'),
    ('lo', 'Laoo', 'm0-alaloc'),
    ('mad', 'Java', 'm0-alaloc'),
    ('ml', 'Mlym', 'm0-alaloc'),
    ('mn', 'Mong', 'm0-alaloc'),
    ('mnc', 'Mong', 'm0-alaloc'),
    ('mr', 'Deva', 'm0-alaloc'),
    ('my', 'Mymr', 'm0-alaloc'),
    ('or', 'Orya', 'm0-alaloc'),
    ('pa', 'Guru', 'm0-alaloc'),
    ('pi', 'Beng', 'm0-alaloc'),
    ('pi', 'Mymr', 'm0-alaloc'),
    ('pi', 'Deva', 'm0-alaloc'),
    ('pi', 'Sinh', 'm0-alaloc'),
    ('pi', 'Thai', 'm0-alaloc'),
    ('ps', 'Arab', 'm0-alaloc'),
    ('sat', 'Olck', 'm0-alaloc'),
    ('sd', 'Arab', 'm0-alaloc'),
    ('sd', 'Deva', 'm0-alaloc'),
    ('shn', 'Mymr', 'm0-alaloc'),
    ('si', 'Sinh', 'm0-alaloc'),
    ('su', 'Java', 'm0-alaloc'),
    ('syc', 'Syrc', 'm0-alaloc'),
    ('syr', 'Syrc', 'm0-alaloc'),
    ('ta', 'Taml', 'm0-alaloc'),
    ('te', 'Telu', 'm0-alaloc'),
    ('tg', 'Cyrl', 'm0-alaloc'),
    ('th', 'Thai', 'm0-alaloc'),
    ('ti', 'Ethi', 'm0-alaloc'),
    ('tk', 'Cyrl', 'm0-alaloc'),
    ('tt', 'Cyrl', 'm0-alaloc'),
    ('ug', 'Arab', 'm0-alaloc'),
    ('ug', 'Cyrl', 'm0-alaloc'),
    ('ur', 'Arab', 'm0-alaloc'),
    ('uz', 'Arab', 'm0-alaloc'),
    ('uz', 'Cyrl', 'm0-alaloc'),
    ('vai', 'Vaii', 'm0-alaloc'),
    ('yi', 'Hebr', 'm0-alaloc'),
    ('zh', 'Hani', 'm0-alaloc'),
]

LANG_FORM = "TransformedLanguageForm"

ALA_LOC_NO_SCRIPT = ['tmh', 'ka']

ALA_LOC_NON_SLAVIC_CYRILLIC = [
    'abk', 'ady', 'alt', 'ava', 'bak', 'bua', 'che', 'chm', 'chv', 'dar',
    'inh', 'kaa', 'kbd', 'kom', 'krc', 'krl', 'kum', 'lez', 'lit', 'nog',
    'oss', 'rom', 'rum', 'rum', 'sah', 'sel', 'tut', 'udm', 'xal',
]

forms = [
    f"{tag}-Latn-t-{tag}-{script}-{rules}"
    for tag, script, rules in COMBINATIONS
] + [
    f"{tag}-Latn-t-{tag}-m0-alaloc"
    for tag in ALA_LOC_NO_SCRIPT
] + [
    f"{tag}-Latn-t-{tag}-Cyrl-m0-alaloc"
    for tag in ALA_LOC_NON_SLAVIC_CYRILLIC
] + [
    f"und-Latn-t-und",
]


LANG_CODE_MAP: dict[str, str] = {}
with open('build/languages.json.lines') as f:
    for l in f:
        thing = json.loads(l)
        if GRAPH in thing:
            thing = thing[GRAPH][1]
        if thing[TYPE] == 'Language':
            tag = thing.get('langTag')
            if tag:
                LANG_CODE_MAP[tag] = thing['code']


def get_langlink(tag):
    # TODO: Decide to EITHER lookup id:
    code = LANG_CODE_MAP.get(tag, tag)
    return {ID: f"/language/{code}"}
    # OR use tag-based sameAs alias to all languages (not done yet):
    #return {ID: f"/i18n/lang/{tag}"}
    # OR rely on LanguageLinker:
    #return {TYPE: "Language", "code": tag}


tags: set[str] = set()
scripts = set()
rules = set()

items = []


def describe(code, cat, rtype):
    desc = {ID: f"/i18n/{cat}/{code}", TYPE: rtype, "code": code}
    items.append(desc)
    return desc


for form in forms:
    desc = describe(form, 'lang', LANG_FORM)
    for tag, script, otag, oscript, rule in FORM_RE.findall(form):
        code = desc.pop("code")
        desc["code"] = [{VALUE: code, TYPE: 'BCP47'}]
        tags.add(tag)
        tags.add(otag)
        langref = get_langlink(tag)
        if tag != otag:
            desc["inLanguage"] = langref
            desc["fromLanguage"] = get_langlink(otag)
        else:
            # TODO: which is better/worse for applications?
            # (Note 1: We do use broader for specialized languages).
            # (Note 2: We've defined inLanguage as a subPropertyOf broader).
            #desc["broader"] = langref
            desc["inLanguage"] = langref

        desc["inLangScript"] = {ID: f"/i18n/script/{script}"}
        scripts.add(script)

        if oscript:
            desc["fromLangScript"] = {ID: f"/i18n/script/{oscript}"}
            scripts.add(oscript)

        if rule:
            rule = rule.replace('0-', '0/')  # TODO: is this what we want?
            desc["langTransformAccordingTo"] = {ID: f"/i18n/rule/{rule}"}
            rules.add(rule)

for script in scripts:
    describe(script, 'script', 'LanguageScript')

for rule in rules:
    base, code = rule.split('/')
    desc = describe(code, f'rule/{base}', 'LanguageTransformRules')
    desc['inCollection'] = {ID: f'/i18n/rule/{base}'}

json.dump({"@graph": items}, sys.stdout, indent=2, ensure_ascii=True)
