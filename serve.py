#!/usr/bin/env python
import sys
import argparse
import logging
from viewer import app

ap = argparse.ArgumentParser()
ap.add_argument('-d', '--debug', action='store_true', default=False)
ap.add_argument('-p', '--port', type=int, default=5000)
args = ap.parse_args()

app.debug = args.debug
if app.debug:
    loghandler = logging.StreamHandler(stream=sys.stdout)
    log = logging.getLogger()
    log.addHandler(loghandler)
    log.setLevel(logging.DEBUG)
app.run(host='0.0.0.0', port=args.port)
