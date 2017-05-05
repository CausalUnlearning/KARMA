__author__ = 'Alex'

import os
import sys
import time
import itertools

sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from spambayes import ActiveUnlearnDriver
from spambayes.Options import options
from spambayes import msgs
from testtools import data_sets as ds
from testtools import data_sets_impact_test as d_test
from testtools import feature_test as f_t

inc = 50
options["TestDriver", "show_histograms"] = False

hams, spams = ds.hams, ds.spams
set_dirs, dir_enumerate = ds.set_dirs, ds.dir_enumerate
stats = d_test.unlearn_stats
seconds_to_english = ds.seconds_to_english
feature_trunc = f_t.feature_trunc
feature_print = f_t.feature_print
feature_lists = f_t.feature_lists
extract_features = f_t.extract_features
au_sig_words = f_t.au_sig_words


def cluster_sig_words(au, cluster):
    c = au.driver.tester.classifier
    features = []
    r_features = []
    words = set(word for msg in cluster.cluster_set for word in msg)

    for word in words:
        record = c.wordinfo.get(word)
        if record is not None:
            prob = c.probability(record)
            features.append((prob, word))
            r_features.append((word, prob))
    features.sort()
    return [features, dict(r_features)]


def cluster_feature_matrix(v_au, p_au, cluster_list, n=None, sep=False):
    machines = [v_au, p_au]
    if sep:
        cluster_list = [item for item in itertools.chain.from_iterable([cluster_separate(cluster)
                                                                        for cluster in cluster_list])]

    keys = [machine.driver.tester.classifier.wordinfo.keys() for machine in machines]
    words = set(itertools.chain.from_iterable(keys))
    au_features = [au_sig_words(machine, words) for machine in machines]
    cluster_features = [cluster_sig_words(v_au, cluster) for cluster in cluster_list]
    sigs = extract_features(au_features + cluster_features, n=n, sep_sigs_only=True)
    if sep:
        feature_matrix = feature_lists(sigs, len(cluster_list) / 2,
                                       labels=("Cluster (Unpolluted)", "Cluster (Polluted)"))
    else:
        feature_matrix = feature_lists(sigs, len(cluster_list), labels="Cluster")

    label_inject(feature_matrix, cluster_list)

    return feature_matrix


def cluster_print(cluster, pollution_set3):
    target = str(cluster.target_set3() if pollution_set3 else cluster.target_set4())
    return "(" + str(cluster.size) + ", " + target + ")"


def cluster_pollution_rate(cluster, pollution_set3):
    target = str(float(cluster.target_set3()) / float(cluster.size) if pollution_set3
                 else float(cluster.target_set4()) / float(cluster.size))
    return "(" + str(cluster.size) + ", " + target + ")"


def label_inject(feature_matrix, cluster_list, pollution_set3=True):
    header = feature_matrix[0]
    for i in range(3, len(header)):
        try:
            header[i] += " " + cluster_print(cluster_list[i - 3], pollution_set3)

        except IndexError:
            print str(i) + " " + str(len(cluster_list)) + " " + str(len(header))
            raise AssertionError


def cluster_separate(cluster):
    unpolluted = []
    polluted = []
    for msg in cluster.cluster_set:
        if msg.train == 0 or msg.train == 1:
            unpolluted.append(msg)

        elif msg.train == 2 or msg.train == 3:
            polluted.append(msg)

        else:
            raise AssertionError

    assert(len(polluted) == cluster.target_set3()), str(len(polluted)) + ", " + str(cluster.target_set3())

    return ProxyCluster(unpolluted), ProxyCluster(polluted)


def print_cluster_features(outfile, cluster_list, v_au, p_au):
    """Prints the most significant features of the unpoluted and polluted portions of the clusters unlearned."""
    outfile.write("Unpolluted and Polluted Most Significant Features:\n")
    outfile.write("---------------------------\n")
    snipped_cluster_list = [cluster[1] for cluster in cluster_list]
    feature_matrix = cluster_feature_matrix(v_au, p_au, snipped_cluster_list, n=100, sep=True)

    feature_col_width = max(len(row[1]) for row in feature_matrix) + 2
    feature_num_col_width = max(len(row[0]) for row in feature_matrix) + 2
    for row in feature_matrix:
        justify = [row[0].ljust(feature_num_col_width)]
        for j in range(1, len(row)):
            justify.append(row[j].strip().ljust(feature_col_width))
        outfile.write("".join(justify) + "\n")


def print_cluster_pollution(outfile, cluster_list):
    """Prints the pollution rates of the clusters unlearned."""
    outfile.write("Cluster Pollution Rates:\n")
    outfile.write("---------------------------\n")
    header = [[""] + ["Cluster %d" % d for d in range(1, len(cluster_list) + 1)]]
    cluster_targets = [cluster_pollution(cluster[1]) for cluster in cluster_list]
    length = max(len(targets) for targets in cluster_targets)
    feature_matrix = header + [[str(inc * i)] + [cluster_target_print(cluster_target, i) for cluster_target in cluster_targets]
                      for i in range(length)]
    feature_col_width = max(len(item) for row in feature_matrix for item in row) + 2
    feature_num_col_width = max(len(row[0]) for row in feature_matrix) + 2
    for row in feature_matrix:
        justify = [row[0].ljust(feature_num_col_width)]
        for j in range(1, len(row)):
            justify.append(row[j].strip().ljust(feature_col_width))
        outfile.write("".join(justify) + "\n")


