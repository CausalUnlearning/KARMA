#!/usr/bin/env python

"""POP3DND - provides drag'n'drop training ability for POP3 clients.

This application is a twisted cross between a POP3 proxy and an IMAP
server.  It sits between your mail client and your POP3 server (like any
other POP3 proxy).  While messages classified as ham are simply passed
through the proxy, messages that are classified as spam or unsure are
intercepted and passed to the IMAP server.  The IMAP server offers four
folders - one where messages classified as spam end up, one for messages
it is unsure about, one for training ham, and one for training spam.

In other words, to use this application, setup your mail client to connect
to localhost, rather than directly to your POP3 server.  Additionally, add
a new IMAP account, also connecting to localhost.  Setup the application
via the web interface, and you are ready to go.  Good messages will appear
as per normal, but you will also have two new incoming folders, one for
spam and one for unsure messages.

To train SpamBayes, use the 'train_as_spam' and 'train_as_ham' folders.
Any messages in these folders will be trained appropriately.

This SpamBayes application is designed to work with Outlook Express, and
provide the same sort of ease of use as the Outlook plugin.  Although the
majority of development and testing has been done with Outlook Express,
Eudora and Thunderbird, any mail client that supports both IMAP and POP3
should be able to use this application - if the client enables the user to
work with an IMAP account and POP3 account side-by-side (and move messages
between them), then it should work equally as well.
"""

from __future__ import generators

todo = """
 o The RECENT flag should be unset at some point, but when?  The
   RFC says that a message is recent if this is the first session
   to be notified about the message.  Perhaps this can be done
   simply by *not* persisting this flag - i.e. the flag is always
   loaded as not recent, and only new messages are recent.  The
   RFC says that if it is not possible to determine, then all
   messages should be recent, and this is what we currently do.
 o The Mailbox should be calling the appropriate listener
   functions (currently only newMessages is called on addMessage).
   flagsChanged should also be called on store, addMessage, or ???
 o We cannot currently get part of a message via the BODY calls
   (with the <> operands), or get a part of a MIME message (by
   prepending a number).  This should be added!
 o Suggestions?
"""

# This module is part of the spambayes project, which is Copyright 2002-2007
# The Python Software Foundation and is covered by the Python Software
# Foundation license.

__author__ = "Tony Meyer <ta-meyer@ihug.co.nz>"
__credits__ = "All the Spambayes folk."

import os
import re
import sys
import time
import errno
import email
import thread
import getopt
import socket
import imaplib
import email.Utils

import cStringIO as StringIO

from twisted import cred
import twisted.application.app
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.protocol import ServerFactory
from twisted.protocols.imap4 import IMessage
from twisted.protocols.imap4 import IAccount
from twisted.protocols.imap4 import MessageSet
from twisted.protocols.imap4 import IMAP4Server, MemoryAccount, IMailbox
from twisted.protocols.imap4 import IMailboxListener

from spambayes import storage
from spambayes import message
from spambayes.Stats import Stats
from spambayes.Options import options
from spambayes.tokenizer import tokenize
from spambayes import FileCorpus, Dibbler
from spambayes.Version import get_current_version
from sb_server import POP3ProxyBase, State, _addressPortStr
from spambayes.port import md5

def ensureDir(dirname):
    """Ensure that the given directory exists - in other words, if it
    does not exist, attempt to create it."""
    try:
        os.mkdir(dirname)
        if options["globals", "verbose"]:
            print "Creating directory", dirname
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise


