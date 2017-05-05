__author__ = 'Alex'

import os
import sys
import time
import argparse


# sys.path.insert(-1, os.getcwd())
# sys.path.insert(-1, os.path.dirname(os.getcwd()))
sys.path.append(os.getcwd())
sys.path.append(os.path.dirname(os.getcwd()))

from spambayes import ActiveUnlearnDriver
from spambayes.Options import options # Imports global options variable from spambayes/Options.py
from spambayes import msgs
from testtools import data_sets as ds # File manager for test/training data
from testtools import partitioner
from testtools.io_locations import dest

# Set options global for spambayes
options["TestDriver", "show_histograms"] = False



# Reassign the functions in ds
dir_enumerate = ds.dir_enumerate
seterize = ds.seterize
seconds_to_english = ds.seconds_to_english

# variables contain all ham data and all spam data
hams = ds.hams
spams = ds.spams
# Schema:
#[
    # [
    #   '/Users/andrewaday/Downloads/Data Sets/DictionarySets-1.1/Ham/Set1', 
    #   '/Users/andrewaday/Downloads/Data Sets/DictionarySets-1.1/Ham/Set2', 
    #   '/Users/andrewaday/Downloads/Data Sets/DictionarySets-1.1/Ham/Set3'
    # ], ...
#]

set_dirs = ds.set_dirs # Array containing names of all parent data directories

pollution_set3 = True #True if Set3 file contains polluted data


