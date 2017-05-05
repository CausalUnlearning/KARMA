import os
import sys
from random import choice

sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from spambayes import ActiveUnlearnDriver
from spambayes.Options import get_pathname_option
from spambayes import msgs
from dictionarysplicer import splice_set
from dictionarywriter import DictionaryWriter
from InjectionPollution import InjectionPolluter
from mislabeledfilemover import MislabeledFileMover
from tabulate import tabulate

def main():

    ham = [get_pathname_option("TestDriver", "ham_directories") % i for i in range(1, 4)]
    spam = [get_pathname_option("TestDriver", "spam_directories") % i for i in range(1, 4)]
    injected = get_pathname_option("TestDriver", "spam_directories") % 3

    au = ActiveUnlearnDriver.ActiveUnlearner([msgs.HamStream(ham[0], [ham[0]]), msgs.HamStream(ham[2], [ham[2]])],
                                             [msgs.SpamStream(spam[0], [spam[0]]), msgs.SpamStream(spam[2], [spam[2]])],
                                             msgs.HamStream(ham[1], [ham[1]]), msgs.SpamStream(spam[1], [spam[1]]))

    msg = choice(au.driver.tester.train_examples[2])    # Randomly chosen from Ham Set3

    original_rate = au.driver.tester.correct_classification_rate()
    cluster_sizes = []
    detection_rates = []
    target_cluster_rates = []

    sizes = []
    for i in range(150, 1050, 50):
        sizes.append(i)
    for i in range(1000, 15000, 1000):
        sizes.append(i)

    for size in sizes:
        cluster = ActiveUnlearnDriver.Cluster(msg, size, au, "extreme")
        print "Clustering with size " + str(cluster.size) + "..."
        cluster_sizes.append(size)
        detection_rates.append(au.detect_rate(cluster))
        target_cluster_rates.append(float(cluster.target_set3()) / float(cluster.size))

    file = open("/Users/AlexYang/Desktop/clues.txt", 'w')

    features = au.driver.classifier._getclues(msg)
    i = 1
    for feature in features:
        file.write(str(i) + ") ")
        file.write(str(feature) + "\n")
        i += 1

    with open("/Users/AlexYang/Desktop/clusterstats.txt", 'w') as outfile:

        outfile.write("Clustered around: " + msg.tag)
        outfile.write("\nOriginal Rate: " + str(original_rate) + "\n")

        outfile.write(tabulate({"Cluster Sizes": cluster_sizes,
                                "Detection Rates": detection_rates,
                                "% of Targets Clustered": target_cluster_rates},
                               headers="keys", tablefmt="plain"))

if __name__ == "__main__":
    main()