class IMAPMessage(message.Message):
    '''IMAP Message base class.'''
    __implements__ = (IMessage,)

    def __init__(self, date=None, message_db=None):
        message.Message.__init__(self, message_info_db=message_db)
        # We want to persist more information than the generic
        # Message class.
        self.stored_attributes.extend(["date", "deleted", "flagged",
                                       "seen", "draft", "recent",
                                       "answered"])
        self.date = date
        self.clear_flags()

    # IMessage implementation
    def getHeaders(self, negate, *names):
        """Retrieve a group of message headers."""
        headers = {}
        for header, value in self.items():
            if (header.upper() in names and not negate) or \
               (header.upper() not in names and negate) or names == ():
                headers[header.lower()] = value
        return headers

    def getFlags(self):
        """Retrieve the flags associated with this message."""
        return self._flags_iter()

    def _flags_iter(self):
        if self.deleted:
            yield "\\DELETED"
        if self.answered:
            yield "\\ANSWERED"
        if self.flagged:
            yield "\\FLAGGED"
        if self.seen:
            yield "\\SEEN"
        if self.draft:
            yield "\\DRAFT"
        if self.recent:
            yield "\\RECENT"

    def getInternalDate(self):
        """Retrieve the date internally associated with this message."""
        assert self.date is not None, \
               "Must set date to use IMAPMessage instance."
        return self.date

    def getBodyFile(self):
        """Retrieve a file object containing the body of this message."""
        # Note: only body, not headers!
        s = StringIO.StringIO()
        s.write(self.body())
        s.seek(0)
        return s

    def getSize(self):
        """Retrieve the total size, in octets, of this message."""
        return len(self.as_string())

    def getUID(self):
        """Retrieve the unique identifier associated with this message."""
        return self.id

    def isMultipart(self):
        """Indicate whether this message has subparts."""
        return False

    def getSubPart(self, part):
        """Retrieve a MIME sub-message

        @type part: C{int}
        @param part: The number of the part to retrieve, indexed from 0.

        @rtype: Any object implementing C{IMessage}.
        @return: The specified sub-part.
        """
        raise NotImplementedError

    # IMessage implementation ends

    def clear_flags(self):
        """Set all message flags to false."""
        self.deleted = False
        self.answered = False
        self.flagged = False
        self.seen = False
        self.draft = False
        self.recent = False

    def set_flag(self, flag, value):
        # invalid flags are ignored
        flag = flag.upper()
        if flag == "\\DELETED":
            self.deleted = value
        elif flag == "\\ANSWERED":
            self.answered = value
        elif flag == "\\FLAGGED":
            self.flagged = value
        elif flag == "\\SEEN":
            self.seen = value
        elif flag == "\\DRAFT":
            self.draft = value
        else:
            print "Tried to set invalid flag", flag, "to", value

    def flags(self):
        """Return the message flags."""
        return list(self._flags_iter())

    def train(self, classifier, isSpam):
        if self.GetTrained() == (not isSpam):
            classifier.unlearn(self.tokenize(), not isSpam)
            self.RememberTrained(None)
        if self.GetTrained() is None:
            classifier.learn(self.tokenize(), isSpam)
            self.RememberTrained(isSpam)
        classifier.store()

    def structure(self, ext=False):
        """Body structure data describes the MIME-IMB
        format of a message and consists of a sequence of mime type, mime
        subtype, parameters, content id, description, encoding, and size.
        The fields following the size field are variable: if the mime
        type/subtype is message/rfc822, the contained message's envelope
        information, body structure data, and number of lines of text; if
        the mime type is text, the number of lines of text.  Extension fields
        may also be included; if present, they are: the MD5 hash of the body,
        body disposition, body language."""
        s = []
        for part in self.walk():
            if part.get_content_charset() is not None:
                charset = ("charset", part.get_content_charset())
            else:
                charset = None
            part_s = [part.get_main_type(), part.get_subtype(),
                      charset,
                      part.get('Content-Id'),
                      part.get('Content-Description'),
                      part.get('Content-Transfer-Encoding'),
                      str(len(part.as_string()))]
            #if part.get_type() == "message/rfc822":
            #    part_s.extend([envelope, body_structure_data,
            #                  part.as_string().count("\n")])
            #elif part.get_main_type() == "text":
            if part.get_main_type() == "text":
                part_s.append(str(part.as_string().count("\n")))
            if ext:
                part_s.extend([md5(part.as_string()).digest(),
                               part.get('Content-Disposition'),
                               part.get('Content-Language')])
            s.append(part_s)
        if len(s) == 1:
            return s[0]
        return s

    def body(self):
        rfc822 = self.as_string()
        bodyRE = re.compile(r"\r?\n(\r?\n)(.*)",
                            re.DOTALL + re.MULTILINE)
        bmatch = bodyRE.search(rfc822)
        return bmatch.group(2)

    def headers(self):
        rfc822 = self.as_string()
        bodyRE = re.compile(r"\r?\n(\r?\n)(.*)",
                            re.DOTALL + re.MULTILINE)
        bmatch = bodyRE.search(rfc822)
        return rfc822[:bmatch.start(2)]


