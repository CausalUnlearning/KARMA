#! /usr/bin/env python

"""Convert configuration files

This script will convert configuration files to the new format.
It works by reading in the old configuration file and updating it -
this means that as soon as the Options module stops accepting the old
style input, this script will also stop working, and need to be replaced
with a new, much more complicated one.

By default, the script looks for a file called "bayescustomize.ini" in
the current working directory.  You may override this with the "-f" option.

The "-v" option produces verbose output, and "-h" produces this text.

For safety, a backup of the old configuration file is saved with a
".backup" suffix - note that if a file by this name already exists, this
does not occur.

Note that around options that change blank lines might move - there isn't
really an easy way around this, but it's easily fixed by hand, and if you
don't look at the config file, you'll never know <wink>.
"""

# This module is part of the spambayes project, which is Copyright 2002-2007
# The Python Software Foundation and is covered by the Python Software
# Foundation license.

__author__ = "Tony Meyer, <ta-meyer@ihug.co.nz>"
__credits__ = "All the Spambayes folk."

import getopt
import sys
import shutil
import os

# a bit of a hack to help those without spambayes on their
# Python path - stolen from timtest.py
sys.path.insert(-1, os.getcwd())
sys.path.insert(-1, os.path.dirname(os.getcwd()))

from spambayes import Options

def run():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'vhf:')
    except getopt.error, msg:
        print >> sys.stderr, str(msg) + '\n\n' + __doc__
        sys.exit()

    filename = "bayescustomize.ini"
    verbose = False

    for opt, arg in opts:
        if opt == '-h':
            print >>  sys.stderr, __doc__
            sys.exit()
        elif opt == '-f':
            filename = arg
        elif opt == '-v':
            verbose = True

    o = Options.OptionsClass()
    if verbose:
        print "Loading defaults"
    o.load_defaults()
    if verbose:
        print "Updating file:", filename
    if os.path.exists(filename):
        if verbose:
            print "Merging..."
        o.merge_file(filename)
    else:
        print filename, "does not exist; exiting."
        sys.exit(-1)
    backup_name = filename + ".backup"
    if not os.path.exists(backup_name):
        if verbose:
            print "Copying file", filename, "to", backup_name
        shutil.copyfile(filename, backup_name)
    if verbose:
        print "Updating..."
    o.update_file(filename)
    if verbose:
        print "Done."

if __name__ == '__main__':
    run()
