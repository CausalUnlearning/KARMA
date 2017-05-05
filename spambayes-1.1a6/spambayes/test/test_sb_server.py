#! /usr/bin/env python

"""Test the POP3 proxy is working correctly.

Given no command line options, carries out a test that the
POP3 proxy can be connected to, that incoming mail is classified,
that pipelining is removed from the CAPA[bility] query, and that the
web ui is present.

The -t option runs a fake POP3 server on port 8110.  This is the
same server that test uses, and may be separately run for other
testing purposes.

Usage:

    test_sb-server.py [options]

        options:
            -t      : Runs a fake POP3 server on port 8110 (for testing).
            -h      : Displays this help message.
"""

# This module is part of the spambayes project, which is Copyright 2002-5
# The Python Software Foundation and is covered by the Python Software
# Foundation license.

__author__ = "Richie Hindle <richie@entrian.com>"
__credits__ = "All the Spambayes folk."

# This code originally formed a part of pop3proxy.py.  If you are examining
# the history of this file, you may need to go back to there.

todo = """
Web training interface:

 o Functional tests.
"""

# One example of spam and one of ham - both are used to train, and are
# then classified.  Not a good test of the classifier, but a perfectly
# good test of the POP3 proxy.  The bodies of these came from the
# spambayes project, and Richie added the headers because the
# originals had no headers.

spam1 = """From: friend@public.com
Subject: Make money fast

Hello tim_chandler , Want to save money ?
Now is a good time to consider refinancing. Rates are low so you can cut
your current payments and save money.

http://64.251.22.101/interest/index%38%30%300%2E%68t%6D

Take off list on site [s5]
"""

good1 = """From: chris@example.com
Subject: ZPT and DTML

Jean Jordaan wrote:
> 'Fraid so ;>  It contains a vintage dtml-calendar tag.
>   http://www.zope.org/Members/teyc/CalendarTag
>
> Hmm I think I see what you mean: one needn't manually pass on the
> namespace to a ZPT?

Yeah, Page Templates are a bit more clever, sadly, DTML methods aren't :-(

Chris
"""

# An example of a particularly nasty malformed message - where there is
# no body, and no separator, which would at one point slip through
# SpamBayes.  This is an example that Tony made up.

malformed1 = """From: ta-meyer@ihug.co.nz
Subject: No body, and no separator"""

import asyncore
import socket
import operator
import re
import time
import getopt
import sys, os

import sb_test_support
sb_test_support.fix_sys_path()

from spambayes import Dibbler
from spambayes import tokenizer
from spambayes.UserInterface import UserInterfaceServer
from spambayes.ProxyUI import ProxyUserInterface
from sb_server import BayesProxyListener
from sb_server import state, _recreateState
from spambayes.Options import options

# HEADER_EXAMPLE is the longest possible header - the length of this one
# is added to the size of each message.
HEADER_EXAMPLE = '%s: xxxxxxxxxxxxxxxxxxxx\r\n' % \
                 options["Headers", "classification_header_name"]

# Our simulated slow POP3 server transmits about 100 characters per second.
PER_CHAR_DELAY = 0.01

class Listener(Dibbler.Listener):
    """Listener for TestPOP3Server.  Works on port 8110, to co-exist
    with real POP3 servers."""

    def __init__(self, socketMap=asyncore.socket_map):
        Dibbler.Listener.__init__(self, 8110, TestPOP3Server,
                                  (socketMap,), socketMap=socketMap)


