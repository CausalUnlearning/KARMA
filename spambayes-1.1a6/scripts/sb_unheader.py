#!/usr/bin/env python
"""
    sb_unheader.py: cleans headers from email messages. By default, this
    removes SpamAssassin headers, specify a pattern with -p to supply
    new headers to remove.

    This is often needed because existing spamassassin headers can
    provide killer spam clues, for all the wrong reasons.
"""

import re
import sys
import os
import glob
import mailbox
import email.Parser
import email.Message
import email.Generator
import getopt

def unheader(msg, pat):
    pat = re.compile(pat)
    for hdr in msg.keys():
        if pat.match(hdr):
            del msg[hdr]

# remain compatible with 2.2.1 - steal replace_header from 2.3 source
class Message(email.Message.Message):
    def replace_header(self, _name, _value):
        """Replace a header.

        Replace the first matching header found in the message, retaining
        header order and case.  If no matching header was found, a
        KeyError is raised.
        """
        _name = _name.lower()
        for i, (k, v) in zip(range(len(self._headers)), self._headers):
            if k.lower() == _name:
                self._headers[i] = (k, _value)
                break
        else:
            raise KeyError, _name

class Parser(email.Parser.HeaderParser):
    def __init__(self):
        email.Parser.Parser.__init__(self, Message)

def deSA(msg):
    if msg['X-Spam-Status']:
        if msg['X-Spam-Status'].startswith('Yes'):
            pct = msg['X-Spam-Prev-Content-Type']
            if pct:
                msg['Content-Type'] = pct

            pcte = msg['X-Spam-Prev-Content-Transfer-Encoding']
            if pcte:
                msg['Content-Transfer-Encoding'] = pcte

            subj = re.sub(r'\*\*\*\*\*SPAM\*\*\*\*\* ', '',
                          msg['Subject'] or "")
            if subj != msg["Subject"]:
                msg.replace_header("Subject", subj)

            body = msg.get_payload()
            newbody = []
            at_start = 1
            for line in body.splitlines():
                if at_start and line.startswith('SPAM: '):
                    continue
                elif at_start:
                    at_start = 0
                newbody.append(line)
            msg.set_payload("\n".join(newbody))
    unheader(msg, "X-Spam-")

def process_message(msg, dosa, pats):
    if pats is not None:
        unheader(msg, pats)
    if dosa:
        deSA(msg)

def process_mailbox(f, dosa=1, pats=None):
    gen = email.Generator.Generator(sys.stdout, maxheaderlen=0)
    for msg in mailbox.PortableUnixMailbox(f, Parser().parse):
        process_message(msg, dosa, pats)
        gen.flatten(msg, unixfrom=1)

def process_maildir(d, dosa=1, pats=None):
    parser = Parser()
    for fn in glob.glob(os.path.join(d, "cur", "*")):
        print ("reading from %s..." % fn),
        file = open(fn)
        msg = parser.parse(file)
        process_message(msg, dosa, pats)

        tmpfn = os.path.join(d, "tmp", os.path.basename(fn))
        tmpfile = open(tmpfn, "w")
        print "writing to %s" % tmpfn
        gen = email.Generator.Generator(tmpfile, maxheaderlen=0)
        gen.flatten(msg, unixfrom=0)

        os.rename(tmpfn, fn)

def usage():
    print >> sys.stderr, "usage: unheader.py [ -p pat ... ] [ -s ] folder"
    print >> sys.stderr, "-p pat gives a regex pattern used to eliminate unwanted headers"
    print >> sys.stderr, "'-p pat' may be given multiple times"
    print >> sys.stderr, "-s tells not to remove SpamAssassin headers"
    print >> sys.stderr, "-d means treat folder as a Maildir"

def main(args):
    headerpats = []
    dosa = 1
    ismbox = 1
    try:
        opts, args = getopt.getopt(args, "p:shd")
    except getopt.GetoptError:
        usage()
        sys.exit(1)
    else:
        for opt, arg in opts:
            if opt == "-h":
                usage()
                sys.exit(0)
            elif opt == "-p":
                headerpats.append(arg)
            elif opt == "-s":
                dosa = 0
            elif opt == "-d":
                ismbox = 0
        pats = headerpats and "|".join(headerpats) or None

        if len(args) != 1:
            usage()
            sys.exit(1)

        if ismbox:
            f = file(args[0])
            process_mailbox(f, dosa, pats)
        else:
            process_maildir(args[0], dosa, pats)

if __name__ == "__main__":
    main(sys.argv[1:])
