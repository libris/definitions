from __future__ import absolute_import
import operator
from flask import Flask, render_template
from . import thingview, vocabview, marcframeview


class MyFlask(Flask):
    jinja_options = dict(Flask.jinja_options,
            variable_start_string='${', variable_end_string='}',
            line_statement_prefix='%')

app = MyFlask(__name__, static_url_path='', static_folder='static')

#app.config.from_pyfile('config.cfg', silent=True)

import __builtin__
for name, obj in vars(__builtin__).items():
    if callable(obj):
        app.add_template_global(obj, name)

for func in [operator.itemgetter]:
    app.add_template_global(func, func.__name__)

@app.template_global()
def union(*args):
    return reduce(lambda a, b: a | b, args)

@app.route('/')
def index():
    return render_template('index.html', **vars())

app.register_blueprint(thingview.app)
app.register_blueprint(vocabview.app)
app.register_blueprint(marcframeview.app)
