from __future__ import generators

import cPickle
import os
import sys
import errno
import types
import shutil
import traceback
import operator
import win32api, win32con, win32gui

import timer, thread

import win32com.client
import win32com.client.gencache
import pythoncom

import msgstore

# Characters valid in a filename.  Used to nuke bad chars from the profile
# name (which we try and use as a filename).
# We assume characters > 127 are OK as they may be unicode
filename_chars = ('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                '0123456789'
                """$%'-_@~ `!()^#&+,;=[]""")

# Report a message to the user - should only be used for pretty serious errors
# hence we also print a traceback.
# Module level function so we can report errors creating the manager
def _GetParent():
    try:
        return win32gui.GetActiveWindow()
    except win32gui.error:
        pass
    return 0

def _DoMessage(message, title, flags):
    return win32gui.MessageBox(_GetParent(), message, title, flags)

def ReportError(message, title = None):
    import traceback
    print "ERROR:", repr(message)
    if sys.exc_info()[0] is not None:
        traceback.print_exc()
    if title is None: title = "SpamBayes"
    _DoMessage(message, title, win32con.MB_ICONEXCLAMATION)

def ReportInformation(message, title = None):
    if title is None: title = "SpamBayes"
    _DoMessage(message, title, win32con.MB_ICONINFORMATION)

def AskQuestion(message, title = None):
    if title is None: title = "SpamBayes"
    return _DoMessage(message, title, win32con.MB_YESNO | \
                                      win32con.MB_ICONQUESTION) == win32con.IDYES

# Non-ascii characters in file or directory names only fully work in
# Python 2.3.3+, but latin-1 "compatible" filenames should work in 2.3
try:
    filesystem_encoding = sys.getfilesystemencoding()
except AttributeError:
    filesystem_encoding = "mbcs"

# Work out our "application directory", which is
# the directory of our main .py/.dll/.exe file we
# are running from.
if hasattr(sys, "frozen"):
    assert sys.frozen == "dll", "outlook only supports inproc servers"
    this_filename = win32api.GetModuleFileName(sys.frozendllhandle)
else:
    this_filename = os.path.abspath(__file__)

# Ensure that a bsddb module is available if we are frozen.
# See if we can use the new bsddb module. (The old one is unreliable
# on Windows, so we don't use that)
if hasattr(sys, "frozen"):
    try:
        import bsddb3
    except ImportError:
        bsddb3 = None
    try:
        import bsddb
    except ImportError:
        bsddb = None
    else:
        # This name is not in the old (bad) one.
        if not hasattr(bsddb, "db"):
            bsddb = None
    assert bsddb or bsddb3, \
           "Don't build binary versions without bsddb!"

# This is a little bit of a hack <wink>.  We are generally in a child
# directory of the bayes code.  To help installation, we handle the
# fact that this may not be on sys.path.  Note that doing these
# imports is delayed, so that we can set the BAYESCUSTOMIZE envar
# first (if we import anything from the core spambayes code before
# setting that envar, our .ini file may have no effect).
# However, we want *some* Spambayes code before the options are processed
# so this is now 2 steps - get the "early" spambayes core stuff (which
# must not import spambayes.Options) and sets up sys.path, and "later" core
# stuff, which can include spambayes.Options, and assume sys.path in place.
def import_early_core_spambayes_stuff():
    global bayes_i18n
    try:
        from spambayes import OptionsClass
    except ImportError:
        parent = os.path.abspath(os.path.join(os.path.dirname(this_filename),
                                              ".."))
        sys.path.insert(0, parent)
    from spambayes import i18n
    bayes_i18n = i18n

def import_core_spambayes_stuff(ini_filenames):
    global bayes_classifier, bayes_tokenize, bayes_storage, bayes_options, \
           bayes_message, bayes_stats
    if "spambayes.Options" in sys.modules:
        # The only thing we are worried about here is spambayes.Options
        # being imported before we have determined the INI files we need to
        # use.
        # The only way this can happen otherwise is when the addin is
        # de-selected then re-selected via the Outlook GUI - and when
        # running from source-code, it never appears in this list.
        # So this should never happen from source-code, and if it does, then
        # the developer has recently changed something that causes the early
        # import
        assert hasattr(sys, "frozen")
        # And we don't care (we could try and reload the engine options,
        # but these are very unlikely to have changed)
        return
    # ini_filenames may contain Unicode, but environ not unicode aware.
    # Convert if necessary.
    use_names = []
    for name in ini_filenames:
        if isinstance(name, unicode):
            name = name.encode(filesystem_encoding)
        use_names.append(name)
    os.environ["BAYESCUSTOMIZE"] = os.pathsep.join(use_names)
    from spambayes import classifier
    from spambayes.tokenizer import tokenize
    from spambayes import storage
    from spambayes import message
    from spambayes import Stats
    bayes_classifier = classifier
    bayes_tokenize = tokenize
    bayes_storage = storage
    bayes_message = message
    bayes_stats = Stats
    assert "spambayes.Options" in sys.modules, \
        "Expected 'spambayes.Options' to be loaded here"
    from spambayes.Options import options
    bayes_options = options

