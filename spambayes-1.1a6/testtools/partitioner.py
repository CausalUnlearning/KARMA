import os
import sys
import operator
from random import shuffle


"""
Splits testing data into T1 and T2 to cross-validate the accuracy of active unlearning
"""

def partition(ham_count, ham_dir, spam_count, spam_dir, option, features, copies, mis_only=False, au=None):
    if option == 'random':
        return random(ham_count, spam_count)
        # return range(ham_count), range(spam_count), [], []
    elif option == 'features':
        return feature_parse(ham_dir, spam_dir, features, mis_only=mis_only, au=au)
    elif option == 'mislabeled':
        return mislabeled_parse(ham_count, ham_dir, spam_count, spam_dir, copies, au)
    else:
        raise ValueError

def random(ham_count, spam_count):
    ham_indices = range(ham_count)
    spam_indices = range(spam_count)
    shuffle(ham_indices)
    shuffle(spam_indices)
    t1_ham = ham_indices[:len(ham_indices)/2]
    t2_ham = ham_indices[len(ham_indices)/2:]
    t1_spam = spam_indices[:len(spam_indices)/2]
    t2_spam = spam_indices[len(spam_indices)/2:]
    return t1_ham, t1_spam, t2_ham, t2_spam

def feature_parse(ham_dir, spam_dir, features, mis_only=False, au=None):  # he him his she her them we
    t1_ham = []
    t1_spam = []
    t2_ham = []
    t2_spam = []

    ham_emails = os.listdir(ham_dir)
    spam_emails = os.listdir(spam_dir)

    if au:
        tester = au.driver.tester
        wrong_ham = tester.ham_wrong_examples  # ham called spam
        wrong_spam = tester.spam_wrong_examples  # spam called ham

        contents = {}
        for email in wrong_ham:
            _vectorize(email, contents)
        for email in wrong_spam:
            _vectorize(email, contents)
        sort_contents = sorted(contents.items(), key=operator.itemgetter(1), reverse=True)
        for x in xrange(min(20, len(sort_contents))):
            print sort_contents[x]

        wrong_ham = tester.ham_wrong_examples  # ham called spam
        wrong_spam = tester.spam_wrong_examples  # spam called ham
        wrong_ham = [email.index for email in wrong_ham]
        wrong_spam = [email.index for email in wrong_spam]

    
    for i,ham in enumerate(ham_emails):
        print 'processing ' + str(i) + '/' + str(len(ham_emails)) + ' ham emails'
        sys.stdout.write("\033[F")
        with open(ham_dir+'/'+ham) as f:
            added = False
            for line in f:
                if any(feature in line.split(' ') for feature in features):
                    if mis_only:
                        if i in wrong_ham:
                            t1_ham.append(i)
                            added = True
                            break
                    else:
                        t1_ham.append(i)
                        # print line
                        added = True
                        break
            if not added:
                t2_ham.append(i) 

    for i,spam in enumerate(spam_emails):
        print 'processing ' + str(i) + '/' + str(len(spam_emails)) + ' spam emails'
        sys.stdout.write("\033[F")
        with open(spam_dir+'/'+spam) as f:
            added = False
            for line in f:
                if any(feature in line.split(' ') for feature in features):
                    if mis_only:
                        if i in wrong_spam:
                            t1_spam.append(i)
                            added = True
                            break
                    else:
                        t1_spam.append(i)
                        added = True
                        break
            if not added:
                t2_spam.append(i) 


    return t1_ham, t1_spam, t2_ham, t2_spam

def mislabeled_parse(ham_count, ham_dir, spam_count, spam_dir, copies, au):
    tester = au.driver.tester
    wrong_ham = tester.ham_wrong_examples  # ham called spam
    wrong_spam = tester.spam_wrong_examples  # spam called ham

    wrong_ham = [email.index for email in wrong_ham]
    wrong_spam = [email.index for email in wrong_spam]

    t1_ham = wrong_ham
    t1_spam = wrong_spam
    t2_ham = list(set(range(ham_count)) - set(wrong_ham))
    t2_spam = list(set(range(spam_count)) - set(wrong_spam))


    t1_ham *= copies
    t1_spam *= copies

    return t1_ham, t1_spam, t2_ham, t2_spam

def feature_count(hams, spams, features):
    ham_c = 0
    spam_c = 0
    for ham in hams:
        if any(feature in ham.guts.split("`~`") for feature in features):
            ham_c += 1
    for spam in spams:
        if any(feature in spam.guts.split("`~`") for feature in features):
            spam_c += 1
    return ham_c, spam_c

def polluted_features(polluted_unlearned, ham_dir, spam_dir, features):
    hams = polluted_unlearned['ham']
    spams = polluted_unlearned['spam']

    # indices of pollutedu unlearned
    hams = [ham.index for ham in hams]
    spams = [spam.index for spam in spams]

    ham_emails = os.listdir(ham_dir)
    spam_emails = os.listdir(spam_dir)
    ham_count = len(ham_emails)
    spam_count = len(spam_emails)

    # Indices of polluted emails not unlearned
    missed_ham = list(set(range(ham_count)) - set(hams))  
    missed_spam = list(set(range(spam_count)) - set(spams))
    total = len(missed_ham) + len(missed_spam)
    ham_c = 0
    spam_c = 0
    
    for i in missed_ham:
        name = ham_emails[i]
        with open(ham_dir+'/'+name) as f:
            for line in f:
                if any(feature in line.split(' ') for feature in features):
                    ham_c += 1
                    break

    for i in missed_spam:
        name = spam_emails[i]
        with open(spam_dir+'/'+name) as f:
            for line in f:
                if any(feature in line.split(' ') for feature in features):
                    spam_c += 1
                    break

    return total, ham_c, spam_c

def _vectorize(email, contents):
    words = email.guts.split("`~`")
    for word in words:
        if word in contents:
            contents[word] += 1
        else:
            contents[word] = 1







    