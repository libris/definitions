#!/usr/bin/env python
import argparse
from flask_frozen import Freezer
from viewer import app

ap = argparse.ArgumentParser()
ap.add_argument('-p', '--port', type=int)
args = ap.parse_args()

freezer = Freezer(app)
freezer.freeze()
if args.port:
    freezer.serve(port=args.port)
