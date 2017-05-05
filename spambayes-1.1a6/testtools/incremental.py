"""incremental.py

This is a test harness for doing testing of incremental
training regimes.  The individual regimes used should
be specified in regime.py.

Options:
  -h  --help         Display this message.
  -r [regime]        Use this regime (default: perfect).
  -s [number]        Run only this set.
"""

###
### This is a test harness for doing testing of incremental
### training regimes.  The individual regimes used should
### be specified in regime.py; see the perfect and
### corrected classes for examples.
###

import getopt
import glob
import os
import sys

sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from spambayes.Options import options
from spambayes import classifier
from spambayes import msgs
import email
from email import Message
from testtools import regimes

class Test:
    # Pass a classifier instance (an instance of Bayes).
    # Loop:
    #     # Train the classifer with new ham and spam.
    #     train(ham, spam) # this implies reset_test_results
    #     Loop:
    #         Optional:
    #             # Possibly fiddle the classifier.
    #             set_classifier()
    #             # Forget smessages the classifier was trained on.
    #             untrain(ham, spam) # this implies reset_test_results
    #         Optional:
    #             reset_test_results()
    #         # Predict against (presumably new) examples.
    #         predict(ham, spam)
    #         Optional:
    #             suck out the results, via instance vrbls and
    #             false_negative_rate(), false_positive_rate(),
    #             false_negatives(), and false_positives()

    def __init__(self, classifier):
        self.set_classifier(classifier)
        self.reset_test_results()

    # Tell the tester which classifier to use.
    def set_classifier(self, classifier):
        self.classifier = classifier

    def reset_test_results(self):
        # The number of ham and spam instances tested.
        self.nham_tested = self.nspam_tested = 0

        # The number of ham and spam instances trained.
        self.nham_trained = self.nspam_trained = 0

        # The number of test instances correctly and incorrectly classified.
        self.nham_right = 0
        self.nham_wrong = 0
        self.nham_unsure = 0
        self.nspam_right = 0
        self.nspam_wrong = 0
        self.nspam_unsure = 0

        # Lists of bad predictions.
        self.ham_wrong_examples = []    # False positives:  ham called spam.
        self.spam_wrong_examples = []   # False negatives:  spam called ham.
        self.unsure_examples = []       # ham and spam in middle ground

    # Train the classifier on streams of ham and spam.
    def train(self, hamstream=None, spamstream=None):
        learn = self.classifier.learn
        if hamstream is not None:
            for example in hamstream:
                learn(example, False)
                self.nham_trained += 1
        if spamstream is not None:
            for example in spamstream:
                learn(example, True)
                self.nspam_trained += 1

    # Untrain the classifier on streams of ham and spam.
    def untrain(self, hamstream=None, spamstream=None):
        unlearn = self.classifier.unlearn
        if hamstream is not None:
            for example in hamstream:
                unlearn(example, False)
                self.nham_trained -= 1
        if spamstream is not None:
            for example in spamstream:
                unlearn(example, True)
                self.nspam_trained -= 1

    # Run prediction on each sample in stream.  You're swearing that stream
    # is entirely composed of spam (is_spam True), or of ham (is_spam False).
    # Note that mispredictions are saved, and can be retrieved later via
    # false_negatives (spam mistakenly called ham) and false_positives (ham
    # mistakenly called spam).  For this reason, you may wish to wrap examples
    # in a little class that identifies the example in a useful way, and whose
    # __iter__ produces a token stream for the classifier.
    #
    def predict(self, stream, is_spam):
        guess = self.classifier.spamprob
        for example in stream:
            prob = guess(example)
            is_ham_guessed  = prob <  options["Categorization", "ham_cutoff"]
            is_spam_guessed = prob >= options["Categorization", "spam_cutoff"]
            if is_spam:
                self.nspam_tested += 1
                if is_spam_guessed:
                    self.nspam_right += 1
                elif is_ham_guessed:
                    self.nspam_wrong += 1
                    self.spam_wrong_examples.append(example)
                else:
                    self.nspam_unsure += 1
                    self.unsure_examples.append(example)
            else:
                self.nham_tested += 1
                if is_ham_guessed:
                    self.nham_right += 1
                elif is_spam_guessed:
                    self.nham_wrong += 1
                    self.ham_wrong_examples.append(example)
                else:
                    self.nham_unsure += 1
                    self.unsure_examples.append(example)

        assert (self.nham_right + self.nham_wrong + self.nham_unsure ==
                self.nham_tested)
        assert (self.nspam_right + self.nspam_wrong + self.nspam_unsure ==
                self.nspam_tested)
        num = 0
        if is_ham_guessed:
            num = 1
        if is_spam_guessed:
            num = -1
        return (num, prob)

    def false_positive_rate(self):
        """Percentage of ham mistakenly identified as spam, in 0.0..100.0."""
        return self.nham_wrong * 1e2 / (self.nham_tested or 1)

    def false_negative_rate(self):
        """Percentage of spam mistakenly identified as ham, in 0.0..100.0."""
        return self.nspam_wrong * 1e2 / (self.nspam_tested or 1)

    def unsure_rate(self):
        return ((self.nham_unsure + self.nspam_unsure) * 1e2 /
                ((self.nham_tested + self.nspam_tested) or 1))

    def false_positives(self):
        return self.ham_wrong_examples

    def false_negatives(self):
        return self.spam_wrong_examples

    def unsures(self):
        return self.unsure_examples

