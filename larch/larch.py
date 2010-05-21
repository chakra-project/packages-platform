#!/usr/bin/env python
#
# larch.py
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
# 2010.02.12


"""
This is the main module of the larch program. It needs to run most of the
larch-building commands as root, but it is generally better to run it as
a non-privileged user - it can ask for the root password when it needs it.
One advantage of running as a normal user is that all the larch
configuration files are stored by default in the user's home directory,
and it would be inconvenient to have these only accessible as root.

The graphical user interface runs as a separate process and the
communication is via pipes to the subprocess's stdio channels.
Data is passed as json objects.

The command-line user interface works in a very different way, though it
still uses signals to some extent to control execution. It does not start
a separate process, it just handles the commands passed on the command line
sequentially.

The main work of the program (the steering of the live system
construction) is handled by the imported modules and run in a separate
thread.
"""

import os, sys, traceback, re, pwd, signal, time

import __builtin__
__builtin__.base_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append("%s/modules" % base_dir)
script_dir = "%s/buildscripts" % base_dir

from subprocess import Popen, call, PIPE, STDOUT
import threading, traceback
from Queue import Queue
import pexpect

import base
from installation import Installation

from projectpage import ProjectPage
from installpage import InstallPage
from buildpage import BuildPage
from mediumpage import MediumPage
from tweakpage import TweakPage

doc_home = [
        "gui_project_settings.html",
        "gui_installation.html",
        "gui_larchify.html",
        "gui_medium.html",
        "gui_tweaks.html"
    ]


def errout(text, quitc=0):
    sys.stderr.write(text)
    sys.stderr.flush()
    if quitc:
        exit(quitc)
__builtin__.errout = errout

def debug(text):
    errout("DEBUG: " + text.strip() + "\n")
__builtin__.debug = debug


import gettext
gettext.install('larch', base_dir+'/i18n', unicode=1)
__builtin__.lang = (os.environ.get("LANGUAGE") or os.environ.get("LC_ALL")
            or os.environ.get("LC_MESSAGES") or os.environ.get("LANG"))
# Some of the subprocesses must be run without i18n because the text
# output is parsed.
os.environ["LANGUAGE"] = "C"

