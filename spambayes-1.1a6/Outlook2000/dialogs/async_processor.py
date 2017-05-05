# An async command processor
from dlgutils import *
import win32gui, win32api, win32con, commctrl
import win32process
import time

import processors

verbose = 0

IDC_START = 1100
IDC_PROGRESS = 1101
IDC_PROGRESS_TEXT = 1102

MYWM_SETSTATUS = win32con.WM_USER+11
MYWM_SETWARNING = win32con.WM_USER+12
MYWM_SETERROR = win32con.WM_USER+13
MYWM_FINISHED = win32con.WM_USER+14

# This is called from another thread - hence we need to jump through hoops!
class _Progress:
    def __init__(self, processor):
        self.hdlg = processor.window.hwnd
        self.hprogress = processor.GetControl(processor.statusbar_id)
        self.processor = processor
        self.stopping = False
        self.total_control_ticks = 40
        self.current_stage = 0
        self.set_stages( (("", 1.0),) )

    def set_stages(self, stages):
        self.stages = []
        start_pos = 0.0
        for name, prop in stages:
            stage = name, start_pos, prop
            start_pos += prop
            self.stages.append(stage)
        assert abs(start_pos-1.0) < 0.001, (
               "Proportions must add to 1.0 (%r,%r,%r)" %
                   (start_pos, stages, start_pos-1.0))

    def _next_stage(self):
        if self.current_stage == 0:
            win32api.PostMessage(self.hprogress, commctrl.PBM_SETRANGE, 0, MAKELPARAM(0,self.total_control_ticks))
            win32api.PostMessage(self.hprogress, commctrl.PBM_SETSTEP, 1, 0)
            win32api.PostMessage(self.hprogress, commctrl.PBM_SETPOS, 0, 0)

        self.current_stage += 1
        assert self.current_stage <= len(self.stages)

    def _get_current_stage(self):
        return self.stages[self.current_stage-1]

    def set_max_ticks(self, m):
        # skip to the stage.
        self._next_stage()
        self.current_stage_max = m
        self.current_stage_tick = -1 # ready to go to zero!
        # if earlier stages stopped early, skip ahead.
        self.tick()

    def tick(self):
        if self.current_stage_tick < self.current_stage_max:
            # Don't let us go beyond our stage max
            self.current_stage_tick += 1
        # Calc how far through this stage.
        this_prop = float(self.current_stage_tick) / self.current_stage_max
        # How far through the total.
        stage_name, start, end = self._get_current_stage()
        # Calc the perc of the total control.
        stage_name, start, prop = self._get_current_stage()
        total_prop = start + this_prop * prop
        # How may ticks is this on the control (but always have 1, so the
        # user knows the process has actually started.)
        control_tick = max(1,int(total_prop * self.total_control_ticks))
        if verbose:
            print "Tick", self.current_stage_tick, "is", this_prop, "through the stage,", total_prop, "through the total - ctrl tick is", control_tick
        win32api.PostMessage(self.hprogress, commctrl.PBM_SETPOS, control_tick)

    def _get_stage_text(self, text):
        stage_name, start, end = self._get_current_stage()
        if stage_name:
            text = stage_name + ": " + text
        return text
    def set_status(self, text):
        self.processor.progress_status = self._get_stage_text(text)
        win32api.PostMessage(self.hdlg, MYWM_SETSTATUS)
    def warning(self, text):
        self.processor.progress_warning = self._get_stage_text(text)
        win32api.PostMessage(self.hdlg, MYWM_SETWARNING)
    def error(self, text):
        self.processor.progress_error = self._get_stage_text(text)
        win32api.PostMessage(self.hdlg, MYWM_SETERROR)
    def request_stop(self):
        self.stopping = True
    def stop_requested(self):
        return self.stopping

