#!/usr/bin/env python
#
# buildpage.py
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
# 2010.03.23

from build import Builder, BASEGROUPS, USERINFO
import os
from glob import glob


class BuildPage:
    """This class manages the page dealing with larch system building.
    """
    def connect(self):
        return [
                ("&-:build*clicked", self.build),
                (":ssh*toggled", self.sshtoggle),
                (":locales*clicked", self.locales),
                (":rcconf*clicked", self.rcconf),
                (":initcpio*clicked", self.initcpio),
                (":overlay*clicked", self.overlay),
                ("&-:utable*clicked", self.uedit),
                ("&-:useradd*clicked", self.useradd),
                ("&:userdel*clicked", self.userdel),
                ("&larchify&", self.larchify),
            ]


    def __init__(self):
        ui.widget("Label", ":larchify", text=" *** <strong>%s</strong> ***" %
                _("The system to be compressed must be installed and ready."))
        ui.widget("Button", "^:locales", text=_("Edit supported locales"),
                tt=_("Edit the /etc/locale.gen file to select supported glibc locales"))
        ui.widget("Button", "^:rcconf", text=_("Edit Arch configuration file (/etc/rc.conf)"),
                tt=_("Edit the /etc/rc.conf file to configure the live system"))
        ui.widget("OptionalFrame", ":larchify_advanced",
                text=_("Advanced Options"))
        ui.widget("Button", "^:initcpio", text=_("Edit mkinitcpio.conf"),
                tt=_("Edit the configuration file for generating the initramfs via mkinitcpio"))
        ui.widget("Button", "^:overlay", text=_("Edit overlay (open in file browser)"),
                tt=_("Open a file browser on the profile's 'rootoverlay'"))
        ui.widget("CheckBox", "^:ssh", text=_("Generate ssh keys"),
                tt=_("Enables pre-generation of ssh keys"))
        ui.widget("CheckBox", ":oldsquash", text=_("Reuse existing system.sqf"),
                tt=_("Reuse existing system.sqf, to save time if the base system hasn't changed"))
        ui.widget("Button", "^&-:build", text=_("Larchify"),
                tt=_("Build the main components of the larch system"))

        ui.widget("Frame", ":users", text=_("User accounts"))
        ui.widget("List", "^&-:utable", selectionmode="Single",
                tt=_("Click on a row to select, click on a selected cell to edit"))
        ui.widget("Button", "^&-:useradd", text=_("Add user"),
                tt=_("Create a new user-name"))
        ui.widget("Button", "^&:userdel", text=_("Delete user"),
                tt=_("Remove the selected user-name"))

        ui.layout(":page_larchify", ["*VBOX*", ":larchify", ":users", "*SPACE",
                ["*HBOX*", ":locales", "*SPACE", ":rcconf"], "*SPACE",
                ":larchify_advanced", ["*HBOX*", "*SPACE", "&-:build"]])
        ui.layout(":larchify_advanced", ["*HBOX*",
                ["*VBOX*", ":initcpio", ":overlay"], "*SPACE",
                ["*VBOX*", ":ssh", "*SPACE", ":oldsquash"]])
        ui.layout(":users", ["*VBOX*", "&-:utable",
                ["*HBOX*", "&-:useradd", "&:userdel", "*SPACE"]])

        self.userheaders = [_("User-Name"), _("Password"), _("Group"),
                "UID", _("'skel' directory"), _("Additional Groups"),
                _("Expert options")]
        ui.command("&-:utable.setHeaders", self.userheaders)
        ui.command("&-:utable.compact")
        ui.sendui("^&-:utable clicked")

        self.builder = Builder()
        self.sshgen = True


    def setup(self):
        """Set up the build page widget.
        """
        idir = config.ipath()
        if not os.path.isdir(idir + "/var/lib/pacman/local"):
            config_error(_("No Arch installation at %s") % idir)
            return False
        ui.command(":oldsquash.enable", self.builder.oldsqf_available())
        # ssh keys
        ssh = self.builder.ssh_available()
        self.sshgen = ssh and self.sshgen
        ui.command(":ssh.set", self.sshgen)
        ui.command(":ssh.enable", ssh)
        # users table
        ui.command(":users.enable", False if idir == '/' else True)
        self.readuserinfo()

