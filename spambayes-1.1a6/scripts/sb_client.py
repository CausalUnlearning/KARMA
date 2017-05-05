#! /usr/bin/env python

"""A client for sb_xmlrpcserver.py.

Just feed it your mail on stdin, and it spits out the same message
with the spambayes score in a new X-Spambayes-Disposition header.

"""

import xmlrpclib
import sys

RPCBASE = "http://localhost:65000"

def main():
    msg = sys.stdin.read()
    try:
        x = xmlrpclib.ServerProxy(RPCBASE)
        m = xmlrpclib.Binary(msg)
        out = x.filter(m)
        print out.data
    except:
        if __debug__:
            import traceback
            traceback.print_exc()
        print msg

if __name__ == "__main__":
    main()
