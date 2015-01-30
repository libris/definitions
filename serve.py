#!/usr/bin/env python
import argparse
ap = argparse.ArgumentParser()
ap.add_argument('-d', '--debug', action='store_true', default=False)
ap.add_argument('-p', '--port', type=int, default=5000)
args = ap.parse_args()

from viewer import app
app.debug = args.debug
app.run(host='0.0.0.0', port=args.port)