class DynamicIMAPMessage(IMAPMessage):
    """An IMAP Message that may change each time it is loaded."""
    def __init__(self, func, mdb):
        date = imaplib.Time2Internaldate(time.time())[1:-1]
        IMAPMessage.__init__(self, date, mdb)
        self.func = func
        self.load()
    def load(self):
        # This only works for simple messages (non multi-part).
        self.set_payload(self.func(body=True))
        # This only works for simple headers (no continuations).
        for headerstr in self.func(headers=True).split('\r\n'):
            header, value = headerstr.split(':')
            self[header] = value.strip()


class IMAPFileMessage(IMAPMessage, FileCorpus.FileMessage):
    '''IMAP Message that persists as a file system artifact.'''

    def __init__(self, file_name=None, directory=None, mdb=None):
        """Constructor(message file name, corpus directory name)."""
        date = imaplib.Time2Internaldate(time.time())[1:-1]
        IMAPMessage.__init__(self, date, mdb)
        FileCorpus.FileMessage.__init__(self, file_name, directory)
        self.id = file_name


class IMAPFileMessageFactory(FileCorpus.FileMessageFactory):
    '''MessageFactory for IMAPFileMessage objects'''
    def create(self, key, directory, content=None):
        '''Create a message object from a filename in a directory'''
        if content is None:
            return IMAPFileMessage(key, directory)
        msg = email.message_from_string(content, _class=IMAPFileMessage)
        msg.id = key
        msg.file_name = key
        msg.directory = directory
        return msg


class IMAPMailbox(cred.perspective.Perspective):
    __implements__ = (IMailbox,)

    def __init__(self, name, identity_name, id):
        cred.perspective.Perspective.__init__(self, name, identity_name)
        self.UID_validity = id
        self.listeners = []

    def getUIDValidity(self):
        """Return the unique validity identifier for this mailbox."""
        return self.UID_validity

    def addListener(self, listener):
        """Add a mailbox change listener."""
        self.listeners.append(listener)

    def removeListener(self, listener):
        """Remove a mailbox change listener."""
        self.listeners.remove(listener)


