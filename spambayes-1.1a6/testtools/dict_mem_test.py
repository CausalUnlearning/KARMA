__author__ = 'Alex'

import os
import sys
import memory_profiler

sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from spambayes import TestDriver, msgs
from spambayes.Options import get_pathname_option

@profile
def main():
    ham = [get_pathname_option("TestDriver", "ham_directories") % i for i in range(1, 5)]
    spam = [get_pathname_option("TestDriver", "spam_directories") % i for i in range(1, 5)]

    t = TestDriver.Driver()
    t.train(msgs.HamStream(ham[0], [ham[0]]), msgs.SpamStream(spam[0], [spam[0]]))
    t.dict_test(msgs.HamStream(ham[2], [ham[2]]), msgs.SpamStream(spam[3], [spam[3]]))
    print "Test sizes: ", len(t.tester.truth_examples[0]), ", ", len(t.tester.truth_examples[1]), "\n"
    print "Detection rate:", t.tester.correct_classification_rate(), "\n"

main()
