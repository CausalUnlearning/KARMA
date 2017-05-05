__author__ = 'Alex'

import os
import sys
import time

sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from spambayes import ActiveUnlearnDriver
from spambayes.Options import options
from spambayes import msgs
from testtools import data_sets as ds

options["TestDriver", "show_histograms"] = False
dir_enumerate = ds.dir_enumerate
seterize = ds.seterize
seconds_to_english = ds.seconds_to_english
hams = ds.hams
spams = ds.spams
set_dirs = ds.set_dirs


class ProxyCluster:
    def __init__(self, emails):
        self.size = len(emails)
        self.ham = set()
        self.spam = set()
        for msg in emails:
            if msg.train == 1 or msg.train == 3:
                self.ham.add(msg)
            elif msg.train == 0 or msg.train == 2:
                self.spam.add(msg)
            else:
                raise AssertionError


def main():
    num_data_sets = len(hams)
    assert(len(hams) == len(spams))
    sets = [0]

    for i in sets:
        ham = hams[i]
        spam = spams[i]

        ham_test = ham[0]
        spam_test = spam[0]

        ham_train = ham[1]
        spam_train = spam[1]

        ham_p = ham[2]
        spam_p = spam[2]

        try:
            au = ActiveUnlearnDriver.ActiveUnlearner([msgs.HamStream(ham_train, [ham_train]),
                                                      msgs.HamStream(ham_p, [ham_p])],        # Training Ham
                                                     [msgs.SpamStream(spam_train, [spam_train]),
                                                      msgs.SpamStream(spam_p, [spam_p])],     # Training Spam
                                                     msgs.HamStream(ham_test, [ham_test]),          # Testing Ham
                                                     msgs.SpamStream(spam_test, [spam_test]),       # Testing Spam
                                                     )

            print "Unlearning..."
            cluster = ProxyCluster(au.driver.tester.train_examples[2])
            au.unlearn(cluster)
            """
            time_1 = time.time()
            for i in range(10):
                au.init_ground(update=False)
            time_2 = time.time()
            avg_no_update = float(time_2 - time_1) / 10
            no_update_rate = au.driver.tester.correct_classification_rate()
            time_3 = time.time()
            for i in range(10):
                au.init_ground(update=True)
            time_4 = time.time()
            avg_update = float(time_4 - time_3) / 10
            update_rate = au.driver.tester.correct_classification_rate()
            print "Average test without update: " + str(avg_no_update)
            print "Average test with update: " + str(avg_update)
            print "Detection rate without update: " + str(no_update_rate)
            print "Detection rate with update: " + str(update_rate)
            """
            au.init_ground(update=False)
            au.init_ground(update=True)
            au.driver.tester.correct_classification_rate()
        except KeyboardInterrupt:
            sys.exit()

if __name__ == "__main__":
    main()