class SpambayesMailbox(IMAPMailbox):
    def __init__(self, name, id, directory):
        IMAPMailbox.__init__(self, name, "spambayes", id)
        self.UID_validity = id
        ensureDir(directory)
        self.storage = FileCorpus.FileCorpus(IMAPFileMessageFactory(),
                                             directory, r"[0123456789]*")
        # UIDs are required to be strictly ascending.
        if len(self.storage.keys()) == 0:
            self.nextUID = 1
        else:
            self.nextUID = long(self.storage.keys()[-1]) + 1
        # Calculate initial recent and unseen counts
        self.unseen_count = 0
        self.recent_count = 0
        for msg in self.storage:
            if not msg.seen:
                self.unseen_count += 1
            if msg.recent:
                self.recent_count += 1

    def getUIDNext(self, increase=False):
        """Return the likely UID for the next message added to this
        mailbox."""
        reply = str(self.nextUID)
        if increase:
            self.nextUID += 1
        return reply

    def getUID(self, msg):
        """Return the UID of a message in the mailbox."""
        # Note that IMAP messages are 1-based, our messages are 0-based.
        d = self.storage
        return long(d.keys()[msg - 1])

    def getFlags(self):
        """Return the flags defined in this mailbox."""
        return ["\\Answered", "\\Flagged", "\\Deleted", "\\Seen",
                "\\Draft"]

    def getMessageCount(self):
        """Return the number of messages in this mailbox."""
        return len(self.storage.keys())

    def getRecentCount(self):
        """Return the number of messages with the 'Recent' flag."""
        return self.recent_count

    def getUnseenCount(self):
        """Return the number of messages with the 'Unseen' flag."""
        return self.unseen_count

    def isWriteable(self):
        """Get the read/write status of the mailbox."""
        return True

    def destroy(self):
        """Called before this mailbox is deleted, permanently."""
        # Our mailboxes cannot be deleted
        raise NotImplementedError

    def getHierarchicalDelimiter(self):
        """Get the character which delimits namespaces for in this
        mailbox."""
        return '.'

    def requestStatus(self, names):
        """Return status information about this mailbox."""
        answer = {}
        for request in names:
            request = request.upper()
            if request == "MESSAGES":
                answer[request] = self.getMessageCount()
            elif request == "RECENT":
                answer[request] = self.getRecentCount()
            elif request == "UIDNEXT":
                answer[request] = self.getUIDNext()
            elif request == "UIDVALIDITY":
                answer[request] = self.getUIDValidity()
            elif request == "UNSEEN":
                answer[request] = self.getUnseenCount()
        return answer

    def addMessage(self, content, flags=(), date=None):
        """Add the given message to this mailbox."""
        msg = self.storage.makeMessage(self.getUIDNext(True),
                                       content.read())
        msg.date = date
        self.storage.addMessage(msg)
        self.store(MessageSet(long(msg.id), long(msg.id)), flags, 1, True)
        msg.recent = True
        msg.store()
        self.recent_count += 1
        self.unseen_count += 1

        for listener in self.listeners:
            listener.newMessages(self.getMessageCount(),
                                 self.getRecentCount())
        d = defer.Deferred()
        reactor.callLater(0, d.callback, self.storage.keys().index(msg.id))
        return d

    def expunge(self):
        """Remove all messages flagged \\Deleted."""
        deleted_messages = []
        for msg in self.storage:
            if msg.deleted:
                if not msg.seen:
                    self.unseen_count -= 1
                if msg.recent:
                    self.recent_count -= 1
                deleted_messages.append(long(msg.id))
                self.storage.removeMessage(msg)
        if deleted_messages != []:
            for listener in self.listeners:
                listener.newMessages(self.getMessageCount(),
                                     self.getRecentCount())
        return deleted_messages

    def search(self, query, uid):
        """Search for messages that meet the given query criteria.

        @type query: C{list}
        @param query: The search criteria

        @rtype: C{list}
        @return: A list of message sequence numbers or message UIDs which
        match the search criteria.
        """
        if self.getMessageCount() == 0:
            return []
        all_msgs = MessageSet(long(self.storage.keys()[0]),
                              long(self.storage.keys()[-1]))
        matches = []
        for id, msg in self._messagesIter(all_msgs, uid):
            for q in query:
                if msg.matches(q):
                    matches.append(id)
                    break
        return matches

    def _messagesIter(self, messages, uid):
        if uid:
            if not self.storage.keys():
                return
            messages.last = long(self.storage.keys()[-1])
        else:
            messages.last = self.getMessageCount()
        for id in messages:
            if uid:
                msg = self.storage.get(str(id))
            else:
                msg = self.storage.get(str(self.getUID(id)))
            if msg is None:
                # Non-existant message.
                continue
            # Load the message, if necessary
            if hasattr(msg, "load"):
                msg.load()
            yield (id, msg)

    def fetch(self, messages, uid):
        """Retrieve one or more messages."""
        return self._messagesIter(messages, uid)

    def store(self, messages, flags, mode, uid):
        """Set the flags of one or more messages."""
        stored_messages = {}
        for id, msg in self._messagesIter(messages, uid):
            if mode == 0:
                msg.clear_flags()
                value = True
            elif mode == -1:
                value = False
            elif mode == 1:
                value = True
            for flag in flags or (): # flags might be None
                if flag == '(' or flag == ')':
                    continue
                if flag == "SEEN" and value == True and msg.seen == False:
                    self.unseen_count -= 1
                if flag == "SEEN" and value == False and msg.seen == True:
                    self.unseen_count += 1
                msg.set_flag(flag, value)
            stored_messages[id] = msg.flags()
        return stored_messages


