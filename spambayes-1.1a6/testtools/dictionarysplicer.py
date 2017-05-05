__author__ = 'Alex'
import os
import sys

sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from spambayes.Options import get_pathname_option
from os import listdir, remove


# Assume that Set3 is already populated with dictionaries to splice.
def splice(dict_dest, n):
    dictionary = open(dict_dest)
    splice_list = []
    for i in range(n):
        splice_list.append(open(dict_dest.replace(".spam.txt", "(" + str(i + 1) + ").spam.txt"), 'w'))
    line_c = 0
    for line in dict:
        splice_list[line_c % n].write(line)
        line_c += 1

    dictionary.close()


def splice_set(n, dir_num=3):
    destination = get_pathname_option("TestDriver", "spam_directories") % dir_num + "/"
    dict_c = 1
    for dictionary in listdir(destination):
        print "Slicing dictionary", dict_c, "into", n, "parts"
        splice(destination + dictionary, n)
        remove(destination + dictionary)
        dict_c += 1


def main():
    n = sys.argv[1]
    splice_set(int(n))

if __name__ == "__main__":
    main()