def unlearn_stats(au, args, outfile, data_set, train, test, polluted, total_polluted, total_unpolluted,
                  train_time, polluted_data, clusters=False, vanilla=None, noisy_clusters=False):
        """Runs an unlearn algorithm on an ActiveUnlearner and prints out the resultant stats."""
        outfile.write("---------------------------\n")
        outfile.write("Data Set: " + data_set + "\n")
        outfile.write("Vanilla Training: " + str(train[0]) + " ham and " + str(train[1]) + " spam.\n")
        outfile.write("Testing: " + str(test[0]) + " ham and " + str(test[1]) + " spam.\n")
        outfile.write("Pollution Training: " + str(polluted[0]) + " ham and " + str(polluted[1]) +
                      " spam.\n")
        if vanilla is not None:
            outfile.write("Vanilla Detection Rate: " + str(vanilla[0]) + ".\n")
        outfile.write("---------------------------\n")
        outfile.write("\n\n")
        outfile.write("CLUSTER AND RATE COUNTS:\n")
        outfile.write("---------------------------\n")

        original_detection_rate = au.driver.tester.correct_classification_rate()

        outfile.write("0: " + str(original_detection_rate) + "\n")

        time_start = time.time()
        
        # get the unlearned cluster list
        # Testing shrinking the rejected clusters
        # cluster_list = au.impact_active_unlearn(outfile, test=True, pollution_set3=pollution_set3, gold=True, shrink_rejects=True) 
        cluster_list = au.impact_active_unlearn(outfile, test=True, pollution_set3=pollution_set3, gold=True, shrink_rejects=False) 
        
        time_end = time.time()
        unlearn_time = seconds_to_english(time_end - time_start)
        
        total_polluted_unlearned = 0
        total_unlearned = 0
        total_unpolluted_unlearned = 0
        total_noisy_unlearned = 0
        final_detection_rate = au.current_detection_rate
        noise = []

        print "\nTallying up final counts...\n"
        for cluster in cluster_list:
            cluster = cluster[1]
            total_unlearned += cluster.size # total no. emails unlearned
            total_polluted_unlearned += cluster.target_set3()
            total_unpolluted_unlearned += (cluster.size - cluster.target_set3())

        outfile.write("\nSTATS\n")
        outfile.write("---------------------------\n")
        outfile.write("Initial Detection Rate: " + str(original_detection_rate) + "\n")
        outfile.write("Final Detection Rate: " + str(final_detection_rate) + "\n")
        outfile.write("Total Unlearned:\n")
        outfile.write(str(total_unlearned) + "\n")
        outfile.write("Polluted Percentage of Unlearned:\n")
        outfile.write(str(total_polluted_unlearned) + "/" + str(total_unlearned) + " = " + str(float(total_polluted_unlearned) / float(total_unlearned)) + "\n")
        outfile.write("Unpolluted Percentage of Unlearned:\n")
        outfile.write(str(total_unpolluted_unlearned) + "/" + str(total_unlearned) + " = " + str(float(total_unpolluted_unlearned) / float(total_unlearned)) + "\n")
        outfile.write("Percentage of Polluted Unlearned:\n")
        outfile.write(str(total_polluted_unlearned) + "/" + str(total_polluted) + " = " +  str(float(total_polluted_unlearned) / float(total_polluted)) + "\n")
        outfile.write("Percentage of Unpolluted Unlearned:\n")
        outfile.write(str(total_unpolluted_unlearned) + "/" + str(total_unpolluted) + " = " + str(float(total_unpolluted_unlearned) / float(total_unpolluted)) + "\n")
        outfile.write('--------Experiment2 Statistics--------')
        if au.partition_method == 'features':
            polluted_unlearned = {'ham': [], 'spam': []}
            no_ham_polluted = polluted[0]
            no_spam_polluted = polluted[1]

            for cluster in cluster_list:
                cluster = cluster[1]
                pu = cluster.target_set3(emails=True)
                polluted_unlearned['ham'] += pu['ham']
                polluted_unlearned['spam'] += pu['spam']

            ham_polluted_features, spam_polluted_features = partitioner.feature_count(polluted_unlearned['ham'], polluted_unlearned['spam'], args.features)
            outfile.write("Polluted Ham unlearned with features: " + str(ham_polluted_features))
            outfile.write("Polluted Spam unlearned with features: " + str(spam_polluted_features))
            outfile.write("Of all unlearned, polluted emails, what percentage contain any of the partition features: " + str(float(ham_polluted_features+spam_polluted_features) / float(total_polluted_unlearned)))

            p_total, p_ham, p_spam = partitioner.polluted_features(polluted_unlearned, polluted_data[0], polluted_data[1], args.features)
            outfile.write("Polluted Ham NOT unlearned with features: " + str(p_ham))
            outfile.write("Polluted Spam NOT unlearned with features: " + str(p_spam))
            outfile.write("Of all polluted emails NOT unlearned, what percentage contain any of the partition features: " + str(float(p_ham + p_spam) / float(p_total)))

        if noisy_clusters:
            if vanilla is not None:
                # get list of clusters with 0 polluted emails, but unlearning still improves classification accuracy
                noise = noisy_data_check(find_pure_clusters(cluster_list, ps_3=pollution_set3), vanilla[1]) #vanilla[1] is the v_au instance
                for cluster in noise:
                    total_noisy_unlearned += cluster.size
                outfile.write("Percentage of Noisy Data in Unpolluted Unlearned:\n")
                outfile.write(str(total_noisy_unlearned) + "/" + str(total_unpolluted_unlearned) + " = " +  str(float(total_noisy_unlearned) / float(total_unpolluted_unlearned)) + "\n")
        outfile.write("Time for training:\n")
        outfile.write(train_time + "\n")
        outfile.write("Time for unlearning:\n")
        outfile.write(unlearn_time)
        outfile.write("\n") #always end files w/ newline

        if clusters:
            return cluster_list


def find_pure_clusters(cluster_list, ps_3):
    pure_clusters = []
    for cluster in cluster_list:
        cluster = cluster[1]
        if ps_3:
            pure_clusters.append(cluster.target_set3_get_unpolluted())
            # if cluster.target_set3() == 0:
            #     pure_clusters.append(cluster)

        else:
            if cluster.target_set4() == 0:
                pure_clusters.append(cluster)

    return pure_clusters


def noisy_data_check(pure_clusters, v_au):
    """
    Returns a list of all clusters which had no polluted emails, 
    but unlearning them improves classification accuracy 
    """
    noisy_clusters = []
    original_detection_rate = v_au.current_detection_rate
    counter = 1
    for cluster in pure_clusters:
        print "testing for noise in cluster ", counter, "/", len(pure_clusters)
        v_au.unlearn(cluster)
        v_au.init_ground(True)
        new_detection_rate = v_au.driver.tester.correct_classification_rate()
        if new_detection_rate > original_detection_rate:
            noisy_clusters.append(cluster)

        v_au.learn(cluster)
        counter += 1

    return noisy_clusters


