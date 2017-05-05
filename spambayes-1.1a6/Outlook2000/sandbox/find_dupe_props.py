from __future__ import generators
# Dump every property we can find for a MAPI item

import pythoncom
import os, sys

from win32com.mapi import mapi, mapiutil
from win32com.mapi.mapitags import *

import mapi_driver

def FindDupeProps(driver, mapi_folder, prop_tag, dupe_dict):
    hr, data = mapi_folder.GetProps( (PR_DISPLAY_NAME_A,), 0)
    name = data[0][1]
    try:
        prop_tag = int(prop_tag)
    except ValueError:
        # See if a constant in mapitags.
        if prop_tag.startswith("PR_") and prop_tag in globals():
            prop_tag = globals()[prop_tag]
        else:
            props = ( (mapi.PS_PUBLIC_STRINGS, prop_tag), )
            ids = mapi_folder.GetIDsFromNames(props, 0)
            if PROP_ID(ids[0])==0:
                print "Could not resolve property '%s'" % prop_tag
                return 1
            prop_tag = PROP_TAG( PT_UNSPECIFIED, PROP_ID(ids[0]))

    num_with_prop = num_without_prop = 0
    for item in driver.GetAllItems(mapi_folder):
        hr, data = item.GetProps( (prop_tag,PR_SUBJECT_A, PR_ENTRYID), 0)
        if hr==0:
            (tag_hr, tag_data) = data[0]
            (subject_hr, subject_data) = data[1]
            (eid_hr, eid_data) = data[2]
            dupe_dict.setdefault(tag_data, []).append((eid_data, subject_data))
            num_with_prop += 1
        else:
            num_without_prop += 1
    print "Folder '%s': %d items with the property and %d items without it" \
            % (name, num_with_prop, num_without_prop)

def DumpDupes(dupe_dict):
    for val, items in dupe_dict.items():
        if len(items)>1:
            print "Found %d items with property value %r" % (len(items), val)
            for (eid, subject) in items:
                print "", subject

def usage(driver):
    folder_doc = driver.GetFolderNameDoc()
    msg = """\
Usage: %s [-f foldername] [-f ...] property_name_or_tag
-f - Search for the message in the specified folders (default = Inbox)
-n - Show top-level folder names and exit

Dumps all properties for all messages that match the subject.  Subject
matching is substring and ignore-case.

%s
Use the -n option to see all top-level folder names from all stores.""" \
    % (os.path.basename(sys.argv[0]),folder_doc)
    print msg

def main():
    driver = mapi_driver.MAPIDriver()

    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:n")
    except getopt.error, e:
        print e
        print
        usage(driver)
        sys.exit(1)
    folder_names = []

    for opt, opt_val in opts:
        if opt == "-f":
            folder_names.append(opt_val)
        elif opt == "-n":
            driver.DumpTopLevelFolders()
            sys.exit(1)
        else:
            print "Invalid arg"
            return

    if not folder_names:
        folder_names = ["Inbox"] # Assume this exists!

    if len(args) != 1:
        print "You must specify a property tag/name"
        print
        usage(driver)
        sys.exit(1)

    dupe_dict = {}
    for folder_name in folder_names:
        try:
            folder = driver.FindFolder(folder_name)
        except ValueError, details:
            print details
            sys.exit(1)

        FindDupeProps(driver, folder, args[0], dupe_dict)
    DumpDupes(dupe_dict)

if __name__=='__main__':
    main()
