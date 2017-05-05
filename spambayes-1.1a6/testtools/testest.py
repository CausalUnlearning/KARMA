__author__ = 'Alex'


def main():
    import os
    import sys
    import shutil

    sys.path.insert(-1, os.getcwd())
    sys.path.insert(-1, os.path.dirname(os.getcwd()))

    from spambayes import ActiveUnlearnDriver
    from spambayes.Options import get_pathname_option
    from spambayes import msgs
    import time

    ham = [get_pathname_option("TestDriver", "ham_directories") % i for i in range(1, 5)]
    spam = [get_pathname_option("TestDriver", "spam_directories") % i for i in range(1, 5)]

    for i in range(1):
        au = ActiveUnlearnDriver.ActiveUnlearnDriver([msgs.HamStream(ham[0], [ham[0]]),
                                                      msgs.HamStream(ham[2], [ham[2]]),
                                                      msgs.HamStream(ham[3], [ham[3]])],
                                                     [msgs.SpamStream(spam[0], [spam[0]]),
                                                      msgs.SpamStream(spam[2], [spam[2]]),
                                                      msgs.SpamStream(spam[3], [spam[3]])],
                                                     msgs.HamStream(ham[2], [ham[2]]),
                                                     msgs.SpamStream(spam[2], [spam[2]]),
                                                     "ac-extreme")


        au.driver.test(msgs.HamStream(ham[0], [ham[0]]), msgs.SpamStream(spam[0], [spam[0]]))
        au.driver.untrain(msgs.HamStream(ham[2], [ham[2]]), msgs.SpamStream(spam[2], [spam[2]]))
        au.driver.untrain(msgs.HamStream(ham[3], [ham[3]]), msgs.SpamStream(spam[3], [spam[3]]))
        au.driver.test(msgs.HamStream(ham[0], [ham[0]]), msgs.SpamStream(spam[0], [spam[0]]))
        msg = au.driver.tester.test_examples[5]

        shutil.copy(msg.tag, "C:\Users\Alex\Desktop\clustera")
        print msg.prob

        start_time = time.time()
        cluster = (au.cluster(msg, 10))
        end_time = time.time()
        print cluster

        clueslist = []
        for clue in msg.clues:
            clueslist.append((clue[0], clue[1]))
        print clueslist

        with open("C:\Users\Alex\Desktop\clustera\cluster7.txt", 'w') as outfile:
            spamcounter = 0
            for sim in cluster:
                with open(sim.tag) as infile:
                    if sim.tag.endswith(".spam.txt"):
                        outfile.write("SPAMSPAMSPAMSPAMSPAM" + "\n\n")
                    if sim.tag.endswith(".ham.txt"):
                        outfile.write("HAMHAMHAMHAMHAM" + "\n\n")

                    outfile.write(infile.read())
                    outfile.write("\n\n" + "----------------------------------------" + "\n\n")

                if sim.tag.endswith(".spam.txt"):
                    spamcounter += 1

            print spamcounter

        print end_time - start_time

if __name__ == "__main__":
    main()
