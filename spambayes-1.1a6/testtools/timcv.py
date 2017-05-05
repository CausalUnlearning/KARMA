#! /usr/bin/env python

# A driver for N-fold cross validation.

"""Usage: %(program)s [options] -n nsets

Where:
    -h
        Show usage and exit.
    -n int
        Number of Set directories (Data/Spam/Set1, ... and Data/Ham/Set1, ...).
        This is required.
    -o section:option:value
        set [section, option] in the options database to value

If you only want to use some of the messages in each set,

    --HamTrain int
        The maximum number of msgs to use from each Ham set for training.
        The msgs are chosen randomly.  See also the -s option.

    --SpamTrain int
        The maximum number of msgs to use from each Spam set for training.
        The msgs are chosen randomly.  See also the -s option.

    --HamTest int
        The maximum number of msgs to use from each Ham set for testing.
        The msgs are chosen randomly.  See also the -s option.

    --SpamTest int
        The maximum number of msgs to use from each Spam set for testing.
        The msgs are chosen randomly.  See also the -s option.

    --ham-keep int
        The maximum number of msgs to use from each Ham set for testing
        and training. The msgs are chosen randomly.  See also the -s option.

    --spam-keep int
        The maximum number of msgs to use from each Spam set for testing
        and training. The msgs are chosen randomly.  See also the -s option.

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

program = sys.argv[0]

def usage(code, msg=''):
    """Print usage message and sys.exit(code)."""
    if msg:
        print >> sys.stderr, msg
        print >> sys.stderr
    print >> sys.stderr, __doc__ % globals()
    sys.exit(code)

def drive(nsets):
    print options.display()

    hamdirs  = [get_pathname_option("TestDriver", "ham_directories") % \
                i for i in range(1, nsets+1)]
    spamdirs = [get_pathname_option("TestDriver", "spam_directories") % \
                i for i in range(1, nsets+1)]

    d = TestDriver.Driver()
    # Train it on all sets except the first.
    d.train(msgs.HamStream("%s-%d" % (hamdirs[1], nsets),
                            hamdirs[1:], train=1),
            msgs.SpamStream("%s-%d" % (spamdirs[1], nsets),
                            spamdirs[1:], train=1))

    # Now run nsets times, predicting pair i against all except pair i.
    for i in range(nsets):
        h = hamdirs[i]
        s = spamdirs[i]
        hamstream = msgs.HamStream(h, [h], train=0)
        spamstream = msgs.SpamStream(s, [s], train=0)

        if i > 0:
            if options["CV Driver", "build_each_classifier_from_scratch"]:
                # Build a new classifier from the other sets.
                d.new_classifier()

                hname = "%s-%d, except %d" % (hamdirs[0], nsets, i+1)
                h2 = hamdirs[:]
                del h2[i]

                sname = "%s-%d, except %d" % (spamdirs[0], nsets, i+1)
                s2 = spamdirs[:]
                del s2[i]

                d.train(msgs.HamStream(hname, h2, train=1),
                        msgs.SpamStream(sname, s2, train=1))

            else:
                # Forget this set.
                d.untrain(hamstream, spamstream)

        # Predict this set.
        d.test(hamstream, spamstream)
        d.finishtest()

        if i < nsets - 1 and not options["CV Driver",
                                         "build_each_classifier_from_scratch"]:
            # Add this set back in.
            d.train(hamstream, spamstream)

    d.alldone()

def main():
    import getopt

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hn:s:o:',
                                   ['HamTrain=', 'SpamTrain=',
                                   'HamTest=', 'SpamTest=',
                                   'ham-keep=', 'spam-keep=',
                                   'option='])
    except getopt.error, msg:
        usage(1, msg)

    nsets = seed = hamtrain = spamtrain = None
    hamtest = spamtest = hamkeep = spamkeep = None
    for opt, arg in opts:
        if opt == '-h':
            usage(0)
        elif opt == '-n':
            nsets = int(arg)
        elif opt == '-s':
            seed = int(arg)
        elif opt == '--HamTest':
            hamtest = int(arg)
        elif opt == '--SpamTest':
            spamtest = int(arg)
        elif opt == '--HamTrain':
            hamtrain = int(arg)
        elif opt == '--SpamTrain':
            spamtrain = int(arg)
        elif opt == '--ham-keep':
            hamkeep = int(arg)
        elif opt == '--spam-keep':
            spamkeep = int(arg)
        elif opt in ('-o', '--option'):
            options.set_from_cmdline(arg, sys.stderr)

    if args:
        usage(1, "Positional arguments not supported")
    if nsets is None:
        usage(1, "-n is required")

    if hamkeep is not None:
        msgs.setparms(hamkeep, spamkeep, seed=seed)
    else:
        msgs.setparms(hamtrain, spamtrain, hamtest, spamtest, seed)
    drive(nsets)

if __name__ == "__main__":
    main()