class TestPOP3Server(Dibbler.BrighterAsyncChat):
    """Minimal POP3 server, for testing purposes.  Doesn't support
    UIDL.  USER, PASS, APOP, DELE and RSET simply return "+OK"
    without doing anything.  Also understands the 'KILL' command, to
    kill it, and a 'SLOW' command, to change to really slow retrieval.
    The mail content is the example messages above.
    """

    def __init__(self, clientSocket, socketMap):
        # Grumble: asynchat.__init__ doesn't take a 'map' argument,
        # hence the two-stage construction.
        Dibbler.BrighterAsyncChat.__init__(self, map=socketMap)
        Dibbler.BrighterAsyncChat.set_socket(self, clientSocket, socketMap)
        self.maildrop = [spam1, good1, malformed1]
        self.set_terminator('\r\n')
        self.okCommands = ['USER', 'PASS', 'APOP', 'NOOP', 'SLOW',
                           'DELE', 'RSET', 'QUIT', 'KILL']
        self.handlers = {'CAPA': self.onCapa,
                         'STAT': self.onStat,
                         'LIST': self.onList,
                         'RETR': self.onRetr,
                         'TOP': self.onTop}
        self.push("+OK ready\r\n")
        self.request = ''
        self.push_delay = 0.0 # 0.02 is a useful value for testing.

    def collect_incoming_data(self, data):
        """Asynchat override."""
        self.request = self.request + data

    def found_terminator(self):
        """Asynchat override."""
        if ' ' in self.request:
            command, args = self.request.split(None, 1)
        else:
            command, args = self.request, ''
        command = command.upper()
        if command in self.okCommands:
            self.push("+OK (we hope)\r\n")
            if command == 'QUIT':
                self.close_when_done()
            elif command == 'KILL':
                self.socket.shutdown(2)
                self.close()
                raise SystemExit
            elif command == 'SLOW':
                self.push_delay = PER_CHAR_DELAY
        else:
            handler = self.handlers.get(command, self.onUnknown)
            self.push_slowly(handler(command, args))
        self.request = ''

    def push_slowly(self, response):
        """Sometimes we push out the response slowly to try and generate
        timeouts.  If the delay is 0, this just does a regular push."""
        if self.push_delay:
            for c in response.split('\n'):
                if c and c[-1] == '\r':
                    self.push(c + '\n')
                else:
                    # We want to trigger onServerLine, so need the '\r',
                    # so modify the message just a wee bit.
                    self.push(c + '\r\n')
                time.sleep(self.push_delay * len(c))
        else:
            self.push(response)

    def onCapa(self, command, args):
        """POP3 CAPA command.  This lies about supporting pipelining for
        test purposes - the POP3 proxy *doesn't* support pipelining, and
        we test that it correctly filters out that capability from the
        proxied capability list. Ditto for STLS."""
        lines = ["+OK Capability list follows",
                 "PIPELINING",
                 "STLS",
                 "TOP",
                 ".",
                 ""]
        return '\r\n'.join(lines)

    def onStat(self, command, args):
        """POP3 STAT command."""
        maildropSize = reduce(operator.add, map(len, self.maildrop))
        maildropSize += len(self.maildrop) * len(HEADER_EXAMPLE)
        return "+OK %d %d\r\n" % (len(self.maildrop), maildropSize)

    def onList(self, command, args):
        """POP3 LIST command, with optional message number argument."""
        if args:
            try:
                number = int(args)
            except ValueError:
                number = -1
            if 0 < number <= len(self.maildrop):
                return "+OK %d\r\n" % len(self.maildrop[number-1])
            else:
                return "-ERR no such message\r\n"
        else:
            returnLines = ["+OK"]
            for messageIndex in range(len(self.maildrop)):
                size = len(self.maildrop[messageIndex])
                returnLines.append("%d %d" % (messageIndex + 1, size))
            returnLines.append(".")
            return '\r\n'.join(returnLines) + '\r\n'

    def _getMessage(self, number, maxLines):
        """Implements the POP3 RETR and TOP commands."""
        if 0 < number <= len(self.maildrop):
            message = self.maildrop[number-1]
            try:
                headers, body = message.split('\n\n', 1)
            except ValueError:
                return "+OK %d octets\r\n%s\r\n.\r\n" % (len(message),
                                                         message)
            bodyLines = body.split('\n')[:maxLines]
            message = headers + '\r\n\r\n' + '\n'.join(bodyLines)
            return "+OK\r\n%s\r\n.\r\n" % message
        else:
            return "-ERR no such message\r\n"

    def onRetr(self, command, args):
        """POP3 RETR command."""
        try:
            number = int(args)
        except ValueError:
            number = -1
        return self._getMessage(number, 12345)

    def onTop(self, command, args):
        """POP3 RETR command."""
        try:
            number, lines = map(int, args.split())
        except ValueError:
            number, lines = -1, -1
        return self._getMessage(number, lines)

    def onUnknown(self, command, args):
        """Unknown POP3 command."""
        return "-ERR Unknown command: %s\r\n" % repr(command)