def cluster_target_print(cluster_target, i):
    try:
        return str(cluster_target[i])

    except IndexError:
        return ""


def cluster_pollution(cluster):
    end = cluster.size / inc
    targets = [0]
    sizes = [0]
    if end > 0:
        for i in range(end):
            start = sizes[len(sizes) - 1]
            sizes.append(sizes[len(sizes) - 1] + inc)
            end = sizes[len(sizes) - 1]
            targets.append(targets[len(targets) - 1] + cluster_interval_pollution(cluster, start, end))

    for i in range(1, len(targets)):
        targets[i] = float(targets[i]) / float(sizes[i])

    return targets


def cluster_interval_pollution(cluster, start, end):
    counter = 0
    for email in cluster.dist_list[start:end]:
        if email[1].train == 2 or email[1].train == 3:
            counter += 1

    return counter


class ProxyCluster:
    def __init__(self, emails):
        self.size = len(emails)
        self.cluster_set = emails

    def target_set3(self):
        counter = 0
        for msg in self.cluster_set:
            if "Set3" in msg.tag:
                counter += 1

        return counter

    def target_set4(self):
        counter = 0
        for msg in self.cluster_set:
            if "Set4" in msg.tag:
                counter += 1

        return counter


def main():
    sets = [10]
    dest = "C:/Users/bzpru/Desktop/spambayes-1.1a6/unpollute_stats/Yang_Data_Sets (cluster features)/"

    for i in sets:
        ham = hams[i]
        spam = spams[i]
        data_set = set_dirs[i]

        if i > 10:
            ham_test = ham[1]
            spam_test = spam[1]

            ham_train = ham[0]
            spam_train = spam[0]

        else:
            ham_test = ham[0]
            spam_test = spam[0]

            ham_train = ham[1]
            spam_train = spam[1]

        ham_p = ham[2]
        spam_p = spam[2]

        ham_polluted = dir_enumerate(ham_p)
        spam_polluted = dir_enumerate(spam_p)
        train_ham = dir_enumerate(ham_train)
        train_spam = dir_enumerate(spam_train)
        test_ham = dir_enumerate(ham_test)
        test_spam = dir_enumerate(spam_test)
        total_polluted = ham_polluted + spam_polluted
        total_unpolluted = train_ham + train_spam

        time_1 = time.time()
        p_au = ActiveUnlearnDriver.ActiveUnlearner([msgs.HamStream(ham_train, [ham_train]),
                                                   msgs.HamStream(ham_p, [ham_p])],        # Training Ham
                                                   [msgs.SpamStream(spam_train, [spam_train]),
                                                   msgs.SpamStream(spam_p, [spam_p])],     # Training Spam
                                                   msgs.HamStream(ham_test, [ham_test]),          # Testing Ham
                                                   msgs.SpamStream(spam_test, [spam_test]),       # Testing Spam
                                                   distance_opt="inv-match", all_opt=True,
                                                   update_opt="hybrid", greedy_opt=False)

        v_au = ActiveUnlearnDriver.ActiveUnlearner([msgs.HamStream(ham_train, [ham_train]), []],
                                                   [msgs.SpamStream(spam_train, [spam_train]), []],
                                                   msgs.HamStream(ham_test, [ham_test]),
                                                   msgs.SpamStream(spam_test, [spam_test]))

        vanilla_detection_rate = v_au.current_detection_rate
        time_2 = time.time()
        train_time = seconds_to_english(time_2 - time_1)
        print "Train time:", train_time, "\n"

        with open(dest + data_set + " (unlearn_stats).txt", 'w') as outfile:
            cluster_list = stats(p_au, outfile, data_set, [train_ham, train_spam], [test_ham, test_spam],
                                 [ham_polluted, spam_polluted], total_polluted, total_unpolluted, train_time,
                                 vanilla=[vanilla_detection_rate, v_au], clusters=True)

        with open(dest + data_set + " (Separate Features).txt", 'w') as outfile:
            outfile.write("---------------------------\n")
            outfile.write("Data Set: " + data_set + "\n")
            outfile.write("Vanilla Training: " + str(train_ham) + " ham and " + str(train_spam) + " spam.\n")
            outfile.write("Testing: " + str(test_ham) + " ham and " + str(test_spam) + " spam.\n")
            outfile.write("Pollution Training: " + str(ham_polluted) + " ham and " + str(spam_polluted) +
                          " spam.\n")
            outfile.write("---------------------------\n")
            outfile.write("\n\n")
            print_cluster_pollution(outfile, cluster_list)

        # In the hopes of keeping RAM down between iterations
        del p_au
        del v_au


if __name__ == "__main__":
    main()
