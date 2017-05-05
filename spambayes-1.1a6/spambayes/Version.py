#! /usr/bin/env python
"""Simple version repository for SpamBayes core, and our main apps.

Also has the ability to load this version information from a remote location
(in that case, we actually load a "ConfigParser" version of the file to
avoid importing code we can't trust.)  This allows any app to check if there
is a later version available.

The makefile process for the website will execute this as a script, which
will generate the "ConfigParser" version for the web.
"""

import sys
import re

try:
    _
except NameError:
    _ = lambda arg: arg

# See bug 806238: urllib2 fails in Outlook new-version chk.
# A reason for why the spambayes.org URL fails is given in a comment there.
#LATEST_VERSION_HOME="http://www.spambayes.org/download/Version.cfg"
# The SF URL instead works for Tim and xenogeist.
LATEST_VERSION_HOME = "http://spambayes.sourceforge.net/download/Version.cfg"
DEFAULT_DOWNLOAD_PAGE = "http://spambayes.sourceforge.net/windows.html"

# This module is part of the spambayes project, which is Copyright 2002-2007
# The Python Software Foundation and is covered by the Python Software
# Foundation license.

versions = {
    # Note this means we can change the download page later, and old
    # versions will still go to the new page.
    # We may also like to have a "Release Notes Page" item later?
    "Download Page": DEFAULT_DOWNLOAD_PAGE,

    # Sub-dict for generating sub-sections in the cfg file that are compatible
    # with the update checking in older versions of SpamBayes.
    "Apps": {
        "Outlook" : {
            "Description":      "SpamBayes Outlook Addin",
        },
        "POP3 Proxy" : {
            "Description":      "SpamBayes POP3 Proxy",
        },
    },
}

def get_version(app = None,
                version_dict = None):
    """Get SBVersion object based on the version info in the supplied dict."""
    ver = SBVersion()  # get default version
    if version_dict is not None:
        dict = version_dict  # default to top level dictionary
        if app is not None:
            # attempt to get a sub-dict for the specific app
            try:
                dict = version_dict["Apps"][app]
            except KeyError:
                pass
        try:
            version = dict["Version"]
            # KLUDGE: Perform some bizarre magic to try to figure out if we
            # have an old-format float version instead of a new-format string
            # and massage it into a string format that will compare properly
            # in update checks.
            try:
                float(version)
                # Version converted successfully to a float, which means it
                # may be an old-format version number.  Old convention was to
                # use 1.01 to represent "1.0.1", so check to see if there is
                # more than one digit following the decimal.
                dot = version.find('.')
                ver_frac_part = version[dot+1:]
                if len(ver_frac_part) > 1:
                    # Use the first digit of the fractional part as the minor
                    # version and the rest as the patch version.
                    version = version[0:dot] + '.' + ver_frac_part[0] + '.' + ver_frac_part[1:]
            except ValueError:
                pass
            ver = SBVersion(version, version_dict["Date"])
        except KeyError:
            pass
    return ver

def get_download_page(app = None,
                      version_dict = None):
    if version_dict is None:
        version_dict = versions
    dict = version_dict  # default to top level dictionary
    if app is not None:
        # attempt to get a sub-dict for the specific app
        try:
            dict = version_dict["Apps"][app]
        except KeyError:
            pass
    try:
        return dict["Download Page"]
    except KeyError:
        # "Download Page" key not found so it may be an old-format dictionary.
        # Just use the default download page.
        return DEFAULT_DOWNLOAD_PAGE

def get_current_version():
    return SBVersion()

#============================================================================

# The SBVersion class is a modified version of the StrictVersion class from
# the "distutils" module.  It has been adapted to handle an "rc" pre-release
# designation for release candidates, and to store the version data in the
# format of the sys.version_info tuple.  A date string may also be provided
# that will be included in the long format of the version string.  The
# default version and date info is read from the metadata in the "spambayes"
# module __init__.py file.

