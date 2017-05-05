#! /usr/bin/env python

"""Split an mbox into N random directories of files.

Usage: %(program)s [-h] [-g] [-s seed] [-v] -n N sourcembox ... outdirbase

Options:
    -h / --help
        Print this help message and exit

    -g
        Do globbing on each sourcepath.  This is helpful on Windows, where
        the native shells don't glob, or when you have more mboxes than
        your shell allows you to specify on the commandline.

    -s seed
        Seed the random number generator with seed (an integer).
        By default, use system time at startup to seed.

    -v
        Verbose.  Displays a period for each 100 messages parsed.
        May display other stuff.

    -n N
        The number of output mboxes desired.  This is required.

    -d  Eliminate duplicates.

Arguments:
    sourcembox
        The mbox or path to an mbox to split.

    outdirbase
        The base path + name prefix for each of the N output dirs.
        Output files have names of the form
            outdirbase + ("Set%%d/%%d" %% (i, n))

Example:
    %(program)s -s 123 -n5 Data/spam.mbox Data/Spam/Set

produces 5 directories, named Data/Spam/Set1 through Data/Spam/Set5.  Each
contains a random selection of the messages in spam.mbox, and together
they contain every message in spam.mbox exactly once.  Each has
approximately the same number of messages.  spam.mbox is not altered.  In
addition, the seed for the random number generator is forced to 123, so
that while the split is random, it's reproducible.
"""

import sys
import os
import random
import getopt
import glob

from spambayes import mboxutils
from spambayes.port import md5

program = sys.argv[0]

def usage(code, msg=''):
    print >> sys.stderr, __doc__ % globals()
    if msg:
        print >> sys.stderr, msg
    sys.exit(code)

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'dhgn:s:v', ['help'])
    except getopt.error, msg:
        usage(1, msg)

    doglob = False
    n = None
    verbose = False
    delete_dups = False
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt == '-g':
            doglob = True
        elif opt == '-s':
            random.seed(int(arg))
        elif opt == '-n':
            n = int(arg)
        elif opt == '-v':
            verbose = True
        elif opt == '-d':
            delete_dups = True

    if n is None or n <= 1:
        usage(1, "an -n value > 1 is required")

    if len(args) < 2:
        usage(1, "input mbox name and output base path are required")
    inputpaths, outputbasepath = args[:-1], args[-1]

    outdirs = [outputbasepath + ("%d" % i) for i in range(1, n+1)]
    for dir in outdirs:
        if not os.path.isdir(dir):
            os.makedirs(dir)

    counter = 0
    cksums = set()
    skipped = 0
    for inputpath in inputpaths:
        if doglob:
            inpaths = glob.glob(inputpath)
        else:
            inpaths = [inputpath]

        for inpath in inpaths:
            mbox = mboxutils.getmbox(inpath)
            for msg in mbox:
                astext = str(msg)
                cksum = md5(astext).hexdigest()
                if delete_dups and cksum in cksums:
                    skipped += 1
                    continue
                cksums.add(cksum)
                i = random.randrange(n)
                #assert astext.endswith('\n')
                counter += 1
                msgfile = open('%s/%d' % (outdirs[i], counter), 'wb')
                msgfile.write(astext)
                msgfile.close()
                if verbose:
                    if counter % 100 == 0:
                        sys.stdout.write('.')
                        sys.stdout.flush()

    if verbose:
        print
        print counter, "messages split into", n, "directories"
        if skipped:
            print "skipped", skipped, "duplicate messages"

if __name__ == '__main__':
    main()
