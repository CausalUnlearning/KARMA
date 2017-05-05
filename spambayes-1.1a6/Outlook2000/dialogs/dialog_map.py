# This module is part of the spambayes project, which is Copyright 2003
# The Python Software Foundation and is covered by the Python Software
# Foundation license.

from processors import *
from opt_processors import *
import wizard_processors as wiz

from dialogs import ShowDialog, MakePropertyPage, ShowWizard

# "dialog specific" processors:
class StatsProcessor(ControlProcessor):
    def __init__(self, window, control_ids):
        self.button_id = control_ids[1]
        self.reset_date_id = control_ids[2]
        ControlProcessor.__init__(self, window, control_ids)
        self.stats = self.window.manager.stats

    def Init(self):
        text = "\n".join(self.stats.GetStats())
        win32gui.SendMessage(self.GetControl(), win32con.WM_SETTEXT, 0, text)

        date_label = self.GetControl(self.reset_date_id)
        if self.stats.from_date:
            from time import localtime, strftime
            reset_date = localtime(self.stats.from_date)
            date_string = strftime("%a, %d %b %Y %I:%M:%S %p", reset_date)
        else:
            date_string = _("Never")
        win32gui.SendMessage(date_label, win32con.WM_SETTEXT, 0, date_string)

    def OnCommand(self, wparam, lparam):
        id = win32api.LOWORD(wparam)
        if id == self.button_id:
            self.ResetStatistics()

    def GetPopupHelpText(self, idFrom):
        if idFrom == self.control_id:
            return _("Displays statistics on mail processed by SpamBayes")
        elif idFrom == self.button_id:
            return _("Resets all SpamBayes statistics to zero")
        elif idFrom == self.reset_date_id:
            return _("The date and time when the SpamBayes statistics were last reset")

    def ResetStatistics(self):
        question = _("This will reset all your saved statistics to zero.\r\n\r\n" \
                     "Are you sure you wish to reset the statistics?")
        flags = win32con.MB_ICONQUESTION | win32con.MB_YESNO | win32con.MB_DEFBUTTON2
        if win32gui.MessageBox(self.window.hwnd,
                               question, "SpamBayes", flags) == win32con.IDYES:
            self.stats.Reset()
            self.stats.ResetTotal(True)
            self.Init()  # update the statistics display

class VersionStringProcessor(ControlProcessor):
    def Init(self):
        from spambayes.Version import get_current_version
        import sys
        v = get_current_version()
        vstring = v.get_long_version("SpamBayes Outlook Addin")
        if not hasattr(sys, "frozen"):
            vstring += _(" from source")
        win32gui.SendMessage(self.GetControl(), win32con.WM_SETTEXT, 0, vstring)

    def GetPopupHelpText(self, cid):
        return _("The version of SpamBayes running")

class TrainingStatusProcessor(ControlProcessor):
    def Init(self):
        bayes = self.window.manager.classifier_data.bayes
        nspam = bayes.nspam
        nham = bayes.nham
        if nspam > 10 and nham > 10:
            db_status = _("Database has %d good and %d spam.") % (nham, nspam)
            db_ratio = nham/float(nspam)
            big = small = None
            if db_ratio > 5.0:
                db_status = _("%s\nWarning: you have much more ham than spam - " \
                            "SpamBayes works best with approximately even " \
                            "numbers of ham and spam.") % (db_status, )
            elif db_ratio < (1/5.0):
                db_status = _("%s\nWarning: you have much more spam than ham - " \
                            "SpamBayes works best with approximately even " \
                            "numbers of ham and spam.") % (db_status, )
        elif nspam > 0 or nham > 0:
            db_status = _("Database only has %d good and %d spam - you should " \
                        "consider performing additional training.") % (nham, nspam)
        else:
            db_status = _("Database has no training information.  SpamBayes " \
                        "will classify all messages as 'unsure', " \
                        "ready for you to train.")
        win32gui.SendMessage(self.GetControl(), win32con.WM_SETTEXT,
                             0, db_status)

