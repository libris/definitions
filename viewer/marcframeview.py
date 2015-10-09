from flask import Blueprint, render_template
import re
import json


app = Blueprint('marcframeview', __name__)

MARC_CATEGORIES = 'bib', 'auth', 'hold'

@app.record
def setup_app(setup_state):
    config = setup_state.app.config
    global MARCFRAME_SOURCE
    MARCFRAME_SOURCE = config['MARCFRAME_SOURCE']

@app.route('/marcframeview/')
def marcframeview():

    with open(MARCFRAME_SOURCE) as fp:
        marcframe = json.load(fp)

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
