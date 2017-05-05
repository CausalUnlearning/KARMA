def update_word_frequencies(current, new):
	new_word_vector = _vectorize(new)
	for word in new_word_vector:
		if word in current:
			current[word] += 1
		else:
			current[word] = 1
	return current

def revert_word_frequencies(current, forget):
	forget_word_vector = _vectorize(forget)
	for word in forget_word_vector:
		current[word] -= 1
	return current


def get_word_frequencies(msg):
	word_freq = {}
	word_vector = _vectorize(msg)
	for word in word_vector:
		word_freq[word] = 1
	return word_freq

def _vectorize(msg):
	return [t[1] for t in msg.clues]

def update_unlearned_features(u_f, c_f):
	for key,val in c_f.iteritems():
		if key not in u_f:
			u_f[key] = val
		else:
			u_f[key] += val
