from string import ascii_lowercase
from os import listdir, remove
from random import choice, sample
from spambayes.Options import get_pathname_option

default_dest = get_pathname_option("TestDriver", "spam_directories") % 3


def write_dictionary_sets(number_clusters=26, x=0.5, y=200, destination=default_dest):
    destination += "/"

    letterset = {}  # A dictionary of words: Key = Letter, Value = Words beginning with that letter

    for letter in ascii_lowercase:
        letterset[letter] = []

    with open("dictionary.txt", 'r') as dictionary:
        for line in dictionary:
            letter = line[0]
            letterset[letter].append(line.strip())

    keys = sample(letterset.keys(), number_clusters)
    for letter in keys:
        print "Writing sets for letter " + letter + " ..."
        x = x                       # Percentage overlap of words between sets
        y = y                       # Number of sets per letter
        o_set = letterset[letter]   # Size of original set of words beginning with letter
        b = len(o_set)              # Size of set being pulled from
        a = int(b * x)              # Size of resultant sets

        for i in range(y):
            with open(destination + str(letter) + str(i + 1) + ".txt", 'w') as outfile:
                output = []
                for k in range(a):
                    word = choice(o_set)
                    if word in output:
                        k -= 1
                        continue
                    else:
                        output.append(word)
                for word in output:
                    outfile.write(word + "\n")


def reset(destination=default_dest):
    print "Removing all dictionary sets..."
    dir = destination + "/"

    for dictionary in listdir(dir):
        print "Removing " + dir + dictionary
        remove(dir + dictionary)


def main():
    write_dictionary_sets(26, x=0.5, y=1000)

if __name__ == "__main__":
    main()
