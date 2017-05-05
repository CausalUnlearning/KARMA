__author__ = 'Alex'

import os
import sys
import time

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
    set_dirs = ["Mislabeled-Big"]

    hams = [seterize(data_sets_dir, set_dir, False, 3) for set_dir in set_dirs]
    spams = [seterize(data_sets_dir, set_dir, True, 3) for set_dir in set_dirs]

    num_data_sets = len(hams)
    assert(len(hams) == len(spams))

    for i in range(num_data_sets):
        ham = hams[i]
        spam = spams[i]

        ham_polluted = dir_enumerate(ham[2])
        spam_polluted = dir_enumerate(spam[2])
        train_ham = dir_enumerate(ham[1])
        train_spam = dir_enumerate(spam[1])
        test_ham = dir_enumerate(ham[0])
        test_spam = dir_enumerate(spam[0])
        total_polluted = ham_polluted + spam_polluted

        try:
            time_1 = time.time()
            au = ActiveUnlearnDriver.ActiveUnlearner([msgs.HamStream(ham[1], [ham[1]]),
                                                      msgs.HamStream(ham[2], [ham[2]])],        # Training Ham
                                                     [msgs.SpamStream(spam[1], [spam[1]]),
                                                      msgs.SpamStream(spam[2], [spam[2]])],     # Training Spam
                                                     msgs.HamStream(ham[0], [ham[0]]),          # Testing Ham
                                                     msgs.SpamStream(spam[0], [spam[0]]),       # Testing Spam
                                                     )

            time_2 = time.time()
            train_time = time_2 - time_1
            print "Train time:", train_time, "\n"

            with open("C:\\Users\\Alex\\Desktop\\unpollute_stats\\big_yang_" + str(i + 1)
                      + ".txt", 'w') \
                    as outfile:
                try:
                    outfile.write("---------------------------\n")
                    outfile.write("Data Set: " + set_dirs[i] + "\n")
                    outfile.write("Vanilla Training: " + str(train_ham) + " ham and " + str(train_spam) + " spam.\n")
                    outfile.write("Testing: " + str(test_ham) + " ham and " + str(test_spam) + " spam.\n")
                    outfile.write("Pollution Training: " + str(ham_polluted) + " ham and " + str(spam_polluted) +
                                  " spam.\n")
                    outfile.write("---------------------------\n")
                    outfile.write("\n\n")
                    outfile.write("CLUSTER AND RATE COUNTS:\n")
                    outfile.write("---------------------------\n")

                    original_detection_rate = au.driver.tester.correct_classification_rate()

                    outfile.write("0: " + str(original_detection_rate) + "\n")

                    time_start = time.time()
                    cluster_list = au.greatest_impact_active_unlearn(outfile, test=True, pollution_set3=True, gold=True)
                    time_end = time.time()
                    unlearn_time = time_end - time_start
                    total_polluted_unlearned = 0
                    total_unlearned = 0
                    total_unpolluted_unlearned = 0
                    final_detection_rate = au.current_detection_rate

                    print "\nTallying up final counts...\n"
                    for cluster in cluster_list:
                        cluster = cluster[1]
                        total_unlearned += cluster.size
                        total_polluted_unlearned += cluster.target_set3()
                        total_unpolluted_unlearned += (cluster.size - cluster.target_set3())

                    outfile.write("\nSTATS\n")
                    outfile.write("---------------------------\n")
                    outfile.write("Initial Detection Rate: " + str(original_detection_rate) + "\n")
                    outfile.write("Final Detection Rate: " + str(final_detection_rate) + "\n")
                    outfile.write("Total Unlearned:\n")
                    outfile.write(str(total_unlearned) + "\n")
                    outfile.write("Polluted Percentage of Unlearned:\n")
                    outfile.write(str(float(total_polluted_unlearned) / float(total_unlearned)) + "\n")
                    outfile.write("Unpolluted Percentage of Unlearned:\n")
                    outfile.write(str(float(total_unpolluted_unlearned) / float(total_unlearned)) + "\n")
                    outfile.write("Percentage of Polluted Unlearned:\n")
                    outfile.write(str(float(total_polluted_unlearned) / float(total_polluted)) + "\n")
                    outfile.write("Time for training:\n")
                    outfile.write(str(train_time) + "\n")
                    outfile.write("Time for unlearning:\n")
                    outfile.write(str(unlearn_time))

                except KeyboardInterrupt:
                    outfile.flush()
                    os.fsync(outfile)
                    sys.exit()

        except KeyboardInterrupt:
            sys.exit()

main()
