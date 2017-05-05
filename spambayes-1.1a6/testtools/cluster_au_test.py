__author__ = 'Alex'

import os
import sys

sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from spambayes import ActiveUnlearnDriver
from spambayes.Options import options
from spambayes import msgs

options["TestDriver", "show_histograms"] = False


def seterize(main_dir, sub_dir, is_spam, n):
    if is_spam:
        parent_dir = main_dir + "\\" + sub_dir + "\\" + "Spam" + "\\" + "Set%d"

    else:
        parent_dir = main_dir + "\\" + sub_dir + "\\" + "Ham" + "\\" + "Set%d"

    return [parent_dir % i for i in range(1, n + 1)]


def dir_enumerate(dir_name):
    return len([name for name in os.listdir(dir_name) if os.path.isfile(os.path.join(dir_name, name))])


def main():

    data_sets_dir = "C:\\Users\\Alex\\Downloads\\Data Sets"
    set_dirs = ["DictionarySets-1.1", "DictionarySets-1.2", "DictionarySets-2.1", "DictionarySets-2.2",
                "DictionarySets-3.1", "Mislabeled-Big", "Mislabeled-Both-1.1", "Mislabeled-Both-1.2",
                "Mislabeled-Both-2.1", "Mislabeled-Both-2.2", "Mislabeled-Both-3.1", "Mislabeled-HtoS-1.1",
                "Mislabeled-HtoS-1.2", "Mislabeled-HtoS-1.3", "Mislabeled-HtoS-1.4", "Mislabeled-HtoS-1.5",
                "Mislabeled-StoH-1.1", "Mislabeled-StoH-1.2", "Mislabeled-StoH-1.3", "Mislabeled-StoH-2.1",
                "Mislabeled-StoH-2.2"]

    hams = [seterize(data_sets_dir, set_dir, False, 3) for set_dir in set_dirs]
    spams = [seterize(data_sets_dir, set_dir, True, 3) for set_dir in set_dirs]

    assert(len(hams) == len(spams))
    sets = [0]

    for i in sets:
        ham = hams[i]
        spam = spams[i]

        au = ActiveUnlearnDriver.ActiveUnlearner([msgs.HamStream(ham[1], [ham[1]]),
                                                  msgs.HamStream(ham[2], [ham[2]])],        # Training Ham
                                                 [msgs.SpamStream(spam[1], [spam[1]]),
                                                  msgs.SpamStream(spam[2], [spam[2]])],     # Training Spam
                                                 msgs.HamStream(ham[0], [ham[0]]),          # Testing Ham
                                                 msgs.SpamStream(spam[0], [spam[0]]),       # Testing Spam
                                                 )

        print "Cluster list:\n"
        outfile = open("C:\\Users\\Alex\\Desktop\\cluster_au.txt", 'w')
        cluster_list = ActiveUnlearnDriver.cluster_au(au, gold=True, test=True)
        print cluster_list
        outfile.write(cluster_list)
        outfile.close()

if __name__ == "__main__":
    main()
