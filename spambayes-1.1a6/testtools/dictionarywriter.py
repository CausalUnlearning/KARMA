from os import listdir, remove
import os
import sys

sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))
from spambayes.Options import get_pathname_option


class DictionaryWriter:
    # A simple class to write dictionaries to Set 3 of the spam directories.
    # Used for unlearning experiments.

    def __init__(self, num_files, dir_num=3):
        self.NUMFILES = num_files
        self.destination = get_pathname_option("TestDriver", "spam_directories") % dir_num + "/"
        self.destination_files = listdir(self.destination)

    def reset(self):
        """Deletes all dictionary files"""
        print "Deleting Dictionary Files..."

        for dictionary in listdir(self.destination):
            remove(self.destination + dictionary)

    def write(self):

        self.reset()

        print "Initial # of Files: " + str(len(self.destination_files))

        if self.dictionary:
            for i in range(0, self.NUMFILES):
                print "Preparing dictionary.txt # " + str(i + 1)

                file_in = open("dictionary.txt", 'r')
                file_out = open(self.destination + "00000dictionary" + str(i + 1) + ".spam" + ".txt", 'w')

                file_out.write(file_in.read())

                file_in.close()
                file_out.close()

        if self.wordlist:
            for i in range(0, self.NUMFILES):
                print "Preparing wordlist.txt # " + str(i + 1)

                file_in = open("wordlist.txt", 'r')
                file_out = open(self.destination + "00000wordlist" + str(i + 1) + ".spam" + ".txt", 'w')

                file_out.write(file_in.read())

                file_in.close()
                file_out.close()

        if self.words:
            for i in range(0, self.NUMFILES):
                print "Preparing words.txt # " + str(i + 1)

                file_in = open("words.txt", 'r')
                file_out = open(self.destination + "00000words" + str(i + 1) + ".spam" + ".txt", 'w')

                file_out.write(file_in.read())

                file_in.close()
                file_out.close()

        if self.wordsEn:
            for i in range(0, self.NUMFILES):
                print "Preparing wordsEn.txt # " + str(i + 1)

                file_in = open("wordsEn.txt", 'r')
                file_out = open(self.destination + "00000wordsEn" + str(i + 1) + ".spam" + ".txt", 'w')

                file_out.write(file_in.read())

                file_in.close()
                file_out.close()

        self.destination_files = listdir(self.destination)
        print "Final # of Files: " + str(len(self.destination_files))


def main():
    dw = DictionaryWriter(100)

    dw.write()

if __name__ == "__main__":
    main()