def helper():
    """Runs a self-test using TestPOP3Server, a minimal POP3 server
    that serves the example emails above.
    """
    # Run a proxy and a test server in separate threads with separate
    # asyncore environments.
    import threading
    state.isTest = True
    testServerReady = threading.Event()
    def runTestServer():
        testSocketMap = {}
        Listener(socketMap=testSocketMap)
        testServerReady.set()
        asyncore.loop(map=testSocketMap)

    proxyReady = threading.Event()
    def runUIAndProxy():
        httpServer = UserInterfaceServer(8881)
        proxyUI = ProxyUserInterface(state, _recreateState)
        httpServer.register(proxyUI)
        BayesProxyListener('localhost', 8110, ('', 8111))
        state.bayes.learn(tokenizer.tokenize(spam1), True)
        state.bayes.learn(tokenizer.tokenize(good1), False)
        proxyReady.set()
        Dibbler.run()

    testServerThread = threading.Thread(target=runTestServer)
    testServerThread.setDaemon(True)
    testServerThread.start()
    testServerReady.wait()
    
    proxyThread = threading.Thread(target=runUIAndProxy)
    proxyThread.setDaemon(True)
    proxyThread.start()
    proxyReady.wait()

    # Connect to the proxy and the test server.
    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy.connect(('localhost', 8111))
    response = proxy.recv(100)
    assert response == "+OK ready\r\n"
    pop3Server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    pop3Server.connect(('localhost', 8110))
    response = pop3Server.recv(100)
    assert response == "+OK ready\r\n"

    # Verify that the test server claims to support pipelining.
    pop3Server.send("capa\r\n")
    response = pop3Server.recv(1000)
    assert response.find("PIPELINING") >= 0

    # Ask for the capabilities via the proxy, and verify that the proxy
    # is filtering out the PIPELINING capability.
    proxy.send("capa\r\n")
    response = proxy.recv(1000)
    assert response.find("PIPELINING") == -1

    # Verify that the test server claims to support STLS.
    pop3Server.send("capa\r\n")
    response = pop3Server.recv(1000)
    assert response.find("STLS") >= 0

    # Ask for the capabilities via the proxy, and verify that the proxy
    # is filtering out the STLS capability.
    proxy.send("capa\r\n")
    response = proxy.recv(1000)
    assert response.find("STLS") == -1

    # Stat the mailbox to get the number of messages.
    proxy.send("stat\r\n")
    response = proxy.recv(100)
    count, totalSize = map(int, response.split()[1:3])
    assert count == 3

    # Loop through the messages ensuring that they have judgement
    # headers.
    for i in range(1, count+1):
        response = ""
        proxy.send("retr %d\r\n" % i)
        while response.find('\n.\r\n') == -1:
            response = response + proxy.recv(1000)
        assert response.find(options["Headers", "classification_header_name"]) >= 0

    # Check that the proxy times out when it should.  The consequence here
    # is that the first packet we receive from the proxy will contain a
    # partial message, so we assert for that.  At 100 characters per second
    # with a 1-second timeout, the message needs to be significantly longer
    # than 100 characters to ensure that the timeout fires, so we make sure
    # we use a message that's at least 200 characters long.
    assert len(spam1) >= 2 * (1/PER_CHAR_DELAY)
    options["pop3proxy", "retrieval_timeout"] = 1
    options["Headers", "include_evidence"] = False
    proxy.send("slow\r\n")
    response = proxy.recv(100)
    assert response.find("OK") != -1
    proxy.send("retr 1\r\n")
    response = proxy.recv(1000)
    assert len(response) < len(spam1)

    # Smoke-test the HTML UI.
    httpServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    httpServer.connect(('localhost', 8881))
    httpServer.sendall("get / HTTP/1.0\r\n\r\n")
    response = ''
    while 1:
        packet = httpServer.recv(1000)
        if not packet: break
        response += packet
    assert re.search(r"(?s)<html>.*SpamBayes proxy.*</html>", response)

    # Kill the proxy and the test server.
    proxy.sendall("kill\r\n")
    proxy.recv(100)
    pop3Server.sendall("kill\r\n")
    pop3Server.recv(100)

def test_run():
    # Read the arguments.
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'ht')
    except getopt.error, msg:
        print >>sys.stderr, str(msg) + '\n\n' + __doc__
        sys.exit()

    state.isTest = True
    runSelfTest = True
    for opt, arg in opts:
        if opt == '-h':
            print >>sys.stderr, __doc__
            sys.exit()
        elif opt == '-t':
            state.isTest = True
            state.runTestServer = True
            runSelfTest = False

    state.createWorkers()

    if runSelfTest:
        print "\nRunning self-test...\n"
        state.buildServerStrings()
        helper()
        print "Self-test passed."   # ...else it would have asserted.

    elif state.runTestServer:
        print "Running a test POP3 server on port 8110..."
        Listener()
        asyncore.loop()


if __name__ == '__main__':
    test_run()
