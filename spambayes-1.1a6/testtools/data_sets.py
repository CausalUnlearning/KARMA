__author__ = 'Alex'

import os, sys

sys.path.insert(-1, os.getcwd())
from io_locations import *


def seterize(main_dir, sub_dir, is_spam, n):
    if is_spam:
        parent_dir = main_dir + "/" + sub_dir + "/" + "Spam" + "/" + "Set%d"

    else:
        parent_dir = main_dir + "/" + sub_dir + "/" + "Ham" + "/" + "Set%d"

    return [parent_dir % i for i in range(1, n + 1)]


def dir_enumerate(dir_name):
    return len([name for name in os.listdir(dir_name) if os.path.isfile(os.path.join(dir_name, name))])


def seconds_to_english(seconds):
    seconds_trunc_1 = int(seconds // 60) * 60
    s = seconds - seconds_trunc_1
    seconds -= s
    seconds /= 60
    seconds_trunc_2 = int(seconds // 60) * 60
    m = int(seconds - seconds_trunc_2)
    h = seconds_trunc_2 / 60
    return str(h) + " hours, " + str(m) + " minutes, and " + str(s) + " seconds."


class VirtualDir:
    def __init__(self, content=None):
        self.content = content if content is not None else []

    def __iter__(self):
        for item in self.content:
            yield item

    def __str__(self):
        return str(len(self.content)) + " items"

    def __repr__(self):
        return str(len(self.content)) + " items"


hams = [seterize(data_sets_dir, set_dir, False, 3) for set_dir in set_dirs]
spams = [seterize(data_sets_dir, set_dir, True, 3) for set_dir in set_dirs]

