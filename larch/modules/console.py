#!/usr/bin/env python
#
# console.py
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
# 2010.02.01


"""Implement a command line driven user interface for larch.
"""

import sys, os, getpass, threading
from uipi import Uipi


def out(line):
    if type(line) == unicode:
        line = line.encode("UTF-8")
    sys.stdout.write(line)
    sys.stdout.flush()


class Ui(Uipi):
    def __init__(self, guiexec):
        Uipi.__init__(self, backend=None)
        self.autocontinue = ("x" in sys.argv[1])

        self.logger = Logger()
        self.out_lock = threading.Lock()
        self.progress = Progress(self.logger)
        self.docviewer = None

        # Associate command names with functions (aliases are allowed)
        self.functions = {}
        for assoc in function_list:
            for n in assoc[1:]:
                self.functions[n] = assoc[0]


    def init(self):
        return


    def go(self):
        self.logger.setVisible("l" not in sys.argv[1])
        self.input = list(sys.argv[2:])


    def mainloop(self):
        try:
            r = 1
            for cmd in self.input:
                r = self.do(cmd)
                command.worker_wait()
                if r != 0:
                    break
        except:
            r = 1
        if r:
            self.sendsignal("$$$uiquit$$$")
            usage()
        return r


    def _dialog(self, title, message=None):
        logqueue.join()
        out("***** %s *****\n" % title)
        if message:
            out(message + "\n")

    def infoDialog(self, message, title=None, async=""):
        if title == None:
            title = _("Information")
        self._dialog(title, message)
        if not self.autocontinue:
            raw_input(_("Press <Enter> to continue").encode("UTF-8"))
        return self.async(async, True)


    def confirmDialog(self, message, title=None, async=""):
        if title == None:
            title = _("Confirmation")
        self._dialog(title, message)
        if self.autocontinue:
            r = True
        else:
            l = raw_input("%s (y) | %s (n) ? " % (_("Yes"), _("No")))
            r = (l.strip()[0] in "yY")
        return self.async(async, r)


    def textLineDialog(self, label=None, title=None, text="", pw=False,
            async=""):
        if title == None:
            title = _("Input Required")
        self._dialog(title)
        x = (": (%s) " % text) if text else ": "
        if pw:
            r = getpass.getpass(label + x)
        else:
            out(label + x)
            r = raw_input()
        return self.async(async, (True, r))


    def async(self, sig, result):
        if sig:
            self.sendsignal(sig, result)
        else:
            return result


    def error(self, message, title=None, fatal=True):
        """In console mode all errors are fatal.
        """
        if title == None:
            title =  _("ERROR")
        self.infoDialog(message, title)
        command.uiquit()
        assert False


    def do(self, cmdline):
        cmda = cmdline.split()
        fn = self.functions.get(cmda[0])
        if fn:
            fn(*cmda[1:])
            return 0
        else:
            self.error(_("Unknown command: %s") % cmda[0])


    # The gui interface functions are not used here
    def command(self, cmd, *args):
        return

    def ask(self, cmd, *args):
        return None

    def asknowait(self, cmd, *args):
        return

    def sendui(self, line):
        return

    def busy(self):
        return

    def unbusy(self):
        return


#-----------------------------------------------------------
# Main Actions

def x_install():
    ui.sendsignal("&-:install*clicked")

def x_larchify(opts=""):
    """opts: string containing 's' to generate sshkeys, 'r' to use oldsquash
    """
    ui.sendsignal("&larchify&", "s" not in opts, "r" in opts)

def x_create_iso():
    """Create an iso of the live system
    """
    ui.sendsignal("&makelive&", True, "", False, True)
    # + iso? + partition + format? + larchboot?

def x_write_partition(part, opts=""):
    """Write the live system to the given partition.
    opts: string containing 'n' to suppress formatting, 'l' to force larchboot
    """
    ui.sendsignal("&makelive&", False, part, 'n' not in opts, 'l' in opts)
    # + iso? + partition + format? + larchboot?

def x_create_bootiso(part):
    ui.sendsignal("&bootiso&", part)
#-----------------------------------------------------------


def infoline(item, value):
    out("  %-25s %s\n" % (item, value))

def show_project_info():
    yes = _("Yes")
    no = _("No")
    infoline(_("Project Name:"), config.project)
    infoline(_("Profile:"), config.get("profile"))
    infoline(_("Installation Path:"), config.get("install_path"))
    infoline(_("Working Directory:"), config.working_dir)
    infoline(_("Platform:"), config.get("platform"))
    infoline(_("Installation Mirror:"), config.get("localmirror"))
    infoline(_("--- use mirror:"), yes if config.get("uselocalmirror") else no)
    infoline(_("Use Project Mirrorlist:"), yes if config.get("usemirrorlist") else no)
    infoline(_("Bootloader:"), config.get("medium_btldr"))
    infoline(_("Medium Detection:"), config.get("medium_search"))
    infoline(_("Medium Label:"), config.get("medium_label"))
    infoline(_("iso 'application ID':"), config.get("isoA"))
    infoline(_("iso 'publisher':"), config.get("isopublisher"))
    infoline(_("Package Cache:"), config.get("pacman_cache"))

def show_projects():
    out(_("Projects:\n"))
    for p in config.getsections():
        out("    %s\n" % p)

def show_profiles():
    out(_("Profiles (in %s):\n") % config.profile_dir)
    for p in config.profiles():
        out("    %s\n" % p)

def show_example_profiles():
    out(_("Example Profiles (in %s):\n") % base_dir + "/profiles")
    for p in os.listdir(base_dir + "/profiles"):
        out("    %s\n" % p)

