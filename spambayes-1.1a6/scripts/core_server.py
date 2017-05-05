#!/usr/bin/env python

"""The primary server for SpamBayes.

Currently serves the web interface only.  Plugging in listeners for various
protocols is TBD.  This is a first cut at creating a standalone server which
uses a plugin architecture to support different protocols.  The primary
motivation is that web apps like MoinMoin, Trac and Roundup can use spam
detection, but they don't necessarily provide the mechanisms necessary to
save ham and spam databases for retraining.  By providing protocol plugins
you should be able to fairly easily provide (for example) an XML-RPC
interface web apps can use.  The core server takes care of all the training
bells and whistles.

Usage:

    core_server.py [options]

        options:
            -h      : Displays this help message.
            -P module :
                      Identify plugin module to use (required)
            -d FILE : use the named DBM database file
            -p FILE : the the named Pickle database file
            -u port : User interface listens on this port number
                      (default 8880; Browse http://localhost:8880/)
            -b      : Launch a web browser showing the user interface.

            -o section:option:value :
                      set [section, option] in the options database
                      to value

        All command line arguments and switches take their default
        values from the [html_ui] section of bayescustomize.ini.
"""

# This module is part of the spambayes project, which is Copyright 2002-2007
# The Python Software Foundation and is covered by the Python Software
# Foundation license.

__author__ = "Richie Hindle <richie@entrian.com>"
__credits__ = "Tim Peters, Neale Pickett, Tim Stone, all the Spambayes folk."

_TODO = """

Protocol plugin interface:
 o Classifier for web apps (e.g. Trac, Roundup, Moin)
 o POP3?
 o NNTP?

Web training interface:

User interface improvements:

 o Once the pieces are on separate pages, make the paste box bigger.
 o Deployment: Windows executable?  atlaxwin and ctypes?  Or just
   webbrowser?
 o "Reload database" button.


New features:

 o Online manual.
 o Links to project homepage, mailing list, etc.
 o List of words with stats (it would have to be paged!) a la SpamSieve.


Info:

 o Slightly-wordy index page; intro paragraph for each page.
 o In both stats and training results, report nham and nspam.
 o "Links" section (on homepage?) to project homepage, mailing list,
   etc.


Gimmicks:

 o Graphs.  Of something.  Who cares what?
"""

import sys, getopt

from spambayes import Dibbler
from spambayes.Options import options, _
from spambayes.UserInterface import UserInterfaceServer
from spambayes.Version import get_current_version
from spambayes.CoreUI import CoreUserInterface, CoreState, \
     AlreadyRunningException


# Increase the stack size on MacOS X.  Stolen from Lib/test/regrtest.py
if sys.platform == 'darwin':
    try:
        import resource
    except ImportError:
        pass
    else:
        soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
        newsoft = min(hard, max(soft, 1024*2048))
        resource.setrlimit(resource.RLIMIT_STACK, (newsoft, hard))

# Option-parsing helper functions
def _addressAndPort(s):
    """Decode a string representing a port to bind to, with optional address."""
    s = s.strip()
    if ':' in s:
        addr, port = s.split(':')
        return addr, int(port)
    else:
        return '', int(s)

def _addressPortStr((addr, port)):
    """Encode a string representing a port to bind to, with optional address."""
    if not addr:
        return str(port)
    else:
        return '%s:%d' % (addr, port)

def load_plugin(name, state):
    try:
        plugin_module = __import__(name)
    except ImportError:
        plugin_module = __import__("spambayes.%s" % name)
        plugin_module = getattr(plugin_module, name)
    plugin = plugin_module.register()
    plugin.state = state
    return plugin

def main(state):
    """Runs the core server forever or until a 'KILL' command is received or
    someone hits Ctrl+Break."""
    http_server = UserInterfaceServer(state.ui_port)
    http_server.register(CoreUserInterface(state))
    Dibbler.run(launchBrowser=state.launch_ui)

# ===================================================================
# __main__ driver.
# ===================================================================

def run():
    # Read the arguments.
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hbd:p:l:u:o:P:')
    except getopt.error, msg:
        print >> sys.stderr, str(msg) + '\n\n' + __doc__
        sys.exit()

    state = CoreState()
    state.plugin = None

    for opt, arg in opts:
        if opt == '-h':
            print >> sys.stderr, __doc__
            sys.exit()
        elif opt == '-b':
            state.launch_ui = True
        # '-p' and '-d' are handled by the storage.database_type call
        # below, in case you are wondering why they are missing.
        elif opt == '-l':
            state.proxyPorts = [_addressAndPort(a) for a in arg.split(',')]
        elif opt == '-u':
            state.ui_port = int(arg)
        elif opt == '-o':
            options.set_from_cmdline(arg, sys.stderr)
        elif opt == '-P':
            state.plugin = load_plugin(arg, state)

    if state.plugin is None:
        print >> sys.stderr, "No plugin argument (-P) was given."
        print >> sys.stderr, __doc__
        sys.exit()

    # Let the user know what they are using...
    v = get_current_version()
    print "%s\n" % (v.get_long_version("SpamBayes Core Proxy"),)

    if 0 <= len(args) <= 2:
        # Normal usage, with optional server name and port number.
        if len(args) == 1:
            state.servers = [(args[0], 110)]
        elif len(args) == 2:
            state.servers = [(args[0], int(args[1]))]

        try:
            state.prepare()
        except AlreadyRunningException:
            print  >> sys.stderr, \
                   "ERROR: The proxy is already running on this machine."
            print  >> sys.stderr, "Please stop the existing proxy and try again"
            return

        # kick everything off
        try:
            main(state)
        finally:
            state.close()

    else:
        print >> sys.stderr, __doc__

if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        print "bye!"