class WizardTrainingStatusProcessor(ControlProcessor):
    def Init(self):
        bayes = self.window.manager.classifier_data.bayes
        nspam = bayes.nspam
        nham = bayes.nham
        if nspam > 10 and nham > 10:
            msg = _("SpamBayes has been successfully trained and configured.  " \
                  "You should find the system is immediately effective at " \
                  "filtering spam.")
        else:
            msg = _("SpamBayes has been successfully trained and configured.  " \
                  "However, as the number of messages trained is quite small, " \
                  "SpamBayes may take some time to become truly effective.")
        win32gui.SendMessage(self.GetControl(), win32con.WM_SETTEXT,
                             0, msg)

class IntProcessor(OptionControlProcessor):
    def UpdateControl_FromValue(self):
        win32gui.SendMessage(self.GetControl(), win32con.WM_SETTEXT, 0, str(self.option.get()))
    def UpdateValue_FromControl(self):
        buf_size = 100
        buf = win32gui.PyMakeBuffer(buf_size)
        nchars = win32gui.SendMessage(self.GetControl(), win32con.WM_GETTEXT,
                                      buf_size, buf)
        str_val = buf[:nchars]
        val = int(str_val)
        if val < 0 or val > 10:
            raise ValueError, "Value must be between 0 and 10"
        self.SetOptionValue(val)
    def OnCommand(self, wparam, lparam):
        code = win32api.HIWORD(wparam)
        if code==win32con.EN_CHANGE:
            try:
                self.UpdateValue_FromControl()
            except ValueError:
                # They are typing - value may be currently invalid
                pass

class FilterEnableProcessor(BoolButtonProcessor):
    def OnOptionChanged(self, option):
        self.Init()

    def Init(self):
        BoolButtonProcessor.Init(self)
        reason = self.window.manager.GetDisabledReason()
        win32gui.EnableWindow(self.GetControl(), reason is None)

    def UpdateValue_FromControl(self):
        check = win32gui.SendMessage(self.GetControl(), win32con.BM_GETCHECK)
        if check:
            reason = self.window.manager.GetDisabledReason()
            if reason is not None:
                win32gui.SendMessage(self.GetControl(), win32con.BM_SETCHECK, 0)
                raise ValueError, reason
        check = not not check # force bool!
        self.SetOptionValue(check)

class FilterStatusProcessor(ControlProcessor):
    def OnOptionChanged(self, option):
        self.Init()

    def Init(self):
        manager = self.window.manager
        reason = manager.GetDisabledReason()
        if reason is not None:
            win32gui.SendMessage(self.GetControl(), win32con.WM_SETTEXT,
                                 0, reason)
            return
        if not manager.config.filter.enabled:
            status = _("Filtering is disabled.  Select 'Enable SpamBayes' to enable.")
            win32gui.SendMessage(self.GetControl(), win32con.WM_SETTEXT,
                                 0, status)
            return
        # ok, enabled and working - put together the status text.
        config = manager.config.filter
        certain_spam_name = manager.FormatFolderNames(
                                    [config.spam_folder_id], False)
        if config.unsure_folder_id:
            unsure_name = manager.FormatFolderNames(
                                    [config.unsure_folder_id], False)
            unsure_text = _("Unsure managed in '%s'") % (unsure_name,)
        else:
            unsure_text = _("Unsure messages untouched")
        if config.ham_folder_id:
            ham_name = manager.FormatFolderNames(
                                    [config.ham_folder_id], False)
            ham_text = _("Good managed in '%s'") % (ham_name,)
        else:
            ham_text = _("Good messages untouched")

        watch_names = manager.FormatFolderNames(
                        config.watch_folder_ids, config.watch_include_sub)
        filter_status = _("Watching '%s'.\r\n%s.\r\nSpam managed in '%s'.\r\n%s.") \
                                % (watch_names,
                                   ham_text,
                                   certain_spam_name,
                                   unsure_text)
        win32gui.SendMessage(self.GetControl(), win32con.WM_SETTEXT,
                             0, filter_status)

