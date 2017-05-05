__author__ = "Alex"

import time
import sys
import os
sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from spambayes import quickselect
from random import shuffle


def main():
	k_smallest = quickselect.k_smallest
	l_1 = []

	l_1 = [i for i in range(10000)]
	shuffle(l_1)
	l_2 = [item for item in l_1]

	start_1 = time.time()
	l_1.sort()
	c_1 = l_1[:100]
	end_1 = time.time()

	start_2 = time.time()
	c_5 = k_smallest(l_2, 100)
	end_2 = time.time()

	secs_1 = end_1 - start_1
	secs_2 = end_2 - start_2

	print "Time 1:", secs_1, "\n"
	print "Time 2:", secs_2, "\n"

main()