class SBVersion:

    """Version numbering for SpamBayes releases.
    A version number consists of two or three dot-separated numeric
    components, with an optional "pre-release" tag on the end.  The
    pre-release tag consists of the designations 'a' (for alpha),
    'b' (for beta), or 'rc' (for release candidate) followed by a number.
    If the numeric components of two version numbers are equal, then one
    with a pre-release tag will always be deemed earlier (lesser) than
    one without.

    The following are valid version numbers (shown in the order that
    would be obtained by sorting according to the supplied cmp function):

        0.4       0.4.0  (these two are equivalent)
        0.4.1
        0.5a1
        0.5b3
        0.5
        0.9.6
        1.0
        1.0.4a3
        1.0.4b1
        1.0.4rc2
        1.0.4

    The following are examples of invalid version numbers:

        1
        2.7.2.2
        1.3.a4
        1.3pl1
        1.3c4

    A date may also be associated with the version, typically to track the
    date when the release was made public.  The date is specified as a string,
    and is only used in formatting the long version of the version string.
    """

    def __init__(self, vstring=None, date=None):
        import spambayes
        if vstring:
            self.parse(vstring)
        else:
            self.parse(spambayes.__version__)
        if date:
            self.date = date
        else:
            self.date = spambayes.__date__

    def __repr__ (self):
        return "%s('%s', '%s')" % (self.__class__.__name__, str(self), self.date)

    version_re = re.compile(r'^(\d+) \. (\d+) (\. (\d+))? (([ab]|rc)(\d+))?\+?$',
                            re.VERBOSE)

    def parse(self, vstring):
        match = self.version_re.match(vstring)
        if not match:
            raise ValueError, "invalid version number '%s'" % vstring

        (major, minor, patch, prerelease, prerelease_num) = \
            match.group(1, 2, 4, 6, 7)

        if not patch:
            patch = "0"
            
        if not prerelease:
            releaselevel = "final"
            serial = 0
        else:
            serial = int(prerelease_num)
            if prerelease == "a":
                releaselevel = "alpha"
            elif prerelease == "b":
                releaselevel = "beta"
            elif prerelease == "rc":
                releaselevel = "candidate"
        self.version_info = tuple(map(int, [major, minor, patch]) + \
                                  [releaselevel, serial])

    def __str__(self):
        if self.version_info[2] == 0:
            vstring = '.'.join(map(str, self.version_info[0:2]))
        else:
            vstring = '.'.join(map(str, self.version_info[0:3]))

        releaselevel = self.version_info[3][0]
        if releaselevel != 'f':
            if releaselevel == 'a':
                prerelease = "a"
            elif releaselevel == 'b':
                prerelease = "b"
            elif releaselevel == 'c':
                prerelease = "rc"
            vstring = vstring + prerelease + str(self.version_info[4])

        return vstring

    def __cmp__(self, other):
        if isinstance(other, str):
            other = SBVersion(other)

        return cmp(self.version_info, other.version_info)

    def get_long_version(self, app_name = None):
        if app_name is None:
            app_name = "SpamBayes"
        return _("%s Version %s (%s)") % (app_name, str(self), self.date)

#============================================================================

# Utilities to check the "latest" version of an app.
# Assumes that a 'config' version of this file exists at the given URL
# No exceptions are caught
try:
    import ConfigParser
    class MySafeConfigParser(ConfigParser.SafeConfigParser):
        def optionxform(self, optionstr):
            return optionstr # no lower!
except AttributeError: # No SafeConfigParser!
    MySafeConfigParser = None

def fetch_latest_dict(url=LATEST_VERSION_HOME):
    if MySafeConfigParser is None:
        raise RuntimeError, \
              "Sorry, but only Python 2.3+ can trust remote config files"

    import urllib2
    from spambayes.Options import options
    server = options["globals", "proxy_server"]
    if server != "":
        if ':' in server:
            server, port = server.split(':', 1)
            port = int(port)
        else:
            port = 8080
        if options["globals", "proxy_username"]:
            user_pass_string = "%s:%s" % \
                               (options["globals", "proxy_username"],
                                options["globals", "proxy_password"])
        else:
            user_pass_string = ""
        proxy_support = urllib2.ProxyHandler({"http" :
                                              "http://%s@%s:%d" % \
                                              (user_pass_string, server,
                                               port)})
        opener = urllib2.build_opener(proxy_support, urllib2.HTTPHandler)
        urllib2.install_opener(opener)
    stream = urllib2.urlopen(url)
    cfg = MySafeConfigParser()
    cfg.readfp(stream)
    ret_dict = {}
    apps_dict = ret_dict["Apps"] = {}
    for sect in cfg.sections():
        if sect == "SpamBayes":
            target_dict = ret_dict
        else:
            target_dict = apps_dict.setdefault(sect, {})
        for opt in cfg.options(sect):
            val = cfg.get(sect, opt)
            target_dict[opt] = val
    return ret_dict

