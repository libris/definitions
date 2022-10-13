import json
import re
import sys

ID = "@id"
TYPE = "@type"
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
        thing = json.loads(l)[GRAPH][-1]
        if thing[TYPE] == 'Language':
            tag = thing.get('langTag')
            if tag:
                LANG_CODE_MAP[tag] = thing['code']

def get_langcode(tag):
    return LANG_CODE_MAP.get(tag, tag)


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
        tags.add(tag)
        tags.add(otag)
        # TODO: lookup id *or* add tag-based sameAs alias to all languages!
        #langref = {ID: f"/i18n/lang/{tag}"}
        #langref = {TYPE: "Language", "code": tag}
        langref = {ID: f"/language/{get_langcode(tag)}"}
        if tag != otag:
            desc["inLanguage"] = langref
            desc["fromLanguage"] = langref
        else:
            desc["broader"] = langref

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
