import re
import json
from os import makedirs, path as P

import requests
from flask import Blueprint, render_template


app = Blueprint('marcframeview', __name__)

MARC_CATEGORIES = 'bib', 'auth', 'hold'

@app.record
def setup_app(setup_state):
    global marcframe

    config = setup_state.app.config

    MARCFRAME_SOURCE = config['MARCFRAME_SOURCE']

    cachedir = config['CACHE_DIR']
    if not P.isdir(cachedir):
        makedirs(cachedir)
    marcframe_file = P.join(cachedir, 'marcframe.json')

    try:
        with open(marcframe_file, 'w') as f:
            resp = requests.get(MARCFRAME_SOURCE, stream=True)
            for chunk in resp.iter_content(1024):
                f.write(chunk)
    except requests.exceptions.ConnectionError:
        pass

    with open(marcframe_file) as fp:
        try:
            marcframe = json.load(fp)
        except ValueError:
            marcframe = None

@app.route('/marcframeview/')
def marcframeview():

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

    return render_template('marcframeview.html', marcframe=marcframe, **vars())
