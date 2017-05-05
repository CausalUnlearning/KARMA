from distance import distance, vectorize_set
import helpers as h
import time
class Cluster:
    def __init__(self, msg, size, active_unlearner, label, distance_opt, 
                working_set=None, separate=True):
        # Clustroid specs
        self.clustroid = msg[1] # index of msg
        self.label = label
        self.common_features = []
        self.separate = separate
        self.size = size # arbitrarily set to 100
        self.active_unlearner = active_unlearner # point to calling au instance
        self.opt = distance_opt

        # The data
        self.working_set = working_set
        self.train_y = self.working_set[0]
        self.train_x = self.working_set[1]
        self.pol_y = self.working_set[2]
        self.pol_x = self.working_set[3]
        self.data_y, self.data_x = h.compose_set(self.working_set)
        time_1 = time.time()
        self.vec_data_x = vectorize_set(self.data_x)
        print 'Vectorizing data_x took: ', h.sec_to_english(time.time() - time_1)

        self.ham = set()
        self.spam = set()

        if 'frequency' in self.opt:
            self.cluster_word_frequency = msg[0] # actual vector representation of msg
            self.added = [] # keeps track of order emails are added

        self.dist_list = self.distance_array(self.separate) # returns list containing dist from all emails in phantom space to center clustroid
        self.cluster_set = self.make_cluster() # adds closest emails to cluster
        self.divide() # adds cluster emails to ham and spam

    def __repr__(self):
        return repr((self.label,self.clustroid))

    def distance_array(self, separate):
        """Returns a list containing the distances from each email to the center."""

        if separate: # if true, all emails must be same type (spam or ham) as centroid
            dist_list = []
            for x in range(len(self.data_y)):
                if self.data_y[x] == self.label and x != self.clustroid: # same type, no duplicate 
                    dist_list.append((distance(self.vec_data_x[x], self.cluster_word_frequency, self.opt), x))

        dist_list.sort() # sorts tuples by first element default, the distance

        print "\n ----------------Generated Distance Array----------------\n"
        print "Distance: ", [email[0] for email in dist_list[:5]]
        print "Indices: ", [email[1] for email in dist_list[:5]]

        return dist_list

    def update_dist_list(self, t=False): 
        """Updates self.dist_list for the frequency method"""
        if t:
            time_1 = time.time()
        indices = [train[1] for train in self.dist_list] # get array of indices
        self.dist_list = [(distance(self.vec_data_x[i], self.cluster_word_frequency, self.opt), i) for i in indices]
        self.dist_list.sort()
        if t:
            time_2 = time.time()
            print 'update_dist_list took: ', h.sec_to_english(time_2 - time_1)

    def make_cluster(self):
        """Constructs the initial cluster of emails."""
        # self.dist_list = [t for t in self.dist_list if t is not None]
        if self.size > len(self.dist_list):
            print "\nTruncating cluster size...\n"
            self.size = len(self.dist_list)

        if 'frequency' in self.opt:
            emails = [self.clustroid] # list of added emails

            current_size = 1

            while current_size < self.size:
                d,i = self.dist_list.pop(0) # get nearest email
                emails.append(i) # add to list
                self.added.append(i) # track order in which emails are added
                self.cluster_word_frequency = h.update_word_frequencies(self.cluster_word_frequency, self.data_x[i]) # update word frequencies
                self.update_dist_list()
                if current_size % 10 == 0:
                    print current_size, "/", self.size
                 # new cluster_word_frequency, so need to resort closest emails
                current_size += 1
                
            print "-> cluster initialized with size", len(emails)
        return set(emails)

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
                d,i = self.dist_list.pop(0) # get nearest email
                new_elements.append(i) # add to new list
                self.added.append(i)
                self.cluster_set.add(i) # add to original cluster set
                self.cluster_word_frequency = h.update_word_frequencies(self.cluster_word_frequency, self.data_x[i]) # update word frequencies
                self.update_dist_list()
                added += 1
                if added % 10 == 0:
                    print added, "/", n
            assert(len(new_elements) == n), str(len(new_elements)) + " " + str(n)
            assert(len(self.cluster_set) == self.size), str(len(self.cluster_set)) + " " + str(self.size)
            self.divide(new_elements)
            return new_elements

    def cluster_less(self, n):
        """Contracts the cluster to include n less emails and returns the now newly excluded emails."""

        old_cluster_set = self.cluster_set
        self.size -= n
        assert(self.size > 0), "Cluster size would become negative!"
        if "frequency" in self.opt:
            unlearned = 0
            new_elements = []
            while unlearned < n:
                i = self.added.pop() # remove most recently added email
                new_elements.append(i) # add index to new emails list
                self.cluster_set.remove(i)
                self.cluster_word_frequency = h.revert_word_frequencies(self.cluster_word_frequency, self.data_x[i]) # update word frequencies
                self.dist_list.append((0, i))
                unlearned += 1
            self.update_dist_list()
            assert(len(new_elements) == n), str(len(new_elements)) + " " + str(n)
            assert(len(self.cluster_set) == self.size), str(len(self.cluster_set)) + " " + str(self.size)

            self.divide(new_elements, rem=True)
            return new_elements

    def divide(self, new_elements=None, rem=False):
        """Divides messages in the cluster between spam and ham."""
        if new_elements is None:
            for msg in self.cluster_set: # indices of added msgs
                if self.data_y[msg] == -1: # -1 indicates msg is ham
                    self.ham.add(msg) if not rem else self.ham.remove(msg)
                else:
                    self.spam.add(msg) if not rem else self.spam.remove(msg)
        else:
            for msg in new_elements:
                if self.data_y[msg] == -1:
                    self.ham.add(msg) if not rem else self.ham.remove(msg)
                else:
                    self.spam.add(msg) if not rem else self.spam.remove(msg)

    def target_spam(self):
        """Returns a count of the number of spam emails in the cluster."""
        return len(self.spam)

    def target_set3(self):
        """Returns a count of the number of Set3 emails in the cluster."""
        counter = 0
        for msg in self.cluster_set:
            if msg >= len(self.train_y):
                counter += 1
        return counter

    def target_set3_get_unpolluted(self):
        cluster_set_new = []
        spam_new = set()
        ham_new = set()
        for msg in self.cluster_set:
            if msg >= len(self.train_y): #msg is polluted, remove from cluster
                self.size -= 1
            else:
                cluster_set_new.append(msg)
                if self.train_y[msg] == -1:
                    ham_new.add(msg)
                else:
                    spam_new.add(msg)
        self.cluster_set = cluster_set_new
        self.spam = spam_new
        self.ham = ham_new
        return self # return the cluster
