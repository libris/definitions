from __future__ import absolute_import
import operator
from flask import Flask, render_template, abort
from . import thingview, vocabview, marcframeview


class MyFlask(Flask):
    jinja_options = dict(Flask.jinja_options,
            variable_start_string='${', variable_end_string='}',
            line_statement_prefix='%')

app = MyFlask(__name__, static_url_path='/media', static_folder='static',
        instance_relative_config=True)
app.config.from_object('viewer.configdefaults')
app.config.from_envvar('DEFVIEW_SETTINGS', silent=True)
app.config.from_pyfile('config.cfg', silent=True)

import __builtin__
for name, obj in vars(__builtin__).items():
    if callable(obj):
        app.add_template_global(obj, name)

for func in [operator.itemgetter]:
    app.add_template_global(func, func.__name__)

@app.template_global()
def union(*args):
    return reduce(lambda a, b: a | b, args)

@app.template_global()
def format_number(n):
    return '{:,}'.format(n).replace(',', ' ')

@app.route('/')
def index():
    return render_template('index.html', **vars())

@app.route('/favicon.ico')
def favicon():
    abort(404)

app.register_blueprint(vocabview.app)
app.register_blueprint(marcframeview.app)
app.register_blueprint(thingview.app)
