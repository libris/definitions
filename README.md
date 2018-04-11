# KB/LIBRIS Definitions

This repository is a collection of vocabulary and scheme definitions and
mappings to external resources. These define the foundation of linked library
data used by the National Library of Sweden.

## Dependencies

Install the Python-based dependencies (preferably within a virtualenv):

    $ pip install -r requirements.txt

## Usage

Run the following script to build the full set of definition resources:

    $ python datasets.py -l

You can also pass dataset names to generate the different parts in isolation.
Pass `-h` or `--help` to the script for details.

## Contents

The `source/` directory contains the main vocabulary mappings for linked data
at KB.

Here can also be found a bunch of common definitions and mappings, as well as
language labels more or less manually synced with various external origins. See
`datasets.py` for the details.

It also contains a hand-curated set of RDF types extracted from MARC fixed
field definitions (006, 007 and 008 for bib, auth and hold).

### Vocab & MARC

The vocabulary is split into the formally deciced "vocab" terms, and the legacy
"marc" (often unstable) terms stemming from MARC21 constructs not yet
interpreted according to the new modelling principles (based on RDF and linked
data (see source/doc/model.en.mkd)).

In  these files are special:

* `source/vocab/bf-to-kbv-base.rq` and `source/vocab/bf-map.ttl` are used to
  automatically wire up the base BF2 mappings and term hierarchies.

* `source/vocab/display.jsonld` defines lenses used to display data (as "cards"
  or "chips").

* `source/vocab/platform.ttl` and `source/vocab/services.ttl` map various
  technical terms to public vocabularies.

* `source/vocab/enums.ttl`, `source/vocab/construct-enum-restrictions.rq`,
  and `source/marc/enums.ttl` define the terms (properties and classes) for
  controlled, "enumerable" values. A lot of these stem from controlled values
  for columns in fixed fields in MARC21. Some come from RDA, and some from
  cleaned up defintions in BibFrame 2, or our own vocabulary. (See links in the
  data for references.)

  These files also contain certain *instances* of these classes. Specifically,
  these correspond to the domain of the properties defined as `@type: @vocab`
  in `source/vocab-overlay.jsonld`. These are special values defined within the
  vocabulary (often because they are very "type-like"). A prime example is
  `IssuanceType`, whose values are kept together with the vocabulary itself.

* `source/marc/construct-enums.rq` combine to create all other "enumerable"
  values, which may or may not become merged with other controlled lists in the
  future. (When that is done, the definition here must be removed and its URI
  be places in a `sameAs` relation in whatever term that is replacing it.

**Note:** the file `source/vocab/check-bases.rq` is used to check some sanity
in the generated structures. It is advised to heed any warnings by correcting
the relevant sources.

## Maintenance

*Tip:* During vocab development. Regularly run just:

    $ python datasets.py vocab

to generate a vocab build file. Look at it as Turtle by running:

    $ rdfpipe -ijson-ld:context=build/vocab/context.jsonld build/vocab.jsonld

, and/or make a nice, digested tree view by running:

    $ python scripts/misc/vocab-summary.py build/vocab.jsonld -c build/vocab/context.jsonld -v

### marcframe & legacy mappings

By using utilities in the whelk-core repository; you can generate a SPARQL
construct file from the marcframe.json mappings, from which you can i turn
generate a basic vocab file:

    $ cd ../whelk-core/ && gradle -q vocabFromMarcFrame #.rq

To generate RDF descriptions from legacy MARC definitions, use:

    $ python scripts/marcframe-skeleton-from-marcmap.py scripts/marc/marcmap.json --enums

See that script for other options.

Pipe the output to `rdfpipe -ijson-ld:base=source/ -oturtle -` to get it as Turtle.