def show_partitions():
    out(_("Available Partitions:\n"))
    for p in command.get_partitions():
        out(p + "\n")


def set_project(name):
    try:
        i = config.getsections().index(name)
        ui.sendsignal(":choose_project_combo*changed", i)
    except:
        ui.error(_("Unknown project name: '%s'") % name)

def new_project(name):
    ui.sendsignal("$*new_project_name*$", name)

def del_project(name):
    if name in config.getsections():
        ui.sendsignal("&-:project_delete*clicked", name)
    else:
        ui.error(_("Unknown project name: '%s'") % name)


def set_profile(name):
    try:
        i = config.profiles().index(name)
        ui.sendsignal(":choose_profile_combo*changed", i)
    except:
        ui.error(_("Unknown profile name: '%s'") % name)

def rename_profile(name):
    ui.sendsignal("$*rename_profile*$", name)

def new_profile(path, name=None):
    ui.sendsignal("$*make_new_profile*$", path, name)

def del_profile(name):
    if name in config.profiles():
        ui.sendsignal("&-:profile_delete*clicked", name)
    else:
        ui.error(_("Unknown profile name: '%s'") % name)


def set_ipath(path):
    ui.sendsignal("$*set_ipath*$", path)


def set_platform(arch):
    try:
        i = config.platforms.index(arch)
        ui.sendsignal(":platform*changed", i)
    except:
        ui.error(_("Available platforms: %s") % repr(config.platforms))


def set_buildmirror(path):
    ui.sendsignal("$*set_build_mirror*$", path)


def set_pacman_cache(path):
    ui.sendsignal("$*set_pacman_cache*$", path)


def use_build_mirror(on):
    ui.sendsignal(":use_local_mirror*toggled", on[0] in "yY")


def use_project_mirrorlist(on):
    ui.sendsignal(":mirrorlist*toggled", on[0] in "yY")


def set_bootloader(bl):
    bl = bl.lower()
    if bl == "isolinux":
        bl = "syslinux"
    elif bl in ("grub", "syslinux", "none"):
        ui.sendsignal(":%s*toggled" % bl, True)
    else:
        ui.error(_("Invalid bootloader: %s") % bl)


def set_medium_detection(mdet):
    mdet = mdet.lower()
    if mdet in ("search", "uuid", "label", "device"):
        ui.sendsignal(":%s*toggled" % mdet, True)


def set_label(label):
    ui.sendsignal("$*new_label*$", label)


def set_isoa(label):
    ui.sendsignal("$*new_isoa*$", label)


def set_isop(label):
    ui.sendsignal("$*new_isop*$", label)


def pacman_s(*names):
    ui.sendsignal("&*pacmanS*&", " ".join(names))


def pacman_r(*names):
    ui.sendsignal("&*pacmanR*&", " ".join(names))


def pacman_u(filepaths):
    ui.sendsignal("&*pacmanU*&", " ".join(filepaths))


def pacman_sy():
    ui.sendsignal("&-:sync*clicked")



function_list = (
    [x_install, "install", "i"],
    [x_larchify, "larchify", "l"],
    [x_create_iso, "create_iso", "ci"],
    [x_write_partition, "create_part", "cp"],
    [x_create_bootiso, "create_bootiso", "cb"],
    [show_project_info, "show_project_info", "i?"],
    [show_projects, "show_projects", "P?"],
    [show_profiles, "show_profiles", "p?"],
    [show_example_profiles, "show_example_profiles", "e?"],
    [show_partitions, "show_partitions", "d?"],
    [set_project, "set_project", "P:"],
    [new_project, "new_project", "P+"],
    [del_project, "del_project", "P-"],
    [set_profile, "set_profile", "p:"],
    [rename_profile, "rename_profile", "p!"],
    [new_profile, "new_profile", "p+"],
    [del_profile, "del_profile", "p-"],
    [set_ipath, "set_ipath", "ip:"],
    [set_platform, "set_platform", "arch:"],
    [set_buildmirror, "set_buildmirror", "m:"],
    [set_pacman_cache, "set_pacman_cache", "cache:"],
    [use_build_mirror, "use_build_mirror", "um:"],
    [use_project_mirrorlist, "use_project_mirrorlist", "upm:"],
    [set_bootloader, "set_bootloader", "bl:"],
    [set_medium_detection, "set_medium_detection", "md:"],
    [set_label, "set_label", "lab:"],
    [set_isoa, "set_isoa", "isoa:"],
    [set_isop, "set_isop", "isop:"],
    [pacman_s, "pacman_s", "ps:"],
    [pacman_r, "pacman_r", "pr:"],
    [pacman_u, "pacman_u", "pu:"],
    [pacman_sy, "pacman_sy", "psy"],
)



class Logger:
    def __init__(self):
        self.visible = True
        self.buffered = None
        self.dirty = False

    def setVisible(self, on):
        self.visible = on

    def clear(self):
        return

    def addLine(self, line):
        if self.visible:
            if self.dirty:
                sys.stdout.write("\r" + " "*80 + "\r")
            out("LOG: " + line + "\n")
        self.dirty = False


class Progress:
    def __init__(self, logger):
        self.active = False
        self.logger = logger

    def _done(self):
        return

    def start(self):
        self.active = True
        out("+Working ...\n")

    def end(self):
        self.active = False
        out("+ ... Completed\n")

    def addLine(self, line):
        return

    def set(self, text=""):
        if self.active and text and self.logger.visible:
            sys.stdout.write("\r" + " "*80 + "\r")
            out(text)
            self.logger.dirty = True