class Command:
    def __init__(self):
        self.password = None
        # Supershell/worker variables
        self.supershell_process = None
        self.worker_lock = threading.Lock()
        self.worker_breakin = False
        self.worker_active = False

        # Keep a record of mounts
        self.mounts = []


    def gui_init(self):
        """The user interface must already be running before entering here.
        """
        ui.init()
        # Initialize gui modules
        self.pages = [ProjectPage(), InstallPage(), BuildPage(),
                MediumPage(), TweakPage()]

        # Connect up the signals and slots
        self.addconnections([
                ("$$$uiquit$$$", self.uiquit),
                ("$$$cancel$$$", self.cancel),
                (":showlog*clicked", self._showlog),
                (":docs*clicked", self._showdocs),
                (":notebook*changed", self.pageswitch),
            ])
        for p in self.pages:
            self.addconnections(p.connect())


    def addconnections(self, connlist):
        for s, f in connlist:
            ui.addslot(s, f)


    def run(self):
        # Start on the project page
        self.pageswitch(0)
        ui.go()


    def pageswitch(self, index):
        if ui.docviewer:
            ui.docviewer.gohome(doc_home[index])
        if (not self.pages[index].setup()) and (index != 0):
            ui.command(":notebook.set", 0)


    def log(self, line):
        # The line should not have a newline terminator
        logqueue.put(line)


    def worker(self, fun, *args):
        """Functions run via this function will have their output displayed
        in the progress view, and it should be possible to cancel them
        manually.
        This method should only be called from a background thread (i.e.
        from an '&'-signal handler.
        """
        self.worker_lock.acquire()
        if self.worker_active:
            self.worker_lock.release()
            fatal_error("*BUG* Attempted to start second worker thread")
            return
        self.worker_breakin = False
        self.worker_active = True
        self.worker_lock.release()

        ui.progress.start()
        try:
            fun(*args)
            result = True
        except:
            result = False
            #debug("WORKER: " + traceback.format_exc())
        ui.progress.end()

        self.worker_lock.acquire()
        self.worker_active = False
        self.worker_lock.release()
        return result


    def worker_wait(self):
        """Used by the cli (only) to wait for the completion of an operation.
        It doesn't use any locking, so it should be used carefully
        """
        while self.worker_active:
                time.sleep(0.1)


    def supershell(self, cmd):
        """Run a command as root and wait until it completes.
        To be used (only) in the 'worker' thread.
        Return a pair (ok, output)
        Note that 'cmd' may not contain '"' characters!
        To handle 'Cancel' operations, interrupts are checked before and
        after execution of supershell commands.
        """
        if (os.getuid() != 0) and not self.password:
            while True:
                okpw = ui.textLineDialog(_("Please enter root password"),
                    "larch: root pw", pw=True)
                if okpw[0]:
                    self.password = okpw[1]
                    # Run a command as root, using the known password.
                    child = pexpect.spawn('su -c "echo _OK_"')
                    child.expect('Password:')
                    child.sendline(self.password)
                    child.expect(pexpect.EOF)
                    o = child.before.strip()
                    if o.endswith('_OK_'):
                        break
                    run_error(_("Incorrect root password"))
                    continue
                else:
                    run_error( _("No root password, cancelling operation"))
                    assert False

        self.worker_lock.acquire()
        if self.worker_breakin:
            self.worker_lock.release()
            assert False

        if self.supershell_process:
            self.worker_lock.release()
            fatal_error("*BUG* Attempted to start second supershell process")
            assert False

        self.supershell_process = self.asroot(cmd)
        if not self.supershell_process:
            self.worker_lock.release()
            fatal_error(_("Supershell couldn't be started"))
            assert False

        self.log(">" + cmd)
        self.worker_lock.release()

        result = []
        line0 = ""
        while True:
            ch = self.supershell_process.read(1)
            if not ch:
                if not line0:
                    break
            elif ch == "\n":
                continue
            elif ch != "\r":
                line0 += ch
                continue
            line = line0.strip()
            line0 = ""
            self.log(":-" + line)
            result.append(line)

        self.supershell_process.close()
        rc = self.supershell_process.exitstatus

        self.worker_lock.acquire()
        self.supershell_process = None
        interrupted = self.worker_breakin or (rc == None)
        self.log("@%d" % (-1 if rc == None else rc))
        self.worker_lock.release()

        assert not interrupted
        return (rc == 0, result)


    def asroot(self, cmd):
        """Run the command as root with pexpect. Return the spawned process.
        If it cannot be started return None.
        """
        p = pexpect.spawn('''su -s /bin/bash -c "echo _GO_ && %s"''' % cmd,
                timeout=None)
        e = p.expect(["_GO_.*\n", pexpect.TIMEOUT, "Password:"], 5)
        while e != 0:
            if e == 2:
                p.sendline(self.password)
                e = p.expect(["_GO_.*\n", pexpect.TIMEOUT], 5)
            else:
                return None
        return p


    def script(self, cmd):
        s = self.supershell("%s/%s" % (script_dir, cmd))
        if s[0]:
            return ""
        else:
            return "SCRIPT ERROR: (%s)\n" % cmd + "".join(s[1])


    def worker_cancel(self):
        """Cancel the current worker thread.
        This is achieved by inserting traps in the supershell calls.
        """
        self.worker_lock.acquire()
        if self.supershell_process:
            self.asroot("pkill -g %d" % self.supershell_process.pid)
        self.worker_breakin = True
        self.worker_lock.release()


    def _showlog(self):
        ui.runningtab(2)


    def _showdocs(self):
        ui.runningtab(3)


    def _browse(self, btype, path):
        simple_thread(self._browse_set, btype, path)


    def _browse_set(self, btype, path):
        appcall = config.get(btype)
        while (call(["which", appcall.split()[0]],
                stdout=PIPE, stderr=STDOUT) != 0):
            ok, new = ui.textLineDialog(
                    _("Enter '%s' application ('$' for path argument):") % btype,
                    text=appcall)
            if ok:
                appcall = new
                config.set(btype, appcall)
            else:
                return

        Popen(appcall.replace("$", path) + " &", shell=True)


    def sigint(self, num, frame):
        """CONSOLE MODE ONLY: A handler for SIGINT. Tidy up properly and quit.
        First kill potential running supershell process, then terminate
        logger, and then, finally, terminate the ui process.
        """
        self.uiquit()


    def uiquit(self):
        self.cancel(True)


    def cancel(self, terminate=False):
