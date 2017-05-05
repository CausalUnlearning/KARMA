#! /usr/bin/env python

"""Split an mbox into N random mboxes.

Usage: %(program)s [-h] [-s seed] [-v] -n N sourcembox outfilebase

Options:
    -h / --help
        Print this help message and exit

    -s seed
        Seed the random number generator with seed (an integer).
        By default, use system time at startup to seed.

    -v
        Verbose.  Displays a period for each 100 messages parsed.
        May display other stuff.

    -n N
        The number of output mboxes desired.  This is required.

Arguments:
    sourcembox
        The mbox to split.

    outfilebase
        The base path + name prefix for each of the N output files.
        Output mboxes have names of the form
            outfilebase + ("%%d.mbox" %% i)

Example:
    %(program)s -s 123 -n5 spam.mbox rspam

produces 5 mboxes, named rspam1.mbox through rspam5.mbox.  Each contains
a random selection of the messages in spam.mbox, and together they contain
every message in spam.mbox exactly once.  Each has approximately the same
number of messages.  spam.mbox is not altered.  In addition, the seed for
the random number generator is forced to 123, so that while the split is
random, it's reproducible.
"""

import sys
import random
import mailbox
import getopt

from spambayes import mboxutils

program = sys.argv[0]

def usage(code, msg=''):
    print >> sys.stderr, __doc__ % globals()
    if msg:
        print >> sys.stderr, msg
    sys.exit(code)

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hn:s:v', ['help'])
    except getopt.error, msg:
        usage(1, msg)

    n = None
    verbose = False
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt == '-s':
            random.seed(int(arg))
        elif opt == '-n':
            n = int(arg)
        elif opt == '-v':
            verbose = True

    if n is None or n <= 1:
        usage(1, "an -n value > 1 is required")

    if len(args) != 2:
        usage(1, "input mbox name and output base path are required")
    inputpath, outputbasepath = args

    infile = file(inputpath, 'rb')
    outfiles = [file(outputbasepath + ("%d.mbox" % i), 'wb')
                for i in range(1, n+1)]

    mbox = mailbox.PortableUnixMailbox(infile, mboxutils.get_message)
    counter = 0
    for msg in mbox:
        i = random.randrange(n)
        astext = str(msg)
        outfiles[i].write(astext)
        counter += 1
        if verbose:
            if counter % 100 == 0:
                print '.',

    if verbose:
        print
        print counter, "messages split into", n, "files"
    infile.close()
    for f in outfiles:
        f.close()

if __name__ == '__main__':
    main()