class TabProcessor(ControlProcessor):
    def __init__(self, window, control_ids, page_ids):
        ControlProcessor.__init__(self, window, control_ids)
        self.page_ids = page_ids.split()

    def Init(self):
        self.pages = {}
        self.currentPage = None
        self.currentPageIndex = -1
        self.currentPageHwnd = None
        for index, page_id in enumerate(self.page_ids):
            template = self.window.manager.dialog_parser.dialogs[page_id]
            self.addPage(index, page_id, template[0][0])
        self.switchToPage(0)

    def Done(self):
        if self.currentPageHwnd is not None:
            if not self.currentPage.SaveAllControls():
                win32gui.SendMessage(self.GetControl(), commctrl.TCM_SETCURSEL, self.currentPageIndex,0)
                return False
        return True

    def OnNotify(self, nmhdr, wparam, lparam):
        # this does not appear to be in commctrl module
        selChangedCode =  5177342
        code = nmhdr[2]
        if code==selChangedCode:
            index = win32gui.SendMessage(self.GetControl(), commctrl.TCM_GETCURSEL, 0,0)
            if index!=self.currentPageIndex:
                self.switchToPage(index)

    def switchToPage(self, index):
        if self.currentPageHwnd is not None:
            if not self.currentPage.SaveAllControls():
                win32gui.SendMessage(self.GetControl(), commctrl.TCM_SETCURSEL, self.currentPageIndex,0)
                return 1
            win32gui.DestroyWindow(self.currentPageHwnd)
        self.currentPage = MakePropertyPage(self.GetControl(), self.window.manager, self.window.config, self.pages[index])
        self.currentPageHwnd = self.currentPage.CreateWindow()
        self.currentPageIndex = index
        return 0

    def addPage(self, item, idName, label):
        format = "iiiiiii"
        lbuf = win32gui.PyMakeBuffer(len(label)+1)
        address,l = win32gui.PyGetBufferAddressAndLen(lbuf)
        win32gui.PySetString(address, label)

        buf = struct.pack(format,
            commctrl.TCIF_TEXT, # mask
            0, # state
            0, # state mask
            address,
            0, #unused
            0, #image
            item
            )
        item = win32gui.SendMessage(self.GetControl(),
                             commctrl.TCM_INSERTITEM,
                             item,
                             buf)
        self.pages[item] = idName


def ShowAbout(window):
    """Opens the SpamBayes documentation in a browser"""
    window.manager.ShowHtml("about.html")
def ShowTrainingDoc(window):
    """Opens documentation on SpamBayes training in a browser"""
    window.manager.ShowHtml("docs/welcome.html")
def ShowDataFolder(window):
    """Uses Windows Explorer to show where SpamBayes data and configuration
    files are stored
    """
    import os
    import sys
    filesystem_encoding = sys.getfilesystemencoding()
    os.startfile(window.manager.data_directory.encode(filesystem_encoding))
def ShowLog(window):
    """Opens the log file for the current SpamBayes session
    """
    import sys, os, win32api, win32con
    if hasattr(sys, "frozen"):
        # current log always "spambayes1.log"
        log_name = os.path.join(win32api.GetTempPath(), "spambayes1.log")
        if not os.path.exists(log_name):
            window.manager.ReportError(_("The log file for this session can not be located"))
        else:
            cmd = 'notepad.exe "%s"' % log_name
            win32api.WinExec(cmd, win32con.SW_SHOW)
    else:
        question = _("As you are running from source-code, viewing the\n" \
                   "log means executing a Python program.  If you already\n" \
                   "have a viewer running, the output may appear in either.\n\n"\
                   "Do you want to execute this viewer?")
        if not window.manager.AskQuestion(question):
            return
        # source-code users - fire up win32traceutil.py
        import win32traceutil # will already be imported
        py_name = win32traceutil.__file__
        if py_name[-1] in 'co': # pyc/pyo
            py_name = py_name[:-1]
        # execute the .py file - hope that this will manage to invoke
        # python.exe for it.  If this breaks for you, feel free to send me
        # a patch :)
        os.system('start ' + win32api.GetShortPathName(py_name))

def ResetConfig(window):
    question = _("This will reset all configuration options to their default values\r\n\r\n" \
               "It will not reset the folders you have selected, nor your\r\n" \
               "training information, but all other options will be reset\r\n" \
               "and SpamBayes will need to be re-enabled before it will\r\n" \
               "continue filtering.\r\n\r\n" \
               "Are you sure you wish to reset all options?")
    flags = win32con.MB_ICONQUESTION | win32con.MB_YESNO | win32con.MB_DEFBUTTON2
    if win32gui.MessageBox(window.hwnd,
                           question, "SpamBayes",flags) == win32con.IDYES:
        options = window.config._options
        for sect in options.sections():
            for opt_name in options.options_in_section(sect):
                opt = options.get_option(sect, opt_name)
                if not opt.no_restore():
                    assert opt.is_valid(opt.default_value), \
                           "Resetting '%s' to invalid default %r" % (opt.display_name(), opt.default_value)
                    opt.set(opt.default_value)
        window.LoadAllControls()


