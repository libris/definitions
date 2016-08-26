# KB/LIBRIS Definitions

This repository is a collection of vocabulary and scheme definitions and
mappings to external resources. These define the foundation of linked library
data used by the National Library of Sweden.

## Dependencies

First, make sure you have `libpq-dev`, `libxml2-dev`, and
`libxslt1-dev` installed (or the corresponding packages for your
operating system).

Install the Python-based dependencies (preferably within a virtualenv):

```
$ cd /path/to/definitions
$ virtualenv .venv && source .venv/bin/activate
$ pip install -r requirements.txt
```

## Build Datasets

Run the following script to build the full set of definition resources:

    $ python datasets.py

You can also pass dataset names to generate the different parts in isolation.
Pass `-h` or `--help` to the script for details.

## Upload Datasets to an LDP-compliant Service

Use this script to HTTP PUT resources to a resource collection:

    $ scripts/load-defs-whelk.sh <COLLECTION-URL>

## Contents

The `source/` directory contains the main vocabulary mappings for linked data
at KB.

Here can also be found a bunch of common definitions and mappings, as well as
language labels more or less manually synced with various external origins. See
`datasets.py` for the details.

It also contains a hand-curated set of RDF types extracted from MARC fixed
field definitions (006, 007 and 008 for bib, auth and hold).

## Maintenance Utilities

To generate RDF descriptions from legacy MARC definitions, use:

    $ python scripts/marcframe-skeleton-from-marcmap.py scripts/marc/marcmap.json --enums

(See script for other options. Pipe the output to
`rdfpipe -ijson-ld:base=source/ -oturtle -` to get Turtle.)

To generate a JSON mapping file for enum tokens from that, use:

    $ python scripts/tokenmaps-from-enums.py source/marc/enums.ttl #.json

