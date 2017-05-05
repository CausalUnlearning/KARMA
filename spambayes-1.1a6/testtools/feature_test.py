import os
import sys
import time

import numpy as np

sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

import spambayes.ActiveUnlearnDriver as ActiveUnlearnDriver
import spambayes.Options
import spambayes.msgs as msgs
import testtools.data_sets as ds
import testtools.data_sets_impact_test as d_test
import testtools.update_test as dut


ProxyCluster = dut.ProxyCluster
options = spambayes.Options.options

options["TestDriver", "show_histograms"] = False

hams, spams = ds.hams, ds.spams
set_dirs, dir_enumerate = ds.set_dirs, ds.dir_enumerate
stats = d_test.unlearn_stats
seconds_to_english = ds.seconds_to_english


def au_sig_words(au, words):
    c = au.driver.tester.classifier
    features = []
    r_features = []
    assert(len(words) > 0)
    for word in words:
        record = c.wordinfo.get(word)
        if record is not None:
            prob = c.probability(record)
            features.append((prob, word))
            r_features.append((word, prob))
    assert(len(features) > 0), c.wordinfo
    features.sort()
    return [features, dict(r_features)]


def extract_features(feature_dict_list, n=None, sep_sigs_only=False):
    if sep_sigs_only:
        return most_sigs(feature_dict_list, n)

    else:
        sigs = most_sigs(feature_dict_list, n)
        return feature_combine(sigs, feature_dict_list), sigs


def most_sigs(feature_dict_list, n=None):
    sigs = []
    for pair in feature_dict_list:
        pair[0] = [(feature[0], feature_trunc(feature[1])) for feature in pair[0]]

        if n is not None:
            p_most_sig = pair[0][:n] + pair[0][-n:]

        else:
            p_most_sig = pair[0]

        sigs.append(p_most_sig)

    return sigs


def feature_combine(sigs, feature_dict_list):
    all_sig_words = set()
    for p_most_sig in sigs:
        for feature in p_most_sig:
            all_sig_words.add(feature[1])

    features = []

    for word in all_sig_words:
        prob_list = []
        for pair in feature_dict_list:
            prob = 0
            try:
                prob = pair[1][word]

            except KeyError:
                pass

            prob_list.append(prob)

        features.append([word] + prob_list)

    data = np.array(features)
    features = data[np.argsort(data[:, 1])]
    return features


def feature_trunc(feature):
    if len(feature) > 30:
        return feature[:30]

    else:
        return feature


def feature_print(most_sig, i):
    try:
        return str(most_sig[i][0]) + ": " + str(most_sig[i][1])

    except IndexError:
        return ""


def feature_lists(sigs, column_num, labels=("Unlearned")):
    header_labels = tuple(label + " %d" for label in labels)
    length = max(len(most_sig) for most_sig in sigs)
    header = [["", "Unpolluted", "Polluted"] + [header_label % d for d in range(1, column_num + 1) 
                                                for header_label in header_labels]]
    data = [[str(i + 1)] + [feature_print(most_sig, i) for most_sig in sigs] for i in range(length)]
    return header + data


def main():
    sets = [1, 2, 3, 4]
    dest = "C:/Users/bzpru/Desktop/spambayes-1.1a6/unpollute_stats/Yang_Data_Sets (inverse)/Hybrid Update - Nongreedy/"

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
        time_2 = time.time()
        train_time = seconds_to_english(time_2 - time_1)
        print "Train time:", train_time, "\n"

        v_au = ActiveUnlearnDriver.ActiveUnlearner([msgs.HamStream(ham_train, [ham_train]),
                                                    []],
                                                   [msgs.SpamStream(spam_train, [spam_train]),
                                                    []],
                                                   msgs.HamStream(ham_test, [ham_test]),
                                                   msgs.SpamStream(spam_test, [spam_test]))

        p_c = p_au.driver.tester.classifier
        v_c = p_au.driver.tester.classifier
        words = set().union(set(p_c.wordinfo.keys()), set(v_c.wordinfo.keys()))
        p_pair = au_sig_words(p_au, words)
        v_pair = au_sig_words(v_au, words)

        with open(dest + data_set + " (unlearn_stats).txt", 'w') as outfile:
            stats(p_au, outfile, data_set, [train_ham, train_spam], [test_ham, test_spam],
                  [ham_polluted, spam_polluted], total_polluted, total_unpolluted, train_time)

        words = words.union(set(p_c.wordinfo.keys()))
        u_pair = au_sig_words(p_au, words)

        features, sigs = extract_features([v_pair, p_pair, u_pair])
        feature_matrix = feature_lists(sigs, 1)

        combined_matrix = [["", "Unpolluted", "Polluted", "Unlearned 1"]] + [[str(column) for column in feature]
                                                                             for feature in features]

        feature_col_width = max(len(row[1]) for row in feature_matrix) + 2
        combined_col_width = max(len(item) for row in combined_matrix for item in row) + 2
        feature_num_col_width = max(len(row[0]) for row in feature_matrix) + 2

        with open(dest + data_set + " (Separate Features).txt", 'w') as outfile:
            outfile.write("---------------------------\n")
            outfile.write("Data Set: " + data_set + "\n")
            outfile.write("Vanilla Training: " + str(train_ham) + " ham and " + str(train_spam) + " spam.\n")
            outfile.write("Testing: " + str(test_ham) + " ham and " + str(test_spam) + " spam.\n")
            outfile.write("Pollution Training: " + str(ham_polluted) + " ham and " + str(spam_polluted) +
                          " spam.\n")
            outfile.write("---------------------------\n")
            outfile.write("\n\n")
            outfile.write("Unpolluted and Polluted Most Significant Features:\n")
            outfile.write("---------------------------\n")
            for row in feature_matrix:
                justify = [row[0].ljust(feature_num_col_width)]
                for j in range(1, len(row)):
                    justify.append(row[j].strip().ljust(feature_col_width))
                outfile.write("".join(justify) + "\n")

        with open(dest + data_set + " (Combined Features).txt", 'w') as outfile:
            outfile.write("---------------------------\n")
            outfile.write("Data Set: " + data_set + "\n")
            outfile.write("Vanilla Training: " + str(train_ham) + " ham and " + str(train_spam) + " spam.\n")
            outfile.write("Testing: " + str(test_ham) + " ham and " + str(test_spam) + " spam.\n")
            outfile.write("Pollution Training: " + str(ham_polluted) + " ham and " + str(spam_polluted) +
                          " spam.\n")
            outfile.write("---------------------------\n")
            outfile.write("\n\n")
            outfile.write("Feature Comparison:\n")
            outfile.write("---------------------------\n")

            for row in combined_matrix:
                outfile.write("".join(word.strip().ljust(combined_col_width) for word in row) + "\n")


if __name__ == "__main__":
    main()