class AsyncCommandProcessor(processors.CommandButtonProcessor):
    def __init__(self, window, control_ids, func, start_text, stop_text, disable_ids):
        processors.CommandButtonProcessor.__init__(self, window, control_ids[:1], func, ())
        self.progress_status = ""
        self.progress_error = ""
        self.progress_warning = ""
        self.running = False
        self.statusbar_id = control_ids[1]
        self.statustext_id = control_ids[2]
        self.process_start_text = start_text
        self.process_stop_text = stop_text
        dids = self.disable_while_running_ids = []
        for id in disable_ids.split():
            dids.append(window.manager.dialog_parser.ids[id])

    def Init(self):
        win32gui.ShowWindow(self.GetControl(self.statusbar_id), win32con.SW_HIDE)
        self.SetStatusText("")

    def Done(self):
        if self.running:
            msg = "You must let the running process finish before closing this window"
            win32gui.MessageBox(self.window.hwnd, msg, "SpamBayes",
                                win32con.MB_OK | win32con.MB_ICONEXCLAMATION)
        return not self.running
    def Term(self):
        # The Window is dieing!  We *must* kill it and wait for it to finish
        # else bad things happen once the main thread dies before us!
        if self.running:
            self.progress.request_stop()
            i = 0
            while self.running:
                win32gui.PumpWaitingMessages(0,-1)
                if i % 100 == 0:
                    print "Still waiting for async process to finish..."
                time.sleep(0.01)
                i += 1
        return True

    def GetMessages(self):
        return [MYWM_SETSTATUS, MYWM_SETWARNING, MYWM_SETERROR, MYWM_FINISHED]

    def SetEnabledStates(self, enabled):
        for id in self.disable_while_running_ids:
            win32gui.EnableWindow(self.GetControl(id), enabled)

    def OnMessage(self, msg, wparam, lparam):
        if msg == MYWM_SETSTATUS:
            self.OnProgressStatus(wparam, lparam)
        elif msg == MYWM_SETWARNING:
            self.OnProgressWarning(wparam, lparam)
        elif msg == MYWM_SETERROR:
            self.OnProgressError(wparam, lparam)
        elif msg == MYWM_FINISHED:
            self.OnFinished(wparam, lparam)
        else:
            raise RuntimeError, "Not one of my messages??"

    def OnFinished(self, wparam, lparam):
        self.seen_finished = True
        wasCancelled = wparam
        self.SetEnabledStates(True)

        if self.process_start_text:
            win32gui.SendMessage(self.GetControl(), win32con.WM_SETTEXT,
                                 0, self.process_start_text)
        win32gui.ShowWindow(self.GetControl(self.statusbar_id), win32con.SW_HIDE)
        if wasCancelled:
            self.SetStatusText("Cancelled")

    def SetStatusText(self, text):
        win32gui.SendMessage(self.GetControl(self.statustext_id),
                                win32con.WM_SETTEXT,
                                0, text)

    def OnProgressStatus(self, wparam, lparam):
        self.SetStatusText(self.progress_status)

    def OnProgressError(self, wparam, lparam):
        self.SetStatusText(self.progress_error)
        win32gui.MessageBox(self.window.hwnd,
                            self.progress_error, "SpamBayes",
                            win32con.MB_OK | win32con.MB_ICONEXCLAMATION)
        if not self.running and not self.seen_finished:
            self.OnFinished(0,0)

    def OnProgressWarning(self, wparam, lparam):
        pass

    def OnClicked(self, id):
        self.StartProcess()

    def StartProcess(self):
        if self.running:
            self.progress.request_stop()
        else:
            # Do anything likely to fail before we screw around with the
            # control states - this way the dialog doesn't look as 'dead'
            progress=_Progress(self)
            # Now screw around with the control states, restored when
            # the thread terminates.
            self.SetEnabledStates(False)
            if self.process_stop_text:
                win32gui.SendMessage(self.GetControl(),
                                     win32con.WM_SETTEXT,
                                     0, self.process_stop_text)
            win32gui.SendMessage(self.GetControl(self.statustext_id),
                                 win32con.WM_SETTEXT, 0, "")
            win32gui.ShowWindow(self.GetControl(self.statusbar_id),
                                win32con.SW_SHOW)
            # Local function for the thread target that notifies us when finished.
            def thread_target(h, progress):
                try:
                    self.progress = progress
                    self.seen_finished = False
                    self.running = True
                    # Drop my thread priority, so outlook can keep repainting
                    # and doing its stuff without getting stressed.
                    import win32process, win32api
                    THREAD_PRIORITY_BELOW_NORMAL=-1
                    win32process.SetThreadPriority(win32api.GetCurrentThread(), THREAD_PRIORITY_BELOW_NORMAL)
                    self.func( self.window.manager, self.window.config, progress)
                finally:
                    try:
                        win32api.PostMessage(h, MYWM_FINISHED, self.progress.stop_requested())
                    except win32api.error:
                        # Bad window handle - already down.
                        pass
                    self.running = False
                    self.progress = None

            # back to the program :)
            import threading
            t = threading.Thread(target=thread_target, args =(self.window.hwnd, progress))
            t.start()

if __name__=='__main__':
    verbose = 1
    # Test my "multi-stage" code
    class HackProgress(_Progress):
        def __init__(self): # dont use dlg
            self.hprogress = self.hdlg = 0
            self.dlg = None
            self.stopping = False
            self.total_control_ticks = 40
            self.current_stage = 0
            self.set_stages( (("", 1.0),) )

    print "Single stage test"
    p = HackProgress()
    p.set_max_ticks(10)
    for i in range(10):
        p.tick()

    print "First stage test"
    p = HackProgress()
    stages = ("Stage 1", 0.2), ("Stage 2", 0.8)
    p.set_stages(stages)
    # Do stage 1
    p.set_max_ticks(10)
    for i in range(10):
        p.tick()
    # Do stage 2
    p.set_max_ticks(20)
    for i in range(20):
        p.tick()
    print "Second stage test"
    p = HackProgress()
    stages = ("Stage 1", 0.9), ("Stage 2", 0.1)
    p.set_stages(stages)
    p.set_max_ticks(10)
    for i in range(7): # do a few less just to check
        p.tick()
    p.set_max_ticks(2)
    for i in range(2):
        p.tick()
    print "Third stage test"
    p = HackProgress()
    stages = ("Stage 1", 0.9), ("Stage 2", 0.1)
    p.set_stages(stages)
    p.set_max_ticks(300)
    for i in range(313): # do a few more just to check
        p.tick()
    p.set_max_ticks(2)
    for i in range(2):
        p.tick()

    print "Done!"
