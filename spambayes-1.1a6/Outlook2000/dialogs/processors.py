# Control Processors for our dialog.

# This module is part of the spambayes project, which is Copyright 2003
# The Python Software Foundation and is covered by the Python Software
# Foundation license.

import win32gui, win32api, win32con
import commctrl
import struct, array
from dlgutils import *

# Cache our leaky bitmap handles
bitmap_handles = {}

# A generic set of "ControlProcessors".  A control processor by itself only
# does a few basic things.
class ControlProcessor:
    def __init__(self, window, control_ids):
        self.control_id = control_ids[0]
        self.other_ids = control_ids[1:]
        self.window = window
    def Init(self):
        pass
    def Done(self): # done with 'ok' - ie, save options.  May return false.
        return True
    def Term(self): # closing - can't fail.
        pass
    def GetControl(self, control_id = None):
        control_id = control_id or self.control_id
        try:
            h = win32gui.GetDlgItem(self.window.hwnd, control_id)
        except:
            hparent = win32gui.GetParent(self.window.hwnd)
            hparent = win32gui.GetParent(hparent)
            h = win32gui.GetDlgItem(hparent, control_id)
        return h
    def GetPopupHelpText(self, idFrom):
        return None
    def OnCommand(self, wparam, lparam):
        pass
    def OnNotify(self, nmhdr, wparam, lparam):
        pass
    def GetMessages(self):
        return []
    def OnMessage(self, msg, wparam, lparam):
        raise RuntimeError, "I don't hook any messages, so I shouldn't be called"
    def OnOptionChanged(self, option):
        pass
    def OnRButtonUp(self, wparam, lparam):
        pass

class ImageProcessor(ControlProcessor):
    def Init(self):
        rcp = self.window.manager.dialog_parser;
        bmp_id = int(win32gui.GetWindowText(self.GetControl()))

        if bitmap_handles.has_key(bmp_id):
            handle = bitmap_handles[bmp_id]
        else:
            import resources
            mod_handle, mod_bmp, extra_flags = resources.GetImageParamsFromBitmapID(rcp, bmp_id)
            load_flags = extra_flags|win32con.LR_COLOR|win32con.LR_SHARED
            handle = win32gui.LoadImage(mod_handle, mod_bmp,
                                        win32con.IMAGE_BITMAP,0,0,load_flags)
            bitmap_handles[bmp_id] = handle
        win32gui.SendMessage(self.GetControl(), win32con.STM_SETIMAGE, win32con.IMAGE_BITMAP, handle)

    def GetPopupHelpText(self, cid):
        return None

class ButtonProcessor(ControlProcessor):
    def OnCommand(self, wparam, lparam):
        code = win32api.HIWORD(wparam)
        id = win32api.LOWORD(wparam)
        if code == win32con.BN_CLICKED:
            self.OnClicked(id)

class CloseButtonProcessor(ButtonProcessor):
    def OnClicked(self, id):
        problem = self.window.manager.GetDisabledReason()
        if problem:
            q = _("There appears to be a problem with SpamBayes' configuration" \
                "\r\nIf you do not fix this problem, SpamBayes will be" \
                " disabled.\r\n\r\n%s" \
                "\r\n\r\nDo you wish to re-configure?") % (problem,)
            if self.window.manager.AskQuestion(q):
                return
        win32gui.EndDialog(self.window.hwnd, id)
    def GetPopupHelpText(self, ctrlid):
        return _("Closes this dialog")

class CommandButtonProcessor(ButtonProcessor):
    def __init__(self, window, control_ids, func, args):
        assert len(control_ids)==1
        self.func = func
        self.args = args
        ControlProcessor.__init__(self, window, control_ids)

    def OnClicked(self, id):
        # Bit of a hack - always pass the manager as the first arg.
        args = (self.window,) + self.args
        self.func(*args)

    def GetPopupHelpText(self, ctrlid):
        assert ctrlid == self.control_id
        doc = self.func.__doc__
        if doc is None:
            return ""
        return " ".join(doc.split())