class _Example:
    def __init__(self, name, words):
        self.name = name
        self.words = words
    def __iter__(self):
        return iter(self.words)

_easy_test = """
    >>> from spambayes.classifier import Bayes
    >>> from spambayes.Options import options
    >>> options["Categorization", "ham_cutoff"] = options["Categorization", "spam_cutoff"] = 0.5

    >>> good1 = _Example('', ['a', 'b', 'c'])
    >>> good2 = _Example('', ['a', 'b'])
    >>> bad1 = _Example('', ['c', 'd'])

    >>> t = Test(Bayes())
    >>> t.train([good1, good2], [bad1])
    >>> t.predict([_Example('goodham', ['a', 'b']),
    ...            _Example('badham', ['d'])    # FP
    ...           ], False)
    >>> t.predict([_Example('goodspam', ['d']),
    ...            _Example('badspam1', ['a']), # FN
    ...            _Example('badspam2', ['a', 'b']),    # FN
    ...            _Example('badspam3', ['d', 'a', 'b'])    # FN
    ...           ], True)

    >>> t.nham_tested
    2
    >>> t.nham_right, t.nham_wrong
    (1, 1)
    >>> t.false_positive_rate()
    50.0
    >>> [e.name for e in t.false_positives()]
    ['badham']

    >>> t.nspam_tested
    4
    >>> t.nspam_right, t.nspam_wrong
    (1, 3)
    >>> t.false_negative_rate()
    75.0
    >>> [e.name for e in t.false_negatives()]
    ['badspam1', 'badspam2', 'badspam3']

    >>> [e.name for e in t.unsures()]
    []
    >>> t.unsure_rate()
    0.0
"""

__test__ = {'easy': _easy_test}

def _test():
    import doctest, Tester
    doctest.testmod(Tester)


def group_perfect(which, test):
    pass

def guess_perfect(which, test, guess, actual, msg):
    return actual


spam_to_ham = []
ham_to_spam = []
unsure_to_ham = []
unsure_to_spam = []

def group_corrected(which, test):
    global spam_to_ham
    global ham_to_spam
    global unsure_to_ham
    global unsure_to_spam
    test.untrain(ham_to_spam[which], spam_to_ham[which])
    test.train(spam_to_ham[which], ham_to_spam[which])
    test.train(unsure_to_ham[which], unsure_to_spam[which])

def guess_corrected(which, test, guess, actual, msg):
    global spam_to_ham
    global ham_to_spam
    global unsure_to_ham
    global unsure_to_spam
    if guess[0] != actual:
        if actual < 0:
            if guess == 0:
                try:
                    unsure_to_spam[which].append(msg)
                except:
                    unsure_to_spam[which] = [msg]
            else:
                try:
                    ham_to_spam[which].append(msg)
                except:
                    ham_to_spam[which] = [msg]
        else:
            if guess == 0:
                try:
                    unsure_to_ham[which].append(msg)
                except:
                    unsure_to_ham[which] = [msg]
            else:
                try:
                    spam_to_ham[which].append(msg)
                except:
                    spam_to_ham[which] = [msg]
    return guess[0]




