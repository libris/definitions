#!/usr/bin/env python
import sys
import logging
import argparse
from viewer import app

log = logging.getLogger()
log.addHandler(logging.StreamHandler(stream=sys.stdout))
log.setLevel(logging.DEBUG if app.debug else logging.INFO)

argp = argparse.ArgumentParser()
argp.add_argument('--port', '-p', type=int)
args = argp.parse_args()

app.run(port=args.port)
