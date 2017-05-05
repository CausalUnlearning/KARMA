# Control Processors for our wizard

# This module is part of the spambayes project, which is Copyright 2003
# The Python Software Foundation and is covered by the Python Software
# Foundation license.

import win32gui, win32con, win32api, commctrl
from dialogs import ShowDialog, MakePropertyPage

import processors
import opt_processors
import async_processor

import timer

# An "abstract" wizard class.  Not technically abstract - this version
# supports sequential stepping through all the pages.  It is expected
# sub-classes will override "getNextPage" and "atFinish" to provide a
# custom navigation path.
class WizardButtonProcessor(processors.ButtonProcessor):
    def __init__(self, window, control_ids, pages, finish_fn):
        processors.ButtonProcessor.__init__(self, window,control_ids)
        self.back_btn_id = self.other_ids[0]
        self.page_ids = pages.split()
        self.currentPage = None
        self.currentPageIndex = -1
        self.currentPageHwnd = None
        self.finish_fn = finish_fn
        self.page_placeholder_id = self.other_ids[1]

    def Init(self):
        processors.ButtonProcessor.Init(self)
        self.back_btn_hwnd = self.GetControl(self.back_btn_id)
        self.forward_btn_hwnd = self.GetControl()
        self.forward_captions = win32gui.GetWindowText(self.forward_btn_hwnd).split(",")
        self.page_placeholder_hwnd = self.GetControl(self.page_placeholder_id)
        self.page_stack = []
        self.switchToPage(0)
        # brute-force timer to check if we can move forward.
        self.timer_id = timer.set_timer(800, self.OnCheckForwardTimer)

    def Done(self):
        if self.timer_id is not None:
            timer.kill_timer(self.timer_id)
            self.timer_id = None
        return processors.ButtonProcessor.Done(self)

    def changeControls(self):
        win32gui.EnableWindow(self.back_btn_hwnd,self.currentPageIndex!=0)
        if self.canGoNext():
            enabled = 1
        else:
            enabled = 0
        win32gui.EnableWindow(self.forward_btn_hwnd,enabled)
        index = 0
        if self.atFinish():
            index = 1
        win32gui.SetWindowText(self.forward_btn_hwnd, self.forward_captions[index])

    # No obvious way to communicate the state of what the "Forward" button
    # should be.  brute-force - check a config boolean on a timer.
    def OnCheckForwardTimer(self, event, time):
        #print "Timer fired"
        if self.canGoNext():
            enabled = 1
        else:
            enabled = 0
        win32gui.EnableWindow(self.forward_btn_hwnd,enabled)

    def OnClicked(self, id):
        if id == self.control_id:
            if self.atFinish():
                if not self.currentPage.SaveAllControls():
                    return
                #finish
                win32gui.EnableWindow(self.forward_btn_hwnd, False)
                win32gui.EnableWindow(self.back_btn_hwnd, False)
                try:
                    #optional
                    h = GetControl(self.window.manager.dialog_parser.ids["IDCANCEL"])
                    win32gui.EnableWindow(h, False)
                except:
                    pass

                self.finish_fn(self.window.manager, self.window)
                win32gui.EndDialog(self.window.hwnd, win32con.IDOK)
            else:
                #forward
                if self.canGoNext() and self.currentPage.SaveAllControls():
                    self.page_stack.append(self.currentPageIndex)
                    nextPage = self.getNextPageIndex()
                    self.switchToPage(nextPage)
        elif id == self.back_btn_id:
            #backward
            assert self.page_stack, "Back should be disabled when no back stack"
            pageNo = self.page_stack.pop()
            print "Back button switching to page", pageNo
            self.switchToPage(pageNo)

    def switchToPage(self, index):
        if self.currentPageHwnd is not None:
            if not self.currentPage.SaveAllControls():
                return 1
            win32gui.DestroyWindow(self.currentPageHwnd)
        #template = self.window.manager.dialog_parser.dialogs[self.page_ids[index]]
        import dlgcore
        self.currentPage = MakePropertyPage(self.page_placeholder_hwnd,
                                            self.window.manager,
                                            self.window.config,
                                            self.page_ids[index],
                                            3)
        self.currentPageHwnd = self.currentPage.CreateWindow()
        self.currentPageIndex = index
        self.changeControls()
        return 0
    def getNextPageIndex(self):
        next = self.getNextPage()
        if type(next)==type(0):
            return next
        # must be a dialog ID.
        for index, pid in enumerate(self.page_ids):
            if pid == next:
                return index
        assert 0, "No page '%s'" % next

    # methods to be overridden.  default implementation is simple sequential
    def getNextPage(self):
        return self.currentPageIndex+1
    def atFinish(self):
        return self.currentPageIndex==len(self.page_ids)-1
    def canGoNext(self):
        return True

