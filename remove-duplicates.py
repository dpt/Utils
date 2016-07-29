#!/usr/bin/env python
#
# remove-duplicates.py: recursively travese the specified directory and delete
#                       files which have duplicate size and md5sum
#
# Copyright (c) David Thomas, 2007-2016. <dave@davespace.co.uk>
#

import md5
import os
import sys

IGNORE = ('Thumbs.db',)


def getmd5(filename):
    md5sum = md5.new()
    md5sum.update(file(filename, 'rb').read(-1))
    return md5sum.hexdigest()


def usage():
    print 'Usage: remove-duplicates.py DIRECTORY'
    sys.exit(1)


def main(argv):
    if len(argv) < 1:
        usage()

    root = os.path.abspath(argv[0])

    print 'Reading sizes...'

    # Create a dictionary keyed by size, with each entry holding a list of
    # filenames of that size.

    data = {}

    for root, _, files in os.walk(root):
        for name in files:
            if name in IGNORE:
                continue
            path = os.path.join(root, name)
            size = os.path.getsize(path)
            if size not in data:
                data[size] = []

            data[size].append(path)

    # For each key, checksum each list entry and compare.

    removed = 0

    for k in data.keys():
        ent = data[k]
        if len(ent) > 1:
            # print k, len(ent)
            sizes = {}
            for j in ent:
                md5sum = getmd5(j)
                if md5sum in sizes:
                    print j, 'is a dupe of', sizes[md5sum]
                    try:
                        os.remove(j)
                        removed += 1
                    except OSError:
                        pass
                else:
                    sizes[md5sum] = j

    print 'Done, %d files removed.' % (removed)

if __name__ == '__main__':
    main(sys.argv[1:])

# vim: ts=8 sts=4 sw=4 et