class DialogCommand(ButtonProcessor):
    def __init__(self, window, control_ids, idd):
        self.idd = idd
        ButtonProcessor.__init__(self, window, control_ids)
    def OnClicked(self, id):
        parent = self.window.hwnd
        # This form and the other form may "share" options, or at least
        # depend on others.  So we must save the current form back to the
        # options object, display the new dialog, then reload the current
        # form from the options object/
        self.window.SaveAllControls()
        ShowDialog(parent, self.window.manager, self.window.config, self.idd)
        self.window.LoadAllControls()

    def GetPopupHelpText(self, id):
        dd = self.window.manager.dialog_parser.dialogs[self.idd]
        return _("Displays the %s dialog") % dd.caption

class HiddenDialogCommand(DialogCommand):
    def __init__(self, window, control_ids, idd):
        DialogCommand.__init__(self, window, control_ids, idd)
    def Init(self):
        DialogCommand.Init(self)
        # Hide it
        win32gui.SetWindowText(self.GetControl(), "")
    def OnCommand(self, wparam, lparam):
        pass
    def OnRButtonUp(self, wparam, lparam):
        self.OnClicked(0)
    def GetPopupHelpText(self, id):
        return _("Nothing to see here.")

class ShowWizardCommand(DialogCommand):
    def OnClicked(self, id):
        import win32con
        existing = self.window
        manager = self.window.manager
        # Kill the main dialog - but first have to find it!
        dlg = self.window.hwnd
        while dlg:
            style = win32api.GetWindowLong(dlg, win32con.GWL_STYLE)
            if not style & win32con.WS_CHILD:
                break
            dlg = win32gui.GetParent(dlg)
        else:
            assert 0, "no parent!"

        try:
            parent = win32gui.GetParent(dlg)
        except win32gui.error:
            parent = 0 # no parent
        win32gui.EndDialog(dlg, win32con.IDOK)
        # And show the wizard.
        ShowWizard(parent, manager, self.idd, use_existing_config = True)

def WizardFinish(mgr, window):
    print _("Wizard Done!")

def WizardTrainer(mgr, config, progress):
    import os, manager, train
    bayes_base = os.path.join(mgr.data_directory, "$sbwiz$default_bayes_database")
    mdb_base = os.path.join(mgr.data_directory, "$sbwiz$default_message_database")
    fnames = []
    for ext in ".pck", ".db":
        fnames.append(bayes_base+ext)
        fnames.append(mdb_base+ext)
    config.wizard.temp_training_names = fnames
    # determine which db manager to use, and create it.
    ManagerClass = manager.GetStorageManagerClass()
    db_manager = ManagerClass(bayes_base, mdb_base)
    classifier_data = manager.ClassifierData(db_manager, mgr)
    classifier_data.InitNew()

    rescore = config.training.rescore

    if rescore:
        stages = (_("Training"), .3), (_("Saving"), .1), (_("Scoring"), .6)
    else:
        stages = (_("Training"), .9), (_("Saving"), .1)
    progress.set_stages(stages)

    train.real_trainer(classifier_data, config, mgr.message_store, progress)

    # xxx - more hacks - we should pass the classifier data in.
    orig_classifier_data = mgr.classifier_data
    mgr.classifier_data = classifier_data # temporary
    try:
        progress.tick()

        if rescore:
            # Setup the "filter now" config to what we want.
            now_config = config.filter_now
            now_config.only_unread = False
            now_config.only_unseen = False
            now_config.action_all = False
            now_config.folder_ids = config.training.ham_folder_ids + \
                                    config.training.spam_folder_ids
            now_config.include_sub = config.training.ham_include_sub or \
                                     config.training.spam_include_sub
            import filter
            filter.filterer(mgr, config, progress)

        bayes = classifier_data.bayes
        progress.set_status(_("Completed training with %d spam and %d good messages") \
                            % (bayes.nspam, bayes.nham))
    finally:
        mgr.wizard_classifier_data = classifier_data
        mgr.classifier_data = orig_classifier_data

