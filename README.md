# KB/LIBRIS Definitions

This repository is a collection of vocabulary and scheme definitions and
mappings to external resources. These define the foundation of linked library
data used by the National Library of Sweden.

## Dependencies

Install the Python-based dependencies (preferably within a virtualenv):

    $ pip install -r requirements.txt

## Generate Datasets

Run the following script to build the full set of definition resources:

    $ python scripts/compile_defs.py -c cache/ -o build/

You can also provide resource names to generate the different parts in
isolation. Pass `--help` to the script for details.

## Upload Datasets to an LDP-compliant Service

Use this script to HTTP PUT resources to a resource collection:

    $ scripts/load_defs_whelk.sh <COLLECTION-URL>

## Contents

The `def/` directory contains local RDF definitions and mappings.

The `etc/` directory defines mappings from MARC to the terms used in the JSON-LD
context.

The `source/` directory mainly contains language labels manually synced with
various external origins. See `scripts/compile_defs.py` for the details. It
also contains `enums.json`, which is a hand-curated set of RDF types extracted
from MARC fixed field definitions (006, 007 and 008 for bib, auth and hold).