# An implementation with the logic specific to our configuration wizard.
class ConfigureWizardProcessor(WizardButtonProcessor):
    def atFinish(self):
        index = self.currentPageIndex
        id = self.page_ids[index]
        return id.startswith("IDD_WIZARD_FINISHED")

    def canGoNext(self):
        # XXX - how to hook this in?  We really want this to be dynamic, as
        # options change - however, hooking WM_COMMAND at the parent doesn't
        # work how we want due to the property page being in the middle
        # (and then I gave up)
        index = self.currentPageIndex
        id = self.page_ids[index]
        config = self.window.config
        ok = True
        if id == 'IDD_WIZARD_FOLDERS_WATCH':
            ok = config.filter.watch_folder_ids
        elif id == 'IDD_WIZARD_FOLDERS_REST':
            # Check we have folders.
            ok = (config.wizard.spam_folder_name or config.filter.spam_folder_id) and \
               (config.wizard.unsure_folder_name or config.filter.unsure_folder_id)
        elif id == 'IDD_WIZARD_FOLDERS_TRAIN':
            ok = config.training.ham_folder_ids and \
                 config.training.spam_folder_ids
        elif id == 'IDD_WIZARD_TRAIN':
            # magically set to False when training finished (and back to True
            # if a folder ID is changed)
            ok = not self.window.config.wizard.need_train
        return ok

    def getNextPage(self):
        index = self.currentPageIndex
        id = self.page_ids[index]
        config = self.window.config
        print "GetNextPage with current", index, id
        if id == 'IDD_WIZARD_WELCOME':
            # Welcome page
            if config.wizard.preparation == 0: # unprepared
                return "IDD_WIZARD_TRAINING_IS_IMPORTANT"
            elif config.wizard.preparation == 1: # pre-prepared.
                return "IDD_WIZARD_FOLDERS_TRAIN"
            elif config.wizard.preparation == 2: # configure manually
                return "IDD_WIZARD_FINISHED_UNCONFIGURED"
            else:
                assert 0, "oops"
        elif id == 'IDD_WIZARD_TRAINING_IS_IMPORTANT':
            if config.wizard.will_train_later:
                # user wants to pre-sort and configure later.
                return 'IDD_WIZARD_FINISHED_TRAIN_LATER'
            return 'IDD_WIZARD_FOLDERS_WATCH'
        elif id == 'IDD_WIZARD_FOLDERS_TRAIN':
            return 'IDD_WIZARD_TRAIN'
        elif id == 'IDD_WIZARD_TRAIN':
            return 'IDD_WIZARD_FOLDERS_WATCH'
        elif id == 'IDD_WIZARD_FOLDERS_WATCH':
            return 'IDD_WIZARD_FOLDERS_REST'
        elif id == 'IDD_WIZARD_FOLDERS_REST':
            if config.wizard.preparation==1:
                return 'IDD_WIZARD_FINISHED_TRAINED'
            else:
                return 'IDD_WIZARD_FINISHED_UNTRAINED'