from async_processor import AsyncCommandProcessor
import filter, train

dialog_map = {
    "IDD_MANAGER" : (
        (CloseButtonProcessor,    "IDOK IDCANCEL"),
        (TabProcessor,            "IDC_TAB",
                                  """IDD_GENERAL IDD_FILTER IDD_TRAINING
                                  IDD_STATISTICS IDD_NOTIFICATIONS
                                  IDD_ADVANCED"""),
        (CommandButtonProcessor,  "IDC_ABOUT_BTN", ShowAbout, ()),
    ),
    "IDD_GENERAL": (
        (ImageProcessor,          "IDC_LOGO_GRAPHIC"),
        (VersionStringProcessor,  "IDC_VERSION"),
        (TrainingStatusProcessor, "IDC_TRAINING_STATUS"),
        (FilterEnableProcessor,   "IDC_BUT_FILTER_ENABLE", "Filter.enabled"),
        (FilterStatusProcessor,   "IDC_FILTER_STATUS"),
        (ShowWizardCommand,       "IDC_BUT_WIZARD", "IDD_WIZARD"),
        (CommandButtonProcessor,  "IDC_BUT_RESET", ResetConfig, ()),
        ),
    "IDD_FILTER_NOW" : (
        (CloseButtonProcessor,    "IDCANCEL"),
        (BoolButtonProcessor,     "IDC_BUT_UNREAD",    "Filter_Now.only_unread"),
        (BoolButtonProcessor,     "IDC_BUT_UNSEEN",    "Filter_Now.only_unseen"),
        (BoolButtonProcessor,     "IDC_BUT_ACT_ALL IDC_BUT_ACT_SCORE",
                                                       "Filter_Now.action_all"),
        (FolderIDProcessor,       "IDC_FOLDER_NAMES IDC_BROWSE",
                                  "Filter_Now.folder_ids",
                                  "Filter_Now.include_sub"),
        (AsyncCommandProcessor,   "IDC_START IDC_PROGRESS IDC_PROGRESS_TEXT",
                                  filter.filterer,
                                  _("Start Filtering"), _("Stop Filtering"),
                                  """IDCANCEL IDC_BUT_UNSEEN
                                  IDC_BUT_UNREAD IDC_BROWSE IDC_BUT_ACT_SCORE
                                  IDC_BUT_ACT_ALL"""),
    ),
    "IDD_FILTER" : (
        (FolderIDProcessor,       "IDC_FOLDER_WATCH IDC_BROWSE_WATCH",
                                  "Filter.watch_folder_ids",
                                  "Filter.watch_include_sub"),
        (ComboProcessor,          "IDC_ACTION_CERTAIN", "Filter.spam_action",
                                  _("Untouched,Moved,Copied")),
        (FolderIDProcessor,       "IDC_FOLDER_CERTAIN IDC_BROWSE_CERTAIN",
                                  "Filter.spam_folder_id"),
        (EditNumberProcessor,     "IDC_EDIT_CERTAIN IDC_SLIDER_CERTAIN",
                                  "Filter.spam_threshold"),
        (BoolButtonProcessor,     "IDC_MARK_SPAM_AS_READ",    "Filter.spam_mark_as_read"),
        (FolderIDProcessor,       "IDC_FOLDER_UNSURE IDC_BROWSE_UNSURE",
                                  "Filter.unsure_folder_id"),
        (EditNumberProcessor,     "IDC_EDIT_UNSURE IDC_SLIDER_UNSURE",
                                  "Filter.unsure_threshold"),
        (ComboProcessor,          "IDC_ACTION_UNSURE", "Filter.unsure_action",
                                  _("Untouched,Moved,Copied")),
        (BoolButtonProcessor,     "IDC_MARK_UNSURE_AS_READ",    "Filter.unsure_mark_as_read"),
        (FolderIDProcessor,       "IDC_FOLDER_HAM IDC_BROWSE_HAM",
                                  "Filter.ham_folder_id"),
        (ComboProcessor,          "IDC_ACTION_HAM", "Filter.ham_action",
                                  _("Untouched,Moved,Copied")),
        ),
    "IDD_TRAINING" : (
        (FolderIDProcessor,       "IDC_STATIC_HAM IDC_BROWSE_HAM",
                                  "Training.ham_folder_ids",
                                  "Training.ham_include_sub"),
        (FolderIDProcessor,       "IDC_STATIC_SPAM IDC_BROWSE_SPAM",
                                  "Training.spam_folder_ids",
                                  "Training.spam_include_sub"),
        (BoolButtonProcessor,     "IDC_BUT_RESCORE",    "Training.rescore"),
        (BoolButtonProcessor,     "IDC_BUT_REBUILD",    "Training.rebuild"),
        (AsyncCommandProcessor,   "IDC_START IDC_PROGRESS IDC_PROGRESS_TEXT",
                                  train.trainer, _("Start Training"), _("Stop"),
                                  "IDOK IDCANCEL IDC_BROWSE_HAM IDC_BROWSE_SPAM " \
                                  "IDC_BUT_REBUILD IDC_BUT_RESCORE"),
        (BoolButtonProcessor,     "IDC_BUT_TRAIN_FROM_SPAM_FOLDER",
                                  "Training.train_recovered_spam"),
        (BoolButtonProcessor,     "IDC_BUT_TRAIN_TO_SPAM_FOLDER",
                                  "Training.train_manual_spam"),
        (ComboProcessor,          "IDC_DEL_SPAM_RS", "General.delete_as_spam_message_state",
         _("not change the message,mark the message as read,mark the message as unread")),
        (ComboProcessor,          "IDC_RECOVER_RS", "General.recover_from_spam_message_state",
         _("not change the message,mark the message as read,mark the message as unread")),

    ),
    "IDD_STATISTICS" : (
        (StatsProcessor,        "IDC_STATISTICS IDC_BUT_RESET_STATS " \
                                "IDC_LAST_RESET_DATE"),
        ),
    "IDD_NOTIFICATIONS" : (
        (BoolButtonProcessor,   "IDC_ENABLE_SOUNDS",     "Notification.notify_sound_enabled",
                                """IDC_HAM_SOUND IDC_BROWSE_HAM_SOUND
                                   IDC_UNSURE_SOUND IDC_BROWSE_UNSURE_SOUND
                                   IDC_SPAM_SOUND IDC_BROWSE_SPAM_SOUND
                                   IDC_ACCUMULATE_DELAY_SLIDER
                                   IDC_ACCUMULATE_DELAY_TEXT"""),
        (FilenameProcessor,     "IDC_HAM_SOUND IDC_BROWSE_HAM_SOUND",
                                "Notification.notify_ham_sound", _("Sound Files (*.wav)|*.wav|All Files (*.*)|*.*")),
        (FilenameProcessor,     "IDC_UNSURE_SOUND IDC_BROWSE_UNSURE_SOUND",
                                "Notification.notify_unsure_sound", _("Sound Files (*.wav)|*.wav|All Files (*.*)|*.*")),
        (FilenameProcessor,     "IDC_SPAM_SOUND IDC_BROWSE_SPAM_SOUND",
                                "Notification.notify_spam_sound", _("Sound Files (*.wav)|*.wav|All Files (*.*)|*.*")),
        (EditNumberProcessor,   "IDC_ACCUMULATE_DELAY_TEXT IDC_ACCUMULATE_DELAY_SLIDER",
                                "Notification.notify_accumulate_delay", 0, 30, 20, 60),
        ),
    "IDD_ADVANCED" : (
        (BoolButtonProcessor,   "IDC_BUT_TIMER_ENABLED", "Filter.timer_enabled",
                                """IDC_DELAY1_TEXT IDC_DELAY1_SLIDER
                                   IDC_DELAY2_TEXT IDC_DELAY2_SLIDER
                                   IDC_INBOX_TIMER_ONLY"""),
        (EditNumberProcessor,   "IDC_DELAY1_TEXT IDC_DELAY1_SLIDER", "Filter.timer_start_delay", 0, 10, 20, 60),
        (EditNumberProcessor,   "IDC_DELAY2_TEXT IDC_DELAY2_SLIDER", "Filter.timer_interval", 0, 10, 20, 60),
        (BoolButtonProcessor,   "IDC_INBOX_TIMER_ONLY", "Filter.timer_only_receive_folders"),
        (CommandButtonProcessor,  "IDC_SHOW_DATA_FOLDER", ShowDataFolder, ()),
        (DialogCommand,         "IDC_BUT_SHOW_DIAGNOSTICS", "IDD_DIAGNOSTIC"),
        ),
    "IDD_DIAGNOSTIC" : (
        (BoolButtonProcessor,     "IDC_SAVE_SPAM_SCORE",    "Filter.save_spam_info"),
        (IntProcessor,   "IDC_VERBOSE_LOG",  "General.verbose"),
        (CommandButtonProcessor, "IDC_BUT_VIEW_LOG", ShowLog, ()),
        (CloseButtonProcessor,    "IDOK IDCANCEL"),
        ),
    # All the wizards
    "IDD_WIZARD": (
        (ImageProcessor,          "IDC_WIZ_GRAPHIC"),
        (CloseButtonProcessor,  "IDCANCEL"),
        (wiz.ConfigureWizardProcessor, "IDC_FORWARD_BTN IDC_BACK_BTN IDC_PAGE_PLACEHOLDER",
         """IDD_WIZARD_WELCOME IDD_WIZARD_FOLDERS_WATCH IDD_WIZARD_FOLDERS_REST
         IDD_WIZARD_FOLDERS_TRAIN IDD_WIZARD_TRAIN
         IDD_WIZARD_TRAINING_IS_IMPORTANT
         IDD_WIZARD_FINISHED_UNCONFIGURED IDD_WIZARD_FINISHED_UNTRAINED
         IDD_WIZARD_FINISHED_TRAINED IDD_WIZARD_FINISHED_TRAIN_LATER
         """,
         WizardFinish),
        ),
    "IDD_WIZARD_WELCOME": (
        (CommandButtonProcessor,  "IDC_BUT_ABOUT", ShowAbout, ()),
        (RadioButtonProcessor,    "IDC_BUT_PREPARATION", "Wizard.preparation"),
        ),
    "IDD_WIZARD_TRAINING_IS_IMPORTANT" : (
        (BoolButtonProcessor,     "IDC_BUT_TRAIN IDC_BUT_UNTRAINED",    "Wizard.will_train_later"),
        (CommandButtonProcessor,  "IDC_BUT_ABOUT", ShowTrainingDoc, ()),
    ),
    "IDD_WIZARD_FOLDERS_REST": (
        (wiz.EditableFolderIDProcessor,"IDC_FOLDER_CERTAIN IDC_BROWSE_SPAM",
                                      "Filter.spam_folder_id", "Wizard.spam_folder_name",
                                      "Training.spam_folder_ids"),
        (wiz.EditableFolderIDProcessor,"IDC_FOLDER_UNSURE IDC_BROWSE_UNSURE",
                                      "Filter.unsure_folder_id", "Wizard.unsure_folder_name"),
    ),
    "IDD_WIZARD_FOLDERS_WATCH": (
        (wiz.WatchFolderIDProcessor,"IDC_FOLDER_WATCH IDC_BROWSE_WATCH",
                                    "Filter.watch_folder_ids"),
    ),
    "IDD_WIZARD_FOLDERS_TRAIN": (
        (wiz.TrainFolderIDProcessor,"IDC_FOLDER_HAM IDC_BROWSE_HAM",
                                    "Training.ham_folder_ids"),
        (wiz.TrainFolderIDProcessor,"IDC_FOLDER_CERTAIN IDC_BROWSE_SPAM",
                                    "Training.spam_folder_ids"),
        (BoolButtonProcessor,     "IDC_BUT_RESCORE",    "Training.rescore"),

    ),
    "IDD_WIZARD_TRAIN" : (
        (wiz.WizAsyncProcessor,   "IDC_PROGRESS IDC_PROGRESS_TEXT",
                                  WizardTrainer, "", "",
                                  ""),
    ),
    "IDD_WIZARD_FINISHED_UNCONFIGURED": (
    ),
    "IDD_WIZARD_FINISHED_UNTRAINED": (
    ),
    "IDD_WIZARD_FINISHED_TRAINED": (
        (WizardTrainingStatusProcessor, "IDC_TRAINING_STATUS"),
    ),
    "IDD_WIZARD_FINISHED_TRAIN_LATER" : (
    ),
}
