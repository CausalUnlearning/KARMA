# Loop:
#     Optional:
#         # Set up a new base classifier for testing.
#         new_classifier(), or set_classifier()
#     # Run tests against (possibly variants of) this classifier.
#     Loop:
#         Loop:
#             Optional:
#                 # train on more ham and spam
#                 train(ham, spam)
#             Optional:
#                 # Forget training for some subset of ham and spam.
#                 untrain(ham, spam)
#         # Predict against other data.
#         Loop:
#             test(ham, spam)
#         # Display stats against all runs on this classifier variant.
#         # This also saves the trained classifer, if desired (option
#         # save_trained_pickles).
#         finishtest()
# # Display stats against all runs.
# alldone()

from spambayes.Options import options
from spambayes import Tester
from spambayes import classifier
from spambayes.Histogram import Hist
from spambayes.safepickle import pickle_write

def printhist(tag, ham, spam, nbuckets=options["TestDriver", "nbuckets"]):
    print
    print "-> <stat> Ham scores for", tag,
    ham.display(nbuckets)

    print
    print "-> <stat> Spam scores for", tag,
    spam.display(nbuckets)

    if not options["TestDriver", "compute_best_cutoffs_from_histograms"]:
        return
    if ham.n == 0 or spam.n == 0:
        return

    # Figure out "the best" ham & spam cutoff points, meaning the ones that
    # minimize
    #    num_fp * fp_weight + num_fn + fn_weight + num_unsure * unsure_weight
    # the total number of misclassified msgs (other definitions are
    # certainly possible!).

    # At cutoff 0, everything is called spam, so there are no false negatives,
    # and every ham is a false positive.
    assert ham.nbuckets == spam.nbuckets
    n = ham.nbuckets
    FPW = options["TestDriver", "best_cutoff_fp_weight"]
    FNW = options["TestDriver", "best_cutoff_fn_weight"]
    UNW = options["TestDriver", "best_cutoff_unsure_weight"]

    # Get running totals:  {h,s}total[i] is # of ham/spam below bucket i
    htotal = [0] * (n+1)
    stotal = [0] * (n+1)
    for i in range(1, n+1):
        htotal[i] = htotal[i-1] + ham.buckets[i-1]
        stotal[i] = stotal[i-1] + spam.buckets[i-1]
    assert htotal[-1] == ham.n
    assert stotal[-1] == spam.n

    best_cost = 1e200   # infinity
    bests = []          # best h and s cutoffs

    for h in range(n+1):
        num_fn = stotal[h]
        fn_cost = num_fn * FNW
        for s in xrange(h, n+1):
            # ham  0:h  correct
            #      h:s  unsure
            #      s:   FP
            # spam 0:h  FN
            #      h:s  unsure
            #      s:   correct
            num_fp = htotal[-1] - htotal[s]
            num_un = htotal[s] - htotal[h] + stotal[s] - stotal[h]
            cost = num_fp * FPW + fn_cost + num_un * UNW
            if cost <= best_cost:
                if cost < best_cost:
                    best_cost = cost
                    bests = []
                bests.append((h, s))

    print '-> best cost for %s $%.2f' % (tag, best_cost)
    print '-> per-fp cost $%.2f; per-fn cost $%.2f; per-unsure cost $%.2f' % (
          FPW, FNW, UNW)

    if len(bests) > 1:
        print '-> achieved at', len(bests), 'cutoff pairs'
        info = [('smallest ham & spam cutoffs', bests[0]),
                ('largest ham & spam cutoffs', bests[-1])]
    else:
        info = [('achieved at ham & spam cutoffs', bests[0])]

    for tag, (h, s) in info:
        print '-> %s %g & %g' % (tag, float(h)/n, float(s)/n)
        num_fn = stotal[h]
        num_fp = htotal[-1] - htotal[s]
        num_unh = htotal[s] - htotal[h]
        num_uns = stotal[s] - stotal[h]
        print '->     fp %d; fn %d; unsure ham %d; unsure spam %d' % (
              num_fp, num_fn, num_unh, num_uns)
        print '->     fp rate %.3g%%; fn rate %.3g%%; unsure rate %.3g%%' % (
              num_fp*1e2 / ham.n, num_fn*1e2 / spam.n,
              (num_unh + num_uns)*1e2 / (ham.n + spam.n))

    return float(bests[0][0])/n, float(bests[0][1])/n


