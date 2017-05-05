"""Spam-filtering proxy for a POP3 server.

The implementation uses the SocketServer module to run a
multi-threaded POP3 proxy.  It adds an X-Spambayes header with a spam
probability.  It scores a message using a persistent spambayes
classifier loaded from a ZEO server.

The strategy for adding spam headers is from Richie Hindle's
pop3proxy.py.  The STAT, LIST, RETR, and TOP commands are intercepted
to change the number of bytes the client is told to expect and/or to
insert the spam header.

The proxy can connect to any real POP3 server.  It parses the USER
command to figure out the address of the real server.  It expects the
USER argument to follow this format user@server[:port].  For example,
if you configure your POP client to send USER jeremy@example.com:111.
It will connect to a server on port 111 at example.com and send it the
command USER jeremy.

XXX A POP3 server sometimes adds the number of bytes in the +OK
response to some commands when the POP3 spec doesn't require it to.
In those case, the proxy does not re-write the number of bytes.  I
assume the clients won't be confused by this behavior, because they
shouldn't be expecting to see the number of bytes.

POP3 is documented in RFC 1939.
"""

import SocketServer
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

import email
import re
import socket
import sys
import time

import zLOG

from spambayes.tokenizer import tokenize
import pspam.database
from spambayes.Options import options

HEADER = "X-Spambayes: %5.3f\r\n"
HEADER_SIZE = len(HEADER % 0.0)

VERSION = 0.1

class POP3ProxyServer(SocketServer.ThreadingTCPServer):

    allow_reuse_address = True

    def __init__(self, addr, handler, classifier, log, zodb):
        SocketServer.ThreadingTCPServer.__init__(self, addr, handler)
        self.classifier = classifier
        self.log = log
        self.zodb = zodb

class LogWrapper:

    def __init__(self, log, file):
        self.log = log
        self.file = file

    def readline(self):
        line = self.file.readline()
        self.log.write(line)
        return line

    def write(self, buf):
        self.log.write(buf)
        return self.file.write(buf)

    def close(self):
        self.file.close()

