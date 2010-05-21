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
# 2010.03.07

import os, shutil


class InstallPage:
    """This class manages the page dealing with Arch installation.
    """
    def connect(self):
        return [
                (":addedpacks*clicked", self.edit_addedpacks),
                (":vetopacks*clicked", self.edit_vetopacks),
                (":pacmanconf*clicked", self.edit_pacmanconf),
                (":repos*clicked", self.edit_repos),
                (":mirrorlist_change*clicked", self.edit_mirrorlist),
                (":mirrorlist*toggled", self.toggle_mirrorlist),
                (":use_local_mirror*toggled", self.toggle_local_mirror),
                ("&-:local_mirror_change*clicked", self.new_local_mirror_path),
                ("&-:cache_change*clicked", self.new_cache_path),
                ("&-:install*clicked", self.install),
                ("$*set_build_mirror*$", self.set_build_mirror),
                ("$*set_pacman_cache*$", self.set_pacman_cache),
            ]


    def __init__(self):
        ui.widget("Frame", ":edit_profile", text=_("Edit Profile"))
        ui.widget("Button", "^:addedpacks", text=_("Edit 'addedpacks'"),
                tt=_("Edit the list of packages to be installed"))
        ui.widget("Button", "^:vetopacks", text=_("Edit 'vetopacks'"),
                tt=_("Edit the list of group member packages NOT to install"))
        ui.widget("Button", "^:pacmanconf", text=_("Edit pacman.conf options"),
                tt=_("Edit pacman.conf options - not the repositories"))
        ui.widget("Button", "^:repos", text=_("Edit pacman.conf repositories"),
                tt=_("Edit the repository entries for pacman.conf"))

        ui.widget("OptionalFrame", ":settings_advanced", text=_("Advanced Options"))

        ui.widget("OptionalFrame", "^:mirrorlist", text=_("Use project mirrorlist"),
                tt=_("Enables use of the mirrorlist file saved in the working directory, for installation only"))
        ui.widget("Button", "^:mirrorlist_change", text=_("Edit project mirrorlist"),
                tt=_("Edit mirrorlist in working directory"))

        ui.widget("OptionalFrame", "^:use_local_mirror", text=_("Use special mirror for installation"),
                tt=_("Allows a specific (e.g. local) mirror to be used just for the installation"))
        ui.widget("Label", ":l1", text=_("URL:"))
        ui.widget("LineEdit", ":local_mirror", ro=True,
                tt=_("The url of the installation mirror"))
        ui.widget("Button", "^&-:local_mirror_change", text=_("Change"),
                tt=_("Change the installation mirror path"))

        ui.widget("Label", ":cache", text=_("Package Cache:"))
        ui.widget("LineEdit", ":cache_show", ro=True,
                tt=_("The path to the (host's) package cache"))
        ui.widget("Button", "^&-:cache_change", text=_("Change"),
                tt=_("Change the package cache path"))

        ui.widget("Button", "^&-:install", text=_("Install"),
                tt=_("This will start the installation to the set path"))

        ui.layout(":page_installation", ["*VBOX*", ":edit_profile",
                ":settings_advanced", "*HLINE",
                ["*HBOX*", "*SPACE", "&-:install"]])
        ui.layout(":edit_profile", ["*GRID*",
                ["*+*", ":addedpacks", ":vetopacks"],
                ["*+*", ":pacmanconf", ":repos"]])
        ui.layout(":settings_advanced", ["*VBOX*",
                ["*HBOX*", ":mirrorlist", ":use_local_mirror"],
                ["*HBOX*", ":cache", ":cache_show", "&-:cache_change"]])
        ui.layout(":mirrorlist", ["*HBOX*", ":mirrorlist_change"])
        ui.layout(":use_local_mirror", ["*HBOX*", ":l1", ":local_mirror", "&-:local_mirror_change"])


    def setup(self):
        """Set up the installation page widget.
        """
        self.profile = config.get("profile")
        ui.command(":cache_show.x__text", config.get("pacman_cache"))

        ulm = (config.get("uselocalmirror") != "")
        ui.command(":mirrorlist.opton", config.get("usemirrorlist") != "")
        ui.command(":mirrorlist.enable", not ulm)
        ui.command(":use_local_mirror.opton", ulm)
        ui.command(":local_mirror.x__text", config.get("localmirror"))
        return True


    def edit_addedpacks(self):
        command.edit("addedpacks")

    def edit_vetopacks(self):
        command.edit("vetopacks", "")

    def edit_pacmanconf(self):
        command.edit("pacman.conf.options",
                os.path.join(base_dir, "data", "pacman.conf"),
                label=_("Editing pacman.conf options only"),
                filter=installation.pacmanoptions)

    def edit_repos(self):
        command.edit("pacman.conf.larch",
                os.path.join(base_dir, "data", "pacman.conf.larch"),
                label=_("Editing pacman.conf repositories only"))

    def edit_mirrorlist(self):
        f = config.working_dir + "/mirrorlist"
        fi = "/etc/pacman.d/mirrorlist"
        if not os.path.isfile(fi):
            # This file should only be necessary on non-Arch hosts -
            #   it is supplied in the pacman-allin package
            fi = base_dir + "/data/mirrorlist"
            if not os.path.isfile(fi):
                config_error(_("No 'mirrorlist' file found"))
                return
        command.edit(f, fi, label=_("Editing mirrorlist: Uncomment ONE entry"))


    def toggle_mirrorlist(self, on):
        config.set("usemirrorlist", "yes" if on else "")


    def toggle_local_mirror(self, on):
        config.set("uselocalmirror", "yes" if on else "")
        ui.command(":mirrorlist.enable", not on)


    def new_local_mirror_path(self):
        # Is anything more necessary? Do I need to test the path?
        # Would a directory browser be better?
        ok, path = ui.ask("textLineDialog",
                _("Enter new local mirror path:"),
                None, config.get("localmirror"))
        if ok:
            if "://" in path:
                self.set_build_mirror(path)
            else:
                config_error(_("You must specify a URL, with protocol,"
                        " e.g. 'file:///a/b/c'"))


    def set_build_mirror(self, path):
        path = path.strip().rstrip("/")
        config.set("localmirror", path)
        ui.command(":local_mirror.x__text", path)


    def new_cache_path(self):
        # Is anything more necessary? Do I need to test the path?
        # Would a directory browser be better?
        ok, path = ui.ask("textLineDialog",
                _("Enter new package cache path:"),
                None, config.get("pacman_cache"))
        if ok:
            self.set_pacman_cache(path)


    def set_pacman_cache(self, path):
            path = path.strip().rstrip("/")
            config.set("pacman_cache", path)
            ui.command(":cache_show.x__text", path)


    def install(self):
        command.worker(installation.install)
