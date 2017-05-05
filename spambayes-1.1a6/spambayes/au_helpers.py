from Cluster import Cluster
from random import choice, shuffle
import sys
import gc
import os
import time
import operator
from math import sqrt, fabs

NO_CENTROIDS = '1234567890'

def cluster_au(au, gold=False, shrink_rejects=False):
    """Clusters the training space of an ActiveUnlearner and returns the list of clusters."""
    print "\n-----------------------------------------------\n"
    cluster_list = [] # list of tuples (net_rate_change, cluster)
    training = au.shuffle_training() # returns a shuffled array containing all training emails
    print "\nResetting mislabeled...\n"
    mislabeled = au.get_mislabeled(update=True) # gets an array of all false positives, false negatives
    # ^ also runs init_ground, which will update accuracy of classifier on test emails
    
    au.mislabeled_chosen = set() # reset set of clustered mislabeled emails in this instance of au

    print "\ncluster_au(ActiveUnelearnDriver:32): Clustering...\n"
    original_training_size = len(training)
    pre_cluster_rate = au.current_detection_rate
    while len(training) > 0: # loop until all emails in phantom training space have been assigned
        print "\n-----------------------------------------------------\n"
        print "\n" + str(len(training)) + " emails out of " + str(original_training_size) + \
              " still unclustered.\n"

        # Choose an arbitrary email from the mislabeled emails and returns the training email closest to it.
        # Final call and source of current_seed is mislabeled_initial() function
        current_seed = cluster_methods(au, "weighted", training, mislabeled) # weighted function selects most confident falsely labeled email
        while current_seed is None:
            current_seed = cluster_methods(au, "weighted", training, mislabeled) # weighted function selects most confident falsely labeled email
        if str(current_seed) == NO_CENTROIDS:
            current_seed = choice(training) # choose random remail from remaining emails as seed
            cluster_result = cluster_remaining(current_seed, au, training, impact=True)
        else:
            cluster_result = determine_cluster(current_seed, au, working_set=training, gold=gold, impact=True, # if true, relearn clusters after returning them
                                               shrink_rejects=shrink_rejects)
        if cluster_result is None:
            print "!!!How did this happen?????"
            sys.exit(cluster_result)
            # while cluster_result is None:
            #     # current_seed = cluster_methods(au, "mislabeled", training, mislabeled)
            #     current_seed = cluster_methods(au, "weighted", training, mislabeled)
            #     cluster_result = determine_cluster(current_seed, au, working_set=training, gold=gold, impact=True,
            #                                        pos_cluster_opt=pos_cluster_opt,shrink_rejects=shrink_rejects)

        net_rate_change, cluster = cluster_result
        # After getting the cluster and net_rate_change, you relearn the cluster in original dataset if impact=True

        post_cluster_rate = au.current_detection_rate

        # make sure the cluster was properly relearned
        assert(post_cluster_rate == pre_cluster_rate), str(pre_cluster_rate) + " " + str(post_cluster_rate)
        print "cluster relearned successfully: au detection rate back to ", post_cluster_rate

        cluster_list.append([net_rate_change, cluster])

        print "\nRemoving cluster from shuffled training set...\n"
        original_len = len(training)
        for email in cluster.cluster_set: # remove emails from phantom training set so they are not assigned to other clusters
            training.remove(email)
        #print "\nTraining space is now at ", original_len, " --> ", len(training), " emails"

    cluster_list.sort() # sorts by net_rate_change
    print "\nClustering process done and sorted.\n"
    return cluster_list 


def cluster_methods(au, method, working_set, mislabeled):
    """Given a desired clustering method, returns the next msg to cluster around."""
    
    if method == "weighted":
        return au.select_initial(mislabeled, "weighted", working_set)
    else:
        raise AssertionError("Please specify clustering method.")

