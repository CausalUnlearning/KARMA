from spambayes import helpers
from Distance import distance
from itertools import chain

class Cluster:
    def __init__(self, msg, size, active_unlearner, distance_opt, working_set=None, sort_first=True, separate=True):
        self.clustroid = msg # seed of the cluster
        if msg.train == 1 or msg.train == 3: # if ham set1 or ham set3
            self.train = [1, 3]
        elif msg.train == 0 or msg.train == 2: # if spam set1 or spam set3
            self.train = [0, 2]
        self.common_features = []
        self.msg_index = {}
        self.separate = separate
        self.size = size # arbitrarily set to 100
        self.active_unlearner = active_unlearner # point to calling au instance
        self.sort_first = sort_first
        self.opt = distance_opt

        self.working_set = working_set

        # if 'frequency' in self.opt:
        #     self.working_set = [train for train in working_set]
        # else:
        #     self.working_set = working_set
        self.ham = set()
        self.spam = set()
        if 'frequency' in self.opt:
            self.cluster_word_frequency = helpers.get_word_frequencies(self.clustroid)
            self.added = [] # keeps track of order emails are added

        self.dist_list = self.distance_array(self.separate) # returns list containing dist from all emails in phantom space to center clustroid
        self.cluster_set = self.make_cluster() # adds closest emails to cluster
        self.divide() # adds cluster emails to ham and spam

    def __repr__(self):
        return "(" + self.clustroid.tag + ", " + str(self.size) + ")"

    def distance_array(self, separate):
        """Returns a list containing the distances from each email to the center."""
        train_examples = self.active_unlearner.driver.tester.train_examples

        if separate: # if true, all emails must be same type (spam or ham) as centroid
            if self.working_set is None:
                if "frequency" in self.opt:
                    print "     Creating Distance Array using frequency method"
                    dist_list = [(distance(train, self.cluster_word_frequency, self.opt), train) for train in chain(train_examples[0],
                                                                                                   train_examples[1],
                                                                                                   train_examples[2],
                                                                                                   train_examples[3])
                                                                    if train.train in self.train]
                else: 
                    dist_list = [(distance(self.clustroid, train, self.opt), train) for train in chain(train_examples[0],
                                                                                                       train_examples[1],
                                                                                                       train_examples[2],
                                                                                                       train_examples[3])
                                 if train.train in self.train]
            else:
                if "frequency" in self.opt:
                    print "     Creating Distance Array using frequency method"
                    dist_list = [(distance(train, self.cluster_word_frequency, self.opt), train) for train in self.working_set if
                                 train.train in self.train]
                    
                else:
                    dist_list = [(distance(self.clustroid, train, self.opt), train) for train in self.working_set if
                                 train.train in self.train]
                    assert(len(dist_list) > 0)
                
                
        else:
            if self.working_set is None:
                dist_list = [(distance(self.clustroid, train, self.opt), train) for train in chain(train_examples[0],
                                                                                                   train_examples[1],
                                                                                                   train_examples[2],
                                                                                                   train_examples[3])]

            else:
                dist_list = [(distance(self.clustroid, train, self.opt), train) for train in self.working_set]

        if self.sort_first:
            dist_list.sort() # sorts tuples by first element default, the distance

        if self.opt == "intersection":
            dist_list = dist_list[::-1]
            return dist_list # reverse the distance list so that closest element is at start
        print "\n ----------------Generated Distance Array----------------\n"
        print [email[0] for email in dist_list[:5]]

        return dist_list

    # def unset(self, tag):
    #     self.dist_list[self.msg_index[tag]] = None

    # def updateset(self,tag,update):
    #     self.dist_list[self.msg_index[tag]] = update
    def update_dist_list(self, separate=True): 
        """Updates self.dist_list for the frequency[1,2] method"""
        emails = [train[1] for train in self.dist_list] # get array of emails
        self.dist_list = [(distance(train, self.cluster_word_frequency, self.opt), train) for train in emails]
        self.dist_list.sort()
        
        

    def make_cluster(self):
        """Constructs the initial cluster of emails."""
        # self.dist_list = [t for t in self.dist_list if t is not None]
        if self.size > len(self.dist_list):
            print "\nTruncating cluster size...\n"
            self.size = len(self.dist_list)

        if self.sort_first:
            if 'frequency' in self.opt:
                emails = [self.clustroid] # list of added emails
                
                for d,e in self.dist_list: # Remove the duplicate clustroid in self.dist_list 
                    if e.tag == self.clustroid.tag:
                        self.dist_list.remove((d,e))
                        # self.working_set.remove(e)
                        print "-> removed duplicate clustroid ", e.tag
                        break

                current_size = 1
                while current_size < self.size:
                    nearest = self.dist_list[0][1] # get nearest email
                    assert(nearest.tag != self.clustroid.tag), str(nearest.tag) + " " + str(self.clustroid.tag)
                    emails.append(nearest) # add to list
                    self.added.append(nearest) # track order in which emails are added
                    # self.working_set.remove(nearest) # remove from working set so email doesn't show up again when we recreate dist_list
                    self.cluster_word_frequency = helpers.update_word_frequencies(self.cluster_word_frequency, nearest) # update word frequencies
                    del self.dist_list[0] # so we don't add the email twice
                    self.update_dist_list() # new cluster_word_frequency, so need to resort closest emails
                    # self.dist_list = self.distance_array(self.separate) # update distance list w/ new frequency list
                    current_size += 1
                print "-> cluster initialized with size", len(emails)
                return set(emails)
            else:
                return set(item[1] for item in self.dist_list[:self.size])

        else:
            k_smallest = quickselect.k_smallest
            return set(item[1] for item in k_smallest(self.dist_list, self.size))

    def divide(self):
        """Divides messages in the cluster between spam and ham."""
        for msg in self.cluster_set:
            if msg.train == 1 or msg.train == 3:
                self.ham.add(msg)
            elif msg.train == 0 or msg.train == 2:
                self.spam.add(msg)
            else:
                raise AssertionError

    def target_spam(self):
        """Returns a count of the number of spam emails in the cluster."""
        counter = 0
        for msg in self.cluster_set:
            if msg.tag.endswith(".spam.txt"):
                counter += 1

        return counter

    def target_set3(self, emails=False):
        """Returns a count of the number of Set3 emails in the cluster."""
        ret = {'ham': [], 'spam': []} if emails else 0
        for msg in self.cluster_set:
            if "Set3" in msg.tag:
                if emails:
                    if '/Ham/' in msg.tag:
                        ret['ham'].append(msg)
                    else:
                        ret['spam'].append(msg)
                else:
                    ret += 1
        return ret

    def target_set3_get_unpolluted(self):
        cluster_set_new = []
        spam_new = set()
        ham_new = set()
        for msg in self.cluster_set:
            if "Set3" in msg.tag: #msg is polluted, remove from cluster
                self.size -= 1
            else:
                cluster_set_new.append(msg)  
                if "ham" in msg.tag:
                    ham_new.add(msg)
                else:
                    spam_new.add(msg)
        self.cluster_set = cluster_set_new
        self.spam = spam_new
        self.ham = ham_new
        return self # return the cluster

    def target_set4(self):
        """Returns a count of the number of Set4 emails in the cluster."""
        counter = 0
        for msg in self.cluster_set:
            if "Set4" in msg.tag:
                counter += 1
        return counter

    def cluster_more(self, n):
        """Expands the cluster to include n more emails and returns these additional emails.
           If n more is not available, cluster size is simply truncated to include all remaining
           emails."""
        if 'frequency' in self.opt:
            if n >= len(self.dist_list):
                n = len(self.dist_list)
            print "Adding ", n, " more emails to cluster of size ", self.size, " via ", self.opt,  " method"
            self.size += n

            new_elements = []
            added = 0
            while added < n:
                nearest = self.dist_list[0][1] # get nearest email
                new_elements.append(nearest) # add to new list
                self.added.append(nearest)
                self.cluster_set.add(nearest) # add to original cluster set
                self.cluster_word_frequency = helpers.update_word_frequencies(self.cluster_word_frequency, nearest) # update word frequencies
                # self.dist_list = self.distance_array(self.separate) # update distance list w/ new frequency list
                del self.dist_list[0]
                self.update_dist_list()
                added += 1
            assert(len(new_elements) == n), str(len(new_elements)) + " " + str(n)
            assert(len(self.cluster_set) == self.size), str(len(self.cluster_set)) + " " + str(self.size)
            for msg in new_elements:
                if msg.train == 1 or msg.train == 3:
                    self.ham.add(msg)
                elif msg.train == 0 or msg.train == 2:
                    self.spam.add(msg)
            return new_elements 

        old_cluster_set = self.cluster_set
        if self.size + n <= len(self.dist_list):
            self.size += n

        else:
            print "\nTruncating cluster size...\n"
            if len(self.dist_list) > 0:
                self.size = len(self.dist_list)

        if self.sort_first:
            new_cluster_set = set(item[1] for item in self.dist_list[:self.size])
        else:
            k_smallest = quickselect.k_smallest
            new_cluster_set = set(item[1] for item in k_smallest(self.dist_list, self.size))

        new_elements = list(item for item in new_cluster_set if item not in old_cluster_set)
        self.cluster_set = new_cluster_set

        assert(len(self.cluster_set) == self.size), len(self.cluster_set)

        for msg in new_elements:
            if msg.train == 1 or msg.train == 3:
                self.ham.add(msg)
            elif msg.train == 0 or msg.train == 2:
                self.spam.add(msg)

        return new_elements

    def learn(self, n): # relearn only set.size elements. unlearning is too convoluted
        print "-> relearning a cluster of size ", self.size, " via intersection method"
        old_cluster_set = self.cluster_set
        self.ham = set()
        self.spam = set()
        self.cluster_set = set()
        self.dist_list = self.distance_array(self.separate)
        self.cluster_set = self.make_cluster()
        self.divide()
        new_cluster_set = self.cluster_set
        new_elements = list(item for item in old_cluster_set if item not in new_cluster_set)
        assert(len(self.cluster_set) == self.size), str(len(self.cluster_set)) + " " + str(self.size)
        assert(len(new_elements) == n), len(new_elements)        
        return new_elements

    def cluster_less(self, n):
        """Contracts the cluster to include n less emails and returns the now newly excluded emails."""

        old_cluster_set = self.cluster_set
        self.size -= n
        assert(self.size > 0), "Cluster size would become negative!"
        if self.sort_first:
            if "frequency" in self.opt:
                unlearned = 0
                new_elements = []
                while unlearned < n:
                    email = self.added.pop() # remove most recently added email
                    new_elements.append(email) # add to new emails list
                    self.cluster_set.remove(email)
                    # self.working_set.append(email)
                    self.cluster_word_frequency = helpers.revert_word_frequencies(self.cluster_word_frequency, email) # update word frequencies
                    self.dist_list.append((0, email))
                    unlearned += 1
                #self.dist_list = self.distance_array(self.separate) 
                self.update_dist_list()
                assert(len(new_elements) == n), str(len(new_elements)) + " " + str(n)
                assert(len(self.cluster_set) == self.size), str(len(self.cluster_set)) + " " + str(self.size)

                for msg in new_elements:
                    if msg.train == 1 or msg.train == 3:
                        self.ham.remove(msg)
                    elif msg.train == 0 or msg.train == 2:
                        self.spam.remove(msg)

                return new_elements
            else:
                new_cluster_set = set(item[1] for item in self.dist_list[:self.size])
        else:
            k_smallest = quickselect.k_smallest
            new_cluster_set = set(item[1] for item in k_smallest(self.dist_list, self.size))

        new_elements = list(item for item in old_cluster_set if item not in new_cluster_set)
        self.cluster_set = new_cluster_set

        assert(len(self.cluster_set) == self.size), str(len(self.cluster_set)) + " " + str(self.size)
        assert(len(new_elements) == n), len(new_elements)        

        for msg in new_elements:
            if msg.train == 1 or msg.train == 3:
                self.ham.remove(msg)
            elif msg.train == 0 or msg.train == 2:
                self.spam.remove(msg)

        return new_elements