# Function to "safely" save a pickle, only overwriting
# the existing file after a successful write.
def SavePickle(what, filename):
    temp_filename = filename + ".tmp"
    file = open(temp_filename,"wb")
    try:
        cPickle.dump(what, file, 1)
    finally:
        file.close()
    # now rename to the correct file.
    try:
        os.unlink(filename)
    except os.error:
        pass
    os.rename(temp_filename, filename)

# Base class for our "storage manager" - we choose between the pickle
# and DB versions at runtime.  As our bayes uses spambayes.storage,
# our base class can share common bayes loading code, and we use
# spambayes.message, so the base class can share common message info
# code, too.
class BasicStorageManager:
    db_extension = None # for pychecker - overwritten by subclass
    def __init__(self, bayes_base_name, mdb_base_name):
        self.bayes_filename = bayes_base_name.encode(filesystem_encoding) + \
                              self.db_extension
        self.mdb_filename = mdb_base_name.encode(filesystem_encoding) + \
                            self.db_extension
    def new_bayes(self):
        # Just delete the file and do an "open"
        try:
            os.unlink(self.bayes_filename)
        except EnvironmentError, e:
            if e.errno != errno.ENOENT: raise
        return self.open_bayes()
    def store_bayes(self, bayes):
        bayes.store()
    def open_bayes(self):
        return bayes_storage.open_storage(self.bayes_filename, self.klass)
    def close_bayes(self, bayes):
        bayes.close()
    def open_mdb(self):
        # MessageInfo storage types may lag behind, so use pickle if the
        # matching type isn't available.
        if self.klass in bayes_message._storage_types.keys():
            return bayes_message.open_storage(self.mdb_filename, self.klass)
        return bayes_message.open_storage(self.mdb_filename, "pickle")
    def store_mdb(self, mdb):
        mdb.store()
    def close_mdb(self, mdb):
        mdb.close()

class PickleStorageManager(BasicStorageManager):
    db_extension = ".pck"
    klass = "pickle"
    def new_mdb(self):
        return {}
    def is_incremental(self):
        return False # False means we always save the entire DB

class DBStorageManager(BasicStorageManager):
    db_extension = ".db"
    klass = "dbm"
    def new_mdb(self):
        try:
            os.unlink(self.mdb_filename)
        except EnvironmentError, e:
            if e.errno != errno.ENOENT: raise
        return self.open_mdb()
    def is_incremental(self):
        return True # True means only changed records get actually written

class ZODBStorageManager(DBStorageManager):
    db_extension = ".fs"
    klass = "zodb"

