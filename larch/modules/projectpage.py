#!/usr/bin/env python
#
# projectpage.py
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

import os


class ProjectPage:
    """This class manages the page dealing with project settings.
    """
    def connect(self):
        return [
                (":platform*changed", self.switch_platform),
                (":choose_profile_combo*changed", self.switch_profile),
                ("&-:profile_rename*clicked", self.get_new_profile_name),
                ("&-:profile_browse*clicked", self.new_profile),
                ("&-:profile_delete*clicked", self.delete_profile),
                ("&-:installation_path_change*clicked", self.get_new_installation_path),
                (":choose_project_combo*changed", self.switch_project),
                ("&-:new_project*clicked", self.get_new_project_name),
                ("&-:project_delete*clicked", self.delete_project),
                ("$*new_project_name*$", self.new_project_name),
                ("$*rename_profile*$", self.rename_profile),
                ("$*make_new_profile*$", self.make_new_profile),
                ("$*set_ipath*$", self.set_ipath),
            ]

    def __init__(self):
        ui.widget("Frame", ":settings_profile", text=_("Profile"))
        ui.widget("Label", ":choose_profile", align="right",
                text=_("Choose Existing Profile:"))
        ui.widget("Label", ":new_profile", align="right",
                text=_("New Profile:"))
        ui.widget("ComboBox", "^:choose_profile_combo",
                tt=_("Choose a profile from those already in your larch working folder"))
        ui.widget("Button", "^&-:profile_browse", text=_("Browse for Profile"),
                tt=_("Fetch a profile from the file-system"))
        ui.widget("Button", "^&-:profile_rename", text=_("Rename"),
                tt=_("Rename the current profile"))
        ui.widget("Button", "^&-:profile_delete", text=_("Delete"),
                tt=_("Delete the current profile"))

        ui.widget("Label", ":lplat", text=_("Platform (processor architecture):"))
        ui.widget("ComboBox", "^:platform",
                tt=_("Which processor architecture?"))

        ui.widget("OptionalFrame", ":options_advanced", text=_("Advanced Options"))

        ui.widget("Frame", ":project", text=_("Project"))
        ui.widget("Label", ":choose_project", text=_("Choose Existing Project:"))
        ui.widget("ComboBox", "^:choose_project_combo",
                tt=_("Choose a project from those already defined"))
        ui.widget("Button", "^&-:new_project", text=_("New Project"),
                tt=_("Create a new project"))
        ui.widget("Button", "^&-:project_delete", text=_("Delete"),
                tt=_("Delete the current project"))

        ui.widget("Label", ":installation_path", text=_("Installation Path:"))
        ui.widget("LineEdit", ":installation_path_show", ro=True,
                tt=_("The root directory of the Arch installation to larchify"))
        ui.widget("Button", "^&-:installation_path_change", text=_("Change"),
                tt=_("Change the root directory of the Arch installation"))

        ui.layout(":page_settings", ["*VBOX*", ":settings_profile",
                "*SPACE", ["*HBOX*", "*SPACE", ":lplat", ":platform"],
                ":options_advanced"])
        ui.layout(":settings_profile", ["*GRID*",
                ["*+*", ":choose_profile", ":choose_profile_combo", "*VLINE", "&-:profile_rename"],
                ["*+*", ":new_profile",    "&-:profile_browse",       "*|",   "&-:profile_delete"]])
        ui.layout(":options_advanced", ["*VBOX*", ":project",
                ["*HBOX*", ":installation_path", ":installation_path_show",
                        "&-:installation_path_change"]])
        ui.layout(":project", ["*HBOX*", ":choose_project", ":choose_project_combo",
                "&-:new_project", "&-:project_delete"])


    def setup(self):
        """Set up the project page widget.
        The widget needs config.get("install_path").
        It also needs the list of available profiles (got from listing the
        dirs in the profiles folder in the working directory -
        config.working_dir) and the currently selected profile -
        config.get("profile").
        It needs the list of available projects - config.getsections().
        Also the currently selected project name is needed - config.project.
        """
        self.profiles = config.profiles()
        self.profile = config.get("profile")
        pdn = os.path.dirname(self.profile)
        self.profilename = os.path.basename(self.profile)
        if pdn != config.profile_dir:
            config_error(_("Profile directory mismatch: '%s' vs. '%s'") %
                    (pdn, config.profile_dir))
            self.profile = None
            config.defaultprofile()
            self.profilename = os.path.basename(self.profile)
            config.set("profile", self.profile)
        elif self.profilename not in self.profiles:
            config_error(_("Profile '%s' doesn't exist") % self.profile)
            self.profile = None
        if not self.profile:
            self.profile = config.defaultprofile()
            self.profilename = os.path.basename(self.profile)
            config.set("profile", self.profile)
        self.projects = config.getsections()
        self.projects.sort()
        self.project = config.project

        i = config.platforms.index(config.get("platform"))
        ui.command(":platform.set", config.platforms, i)

        ui.command(":choose_profile_combo.set", self.profiles,
                self.profiles.index(self.profilename))
        ui.command(":choose_project_combo.set", self.projects,
                self.projects.index(self.project))
        installpath = config.get("install_path")
        ui.command(":installation_path_show.x__text", installpath)
        command.enable_install()
        return True


    def switch_platform(self, index):
        """This has no effect on the display!
        It is assumed that the display is already updated, or will be
        updated later.
        Invalidates the installation for another platform.
        """
        config.set("platform", config.platforms[index])
        self.setup()


    def switch_profile(self, index):
        """This has no effect on the display!
        It is assumed that the display is already updated, or will be
        updated later, and that the index is valid, so that the operation
        cannot fail.
        """
        self.profile = config.profile_dir + "/" + self.profiles[index]
        config.set("profile", self.profile)


    def new_profile(self):
        ok, source, name = ui.ask("specialFileDialog",
                _("Select profile source folder and enter new name"),
                config.profile_dir, _("New name:"),
                (config.profile_dir, base_dir + "/profiles",
                config.current_dir, config.home_dir))
        if ok:
            self.make_new_profile(source, name)


    def make_new_profile(self, source, name):
        profile = config.copyprofile(name, source)
        if profile:
            config.set("profile", profile)
            self.setup()


    def get_new_profile_name(self):
        if self.check_profile(self.profile):
            ok, new = ui.textLineDialog(
                    _("Enter new name for current profile:"),
                    text=self.profilename)
            if ok:
                self._rename_profile(new)


    def rename_profile(self, name):
        if self.check_profile(self.profile):
             self._rename_profile(name)


    def _rename_profile(self, name):
        if config.renameprofile(name):
            self.setup()


    def delete_profile(self, name=None):
        if name:
            p = os.path.join(config.profile_dir, name)
            if p == self.profile:
                name = None
        else:
            p = self.profile

        if self.check_profile(p) and ui.confirmDialog(
                _("Do you really want to delete profile '%s'?")
                % os.path.basename(p)):
            config.deleteprofile(p)
            if not name:
                self.setup()


    def check_profile(self, p):
        proj = config.checkprofile(p)
        if proj:
            config_error(_("Profile '%s' in use by project '%s") %
                    (os.path.basename(p), proj))
        return proj == None


    def get_new_installation_path(self):
        # Is anything more necessary? Do I need to test or create the path?
        # I don't think so, the installation code does that.
        # If the path is "/", the installation page should be inhibited,
        # but that is handled by 'setup'.
        ok, path = ui.textLineDialog(
                _("WARNING: Double check your path -\n"
                "  If you make a mistake here it could destroy your system!"
                "\n\nEnter new installation path:"),
                text=config.get("install_path"))
        if ok:
            self.set_ipath(path)


    def set_ipath(self, path):
        ip = "/" + path.strip().strip("/")
        if (ip != "/") and os.path.isdir(ip):
            ok = 0
            nok = []
            for f in os.listdir(ip):
                if f in ("bin", "boot", "dev", "etc", "home", "lib", "media",
                        "mnt", "opt", "proc", "root", "sbin", "srv", "sys",
                        "tmp", "usr", "var", ".larch", ".ARCH"):
                    ok += 1
                else:
                    ok -= 1
                    nok.append(f)
            if ok < 0:
                if not ui.confirmDialog(_("Your selected installation path"
                        " (%s) contains unexpected items:\n %s\n"
                        "\nIs that really ok?") %
                        (ip, " ".join(nok))):
                    return
        config.set("install_path", ip)
        self.setup()


    def switch_project(self, index):
        config.setproject(self.projects[index])
        self.setup()


    def get_new_project_name(self):
        ok, new = ui.textLineDialog(_("Enter name for new project:"),
                text=self.project)
        if ok:
            self.new_project_name(new)


    def new_project_name(self, name):
        if name in self.projects:
            config_error(_("Project '%s' already exists.") % name)
        else:
            config.setproject(name)
            self.setup()


    def delete_project(self, name=None):
        if len(self.projects) < 2:
            config_error(_("Can't delete the only existing project."))
            return
        if name:
            p = name
            if name == self.project:
                name = None
        else:
            p = self.project
        if ui.confirmDialog(_("Do you really want to delete project '%s'?")
                % p):
            config.deleteproject(p)
            if not name:
                self.setup()
