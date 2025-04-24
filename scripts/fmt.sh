#!/bin/bash
trld -ittl -e -f -c $(dirname $0)/../build/sys/context/kbv.jsonld -B -ottl | sed 's/rdf:type/a/'
