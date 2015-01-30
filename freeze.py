#!/usr/bin/env python
import argparse
ap = argparse.ArgumentParser()
ap.add_argument('-p', '--port', type=int)
args = ap.parse_args()

from flask_frozen import Freezer
from viewer import app

#app.config['FREEZER_DESTINATION'] = "build/viewer"
freezer = Freezer(app)
freezer.freeze()
if args.port:
    freezer.serve(port=args.port)
