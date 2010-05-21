#!/usr/bin/env python
#
# base.py
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

"""This module handles the basic framework and configuration of the
larch build system.

Access configs only via config.get and config.set (as far as possible).
"""

import sys, os, shutil
from ConfigParser import SafeConfigParser

config_dir = ".config/larch"        # within the user's home directory
config_file = "larch-config"        # within config_dir
project0 = "larch0"

# Some default values for the config file
defaults = {    "install_path"  : "/home/larchbuild",
                "pacman_cache"  : "/var/cache/pacman/pkg",
                "profile"       : "",       # => Use default, needs initialization
                "platform"      : "",       # => Needs initialization
                "uselocalmirror" : "",
                "localmirror"   : "",
                "usemirrorlist" : "",
                "dl_progress"   : "",               # Not used
                "filebrowser"   : "xdgx-open $",
                "html_reader"   : "xdg-open $",     # Not used
                "medium_iso"    : "yes",    # "yes" / ""
                "medium_btldr"  : "grub",   # "grub" / "syslinux" / "none"
                "medium_search" : "search", # "search" / "uuid" / "label" / "device"
                "medium_label"  : "CHAKRA",
                "isoA"          : "chakra",
                "isopublisher"  : "designed by Chakra-Developers-Team, licence: GPL",
    }


class LarchConfig:
    # The following paths are all based on the installation directory (as
    # they would be found within a chroot command), so if you want to
    # address them from the host, run them through the ipath function.
    larch_build_dir = "/.larch"
    medium_dir = "/.larch/cd"
    overlay_build_dir = "/.larch/tmp/overlay"
    system_sqf = "/.larch/system.sqf"

    def __init__(self, home):
        self.current_dir = os.getcwd()
        self.home_dir = home

        # The working directory is by default within the config directory.
        # If you want it somewhere else, move it there and sym-link it from
        # the original path.
        self.working_dir = os.path.join(home, config_dir, "working_dir")
        self.profile_dir = os.path.join(self.working_dir, "MyProfiles")
        if not os.path.isdir(self.working_dir):
            # If the config directory itself doesn't yet exist, this will
            # also create that.
            os.makedirs(self.working_dir)

        self.pacman = "/usr/bin/pacman"
        if not os.path.isfile(self.pacman):
            # If the host is not Arch, there will be no pacman.
            # (If there is some other program at "/usr/bin/pacman" that's
            # a real spanner in the works.)
            self.pacman = base_dir + "/pacman"
            if not os.path.isfile(self.pacman):
                fatal_error(_("No pacman executable found"))

        # Use the ConfigParser module to handle the low level aspects of
        # the config file.
        self.config = SafeConfigParser()
        self.config_file = os.path.join(home, config_dir, config_file)
        if not os.path.isfile(self.config_file):
            open(self.config_file, 'w').close()

        self.config.read(self.config_file)
        sections = self.config.sections()
        # Use "_" as the top-level section (ConfigParser can't handle
        # unsectioned data)
        if "_" not in sections:
            self.newsection("_")
        # The main (only?) setting in this section is the project, which
        # in most cases will never change from the default.

        if self.config.has_option("_", "project"):
            project = self.config.get("_", "project")
        else:
            project = project0
        self.architecture = os.uname()[4]
        if self.architecture == "i686":
            self.platforms = ["i686"]
        elif self.architecture == "x86_64":
            self.platforms = ["x86_64", "i686"]
        else:
            fatal_error(_("Unknown platform: '%s'") % self.architecture)
        self.setproject(project)


    def ipath(self, path=""):
        p = self.get("install_path").rstrip("/")
        x = path.strip("/")
        if x:
            return p + "/" + x
        elif p:
            return p
        else:
            return "/"


    def setproject(self, project):
        if project not in self.getsections():
            # Create a section for the project.
            self.newsection(project)
        # Set as current project.
        self.config.set("_", "project", project)
        self.update()

        self.project = project

        if not self.get("profile"):
            self.set("profile", self.defaultprofile())

        if not self.get("platform"):
            # Is cross-platform building possible? It is conceivable that
            # an i686 larch system could be built on an x86_64 platform.
            self.set("platform", self.architecture)


    def get(self, item):
        if self.config.has_option(self.project, item):
            return self.config.get(self.project, item)
        elif defaults.has_key(item):
            return defaults[item]
        sys.stderr.write(_("Unknown configuration option: %s\n") % item)
        sys.stderr.flush()
        assert False


    def checkprofile(self, profile):
        for proj in self.getsections():
            if proj == self.project:
                continue
            if self.config.get(proj, "profile") == profile:
                return proj
        return None


    def set(self, item, value):
        self.config.set(self.project, item, value)
        self.update()


    def newsection(self, section):
        self.config.add_section(section)


    def getsections(self):
        s = self.config.sections()
        s.remove("_")
        return s


    def update(self):
        configfile = open(self.config_file, 'w')
        self.config.write(configfile)
        configfile.close()


    def profiles(self):
        return os.listdir(self.profile_dir)


    def defaultprofile(self):
        dprofile = self.profile_dir + "/default"
        if not os.path.isdir(dprofile):
            self.copyprofile()
        return dprofile


    def copyprofile(self, pname="default", psource=None):
        """Create a new profile folder with the given name in the working
        directory by copying it from the path in 'psource' (by default
        the folder of the same name within the profiles folder supplied
        in the larch distribution). Note that if 'psource' is given it must
        include the source profile name, this is not added, thus allowing
        the name to be changed.
        """
        if pname:
            if not psource:
                psource = os.path.join(base_dir, "profiles", pname)
        elif psource:
            pname = os.path.basename(psource)
        else:
            config_error(_("No name for new profile"))
            return None
        ppath = os.path.join(self.profile_dir, pname)
        if os.path.isdir(ppath):
            config_error(_("Profile '%s' already exists") % pname)
            return None
        shutil.copytree(psource, ppath, symlinks=True)
        return ppath


    def setprofile(self, name):
        self.set("profile", os.path.join(self.profile_dir, name))


    def renameprofile(self, newname):
        pnew = os.path.join(self.profile_dir, newname)
        pold = self.get("profile")
        if os.path.exists(pnew):
            config_error(_("Profile '%s' exists already.") % newname)
            return False
        os.rename(pold, pnew)
        self.set("profile", pnew)
        return True


    def deleteprofile(self, path):
        shutil.rmtree(path)
        if path == self.get("profile"):
            self.set("profile", self.defaultprofile())


    def deleteproject(self, name):
        if self.config.remove_section(name) and name == self.project:
            self.setproject(self.getsections()[0])
