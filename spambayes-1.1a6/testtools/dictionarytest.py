import os
import sys
sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from dictionarysets import write_dictionary_sets, reset
from spambayes import TestDriver, msgs
from tabulate import tabulate
from testtools import data_sets as ds


hams, spams = ds.hams, ds.spams
set_dirs, dir_enumerate = ds.set_dirs, ds.dir_enumerate


def test():

    p = [0.05, 0.15, 0.20, 0.25, 0.35]
    s = [13, 26]

    ham = hams[0]
    spam = spams[0]

    ham_test = ham[0]
    spam_test = spam[0]

    ham_train = ham[1]
    spam_train = spam[1]

    d = TestDriver.Driver()
    d.new_classifier()
    d.train(msgs.HamStream(ham_train, [ham_train]),
            msgs.SpamStream(spam_train, [spam_train]))
    p_s = []
    s_s = []
    detection_rates = []
    data_set_counter = 0
    data_sets = range(1, len(p) * len(s) + 1)
    data_set_dirs = ["C:/Users/bzpru/Downloads/Data Sets/Dictionary %d" % i for i in data_sets]

    for size in s:
        for p_val in p:
            p_s.append(p_val)
            s_s.append(size)

            reset(data_set_dirs[data_set_counter])
            write_dictionary_sets(size, x=p_val, y=1000, destination=data_set_dirs[data_set_counter])

            ham_p = []
            spam_p = data_set_dirs[data_set_counter]

            d.train(ham_p,
                    msgs.SpamStream(spam_p, [spam_p]))
            d.test(msgs.HamStream(ham_test, [ham_test]),
                   msgs.SpamStream(spam_test, [spam_test]))

            rate = d.tester.correct_classification_rate()
            detection_rates.append(rate)

            d.untrain(ham_p,
                      msgs.SpamStream(spam_p, [spam_p]))
            data_set_counter += 1

    outfile = open("rates.txt", 'w')
    outfile.write(tabulate({"# of Sets": s_s,
                            "Percent Correlation": p_s,
                            "Detection Rate": detection_rates},
                           headers="keys"))


def main():
    test()

if __name__ == "__main__":
    test()
