#!/bin/bash
trld -ittl -e -f -c context.jsonld -B -ottl | sed 's/rdf:type/a/'