def cluster_remaining(center, au, working_set, impact=True):
    """ This function is called if weighted_initial returns NO_CENTROIDS, meaning there are no more misabeled emails to use as centers.
    The remaining emails in the working set are then returned as one cluster.
    """

    print "No more cluster centroids, grouping all remaining emails into one cluster"

    first_state_rate = au.current_detection_rate
    cluster = Cluster(center, len(working_set), au, working_set=working_set, 
                                    distance_opt=au.distance_opt)

    au.unlearn(cluster)
    au.init_ground()
    new_detection_rate = au.driver.tester.correct_classification_rate()

    if impact: #include net_rate_change in return
        au.learn(cluster) # relearn cluster in real training space so deltas of future cluster are not influenced
        second_state_rate = au.current_detection_rate
        
        net_rate_change = second_state_rate - first_state_rate
        au.current_detection_rate = first_state_rate

        assert(au.current_detection_rate == first_state_rate), str(au.current_detection_rate) + " " + str(first_state_rate)
        print "clustered remaining with a net rate change of ", second_state_rate, " - ", first_state_rate, " = ", net_rate_change
        
        return net_rate_change, cluster
    else:
        return cluster
    


def determine_cluster(center, au, working_set=None, gold=False, impact=False, test_waters=False, shrink_rejects=False):
    """Given a chosen starting center and a given increment of cluster size, it continues to grow and cluster more
    until the detection rate hits a maximum peak (i.e. optimal cluster); if first try is a decrease, reject this
    center and return False.
    """

    print "\nDetermining appropriate cluster around", center.tag, "...\n"
    old_detection_rate = au.current_detection_rate
    first_state_rate = au.current_detection_rate
    counter = 0

    cluster = Cluster(center, au.increment, au, working_set=working_set, 
                            distance_opt=au.distance_opt)
    # Test detection rate after unlearning cluster
    au.unlearn(cluster)
    au.init_ground()
    new_detection_rate = au.driver.tester.correct_classification_rate()

    if new_detection_rate <= old_detection_rate:    # Detection rate worsens - Reject
        print "\nCenter is inviable. " + str(new_detection_rate) + " < " + str(old_detection_rate) + "\n" 
        print "relearning cluster... "
        au.learn(cluster)

        second_state_rate = new_detection_rate
        net_rate_change = second_state_rate - first_state_rate
        print "cluster rejected with a net rate change of ", second_state_rate, " - ", first_state_rate, " = ", net_rate_change
        au.current_detection_rate = first_state_rate

        return net_rate_change, cluster

    elif cluster.size < au.increment:
        if impact:
            au.learn(cluster)
            second_state_rate = new_detection_rate
            net_rate_change = second_state_rate - first_state_rate
            au.current_detection_rate = first_state_rate
            print "no more emails to cluster, returning cluster of size ", cluster.size
            return net_rate_change, cluster

    else:   # Detection rate improves - Grow cluster
        if gold:
            cluster = au.cluster_by_gold(cluster, old_detection_rate, new_detection_rate, counter, test_waters)
        if impact: #include net_rate_change in return
            au.learn(cluster) # relearn cluster in real training space so deltas of future cluster are not influenced
            second_state_rate = au.current_detection_rate
            net_rate_change = second_state_rate - first_state_rate
            print "cluster found with a net rate change of ", second_state_rate, " - ", first_state_rate, " = ", net_rate_change
            au.current_detection_rate = first_state_rate
            return net_rate_change, cluster

def cluster_print_stats(outfile, pollution_set3, detection_rate, cluster, cluster_count, attempt_count):
    """Prints stats for a given unlearned cluster and the present state of the machine after unlearning."""
    if outfile is not None:
        if pollution_set3:
            outfile.write(str(cluster_count) + ", " + str(attempt_count) + ": " + str(detection_rate) + ", " +
                          str(cluster[1].size) + ", " + str(cluster[1].target_set3()) + "\n")

        else:
            outfile.write(str(cluster_count) + ", " + str(attempt_count) + ": " + str(detection_rate) + ", " +
                          str(cluster[1].size) + ", " + str(cluster[1].target_set4()) + "\n")
        outfile.flush()
        os.fsync(outfile)

    else:
        pass

def t2_print_stats(outfile, detection_rate):
    outfile.write('t2 detection rate: ' + str(detection_rate) + "\n")
    outfile.flush()
    os.fsync(outfile)

def feature_print_stats(outfile, u_f, number=20):
    outfile.write('Top ' + str(number) + ' most common features in unlearned emails as (word, frequency)' + "\n")
    sorted_uf = sorted(u_f.items(), key=operator.itemgetter(1), reverse=True)
    for x in xrange(min(number, len(sorted_uf))):
        outfile.write(str(sorted_uf[x]))
        outfile.write("\n")
    outfile.flush()
    os.fsync(outfile)






