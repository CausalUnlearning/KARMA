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
from spambayes import Distance
from testtools import benignfilemover, mislabeledfilemover, dictionarywriter
from scipy.stats import pearsonr
from math import sqrt

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

    r = mislabeledfilemover.MislabeledFileMover(num)
    r.random_move_file()

    d = TestDriver.Driver()
    d.new_classifier()
    d.train(msgs.HamStream(hamdirs[0], [hamdirs[0]]),
            msgs.SpamStream(spamdirs[0], [spamdirs[0]]))
    d.train(msgs.HamStream(hamdirs[2], [hamdirs[2]]),
            msgs.SpamStream(spamdirs[2], [spamdirs[2]]))
    d.test(msgs.HamStream(hamdirs[1], [hamdirs[1]]),
           msgs.SpamStream(spamdirs[1], [spamdirs[1]]))

    guess = d.classifier.spamprob
    polluted = []
    for msg in msgs.HamStream(hamdirs[2], [hamdirs[2]]):
        msg.prob = guess(msg)
        polluted.append(msg)

    for msg in msgs.SpamStream(spamdirs[2], [spamdirs[2]]):
        msg.prob = guess(msg)
        polluted.append(msg)

    mislabeled = []
    for fp in d.tester.false_positives():
        mislabeled.append(fp)

    for fn in d.tester.false_negatives():
        mislabeled.append(fn)

    for unsure in d.unsure:
        mislabeled.append(unsure)

    d.finishtest()
    d.alldone()

    data = v_correlation(polluted, mislabeled)

    print "Percentage Overlap (Correlation): " + str(data)


def p_correlation(polluted, mislabeled):
    """Uses Pearson's Correlation Coefficient to calculate correlation
     between mislabeled results and initial polluted emails in ground truth"""

    n = min(len(polluted), len(mislabeled))

    x = []
    for i in range(0, n):
        x.append(polluted[i].prob)

    y = []
    for i in range(0, n):
        y.append(mislabeled[i].prob)

    return pearsonr(x, y)


def v_correlation(polluted, mislabeled):

    print "Calculating Polluted Data Clustroid..."

    p_minrowsum = sys.maxint
    p_clustroid = None
    p_avgdistance = 0
    i = 1
    for email in polluted:
        print "Calculating on email " + str(i) + " of " + str(len(polluted))
        rowsum = 0
        for email2 in polluted:
            if email == email2:
                continue
            dist = Distance.distance(email, email2, "extreme")
            rowsum += dist ** 2
        if rowsum < p_minrowsum:
            p_minrowsum = rowsum
            p_clustroid = email
            p_avgdistance = sqrt(rowsum / (len(polluted) - 1))
        i += 1

    print "Calculating Mislabeled Data Clustroid..."

    m_minrowsum = sys.maxint
    m_clustroid = None
    m_avgdistance = 0
    i = 1
    for email in mislabeled:
        print "Calculating on email " + str(i) + " of " + str(len(mislabeled))
        rowsum = 0
        for email2 in mislabeled:
            if email == email2:
                continue
            dist = Distance.distance(email, email2, "extreme")
            rowsum += dist ** 2
        if rowsum < m_minrowsum:
            m_minrowsum = rowsum
            m_clustroid = email
            m_avgdistance = sqrt(rowsum / (len(polluted) - 1))
        i += 1

    print "Calculating Overlap..."

    p_size = 0
    i = 1
    for email in polluted:
        print "Scanning Polluted Email " + str(i) + " of " + str(len(polluted))
        if Distance.distance(email, m_clustroid, "extreme") < m_avgdistance:
            p_size += 1
        i += 1
    m_size = 0
    i = 1
    for email in mislabeled:
        print "Scanning Mislabeled Email " + str(i) + " of " + str(len(mislabeled))
        if Distance.distance(email, p_clustroid, "extreme") < p_avgdistance:
            m_size += 1
        i += 1

    total_size = len(polluted) + len(mislabeled)

    print "Total Size: " + str(total_size)
    print "Size of Polluted Overlap: " + str(p_size)
    print "Size of Mislabeled Overlap: " + str(m_size)

    return (float(p_size) + float(m_size)) / float(total_size)


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
