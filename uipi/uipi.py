# uipi.py
#
# (c) Copyright 2009-2010 Michael Towers (larch42 at googlemail dot com)
#
# This file is part of the larch project.
#
#    larch is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    larch is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with larch; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#----------------------------------------------------------------------------
# 2010.01.27

"""This is an example of an interface class to the larch text-line
based ui toolkit ([q]uip).

It includes a very simple signal-slot mechanism, which can easily be
overridden.
"""

import sys, traceback
from subprocess import Popen, PIPE, STDOUT
import threading
try:
    import json
except:
    import simplejson as json


def debug(text):
    sys.stderr.write("uipi: %s\n" % text)
    sys.stderr.flush()


class Uipi:
    def __init__(self, backend="quip", **kwargs):
        """Using the **kwargs parameter allows options for the process
        start to be passed, for example 'cwd' or 'preexec_fn'.
        """
        # A dict for query tags (see 'Uipi.ask')
        self.query = {}
        # A dict to connect signals to slots. Note that the values
        # are lists of slots, not single slots.
        self.signal_dict = {}
        # Initially no widgets are disabled while 'busy' is active
        self.setDisableWidgets()
        self.interrupt = False
        self.siglock = threading.Lock()

        # Start ui process
        kwargs['stdin'] = PIPE
        kwargs['stdout'] = PIPE
        if backend:
            self.uiprocess = Popen(backend, **kwargs)


    def addsignal(self, wname, signal, slot=None, sname=None):
        """Enable emission of the given signal.
        """
        cmd = "^%s %s" % (wname, signal)
        if sname:
            cmd += " " + sname
        else:
            sname = wname + "*" + signal
        self.sendui(cmd)
        if slot:
            self.addslot(sname, slot)


    def addslot(self, signal, function):
        if self.signal_dict.has_key(signal):
            self.signal_dict[signal].append(function)
        else:
            self.signal_dict[signal] = [function]


    def sendsignal(self, *args):
        sig = args[0]
        if not self.signal_dict.get(sig):
            return
        if sig[0] == "&":
            # This type starts a new thread for each signal call
            if sig[1] == "-":
                # This type also shows 'busy', and cannot be nested
                if not self.siglock.acquire(False):
                    debug("Signal ignored: " + repr(args))
                    return
                self.busy()
            t = threading.Thread(target=self._sendsignal, args=args)
            t.start()
        else:
            # This type is executed within the calling (normally mainloop)
            # thread
            self._sendsignal(*args)


    def _sendsignal(self, name, *args):
        # When there are no slots the signal is simply ignored.
        try:
            for slot in self.signal_dict.get(name, []):
                slot(*args)
        except:
            if not self.interrupt:
                debug(traceback.format_exc())
        if name.startswith("&-"):
            self.interrupt = False
            self.unbusy()
            self.siglock.release()


    def setInterrupt(self):
        if self.unblocked(False):
            debug("Attempt to set interrupt when not 'busy'")
        else:
            self.interrupt = True


    def unblocked(self, block=True, release=True):
        if not self.siglock.acquire(block):
            return False
        if release:
            self.siglock.release()
            return True
        else:
            return self.siglock


##### These might well be overridden
    def setDisableWidgets(self, window=None, widgetlist=()):
        self.mainWindow = window
        self.disableWidgetList = widgetlist

    def busy(self):
        if self.mainWindow:
            self.command(self.mainWindow + ".busy",
                    self.disableWidgetList, True)

    def unbusy(self):
        if self.mainWindow:
            self.command(self.mainWindow + ".busy",
                    self.disableWidgetList, False)