class SpambayesInbox(SpambayesMailbox):
    """A special mailbox that holds status messages from SpamBayes."""
    def __init__(self, id, state):
        SpambayesMailbox.__init__(self, "INBOX", "spambayes", id)
        self.mdb = state.mdb
        self.UID_validity = id
        self.nextUID = 1
        self.unseen_count = 0
        self.recent_count = 0
        self.storage = {}
        self.createMessages()
        self.stats = state.stats

    def buildStatusMessage(self, body=False, headers=False):
        """Build a message containing the current status message.

        If body is True, then return the body; if headers is True
        return the headers.  If both are true, then return both
        (and insert a newline between them).
        """
        msg = []
        if headers:
            msg.append("Subject: SpamBayes Status")
            msg.append('From: "SpamBayes" <no-reply@spambayes.invalid>')
            if body:
                msg.append('\r\n')
        if body:
            state.buildStatusStrings()
            msg.append("POP3 proxy running on %s, proxying to %s." % \
                       (state.proxyPortsString, state.serversString))
            msg.append("Active POP3 conversations: %s." % \
                       (state.activeSessions,))
            msg.append("POP3 conversations this session: %s." % \
                       (state.totalSessions,))
            msg.append("IMAP server running on %s." % \
                       (state.serverPortString,))
            msg.append("Active IMAP4 conversations: %s." % \
                       (state.activeIMAPSessions,))
            msg.append("IMAP4 conversations this session: %s." % \
                       (state.totalIMAPSessions,))
            msg.append("Emails classified this session: %s spam, %s ham, "
                       "%s unsure." % (state.numSpams, state.numHams,
                                       state.numUnsure))
            msg.append("Total emails trained: Spam: %s Ham: %s" % \
                       (state.bayes.nspam, state.bayes.nham))
            msg.append(state.warning or "SpamBayes is operating correctly.\r\n")
        return "\r\n".join(msg)

    def buildStatisticsMessage(self, body=False, headers=False):
        """Build a mesasge containing the current statistics.

        If body is True, then return the body; if headers is True
        return the headers.  If both are true, then return both
        (and insert a newline between them).
        """
        msg = []
        if headers:
            msg.append("Subject: SpamBayes Statistics")
            msg.append('From: "SpamBayes" <no-reply@spambayes.invalid')
            if body:
                msg.append('\r\n')
        if body:
            msg.extend(self.stats.GetStats(use_html=False))
        return "\r\n".join(msg)

    def createMessages(self):
        """Create the special messages that live in this mailbox."""
        state.buildStatusStrings()
        state.buildServerStrings()
        about = 'Subject: About SpamBayes / POP3DND\r\n' \
                 'From: "SpamBayes" <no-reply@spambayes.invalid>\r\n\r\n' \
                 '%s\r\nSee <http://spambayes.org>.\r\n' % (__doc__,)
        date = imaplib.Time2Internaldate(time.time())[1:-1]
        msg = email.message_from_string(about, _class=IMAPMessage)
        msg.date = date
        self.addMessage(msg)
        msg = DynamicIMAPMessage(self.buildStatusMessage, self.mdb)
        self.addMessage(msg)
        msg = DynamicIMAPMessage(self.buildStatisticsMessage, self.mdb)
        self.addMessage(msg)
        # XXX Add other messages here, for example
        # XXX help and other documentation.

    def isWriteable(self):
        """Get the read/write status of the mailbox."""
        return False

    def addMessage(self, msg, flags=(), date=None):
        """Add the given message to this mailbox."""
        msg.id = self.getUIDNext(True)
        self.storage[msg.id] = msg
        d = defer.Deferred()
        reactor.callLater(0, d.callback, self.storage.keys().index(msg.id))
        return d

    def expunge(self):
        """Remove all messages flagged \\Deleted."""
        # Mailbox is read-only.
        return []

    def store(self, messages, flags, mode, uid):
        """Set the flags of one or more messages."""
        # Mailbox is read-only.
        return {}


class Trainer(object):
    """Listens to a given mailbox and trains new messages as spam or
    ham."""
    __implements__ = (IMailboxListener,)

    def __init__(self, mailbox, asSpam):
        self.mailbox = mailbox
        self.asSpam = asSpam

    def modeChanged(self, writeable):
        # We don't care
        pass

    def flagsChanged(self, newFlags):
        # We don't care
        pass

    def newMessages(self, exists, recent):
        # We don't get passed the actual message, or the id of
        # the message, or even the message number.  We just get
        # the total number of new/recent messages.
        # However, this function should be called _every_ time
        # that a new message appears, so we should be able to
        # assume that the last message is the new one.
        # (We ignore the recent count)
        if exists is not None:
            id = self.mailbox.getUID(exists)
            msg = self.mailbox.storage[str(id)]
            msg.train(state.bayes, self.asSpam)


