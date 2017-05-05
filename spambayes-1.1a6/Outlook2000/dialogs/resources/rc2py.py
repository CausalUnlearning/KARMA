# rc2py.py
# This module is part of the spambayes project, which is Copyright 2003
# The Python Software Foundation and is covered by the Python Software
# Foundation license.
__author__="Adam Walker"
__doc__=""""
Converts an .rc windows resource source file into a python source file
with the same basic public interface as the rcparser module.
"""
import sys, os, stat
import rcparser

def convert(inputFilename = None, outputFilename = None,
            enableGettext = True):
    """See the module doc string"""
    if inputFilename is None:
        inputFilename = "dialogs.rc"
    if outputFilename is None:
        outputFilename = "test.py"
    rcp = rcparser.ParseDialogs(inputFilename, enableGettext)
    in_stat = os.stat(inputFilename)

    out = open(outputFilename, "wt")
    out.write("#%s\n" % outputFilename)
    out.write("#This is a generated file. Please edit %s instead.\n" % inputFilename)
    out.write("_rc_size_=%d\n_rc_mtime_=%d\n" % (in_stat[stat.ST_SIZE], in_stat[stat.ST_MTIME]))
    out.write("try:\n    _\nexcept NameError:\n    def _(s):\n        return s\n")
    out.write("class FakeParser:\n")
    out.write("    dialogs = "+repr(rcp.dialogs)+"\n")
    out.write("    ids = "+repr(rcp.ids)+"\n")
    out.write("    names = "+repr(rcp.names)+"\n")
    out.write("    bitmaps = "+repr(rcp.bitmaps)+"\n")
    out.write("def ParseDialogs(s):\n")
    out.write("    return FakeParser()\n")
    out.close()

if __name__=="__main__":
    if len(sys.argv) > 3:
        convert(sys.argv[1], sys.argv[2], bool(int(sys.argv[3])))
    elif len(sys.argv) > 2:
        convert(sys.argv[1], sys.argv[2], True)
    else:
        convert()
