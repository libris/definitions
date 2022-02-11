# KB/LIBRIS Definitions

This repository is a collection of vocabulary and scheme definitions and
mappings to external resources. These define the foundation of linked library
data used by the National Library of Sweden.

## Dependencies

Requires Python 3.7+. (Use PyPy for a general speed improvement.)

Preferably set up a virtualenv:

    $ python3 -m venv PATH_TO_VENV_OF_YOUR_CHOICE
    $ source PATH_TO_VENV_OF_YOUR_CHOICE/bin/activate

Install the Python-based dependencies:

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

### Vocabulary Source Files

The vocabulary is split into the formally decided "vocab" terms (which we call
the *KBV* namespace), and the legacy (often unstable) "marc" terms stemming
from MARC21 constructs not yet interpreted according to the new modelling
principles (based on RDF and linked data (see source/doc/model.en.mkd)).

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

### Term Categories

To categorize classes and properties, we use or own `kbv:category` property,
which links to various terms we've defined for various purposes, such as
`:pending`.

We do not use `vs:term_status` for this, since:

1. We have a more broad set of categories than "status" implies. Categories are
   defined for various application-specific purposes, e.g. to state that a term
   is a shorthand term, or that a class belongs to a group of classes mappable
   to MARC bibliographic records).

2. Its use of string literals is poor practise, since out-of-band definitions
   are then needed to discover applicable values and their meanings. This is
   natural when using linked data by simply minting a URI for the status item
   and defining it with labels and definition texts (in any languages needed).

We have put `vs:term_status "unstable"` to use in some places, to clearly
indicate that using a common colloquialism. But for out application purposes,
we use `:category :pending`.

For deprecation we use `owl:deprecated true`, to facilitate any eventual
tooling requiring this exact form.

We also mark terms using `ptg:abstract true` if they are not supposed to be
used for resources directly (and thus choosable e.g. in an editing interface),
but to represent a point in a class or property hierarchy defined for
structuring the vocabulary.

### Cleaning Up Terms

In principle, we should keep any published terms indefinitely. Everything at
`id.kb.se` is potentially used externally (even without us knowing so), as
we're an official agency tasked with ensuring long term stability and promoting
data reuse.

If we consider a certain term ill-defined and detrimental to use, do not expect
anyone else to be using it, and consider keeping it along with a
`owl:deprecated true` as potentially problematic, it is OK to comment it out
along with a note like:

    # Dropped at 2021-09-08. Feel free to delete this after 5 years.

If its disappearance prompts any complaints, this gives us an easy way of
seeing that we've removed it, and provides a window for restoring it.

#### KBV

This is a public *application* vocabulary. As such, we have no contract in
terms of stability or officiality, other than that all terms *we* use in our
data are to be defined within it. In general, this holds even if our data for
certain resources is deleted, since their descriptions may have been kept in
other systems. We do not guarantee this indefinitely though, and especially we
might drop terms if they are deemed incorrect. Other than that, we will use
`owl:deprecated true` to signal intended disappearance of a term.

#### MARC

All of these terms are implicitly `owl:deprecated true` and can in theory be
dropped at any time (after removing any use of them from our datasets). *No
external use should depend on them.* Any long-term use of these which indicate
meaningful requirements *should* be reworked into proper KBV terms.

### marcframe & legacy mappings

By using utilities in the whelk-core repository; you can generate a SPARQL
construct file from the marcframe.json mappings, from which you can in turn
generate a basic vocab file:

    $ cd ../whelk-core/ && gradle -q vocabFromMarcFrame #.rq

To generate RDF descriptions from legacy MARC definitions, use:

    $ python scripts/marcframe-skeleton-from-marcmap.py scripts/marc/marcmap.json --enums

See that script for other options.

Pipe the output to `rdfpipe -ijson-ld:base=source/ -oturtle -` to get it as Turtle.
