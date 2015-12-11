# KB/LIBRIS Definitions

This repository is a collection of vocabulary and scheme definitions and
mappings to external resources. These define the foundation of linked library
data used by the National Library of Sweden.

## Dependencies

Install the Python-based dependencies (preferably within a virtualenv):

    $ pip install -r requirements.txt

## Build Datasets

Run the following script to build the full set of definition resources:

    $ python datasets.py

You can also pass dataset names to generate the different parts in isolation.
Pass `-h` or `--help` to the script for details.

## Upload Datasets to an LDP-compliant Service

Use this script to HTTP PUT resources to a resource collection:

    $ scripts/load-defs-whelk.sh <COLLECTION-URL>

## Contents

The `def/` directory contains local RDF definitions and mappings.

The `source/` directory mainly contains language labels manually synced with
various external origins. See `datasets.py` for the details. It
also contains `enums.json`, which is a hand-curated set of RDF types extracted
from MARC fixed field definitions (006, 007 and 008 for bib, auth and hold).

