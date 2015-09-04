#!/usr/bin/env python
import sys
import logging
from viewer import app

log = logging.getLogger()
log.addHandler(logging.StreamHandler(stream=sys.stdout))
log.setLevel(logging.DEBUG if app.debug else logging.INFO)

app.run()
