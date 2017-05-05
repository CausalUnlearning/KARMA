from spambayes.Options import get_pathname_option
from os import listdir

class InjectionPolluter:

    # Inject a common feature into some mislabeled benign data samples

    def __init__(self, spam_feature=None, ham_feature=None, inject_type=0):

        self.h_injected = get_pathname_option("TestDriver", "ham_directories") % 3 + "/"
        self.s_injected = get_pathname_option("TestDriver", "spam_directories") % 3 + "/"

        if inject_type is 0:
            self.feature = spam_feature
        elif inject_type is 1:
            self.feature = ham_feature

    # Remove all injected features
    def reset(self):
        print "Resetting ..."

        for email in listdir(self.h_injected):
            print "Clearing pollution from " + email
            current = open(self.h_injected + email, 'r')
            lines = current.readlines()
            current.close()
            new_lines = []
            for line in lines:
                if self.feature not in line:
                    new_lines.append(line)
                else:
                    continue
            print new_lines

            current = open(self.h_injected + email, 'w')
            for line in new_lines:
                current.write(line)
            current.close()

        for email in listdir(self.s_injected):
            print "Clearing pollution from " + email
            current = open(self.s_injected + email, 'r')
            lines = current.readlines()
            current.close()
            new_lines = []
            for line in lines:
                if self.feature not in line:
                    new_lines.append(line)
                else:
                    continue

            current = open(self.s_injected + email, 'w')
            for line in new_lines:
                current.write(line)
            current.close()

    def injectfeatures(self):
        for email in listdir(self.h_injected):
            current = open(self.h_injected + email, 'a')
            current.write("\n" + self.feature)
            current.close()
        for email in listdir(self.s_injected):
            current = open(self.s_injected + email, 'a')
            current.write("\n" + self.feature)
            current.close()

def main():
    IP = InjectionPolluter(6000, 5, 3)

    IP.reset()


if __name__ == "__main__":
    main()
