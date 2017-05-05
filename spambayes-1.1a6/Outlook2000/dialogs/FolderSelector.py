from __future__ import generators

import sys, os
import win32con
import commctrl
import win32api
import win32gui
import winerror

import struct, array

import dlgutils

from pprint import pprint # debugging only
verbose = 0

def INDEXTOSTATEIMAGEMASK(i): # from new commctrl.h
    return i << 12
IIL_UNCHECKED = 1
IIL_CHECKED = 2

# Helpers for building the folder list
class FolderSpec:
    def __init__(self, folder_id, name, ignore_eids = None):
        self.folder_id = folder_id
        self.name = name
        self.children = []
        self.ignore_eids = ignore_eids

    def dump(self, level=0):
        prefix = "  " * level
        print prefix + self.name
        for c in self.children:
            c.dump(level+1)

# Oh, lord help us.
# We started with a CDO version - but CDO sucks for lots of reasons I
# wont even start to mention.
# So we moved to an Extended MAPI version with is nice and fast - screams
# along!  Except it doesn't work in all cases with Exchange (which
# strikes Mark as extremely strange given that the Extended MAPI Python
# bindings were developed against an Exchange Server - but Mark doesn't
# have an Exchange server handy these days, and really doesn't give a
# rat's arse <wink>).
# So finally we have an Outlook object model version!
# But then Tony Meyer came to the rescue - he noticed that we were
# simply using short-term EID values for Exchange Folders - so now that
# is solved, we are back to the Extended MAPI version.

# These variants were deleted by MarkH - cvs is your friend :)
# Last appeared in Rev 1.10

#########################################################################
## An extended MAPI version
#########################################################################
from win32com.mapi import mapi, mapiutil
from win32com.mapi.mapitags import *
import pythoncom

def _BuildFoldersMAPI(manager, folder_spec):
    # This is called dynamically as folders are expanded.
    dlgutils.SetWaitCursor(1)
    folder = manager.message_store.GetFolder(folder_spec.folder_id).OpenEntry()
    # Get the hierarchy table for it.
    table = folder.GetHierarchyTable(0)
    children = []
    order = (((PR_DISPLAY_NAME_A, mapi.TABLE_SORT_ASCEND),),0,0)
    rows = mapi.HrQueryAllRows(table, (PR_ENTRYID,
                                       PR_STORE_ENTRYID,
                                       PR_DISPLAY_NAME_A), None, order, 0)
    if verbose:
        print "Rows for sub-folder of", folder_spec.name, "-", folder_spec.folder_id
        pprint(rows)
    for (eid_tag, eid),(storeeid_tag, store_eid), (name_tag, name) in rows:
        # Note the eid we get here is short-term - hence we must
        # re-fetch from the object itself (which is what our manager does,
        # so no need to do it explicitly - just believe folder.id over eid)
        ignore = False
        for check_eid in folder_spec.ignore_eids:
            if manager.message_store.session.CompareEntryIDs(check_eid, eid):
                ignore = True
                break
        if ignore:
            continue
        temp_id = mapi.HexFromBin(store_eid), mapi.HexFromBin(eid)
        try:
            # may get MsgStoreException for GetFolder, or
            # a mapi exception for the underlying MAPI stuff we then call.
            # Either way, just skip it.
            child_folder = manager.message_store.GetFolder(temp_id)
            spec = FolderSpec(child_folder.GetID(), name, folder_spec.ignore_eids)
            # If we have no children at all, indicate
            # the item is not expandable.
            table = child_folder.OpenEntry().GetHierarchyTable(0)
            if table.GetRowCount(0) == 0:
                spec.children = []
            else:
                spec.children = None # Flag as "not yet built"
            children.append(spec)
        except (pythoncom.com_error, manager.message_store.MsgStoreException), details:
            # Users have reported failure here - it is not clear if the
            # entire tree is going to fail, or just this folder
            print "** Unable to open child folder - ignoring"
            print details
    dlgutils.SetWaitCursor(0)
    return children