class SpambayesAccount(MemoryAccount):
    """Account for Spambayes server."""

    def __init__(self, id, ham, spam, unsure, train_spam, inbox):
        MemoryAccount.__init__(self, id)
        self.mailboxes = {"SPAM" : spam,
                          "UNSURE" : unsure,
                          "TRAIN_AS_HAM" : ham,
                          "TRAIN_AS_SPAM" : train_spam,
                          "INBOX" : inbox}

    def select(self, name, readwrite=1):
        # 'INBOX' is a special case-insensitive name meaning the
        # primary mailbox for the user; for our purposes this contains
        # special messages from SpamBayes.
        return MemoryAccount.select(self, name, readwrite)


class SpambayesIMAPServer(IMAP4Server):
    IDENT = "Spambayes IMAP Server IMAP4rev1 Ready"

    def __init__(self, user_account):
        IMAP4Server.__init__(self)
        self.account = user_account

    def authenticateLogin(self, user, passwd):
        """Lookup the account associated with the given parameters."""
        if user == options["imapserver", "username"] and \
           passwd == options["imapserver", "password"]:
            return (IAccount, self.account, None)
        raise cred.error.UnauthorizedLogin()

    def connectionMade(self):
        state.activeIMAPSessions += 1
        state.totalIMAPSessions += 1
        IMAP4Server.connectionMade(self)

    def connectionLost(self, reason):
        state.activeIMAPSessions -= 1
        IMAP4Server.connectionLost(self, reason)

    def do_CREATE(self, tag, args):
        """Creating new folders on the server is not permitted."""
        self.sendNegativeResponse(tag, \
                                  "Creation of new folders is not permitted")
    auth_CREATE = (do_CREATE, IMAP4Server.arg_astring)
    select_CREATE = auth_CREATE

    def do_DELETE(self, tag, args):
        """Deleting folders on the server is not permitted."""
        self.sendNegativeResponse(tag, \
                                  "Deletion of folders is not permitted")
    auth_DELETE = (do_DELETE, IMAP4Server.arg_astring)
    select_DELETE = auth_DELETE


class OneParameterFactory(ServerFactory):
    """A factory that allows a single parameter to be passed to the created
    protocol."""
    def buildProtocol(self, addr):
        """Create an instance of a subclass of Protocol, passing a single
        parameter."""
        if self.parameter is not None:
            p = self.protocol(self.parameter)
        else:
            p = self.protocol()
        p.factory = self
        return p


