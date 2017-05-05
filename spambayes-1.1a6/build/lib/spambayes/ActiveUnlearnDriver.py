from random import choice, shuffle
from spambayes import TestDriver, quickselect
from Distance import distance
from itertools import chain
import heapq
import sys
import copy
import os
from math import sqrt

phi = (1 + sqrt(5)) / 2


def chosen_sum(chosen, x, opt=None):
    s = 0
    for msg in chosen:
        s += distance(msg, x, opt)
    return s


class PriorityQueue:

    def __init__(self):
        self._queue = []
        self._index = 0

    def __len__(self):
        return len(self._queue)

    def push(self, item, priority):
        heapq.heappush(self._queue, (-priority, self._index, item))
        self._index -= 1

    def pop(self):
        return heapq.heappop(self._queue)[-1]

    def pushpop(self, item, priority):
        item = heapq.heappushpop(self._queue, (-priority, self._index, item))[-1]
        self._index -= 1
        return item

    def taskify(self):
        l = set()
        for item in self._queue:
            l.add(item[-1])
        return l


class Cluster:

    def __init__(self, msg, size, active_unlearner, opt="extreme", working_set=None, sort_first=True):
        self.clustroid = msg
        self.size = size
        self.active_unlearner = active_unlearner
        self.sort_first = sort_first
        self.working_set = working_set
        self.ham = set()
        self.spam = set()
        self.opt = opt
        self.dist_list = self.distance_array()
        """
        self.cluster_set, self.cluster_heap = self.make_cluster()
        """
        self.cluster_set = self.make_cluster()
        self.divide()

    def distance_array(self):
        train_examples = self.active_unlearner.driver.tester.train_examples
        if self.working_set is None:
            """
            for i in range(len(self.active_unlearner.driver.tester.train_examples)):
                for train in self.active_unlearner.driver.tester.train_examples[i]:
                    if train != self.clustroid:
                        dist_list.append((distance(self.clustroid, train, self.opt), train))
            """
            dist_list = [(distance(self.clustroid, train, self.opt), train) for train in chain(train_examples[0],
                                                                                               train_examples[1],
                                                                                               train_examples[2],
                                                                                               train_examples[3])]

        else:
            dist_list = [(distance(self.clustroid, train, self.opt), train) for train in self.working_set]

        if self.sort_first:
            dist_list.sort()

        return dist_list

    def make_cluster(self):
        """
        heap = PriorityQueue()
        for i in range(len(self.active_unlearner.driver.tester.train_examples)):
            for train in self.active_unlearner.driver.tester.train_examples[i]:
                if train != self.clustroid:
                    if len(heap) < self.size:
                        heap.push(train, distance(self.clustroid, train, self.opt))
                    else:
                        heap.pushpop(train, distance(self.clustroid, train, self.opt))

        l = heap.taskify()
        assert (len(l) == self.size)
        return l, heap
        """
        if self.sort_first:
            return set(item[1] for item in self.dist_list[:self.size])

        else:
            k_smallest = quickselect.k_smallest
            return set(item[1] for item in k_smallest(self.dist_list, self.size))

    def divide(self):
        """Divides messages in the cluster between spam and ham"""
        for msg in self.cluster_set:
            if msg.train == 1 or msg.train == 3:
                self.ham.add(msg)
            elif msg.train == 0 or msg.train == 2:
                self.spam.add(msg)
            else:
                raise AssertionError
        """            
        if self.clustroid.train == 1 or msg.train == 3:
            self.ham.add(self.clustroid)

        elif self.clustroid.train == 0 or msg.train == 2:
            self.spam.add(self.clustroid)
        """

    def target_spam(self):
        """Returns a count of the number of spam emails in the cluster"""
        counter = 0
        for msg in self.cluster_set:
            if msg.tag.endswith(".spam.txt"):
                counter += 1

        """
        if self.clustroid.tag.endswith(".spam.txt"):
            counter += 1
        """

        return counter

    def target_set3(self):
        """Returns a count of the number of Set3 emails in the cluster"""
        counter = 0
        for msg in self.cluster_set:
            if "Set3" in msg.tag:
                counter += 1

        """
        if "Set3" in self.clustroid.tag:
            counter += 1
        """

        return counter

    def target_set4(self):
        """Returns a count of the number of Set4 emails in the cluster"""
        counter = 0
        for msg in self.cluster_set:
            if "Set4" in msg.tag:
                counter += 1

        """
        if "Set4" in self.clustroid.tag:
            counter += 1
        """

        return counter

    def cluster_more(self, n):
        old_cluster_set = self.cluster_set
        if self.size + n <= len(self.dist_list):
            self.size += n

        else:
            self.size = len(self.dist_list)
        """
        for i in range(len(self.active_unlearner.driver.tester.train_examples)):
            for train in self.active_unlearner.driver.tester.train_examples[i]:
                if train != self.clustroid and train not in self.cluster_set:
                    if len(self.cluster_heap) < k:
                        self.cluster_heap.push(train, distance(self.clustroid, train, self.opt))

                    else:
                        self.cluster_heap.pushpop(train, distance(self.clustroid, train, self.opt))
        assert(len(self.cluster_heap) == k), len(self.cluster_heap)
        self.cluster_set = self.cluster_heap.taskify()
        assert(len(self.cluster_heap) == k), len(self.cluster_heap)
        assert(len(self.cluster_set) == k), len(self.cluster_set)
        """
        if self.sort_first:
            new_cluster_set = set(item[1] for item in self.dist_list[:self.size])
        else:
            k_smallest = quickselect.k_smallest
            new_cluster_set = set(item[1] for item in k_smallest(self.dist_list, self.size))

        new_elements = list(item for item in new_cluster_set if item not in old_cluster_set)
        self.cluster_set = new_cluster_set

        assert(len(self.cluster_set) == self.size), len(self.cluster_set)
        assert(len(new_elements) == n), len(new_elements)

        for msg in new_elements:
            if msg.train == 1 or msg.train == 3:
                self.ham.add(msg)
            elif msg.train == 0 or msg.train == 2:
                self.spam.add(msg)

        return new_elements

    def cluster_less(self, n):
        old_cluster_set = self.cluster_set
        self.size -= n
        assert(self.size >= 0), "Cluster size would become negative!"
        if self.sort_first:
            new_cluster_set = set(item[1] for item in self.dist_list[:self.size])
        else:
            k_smallest = quickselect.k_smallest
            new_cluster_set = set(item[1] for item in k_smallest(self.dist_list, self.size))

        new_elements = list(item for item in old_cluster_set if item not in new_cluster_set)
        self.cluster_set = new_cluster_set

        assert(len(self.cluster_set) == self.size), len(self.cluster_set)
        assert(len(new_elements) == n), len(new_elements)        

        for msg in new_elements:
            if msg.train == 1 or msg.train == 3:
                self.ham.remove(msg)

            elif msg.train == 0 or msg.train == 2:
                self.spam.remove(msg)

        return new_elements


