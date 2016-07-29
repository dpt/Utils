#!/usr/bin/env python
#
# resetjpegdpi.py: recursively traverse the specified directory and reset the
#                  version, units and density fields of JPEGs
#
# Copyright (c) David Thomas, 2007-2016. <dave@davespace.co.uk>
#

"Reset the version, units and density fields of JPEGs."

import array
import os
import struct
import sys

HIDDEN = ('Thumbs.db',)
EXTENSION = os.extsep + 'jpg'

# SOI, APP0, length (16), 'JFIF\0'
SIGNATURE = array.array('c')
SIGNATURE.fromstring('\xff\xd8\xff\xe0\x00\x10\x4a\x46\x49\x46\x00')

FORMAT = '>hbhh'

NEW_VALUES = array.array('c')
NEW_VALUES.fromstring(struct.pack(FORMAT, 0x102, 0, 100, 100))


def usage():
    print 'Usage: resetjpegdpi.py DIRECTORY'
    sys.exit(1)


def main(argv):
    if len(argv) < 1:
        usage()

    path = os.path.abspath(argv[0])

    for root, _, files in os.walk(path):
        for name in files:
            if name in HIDDEN:
                continue
            if not name.endswith(EXTENSION):
                continue

            fullname = os.path.join(root, name)
            f = file(fullname)
            f.seek(0, 2)
            length = f.tell()
            f.seek(0, 0)
            data = array.array('c')
            data.fromfile(f, length)
            f.close()

            if data[:11] != SIGNATURE:
                print '%s has no signature' % (fullname)
                continue

            (version, units, xdensity, ydensity) = struct.unpack(FORMAT,
                                                                 data[11:18])

            if (version, units, xdensity, ydensity) == (0x102, 0, 100, 100):
                print '%s ok' % (fullname)
            else:

                print '%s was (%x,%d,%d,%d)' % (fullname,
                                                version,
                                                units,
                                                xdensity,
                                                ydensity)

                data[11:18] = NEW_VALUES

                f = file(fullname, "wb")
                f.write(data)
                f.close()

            del data

if __name__ == '__main__':
    main(sys.argv[1:])

# vim: ts=8 sts=4 sw=4 et