class RedirectingBayesProxy(POP3ProxyBase):
    """Proxies between an email client and a POP3 server, redirecting
    mail to the imap server as necessary.  It acts on the following
    POP3 commands:

     o RETR:
        o Adds the judgement header based on the raw headers and body
          of the message.
    """

    # This message could be a bit more informative - it could at least
    # say whether it's the spam or unsure folder.  It could give
    # information about who the message was from, or what the subject
    # was, if people thought that would be a good idea.
    intercept_message = 'From: "Spambayes" <no-reply@spambayes.invalid>\r\n' \
                        'Subject: Spambayes Intercept\r\n\r\nA message ' \
                        'was intercepted by Spambayes (it scored %s).\r\n' \
                        '\r\nYou may find it in the Spam or Unsure ' \
                        'folder.\r\n\r\n'

    def __init__(self, clientSocket, serverName, serverPort, spam, unsure):
        POP3ProxyBase.__init__(self, clientSocket, serverName, serverPort)
        self.handlers = {'RETR': self.onRetr}
        state.totalSessions += 1
        state.activeSessions += 1
        self.isClosed = False
        self.spam_folder = spam
        self.unsure_folder = unsure

    def send(self, data):
        """Logs the data to the log file."""
        if options["globals", "verbose"]:
            state.logFile.write(data)
            state.logFile.flush()
        try:
            return POP3ProxyBase.send(self, data)
        except socket.error:
            self.close()

    def recv(self, size):
        """Logs the data to the log file."""
        data = POP3ProxyBase.recv(self, size)
        if options["globals", "verbose"]:
            state.logFile.write(data)
            state.logFile.flush()
        return data

    def close(self):
        # This can be called multiple times by async.
        if not self.isClosed:
            self.isClosed = True
            state.activeSessions -= 1
            POP3ProxyBase.close(self)

    def onTransaction(self, command, args, response):
        """Takes the raw request and response, and returns the
        (possibly processed) response to pass back to the email client.
        """
        handler = self.handlers.get(command, self.onUnknown)
        return handler(command, args, response)

    def onRetr(self, command, args, response):
        """Classifies the message.  If the result is ham, then simply
        pass it through.  If the result is an unsure or spam, move it
        to the appropriate IMAP folder."""
        # XXX This is all almost from sb_server!  We could just
        # XXX extract that out into a function and call it here.

        # Use '\n\r?\n' to detect the end of the headers in case of
        # broken emails that don't use the proper line separators.
        if re.search(r'\n\r?\n', response):
            # Remove the trailing .\r\n before passing to the email parser.
            # Thanks to Scott Schlesier for this fix.
            terminatingDotPresent = (response[-4:] == '\n.\r\n')
            if terminatingDotPresent:
                response = response[:-3]

            # Break off the first line, which will be '+OK'.
            ok, messageText = response.split('\n', 1)

            try:
                msg = email.message_from_string(messageText,
                                                _class=message.SBHeaderMessage)
                # Now find the spam disposition and add the header.
                (prob, clues) = state.bayes.spamprob(msg.tokenize(),
                                                     evidence=True)

                # Note that the X-SpamBayes-MailID header will be worthless
                # because we don't know the message id at this point.  It's
                # not necessary for anything anyway, so just don't set the
                # [Headers] add_unique_id option.
                msg.addSBHeaders(prob, clues)

                # Check for "RETR" or "TOP N 99999999" - fetchmail without
                # the 'fetchall' option uses the latter to retrieve messages.
                if (command == 'RETR' or
                    (command == 'TOP' and
                     len(args) == 2 and args[1] == '99999999')):
                    cls = msg.GetClassification()
                    dest_folder = None
                    if cls == options["Headers", "header_ham_string"]:
                        state.numHams += 1
                        headers = []
                        for name, value in msg.items():
                            header = "%s: %s" % (name, value)
                            headers.append(re.sub(r'\r?\n', '\r\n', header))
                        body = re.split(r'\n\r?\n', messageText, 1)[1]
                        messageText = "\r\n".join(headers) + "\r\n\r\n" + body
                    elif prob > options["Categorization", "spam_cutoff"]:
                        dest_folder = self.spam_folder
                        state.numSpams += 1
                    else:
                        dest_folder = self.unsure_folder
                        state.numUnsure += 1
                    if dest_folder:
                        msg = StringIO.StringIO(msg.as_string())
                        date = imaplib.Time2Internaldate(time.time())[1:-1]
                        dest_folder.addMessage(msg, (), date)

                        # We have to return something, because the client
                        # is expecting us to.  We return a short message
                        # indicating that a message was intercepted.
                        messageText = self.intercept_message % (prob,)
            except:
                messageText, details = \
                             message.insert_exception_header(messageText)

                # Print the exception and a traceback.
                print >> sys.stderr, details
            retval = ok + "\n" + messageText
            if terminatingDotPresent:
                retval += '.\r\n'
            return retval
        else:
            # Must be an error response.
            return response

    def onUnknown(self, command, args, response):
        """Default handler; returns the server's response verbatim."""
        return response


class RedirectingBayesProxyListener(Dibbler.Listener):
    """Listens for incoming email client connections and spins off
    RedirectingBayesProxy objects to serve them.
    """
    def __init__(self, serverName, serverPort, proxyPort, spam, unsure):
        proxyArgs = (serverName, serverPort, spam, unsure)
        Dibbler.Listener.__init__(self, proxyPort, RedirectingBayesProxy,
                                  proxyArgs)
        print 'Listener on port %s is proxying %s:%d' % \
               (_addressPortStr(proxyPort), serverName, serverPort)


