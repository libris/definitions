from __future__ import unicode_literals, print_function, division
from collections import Counter
import json


def get_keywords(marcframe, ignore_speced=False):
    keywords = Counter()
    speced = set()
    for key, part in marcframe.items():
        if not isinstance(part, dict):
            continue
        for field in part.values():
            if not field:
                continue
            is_speced = any(kw in field for kw in ['_specSource', '_spec'])
            if not isinstance(field, dict):
                #print "Skipping:", field
                continue
            for kw, obj in field.items():
                if '$' in kw or kw in {'i1', 'i2'} or kw[0].isupper():
                    if obj:
                        if not isinstance(obj, dict):
                            continue
                        for subkw, subobj in obj.items():
                            if subkw.startswith('['):
                                keywords.update(subobj.keys())
                                if is_speced:
                                    speced |= set(subobj)
                            else:
                                keywords[subkw] += 1
                                if is_speced:
                                    speced.add(kw)
                elif not kw.startswith('['):
                    keywords[kw] += 1
                    if is_speced:
                        speced.add(kw)
    if ignore_speced:
        for k in speced:
            del keywords[k]
    return keywords


if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    source = args.pop(0)

    with open(source) as fp:
        marcframe = json.load(fp)

    keywords = get_keywords(marcframe)
    for kw, i in keywords.most_common():
        if 'NOTE:' in kw.upper() or 'TODO' in kw.upper():
            continue
        print(kw, i)