def printmsg(msg, prob, clues):
    print msg.tag
    print "prob =", prob
    for clue in clues:
        print "prob(%r) = %g" % clue
    print
    guts = str(msg)
    if options["TestDriver", "show_charlimit"] > 0:
        guts = guts[:options["TestDriver", "show_charlimit"]]
    print guts


class Driver:

    def __init__(self):
        self.falsepos = set()
        self.falseneg = set()
        self.unsure = set()
        self.global_ham_hist = Hist()
        self.global_spam_hist = Hist()
        self.ntimes_finishtest_called = 0
        self.new_classifier()
        from spambayes import CostCounter
        self.cc = CostCounter.default()

    def new_classifier(self):
        """Create and use a new, virgin classifier."""
        self.set_classifier(classifier.Bayes())

    def set_classifier(self, classifier):
        """Specify a classifier to be used for further testing."""
        self.classifier = classifier
        self.tester = Tester.Test(classifier)
        self.trained_ham_hist = Hist()
        self.trained_spam_hist = Hist()

    def train(self, ham, spam):
        try:
            print "-> Training on ham of size " + str(len(ham)) + " & spam of size " + str(len(spam)) +  " ..."
        except TypeError:
            print "-> Training on", ham, "&", spam, "..."

        c = self.classifier
        nham, nspam = c.nham, c.nspam
        self.tester.train(ham, spam)
        print c.nham - nham, "hams &", c.nspam - nspam, "spams" # c.nham - nham gives number of new emails trained on 

    def untrain(self, ham, spam):
        try:
            print "-> Forgetting ham of size " + str(len(ham)) + " & spam of size " + str(len(spam)) +  " ..."
        except TypeError:
            print "-> Forgetting", ham, "&", spam, "..."
        c = self.classifier
        nham, nspam = c.nham, c.nspam
        self.tester.untrain(ham, spam)
        print nham - c.nham, "hams &", nspam - c.nspam, "spams"

    def finishtest(self):
        if options["TestDriver", "show_histograms"]:
            printhist("all in this training set:",
                      self.trained_ham_hist, self.trained_spam_hist)
        self.global_ham_hist += self.trained_ham_hist
        self.global_spam_hist += self.trained_spam_hist
        self.trained_ham_hist = Hist()
        self.trained_spam_hist = Hist()

        self.ntimes_finishtest_called += 1
        if options["TestDriver", "save_trained_pickles"]:
            fname = "%s%d.pik" % (options["TestDriver", "pickle_basename"],
                                  self.ntimes_finishtest_called)
            print "    saving pickle to", fname
            pickle_write(fname, self.classifier, 1)

    def alldone(self):
        if options["TestDriver", "show_histograms"]:
            besthamcut, bestspamcut = printhist("all runs:",
                                                self.global_ham_hist,
                                                self.global_spam_hist)
        else:
            besthamcut = options["Categorization", "ham_cutoff"]
            bestspamcut = options["Categorization", "spam_cutoff"]
            self.global_ham_hist.compute_stats()
            self.global_spam_hist.compute_stats()
        nham = self.global_ham_hist.n
        nspam = self.global_spam_hist.n
        nfp = len(self.falsepos)
        nfn = len(self.falseneg)
        nun = len(self.unsure)
        print "-> <stat> all runs false positives:", nfp
        print "-> <stat> all runs false negatives:", nfn
        print "-> <stat> all runs unsure:", nun
        print "-> <stat> all runs false positive %:", (nfp * 1e2 / nham)
        print "-> <stat> all runs false negative %:", (nfn * 1e2 / nspam)
        print "-> <stat> all runs unsure %:", (nun * 1e2 / (nham + nspam))
        print "-> <stat> all runs cost: $%.2f" % (
              nfp * options["TestDriver", "best_cutoff_fp_weight"] +
              nfn * options["TestDriver", "best_cutoff_fn_weight"] +
              nun * options["TestDriver", "best_cutoff_unsure_weight"])
        # Set back the options for the delayed calculations in self.cc
        options["Categorization", "ham_cutoff"] = besthamcut
        options["Categorization", "spam_cutoff"] = bestspamcut
        print self.cc

        if options["TestDriver", "save_histogram_pickles"]:
            for f, h in (('ham', self.global_ham_hist),
                         ('spam', self.global_spam_hist)):
                fname = "%s_%shist.pik" % (options["TestDriver",
                                                   "pickle_basename"], f)
                print "    saving %s histogram pickle to %s" % (f, fname)
                pickle_write(fname, h, 1)

    def test(self, ham, spam, init_ground=False, update=True, all_opt=False):
        c = self.classifier
        t = self.tester
        local_ham_hist = Hist()
        local_spam_hist = Hist()

        def new_ham(msg, prob, lo=options["TestDriver", "show_ham_lo"],
                               hi=options["TestDriver", "show_ham_hi"]):
            local_ham_hist.add(prob * 100.0)
            self.cc.ham(prob)
            if lo <= prob <= hi:
                print
                print "Ham with prob =", prob
                prob, clues = c.spamprob(msg, True, update=update, all_opt=all_opt)
                printmsg(msg, prob, clues)

        def new_spam(msg, prob, lo=options["TestDriver", "show_spam_lo"],
                                hi=options["TestDriver", "show_spam_hi"]):
            local_spam_hist.add(prob * 100.0)
            self.cc.spam(prob)
            if lo <= prob <= hi:
                print
                print "Spam with prob =", prob
                prob, clues = c.spamprob(msg, True, update=update, all_opt=all_opt)
                printmsg(msg, prob, clues)

        t.reset_test_results()
        try:
            print "-> Predicting ham of size " + str(len(ham)) + " & spam of size " + str(len(spam)) +  " ..."

        except TypeError:
            print "-> Predicting", ham, "&", spam, "..."

        t.predict(spam, True, init_ground, new_spam, update=update)
        t.predict(ham, False, init_ground, new_ham, update=update)
        print "-> <stat> tested", t.nham_tested, "hams &", t.nspam_tested, \
              "spams against", c.nham, "hams &", c.nspam, "spams"

        print "-> <stat> false positive %:", t.false_positive_rate()
        print "-> <stat> false negative %:", t.false_negative_rate()
        print "-> <stat> unsure %:", t.unsure_rate()
        print "-> <stat> cost: $%.2f" % (
               t.nham_wrong * options["TestDriver", "best_cutoff_fp_weight"] +
               t.nspam_wrong * options["TestDriver", "best_cutoff_fn_weight"] +
               (t.nham_unsure + t.nspam_unsure) *
               options["TestDriver", "best_cutoff_unsure_weight"])

        newfpos = set(t.false_positives()) - self.falsepos
        self.falsepos |= newfpos
        print "-> <stat> %d total false positives" % len(set(t.false_positives()))

        """
        if newfpos:
            print "    new fp:", [e.tag for e in newfpos]
        """
        if not options["TestDriver", "show_false_positives"]:
            newfpos = ()
        """
        for e in newfpos:
            print '*' * 78
            prob, clues = c.spamprob(e, True)
            printmsg(e, prob, clues)
        """
        newfneg = set(t.false_negatives()) - self.falseneg
        self.falseneg |= newfneg
        print "-> <stat> %d total false negatives" % len(set(t.false_negatives()))

        """
        if newfneg:
            print "    new fn:", [e.tag for e in newfneg]
        """
        if not options["TestDriver", "show_false_negatives"]:
            newfneg = ()
        """
        for e in newfneg:
            print '*' * 78
            prob, clues = c.spamprob(e, True)
            printmsg(e, prob, clues)
        """
        newunsure = set(t.unsures()) - self.unsure
        self.unsure |= newunsure

        print "-> <stat> %d total unsure" % len(set(t.unsures()))

        """
        if newunsure:
            print "    new unsure:", [e.tag for e in newunsure]
        """
        if not options["TestDriver", "show_unsure"]:
            newunsure = ()
        """
        for e in newunsure:
            print '*' * 78
            prob, clues = c.spamprob(e, True)
            printmsg(e, prob, clues)
        """
        if options["TestDriver", "show_histograms"]:
            printhist("this pair:", local_ham_hist, local_spam_hist)
        self.trained_ham_hist += local_ham_hist
        self.trained_spam_hist += local_spam_hist

    def train_test(self, ham, spam, update=False, all_opt=False):
        c = self.classifier
        t = self.tester
        local_ham_hist = Hist()
        local_spam_hist = Hist()

        t.reset_test_results()
        print "-> Predicting", ham, "&", spam, "..."
        t.train_predict(spam, 0, update=update, all_opt=all_opt)
        t.train_predict(ham, 1, update=update, all_opt=all_opt)

    def pol_test(self, ham, spam, update=False, all_opt=False):
        c = self.classifier
        t = self.tester
        local_ham_hist = Hist()
        local_spam_hist = Hist()

        t.reset_test_results()
        print "-> Predicting", ham, "&", spam, "..."
        t.train_predict(ham, 3, update=update, all_opt=all_opt)
        t.train_predict(spam, 2, update=update, all_opt=all_opt)
