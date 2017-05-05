#! /usr/bin/env python

"""Count the number of messages in Unix mboxes.

Usage: %(programs)s [-g] [-h] path1 ...
Options:

    -h
        Print this help message and exit
    -g
        Do globbing on each path.  This is helpful on Windows, where the
        native shells don't glob.
"""

"""
Stats for Barry's corpora, as of 26-Aug-2002, using then-current 2.3a0:

edu-sig-clean.mbox                 252 (+ unparseable: 0)
python-dev-clean.mbox             8326 (+ unparseable: 0)
mailman-developers-clean.mbox     2427 (+ unparseable: 0)
python-list-clean.mbox          159072 (+ unparseable: 2)
zope3-clean.mbox                  2177 (+ unparseable: 0)

Unparseable messages are likely spam.
zope3-clean.mbox is really from the zope3-dev mailing list.
The Python version matters because the email package varies across releases
in whether it uses strict or lax parsing.
"""

import sys
import mailbox
import getopt
import glob

from spambayes.mboxutils import get_message

program = sys.argv[0]

def usage(code, msg=''):
    print >> sys.stderr, __doc__
    if msg:
        print >> sys.stderr, msg
    sys.exit(code)

def count(fname):
    fp = open(fname, 'rb')
    mbox = mailbox.PortableUnixMailbox(fp, get_message)
    goodcount = 0
    badcount = 0
    for msg in mbox:
        if msg["to"] is None and msg["cc"] is None:
            badcount += 1
        else:
            goodcount += 1
    fp.close()
    return goodcount, badcount

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hg', ['help'])
    except getopt.error, msg:
        usage(1, msg)

    doglob = False
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt == '-g':
            doglob = True

    for path in args:
        if doglob:
            fnames = glob.glob(path)
        else:
            fnames = [path]

        for fname in fnames:
            goodn, badn = count(fname)
            print "%-35s %7d (+ unparseable: %d)" % (fname, goodn, badn)

if __name__ == '__main__':
    main()
