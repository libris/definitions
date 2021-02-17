#!/usr/bin/env python
from __future__ import unicode_literals, print_function

from zlib import crc32
import string
import time
import random


lower_consonants_numbers = string.digits + "".join(
        c for c in string.ascii_lowercase if c not in "aoueiy")

def tobase(alphabet, i):
    v = ''
    size = len(alphabet)
    n = i
    while True:
        n, rest = divmod(n, size)
        v = alphabet[rest] + v
        if not n:
            return v

def caesarize(alphabet, s):
    size = len(alphabet)
    last = s[-1]
    rotation = alphabet.index(last)
    def rotate(c):
        pos = alphabet.index(c) + rotation
        return pos - size if pos >= size else pos
    return "".join(alphabet[rotate(c)] for c in s[:-1]) + last

def checksum(data):
    return crc32(data.encode('utf-8')) & 0xffffffff

def librisencode(a, b):
    alphabet = lower_consonants_numbers
    timepart = "".join(reversed(caesarize(alphabet, tobase(alphabet, a))))
    codepart = tobase(alphabet, b)
    codelen = len(codepart)
    if codelen < 7:
        codepart = ("0" * (7 - codelen)) + codepart
    return  timepart + codepart


if __name__ == '__main__':
    import sys
    import os.path as P

    args = sys.argv[:]
    cmd = P.basename(args.pop(0))

    if len(args) < 2:
        print("Usage: %s TIMESTAMP IDENTIFIER" % (cmd), file=sys.stderr)
        exit(1)

    timestamp = args.pop(0)
    identifiers = args

    try:
        timestamp = int(timestamp)
    except ValueError:
        timestamp, dot, frag = timestamp.partition('.')
        timestamp = (time.mktime(
            time.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")) * 1000)
        if frag:
            assert len(frag) < 4
            timestamp += + int(frag)

    def faux_offset(s):
        return sum(ord(c) * ((i+1) ** 2)  for i, c in enumerate(s))

    for identifier in identifiers:
        offset = faux_offset(identifier)
        check = checksum(identifier)
        slug = librisencode(int(timestamp + offset), check)
        print("<{}> = <{}> # {}, {}".format(slug, identifier, offset, check))