class IMAPState(State):
    def __init__(self):
        State.__init__(self)

        # Set up the extra statistics.
        self.totalIMAPSessions = 0
        self.activeIMAPSessions = 0

    def createWorkers(self):
        """There aren't many workers in an IMAP State - most of the
        work is done elsewhere.  We do need to load the classifier,
        though, and build the status strings."""
        # Load token and message databases.
        if not hasattr(self, "DBName"):
            self.DBName, self.useDB = storage.database_type([])
        self.bayes = storage.open_storage(self.DBName, self.useDB)
        if not hasattr(self, "MBDName"):
            self.MDBName, self.useMDB = message.database_type()
        self.mdb = message.open_storage(self.MDBName, self.useMDB)

        # Load stats manager.
        self.stats = Stats(options, self.mdb)

        # Build status strings.
        self.buildStatusStrings()

    def buildServerStrings(self):
        """After the server details have been set up, this creates string
        versions of the details, for display in the Status panel."""
        self.serverPortString = str(self.imap_port)
        # Also build proxy strings
        State.buildServerStrings(self)

state = IMAPState()

# ===================================================================
# __main__ driver.
# ===================================================================

def prepare():
    # Setup state, server, boxes, trainers and account.
    state.imap_port = options["imapserver", "port"]
    state.createWorkers()
    proxyListeners = []

    spam_box = SpambayesMailbox("Spam", 0,
                                options["Storage", "spam_cache"])
    unsure_box = SpambayesMailbox("Unsure", 1,
                                  options["Storage", "unknown_cache"])
    ham_train_box = SpambayesMailbox("TrainAsHam", 2,
                                     options["Storage", "ham_cache"])
    # We don't have a third cache location in the directory, so make one up.
    spam_train_cache = os.path.join(options["Storage", "ham_cache"], "..",
                                    "spam_to_train")
    spam_train_box = SpambayesMailbox("TrainAsSpam", 3, spam_train_cache)
    inbox = SpambayesInbox(4, state)

    spam_trainer = Trainer(spam_train_box, True)
    ham_trainer = Trainer(ham_train_box, False)
    spam_train_box.addListener(spam_trainer)
    ham_train_box.addListener(ham_trainer)

    user_account = SpambayesAccount(options["imapserver", "username"],
                                    ham_train_box, spam_box, unsure_box,
                                    spam_train_box, inbox)

    # Add IMAP4 server.
    f = OneParameterFactory()
    f.protocol = SpambayesIMAPServer
    f.parameter = user_account
    reactor.listenTCP(state.imap_port, f)

    # Add POP3 proxy.
    for (server, serverPort), proxyPort in zip(state.servers,
                                               state.proxyPorts):
        listener = RedirectingBayesProxyListener(server, serverPort,
                                                 proxyPort, spam_box,
                                                 unsure_box)
        proxyListeners.append(listener)
    state.prepare()

def start():
    assert state.prepared, "Must prepare before starting"
    # The asyncore stuff doesn't play nicely with twisted (or vice-versa),
    # so put them in separate threads.
    thread.start_new_thread(Dibbler.run, ())
    reactor.run()

def stop():
    # Save the classifier, although that should not be necessary.
    state.bayes.store()
    # Explicitly closing the db is a good idea, though.
    state.bayes.close()
    
    # Stop the POP3 proxy.
    if state.proxyPorts:
        killer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            killer.connect(('localhost', state.proxyPorts[0][1]))
            killer.send('KILL\r\n')
            killer.close()
        except socket.error:
            # Well, we did our best to shut down gracefully.  Warn the user
            # and just die when the thread we are in does.
            print "Could not shut down POP3 proxy gracefully."
    # Stop the IMAP4 server.
    reactor.stop()

def run():
    # Read the arguments.
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'ho:')
    except getopt.error, msg:
        print >> sys.stderr, str(msg) + '\n\n' + __doc__
        sys.exit()

    for opt, arg in opts:
        if opt == '-h':
            print >> sys.stderr, __doc__
            sys.exit()
        elif opt == '-o':
            options.set_from_cmdline(arg, sys.stderr)

    # Let the user know what they are using...
    v = get_current_version()
    print v.get_long_version()
    from twisted.copyright import version as twisted_version
    print "Twisted version %s.\n" % (twisted_version,)

    # Setup everything.
    prepare()

    # Kick things off.
    start()


if __name__ == "__main__":
    run()
