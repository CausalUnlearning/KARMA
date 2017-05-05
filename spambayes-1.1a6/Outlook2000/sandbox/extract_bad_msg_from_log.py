# extract_bad_msg_from_log.py

import sys

def main(argv = None):
    if argv is None: argv = sys.argv
    if len(argv) < 2:
        print "Need log filename"
        return
    f = open(argv[1])
    trigger = "FAILED to create email.message from:  "
    quotes = "'\""
    for line in f:
        if line.startswith(trigger):
            msg_repr = line[len(trigger):]
            if msg_repr[0] not in quotes or msg_repr[-2] not in quotes:
                print "eeek - not a string repr!"
                return
            msg_str = eval(msg_repr)
            # damn it - stderr in text mode
            msg_str = msg_str.replace("\r\n", "\n")
            sys.stdout.write(msg_str)

    inname = sys.argv[1]

if __name__=='__main__':
    main()