# This is a bit experimental - I'm not sure the worker threads will handle
# the break-ins sensibly.
        # This is not called from the worker thread, so it mustn't block.
        self.qthread = simple_thread(self._quit_run, terminate)


    def _quit_run(self, terminate):
        # Kill any running supershell process
        self.worker_cancel()
        self.worker_wait()

        if terminate:
            # Tell the logger to quit
            self.log("L:/\n")
            # Wait until logger process has terminated
            lthread.join()
            # Tell the user interface to exit
            ui.quit()

        self.worker_breakin = False
        command.unmount()


    def mount(self, src, dst, opts=""):
        if supershell("mount %s %s %s" % (opts, src, dst))[0]:
            self.mounts.append(dst)
            return True
        return False


    def unmount(self, dst=None):
        if dst == None:
            mounts = list(self.mounts)
        elif type(dst) in (list, tuple):
            mounts = list(dst)
        else:
            mounts = [dst]

        r = True
        for m in mounts:
            if supershell("umount %s" % m)[0]:
                self.mounts.remove(m)
            else:
                r = False
        return r


    def edit(self, fname, source=None, label=None, filter=None):
        """The file to be edited can be either an absolute path or else
        relative to the profile directory. If the file already exists its
        contents will be taken as the starting point, otherwise file at
        the 'source' path will be read in. Whichever file is available
        its contents can be filtered by an optional 'filter' function,
        which takes the file contents as a string as argument and
        returns the transformed contents as another string.
        """
        def revert():
            """If a file is addressed by 'source' revert to its contents,
            if source is "", clear the contents, otherwise revert to the
            contents as they were before entering the editor.
            """
            return textsrc if source != None else text0

        def endfile(text):
            t = text.encode("utf8")
            if t and (t[-1] != "\n"):
                t += "\n"
            d = os.path.dirname(f)
            if not os.path.isdir(d):
                os.makedirs(d)
            savefile(f, text)

        if source != None:
            textsrc = "" if source == "" else readfile(source, filter)
        if fname[0] == "/":
            f = fname
        else:
            f = os.path.join(config.get("profile"), fname)
        if os.path.isfile(f):
            text0 = readfile(f, filter)
        else:
            assert source != None   # The file must be present
            text0 = textsrc
        if not label:
            label = _("Editing '%s'") % fname
        ui.editor.start(label, endfile, text0, revert)


    def browser(self, path):
        self._browse("filebrowser", path)


    def chroot(self, cmd, mounts=[]):
        ip = config.ipath()
        if ip != "/":
            for m in mounts:
                self.mount("/" + m, "%s/%s" % (ip, m), "--bind")
            cmd = "chroot %s %s" % (ip, cmd)

        s = supershell(cmd)

        if ip != "/":
            self.unmount(["%s/%s" % (ip, m) for m in mounts])

        if s[0]:
            if s[1]:
                return s[1]
            else:
                return True
        return False


    def check_platform(self, report=True):
        arch = Popen(["cat", config.ipath(".ARCH")],
                stdout=PIPE, stderr=PIPE).communicate()[0].strip()
        if arch:
            if arch != config.get("platform"):
                if report:
                    config_error(_("Platform error, installed system is %s")
                            % arch)
                return False
        else:
            if report:
                config_error(_("No installed system found"))
            return False
        return True


    def enable_install(self):
        withinstall = (config.get("install_path") != "/")
        ui.command(":notebook.enableTab", 1, withinstall)
        ui.command(":notebook.enableTab", 4, withinstall)
        ui.command(":pacmanops.enable", withinstall
                and self.check_platform(report=False))


    def get_partitions(self):
        """Get a list of available partitions (only unmounted ones
        are included).
        """
        # First get a list of mounted devices
        mounteds = []
        fh = open("/etc/mtab")
        for l in fh:
            dev = l.split()[0]
            if dev.startswith("/dev/sd"):
                mounteds.append(dev)
        fh.close()
        # Get a list of partitions
        partlist = []
        for line in supershell("sfdisk -uM -l")[1]:
            if line.startswith("/dev/sd"):
                fields = line.replace("*", "").replace(" - ", " ? ")
                fields = fields.replace("+", "").replace("-", "").split()
                #debug("F5 '%s'" % fields[5])
                if fields[5] in ["0", "5", "f", "82"]:
                    #debug("No")
                    continue        # ignore uninteresting partitions
                if fields[0] in mounteds:
                    continue        # ignore mounted patitions
                # Keep a tuple (partition, size in MiB)
                partlist.append("%-12s %12s MiB" % (fields[0], fields[3]))
        return partlist