class WatchFolderIDProcessor(opt_processors.FolderIDProcessor):
    def __init__(self, window, control_ids,
                 option, option_include_sub = None,
                 use_fqn = True,
                 name_joiner = '\r\n'):
        opt_processors.FolderIDProcessor.__init__(self, window, control_ids,
                                                  option, option_include_sub,
                                                  use_fqn, name_joiner)

# For the wizard - folder "name" in an edit box, and ids used by
# browse dialog.  If ids None, "name" is assumed off the root, and created
# if necessary.
class EditableFolderIDProcessor(opt_processors.FolderIDProcessor):
    def __init__(self, window, control_ids,
                 option, option_folder_name, option_override = None,
                 use_fqn = False, name_joiner = "; "):
        self.button_id = control_ids[1]
        self.use_fqn = use_fqn
        self.name_joiner = name_joiner
        self.in_setting_name = False

        name_sect_name, name_sub_option_name = option_folder_name.split(".")

        self.option_folder_name = window.config.get_option(name_sect_name,
                                                            name_sub_option_name)
        if option_override:
            name_sect_name, name_sub_option_name = option_override.split(".")
            self.option_override = window.config.get_option(name_sect_name,
                                                            name_sub_option_name)
        else:
            self.option_override = None

        opt_processors.FolderIDProcessor.__init__(self, window, control_ids,
                                                  option, None,
                                                  use_fqn, name_joiner)

        # bit of a hack - if "Spam" is default and we have a training folder
        # then use that
        if self.GetOptionValue() is None and self.option_override:
            override = self.GetOptionValue(self.option_override)
            if override:
                # override is a multi-id value, we are single.
                self.SetOptionValue(override[0])
                self.SetOptionValue("", self.option_folder_name)

    def OnCommand(self, wparam, lparam):
        code = win32api.HIWORD(wparam)
        id = win32api.LOWORD(wparam)
        if id == self.control_id:
            if code==win32con.EN_CHANGE:
                if not self.in_setting_name:
                    # reset the folder IDs.
                    self.SetOptionValue(None)
                    # Set the folder name
                    hedit = win32gui.GetDlgItem(self.window.hwnd, id)
                    text = win32gui.GetWindowText(hedit)
                    self.SetOptionValue(text, self.option_folder_name)
        return opt_processors.FolderIDProcessor.OnCommand(self, wparam, lparam)

    def UpdateControl_FromValue(self):
        name_val = self.GetOptionValue(self.option_folder_name)
        id_val = self.GetOptionValue()
        self.in_setting_name = True
        if id_val:
            self.SetOptionValue("", self.option_folder_name)
            opt_processors.FolderIDProcessor.UpdateControl_FromValue(self)
        else:
            if name_val:
                win32gui.SetWindowText(self.GetControl(), name_val)
        self.in_setting_name = False

class TrainFolderIDProcessor(opt_processors.FolderIDProcessor):
    def SetOptionValue(self, value, option = None):
        self.window.config.wizard.need_train = True
        return opt_processors.FolderIDProcessor.SetOptionValue(self, value, option)

class WizAsyncProcessor(async_processor.AsyncCommandProcessor):
    def __init__(self, window, control_ids, func, start_text, stop_text, disable_ids):
        control_ids = [None] + control_ids
        async_processor.AsyncCommandProcessor.__init__(self, window, control_ids, func, start_text, stop_text, disable_ids)
    def Init(self):
        async_processor.AsyncCommandProcessor.Init(self)
        if self.window.config.wizard.need_train:
            self.StartProcess()
        else:
            self.SetStatusText("Training has already been completed - click Next to move to the next step.")
    def OnFinished(self, wparam, lparam):
        wasCancelled = wparam
        if not wasCancelled:
            self.window.config.wizard.need_train = False
        return async_processor.AsyncCommandProcessor.OnFinished(self, wparam, lparam)