def main():
    # sets = [11,12,13,14,15] # mislabeled_both_small
    sets = [17,20]
    # sets = [16,17,18,19,20,21] # mislabeled_both_big
    parser = argparse.ArgumentParser()
    parser.add_argument('-cv', '--cross', type=str, help="partition test set into T1 and T2 for cross-validation",
        choices=['random','features','mislabeled'], default=None)
    parser.add_argument('-f', '--features', nargs='*', help="what features to split into T2", default=None)
    parser.add_argument('-d', '--dest', type=str, help="choose alternate destination for output file")
    parser.add_argument('-dist', '--distance', type=str, default='frequency5', choices=['frequency5','frequency3'], help="choose a distance method")
    parser.add_argument('-hc', '--ham_cutoff', type=float, default=.2, help="choose a ham cutoff probability")
    parser.add_argument('-sc', '--spam_cutoff', type=float, default=.8, help="choose a spam cutoff probability")
    parser.add_argument('-cp', '--copies', type=int, default=1, help="number of times to copy T1")
    parser.add_argument('-mc', '--misclassified', dest='misclassified', action='store_true', help="When partitioning T1, do we include only misclassified emails?")
    parser.set_defaults(misclassified=False)


    args = parser.parse_args()
    print args
    
    if args.dest:
        global dest
        dest += args.dest

    print "path selected: ", dest

    options['Categorization', 'ham_cutoff'] = args.ham_cutoff
    options['Categorization', 'spam_cutoff'] = args.spam_cutoff

    for i in sets:
        ham = hams[i]
        spam = spams[i]
        data_set = set_dirs[i]

        print "beginning tests on ", data_set

        if i > 10: #Set2 is test and Set1 is training for all mislabeled datasets
            ham_test = ham[1] # approx 20,000 test and 12,000 train
            spam_test = spam[1]

            ham_train = ham[0]
            spam_train = spam[0]

        else:
            ham_test = ham[0] # approx 12,000 test and 20,000 train
            spam_test = spam[0]

            ham_train = ham[1]
            spam_train = spam[1]

        # the polluted data sets
        ham_p = ham[2] 
        spam_p = spam[2]

        # Calculate the number of emails for polluted, train, test, and total data sets
        ham_polluted = dir_enumerate(ham_p)
        spam_polluted = dir_enumerate(spam_p)
        train_ham = dir_enumerate(ham_train)
        train_spam = dir_enumerate(spam_train)
        test_ham = dir_enumerate(ham_test)
        test_spam = dir_enumerate(spam_test)
        total_polluted = ham_polluted + spam_polluted
        total_unpolluted = train_ham + train_spam

        try:
            time_1 = time.time() # begin timer
            # Instantiate ActiveUnlearner object
            if args.cross is not None:
                au_temp = None
                
                if args.cross == 'mislabeled' or args.misclassified:  # find mislabeled emails
                    print '------Gathering Mislabeled Emails------'
                    au_temp = ActiveUnlearnDriver.ActiveUnlearner([msgs.HamStream(ham_train, [ham_train]),
                                                          msgs.HamStream(ham_p, [ham_p])],        # Training Ham 
                                                         [msgs.SpamStream(spam_train, [spam_train]),
                                                          msgs.SpamStream(spam_p, [spam_p])],     # Training Spam
                                                         msgs.HamStream(ham_test, [ham_test]),          # Testing Ham
                                                         msgs.SpamStream(spam_test, [spam_test]),       # Testing Spam
                                                         distance_opt=args.distance, all_opt=True,      
                                                         update_opt="hybrid", greedy_opt=True,          
                                                         include_unsures=False) # Don't unclude unsure emails
                    print '------Mislabeled Emails Gathered------'
                
                t1_ham, t1_spam, t2_ham, t2_spam = partitioner.partition(test_ham, ham_test, test_spam, spam_test, 
                                                                        args.cross, args.features, args.copies, mis_only=args.misclassified, au=au_temp)

                au = ActiveUnlearnDriver.ActiveUnlearner([msgs.HamStream(ham_train, [ham_train]),
                                                          msgs.HamStream(ham_p, [ham_p])],        # Training Ham 
                                                         [msgs.SpamStream(spam_train, [spam_train]),
                                                          msgs.SpamStream(spam_p, [spam_p])],     # Training Spam
                                                         msgs.HamStream(ham_test, [ham_test], indices=t1_ham),          # Testing Ham
                                                         msgs.SpamStream(spam_test, [spam_test], indices=t1_spam),       # Testing Spam
                                                         cv_ham=msgs.HamStream(ham_test, [ham_test], indices=t2_ham),       # T2 testing Ham
                                                         cv_spam=msgs.SpamStream(spam_test, [spam_test], indices=t2_spam),  # T2 testing Spam
                                                         distance_opt=args.distance, all_opt=True,      
                                                         update_opt="hybrid", greedy_opt=True,          
                                                         include_unsures=False, partition_method=args.cross) # Don't unclude unsure emails        

            else:
                au = ActiveUnlearnDriver.ActiveUnlearner([msgs.HamStream(ham_train, [ham_train]),
                                                          msgs.HamStream(ham_p, [ham_p])],        # Training Ham 
                                                         [msgs.SpamStream(spam_train, [spam_train]),
                                                          msgs.SpamStream(spam_p, [spam_p])],     # Training Spam
                                                         msgs.HamStream(ham_test, [ham_test]),          # Testing Ham
                                                         msgs.SpamStream(spam_test, [spam_test]),       # Testing Spam
                                                         distance_opt=args.distance, all_opt=True,      
                                                         update_opt="hybrid", greedy_opt=True,          
                                                         include_unsures=False) # Don't unclude unsure emails        

            # vanilla active unlearner
            v_au = ActiveUnlearnDriver.ActiveUnlearner([msgs.HamStream(ham_train, [ham_train]), []],
                                                       [msgs.SpamStream(spam_train, [spam_train]), []],
                                                       msgs.HamStream(ham_test, [ham_test]),
                                                       msgs.SpamStream(spam_test, [spam_test]))

            vanilla_detection_rate = v_au.current_detection_rate

            time_2 = time.time()
            train_time = seconds_to_english(time_2 - time_1)
            print "Train time:", train_time, "\n"

            with open(dest + data_set + " (unlearn_stats).txt", 'w+') as outfile:
                try:
                    if args.cross == 'features' or args.cross == 'mislabeled':
                        t1_total = len(t1_ham) + len(t1_spam)
                        t2_total = len(t2_ham) + len(t2_spam)
                        print '----------------------T1/T2 TOTALS----------------------'
                        print 'Size of T1 Ham: ' + str(len(t1_ham))
                        print 'Size of T1 Spam: ' + str(len(t1_spam))
                        print 'Size of T2 Ham: ' + str(len(t2_ham))
                        print 'Size of T2 Spam: ' + str(len(t2_spam))
                        if args.cross == 'features':
                            outfile.write('Features used to distinguish T2: ' + ', '.join(args.features) + "\n")
                        if args.cross == 'mislabeled':
                            outfile.write('Ham cutoff : ' + str(args.ham_cutoff) + "\n")
                            outfile.write('Spam cutoff : ' + str(args.spam_cutoff) + "\n")
                        outfile.write('Size of T1 Ham: ' + str(len(t1_ham)) + "\n")
                        outfile.write('Size of T1 Spam: ' + str(len(t1_spam)) + "\n")
                        outfile.write('Size of T2 Ham: ' + str(len(t2_ham)) + "\n")
                        outfile.write('Size of T2 Spam: ' + str(len(t2_spam)) + "\n")
                        outfile.flush()
                        os.fsync(outfile)
                    unlearn_stats(au, args, outfile, data_set, [train_ham, train_spam], [test_ham, test_spam],
                                  [ham_polluted, spam_polluted], total_polluted, total_unpolluted,
                                  train_time, [ham_p, spam_p], vanilla=[vanilla_detection_rate, v_au], noisy_clusters=True)
                    # unlearn_stats(au, outfile, data_set, [train_ham, train_spam], [test_ham, test_spam],
                    #               [ham_polluted, spam_polluted], total_polluted, total_unpolluted,
                    #               train_time, vanilla=None, noisy_clusters=True)

                except KeyboardInterrupt:
                    outfile.flush()
                    sys.exit()

            # In the hopes of keeping RAM down between iterations
            del au
            del v_au

        except KeyboardInterrupt:
            sys.exit()

if __name__ == "__main__":
    main()
