from liblinearutil import *

def _seterize(main_dir, is_spam=False, n=3):
    """ Stores locations of spam/ham data files in a list """
    if is_spam:
        parent_dir = main_dir +  "/" + "Spam" + "/" + "Set%d" + "/" + "data"
    else:
        parent_dir = main_dir +  "/" + "Ham" + "/" + "Set%d" + "/" + "data"

    return [parent_dir % i for i in range(1, n + 1)]

def get_emails(main_dir, n=3):
    """ Returns training and testing data 
        Note: it is assumed that pollution data is stored in Set3
    """
    ham_files = _seterize(main_dir, False, n)
    spam_files = _seterize(main_dir, True, n)
    
    print "Processing Ham files: ", ham_files
    print "Processing Spam files: ", spam_files

    # process the data files
    ham_train_y, ham_train_x = svm_read_problem(ham_files[0])
    ham_test_y, ham_test_x = svm_read_problem(ham_files[1])
    ham_pol_y, ham_pol_x = svm_read_problem(ham_files[2])

    spam_train_y, spam_train_x = svm_read_problem(spam_files[0])
    spam_test_y, spam_test_x = svm_read_problem(spam_files[1])
    spam_pol_y, spam_pol_x = svm_read_problem(spam_files[2])

    test_x = ham_test_x + spam_test_x
    test_y = ham_test_y + spam_test_y

    assert len(test_x) == len(test_y), \
        "test_x length: %r != test_y length: %r" % (len(test_x), len(test_y))

    pol_x = ham_pol_x + spam_pol_x
    pol_y = ham_pol_y + spam_pol_y
    train_x = ham_train_x + spam_train_x
    train_y = ham_train_y + spam_train_y

    assert len(train_x) == len(train_y), \
        "train_x length: %r != train_y length: %r" % (len(train_x), len(train_y))
    assert len(pol_x) == len(pol_y), \
        "pol_x length: %r != pol_y length: %r" % (len(pol_x), len(pol_y))

    # Compile data size
    size = {}
    size['ham_polluted'] = len(ham_pol_y)
    size['spam_polluted'] = len(spam_pol_y)
    size['train_ham'] = len(ham_train_y)
    size['train_spam'] = len(spam_train_y)
    size['test_ham'] = len(ham_test_y)
    size['test_spam'] = len(spam_test_y)
    size['total_polluted'] = size['ham_polluted'] + size['spam_polluted']
    size['total_unpolluted'] = size['train_ham'] + size['train_spam']

    return [(pol_y, pol_x), (train_y, train_x), (test_y, test_x), size]




