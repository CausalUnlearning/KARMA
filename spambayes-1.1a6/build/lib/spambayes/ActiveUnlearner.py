# Keeps track of characteristics for benign and pollutant emails

class ActiveUnlearn:

    # Takes in training ham and spam
    def __init__(self, ham, spam):
        self.visited = set()
        self.benign = set()
        self.pollutant = set()
        self.ham = ham
        self.spam = spam

    def add_benign(self, message):
        self.benign.add(message)

    def add_pollutant(self, message):
        self.pollutant.add(message)

