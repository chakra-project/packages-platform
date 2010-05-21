#!/usr/bin/env python
#
# installpage.py
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

import os, shutil


class TweakPage:
    """This class manages the page dealing with Arch installation.
    """
    def connect(self):
        return [
                ("&-:sync*clicked", self.dosync),
                ("&-:update*clicked", self.doupdate),
                ("&-:add*clicked", self.doadd),
                ("&-:remove*clicked", self.doremove),
                ("&*pacmanU*&", self.pacmanU),
                ("&*pacmanS*&", self.pacmanS),
                ("&*pacmanR*&", self.pacmanR),
            ]


    def __init__(self):
        ui.widget("Frame", ":pacmanops", text=_("Package Management"))
        ui.widget("Button", "^&-:sync", text=_("Synchronize db"),
                tt=_("Synchronize the pacman db on the target (pacman -Sy)"))
        ui.widget("Button", "^&-:update", text=_("Update / Add package    [-U]"),
                tt=_("Update / Add a package from a package file using pacman -U"))
        ui.widget("Button", "^&-:add", text=_("Add package(s)    [-S]"),
                tt=_("Add one or more packages (space separated) using pacman -S"))
        ui.widget("Button", "^&-:remove", text=_("Remove package(s)    [-Rs]"),
                tt=_("Remove one or more packages (space separated) using pacman -Rs"))

        ui.layout(":page_tweaks", ["*VBOX*", ":pacmanops", "*SPACE"])
        ui.layout(":pacmanops", ["*GRID*",
                ["*+*", "&-:sync", "&-:update"],
                ["*+*", "&-:add", "&-:remove"]])


    def setup(self):
        """Set up the tweak page widget.
        """
        self.profile = config.get("profile")
        return True


    def dosync(self):
        command.worker(installation.update_db)


    def doupdate(self):
        f = ui.ask("fileDialog", _("Package to add/update"),
                None, "pacman -U", False, False,
                (_("Packages"), "*.pkg.tar.gz"))
        if f:
            command.worker(self.pacmanU, f)


    def pacmanU(self, flist):
        if not installation.x_pacman("-U", flist):
            run_error(_("Error during package update."))


    def doadd(self):
        ok, plist = ui.ask("textLineDialog",
                _("Enter the names of packages to install -"
                "\n  separated by spaces:"),
                "pacman -S")
        if ok:
            command.worker(self.pacmanS, plist.strip())


    def pacmanS(self, plist):
        if plist and not installation.x_pacman("-S", plist):
            run_error(_("Error during package installation."))


    def doremove(self):
        ok, plist = ui.ask("textLineDialog",
                _("Enter the names of packages to remove -"
                "\n  separated by spaces:"),
                "pacman -Rs")
        if ok:
            command.worker(self.pacmanR, plist.strip())


    def pacmanR(self, plist):
        if plist and not installation.x_pacman("-Rs", plist):
            run_error(_("Error during package removal."))
