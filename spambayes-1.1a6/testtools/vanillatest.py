import os
import sys

sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from spambayes.Options import get_pathname_option
from spambayes import msgs, TestDriver
from tabulate import tabulate
from mislabeledfilemover import MislabeledFileMover
from dictionarywriter import DictionaryWriter
from dictionarysets import write_dictionary_sets

def main():

    ham = [get_pathname_option("TestDriver", "ham_directories") % i for i in range(1, 4)]
    spam = [get_pathname_option("TestDriver", "spam_directories") % i for i in range(1, 4)]

    sizes = [0, 60, 120, 240, 480, 840, 1200, 2400, 3600, 4800, 6000]

    d = TestDriver.Driver()
    d.new_classifier()

    detection_rates = []
    target_rates    = []
    false_positives = []
    false_negatives = []
    unsures         = []

    for size in sizes:

        mislabeler = MislabeledFileMover(size)
        mislabeler.random_move_file()

        d.train(msgs.HamStream(ham[0], [ham[0]]),
            msgs.SpamStream(spam[0], [spam[0]]))
        d.test(msgs.HamStream(ham[1], [ham[1]]),
               msgs.SpamStream(spam[1], [spam[1]]))

        target_rate = d.tester.correct_classification_rate()
        target_rates.append(target_rate)

        d.train(msgs.HamStream(ham[2], [ham[2]]),
                msgs.SpamStream(spam[2], [spam[2]]))
        d.test(msgs.HamStream(ham[1], [ham[1]]),
               msgs.SpamStream(spam[1], [spam[1]]))

        detection_rate = d.tester.correct_classification_rate()
        detection_rates.append(detection_rate)

        fp = d.tester.nham_wrong
        false_positives.append(fp)
        fn = d.tester.nspam_wrong
        false_negatives.append(fn)
        unsure = d.tester.nham_unsure + d.tester.nspam_unsure
        unsures.append(unsure)

        d.untrain(msgs.HamStream(ham[0], [ham[0]]),
                  msgs.SpamStream(spam[0], [spam[0]]))
        d.untrain(msgs.HamStream(ham[2], [ham[2]]),
                  msgs.SpamStream(spam[2], [spam[2]]))

        mislabeler.reset()

    with open("/Users/AlexYang/Desktop/hamasspam.txt", 'w') as outfile:

        outfile.write(tabulate({"# of Mislabeled Words": sizes,
                                "Detection Rates": detection_rates,
                                "Target Rates": target_rates},
                               headers="keys", tablefmt="plain"))

if __name__ == "__main__":
    main()