#####


    def uipi_error(self, text):
        """This method provides a simple means of outputting an error
        report, assuming of course that stderr goes somewhere and is visible!
        It might be better to throw an exception, but the advantage of this
        function is that it doesn't disrupt the normal course of events.
        Override it if you want something else to happen.
        """
        sys.stderr.write(text)
        sys.stderr.flush()


    def mainloop(self):
        """Loop to read input from ui and act on it.
        """
        exitcode = 0
        while True:
            line = self.getline()
            if not line:
                # Occurs when the ui process has exited
                break

            elif line[0] == "^":
                # signal, call slots
                sig, args = line[1:].split(None, 1)
                self.sendsignal(sig, *json.loads(args))

            elif line[0] == "@":
                # The response to an enquiry
                self.response(line[1:])

            elif line[0] == "/":
                # ui exiting
                exitcode = int(line[1:])

            else:
                self.uipi_error("Unexpected message from ui:\n%s\n" % line)

        self.uiprocess = None
        return exitcode


    def getline(self):
        return self.uiprocess.stdout.readline()


    def command(self, cmd, *args):
        """Send a command to the user interface.
        The command is of the form 'widget.method', 'args' is the
        list of arguments. The argument list is encoded as json for
        transmission.
        """
        c = "!" + cmd
        if args:
            c += " " + json.dumps(args)
        self.sendui(c)


    def asknowait(self, cmd, signal, *args):
        """Send a request for information to the user interface.
        The method returns immediately without a response, which is sent
        later by means of the signal.
        The command is of the form 'widget.method', 'args' is the list of
        arguments. The argument list is encoded as json for transmission.
        'signal' is the name of the signal to be sent to return the result
        of the enquiry when it is available.
        """
        c = "?%s:%s" % (signal, cmd)
        if args:
            c += " " + json.dumps(args)
        self.sendui(c)
        return None


    def ask(self, cmd, *args):
        """Send a request for information to the user interface.
        This method waits until the result has been received, which means:
        *** WARNING *** It may not be called within the same thread as
        the main loop, or else the whole interface will hang.
        Thus care should be exercised when using this method.

        The command is of the form 'widget.method', 'args' is the
        list of arguments. The argument list is encoded as json for
        transmission.
        """
        event = AskEvent()
        self.query[event.tag] = event
        c = "?%s:%s" % (event.tag, cmd)
        if args:
            c += " " + json.dumps(args)
        self.sendui(c)
        event.wait()
        del(self.query[event.tag])
        return event.answer


    def response(self, text):
        l, r = text.split(":", 1)
        a = json.loads(r)
        if self.query.has_key(l):
            self.query[l].set(a)
        else:
            self.sendsignal(l, a)


    def widget(self, wtype, wname, **args):
        """Define a new widget.
        """
        self.sendui("%%%s %s %s" % (wtype, wname, json.dumps(args)))


    def layout(self, wname, ltree):
        """Layout a widget.
        Essentially this means specifying the layout of the widget's
        sub-widgets within the named widget.
        """
        self.sendui("$%s %s" % (wname, json.dumps(ltree)))


    def sendui(self, line):
        """Send a text line to the user interface process.
        """
        #self.process_lock.acquire()
        try:
            self.uiprocess.stdin.write("%s\n" % line)
        except:
            self.uipi_error("ui dead (%s)\n" % line)
        #self.process_lock.release()


    def quit(self, rc=0):
        self.sendui("/" + str(rc))


    def infoDialog(self, message, title=None, async=""):
        if title == None:
            title = _("Information")
        if async:
            return self.asknowait("infoDialog", async, message, title)
        return self.ask("infoDialog", message, title)


    def confirmDialog(self, message, title=None, async=""):
        if title == None:
            title = _("Confirmation")
        if async:
            return self.asknowait("confirmDialog", async, message, title)
        return self.ask("confirmDialog", message, title)


    def textLineDialog(self, label=None, title=None, text="", pw=False,
            async=""):
        if label == None:
            label = _("Enter the value here:")
        if title == None:
            title = _("Enter Information")
        if async:
            return self.asknowait("textLineDialog", async, label, title,
                    text, pw)
        return self.ask("textLineDialog", label, title, text, pw)


    def error(self, message, title=None, fatal=False):
        if title == None:
            title = _("Error")
        self.command("errorDialog" if fatal else "warningDialog",
            message, title)



class AskEvent:
    """Generate a tagged threading.Event which can store a response object.
    """
    count = 0

    def __init__(self):
        self.event = threading.Event()
        self.tag = str(AskEvent.count)
        AskEvent.count +=1

    def wait(self):
        self.event.wait()

    def set(self, a):
        self.answer = a
        self.event.set()