def main():
    group_action = None
    guess_action = None

    regime = "perfect"
    which = None

    opts, args = getopt.getopt(sys.argv[1:], 'hs:r:', ['help', 'examples'])
    for opt, arg in opts:
        if opt == '-s':
            which = int(arg) - 1
        elif opt == '-r':
            regime = arg
        elif opt == '-h' or opt == '--help':
            print __doc__
            sys.exit()

    nsets = len(glob.glob("Data/Ham/Set*"))

    files = glob.glob("Data/*/Set*/*")
    files.sort(lambda a,b: cmp(os.path.basename(a), os.path.basename(b)))

    tests = []
    rules = []
    nham_tested = []
    nham_trained = []
    nham_right = []
    nham_wrong = []
    nham_unsure = []
    nspam_tested = []
    nspam_trained = []
    nspam_right = []
    nspam_wrong = []
    nspam_unsure = []
    for j in range(0, nsets):
        # if which is not None and j != which:
        #     continue
        tests.append(Test(classifier.Bayes()))
        exec """rules.append(regimes.%s())""" % (regime) in globals(), locals()
        nham_tested.append([])
        nham_trained.append([])
        nham_right.append([])
        nham_wrong.append([])
        nham_unsure.append([])
        nspam_tested.append([])
        nspam_trained.append([])
        nspam_right.append([])
        nspam_wrong.append([])
        nspam_unsure.append([])

    oldgroup = 0
    for f in files:
        base = os.path.basename(f)
        group = int(base.split('-')[0]);
        dir = os.path.dirname(f)
        set = os.path.basename(dir)
        set = int(set[3:]) - 1
        isspam = (dir.find('Spam') >= 0)

        msg = msgs.Msg(dir, base)

        for j in range(0, nsets):
            if which is not None and j != which:
                continue
            if group != oldgroup:
                sys.stderr.write("%-78s\r" % ("%s  : %d" % (base, set)))
                sys.stderr.flush()

                nham_tested[j].append(tests[j].nham_tested)
                nham_trained[j].append(tests[j].nham_trained)
                nham_right[j].append(tests[j].nham_right)
                nham_wrong[j].append(tests[j].nham_wrong)
                nham_unsure[j].append(tests[j].nham_unsure)
                nspam_tested[j].append(tests[j].nspam_tested)
                nspam_trained[j].append(tests[j].nspam_trained)
                nspam_right[j].append(tests[j].nspam_right)
                nspam_wrong[j].append(tests[j].nspam_wrong)
                nspam_unsure[j].append(tests[j].nspam_unsure)
                # tests[j].reset_test_results()
                rules[j].group_action(j, tests[j])

            if j != set:
                guess = tests[j].predict([msg], isspam)
                if isspam:
                    actual = -1
                else:
                    actual = 1
                todo = rules[j].guess_action(j, tests[j], guess, actual, msg)
                if todo == -1:
                    tests[j].train(None, [msg])
                elif todo == 1:
                    tests[j].train([msg], None)

        oldgroup = group

    sys.stderr.write("\n")
    sys.stderr.flush()

    for j in range(0, nsets):
        if which is not None and j != which:
            continue
        nham_tested[j].append(tests[j].nham_tested)
        nham_trained[j].append(tests[j].nham_trained)
        nham_right[j].append(tests[j].nham_right)
        nham_wrong[j].append(tests[j].nham_wrong)
        nham_unsure[j].append(tests[j].nham_unsure)
        nspam_tested[j].append(tests[j].nspam_tested)
        nspam_trained[j].append(tests[j].nspam_trained)
        nspam_right[j].append(tests[j].nspam_right)
        nspam_wrong[j].append(tests[j].nspam_wrong)
        nspam_unsure[j].append(tests[j].nspam_unsure)

    for j in range(0, nsets):
        if which is not None and j != which:
            continue
        print 'Set %d' % (j + 1)
        for k in range(0, len(nham_tested[j])):
            print '%d %d %d %d %d %d %d %d %d %d' % (
                nham_tested[j][k],
                nham_trained[j][k],
                nham_right[j][k],
                nham_wrong[j][k],
                nham_unsure[j][k],
                nspam_tested[j][k],
                nspam_trained[j][k],
                nspam_right[j][k],
                nspam_wrong[j][k],
                nspam_unsure[j][k]
            )
        print

    print '$ end'

if __name__ == '__main__':
    main()