def BuildFolderTreeMAPI(session, ignore_ids):
    root = FolderSpec(None, "root")
    tab = session.GetMsgStoresTable(0)
    prop_tags = PR_ENTRYID, PR_DISPLAY_NAME_A
    rows = mapi.HrQueryAllRows(tab, prop_tags, None, None, 0)
    if verbose:
        print "message store rows:"
        pprint(rows)
    for row in rows:
        (eid_tag, eid), (name_tag, name) = row
        hex_eid = mapi.HexFromBin(eid)
        try:
            msgstore = session.OpenMsgStore(0, eid, None, mapi.MDB_NO_MAIL |
                                                          mapi.MAPI_DEFERRED_ERRORS)
            hr, data = msgstore.GetProps((PR_IPM_SUBTREE_ENTRYID,)+ignore_ids, 0)
            # It appears that not all stores have a subtree.
            if PROP_TYPE(data[0][0]) != PT_BINARY:
                print "FolderSelector dialog found message store without a subtree - ignoring"
                continue
            subtree_eid = data[0][1]
            ignore_eids = [item[1] for item in data[1:] if PROP_TYPE(item[0])==PT_BINARY]
        except pythoncom.com_error, details:
            # Handle 'expected' errors.
            if details[0]== mapi.MAPI_E_FAILONEPROVIDER:
                print "A message store is temporarily unavailable - " \
                      "it will not appear in the Folder Selector dialog"
            else:
                # Some weird error opening a folder tree
                # Just print a warning and ignore the tree.
                print "Failed to open a message store for the FolderSelector dialog"
                print "Exception details:", details
            continue
        folder_id = hex_eid, mapi.HexFromBin(subtree_eid)
        if verbose:
            print "message store root folder id is", folder_id

        spec = FolderSpec(folder_id, name, ignore_eids)
        spec.children = None
        root.children.append(spec)
    return root

# XXX - Note - the following structure code has been copied into the new
# XXX - win32gui_struct module.  One day we can rip this in preference
# XXX - for this new standard win32all module
# Helpers for the ugly win32 structure packing/unpacking
def _GetMaskAndVal(val, default, mask, flag):
    if val is None:
        return mask, default
    else:
        mask |= flag
        return mask, val

def PackTVINSERTSTRUCT(parent, insertAfter, tvitem):
    tvitem_buf, extra = PackTVITEM(*tvitem)
    tvitem_buf = tvitem_buf.tostring()
    format = "ii%ds" % len(tvitem_buf)
    return struct.pack(format, parent, insertAfter, tvitem_buf), extra

def PackTVITEM(hitem, state, stateMask, text, image, selimage, citems, param):
    extra = [] # objects we must keep references to
    mask = 0
    mask, hitem = _GetMaskAndVal(hitem, 0, mask, commctrl.TVIF_HANDLE)
    mask, state = _GetMaskAndVal(state, 0, mask, commctrl.TVIF_STATE)
    if not mask & commctrl.TVIF_STATE:
        stateMask = 0
    mask, text = _GetMaskAndVal(text, None, mask, commctrl.TVIF_TEXT)
    mask, image = _GetMaskAndVal(image, 0, mask, commctrl.TVIF_IMAGE)
    mask, selimage = _GetMaskAndVal(selimage, 0, mask, commctrl.TVIF_SELECTEDIMAGE)
    mask, citems = _GetMaskAndVal(citems, 0, mask, commctrl.TVIF_CHILDREN)
    mask, param = _GetMaskAndVal(param, 0, mask, commctrl.TVIF_PARAM)
    if text is None:
        text_addr = text_len = 0
    else:
        text_buffer = array.array("c", text+"\0")
        extra.append(text_buffer)
        text_addr, text_len = text_buffer.buffer_info()
    format = "iiiiiiiiii"
    buf = struct.pack(format,
                      mask, hitem,
                      state, stateMask,
                      text_addr, text_len, # text
                      image, selimage,
                      citems, param)
    return array.array("c", buf), extra