# Encapsulates our entire classification database
# This allows a couple of different "databases" to be open at once
# eg, a "temporary" one for training, etc.
# The manager should contain no database state - it should all be here.
class ClassifierData:
    def __init__(self, db_manager, logger):
        self.db_manager = db_manager
        self.bayes = None
        self.message_db = None
        self.dirty = False
        self.logger = logger # currently the manager, but needed only for logging

    def Load(self):
        import time
        start = time.clock()
        bayes = message_db = None
        # Exceptions must be caught by caller.
        # file-not-found handled gracefully by storage.
        bayes = self.db_manager.open_bayes()
        fname = self.db_manager.bayes_filename.encode("mbcs", "replace")
        print "Loaded bayes database from '%s'" % (fname,)

        message_db = self.db_manager.open_mdb()
        fname = self.db_manager.mdb_filename.encode("mbcs", "replace")
        print "Loaded message database from '%s'" % (fname,)

        self.logger.LogDebug(0, "Bayes database initialized with "
                   "%d spam and %d good messages" % (bayes.nspam, bayes.nham))
        # Once, we checked that the message database was the same length
        # as the training database here.  However, we now store information
        # about messages that are classified but not trained in the message
        # database, so the lengths will not be equal (unless all messages
        # are trained).  That step doesn't really gain us anything, anyway,
        # since it no longer would tell us useful information, so remove it.
        self.bayes = bayes
        self.message_db = message_db
        self.dirty = False
        self.logger.LogDebug(1, "Loaded databases in %gms" % ((time.clock()-start)*1000))

    def InitNew(self):
        if self.bayes is not None:
            self.db_manager.close_bayes(self.bayes)
        if self.message_db is not None:
            self.db_manager.close_mdb(self.message_db)
        self.bayes = self.db_manager.new_bayes()
        self.message_db = self.db_manager.new_mdb()
        self.dirty = True

    def SavePostIncrementalTrain(self):
        # Save the database after a training operation - only actually
        # saves if we aren't using pickles.
        if self.db_manager.is_incremental():
            if self.dirty:
                self.Save()
            else:
                self.logger.LogDebug(1, "Bayes database is not dirty - not writing")
        else:
            print "Using a slow database - not saving after incremental train"

    def Save(self):
        import time
        start = time.clock()
        bayes = self.bayes

        if self.logger.verbose:
            print "Saving bayes database with %d spam and %d good messages" %\
                   (bayes.nspam, bayes.nham)
            print " ->", self.db_manager.bayes_filename
        self.db_manager.store_bayes(self.bayes)
        if self.logger.verbose:
            print " ->", self.db_manager.mdb_filename
        self.db_manager.store_mdb(self.message_db)
        self.dirty = False
        self.logger.LogDebug(1, "Saved databases in %gms" % ((time.clock()-start)*1000))

    def Close(self):
        if self.dirty and self.bayes:
            print "Warning: ClassifierData closed while Bayes database dirty"
        if self.db_manager:
            self.db_manager.close_bayes(self.bayes)
            self.db_manager.close_mdb(self.message_db)
            self.db_manager = None
        self.bayes = None
        self.logger = None

    def Adopt(self, other):
        assert not other.dirty, "Adopting dirty classifier data!"
        other.db_manager.close_bayes(other.bayes)
        other.db_manager.close_mdb(other.message_db)
        self.db_manager.close_bayes(self.bayes)
        self.db_manager.close_mdb(self.message_db)
        # Move the files
        shutil.move(other.db_manager.bayes_filename, self.db_manager.bayes_filename)
        shutil.move(other.db_manager.mdb_filename, self.db_manager.mdb_filename)
        # and re-open.
        self.Load()

def GetStorageManagerClass():
    # We used to enforce this so that all binary users used bsddb, and
    # unless they modified the source, so would all source users.  We
    # would like more flexibility now, so we match what the rest of the
    # applications do - this isn't exposed via the GUI, so Outlook users
    # still get bsddb by default, and have to fiddle with a text file
    # to change that.
    use_db = bayes_options["Storage", "persistent_use_database"]
    available = {"pickle" : PickleStorageManager,
                 "dbm"    : DBStorageManager,
                 "zodb"   : ZODBStorageManager,
                 }
    if use_db not in available:
        # User is trying to use something fancy which isn't available.
        # Fall back on bsddb.
        print use_db, "storage type not available.  Using bsddb."
        use_db = "dbm"
    return available[use_db]

