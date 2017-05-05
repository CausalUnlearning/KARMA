# Extract a property from a message to a file.  This is about the only
# way to extract huge properties such that the original data is available.
import sys, os
import mapi_driver
from win32com.mapi import mapitags, mapi
import pythoncom


def DumpItemProp(item, prop, outfile):
    if type(prop)!=type(0):
        # see if a mapitags contant
        try:
            prop = mapitags.__dict__[prop]
        except KeyError:
            # resolve as a name
            props = ( (mapi.PS_PUBLIC_STRINGS, prop), )
            propIds = obj.GetIDsFromNames(props, 0)
            prop = mapitags.PROP_TAG( mapitags.PT_UNSPECIFIED, mapitags.PROP_ID(propIds[0]))

    hr, data = item.GetProps((prop,), 0)
    prop_tag, prop_val = data[0]

    # Do some magic rtf conversion
    if mapitags.PROP_ID(prop_tag) == mapitags.PROP_ID(mapitags.PR_RTF_COMPRESSED):
        rtf_stream = item.OpenProperty(mapitags.PR_RTF_COMPRESSED, pythoncom.IID_IStream,
                                                0, 0)
        html_stream = mapi.WrapCompressedRTFStream(rtf_stream, 0)
        chunks = []
        while 1:
            chunk = html_stream.Read(4096)
            if not chunk:
                break
            chunks.append(chunk)
        prop_val = "".join(chunks)
    elif mapitags.PROP_TYPE(prop_tag)==mapitags.PT_ERROR and \
         prop_val in [mapi.MAPI_E_NOT_ENOUGH_MEMORY,'MAPI_E_NOT_ENOUGH_MEMORY']:
        prop_tag = mapitags.PROP_TAG(mapitags.PT_BINARY, mapitags.PROP_ID(prop_tag))
        stream = item.OpenProperty(prop_tag,
                                    pythoncom.IID_IStream,
                                    0, 0)
        chunks = []
        while 1:
            chunk = stream.Read(4096)
            if not chunk:
                break
            chunks.append(chunk)
        prop_val = "".join(chunks)
    outfile.write(prop_val)

def DumpProp(driver, mapi_folder, subject, prop_tag, outfile):
    hr, data = mapi_folder.GetProps( (mapitags.PR_DISPLAY_NAME_A,), 0)
    name = data[0][1]
    items = driver.GetItemsWithValue(mapi_folder, mapitags.PR_SUBJECT_A, subject)
    num = 0
    for item in items:
        if num > 1:
            print >> sys.stderr, "Warning: More than one matching item - ignoring"
            break
        DumpItemProp(item, prop_tag, outfile)
        num += 1
    if num==0:
        print >> sys.stderr, "Error: No matching items"

def usage(driver):
    folder_doc = driver.GetFolderNameDoc()
    msg = """\
Usage: %s [-f foldername] [-o output_file] -p property_name subject of the message
-f - Search for the message in the specified folder (default = Inbox)
-p - Name of the property to dump
-o - Output file to be created - default - stdout.

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
        opts, args = getopt.getopt(sys.argv[1:], "np:f:o:")
    except getopt.error, e:
        print e
        print
        usage(driver)
        sys.exit(1)
    folder_name = prop_name = output_name = ""

    for opt, opt_val in opts:
        if opt == "-p":
            prop_name = opt_val
        elif opt == "-f":
            folder_name = opt_val
        elif opt == '-o':
            output_name = os.path.abspath(opt_val)
        elif opt == "-n":
            driver.DumpTopLevelFolders()
            sys.exit(1)
        else:
            print "Invalid arg"
            return

    if not folder_name:
        folder_name = "Inbox" # Assume this exists!

    subject = " ".join(args)
    if not subject:
        print "You must specify a subject"
        print
        usage(driver)
        sys.exit(1)
    if not prop_name:
        print "You must specify a property"
        print
        usage(driver)
        sys.exit(1)
    if output_name:
        output_file = file(output_name, "wb")
    else:
        output_file = sys.stdout

    try:
        folder = driver.FindFolder(folder_name)
    except ValueError, details:
        print details
        sys.exit(1)

    DumpProp(driver, folder, subject, prop_name, output_file)

if __name__=='__main__':
    main()
