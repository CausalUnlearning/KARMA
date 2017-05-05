__author__ = 'Alex'

import os
import sys
import time

sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from spambayes import TestDriver, msgs
from spambayes.Options import get_pathname_option


def main():
    ham = [get_pathname_option("TestDriver", "ham_directories") % i for i in range(1, 5)]
    spam = [get_pathname_option("TestDriver", "spam_directories") % i for i in range(1, 5)]

    t = TestDriver.Driver()
    t.train(msgs.HamStream(ham[1], [ham[1]]), msgs.SpamStream(spam[1], [spam[1]]))

    keep_going = True
    trial_number = 0

    while keep_going:
        start_time = time.time()
        if trial_number == 0:
            t.test(msgs.HamStream(ham[0], [ham[0]]), msgs.SpamStream(spam[0], [spam[0]]), True)

        else:
            t.test(t.tester.truth_examples[1], t.tester.truth_examples[0])
        end_time = time.time()
        seconds = end_time - start_time

        trial_number += 1
        print "Test sizes: ", len(t.tester.truth_examples[0]), ", ", len(t.tester.truth_examples[1]), "\n"
        print "Detection rate:", t.tester.correct_classification_rate(), "\n"
        print "\nTime elapsed:", seconds, "seconds.\n"
        answer = raw_input("Keep trying (y/n)? You have performed " + str(trial_number) + " trial(s) so far. ")

        valid_input = False
        while not valid_input:
            if answer == "y":
                valid_input = True

            elif answer == "n":
                sys.exit()

            else:
                answer = raw_input("Please enter either y or n. ")


main()
