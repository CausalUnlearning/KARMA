#!/usr/bin/env python

'''
Find the next "best" unsure message to train on.

    %(prog)s [ -h ] [ -s ] [ -b N ] ham spam unsure

Given a number of unsure messages and a desire to keep your training
database small, the question naturally arises, "Which message should I add
to my database next?".  A common approach is to sort the unsures by their
SpamBayes scores and train on the one which scores lowest.  This is a
reasonable approach, but there is no guarantee the lowest scoring unsure is
in any way related to the other unsure messages.

This script offers a different approach.  Given an existing pile of ham and
spam, it trains on them to establish a baseline, then for each message in
the unsure pile, it trains on that message, scores the entire unsure pile
against the resulting training database, then untrains on that message.  For
each such message the following output is generated:

    * spamprob of the candidate message

    * number of other unsure messages which would score as spam if it was
      added to the training database

    * overall mean of all scored messages after training

    * standard deviation of all scored messages after training

    * message-id of the candidate message

With no options, all candidate unsure messages are trained and scored
against.  At the end of the run, a file, "best.pck" is written out which is
a dictionary keyed by the overall mean rounded to three decimal places.  The
values are lists of message-ids which generate that mean.

Three options affect the behavior of the program.  If the -h flag is given,
this help message is displayed and the program exits.  If the -s flag is
given, no messages which score as spam are tested as candidates.  If the -b
N flag is given, only the messages which generated the N highest means in
the last run without the -b flag are tested as candidates.  Because the
program runtime can be very slow (O(n^2) in the number of unsure messages),
if you have a fairly large pile of unsure messages, these options can speed
things up dramatically.  If the -b flag is used, a new "best.pck" file is
not written.  Typically you would run once without the -b flag, then several
times with the -b flag, adding one message to the spam pile after each run.
After adding several messages to your spam file, you might then redistribute
the unsure pile to move spams and hams to their respective folders, then
start again with a smaller unsure pile.

The ham, spam and unsure command line arguments can be anything suitable for
feeding to spambayes.mboxutils.getmbox().  The "best.pck" file is searched
for and written to these files in this order:

    * best.pck in the current directory

    * $HOME/tmp/best.pck

    * $HOME/best.pck

[To do?  Someone might consider the reverse operation.  Given a pile of ham
and spam, which message can be removed with the least impact?  What pile of
mail should that removal be tested against?]

'''

import sys
import os
import getopt
import math

from spambayes.mboxutils import getmbox
from spambayes.classifier import Classifier
from spambayes.hammie import Hammie
from spambayes.tokenizer import tokenize
from spambayes.Options import options
from spambayes import storage
from spambayes.safepickle import pickle_read, pickle_write

cls = Classifier()
h = Hammie(cls)

def counter(tag, i):
    if tag:
        sys.stdout.write("\r%s: %4d" % (tag, i))
    else:
        sys.stdout.write("\r%4d" % i)
    sys.stdout.flush()

def learn(mbox, h, is_spam):
    i = 0
    tag = is_spam and "Spam" or "Ham"
    for msg in getmbox(mbox):
        counter(tag, i)
        i += 1
        h.train(msg, is_spam)
    print

def score(unsure, h, cls, scores, msgids=None, skipspam=False):
    """See what effect on others each msg in unsure has"""

    spam_cutoff = options["Categorization", "spam_cutoff"]

    # compute a base - number of messages in unsure already in the
    # region of interest
    n = 0
    total = 0.0
    okalready = set()
    add = okalready.add
    for msg in getmbox(unsure):
        prob = cls.spamprob(tokenize(msg))
        n += 1
        if prob >= spam_cutoff:
            add(msg['message-id'])
        else:
            total += prob
    first_mean = total/n

    print len(okalready), "out of", n, "messages already score as spam"
    print "initial mean spam prob: %.3f" % first_mean

    print "%5s %3s %5s %5s %s" % ("prob", "new", "mean", "sdev", "msgid")

    # one by one, train on each message and see what effect it has on
    # the other messages in the mailbox
    for msg in getmbox(unsure):
        msgid = msg['message-id']
        if msgids is not None and msgid not in msgids:
            continue

        msgprob = cls.spamprob(tokenize(msg))

        if skipspam and msgprob >= spam_cutoff:
            continue

        n = j = 0
        h.train(msg, True)
        # see how many other messages in unsure now score as spam
        total = 0.0
        probs = []
        for trial in getmbox(unsure):
            # don't score messages which previously scored as spam
            if trial['message-id'] in okalready:
                continue
            n += 1
            if n % 10 == 0:
                counter("", n)
            prob = cls.spamprob(tokenize(trial))
            probs.append(prob)
            total += prob
            if prob >= spam_cutoff:
                j += 1
        counter("", n)
        h.untrain(msg, True)

        mean = total/n
        meankey = round(mean, 3)
        scores.setdefault(meankey, []).append(msgid)

        sdev = math.sqrt(sum([(mean-prob)**2 for prob in probs])/n)

        print "\r%.3f %3d %.3f %.3f %s" % (msgprob, j, mean, sdev, msgid)

prog = os.path.basename(sys.argv[0])

def usage(msg=None):
    if msg is not None:
        print >> sys.stderr, msg
    print >> sys.stderr, __doc__.strip() % globals()

def main(args):
    try:
        opts, args = getopt.getopt(args, "b:sh")
    except getopt.error, msg:
        usage(msg)
        return 1

    best = 0
    skipspam = False
    for opt, arg in opts:
        if opt == "-h":
            usage()
            return 0

        if opt == "-b":
            best = int(arg)
        elif opt == "-s":
            skipspam = True

    if len(args) != 3:
        usage("require ham, spam and unsure message piles")
        return 1

    ham, spam, unsure = args

    choices = ["best.pck"]
    if "HOME" in os.environ:
        home = os.environ["HOME"]
        choices.append(os.path.join(home, "tmp", "best.pck"))
        choices.append(os.path.join(home, "best.pck"))
    choices.append(None)
    for bestfile in choices:
        if bestfile is None:
            break
        if os.path.exists(bestfile):
            break
        try:
            file(bestfile, "w")
        except IOError:
            pass
        else:
            os.unlink(bestfile)

    if bestfile is None:
        usage("can't find a place to write best.pck file")
        return 1

    print "establish base training"

    learn(ham, h, False)
    learn(spam, h, True)

    print "scoring"

    if best:
        last_scores = pickle_read(bestfile)
        last_scores = last_scores.items()
        last_scores.sort()
        msgids = set()
        for (k, v) in last_scores[-best:]:
            msgids.update(set(v))
    else:
        msgids = None
        
    scores = {}
    try:
        score(unsure, h, cls, scores, msgids, skipspam)
    except KeyboardInterrupt:
        # allow early termination without loss of computed scores
        pass

    if not best:
        pickle_write(bestfile, scores)

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
