import os
import sys

sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from os import listdir
from random import randint, choice
from shutil import move
from spambayes.Options import get_pathname_option


class BenignFileMover:
    # A class that moves a given number of randomly selected files
    # from Set1 to Set2 of both the spam and ham directories. The
    # class randomly divides the given number between ham and spam.

    def __init__(self, number):
        self.NUMBER = number

        self.ham_num = self.NUMBER
        self.ham_source = get_pathname_option("TestDriver", "ham_directories") % 1 + "/"
        self.ham_test = get_pathname_option("TestDriver", "ham_directories") % 2 + "/"
        self.ham_destination = get_pathname_option("TestDriver", "ham_directories") % 3 + "/"
        self.ham_source_files = listdir(self.ham_source)
        self.ham_destination_files = listdir(self.ham_destination)

        self.spam_num = 0
        self.spam_source = get_pathname_option("TestDriver", "spam_directories") % 1 + "/"
        self.spam_test = get_pathname_option("TestDriver", "spam_directories") % 2 + "/"
        self.spam_destination = get_pathname_option("TestDriver", "spam_directories") % 3 + "/"
        self.spam_source_files = listdir(self.spam_source)
        self.spam_destination_files = listdir(self.spam_destination)

    def reset(self):
        """Returns all files in Set3 of both spam and ham to their respective Set1"""
        print "Replacing Files..."
        for ham in self.ham_destination_files:
            print " - \tReturning " + ham + " from Ham Set3 to Set1"
            move(self.ham_destination + ham, self.ham_source + ham)

        for spam in self.spam_destination_files:
            print " - \tReturning " + spam + " from Spam Set3 to Set1"
            move(self.spam_destination + spam, self.spam_source + spam)

    def print_filelist(self):
        """Prints the number of files in all Sets, for both Spam and Ham"""
        print "File List:"
        print " - \tFiles in Ham Set1: " + str(listdir(self.ham_source).__len__())
        print " - \tFiles in Ham Set2: " + str(listdir(self.ham_test).__len__())
        print " - \tFiles in Ham Set3: " + str(listdir(self.ham_destination).__len__())
        print " - \tFiles in Spam Set1: " + str(listdir(self.spam_source).__len__())
        print " - \tFiles in Spam Set2: " + str(listdir(self.spam_test).__len__())
        print " - \tFiles in Spam Set3: " + str(listdir(self.spam_destination).__len__())

    def random_move_file(self):
        """Moves a number of random files from Set1 of both spam and ham to Set3"""

        # move 'number' files to the destination
        print "Number of Ham Files to Move: " + str(self.ham_num)
        for i in range(self.ham_num):
            ham = choice(self.ham_source_files)

            self.ham_source_files.remove(ham)

            print "(" + str(i + 1) + ")" + "\tMoving file " + ham

            if ham in self.ham_destination_files:
                i -= 1
                continue
            else:
                move(self.ham_source + ham, self.ham_destination + ham)

        print "Number of Spam Files to Move: " + str(self.spam_num)
        for i in range(self.spam_num):
            spam = choice(self.spam_source_files)

            self.spam_source_files.remove(spam)

            print "(" + str(i + 1) + ")" + "\tMoving file " + spam

            if spam in self.spam_destination_files:
                i -= 1
                continue
            else:
                move(self.spam_source + spam, self.spam_destination + spam)

        self.print_filelist()


def main():
    f = BenignFileMover(3000)

    f.print_filelist()

if __name__ == "__main__":
    main()
