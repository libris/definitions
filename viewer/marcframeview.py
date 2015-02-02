from flask import Blueprint, render_template
import re
import json


app = Blueprint('marcframeview', __name__)

@app.route('/marcframeview/')
def marcframeview():

    marcframe_path = "etc/marcframe.json"
    with open(marcframe_path) as fp:
        marcframe = json.load(fp)

    MARC_CATEGORIES = 'bib', 'auth', 'hold'

    def marc_categories():
        for cat in MARC_CATEGORIES:
            yield cat, marcframe[cat]

    def fields(catdfn):
        for tag, dfn in sorted(catdfn.items()):
            if tag.isdigit() and dfn:
                kind = ('fixed' if any(k for k in dfn if k[0] == '[' and ':' in k)
                        else 'field' if any(k for k in dfn if k[0] == '$')
                        else 'control')
                yield tag, kind, dfn

    def codes(dfn):
        for code, subdfn in sorted(dfn.items()):
            if code.startswith('$') and subdfn:
                yield code, subdfn

    def pretty_json(data):
        s = json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2,
                separators=(',', ': '))
        return re.sub(r'{\s+(\S+: "[^"]*")\s+}', r'{\1}', s)

    return render_template('marcframeview.html', **vars())
