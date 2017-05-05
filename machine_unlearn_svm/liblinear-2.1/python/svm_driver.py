""" Responsbile for training and predicting on data """
import liblinearutil as llu

def train(y, x, params):
    """ Trains on y,x and returns the model """
    print "Training on data of size: ", len(y)
    m = llu.train(y,x, params)
    return m


def predict(y, x, m):
    """ Tests on y,x using model m. Returns the final accuracy. """
    print "Predicting on data of size: ", len(y)
    p_label, p_acc, p_val = llu.predict(y, x, m)
    print "Accuracy: ", p_acc
    return (p_label, p_acc, p_val)