def readfile(f, filter=None):
    try:
        fh = open(f)
        r = fh.read()
        fh.close()
        return filter(r) if filter else r
    except:
        run_error(_("Couldn't read file '%s'") % f)
        return ""

def savefile(f, d):
    try:
        fh = open(f, "w")
        fh.write(d)
        fh.close()
    except:
        run_error(_("Couldn't save file '%s'") % f)


def config_error(text):
    ui.error(text, _("CONFIG ERROR"))
__builtin__.config_error = config_error

def run_error(text):
    ui.error(text, _("BUILD ERROR"))
__builtin__.run_error = run_error

def fatal_error(text):
    ui.error(text, _("FATAL ERROR"), fatal=True)
    command.uiquit()
__builtin__.fatal_error = fatal_error

#---------------------------
# Catch all unhandled errors.
def errorTrap(type, value, tb):
    etext = "".join(traceback.format_exception(type, value, tb))
    ui.error(etext, _("This error could not be handled"), fatal=True)
    command.uiquit()

sys.excepthook = errorTrap
#---------------------------


def simple_thread(func, *args):
        t = threading.Thread(target=func, args=args)
        t.start()
        return t


re_mksquashfs = re.compile(r":-\[.*\](.* ([0-9]+)%)")
re_pacman = re.compile(r":-(?:\(([^/]+/[^)]+)\))?(.*?)\[([-#]+)\]\s+([0-9]+)%")
re_mkisofs = re.compile(r":-\d\d?\.\d\d%")
def ltstart():
    """A thread function for reading log lines from the log queue and
    passing them to the logger.
    """
    progress = ""
    line0 = ""
    text0 = ""
    while True:
        line = logqueue.get()
        logqueue.task_done()
        if line.startswith("L:/"):
            # Quit logging
            break

        mp = re_pacman.match(line)
        if mp:
            #xfromy, text, bars, percent = m.groups()
            text = mp.group(2).strip()
            xfromy = mp.group(1)
            t = text if xfromy else text[:20]
            if (t != text0) and line0:
                logline(line0)
            line0 = "(%s) %s" % (xfromy, text) if xfromy else text
            ui.progress.set(line[2:])
            text0 = t
            continue

        # Filter the output of mksquashfs
        ms = re_mksquashfs.match(line)
        if ms:
            percent = ms.group(2)
            if progress != percent:
                progress = percent
                ui.progress.set("mksquashfs " + ms.group(1))
            continue

        # Test for mkisofs progress
        if re_mkisofs.match(line):
            ui.progress.set("mkisofs " + line[2:])
            continue

        ui.progress.set()
        progress = ""

        if line0:
            logline(line0)
            line0 = ""
            text0 = ""

        logline(line)


def logline(line):
    ui.logger.addLine(line)
    ui.progress.addLine(line)
    logfile.write(line + '\n')



def usage():
    errout(_("   Please see '%s/%s'\n   for usage information.\n")
                % (base_dir, "docs/html/larch_console.html"))
__builtin__.usage = usage



if __name__ == "__main__":

    # Various ui toolkits could be supported, but at the moment there
    # is only support for pyqt (apart from the console)
    if (len(sys.argv) > 1) and (sys.argv[1].startswith("-c")):
        from console import *
        guiexec = None
    else:
        from gui import *
        if (len(sys.argv) == 1) or (sys.argv[1] == "--pyqt"):
            guiexec = "quip"
        else:
            errout(_("ERROR: Unsupported option - '%s'\n") % sys.argv[1])
            errout(_("Start without arguments or with '--pyqt' to start pyqt gui.\n"))
            errout(_("The command line interface is started with '-c':\n"))
            usage()
            sys.exit(1)

    # The queue for log lines must be available before starting the supershell
    __builtin__.logqueue = Queue()

    # Set up ui
    __builtin__.ui = Ui(guiexec)
    # This starts the command interface
    __builtin__.command = Command()
    __builtin__.installation = Installation()
    __builtin__.config = base.LarchConfig(os.environ["HOME"])

    command.gui_init()

    # Start log reader thread
    logfile = open(config.working_dir + "/larch_log", "w")
    lthread = simple_thread(ltstart)

    __builtin__.supershell = command.supershell

    signal.signal(signal.SIGINT, command.sigint)

    command.run()
    cc = ui.mainloop()
    logfile.close()
    exit(cc)