# Make a new buffer suitable for querying hitem's attributes.
def EmptyTVITEM(hitem, mask = None, text_buf_size=512):
    extra = [] # objects we must keep references to
    if mask is None:
        mask = commctrl.TVIF_HANDLE | commctrl.TVIF_STATE | commctrl.TVIF_TEXT | \
               commctrl.TVIF_IMAGE | commctrl.TVIF_SELECTEDIMAGE | \
               commctrl.TVIF_CHILDREN | commctrl.TVIF_PARAM
    if mask & commctrl.TVIF_TEXT:
        text_buffer = array.array("c", "\0" * text_buf_size)
        extra.append(text_buffer)
        text_addr, text_len = text_buffer.buffer_info()
    else:
        text_addr = text_len = 0
    format = "iiiiiiiiii"
    buf = struct.pack(format,
                      mask, hitem,
                      0, 0,
                      text_addr, text_len, # text
                      0, 0,
                      0, 0)
    return array.array("c", buf), extra

def UnpackTVItem(buffer):
    item_mask, item_hItem, item_state, item_stateMask, \
        item_textptr, item_cchText, item_image, item_selimage, \
        item_cChildren, item_param = struct.unpack("10i", buffer)
    # ensure only items listed by the mask are valid (except we assume the
    # handle is always valid - some notifications (eg, TVN_ENDLABELEDIT) set a
    # mask that doesn't include the handle, but the docs explicity say it is.)
    if not (item_mask & commctrl.TVIF_TEXT): item_textptr = item_cchText = None
    if not (item_mask & commctrl.TVIF_CHILDREN): item_cChildren = None
    if not (item_mask & commctrl.TVIF_IMAGE): item_image = None
    if not (item_mask & commctrl.TVIF_PARAM): item_param = None
    if not (item_mask & commctrl.TVIF_SELECTEDIMAGE): item_selimage = None
    if not (item_mask & commctrl.TVIF_STATE): item_state = item_stateMask = None

    if item_textptr:
        text = win32gui.PyGetString(item_textptr)
    else:
        text = None
    return item_hItem, item_state, item_stateMask, \
        text, item_image, item_selimage, \
        item_cChildren, item_param

def UnpackTVNOTIFY(lparam):
    format = "iiii40s40s"
    buf = win32gui.PyMakeBuffer(struct.calcsize(format), lparam)
    hwndFrom, id, code, action, buf_old, buf_new \
          = struct.unpack(format, buf)
    item_old = UnpackTVItem(buf_old)
    item_new = UnpackTVItem(buf_new)
    return hwndFrom, id, code, action, item_old, item_new

def UnpackTVDISPINFO(lparam):
    format = "iii40s"
    buf = win32gui.PyMakeBuffer(struct.calcsize(format), lparam)
    hwndFrom, id, code, buf_item = struct.unpack(format, buf)
    item = UnpackTVItem(buf_item)
    return hwndFrom, id, code, item
# XXX - end of code copied to win32gui_struct.py

#########################################################################
## The dialog itself
#########################################################################
import dlgcore

