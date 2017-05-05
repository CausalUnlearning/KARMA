import Levenshtein
from math import sqrt
from spambayes.Options import options

l_distance = Levenshtein.distance


def e_s(x, is_eu):
    if is_eu:
        return x**2

    else:
        return x


def e_f(x, is_eu):
    if is_eu:
        return sqrt(x)

    else:
        return x


def distance(msg1, msg2, opt=None, is_eu=True):
    if opt is None:
        s = 0
        for i in range(min(len(msg1.clues), len(msg2.clues))):
            s += e_s(l_distance(msg1.clues[len(msg1.clues) - 1 - i][1], msg2.clues[len(msg2.clues) - 1 - i][1]), is_eu)

        # This basically adds for overlap; we can try removing this to see
        # if distance is a bit more accurate
        if len(msg1.clues) != len(msg2.clues):
            if len(msg1.clues) > len(msg2.clues):
                for i in range(len(msg1.clues) - len(msg2.clues)):
                    s += e_s(l_distance(msg1.clues[i][1], ""), is_eu)
            else:
                for i in range(len(msg2.clues) - len(msg1.clues)):
                    s += e_s(l_distance(msg2.clues[i][1], ""), is_eu)
        return e_f(s, is_eu)

    if opt == "ac":
        s = 0
        for i in range(min(len(msg1.allclues), len(msg2.allclues))):
            s += e_s(l_distance(msg1.allclues[len(msg1.clues) - 1 - i][1], msg2.allclues[len(msg2.clues) - 1 - i][1]),
                     is_eu)
        if len(msg1.allclues) != len(msg2.allclues):
            if len(msg1.allclues) > len(msg2.allclues):
                for i in range(len(msg1.allclues) - len(msg2.allclues)):
                    s += e_s(l_distance(msg1.allclues[i][1], ""), is_eu)
            else:
                for i in range(len(msg2.allclues) - len(msg1.allclues)):
                    s += e_s(l_distance(msg2.allclues[i][1], ""), is_eu)
        return e_f(s, is_eu)

    if opt == "ac-trunc":
        s = 0
        for i in range(min(len(msg1.allclues), len(msg2.allclues))):
            s += e_s(l_distance(msg1.allclues[i][1], msg2.allclues[i][1]), is_eu)
        return e_f(s, is_eu)

    if opt == "trunc":
        s = 0
        for i in range(min(len(msg1.clues), len(msg2.clues))):
            s += e_s(l_distance(msg1.clues[i][1], msg2.clues[i][1]), is_eu)
        return e_f(s, is_eu)

    if opt == "extreme":
        msg1.clues.sort()
        msg2.clues.sort()
        s = 0

        if len(msg1.clues) >= len(msg2.clues):
            i = 0
            j = len(msg2.clues) - 1

            while i < j:
                s += e_s(l_distance(msg1.clues[i][1], msg2.clues[i][1]), is_eu)
                s += e_s(l_distance(msg1.clues[j - len(msg2.clues) + len(msg1.clues)][1], msg2.clues[j][1]), is_eu)
                i += 1
                j -= 1

            if i == j:
                s += e_s(l_distance(msg1.clues[i][1], msg2.clues[i][1]), is_eu)
                i += 1
                j -= 1

            for i in range(i, j - len(msg2.clues) + len(msg1.clues) + 1):
                s += e_s(l_distance(msg1.clues[i][1], ""), is_eu)

        else:
            i = 0
            j = len(msg1.clues) - 1

            while i < j:
                s += e_s(l_distance(msg2.clues[i][1], msg1.clues[i][1]), is_eu)
                s += e_s(l_distance(msg2.clues[j - len(msg1.clues) + len(msg2.clues)][1], msg1.clues[j][1]), is_eu)
                i += 1
                j -= 1

            if i == j:
                s += e_s(l_distance(msg1.clues[i][1], msg2.clues[i][1]), is_eu)

            for i in range(i, j - len(msg1.clues) + len(msg2.clues) + 1):
                s += e_s(l_distance(msg2.clues[i][1], ""), is_eu)
        return e_f(s, is_eu)

    if opt == "extreme-trunc":
        msg1.allclues.sort()
        msg2.allclues.sort()
        s = 0

        if len(msg1.clues) >= len(msg2.clues):
            i = 0
            j = len(msg2.clues) - 1

            while i < j:
                s += e_s(l_distance(msg1.clues[i][1], msg2.clues[i][1]), is_eu)
                s += e_s(l_distance(msg1.clues[j - len(msg2.clues) + len(msg1.clues)][1], msg2.clues[j][1]), is_eu)
                i += 1
                j -= 1

            if i == j:
                s += e_s(l_distance(msg1.clues[i][1], msg2.clues[i][1]), is_eu)
                i += 1
                j -= 1

        else:
            i = 0
            j = len(msg1.clues) - 1

            while i < j:
                s += e_s(l_distance(msg2.clues[i][1], msg1.clues[i][1]), is_eu)
                s += e_s(l_distance(msg2.clues[j - len(msg1.clues) + len(msg2.clues)][1], msg1.clues[j][1]), is_eu)
                i += 1
                j -= 1

            if i == j:
                s += e_s(l_distance(msg1.clues[i][1], msg2.clues[i][1]), is_eu)
                i += 1
                j -= 1

        return e_f(s, is_eu)

    if opt == "ac-extreme":
        msg1.allclues.sort()
        msg2.allclues.sort()
        s = 0

        if len(msg1.allclues) >= len(msg2.allclues):
            i = 0
            j = len(msg2.allclues) - 1

            while i < j:
                s += e_s(l_distance(msg1.allclues[i][1], msg2.allclues[i][1]), is_eu)
                s += e_s(l_distance(msg1.allclues[j - len(msg2.allclues) + len(msg1.allclues)][1],
                                    msg2.allclues[j][1]), is_eu)
                i += 1
                j -= 1

            if i == j:
                s += e_s(l_distance(msg1.allclues[i][1], msg2.allclues[i][1]), is_eu)
                i += 1
                j -= 1

            for i in range(i, j - len(msg2.allclues) + len(msg1.allclues) + 1):
                s += e_s(l_distance(msg1.allclues[i][1], ""), is_eu)

        else:
            i = 0
            j = len(msg1.allclues) - 1

            while i < j:
                s += e_s(l_distance(msg2.allclues[i][1], msg1.allclues[i][1]), is_eu)
                s += e_s(l_distance(msg2.allclues[j - len(msg1.allclues) + len(msg2.allclues)][1],
                                    msg1.allclues[j][1]), is_eu)
                i += 1
                j -= 1

            if i == j:
                s += e_s(l_distance(msg1.allclues[i][1], msg2.allclues[i][1]), is_eu)

            for i in range(i, j - len(msg1.allclues) + len(msg2.allclues) + 1):
                s += e_s(l_distance(msg2.allclues[i][1], ""), is_eu)
        return e_f(s, is_eu)