# Utilities for generating a 'config' version of this file.
# The output of this should exist at the URL above.
compat_apps = {
    "Outlook" : {
        "Description":      "SpamBayes Outlook Addin",
    },
    "POP3 Proxy" : {
        "Description":      "SpamBayes POP3 Proxy",
    },
}
shared_cfg_opts = {
    # Note this means we can change the download page later, and old
    # versions will still go to the new page.
    # We may also like to have a "Release Notes Page" item later?
    "Download Page": "http://spambayes.sourceforge.net/windows.html",
}
def _write_cfg_opts(stream, this_dict):
    for name, val in this_dict.items():
        if type(val)==type(''):
            val_str = repr(val)[1:-1]
        elif type(val)==type(0.0):
            val_str = str(val)
        elif type(val)==type({}):
            val_str = None # sub-dict
        else:
            print "Skipping unknown value type: %r" % val
            val_str = None
        if val_str is not None:
            stream.write("%s:%s\n" % (name, val_str))
def _make_compatible_cfg_section(stream, key, ver, this_dict):
    stream.write("[%s]\n" % key)
    # We need to create a float representation of the current version that
    # sort correctly in older versions that used a float version number.
    ver_num = float(ver.version_info[0])
    ver_num += float(ver.version_info[1] * 0.1)
    ver_num += float(ver.version_info[2] * 0.01)
    releaselevel = ver.version_info[3][0]
    if releaselevel == 'a':
        prerelease_offset = 0.001 - (float(ver.version_info[4]) * 0.00001)
    elif releaselevel == 'b':
        prerelease_offset = 0.0005 - (float(ver.version_info[4]) * 0.00001)
    elif releaselevel == 'c':
        prerelease_offset = 0.0001 - (float(ver.version_info[4]) * 0.00001)
    else:
        prerelease_offset = 0.0
    ver_num -= prerelease_offset
    stream.write("Version:%s\n" % str(ver_num))
    stream.write("BinaryVersion:%s\n" % str(ver_num))
    stream.write("Date:%s\n" % ver.date)
    _write_cfg_opts(stream, this_dict)
    desc_str = "%%(Description)s Version %s (%%(Date)s)" % str(ver)
    stream.write("Full Description:%s\n" % desc_str)
    stream.write("Full Description Binary:%s\n" % desc_str)
    _write_cfg_opts(stream, versions)
    stream.write("\n")
def _make_cfg_section(stream, ver):
    stream.write("[SpamBayes]\n")
    stream.write("Version:%s\n" % str(ver))
    stream.write("Date:%s\n" % ver.date)
    _write_cfg_opts(stream, versions)
    stream.write("\n")

def make_cfg(stream):
    stream.write("# This file is generated from spambayes/Version.py" \
                 " - do not edit\n")
    ver = get_current_version()
    _make_cfg_section(stream, ver)
    for appname in compat_apps:
        _make_compatible_cfg_section(stream, appname, ver, versions["Apps"][appname])

def main(args):
    if '-g' in args:
        make_cfg(sys.stdout)
        sys.exit(0)
        
    v_this = get_current_version()
    print "Current version:", v_this.get_long_version()

    print
    print "Fetching the lastest version information..."
    try:
        latest_dict = fetch_latest_dict()
    except:
        print "FAILED to fetch the latest version"
        import traceback
        traceback.print_exc()
        sys.exit(1)

    v_latest = get_version(version_dict=latest_dict)
    print
    print "Latest version:", v_latest.get_long_version()

if __name__ == '__main__':
    main(sys.argv)