FolderSelector_Parent = dlgcore.TooltipDialog
class FolderSelector(FolderSelector_Parent):
    def __init__ (self, parent, manager, selected_ids=None,
                              single_select=False,
                              checkbox_state=False,
                              checkbox_text=None,
                              desc_noun="Select",
                              desc_noun_suffix="ed",
                              exclude_prop_ids=(PR_IPM_WASTEBASKET_ENTRYID,
                                                PR_IPM_SENTMAIL_ENTRYID,
                                                PR_IPM_OUTBOX_ENTRYID)
                                    ):
        FolderSelector_Parent.__init__(self, parent, manager.dialog_parser, "IDD_FOLDER_SELECTOR")
        assert not single_select or selected_ids is None or len(selected_ids)<=1
        self.single_select = single_select
        self.next_item_id = 1
        self.item_map = {}
        self.timer_id = None
        self.imageList = None

        self.select_desc_noun = desc_noun
        self.select_desc_noun_suffix = desc_noun_suffix
        self.selected_ids = [sid for sid in selected_ids if sid is not None]
        self.manager = manager
        self.checkbox_state = checkbox_state
        self.checkbox_text = checkbox_text or "Include &subfolders"
        self.exclude_prop_ids = exclude_prop_ids
        self.in_label_edit = False
        self.in_check_selections_valid = False

    def CompareIDs(self, id1, id2):
        # Compare the eid of the stores, then the objects
        CompareEntryIDs = self.manager.message_store.session.CompareEntryIDs
        try:
            return CompareEntryIDs(mapi.BinFromHex(id1[0]), mapi.BinFromHex(id2[0])) and \
                   CompareEntryIDs(mapi.BinFromHex(id1[1]), mapi.BinFromHex(id2[1]))
        except pythoncom.com_error:
            # invalid IDs are never the same
            return False

    def InIDs(self, id, ids):
        for id_check in ids:
            if self.CompareIDs(id_check, id):
                return True
        return False

    def _MakeItemParam(self, item):
        item_id = self.next_item_id
        self.next_item_id += 1
        self.item_map[item_id] = item
        return item_id

    def _InsertFolder(self, hParent, child, selected_ids = None, insert_after=0):
        text = child.name
        if child.children is None: # Need to build them!
            cItems = 1 # Anything > 0 will do
        else:
            cItems = len(child.children)
        if cItems==0:
            bitmapCol = bitmapSel = 5 # blank doc
        else:
            bitmapCol = bitmapSel = 0 # folder
        if self.single_select:
            mask = state = 0
        else:
            if (selected_ids and
                    self.InIDs(child.folder_id, selected_ids)):
                state = INDEXTOSTATEIMAGEMASK(IIL_CHECKED)
            else:
                state = INDEXTOSTATEIMAGEMASK(IIL_UNCHECKED)
            mask = commctrl.TVIS_STATEIMAGEMASK
        item_id = self._MakeItemParam(child)
        insert_buf, extras = PackTVINSERTSTRUCT(hParent, insert_after,
                                        (None,
                                        state,
                                        mask,
                                        text,
                                        bitmapCol,
                                        bitmapSel,
                                        cItems,
                                        item_id))
        if verbose:
            print "Inserting item", repr(insert_buf), "-",
        hitem = win32gui.SendMessage(self.list, commctrl.TVM_INSERTITEM,
                                        0, insert_buf)
        if verbose:
            print "got back handle", hitem
        return hitem

    def _InsertSubFolders(self, hParent, folderSpec):
        for child in folderSpec.children:
            hitem = self._InsertFolder(hParent, child, self.selected_ids)
            # If this folder is in the list of ones we need to expand
            # to show pre-selected items, then force expand now.
            if self.InIDs(child.folder_id, self.expand_ids):
                win32gui.SendMessage(self.list,
                                     commctrl.TVM_EXPAND,
                                     commctrl.TVE_EXPAND, hitem)
            # If single-select, and this is ours, select it
            # (multi-select uses check-boxes, not selection)
            if (self.single_select and
                    self.selected_ids and
                    self.InIDs(child.folder_id, self.selected_ids)):
                win32gui.SendMessage(self.list,
                                     commctrl.TVM_SELECTITEM,
                                     commctrl.TVGN_CARET, hitem)

    def _DetermineFoldersToExpand(self):
        folders_to_expand = []
        for folder_id in self.selected_ids:
            try:
                folder = self.manager.message_store.GetFolder(folder_id)
            except self.manager.message_store.MsgStoreException, details:
                print "Can't find a folder to expand:", details
                folder = None
            while folder is not None:
                try:
                    parent = folder.GetParent()
                except self.manager.message_store.MsgStoreException, details:
                    print "Can't find folder's parent:", details
                    parent = None
                if parent is not None and \
                   not self.InIDs(parent.GetID(), folders_to_expand):
                    folders_to_expand.append(parent.GetID())
                folder = parent
        return folders_to_expand

    def _GetTVItem(self, h):
        buffer, extra = EmptyTVITEM(h)
        win32gui.SendMessage(self.list, commctrl.TVM_GETITEM,
                                0, buffer.buffer_info()[0])
        return UnpackTVItem(buffer.tostring())

    def _YieldChildren(self, h):
        try:
            h = win32gui.SendMessage(self.list, commctrl.TVM_GETNEXTITEM,
                                     commctrl.TVGN_CHILD, h)
        except win32gui.error:
            h = 0
        while h:
            info = self._GetTVItem(h)
            item_param = info[-1]
            spec = self.item_map[item_param]

            yield info, spec
            # Check children
            for info, spec in self._YieldChildren(h):
                yield info, spec
            try:
                h = win32gui.SendMessage(self.list, commctrl.TVM_GETNEXTITEM,
                                         commctrl.TVGN_NEXT, h)
            except win32gui.error:
                h = None

    def _YieldAllChildren(self):
        return self._YieldChildren(commctrl.TVI_ROOT)

    def _YieldCheckedChildren(self):
        if self.single_select:
            # If single-select, the checked state is not used, just the
            # selected state.
            try:
                h = win32gui.SendMessage(self.list, commctrl.TVM_GETNEXTITEM,
                                         commctrl.TVGN_CARET, 0)
            except win32gui.error:
                h = 0
            if not h: # nothing selected.
                return
            info = self._GetTVItem(h)
            spec = self.item_map[info[7]]
            yield info, spec
            return # single-hit yield.

        for info, spec in self._YieldAllChildren():
            checked = (info[1] >> 12) - 1
            if checked:
                yield info, spec

    def GetSelectedIDs(self):
        try:
            self.GetDlgItem("IDC_LIST_FOLDERS")
        except win32gui.error: # dialog dead!
            return self.selected_ids, self.checkbox_state
        ret = []
        for info, spec in self._YieldCheckedChildren():
            ret.append(spec.folder_id)
        check = win32gui.SendMessage(self.GetDlgItem("IDC_BUT_SEARCHSUB"),
                                     win32con.BM_GETCHECK, 0, 0)
        return ret, check != 0

    def UnselectItem(self, item):
        if self.single_select:
            win32gui.SendMessage(self.list,
                                 commctrl.TVM_SELECTITEM,
                                 commctrl.TVGN_CARET, 0)
        else:
            state = INDEXTOSTATEIMAGEMASK(IIL_UNCHECKED)
            mask = commctrl.TVIS_STATEIMAGEMASK
            buf, extra = PackTVITEM(item[0], state, mask,
                                    None, None, None, None, None)
            win32gui.SendMessage(self.list, commctrl.TVM_SETITEM,
                                 0, buf)

    def _CheckSelectionsValid(self, is_close = False):
        if self.in_check_selections_valid:
            return
        self.in_check_selections_valid = True
        try:
            if self.single_select:
                if is_close:
                    # Make sure one is selected.
                    for ignore in self._YieldCheckedChildren():
                        break
                    else:
                        self.manager.ReportInformation("You must select a folder")
                        return False
                else:
                    # In a single-select dialog, we can't stop the user selecting
                    # a 'top-level' folder - we can only stop them closing the
                    # dialog while it is selected.
                    return True
            # For a multi-select dialog, we simply un-check the existing item.
            # For single-select, we set no item selected.
            result_valid = True
            for info, spec in self._YieldCheckedChildren():
                try:
                    folder = self.manager.message_store.GetFolder(spec.folder_id)
                    parent = folder.GetParent()
                    try:
                        # Psts and the main Exchange store have top level
                        # folders with parents (with empty display names),
                        # and no grandparents.  Anything below the top
                        # level *does* have a grandparent.  This means our
                        # test for "top level folder" can be: does it have
                        # a parent *and* grandparent.  However, a
                        # secondary Exchange account doesn't have the
                        # empty-display-name parent, so the top-level
                        # doesn't have a parent, and the top selectable
                        # folder doesn't have a grandparent, and our test
                        # fails.  Allow for this by checking for the
                        # "Access denied" exception when getting the
                        # grandparent, and assuming that this means that
                        # this is what is happening.  This will only fail
                        # if we get an 'access denied' error for the
                        # empty-display-name parent, which should not be
                        # the case.
                        grandparent = parent.GetParent()
                    except self.manager.message_store.MsgStoreException, details:
                        hr, msg, exc, argErr = details.mapi_exception
                        if hr == winerror.E_ACCESSDENIED:
                            valid = parent is not None
                        else:
                            raise # but only down a couple of lines...
                    else:
                        valid = parent is not None and grandparent is not None
                except self.manager.message_store.MsgStoreException, details:
                    print "Eeek - couldn't get the folder to check " \
                          "valid:", details
                    valid = False
                if not valid:
                    if result_valid: # are we the first invalid?
                        self.manager.ReportInformation(
                            "Please select a child folder - top-level folders " \
                            "can not be used.")
                    self.UnselectItem(info)
                result_valid = result_valid and valid
            return result_valid
        finally:
            self.in_check_selections_valid = False

    # Message processing