class ProxyCluster:
    def __init__(self, cluster):

        if len(cluster.ham) + len(cluster.spam) != cluster.size:
            print "\nUpdating cluster ham and spam sets for proxy...\n"
            cluster.divide()

        else:
            print "\nProxy cluster ham/spam sets do not need updating; continuing.\n"

        hams = [ham for ham in cluster.ham]
        spams = [spam for spam in cluster.spam]
        cluster_set = set(msg for msg in chain(cluster.ham, cluster.spam))

        assert(len(cluster_set) == len(cluster.ham) + len(cluster.spam))

        self.ham = hams
        self.spam = spams
        self.size = cluster.size
        self.cluster_set = cluster_set

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


class ActiveUnlearner:

    def __init__(self, training_ham, training_spam, testing_ham, testing_spam, threshold=90, increment=100,):
        self.increment = increment
        self.threshold = threshold
        self.driver = TestDriver.Driver()
        self.set_driver()
        self.hamspams = zip(training_ham, training_spam)
        self.set_data()
        self.testing_spam = testing_spam
        self.testing_ham = testing_ham
        self.set_training_nums()
        self.set_dict_nums()
        self.init_ground(True)
        self.mislabeled_chosen = set()
        self.training_chosen = set()
        self.current_detection_rate = self.driver.tester.correct_classification_rate()
        print "Initial detection rate:", self.current_detection_rate

    def set_driver(self):
        self.driver.new_classifier()

    def set_data(self):
        for hamstream, spamstream in self.hamspams:
            self.driver.train(hamstream, spamstream)

    def init_ground(self, first_test=False):
        
        if first_test:
            self.driver.test(self.testing_ham, self.testing_spam, first_test)

        else:
            self.driver.test(self.driver.tester.truth_examples[1], self.driver.tester.truth_examples[0], first_test)

    def set_training_nums(self):
        hamstream, spamstream = self.hamspams[0]
        self.driver.train_test(hamstream, spamstream)

    def set_dict_nums(self):
        hamstream, spamstream = self.hamspams[1]
        self.driver.dict_test(hamstream, spamstream)

    def unlearn(self, cluster):
        if len(cluster.ham) + len(cluster.spam) != cluster.size:
            print "\nUpdating cluster ham and spam sets...\n"
            cluster.divide()

        self.driver.untrain(cluster.ham, cluster.spam)

        for ham in cluster.ham:
            self.driver.tester.train_examples[ham.train].remove(ham)
        for spam in cluster.spam:
            self.driver.tester.train_examples[spam.train].remove(spam)

    def learn(self, cluster):
        if len(cluster.ham) + len(cluster.spam) != cluster.size:
            print "\nUpdating cluster ham and spam sets...\n"
            cluster.divide()

        self.driver.train(cluster.ham, cluster.spam)

        for ham in cluster.ham:
            self.driver.tester.train_examples[ham.train].append(ham)
        for spam in cluster.spam:
            self.driver.tester.train_examples[spam.train].append(spam)

    # --------------------------------------------------------------------------------------------------------------

    def detect_rate(self, cluster):
        """Returns the detection rate if a given cluster is unlearned.
           Relearns the cluster afterwards"""
        self.unlearn(cluster)
        self.init_ground()
        detection_rate = self.driver.tester.correct_classification_rate()
        self.learn(cluster)
        return detection_rate

    def start_detect_rate(self, cluster):
        self.unlearn(cluster)
        self.init_ground()
        detection_rate = self.driver.tester.correct_classification_rate()
        return detection_rate

    def continue_detect_rate(self, cluster, n):
        old_cluster = copy.deepcopy(cluster.cluster_set)
        cluster.cluster_more(n)
        new_cluster = cluster.cluster_set

        new_unlearns = new_cluster - old_cluster
        assert(len(new_unlearns) == len(new_cluster) - len(old_cluster))
        assert(len(new_unlearns) == n), len(new_unlearns)

        unlearn_hams = []
        unlearn_spams = []

        for unlearn in new_unlearns:
            if unlearn.train == 1 or unlearn.train == 3:
                unlearn_hams.append(unlearn)

            elif unlearn.train == 0 or unlearn.train == 2:
                unlearn_spams.append(unlearn)

            self.driver.tester.train_examples[unlearn.train].remove(unlearn)

        self.driver.untrain(unlearn_hams, unlearn_spams)
        self.init_ground()
        detection_rate = self.driver.tester.correct_classification_rate()
        return detection_rate

    # --------------------------------------------------------------------------------------------------------------

    def divide_new_elements(self, messages, unlearn):
        hams = []
        spams = []
        for message in messages:
            if message.train == 1 or message.train == 3:
                hams.append(message)

            elif message.train == 0 or message.train == 2:
                spams.append(message)

            else:
                raise AssertionError("Message lacks train attribute.")

            if unlearn:
                self.driver.tester.train_examples[message.train].remove(message)

            else:
                self.driver.tester.train_examples[message.train].append(message)

        if unlearn:
            self.driver.untrain(hams, spams)

        else:
            self.driver.train(hams, spams)

    def determine_cluster(self, center, working_set=None, gold=False, tolerance=200):
        """ Given a chosen starting center and a given increment of cluster size, it continues to grow and cluster more
            until the detection rate hits a maximum peak (i.e. optimal cluster); if first try is a decrease, reject this
            center and return False."""

        print "\nDetermining appropriate cluster around", center.tag, "...\n"
        old_detection_rate = self.current_detection_rate
        counter = 0
        cluster = Cluster(center, self.increment, self, working_set=working_set)

        # Test detection rate after unlearning cluster
        self.unlearn(cluster)
        self.init_ground()
        new_detection_rate = self.driver.tester.correct_classification_rate()

        if new_detection_rate <= old_detection_rate:    # Detection rate worsens - Reject
            print "\nCenter is inviable.\n"
            proxy_cluster = ProxyCluster(cluster)
            self.learn(cluster)
            return False, proxy_cluster, None

        else:                                           # Detection rate improves - Grow cluster
            unlearn_hams = []
            unlearn_spams = []
            new_unlearns = set()

            if gold:
                sizes = [cluster.size]
                detection_rates = [new_detection_rate]

                while new_detection_rate > old_detection_rate and cluster.size < self.increment * 3:
                    counter += 1
                    old_detection_rate = new_detection_rate
                    print "\nExploring cluster of size", cluster.size, "...\n"

                    new_unlearns = cluster.cluster_more(self.increment)

                    assert(len(new_unlearns) == self.increment), len(new_unlearns)

                    self.divide_new_elements(new_unlearns, True)
                    self.init_ground()
                    new_detection_rate = self.driver.tester.correct_classification_rate()

                if new_detection_rate > old_detection_rate:
                    assert(cluster.size == self.increment * 3), cluster.size
                    try_gold = True

                else:
                    new_learns = cluster.cluster_less(self.increment)
                    assert(cluster.size == self.increment * counter), cluster.size
                    self.divide_new_elements(new_unlearns, False)
                    return True, cluster, None

                if try_gold:
                    extra_cluster = int(phi * cluster.size)
                    while new_detection_rate > old_detection_rate:
                        counter += 1

                        sizes.append(cluster.size)
                        detection_rates.append(new_detection_rate)
                        old_detection_rate = new_detection_rate
                        print "\nExploring cluster of size", cluster.size, "...\n"

                        new_unlearns = cluster.cluster_more(int(extra_cluster))
                        extra_cluster *= phi

                        self.divide_new_elements(new_unlearns, True)
                        self.init_ground()
                        new_detection_rate = self.driver.tester.correct_classification_rate()

                    sizes.append(cluster.size)
                    detection_rates.append(new_detection_rate)

                    cluster, detection_rate, iterations = self.golden_section_search(cluster, len(sizes) - 3,
                                                                                     len(sizes) - 2, len(sizes) - 1,
                                                                                     tolerance, sizes, detection_rates)
                    print "\nAppropriate cluster found, with size " + str(cluster.size) + " after " + \
                          str(counter + iterations) + " tries.\n"

                    if (counter + iterations) <= float(cluster.size) / float(self.increment):
                        print "Gold is at least as efficient as straight up incrementing.\n"
                        efficient = True

                    else:
                        print "Gold is less efficient than striaght up incrementing.\n"
                        efficient = False

                    self.current_detection_rate = detection_rate
                    return True, cluster, efficient

            else:
                while new_detection_rate > old_detection_rate:
                    counter += 1
                    print "\nExploring cluster of size", (counter + 1) * self.increment, "...\n"

                    old_detection_rate = new_detection_rate
                    new_unlearns = cluster.cluster_more(self.increment)

                    assert(len(new_unlearns) == self.increment), len(new_unlearns)
                    self.divide_new_elements(new_unlearns, True)
                    self.init_ground()
                    new_detection_rate = self.driver.tester.correct_classification_rate()

                # This part is done because we've clustered just past the peak point, so we need to go back
                # one increment and relearn the extra stuff.

                new_learns = cluster.cluster_less(self.increment)
                assert(cluster.size == self.increment * counter), counter  
                self.divide_new_elements(new_unlearns, False)

                print "\nAppropriate cluster found, with size " + str(cluster.size) + ".\n"
                self.current_detection_rate = old_detection_rate
                return True, cluster, None

    def golden_section_search(self, cluster, left_index, middle_index, right_index, tolerance, sizes, detection_rates):
        print "\nPerforming golden section search...\n"

        left = sizes[left_index]
        middle_1 = sizes[middle_index]
        right = sizes[right_index]
        pointer = middle_1
        iterations = 0

        if cluster.size > pointer:
            new_relearns = cluster.cluster_less(cluster.size - pointer)
            self.divide_new_elements(new_relearns, False)

        assert(len(sizes) == len(detection_rates)), len(sizes) - len(detection_rates)
        f = dict(zip(sizes, detection_rates))

        middle_2 = right - (middle_1 - left)

        while abs(right - left) > tolerance:
            print "\nWindow is between " + str(left) + " and " + str(right) + ".\n"
            print "Middles are " + str(middle_1) + " and " + str(middle_2) + ".\n"
            try:
                rate_1 = f[middle_1]

            except KeyError:
                if pointer > middle_1:
                    new_relearns = cluster.cluster_less(pointer - middle_1)
                    pointer = middle_1
                    print "Pointer is at " + str(pointer) + ".\n"
                    assert(cluster.size == pointer), cluster.size
                    self.divide_new_elements(new_relearns, False)
                    self.init_ground()
                    rate_1 = self.driver.tester.correct_classification_rate()
                    iterations += 1
                    f[middle_1] = rate_1

                elif pointer < middle_1:
                    raise AssertionError("Pointer is on the left of middle_1.")

                else:
                    raise AssertionError("Pointer is at the same location as middle_1.")

            try:
                rate_2 = f[middle_2]

            except KeyError:
                if pointer < middle_2:
                    new_unlearns = cluster.cluster_more(middle_2 - pointer)
                    pointer = middle_2
                    print "Pointer is at " + str(pointer) + ".\n"
                    assert(cluster.size == pointer), cluster.size
                    self.divide_new_elements(new_unlearns, True)
                    self.init_ground()
                    rate_2 = self.driver.tester.correct_classification_rate()
                    iterations += 1
                    f[middle_2] = rate_2

                elif pointer > middle_2:
                    raise AssertionError("Pointer is on the right of middle_2.")

                else:
                    raise AssertionError("Pointer is at the same location as middle_2.")

            if rate_1 > rate_2:
                right = middle_2
                middle_2 = middle_1
                middle_1 = right - int((right - left) / phi)

            else:
                left = middle_1
                middle_1 = middle_2
                middle_2 = left + int((right - left) / phi)

        size = int(float(left + right) / 2)
        assert (left <= size), left
        assert (size <= right), right
        if pointer < size:
            new_unlearns = cluster.cluster_more(size - pointer)
            assert(cluster.size == size), str(size) + " " + str(cluster.size)
            self.divide_new_elements(new_unlearns, True)
            self.init_ground()
            detection_rate = self.driver.tester.correct_classification_rate()
            iterations += 1

        elif pointer > size:
            new_relearns = cluster.cluster_less(pointer - size)
            assert(cluster.size == size), str(size) + " " + str(cluster.size)
            self.divide_new_elements(new_relearns, False)
            self.init_ground()
            detection_rate = self.driver.tester.correct_classification_rate()
            iterations += 1

        else:
            raise AssertionError("Pointer is at the midpoint of the window.")

        return cluster, detection_rate, iterations

    # -----------------------------------------------------------------------------------
    def active_unlearn(self, outfile, test=False, pollution_set3=True, gold=False, select_initial="mislabeled"):

        cluster_list = []
        cluster_count = 0
        attempt_count = 0
        detection_rate = self.current_detection_rate

        while detection_rate < self.threshold:
            current = self.select_initial(select_initial)
            attempt_count += 1
            cluster = self.determine_cluster(current, gold=gold)
            print "\n-----------------------------------------------------\n"
            print "\nAttempted", attempt_count, "attempts so far.\n"

            while not cluster[0]:
                current = self.select_initial(select_initial)
                attempt_count += 1
                cluster = self.determine_cluster(current, gold=gold)
                print "\nAttempted", attempt_count, "attempts so far.\n"

            cluster_list.append(cluster[1])
            cluster_count += 1
            print "\nUnlearned", cluster_count, "cluster(s) so far.\n"

            detection_rate = self.current_detection_rate
            print "\nCurrent detection rate achieved is " + str(detection_rate) + ".\n"
            if outfile is not None:
                if pollution_set3:
                    outfile.write(str(cluster_count) + ", " + str(attempt_count) + ": " + str(detection_rate) + ", " +
                                  str(cluster[1].size) + ", " + str(cluster[1].target_set3()) + ", " + str(cluster[2]) + "\n")

                else:
                    outfile.write(str(cluster_count) + ", " + str(attempt_count) + ": " + str(detection_rate) + ", " +
                                  str(cluster[1].size) + ", " + str(cluster[1].target_set4()) + ", " + str(cluster[2]) + "\n")
                outfile.flush()
                os.fsync(outfile)

        if test:
            return cluster_list

        print "\nThreshold achieved after", cluster_count, "clusters unlearned and", attempt_count, "attempts.\n"
    # -----------------------------------------------------------------------------------

    def brute_force_active_unlearn(self, outfile, test=False, center_iteration=True, pollution_set3=True, gold=False):
        cluster_list = []
        cluster_count = 0
        rejection_count = 0
        rejections = set()
        training = self.shuffle_training()
        original_training_size = len(training)
        detection_rate = self.current_detection_rate
        print "\nCurrent detection rate achieved is " + str(detection_rate) + ".\n"

        while len(training) > 0:
            print "\n-----------------------------------------------------\n"
            print "\nStarting new round of untraining;", len(training), "out of", original_training_size, "training left" \
                                                                                                          ".\n"

            current = training[len(training) - 1]
            cluster = self.determine_cluster(current, working_set=training, gold=gold)

            if not cluster[0]:
                print "\nMoving on from inviable cluster center...\n"
                if center_iteration:
                    training.remove(current)
                    rejections.add(current)
                    rejection_count += 1

                else:
                    for msg in cluster[1].cluster_set:
                        if msg not in rejections:
                            training.remove(msg)
                            rejections.add(msg)

                    rejection_count += 1

                print "\nRejected", rejection_count, "attempt(s) so far.\n"

            else:
                cluster_list.append(cluster[1])
                print "\nRemoving cluster from shuffled training set...\n"

                for msg in cluster[1].cluster_set:
                    if msg not in rejections:
                        training.remove(msg)
                        rejections.add(msg)

                cluster_count += 1
                print "\nUnlearned", cluster_count, "cluster(s) so far.\n"

                detection_rate = self.current_detection_rate
                print "\nCurrent detection rate achieved is " + str(detection_rate) + ".\n"
                if outfile is not None:
                    if pollution_set3:
                        outfile.write(str(cluster_count) + ", " + str(rejection_count + cluster_count) + ": " +
                                      str(detection_rate) + ", " + str(cluster[1].size) + ", " +
                                      str(cluster[1].target_set3()) + ", " + str(cluster[2]) + "\n")

                    else:
                        outfile.write(str(cluster_count) + ", " + str(rejection_count + cluster_count) + ": " +
                                      str(detection_rate) + ", " + str(cluster[1].size) + ", " +
                                      str(cluster[1].target_set4()) + ", " + str(cluster[2]) + "\n")

                    outfile.flush()
                    os.fsync(outfile)

        if test:
            return cluster_list

        print "\nIteration through training space complete after", cluster_count, "clusters unlearned and", \
            rejection_count, "rejections made.\n"

        print "\nFinal detection rate: " + str(detection_rate) + ".\n"

    def shuffle_training(self):
        train_examples = self.driver.tester.train_examples
        training = [train for train in chain(train_examples[0], train_examples[1], train_examples[2],
                                             train_examples[3])]
        shuffle(training)
        return training

    def get_mislabeled(self, update=False):
        """ Returns the set of mislabeled emails (from the ground truth) based off of the
            current classifier state. By default assumes the current state's numbers and
            tester false positives/negatives have already been generated; if not, it'll run the
            predict method from the tester."""
        tester = self.driver.tester
        if update:
            tester.predict(self.testing_ham, False)
            tester.predict(self.testing_spam, True)

        mislabeled = set()
        for wrong_ham in tester.ham_wrong_examples:
            mislabeled.add(wrong_ham)

        for wrong_spam in tester.spam_wrong_examples:
            mislabeled.add(wrong_spam)

        for unsure in tester.unsure_examples:
            mislabeled.add(unsure)

        return mislabeled

    def select_initial(self, option="mislabeled", distance_opt = "extreme"):
        """ Returns an email to be used as the initial unlearning email based on
            the mislabeled data (our tests show that the mislabeled and pollutant
            emails are strongly, ~80%, correlated) if option is true (which is default)."""
        mislabeled = self.get_mislabeled()
        t_e = self.driver.tester.train_examples
        print "Chosen: ", self.mislabeled_chosen
        print "Total Chosen: ", len(self.mislabeled_chosen)
        if option == "rowsum":
            # We want to minimize the distances (rowsum) between the email we select
            # and the mislabeled emails. This ensures that the initial email we select
            # is correlated with the mislabeled emails.

            minrowsum = sys.maxint
            init_email = None
            for email in chain(t_e[0], t_e[1], t_e[2], t_e[3]):
                rowsum = 0
                for email2 in mislabeled:
                    dist = distance(email, email2, distance_opt)
                    rowsum += dist ** 2
                if rowsum < minrowsum:
                    minrowsum = rowsum
                    init_email = email

            return init_email

        if option == "mislabeled":
            # This chooses an arbitrary point from the mislabeled emails and simply finds the email
            # in training that is closest to this point.
            try:
                mislabeled_point = choice(list(mislabeled - self.mislabeled_chosen))
                self.mislabeled_chosen.add(mislabeled_point)
            except:
                raise AssertionError(str(mislabeled))

            min_distance = sys.maxint

            for email in chain(t_e[0], t_e[1], t_e[2], t_e[3]):
                current_distance = distance(email, mislabeled_point, distance_opt)
                if current_distance < min_distance:
                    init_email = email
                    min_distance = current_distance

            return init_email

        if option == "max_sum":
            try:
                max_sum = 0

                for email in chain(t_e[0], t_e[1], t_e[2], t_e[3]):
                    current_sum = chosen_sum(self.training_chosen, email, distance_opt)
                    if current_sum > max_sum:
                        init_email = email
                        max_sum = current_sum

                self.training_chosen.add(init_email)
                return init_email

            except:
                print "Returning initial seed based off of mislabeled...\n"
                return self.select_initial(option="mislabeled")