from spambayes import TestDriver, msgs
from spambayes.Options import get_pathname_option
from tabulate import tabulate
from dictionarywriter import DictionaryWriter

def test():

    y = [0, 60, 120, 240, 480]

    hamdirs = [get_pathname_option("TestDriver", "ham_directories") % i for i in range(1, 4)]
    spamdirs = [get_pathname_option("TestDriver", "spam_directories") % i for i in range(1, 4)]

    d = TestDriver.Driver()
    d.new_classifier()
    d.train(msgs.HamStream(hamdirs[0], [hamdirs[0]]),
            msgs.SpamStream(spamdirs[0], [spamdirs[0]]))

    mislabeled = [[], [], []]
    prev_detection_rate = None

    detection_rates = []
    detection_rates_on_mislabeled = []
    correct_results = []
    results_from_mislabeled = []
    for y_val in y:
        dw = DictionaryWriter(y_val)
        dw.reset()
        dw.write()

        d.train(msgs.HamStream(hamdirs[2], [hamdirs[2]]),
                msgs.SpamStream(spamdirs[2], [spamdirs[2]]))

        if y_val is 0:  # Initial Test
            d.test(msgs.HamStream(hamdirs[1], [hamdirs[1]]),
                   msgs.SpamStream(spamdirs[1], [spamdirs[1]]))

            rate = d.tester.correct_classification_rate()
            mislabeled[0] = d.tester.ham_wrong_examples    # Ham mislabeled as Spam
            mislabeled[1] = d.tester.spam_wrong_examples   # Spam mislabeled as Ham
            mislabeled[2] = d.tester.unsure_examples       # Unsure

            ham = []
            spam = []

            ham += mislabeled[0]
            spam += mislabeled[1]

            for msg in mislabeled[2]:
                if msg.tag.endswith(".ham.txt"):
                    ham.append(msg)
                elif msg.tag.endswith(".spam.txt"):
                    spam.append(msg)
                else:
                    print "What"
                    exit()

            d.test(ham, spam)
            m_rate = d.tester.correct_classification_rate()

            detection_rates.append(rate)
            prev_detection_rate = rate
            correct_results.append("")
            results_from_mislabeled.append("")
            detection_rates_on_mislabeled.append(m_rate)

            d.untrain(msgs.HamStream(hamdirs[2], [hamdirs[2]]),
                      msgs.SpamStream(spamdirs[2], [spamdirs[2]]))
            dw.reset()
        else:
            d.test(msgs.HamStream(hamdirs[1], [hamdirs[1]]),
                   msgs.SpamStream(spamdirs[1], [spamdirs[1]]))

            rate = d.tester.correct_classification_rate()
            detection_rates.append(rate)

            if rate > prev_detection_rate:
                correct_results.append("Improved")
            elif rate < prev_detection_rate:
                correct_results.append("Worsened")
            else:
                correct_results.append("Unchanged")

            prev_detection_rate = rate

            ham = []
            spam = []

            ham += mislabeled[0]
            spam += mislabeled[1]

            #for msg in mislabeled[2]:
            #    if msg.tag.endswith(".ham.txt"):
            #        ham.append(msg)
            #    elif msg.tag.endswith(".spam.txt"):
            #        spam.append(msg)
            #    else:
            #        print "What"
            #        exit()

            d.test(ham, spam)
            rate = d.tester.correct_classification_rate()
            detection_rates_on_mislabeled.append(rate)

            dw.reset()

    outfile = open("mislabeled_rates.txt", 'w')
    outfile.write(tabulate({"# of Dictionaries": y, "Detection Rate": detection_rates, "True Change": correct_results,
                            "Detection Rate from Mislabeled": detection_rates_on_mislabeled,
                            "Interpreted Change": results_from_mislabeled},
                           headers="keys"))

def main():
    test()

if __name__ == "__main__":
    test()