# Our main "bayes manager"
class BayesManager:
    def __init__(self, config_base="default", outlook=None, verbose=0):
        self.owner_thread_ident = thread.get_ident() # check we aren't multi-threaded
        self.never_configured = True
        self.reported_error_map = {}
        self.reported_startup_error = False
        self.config = self.options = None
        self.addin = None
        self.verbose = verbose
        self.outlook = outlook
        self.dialog_parser = None
        self.test_suite_running = False
        self.received_ham = self.received_unsure = self.received_spam = 0
        self.notify_timer_id = None

        import_early_core_spambayes_stuff()

        self.application_directory = os.path.dirname(this_filename)

        # Load the environment for translation.
        lang_manager = bayes_i18n.LanguageManager()
        # Set the system user default language.
        lang_manager.set_language(lang_manager.locale_default_lang())

        # where windows would like our data stored (and where
        # we do, unless overwritten via a config file)
        self.windows_data_directory = self.LocateDataDirectory()
        # Read the primary configuration files
        self.PrepareConfig()

        # See if the initial config files specify a
        # "data directory".  If so, use it, otherwise
        # use the default Windows data directory for our app.
        value = self.config.general.data_directory
        if value:
            # until I know otherwise, config files are ASCII - but our
            # file system is unicode to some degree.
            # (do config files support encodings at all?)
            # Assume the file system encoding for file names!
            try:
                value = value.decode(filesystem_encoding)
            except AttributeError: # May already be Unicode
                pass
            assert isinstance(value, types.UnicodeType), "%r should be a unicode" % value
            try:
                if not os.path.isdir(value):
                    os.makedirs(value)
                assert os.path.isdir(value), "just made the *ucker"
                value = os.path.abspath(value)
            except os.error:
                print "The configuration files have specified a data " \
                      "directory of", repr(value), "but it is not valid. " \
                      "Using default."
                value = None
        if value:
            self.data_directory = value
        else:
            self.data_directory = self.windows_data_directory

        # Get the message store before loading config, as we use the profile
        # name.
        self.message_store = msgstore.MAPIMsgStore(outlook)
        self.LoadConfig()

        # Load the options for the classifier.  We support
        # default_bayes_customize.ini in the app directory and user data
        # directory (version 0.8 and earlier, we copied the app one to the
        # user dir - that was a mistake - but supporting a version in that
        # directory wasn't).  We also look for a
        # {outlook-profile-name}_bayes_customize.ini file in the data
        # directory, to allow per-profile customisations.
        bayes_option_filenames = []
        # data dir last so options there win.
        for look_dir in [self.application_directory, self.data_directory]:
            look_file = os.path.join(look_dir, "default_bayes_customize.ini")
            if os.path.isfile(look_file):
                bayes_option_filenames.append(look_file)
        look_file = os.path.join(self.data_directory,
                                 self.GetProfileName() + \
                                 "_bayes_customize.ini")
        if os.path.isfile(look_file):
            bayes_option_filenames.append(look_file)
        import_core_spambayes_stuff(bayes_option_filenames)

        # Set interface to use the user language in configuration file.
        for language in bayes_options["globals", "language"][::-1]:
            # We leave the default in there as the last option, to fall
            # back on if necessary.
            lang_manager.add_language(language)
        self.LogDebug(1, "Asked to add languages: " + \
                      ", ".join(bayes_options["globals", "language"]))
        self.LogDebug(1, "Set language to " + \
                      str(lang_manager.current_langs_codes))

        bayes_base = os.path.join(self.data_directory, "default_bayes_database")
        mdb_base = os.path.join(self.data_directory, "default_message_database")
        # determine which db manager to use, and create it.
        ManagerClass = GetStorageManagerClass()
        db_manager = ManagerClass(bayes_base, mdb_base)
        self.classifier_data = ClassifierData(db_manager, self)
        try:
            self.classifier_data.Load()
        except:
            self.ReportFatalStartupError("Failed to load bayes database")
            self.classifier_data.InitNew()
        self.bayes_options = bayes_options
        self.bayes_message = bayes_message
        bayes_options["Categorization", "spam_cutoff"] = \
                                        self.config.filter.spam_threshold \
                                        / 100.0
        bayes_options["Categorization", "ham_cutoff"] = \
                                        self.config.filter.unsure_threshold \
                                        / 100.0
        self.stats = bayes_stats.Stats(bayes_options,
                                       self.classifier_data.message_db)

    def AdoptClassifierData(self, new_classifier_data):
        self.classifier_data.Adopt(new_classifier_data)
        self.stats.messageinfo_db = self.classifier_data.message_db

    # Logging - this should be somewhere else.
    def LogDebug(self, level, *args):
        if self.verbose >= level:
            for arg in args[:-1]:
                print arg,
            print args[-1]

    def ReportError(self, message, title = None):
        if self.test_suite_running:
            print "ReportError:", repr(message)
            print "(but test suite running - not reported)"
            return
        ReportError(message, title)
    def ReportInformation(self, message, title=None):
        if self.test_suite_running:
            print "ReportInformation:", repr(message)
            print "(but test suite running - not reported)"
            return
        ReportInformation(message, title)
    def AskQuestion(self, message, title=None):
        return AskQuestion(message, title)

    # Report a super-serious startup error to the user.
    # This should only be used when SpamBayes was previously working, but a
    # critical error means we are probably not working now.
    # We just report the first such error - subsequent ones are likely a result of
    # the first - hence, this must only be used for startup errors.
    def ReportFatalStartupError(self, message):
        if not self.reported_startup_error:
            self.reported_startup_error = True
            full_message = _(\
                "There was an error initializing the Spam plugin.\r\n\r\n" \
                "Spam filtering has been disabled.  Please re-configure\r\n" \
                "and re-enable this plugin\r\n\r\n" \
                "Error details:\r\n") + message
            # Disable the plugin
            if self.config is not None:
                self.config.filter.enabled = False
            self.ReportError(full_message)
        else:
            # We have reported the error, but for the sake of the log, we
            # still want it logged there.
            print "ERROR:", repr(message)
            traceback.print_exc()

    def ReportErrorOnce(self, msg, title = None, key = None):
        if key is None: key = msg
        # Always print the message and traceback.
        if self.test_suite_running:
            print "ReportErrorOnce:", repr(msg)
            print "(but test suite running - not reported)"
            return
        print "ERROR:", repr(msg)
        if key in self.reported_error_map:
            print "(this error has already been reported - not displaying it again)"
        else:
            traceback.print_exc()
            self.reported_error_map[key] = True
            ReportError(msg, title)

    # Outlook used to give us thread grief - now we avoid Outlook
    # from threads, but this remains a worthwhile abstraction.
    def WorkerThreadStarting(self):
        pythoncom.CoInitialize()

    def WorkerThreadEnding(self):
        pythoncom.CoUninitialize()

    def LocateDataDirectory(self):
        # Locate the best directory for our data files.
        from win32com.shell import shell, shellcon
        try:
            appdata = shell.SHGetFolderPath(0,shellcon.CSIDL_APPDATA,0,0)
            path = os.path.join(appdata, "SpamBayes")
            if not os.path.isdir(path):
                os.makedirs(path)
            return path
        except pythoncom.com_error:
            # Function doesn't exist on early win95,
            # and it may just fail anyway!
            return self.application_directory
        except EnvironmentError:
            # Can't make the directory.
            return self.application_directory

    def FormatFolderNames(self, folder_ids, include_sub):
        names = []
        for eid in folder_ids:
            try:
                folder = self.message_store.GetFolder(eid)
                name = folder.name
            except self.message_store.MsgStoreException:
                name = "<unknown folder>"
            names.append(name)
        ret = '; '.join(names)
        if include_sub:
            ret += " (incl. Sub-folders)"
        return ret

    def EnsureOutlookFieldsForFolder(self, folder_id, include_sub=False):
        # Should be called at least once once per folder you are
        # watching/filtering etc
        # Ensure that our fields exist on the Outlook *folder*
        # Setting properties via our msgstore (via Ext Mapi) sets the props
        # on the message OK, but Outlook doesn't see it as a "UserProperty".
        # Using MAPI to set them directly on the folder also has no effect.
        # Later: We have since discovered that Outlook stores user property
        # information in the 'associated contents' folder - see
        # msgstore.MAPIMsgStoreFolder.DoesFolderHaveOutlookField() for more
        # details.  We can reverse engineer this well enough to determine
        # if a property exists, but not well enough to actually add a
        # property.  Thus, we resort to the Outlook object model to actually
        # add it.
        # Note that this means we need an object in the folder to modify.
        # We could go searching for an existing item then modify and save it
        # (indeed, we did once), but this could be bad-form, as the message
        # we randomly choose to modify will then have a meaningless 'Spam'
        # field.  If we are going to go to the effort of creating a temp
        # item when no item exists, we may as well do it all the time,
        # especially now we know how to check if the folder has the field
        # without opening an Outlook item.

        # Regarding the property type:
        # We originally wanted to use the "Integer" Outlook field,
        # but it seems this property type alone is not exposed via the Object
        # model.  So we resort to olPercent, and live with the % sign
        # (which really is OK!)
        assert self.outlook is not None, "I need outlook :("
        field_name = self.config.general.field_score_name
        for msgstore_folder in self.message_store.GetFolderGenerator(
                                                    [folder_id], include_sub):
            folder_name = msgstore_folder.GetFQName()
            if msgstore_folder.DoesFolderHaveOutlookField(field_name):
                self.LogDebug(1, "Folder '%s' already has field '%s'" \
                                 % (folder_name, field_name))
                continue
            self.LogDebug(0, "Folder '%s' has no field named '%s' - creating" \
                      % (folder_name, field_name))
            # Creating the item via the Outlook model does some strange
            # things (such as moving it to "Drafts" on save), so we create
            # it using extended MAPI (via our msgstore)
            message = msgstore_folder.CreateTemporaryMessage(msg_flags=1)
            outlook_message = message.GetOutlookItem()
            ups = outlook_message.UserProperties
            try:
                # Display format is documented as being the 1-based index in
                # the combo box in the outlook UI for the given data type.
                # 1 is the first - "Rounded", which seems fine.
                format = 1
                ups.Add(field_name,
                       win32com.client.constants.olPercent,
                       True, # Add to folder
                       format)
                outlook_message.Save()
            except pythoncom.com_error, details:
                if msgstore.IsReadOnlyCOMException(details):
                    self.LogDebug(1, "The folder '%s' is read-only - user "
                                     "property can't be added" % (folder_name,))
                else:
                    print "Warning: failed to create the Outlook " \
                          "user-property in folder '%s'" \
                          % (folder_name,)
                    print "", details
            msgstore_folder.DeleteMessages((message,))
            # Check our DoesFolderHaveOutlookField logic holds up.
            if not msgstore_folder.DoesFolderHaveOutlookField(field_name):
                self.LogDebug(0,
                        "WARNING: We just created the user field in folder "
                        "%s, but it appears to not exist.  Something is "
                        "probably wrong with DoesFolderHaveOutlookField()" % \
                        folder_name)

    def PrepareConfig(self):
        # Load our Outlook specific configuration.  This is done before
        # SpamBayes is imported, and thus we are able to change the INI
        # file used for the engine.  It is also done before the primary
        # options are loaded - this means we can change the directory
        # from which these options are loaded.
        import config
        self.options = config.CreateConfig()
        # Note that self.options really *is* self.config - but self.config
        # allows a "." notation to access the values.  Changing one is reflected
        # immediately in the other.
        self.config = config.OptionsContainer(self.options)

        filename = os.path.join(self.application_directory, "default_configuration.ini")
        self._MergeConfigFile(filename)

        filename = os.path.join(self.windows_data_directory, "default_configuration.ini")
        self._MergeConfigFile(filename)

    def _MergeConfigFile(self, filename):
        try:
            self.options.merge_file(filename)
        except:
            msg = _("The configuration file named below is invalid.\r\n" \
                    "Please either correct or remove this file\r\n\r\n" \
                    "Filename: ") + filename
            self.ReportError(msg)

    def GetProfileName(self):
        profile_name = self.message_store.GetProfileName()
        # The profile name may include characters invalid in file names.
        if profile_name is not None:
            profile_name = "".join([c for c in profile_name
                                    if ord(c)>127 or c in filename_chars])
        if profile_name is None:
            # should only happen in source-code versions - older win32alls can't
            # determine this.
            profile_name = "unknown_profile"
            print "*** NOTE: It appears you are running the source-code version of"
            print "* SpamBayes, and running a win32all version pre 154."
            print "* If you work with multiple Outlook profiles, it is recommended"
            print "* you upgrade - see http://starship.python.net/crew/mhammond"""
        return profile_name

    def LoadConfig(self):
        # Insist on English numeric conventions in config file.
        # See addin.py, and [725466] Include a proper locale fix in Options.py
        import locale; locale.setlocale(locale.LC_NUMERIC, "C")
        profile_name = self.GetProfileName()
        self.config_filename = os.path.join(self.data_directory, profile_name + ".ini")
        self.never_configured = not os.path.exists(self.config_filename)
        # Now load it up
        self._MergeConfigFile(self.config_filename)
        # Set global verbosity from the options file.
        self.verbose = self.config.general.verbose
        if self.verbose:
            self.LogDebug(self.verbose, "System verbosity set to", self.verbose)

        # Do any migrations - first the old pickle into the new format.
        self.MigrateOldPickle()
        # Then any options we change (particularly any 'experimental' ones we
        # consider important)
        import config
        config.MigrateOptions(self.options)

        if self.verbose > 1:
            print "Dumping loaded configuration:"
            print self.options.display()
            print "-- end of configuration --"

    def MigrateOldPickle(self):
        assert self.config is not None, "Must have a config"
        pickle_filename = os.path.join(self.data_directory,
                                       "default_configuration.pck")
        try:
            f = open(pickle_filename, 'rb')
        except IOError:
            self.LogDebug(1, "No old pickle file to migrate")
            return
        print "Migrating old pickle '%s'" % pickle_filename
        try:
            try:
                old_config = cPickle.load(f)
            except:
                print "FAILED to load old pickle"
                traceback.print_exc()
                msg = _("There was an error loading your old\r\n" \
                        "SpamBayes configuration file.\r\n\r\n" \
                        "It is likely that you will need to re-configure\r\n" \
                        "SpamBayes before it will function correctly.")
                self.ReportError(msg)
                # But we can't abort yet - we really should still try and
                # delete it, as we aren't gunna work next time in this case!
                old_config = None
        finally:
            f.close()
        if old_config is not None:
            for section, items in old_config.__dict__.items():
                print " migrating section '%s'" % (section,)
                # exactly one value wasn't in a section - now in "general"
                dict = getattr(items, "__dict__", None)
                if dict is None:
                    dict = {section: items}
                    section = "general"
                for name, value in dict.items():
                    sect = getattr(self.config, section)
                    setattr(sect, name, value)
        # Save the config, then delete the pickle so future attempts to
        # migrate will fail.  We save first, so failure here means next
        # attempt should still find the pickle.
        self.LogDebug(1, "pickle migration doing initial configuration save")
        try:
            self.LogDebug(1, "pickle migration removing '%s'" % pickle_filename)
            os.remove(pickle_filename)
        except os.error:
            msg = _("There was an error migrating and removing your old\r\n" \
                    "SpamBayes configuration file.  Configuration changes\r\n" \
                    "you make are unlikely to be reflected next\r\n" \
                    "time you start Outlook.  Please try rebooting.")
            self.ReportError(msg)


    def GetClassifier(self):
        """Return the classifier we're using."""
        return self.classifier_data.bayes

    def SaveConfig(self):
        # Insist on english numeric conventions in config file.
        # See addin.py, and [725466] Include a proper locale fix in Options.py
        import locale; locale.setlocale(locale.LC_NUMERIC, "C")

        # Update our runtime verbosity from the options.
        self.verbose = self.config.general.verbose
        print "Saving configuration ->", self.config_filename.encode("mbcs", "replace")
        assert self.config and self.options, "Have no config to save!"
        if self.verbose > 1:
            print "Dumping configuration to save:"
            print self.options.display()
            print "-- end of configuration --"
        self.options.update_file(self.config_filename)

    def Save(self):
        # No longer save the config here - do it explicitly when changing it
        # (prevents lots of extra pickle writes, for no good reason.  Other
        # alternative is a dirty flag for config - this is simpler)
        if self.classifier_data.dirty:
            self.classifier_data.Save()
        else:
            self.LogDebug(1, "Bayes database is not dirty - not writing")

    def Close(self):
        global _mgr
        self._KillNotifyTimer()
        self.classifier_data.Close()
        self.config = self.options = None
        if self.message_store is not None:
            self.message_store.Close()
            self.message_store = None
        self.outlook = None
        self.addin = None
        # If we are the global manager, reset that
        if _mgr is self:
            _mgr = None

    def score(self, msg, evidence=False):
        """Score a msg.

        If optional arg evidence is specified and true, the result is a
        two-tuple

            score, clues

        where clues is a list of the (word, spamprob(word)) pairs that
        went into determining the score.  Else just the score is returned.
        """
        email = msg.GetEmailPackageObject()
        try:
            return self.classifier_data.bayes.spamprob(bayes_tokenize(email), evidence)
        except AssertionError:
            # See bug 706520 assert fails in classifier
            # For now, just tell the user.
            msg = _("It appears your SpamBayes training database is corrupt.\r\n\r\n" \
                    "We are working on solving this, but unfortunately you\r\n" \
                    "must re-train the system via the SpamBayes manager.")
            self.ReportErrorOnce(msg)
            # and disable the addin, as we are hosed!
            self.config.filter.enabled = False
            raise

    def GetDisabledReason(self):
        # Gets the reason why the plugin can not be enabled.
        # If return is None, then it can be enabled (and indeed may be!)
        # Otherwise return is the string reason
        config = self.config.filter
        ok_to_enable = operator.truth(config.watch_folder_ids)
        if not ok_to_enable:
            return _("You must define folders to watch for new messages.  " \
                     "Select the 'Filtering' tab to define these folders.")

        ok_to_enable = operator.truth(config.spam_folder_id)
        if not ok_to_enable:
            return _("You must define the folder to receive your certain spam.  " \
                     "Select the 'Filtering' tab to define this folder.")

        # Check that the user hasn't selected the same folder as both
        # 'Spam' or 'Unsure', and 'Watch' - this would confuse us greatly.
        ms = self.message_store
        unsure_folder = None # unsure need not be specified.
        if config.unsure_folder_id:
            try:
                unsure_folder = ms.GetFolder(config.unsure_folder_id)
            except ms.MsgStoreException, details:
                return _("The unsure folder is invalid: %s") % (details,)
        try:
            spam_folder = ms.GetFolder(config.spam_folder_id)
        except ms.MsgStoreException, details:
            return _("The spam folder is invalid: %s") % (details,)
        if ok_to_enable:
            for folder in ms.GetFolderGenerator(config.watch_folder_ids,
                                                config.watch_include_sub):
                bad_folder_type = None
                if unsure_folder is not None and unsure_folder == folder:
                    bad_folder_type = _("unsure")
                    bad_folder_name = unsure_folder.GetFQName()
                if spam_folder == folder:
                    bad_folder_type = _("spam")
                    bad_folder_name = spam_folder.GetFQName()
                if bad_folder_type is not None:
                    return _("You can not specify folder '%s' as both the " \
                             "%s folder, and as being watched.") \
                             % (bad_folder_name, bad_folder_type)
        return None

    def ShowManager(self):
        import dialogs
        dialogs.ShowDialog(0, self, self.config, "IDD_MANAGER")
        # And re-save now, just incase Outlook dies on the way down.
        self.SaveConfig()
        # And update the cutoff values in bayes_options (which the
        # stats use) to our thresholds.
        bayes_options["Categorization", "spam_cutoff"] = \
                                        self.config.filter.spam_threshold \
                                        / 100.0
        bayes_options["Categorization", "ham_cutoff"] = \
                                        self.config.filter.unsure_threshold \
                                        / 100.0
        # And tell the addin that our filters may have changed.
        if self.addin is not None:
            self.addin.FiltersChanged()

    def ShowFilterNow(self):
        import dialogs
        dialogs.ShowDialog(0, self, self.config, "IDD_FILTER_NOW")
        # And re-save now, just incase Outlook dies on the way down.
        self.SaveConfig()

    def ShowHtml(self,url):
        """Displays the main SpamBayes documentation in your Web browser"""
        import sys, os, urllib
        if urllib.splittype(url)[0] is None: # just a file spec
            if hasattr(sys, "frozen"):
                # New binary is in ../docs/outlook relative to executable.
                fname = os.path.join(os.path.dirname(sys.argv[0]),
                                     "../docs/outlook",
                                     url)
                if not os.path.isfile(fname):
                    # Still support same directory as to the executable.
                    fname = os.path.join(os.path.dirname(sys.argv[0]),
                                         url)
            else:
                # (ie, main Outlook2000) dir
                fname = os.path.join(os.path.dirname(__file__),
                                        url)
            fname = os.path.abspath(fname)
            if not os.path.isfile(fname):
                self.ReportError("Can't find "+url)
                return
            url = fname
        # else assume it is valid!
        from dialogs import SetWaitCursor
        SetWaitCursor(1)
        os.startfile(url)
        SetWaitCursor(0)

    def HandleNotification(self, disposition):
        if self.config.notification.notify_sound_enabled:
            if disposition == "Yes":
                self.received_spam += 1
            elif disposition == "No":
                self.received_ham += 1
            else:
                self.received_unsure += 1
            self._StartNotifyTimer()
        
    def _StartNotifyTimer(self):
        # First kill any existing timer
        self._KillNotifyTimer()
        # And start a new timer.
        delay = self.config.notification.notify_accumulate_delay
        self._DoStartNotifyTimer(delay)
        
    def _DoStartNotifyTimer(self, delay):
        assert thread.get_ident() == self.owner_thread_ident
        assert self.notify_timer_id is None, "Shouldn't start a timer when already have one"
        assert isinstance(delay, types.FloatType), "Timer values are float seconds"
        # And start a new timer.
        assert delay, "No delay means no timer!"
        delay = int(delay*1000) # convert to ms.
        self.notify_timer_id = timer.set_timer(delay, self._NotifyTimerFunc)
        self.LogDebug(1, "Notify timer started - id=%d, delay=%d" % (self.notify_timer_id, delay))
        
    def _KillNotifyTimer(self):
        assert thread.get_ident() == self.owner_thread_ident
        if self.notify_timer_id is not None:
            timer.kill_timer(self.notify_timer_id)
            self.LogDebug(2, "The notify timer with id=%d was stopped" % self.notify_timer_id)
            self.notify_timer_id = None
        
    def _NotifyTimerFunc(self, event, time):
        # Kill the timer first
        assert thread.get_ident() == self.owner_thread_ident
        self.LogDebug(1, "The notify timer with id=%s fired" % self.notify_timer_id)
        self._KillNotifyTimer()
        
        import winsound
        config = self.config.notification
        sound_opts = winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NOSTOP | winsound.SND_NODEFAULT
        self.LogDebug(3, "Notify received ham=%d, unsure=%d, spam=%d" %
                      (self.received_ham, self.received_unsure, self.received_spam))
        if self.received_ham > 0 and len(config.notify_ham_sound) > 0:
            self.LogDebug(3, "Playing ham sound '%s'" % config.notify_ham_sound)
            winsound.PlaySound(config.notify_ham_sound, sound_opts)
        elif self.received_unsure > 0 and len(config.notify_unsure_sound) > 0:
            self.LogDebug(3, "Playing unsure sound '%s'" % config.notify_unsure_sound)
            winsound.PlaySound(config.notify_unsure_sound, sound_opts)
        elif self.received_spam > 0 and len(config.notify_spam_sound) > 0:
            self.LogDebug(3, "Playing spam sound '%s'" % config.notify_spam_sound)
            winsound.PlaySound(config.notify_spam_sound, sound_opts)
        # Reset received counts to zero after notify.
        self.received_ham = self.received_unsure = self.received_spam = 0

_mgr = None

def GetManager(outlook = None):
    global _mgr
    if _mgr is None:
        if outlook is None:
            outlook = win32com.client.Dispatch("Outlook.Application")
        _mgr = BayesManager(outlook=outlook)
    return _mgr

def ShowManager(mgr):
    mgr.ShowManager()

def main(verbose_level = 1):
    mgr = GetManager()
    mgr.verbose = max(mgr.verbose, verbose_level)
    ShowManager(mgr)
    mgr.Save()
    mgr.Close()
    return 0

def usage():
    print "Usage: manager [-v ...]"
    sys.exit(1)

if __name__=='__main__':
    verbose = 1
    import getopt
    opts, args = getopt.getopt(sys.argv[1:], "v")
    if args:
        usage()
    for opt, val in opts:
        if opt=="-v":
            verbose += 1
        else:
            usage()
    sys.exit(main(verbose))