#TODO: Remove hack if the underlying bug gets fixed
        # A hack to overcome a bug (?) in (py)qt
        ui.command(":larchify_advanced.enable_hack")
        return True

    def readuserinfo(self, select=None):
        """'select' should be a username, defaulting to the first entry.
        """
        self.usersel = 0
        self.userlist = []
        i = 0
        for u in self.builder.allusers():
            self.userlist.append(self.userinfolist(u))
            if u == select:
                self.usersel = i
            i += 1
        ui.command("&-:utable.set", self.userlist, self.usersel)
        ui.command("&-:utable.compact")

    def userinfolist(self, user):
        return [user] + self.builder.userinfo(user, USERINFO)

    def uedit(self, row, column):
        if self.usersel == row:
            uname = self.userlist[row][0]
            ulcell = self.userlist[row][column]
            if column == 4:
                ok, text = self.select_skel(ulcell)
            else:
                ok, text = ui.textLineDialog(self.userheaders[column] + ':',
                        text=ulcell)
            text = text.strip()
            if ok:
                try:
                    if (column == 0) and (text != ''):
                        # Rename the user, by adding a new one and deleting
                        # the old
                        uname = text
                        self.builder.newuser(uname)
                        i = 0
                        for f in USERINFO:
                            i += 1
                            self.builder.userset(uname, f, self.userlist[row][i])
                        self.builder.deluser(ulcell)

                    else:
                        self.builder.userset(uname, USERINFO[column-1], text)
                        self.builder.saveusers()

                except:
                    run_error(_("Couldn't adjust user definition"))
                self.readuserinfo(uname)

        else:
            self.usersel = row

    def select_skel(self, current):
        # Present a list of available 'skel' folders
        self.skellist = [_("Default (/etc/skel)")]
        for f in glob(config.get('profile') + '/skel_*'):
            self.skellist.append(f.rsplit("/skel_", 1)[1])
        try:
            i = self.skellist.index(current)
        except:
            i = 0
        skeli = ui.popuplist(self.skellist, index=i,
                title=_("Choose 'skel' Folder"),
                text=_("This folder will be copied\n"
                "to build the user's home folder:"))
        if skeli != None:
            return (True, "" if skeli <= 0
                    else self.skellist[skeli].split()[0])
        return (False, "")

    def useradd(self):
        ok, name = ui.textLineDialog(_("Enter login-name for new user:"))
        if ok:
            name = name.strip()
            if name != "" and self.builder.newuser(name):
                self.userlist.append(self.userinfolist(name))
                ui.command("&-:utable.set", self.userlist)
                ui.command("&-:utable.compact")

    def userdel(self):
        if self.usersel >= 0:
            user = self.userlist[self.usersel][0]
            if self.builder.deluser(user):
                del(self.userlist[self.usersel])
                ui.command("&-:utable.set", self.userlist)
                ui.command("&-:utable.compact")


    def sshtoggle(self, on):
        self.sshgen = on

    def locales(self):
        command.edit("rootoverlay/etc/locale.gen",
                config.ipath("etc/locale.gen"))

    def rcconf(self):
        command.edit("rootoverlay/etc/rc.conf", config.ipath("etc/rc.conf"))

    def initcpio(self):
        command.edit("rootoverlay/etc/mkinitcpio.conf.larch0",
                config.ipath("etc/mkinitcpio.conf.larch0"))

    def overlay(self):
        path = config.get("profile") + "/rootoverlay"
        if not os.path.isdir(path):
            os.mkdir(path)
        command.browser(path)


    def build(self):
        self.larchify(self.sshgen, ui.ask(":oldsquash.active"))


    def larchify(self, sshkeys, oldsquash):
        command.worker(self.builder.build,
                self.builder.ssh_available() and sshkeys,
                self.builder.oldsqf_available() and oldsquash)

