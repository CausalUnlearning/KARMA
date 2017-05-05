from __future__ import generators

import os
import sys

sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from spambayes.Options import options, get_pathname_option
from spambayes import msgs, Distance, ActiveUnlearnDriver
from testtools import benignfilemover, mislabeledfilemover, dictionarywriter, dictionarysplicer
from scipy.stats import pearsonr
from math import sqrt

program = sys.argv[0]


def usage(code, msg=''):
    """Print usage message and sys.exit(code)."""
    if msg:
        print >> sys.stderr, msg
        print >> sys.stderr
    print >> sys.stderr, __doc__ % globals()
    sys.exit(code)


def drive():
    print options.display()

    spam = [get_pathname_option("TestDriver", "spam_directories") % i for i in range(1, 5)]
    ham = [get_pathname_option("TestDriver", "ham_directories") % i for i in range(1, 5)]

    d = dictionarywriter.DictionaryWriter(150, 4)
    d.write()

    keep_going = True
    trial_number = 1

    au = ActiveUnlearnDriver.ActiveUnlearner([msgs.HamStream(ham[1], [ham[1]]),
                                              msgs.HamStream(ham[2], [ham[2]])],
                                             [msgs.SpamStream(spam[1], [spam[1]]),
                                              msgs.SpamStream(spam[3], [spam[3]])],
                                             msgs.HamStream(ham[0], [ham[0]]),
                                             msgs.SpamStream(spam[0], [spam[0]]),
                                             )
    with open("C:\Users\Alex\Desktop\dict_correlation_stats.txt", 'w') as outfile:

        while keep_going:
            chosen = set()
            current = au.select_initial()
            cluster = au.determine_cluster(current)
            chosen.add(current)
            au.driver.test(au.testing_ham, au.testing_spam)

            while not cluster:
                current = au.select_initial(chosen)
                cluster = au.determine_cluster(current)
                chosen.add(current)
                au.driver.test(au.testing_ham, au.testing_spam)

            cluster_list = list(cluster.cluster_set)

            dicts = au.driver.tester.train_examples[2]

            data = v_correlation(cluster_list, dicts)

            outfile.write("Trial " + str(trial_number) + " Percentage Overlap (Correlation): " + str(data))
            answer = raw_input("Keep going (y/n)? You have performed " + str(trial_number) + " trial(s) so far. ")

            valid_input = False

            while not valid_input:
                if answer == "n":
                    keep_going = False
                    valid_input = True

                elif answer == "y":
                    au.learn(cluster)
                    au.init_ground()
                    trial_number += 1
                    valid_input = True

                else:
                    print "Please enter either y or n."


def p_correlation(cluster_list, dicts):
    """Uses Pearson's Correlation Coefficient to calculate correlation
     between mislabeled results and initial polluted emails in ground truth"""

    n = min(len(cluster_list), len(dicts))

    x = []
    for i in range(0, n):
        x.append(cluster_list[i].prob)

    y = []
    for i in range(0, n):
        y.append(dicts[i].prob)

    return pearsonr(x, y)


def v_correlation(cluster_list, dicts):
    dict_list = [[], [], [], []]

    print "Calculating Clustered Data Clustroid..."

    p_minrowsum = sys.maxint
    p_clustroid = None
    p_avgdistance = 0
    i = 1
    for email in cluster_list:
        print "Calculating on email " + str(i) + " of " + str(len(cluster_list))
        rowsum = 0
        for email2 in cluster_list:
            if email == email2:
                continue
            dist = Distance.distance(email, email2, "extreme")
            rowsum += dist ** 2
        if rowsum < p_minrowsum:
            p_minrowsum = rowsum
            p_clustroid = email
            p_avgdistance = sqrt(rowsum / (len(cluster_list) - 1))
        i += 1

    print "Calculating Dictionary Data Clustroid..."

    m_minrowsum = sys.maxint
    m_clustroid = None
    m_avgdistance = 0
    i = 1
    for email in dicts:
        if "dictionary3.spam.txt" in email.tag:
            dict_list[0] = email.clues
            assert(len(email.clues) > 0)
        elif "wordlist3.spam.txt" in email.tag:
            dict_list[1] = email.clues
        elif "words3.spam.txt" in email.tag:
            dict_list[2] = email.clues
        elif "wordsEn3.spam.txt" in email.tag:
            dict_list[3] = email.clues

        print "Calculating on email " + str(i) + " of " + str(len(dicts))
        rowsum = 0
        for email2 in dicts:
            if email == email2:
                continue
            dist = Distance.distance(email, email2, "extreme")
            rowsum += dist ** 2
        if rowsum < m_minrowsum:
            m_minrowsum = rowsum
            m_clustroid = email
            m_avgdistance = sqrt(rowsum / (len(dicts) - 1))
        i += 1

    print "Calculating Overlap..."

    p_size = 0
    i = 1
    for email in cluster_list:
        distance = Distance.distance(email, m_clustroid, "extreme")
        print "Scanning Clustered Email " + str(i) + " of " + str(len(cluster_list)) + " with distance " + str(distance)
        if distance < m_avgdistance:
            p_size += 1
        i += 1
    m_size = 0
    i = 1
    for email in dicts:
        distance = Distance.distance(email, p_clustroid, "extreme")
        print "Scanning Dictionary Email " + str(i) + " of " + str(len(dicts)) + " with distance " + str(distance)
        if distance < p_avgdistance:
            m_size += 1
        i += 1

    total_size = len(cluster_list) + len(dicts)

    print "Total Size: " + str(total_size)
    print "Size of Cluster Overlap: " + str(p_size)
    print "Size of Dictionary Overlap: " + str(m_size)
    print "Cluster average distance: " + str(p_avgdistance)
    print "Dictionary average distance: " + str(m_avgdistance)
    print "Dictionary Clues: " + str(dict_list)

    return (float(p_size) + float(m_size)) / float(total_size)


def main():
    drive()

if __name__ == "__main__":
    main()
