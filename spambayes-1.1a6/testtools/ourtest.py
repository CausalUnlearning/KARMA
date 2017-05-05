
# A test driver using "the standard" test directory structure.  See also
# rates.py and cmp.py for summarizing results.  This runs an NxN test grid,
# skipping the diagonal.

"""Usage: %(program)s  [options] -n nsets

Where:
    -h
        Show usage and exit.
    -n int
        Number of Set directories (Data/Spam/Set1, ... and Data/Ham/Set1, ...).
        This is required.

If you only want to use some of the messages in each set,

    --ham-keep int
        The maximum number of msgs to use from each Ham set.  The msgs are
        chosen randomly.  See also the -s option.

    --spam-keep int
        The maximum number of msgs to use from each Spam set.  The msgs are
        chosen randomly.  See also the -s option.

    -s int
        A seed for the random number generator.  Has no effect unless
        at least one of {--ham-keep, --spam-keep} is specified.  If -s
        isn't specifed, the seed is taken from current time.

In addition, an attempt is made to merge bayescustomize.ini into the options.
If that exists, it can be used to change the settings in Options.options.
"""

from __future__ import generators

import os
import sys

sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from spambayes.Options import options, get_pathname_option
from spambayes import TestDriver
from spambayes import msgs
from testtools import benignfilemover, mislabeledfilemover, dictionarywriter, InjectionPollution

program = sys.argv[0]


def usage(code, msg=''):
    """Print usage message and sys.exit(code)."""
    if msg:
        print >> sys.stderr, msg
        print >> sys.stderr
    print >> sys.stderr, __doc__ % globals()
    sys.exit(code)


def drive(num):
    print options.display()

    spamdirs = [get_pathname_option("TestDriver", "spam_directories") %
                i for i in range(1, 4)]
    hamdirs = [get_pathname_option("TestDriver", "ham_directories") %
               i for i in range(1, 4)]

    d = TestDriver.Driver()
    d.new_classifier()
    d.train(msgs.HamStream(hamdirs[0], [hamdirs[0]]),
            msgs.SpamStream(spamdirs[0], [spamdirs[0]]))
    d.train(msgs.HamStream(hamdirs[2], [hamdirs[2]]),
            msgs.SpamStream(spamdirs[2], [spamdirs[2]]))
    d.test(msgs.HamStream(hamdirs[1], [hamdirs[1]]),
           msgs.SpamStream(spamdirs[1], [spamdirs[1]]))

    d.finishtest()
    d.alldone()


def main():
    import getopt

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hn:s:',
                                   ['ham-keep=', 'spam-keep='])
    except getopt.error, msg:
        usage(1, msg)

    nsets = seed = hamkeep = spamkeep = None
    for opt, arg in opts:
        if opt == '-h':
            usage(0)
        elif opt == '-n':
            nsets = int(arg)
        elif opt == '-s':
            seed = int(arg)
        elif opt == '--ham-keep':
            hamkeep = int(arg)
        elif opt == '--spam-keep':
            spamkeep = int(arg)

    if args:
        usage(1, "Positional arguments not supported")
    if nsets is None:
        usage(1, "-n is required")

    msgs.setparms(hamkeep, spamkeep, seed=seed)
    drive(nsets)

if __name__ == "__main__":
    main()
