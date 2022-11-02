import json
import re
import sys

ID = "@id"
TYPE = "@type"
VALUE = "@value"
GRAPH = "@graph"

FORM_RE = re.compile(r'(\w+)-(\w+)-t-(\w+)(?:-(?:(\w+)-)?([xm]0-.+))?')

LANG_FORM = "TransformedLanguageForm"

COMBINATIONS = [
    ('el', 'Grek', 'x0-btj'),
    ('grc', 'Grek', 'x0-skr-1980'),
    ('mn', 'Cyrl', 'x0-lessing'),

    ('be', 'Cyrl', 'm0-iso-1995'),
    ('bg', 'Cyrl', 'm0-iso-1995'),
    ('kk', 'Cyrl', 'm0-iso-1995'),
    ('mk', 'Cyrl', 'm0-iso-1995'),
    ('ru', 'Cyrl', 'm0-iso-1995'),
    ('sr', 'Cyrl', 'm0-iso-1995'),
    ('uk', 'Cyrl', 'm0-iso-1995'),

    ('hi', 'Deva', 'm0-alaloc'),
    ('az', 'Cyrl', 'm0-alaloc'),
    ('kir', 'Cyrl', 'm0-alaloc'),
    ('tt', 'Cyrl', 'm0-alaloc'),
    ('tg', 'Cyrl', 'm0-alaloc'),
    ('tk', 'Cyrl', 'm0-alaloc'),
    ('uz', 'Cyrl', 'm0-alaloc'),
    ('zh', 'Hani', 'm0-alaloc'),
    ('mn', 'Mong', 'm0-alaloc'),
]

ALA_LOC_NO_SCRIPT = ['am', 'chu', 'ka', 'hy']

ALA_LOC_NON_SLAVIC_CYRILLIC = [
    'abk', 'ady', 'alt', 'ava', 'bak', 'bua', 'che', 'chm', 'chv', 'dar',
    'inh', 'kaa', 'kbd', 'kom', 'krc', 'krl', 'kum', 'lez', 'lit', 'nog',
    'oss', 'rom', 'rum', 'rum', 'sah', 'sel', 'tut', 'udm', 'xal',
]

JUST_TAGS = ['ara', 'und']  # TODO: map lang to script

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
    f"{tag}-Latn-t-{tag}" for tag in JUST_TAGS
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
            desc["langTransformAccordingTo"] = {ID: f"/i18n/rules/{rule}"}
            rules.add(rule)

for script in scripts:
    describe(script, 'script', 'LanguageScript')

for rule in rules:
    base, code = rule.split('/')
    desc = describe(code, f'rules/{base}', 'LanguageTransformRules')
    desc['inCollection'] = {ID: f'/i18n/rules/{base}'}

json.dump({"@graph": items}, sys.stdout, indent=2, ensure_ascii=True)