class POP3RequestHandler(SocketServer.StreamRequestHandler):
    """Act as proxy between POP client and server."""

    def read_user(self):
        # XXX This could be cleaned up a bit.
        line = self.rfile.readline()
        if line == "":
            return False
        parts = line.split()
        if parts[0] != "USER":
            self.wfile.write("-ERR Invalid command; must specify USER first\n")
            return False
        user = parts[1]
        i = user.rfind("@")
        username = user[:i]
        server = user[i+1:]
        i = server.find(":")
        if i == -1:
            server = server, 110
        else:
            port = int(server[i+1:])
            server = server[:i], port
        zLOG.LOG("POP3", zLOG.INFO, "Got connect for %s" % repr(server))
        self.connect_pop(server)
        self.pop_wfile.write("USER %s\r\n" % username)
        resp = self.pop_rfile.readline()
        # As long the server responds OK, just swallow this reponse.
        if resp.startswith("+OK"):
            return True
        else:
            return False

    def connect_pop(self, pop_server):
        # connect to the pop server
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(pop_server)
        self.pop_rfile = LogWrapper(self.server.log, s.makefile("rb"))
        # the write side should be unbuffered
        self.pop_wfile = LogWrapper(self.server.log, s.makefile("wb", 0))

    def close_pop(self):
        self.pop_rfile.close()
        self.pop_wfile.close()

    def handle(self):
        zLOG.LOG("POP3", zLOG.INFO,
                 "Connection from %s" % repr(self.client_address))
        self.server.zodb.sync()
        self.sess_retr_count = 0
        self.wfile.write("+OK pspam/pop %s\r\n" % VERSION)
        # First read the USER command to get the real server's name
        if not self.read_user():
            zLOG.LOG("POP3", zLOG.INFO, "Did not get valid USER")
            return
        try:
            self.handle_pop()
        finally:
            self.close_pop()
            if self.sess_retr_count == 1:
                ending = ""
            else:
                ending = "s"
            zLOG.LOG("POP3", zLOG.INFO,
                     "Ending session (%d message%s retrieved)"
                     % (self.sess_retr_count, ending))

    _multiline = {"RETR": True, "TOP": True,}
    _multiline_noargs = {"LIST": True, "UIDL": True,}

    def is_multiline(self, command, args):
        if command in self._multiline:
            return True
        if command in self._multiline_noargs and not args:
            return True
        return False

    def parse_request(self, req):
        parts = req.split()
        req = parts[0]
        args = tuple(parts[1:])
        return req, args

    def handle_pop(self):
        # send the initial server hello
        hello = self.pop_rfile.readline()
        self.wfile.write(hello)

        # now get client requests and return server responses
        while 1:
            line = self.rfile.readline()
            if line == '':
                break
            self.pop_wfile.write(line)
            if not self.handle_pop_response(line):
                break

    def handle_pop_response(self, req):
        # Return True if connection is still open
        cmd, args = self.parse_request(req)
        multiline = self.is_multiline(cmd, args)
        firstline = self.pop_rfile.readline()
        zLOG.LOG("POP3", zLOG.DEBUG, "command %s multiline %s resp %s"
                 % (cmd, multiline, firstline.strip()))
        if multiline:
            # Collect the entire response as one string
            resp = StringIO.StringIO()
            while 1:
                line = self.pop_rfile.readline()
                resp.write(line)
                # The response is finished if we get . or an error.
                # XXX should handle byte-stuffed response
                if line == ".\r\n":
                    break
                if line.startswith("-ERR"):
                    break
            buf = resp.getvalue()
        else:
            buf = None

        handler = getattr(self, "handle_%s" % cmd, None)
        if handler:
            firstline, buf = handler(cmd, args, firstline, buf)

        self.wfile.write(firstline)
        if buf is not None:
            self.wfile.write(buf)
        if cmd == "QUIT":
            return False
        else:
            return True

    def handle_RETR(self, cmd, args, firstline, resp):
        if not resp:
            return firstline, resp
        try:
            msg = email.message_from_string(resp)
        except email.Errors.MessageParseError, err:
            zLOG.LOG("POP3", zLOG.WARNING,
                     "Failed to parse msg: %s" % err, error=sys.exc_info())
            resp = self.message_parse_error(resp)
        else:
            self.score_msg(msg)
            resp = msg.as_string()

        self.sess_retr_count += 1
        return firstline, resp

    def handle_TOP(self, cmd, args, firstline, resp):
        # XXX Just handle TOP like RETR?
        return self.handle_RETR(cmd, args, firstline, resp)

    rx_STAT = re.compile("\+OK (\d+) (\d+)(.*)", re.DOTALL)

    def handle_STAT(self, cmd, args, firstline, resp):
        # STAT returns the number of messages and the total size.  The
        # proxy must add the size of new headers to the total size.
        # Example: +OK 3 340
        mo = self.rx_STAT.match(firstline)
        if mo is None:
            return firstline, resp
        count, size, extra = mo.group(1, 2, 3)
        count = int(count)
        size = int(size)
        size += count * HEADER_SIZE
        firstline = "+OK %d %d%s" % (count, size, extra)
        return firstline, resp

    rx_LIST = re.compile("\+OK (\d+) (\d+)(.*)", re.DOTALL)
    rx_LIST_2 = re.compile("(\d+) (\d+)(.*)", re.DOTALL)

    def handle_LIST(self, cmd, args, firstline, resp):
        # If there are no args, LIST returns size info for each message.
        # If there is an arg, LIST return number and size for one message.
        mo = self.rx_LIST.match(firstline)
        if mo:
            # a single-line response
            n, size, extra = mo.group(1, 2, 3)
            size = int(size) + HEADER_SIZE
            firstline = "+OK %s %d%s" % (n, size, extra)
            return firstline, resp
        else:
            # possibility a multiline response
            if not firstline.startswith("+OK"):
                return firstline, resp
            # update each line of the response
            L = []
            for line in resp.split("\r\n"):
                if not line:
                    continue
                mo = self.rx_LIST_2.match(line)
                if not mo:
                    L.append(line)
                else:
                    n, size, extra = mo.group(1, 2, 3)
                    size = int(size) + HEADER_SIZE
                    L.append("%s %d%s" % (n, size, extra))
            return firstline, "\r\n".join(L)

    def message_parse_error(self, buf):
        # We get an error parsing the message.  We've already told the
        # client to expect more bytes that this buffer contains, but
        # there's not clean way to add the header.

        self.server.log.write("# error: %s\n" % repr(buf))

        # XXX what to do?  list's just add it after the first line
        score = self.server.classifier.spamprob(tokenize(buf))

        L = buf.split("\n")
        L.insert(1, HEADER % score)
        return "\n".join(L)

    def score_msg(self, msg):
        score = self.server.classifier.spamprob(tokenize(msg))
        msg.add_header("X-Spambayes", "%5.3f" % score)

def main():
    db = pspam.database.open()
    conn = db.open()
    r = conn.root()
    profile = r["profile"]

    log = open("pop.log", "ab")
    print >> log, "+PROXY start", time.ctime()

    server = POP3ProxyServer(('', int(options["pop3proxy",
                                              "listen_ports"][0])),
                             POP3RequestHandler,
                             profile.classifier,
                             log,
                             conn,
                             )
    server.serve_forever()

if __name__ == "__main__":
    main()
