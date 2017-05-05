

file1 = open("/Users/AlexYang/GitHub/spambayes-1.1a6/testtools/Data/Spam/Set3/x1.txt", 'r')
file2 = open("/Users/AlexYang/GitHub/spambayes-1.1a6/testtools/Data/Spam/Set3/x4.txt", 'r')

words1 = file1.read().split()
words2 = file2.read().split()

count = 0
for word in words1:
    if word in words2:
        count += 1

print str(float(count) / float(len(words1)))