#    def GetMessageMap(self):

    def OnInitDialog (self, hwnd, msg, wparam, lparam):
        FolderSelector_Parent.OnInitDialog(self, hwnd, msg, wparam, lparam)
        caption = "%s folder" % (self.select_desc_noun,)
        if not self.single_select:
            caption += "(s)"
        win32gui.SendMessage(hwnd, win32con.WM_SETTEXT, 0, caption)
        self.SetDlgItemText("IDC_BUT_SEARCHSUB", self.checkbox_text)
        child = self.GetDlgItem("IDC_BUT_SEARCHSUB")
        if self.checkbox_state is None:
            win32gui.ShowWindow(child, win32con.SW_HIDE)
        else:
            win32gui.SendMessage(child, win32con.BM_SETCHECK, self.checkbox_state)
        self.list = self.GetDlgItem("IDC_LIST_FOLDERS")
        import resources
        mod_handle, mod_bmp, extra_flags = \
             resources.GetImageParamsFromBitmapID(self.dialog_parser, "IDB_FOLDERS")
        bitmapMask = win32api.RGB(0,0,255)
        self.imageList = win32gui.ImageList_LoadImage(mod_handle, mod_bmp,
                                                        16, 0,
                                                        bitmapMask,
                                                        win32con.IMAGE_BITMAP,
                                                        extra_flags)
        win32gui.SendMessage( self.list,
                                commctrl.TVM_SETIMAGELIST,
                                commctrl.TVSIL_NORMAL, self.imageList )
        if self.single_select:
            # Remove the checkbox style from the list for single-selection
            style = win32api.GetWindowLong(self.list,
                                           win32con.GWL_STYLE)
            style = style & ~commctrl.TVS_CHECKBOXES
            win32api.SetWindowLong(self.list,
                                   win32con.GWL_STYLE,
                                   style)
            # Hide "clear all"
            child = self.GetDlgItem("IDC_BUT_CLEARALL")
            win32gui.ShowWindow(child, win32con.SW_HIDE)

        # Extended MAPI version of the tree.
        # Build list of all ids to expand - ie, list includes all
        # selected folders, and all parents.
        dlgutils.SetWaitCursor(1)
        self.expand_ids = self._DetermineFoldersToExpand()
        tree = BuildFolderTreeMAPI(self.manager.message_store.session, self.exclude_prop_ids)
        self._InsertSubFolders(0, tree)
        self.selected_ids = [] # Only use this while creating dialog.
        self.expand_ids = [] # Only use this while creating dialog.
        self._UpdateStatus()
        dlgutils.SetWaitCursor(0)

    def OnDestroy(self, hwnd, msg, wparam, lparam):
        import timer
        if self.timer_id is not None:
            timer.kill_timer(self.timer_id)
        self.item_map = None
        if self.imageList:
            win32gui.ImageList_Destroy(self.imageList)
        FolderSelector_Parent.OnDestroy(self, hwnd, msg, wparam, lparam)

    def OnCommand(self, hwnd, msg, wparam, lparam):
        FolderSelector_Parent.OnCommand(self, hwnd, msg, wparam, lparam)
        id = win32api.LOWORD(wparam)
        id_name = self._GetIDName(id)
        code = win32api.HIWORD(wparam)

        if code == win32con.BN_CLICKED:
            if id in (win32con.IDOK, win32con.IDCANCEL) and self.in_label_edit:
                cancel = id == win32con.IDCANCEL
                win32gui.SendMessage(self.list, commctrl.TVM_ENDEDITLABELNOW,
                                     cancel,0)
                return
            # Button clicks
            if id == win32con.IDOK:
                if not self._CheckSelectionsValid(True):
                    return
                self.selected_ids, self.checkbox_state = self.GetSelectedIDs()
                win32gui.EndDialog(hwnd, id)
            elif id == win32con.IDCANCEL:
                win32gui.EndDialog(hwnd, id)
            elif id_name == "IDC_BUT_CLEARALL":
                for info, spec in self._YieldCheckedChildren():
                    self.UnselectItem(info)
            elif id_name == "IDC_BUT_NEW":
                # Force a new entry in the tree at our location, and begin
                # editing.
                # Add the new item to the tree.
                h = win32gui.SendMessage(self.list, commctrl.TVM_GETNEXTITEM,
                                         commctrl.TVGN_CARET, commctrl.TVI_ROOT)
                parent_item = self._GetTVItem(h)
                if parent_item[6]==0:
                    # eeek - parent has no existig children - say we have one
                    # so we can be expanded.
                    update_item, extra = PackTVITEM(h, None, None, None, None, None, 1, None)
                    win32gui.SendMessage(self.list, commctrl.TVM_SETITEM, 0, update_item)

                item_id = self._MakeItemParam(None)
                temp_spec = FolderSpec(None, "New folder")
                hnew = self._InsertFolder(h, temp_spec, None, commctrl.TVI_FIRST)

                win32gui.SendMessage(self.list, commctrl.TVM_ENSUREVISIBLE, 0, hnew)
                win32gui.SendMessage(self.list,
                                     commctrl.TVM_SELECTITEM,
                                     commctrl.TVGN_CARET, hnew)

                # Allow label editing
                s = win32api.GetWindowLong(self.list, win32con.GWL_STYLE)
                s |= commctrl.TVS_EDITLABELS
                win32api.SetWindowLong(self.list, win32con.GWL_STYLE, s)

                win32gui.SetFocus(self.list)
                self.in_label_edit = True
                win32gui.SendMessage(self.list, commctrl.TVM_EDITLABEL, 0, hnew)

        self._UpdateStatus()

    def _DoUpdateStatus(self, id, timeval):
        import timer
        # Kill the timer first to prevent it firing again.
        self.timer_id = None
        timer.kill_timer(id)
        self._CheckSelectionsValid()
        names = []
        num_checked = 0
        for info, spec in self._YieldCheckedChildren():
            num_checked += 1
            if len(names) < 20:
                names.append(info[3])

        status_string = "%s%s %d folder" % (self.select_desc_noun,
                                            self.select_desc_noun_suffix,
                                            num_checked)
        if num_checked != 1:
            status_string += "s"
        self.SetDlgItemText("IDC_STATUS1", status_string)
        self.SetDlgItemText("IDC_STATUS2", "; ".join(names))

    def _UpdateStatus(self):
        # We have problems with the order of events - we get the notification
        # events before the new states are available via GetItem.
        # Therefore, we start a one-shot, immediate timer, which ends up
        # at the end of the message queue, and we work.
        import timer
        if self.timer_id is not None:
            timer.kill_timer(self.timer_id)
        self.timer_id = timer.set_timer (0, self._DoUpdateStatus)

    def OnNotify(self, msg, hwnd, wparam, lparam):
        FolderSelector_Parent.OnNotify(self, hwnd, msg, wparam, lparam)
        format = "iii"
        buf = win32gui.PyMakeBuffer(struct.calcsize(format), lparam)
        hwndFrom, id, code = struct.unpack(format, buf)
        code += commctrl.PY_0U # work around silly old pywin32 bug
        id_name = self._GetIDName(id)
        if id_name == "IDC_LIST_FOLDERS":
            if code == commctrl.NM_CLICK:
                self._UpdateStatus()
            elif code == commctrl.NM_DBLCLK:
                # No special dblclick handling - default behaviour is to
                # expand/collapse tree, and auto-closing the dialog, even
                # when the folder has no children, doesn't really make sense.
                pass
            elif code == commctrl.TVN_ITEMEXPANDING:
                ignore, ignore, ignore, action, itemOld, itemNew = \
                                            UnpackTVNOTIFY(lparam)
                if action == 1: return 0 # contracting, not expanding
                itemHandle = itemNew[0]
                info = itemNew
                folderSpec = self.item_map[info[7]]
                if folderSpec.children is None:
                    folderSpec.children = _BuildFoldersMAPI(self.manager, folderSpec)
                    self._InsertSubFolders(itemHandle, folderSpec)
            elif code == commctrl.TVN_SELCHANGED:
                self._UpdateStatus()
            elif code == commctrl.TVN_ENDLABELEDIT:
                ignore, ignore, ignore, item = UnpackTVDISPINFO(lparam)
                handle = item[0]
                stay_in_edit = False
                try:
                    name = item[3]
                    if name is None:
                        # User cancelled folder creation - delete the item
                        win32gui.SendMessage(self.list, commctrl.TVM_DELETEITEM,
                                             0, handle)
                        return
                    # Attempt to create a folder of that name.
                    parent_handle = win32gui.SendMessage(self.list,
                                                         commctrl.TVM_GETNEXTITEM,
                                                         commctrl.TVGN_PARENT,
                                                         handle)
                    parent_item = self._GetTVItem(parent_handle)
                    parent_spec = self.item_map[parent_item[7]]
                    parent_folder = self.manager.message_store.GetFolder(parent_spec.folder_id)
                    try:
                        new_folder = parent_folder.CreateFolder(name)
                        # Create a new FolderSpec for this folder, and stash
                        new_spec = FolderSpec(new_folder.GetID(), name)
                        # The info passed by the notify message appears to
                        # not have the lparam (even though the docs say it
                        # does.)  Fetch it
                        spec_key = self._GetTVItem(handle)[7]
                        self.item_map[spec_key] = new_spec
                        # And update the tree with the new item
                        buf, extra = PackTVITEM(handle, None, None, name, None, None, None, None)
                        win32gui.SendMessage(self.list, commctrl.TVM_SETITEM, 0, buf)
                    except pythoncom.com_error, details:
                        hr, msg, exc, arg = details
                        if hr == mapi.MAPI_E_COLLISION:
                            user_msg = "A folder with that name already exists"
                        else:
                            user_msg = "MAPI error %s" % mapiutil.GetScodeString(hr)
                        self.manager.ReportError("Could not create the folder\r\n\r\n" + user_msg)
                        stay_in_edit = True
                finally:
                    if stay_in_edit:
                        win32gui.SendMessage(self.list, commctrl.TVM_EDITLABEL, 0, handle)
                    else:
                        # reset to no label edits
                        s = win32api.GetWindowLong(self.list, win32con.GWL_STYLE)
                        s &= ~commctrl.TVS_EDITLABELS
                        win32api.SetWindowLong(self.list, win32con.GWL_STYLE, s)
                        self.in_label_edit = False

def Test():
    single_select =False
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "..")))
    import manager
    mgr = manager.GetManager()
    if mgr.dialog_parser is None:
        import dialogs
        mgr.dialog_parser = dialogs.LoadDialogs()

    ids = [("0000","0000"),] # invalid ID for testing.
    d=FolderSelector(0, mgr, ids, single_select = single_select)
    if d.DoModal() != win32con.IDOK:
        print "Cancelled"
        return
    ids, include_sub = d.GetSelectedIDs()
    d=FolderSelector(0, mgr, ids, single_select = single_select, checkbox_state = include_sub)
    d.DoModal()

if __name__=='__main__':
    verbose = 1
    Test()
