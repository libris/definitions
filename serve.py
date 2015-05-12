#!/usr/bin/env python
import sys
import argparse
import logging

ap = argparse.ArgumentParser()
ap.add_argument('-d', '--debug', action='store_true', default=False)
ap.add_argument('-p', '--port', type=int, default=5000)
args = ap.parse_args()

log = logging.getLogger()
log.addHandler(logging.StreamHandler(stream=sys.stdout))
log.setLevel(logging.DEBUG if args.debug else logging.INFO)

from viewer import app
app.debug = args.debug
app.run(host='0.0.0.0', port=args.port)
