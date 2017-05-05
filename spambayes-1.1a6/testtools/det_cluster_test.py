__author__ = 'Alex'


def main():
    import os
    import sys
    from random import choice

    sys.path.insert(-1, os.getcwd())
    sys.path.insert(-1, os.path.dirname(os.getcwd()))

    from spambayes import ActiveUnlearnDriver
    from spambayes.Options import get_pathname_option
    from spambayes import msgs

    """
    from dictionarywriter import DictionaryWriter
    """

    ham = [get_pathname_option("TestDriver", "ham_directories") % i for i in range(1, 5)]
    spam = [get_pathname_option("TestDriver", "spam_directories") % i for i in range(1, 5)]
    """
    DictionaryWriter(600).write()
    """

    keep_going = True
    trial_number = 1

    au_v = ActiveUnlearnDriver.ActiveUnlearner([msgs.HamStream(ham[1], [ham[1]]),
                                                msgs.HamStream(ham[2], [ham[2]])],
                                               [msgs.SpamStream(spam[1], [spam[1]]),
                                                msgs.SpamStream(spam[3], [spam[3]])],
                                               msgs.HamStream(ham[0], [ham[0]]),
                                               msgs.SpamStream(spam[0], [spam[0]]),
                                               )
    while keep_going:
        msg = choice(au_v.driver.tester.train_examples[0])
        try:
            test_cl, counter = au_v.determine_cluster(msg)
            test_size = test_cl.size
            au_v.learn(test_cl)

        except TypeError:
            counter = 1
            test_size = "100, but fail"

        cluster_detection_rates_v = []
        cluster_spam_rates_v = []
        cluster_sizes = []

        au_v.init_ground()
        original_rate_v = au_v.driver.tester.correct_classification_rate()
        cluster_size = 100
        cluster_sizes.append(100)

        print "Clustering with size", cluster_size, "..."

        cl_v = ActiveUnlearnDriver.Cluster(msg, cluster_size, au_v, "extreme")
        cluster_spam_rates_v.append(float(cl_v.target_spam()) / float(cluster_size))
        cluster_detection_rates_v.append(au_v.start_detect_rate(cl_v))

        for i in range(1, counter + 2):
            cluster_size += 100
            cluster_sizes.append(cluster_size)

            print "Clustering with size", cluster_size, "..."

            cluster_detection_rates_v.append(au_v.continue_detect_rate(cl_v, 100))
            cluster_spam_rates_v.append(float(cl_v.target_spam()) / float(cluster_size))

        with open("C:\Users\Alex\Desktop\det_cluster_stats_v" + str(trial_number) + ".txt", 'w') as outfile:
            outfile.write("VANILLA MACHINE\n")

            outfile.write("--------------------------\n")

            outfile.write("Clustered around: " + msg.tag + "\n")

            outfile.write("--------------------------\n")

            outfile.write("Detection Rates:\n")
            outfile.write(str(original_rate_v) + "\n")

            for item in cluster_detection_rates_v:
                outfile.write(str(item) + "\n")

            outfile.write("--------------------------\n")

            outfile.write("Spam Rate:\n")
            for item in cluster_spam_rates_v:
                outfile.write(str(item) + "\n")

            outfile.write("Test Cluster Size:\n")
            outfile.write(str(test_size))

        answer = raw_input("Keep going (y/n)? You have performed " + str(trial_number) + " trials so far. ")

        if answer == "n":
            keep_going = False

        else:
            au_v.learn(cl_v)
            au_v.init_ground()
            trial_number += 1


if __name__ == "__main__":
    main()
