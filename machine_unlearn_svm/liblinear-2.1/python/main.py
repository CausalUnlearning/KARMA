""" Test Driver for the Unlearning Process """
import os
import sys
import time
import process_data as pd
import helpers
import svm_driver as svm
import copy
import ActiveUnlearnDriver

# Set options liblinear
params = '-c .001 -q'

# Choose directory we want to process
# directory = "Mislabeled-Both-2.2-processed"
directory = "DictionarySets-1.1-processed0.5"
output = directory + "-unlearn-stats"
mislabeled = False

# rename helpers variables
seconds_to_english = helpers.sec_to_english


def unlearn_stats(au, outfile, train_y, train_x, pol_y, pol_x, test_y, test_x, total_polluted, total_unpolluted,
                  train_time, vanilla=None, noisy_clusters=False):
        """Runs an unlearn algorithm on an ActiveUnlearner and prints out the resultant stats."""
        
        outfile.write("---------------------------\n")
        outfile.write("Data Set: " + directory + "\n")
        outfile.write("Training: " + str(len(train_y)) + " unpolluted emails\n")
        outfile.write("Testing: " + str(len(test_y)) + " emails\n")
        outfile.write("Pollution: " + str(len(pol_y))+ " polluted emails\n")
        if vanilla is not None:
            outfile.write("Vanilla Detection Rate: " + str(vanilla.current_detection_rate) + ".\n")
        outfile.write("---------------------------\n")
        outfile.write("\n\n")
        outfile.write("CLUSTER AND RATE COUNTS:\n")
        outfile.write("---------------------------\n")

        original_detection_rate = au.current_detection_rate

        outfile.write("0: " + str(original_detection_rate) + "\n")

        time_start = time.time()
        
        # get the unlearned cluster list
        # Testing shrinking the rejected clusters
        # cluster_list = au.impact_active_unlearn(outfile, test=True, pollution_set3=pollution_set3, gold=True, shrink_rejects=True) 
        cluster_list = au.impact_active_unlearn(outfile, gold=True) 
        
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
        outfile.write("Unlearn Time: " + str(unlearn_time) + "\n")
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
        if noisy_clusters:
            if vanilla is not None:
                # get list of clusters with 0 polluted emails, but unlearning still improves classification accuracy
                noise = noisy_data_check(find_pure_clusters(cluster_list), vanilla) #vanilla[1] is the v_au instance
                for cluster in noise:
                    total_noisy_unlearned += cluster.size
                outfile.write("Percentage of Noisy Data in Unpolluted Unlearned:\n")
                outfile.write(str(total_noisy_unlearned) + "/" + str(total_unpolluted_unlearned) + " = " +  str(float(total_noisy_unlearned) / float(total_unpolluted_unlearned)) + "\n")
        outfile.write("Time for training:\n")
        outfile.write(train_time + "\n")
        outfile.write("Time for unlearning:\n")
        outfile.write(unlearn_time)
        outfile.write("\n") #always end files w/ newline


def find_pure_clusters(cluster_list):
    pure_clusters = []
    for cluster in cluster_list:
        cluster = cluster[1]
        pure_clusters.append(cluster.target_set3_get_unpolluted())
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
        v_au.init_ground()
        new_detection_rate = v_au.current_detection_rate
        if new_detection_rate > original_detection_rate:
            noisy_clusters.append(cluster)

        v_au.learn(cluster)
        counter += 1

    return noisy_clusters


def main():
    time_1 = time.time()
    print "Processing ", directory

    # Collect the processed data
    emails = pd.get_emails(directory)
    van_emails = copy.deepcopy(emails)

    # assign variables to train and test data
    pol_y, pol_x = emails[0]
    train_y, train_x = emails[1]
    test_y, test_x = emails[2]

    van_pol_y, van_pol_x = van_emails[0]    
    van_train_y, van_train_x = van_emails[1]
    van_test_y, van_test_x = van_emails[2]
    if mislabeled:
        van_pol_y = [-1 * y for y in van_pol_y] # correct labeling on vanilla
    else:
        van_pol_y = [] # Remove all dictionary emails
        van_pol_x = []

    # Calculate the number of emails for polluted, train, test, and total data sets
    size = emails[3]
    ham_polluted = size['ham_polluted']
    spam_polluted = size['spam_polluted']
    train_ham = size['train_ham']
    train_spam = size['train_spam']
    test_ham = size['test_ham']
    test_spam = size['test_spam']
    total_polluted = size['total_polluted']
    total_unpolluted = size['total_unpolluted']
    print size

    try:
        # Instantiate ActiveUnlearner object
        print "-----Initializing polluted unlearner-----"
        au = ActiveUnlearnDriver.ActiveUnlearner(train_y, train_x, pol_y, pol_x, test_y, test_x,
                                                 params=params, distance_opt="frequency5", 
                                                 greedy_opt=True)

        # vanilla active unlearner
        print "-----Initializing vanilla unlearner-----"
        v_au = ActiveUnlearnDriver.ActiveUnlearner(van_train_y, van_train_x, van_pol_y, van_pol_x, van_test_y, van_test_x)

        time_2 = time.time()
        train_time = seconds_to_english(time_2 - time_1)
        print "Initialization time:", train_time, "\n"

        with open(output, 'w+') as outfile:
            try:
                unlearn_stats(au, outfile, train_y, train_x, pol_y, pol_x, test_y, test_x,
                             total_polluted, total_unpolluted, train_time, vanilla=v_au, noisy_clusters=True)

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
