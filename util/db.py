# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
__metaclass__ = type

import logging
import os
import urllib2
import json
from util.ld import Vocab, ID, TYPE, REV


logger = logging.getLogger(__name__)


class DB:

    def __init__(self, vocab, *sources):
        self.vocab = vocab
        self.index = {}
        self.same_as = {}
        self.revs = {}
        self.rev_limit = 4000
        build_db_index(sources, self)

    def get_item(self, item_id):
        item = self.index.get(item_id)
        if item:
            return self.expand(item)
        else:
            return None

    def expand(self, item):
        expanded = dict(item)
        rev_map = self.revs.get(item[ID])
        if rev_map:
            for link, revitems in rev_map.items():
                if len(revitems) > self.rev_limit:
                    logger.info("More than %s reverse links for '%s' in <%s>",
                            self.rev_limit, link, item[ID])
                rev_map[link] = revitems[:self.rev_limit]
            expanded[REV] = rev_map
        return expanded


def build_db_index(sources, db, db_dir=None, limit=None):

    chips = {}

    logger.info("Loading data")
    for i, item in enumerate(load_data(sources)):
        if limit and i > limit:
            logger.debug("Stopping on limit: %d", limit)
            break

        logger.debug("Reshaping item #%d: <%s>", i, item[ID])
        item = reshape(item)
        item_id = item[ID]
        if 'sameAs' in item:
            for ref in item.get('sameAs'):
                if ID in ref:
                    db.same_as[ref[ID]] = item_id
        db.index[item_id] = item

    #items_dir = os.path.join(db_dir, 'items')
    #if not os.path.isdir(items_dir):
    #    os.makedirs(items_dir)

    logger.info("Processing items")
    for i, item in enumerate(db.index.values()):
        item_id = item[ID]
        logger.debug("Updating links and saving item #%s: <%s>", i, item_id)
        process_links(db, item)

        #item_path = get_item_path(items_dir, item_id)
        #with open(item_path + '.jsonld', 'w') as f:
        #    save_json(item, f)

        #chips[item_id] = chip = to_chip(db.vocab, item)
        #with open(item_path + '-chip.jsonld', 'w') as f:
        #    save_json(chip, f)

    #for i, (item_id, rev_map) in enumerate(revs.items()):
    #    logger.debug("Saving reverses #%s: <%s>", i, item_id)
    #    item_path = get_item_path(items_dir, item_id)
    #    with open(item_path + '-reverse.jsonld', 'w') as f:
    #        save_json({ID: item_id, REV: rev_map}, f)


def process_links(db, item):
    skip_links = ["sameAs", "describedBy"]
    for link, refs in item.items():
        if link in skip_links:
            continue
        if not isinstance(refs, list):
            refs = [refs]

        if link == TYPE:
            refs = [{ID: ref} for ref in refs]

        for ref in refs:
            if not isinstance(ref, dict):
                continue

            ref_id = ref.get(ID)
            if not ref_id:
                continue

            real_id = db.same_as.get(ref_id)
            if real_id:
                ref_id = ref[ID] = real_id

            revnode = db.revs.setdefault(ref_id, {})
            revitems = revnode.setdefault(link, [])
            revitems.append({ID: item[ID]})


# TODO: work as much as possible into initial conversion
def reshape(data):
    data.pop('_marcUncompleted', None)
    data.pop('_marcBroken', None)
    data.pop('_marcFailedFixedFields', None)
    if 'about' in data:
        item = data.pop('about')
        item['describedBy'] = data
    else:
        item = data

    itype = item[TYPE]
    if isinstance(itype, list):
        try:
            itype.remove('Concept')
        except ValueError:
            pass
        if len(itype) == 1:
            item[TYPE] = itype[0]

    if 'prefLabel_en' in item and 'prefLabel' not in item:
        item['prefLabel'] = item['prefLabel_en']

    return item


def to_chip(vocab, item):
    chip_keys = [ID, TYPE] + vocab.label_keys
    return {k: v for k, v in item.items() if k in chip_keys}


def load_data(sources):
    for source in sources:
        for data in load_source(source):
            yield data


def load_source(source):
    if os.path.isdir(source):
        fpaths = (os.path.join(root, fname)
                for root, dnames, fnames in os.walk(source)
                for fname in fnames
                if fname.endswith(b'.jsonld'))
        for fpath in fpaths:
            logger.debug("Loading JSON from: %s", fpath)
            with open(fpath) as f:
                yield json.load(f)
    else:
        for data in load_lines(source):
            yield data


def load_lines(source):
    if os.path.isfile(source):
        logger.debug("Loading lines from: %s", source)
        with open(source) as f:
            for l in f:
                yield json.loads(l)
    else:
        logger.warn("DB source %s does not exist", source)


def get_item_path(basedir, uri):
    return os.path.join(basedir, urllib2.quote(uri.encode('utf-8'), safe=""))


def save_json(data, f):
    f.write(json.dumps(data).encode('utf-8'))


if __name__ == '__main__':
    import argparse
    argp = argparse.ArgumentParser()
    argp.add_argument('-t', '--test', action='store_true', default=False)
    argp.add_argument('-o', '--output-dir')
    argp.add_argument('-l', '--limit', type=int, default=0)
    argp.add_argument('vocab', metavar='VOCAB', nargs='?')
    argp.add_argument('sources', metavar='SOURCE', nargs='*')
    args = argp.parse_args()

    if args.test:
        import doctest
        doctest.testmod()
    else:
        import sys
        log = logging.getLogger()
        log.addHandler(logging.StreamHandler(stream=sys.stdout))
        #log.setLevel(logging.DEBUG)
        log.setLevel(logging.INFO)

        vocab = Vocab(args.vocab, lang='sv')
        db = DB(vocab)
        build_db_index(args.sources, db, args.output_dir, args.limit)
