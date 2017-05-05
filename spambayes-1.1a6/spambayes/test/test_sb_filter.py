# Test sb_filter script.

import os
import sys
import email
import unittest

import sb_test_support
sb_test_support.fix_sys_path()

from spambayes.Options import options
from spambayes.tokenizer import tokenize
from spambayes.storage import open_storage

import sb_filter

# We borrow the test messages that test_sb_server uses.
# I doubt it really makes much difference, but if we wanted more than
# one message of each type (the tests should all handle this ok) then
# Richie's hammer.py script has code for generating any number of
# randomly composed email messages.
from test_sb_server import good1, spam1
good1 = email.message_from_string(good1)
spam1 = email.message_from_string(spam1)

TEMP_DBM_NAME = os.path.join(os.path.dirname(__file__), "temp.dbm")
# The chances of anyone having a file with this name in the test
# directory is minute, but we don't want to wipe anything, so make
# sure that it doesn't already exist.  Our tearDown code gets rid
# of our copy (whether the tests pass or fail) so it shouldn't
# be ours.
if os.path.exists(TEMP_DBM_NAME):
    print TEMP_DBM_NAME, "already exists.  Please remove this file " \
          "before running these tests (a file by that name will be " \
          "created and destroyed as part of the tests)."
    sys.exit(1)

class HammieFilterTest(unittest.TestCase):
    def setUp(self):
        self.h = sb_filter.HammieFilter()
        self.h.dbname = TEMP_DBM_NAME
        self.h.usedb = "dbm"
    def tearDown(self):
        if self.h.h:
            self.h.close()
        try:
            os.remove(TEMP_DBM_NAME)
        except OSError:
            pass

    def _fake_store(self):
        self.done = True

    def test_open(self):
        mode = 'c'
        self.h.open(mode)
        self.assertEqual(self.h.mode, mode)
        # Check the underlying classifier exists.
        self.assert_(self.h.h is not None)
        # This can also be called when there is an
        # existing classifier, but we want to change
        # mode.  Verify that we store the old database
        # first if we were not in readonly mode.
        self.done = False
        self.h.h.store = self._fake_store
        mode = 'r'
        self.h.open(mode)
        self.assertEqual(self.h.mode, mode)
        self.assert_(self.done)

    def test_close_readonly(self):
        # Must open with 'c' first, because otherwise it doesn't exist.
        self.h.open('c')
        self.h.open('r')
        self.done = False
        self.h.h.store = self._fake_store
        # Verify that the classifier is not stored if we are
        # in readonly mode.
        self.h.close()
        self.assert_(not self.done)
        self.assertEqual(self.h.h, None)

    def test_close(self):
        self.h.open('c')
        self.done = False
        self.h.h.store = self._fake_store
        # Verify that the classifier is stored if we are
        # not in readonly mode.
        self.h.close()
        self.assert_(self.done)
        self.assertEqual(self.h.h, None)

    def test_newdb(self):
        # Create an existing classifier.
        b = open_storage(TEMP_DBM_NAME, "dbm")
        b.learn(tokenize(spam1), True)
        b.learn(tokenize(good1), False)
        b.store()
        b.close()

        # Create the fresh classifier.        
        self.h.newdb()
        
        # Verify that the classifier isn't open.
        self.assertEqual(self.h.h, None)

        # Verify that any existing classifier with the same name
        # is overwritten.
        b = open_storage(TEMP_DBM_NAME, "dbm")
        self.assertEqual(b.nham, 0)
        self.assertEqual(b.nspam, 0)
        b.close()

    def test_filter(self):
        # Verify that the msg has the classification header added.
        self.h.open('c')
        self.h.h.bayes.learn(tokenize(good1), False)
        self.h.h.bayes.learn(tokenize(spam1), True)
        self.h.h.store()
        result = email.message_from_string(self.h.filter(spam1))
        self.assert_(result[options["Headers",
                                    "classification_header_name"]].\
                     startswith(options["Headers", "header_spam_string"]))
        result = email.message_from_string(self.h.filter(good1))
        self.assert_(result[options["Headers",
                                    "classification_header_name"]].\
                     startswith(options["Headers", "header_ham_string"]))

    def test_filter_train(self):
        # Verify that the msg has the classification header
        # added, and that it was correctly trained.
        self.h.open('c')
        self.h.h.bayes.learn(tokenize(good1), False)
        self.h.h.bayes.learn(tokenize(spam1), True)
        self.h.h.store()
        result = email.message_from_string(self.h.filter_train(spam1))
        self.assert_(result[options["Headers",
                                    "classification_header_name"]].\
                     startswith(options["Headers", "header_spam_string"]))
        self.assertEqual(self.h.h.bayes.nspam, 2)
        result = email.message_from_string(self.h.filter_train(good1))
        self.assert_(result[options["Headers",
                                    "classification_header_name"]].\
                     startswith(options["Headers", "header_ham_string"]))
        self.assertEqual(self.h.h.bayes.nham, 2)

    def test_train_ham(self):
        # Verify that the classifier gets trained with the message.
        self.h.open('c')
        self.h.train_ham(good1)
        self.assertEqual(self.h.h.bayes.nham, 1)
        self.assertEqual(self.h.h.bayes.nspam, 0)
        for token in tokenize(good1):
            wi = self.h.h.bayes._wordinfoget(token)
            self.assertEqual(wi.hamcount, 1)
            self.assertEqual(wi.spamcount, 0)

    def test_train_spam(self):
        # Verify that the classifier gets trained with the message.
        self.h.open('c')
        self.h.train_spam(spam1)
        self.assertEqual(self.h.h.bayes.nham, 0)
        self.assertEqual(self.h.h.bayes.nspam, 1)
        for token in tokenize(spam1):
            wi = self.h.h.bayes._wordinfoget(token)
            self.assertEqual(wi.hamcount, 0)
            self.assertEqual(wi.spamcount, 1)

    def test_untrain_ham(self):
        self.h.open('c')
        # Put a message in the classifier to be removed.
        self.h.h.bayes.learn(tokenize(good1), False)
        # Verify that the classifier gets untrained with the message.
        self.h.untrain_ham(good1)
        self.assertEqual(self.h.h.bayes.nham, 0)
        self.assertEqual(self.h.h.bayes.nspam, 0)
        for token in tokenize(spam1):
            wi = self.h.h.bayes._wordinfoget(token)
            self.assertEqual(wi, None)

    def test_untrain_spam(self):
        self.h.open('c')
        # Put a message in the classifier to be removed.
        self.h.h.bayes.learn(tokenize(spam1), True)
        # Verify that the classifier gets untrained with the message.
        self.h.untrain_spam(spam1)
        self.assertEqual(self.h.h.bayes.nham, 0)
        self.assertEqual(self.h.h.bayes.nspam, 0)
        for token in tokenize(spam1):
            wi = self.h.h.bayes._wordinfoget(token)
            self.assertEqual(wi, None)


def suite():
    suite = unittest.TestSuite()
    for cls in (HammieFilterTest,
               ):
        suite.addTest(unittest.makeSuite(cls))
    return suite

if __name__=='__main__':
    sb_test_support.unittest_main(argv=sys.argv + ['suite'])
