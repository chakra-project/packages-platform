#!/usr/bin/env python
#
# installation.py
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

"""This module handles the Arch system which has been or will be installed
to be made into a larch live system. If the installation path is "/" (i.e.
for larchifying the running system) this module will not be used.
"""

import os, filecmp
from subprocess import call, PIPE, STDOUT

class Installation:
    def __init__(self):
        self.pacman_cmd = None


    def make_pacman_conf(self, mirror="final"):
        """Construct the pacman.conf file used by larch.
        This pacman.conf must be regenerated if anything concerning the
        repositories changes. To simplify matters it should be regenerated
        every time it is used.
        The 'mirror' parameter allows the generated pacman.conf to be tweaked
        slightly. With its default value, "final", the version for the live
        system is generated (as specified in pacman.conf.larch); if the
        value is "local", a local mirror will be used for all repositories
        which it supplies. Otherwise entries specified by 'Include' will
        use the specified mirrorlist unless it is '/etc/pacman.d/mirrorlist'
        and 'usemirrorlist' is set. In that case the edited mirrorlist will
        be used (just for building - it doesn't affect the live system itself).
        If that is not the case the host must have a valid
        /etc/pacman.d/mirrorlist.
        The return value is a list of the names of the repositories which
        are included.

        To make it a little easier to manage upstream changes to the default
        pacman.conf, a separate file (pacman.conf.larch) is used to specify
        the repositories to use. The contents of this file are used to modify
        the basic pacman.conf file, which may be the default version or one
        provided in the profile.
        """
        platform = config.get("platform")
        if mirror == "local":
            localmirror = config.get("localmirror")
        else:
            localmirror = None
        repos = []
        pc0 = config.get("profile") + "/pacman.conf.options"
        if not os.path.isfile(pc0):
            pc0 = base_dir + "/data/pacman.conf"
        pc1 = config.get("profile") + "/pacman.conf.larch"
        if not os.path.isfile(pc1):
            pc1 = base_dir + "/data/pacman.conf.larch"

        fhi = open(pc0)
        fho = open(config.working_dir + "/pacman.conf", "w")
        fho.write(self.pacmanoptions(fhi.read()))
        fhi.close()

        # Get the repositories from pacman.conf.larch
        #  - first find a substitute for /etc/pacman.d/mirrorlist
        f = config.working_dir + "/mirrorlist"
        if config.get("usemirrorlist") and os.path.isfile(f):
            mf = f
        else:
            mf = None

        # - then update the Server entries, if necessary
        fhi = open(pc1)
        section = ""
        for line in fhi:
            if line.startswith("["):
                section = line.strip().strip("[]")
                repos.append(section)
            if section:
                if line.startswith("Server") or line.startswith("Include"):
                    if (mirror == "local"):
                        line = "Server = %s\n" % localmirror.replace(
                                "*repo*", section)
                    elif (mirror != "final") and line.startswith("Include"):
                        s = line.split("=", 1)[1].split("#")[0].strip()
                        if s == "/etc/pacman.d/mirrorlist":
                            if mf:
                                line = "Include = %s\n" % mf
                            elif not os.path.isfile("/etc/pacman.d/mirrorlist"):
                                smlist = base_dir + "/data/mirrorlist"
                                if os.path.isfile(smlist):
                                    line = "Include = %s\n" % smlist
                                else:
                                    config_error(_("No 'mirrorlist' file found"))
                                    break

                    line = line.replace("*platform*", platform)
                fho.write(line)
            if not line.strip():
                section = ""

        fhi.close()
        fho.close()
        return repos


    def make_pacman_command(self):
        """Construct pacman command. This must be regenerated if the
        working directory, the installation path or the cache directory
        changes. It might be easier to regenerate every time pacman is used.
        """
#TODO? Allow disabling of progress output?
#        self.pacman_cmd = ("%s -r %s --config %s --noconfirm --noprogressbar" %
        self.pacman_cmd = ("%s -r %s --config %s --noconfirm" %
                (config.pacman, config.get("install_path"),
                 config.working_dir + "/pacman.conf"))
        cache = config.get("pacman_cache")
        if cache:
            self.pacman_cmd += " --cachedir %s" % cache


    def install(self):
        """Clear the chosen installation directory and install the base
        set of packages, together with any additional ones listed in the
        file 'addedpacks' (in the profile).
        """
        installation_path = config.ipath()

        # Can't delete the whole directory because it might be a mount point
        if os.path.isdir(installation_path):
            command.script("cleardir %s" % installation_path)

        # Ensure installation directory exists and check that device nodes
        # can be created (creating /dev/null is also a workaround for an
        # Arch bug - which may have been fixed, but this does no harm)
        if not (supershell("mkdir -p %s/{dev,proc,sys}" % installation_path)[0]
                and supershell("mknod -m 666 %s/dev/null c 1 3" %
                installation_path)[0]):
            config_error(_("Couldn't write to the installation path (%s).") %
                    installation_path)
            return False
        if not supershell("echo 'test' >%s/dev/null" % installation_path)[0]:
            config_error(_("The installation path (%s) is mounted 'nodev'.") %
                    installation_path)
            return False

        # I should also check that it is possible to run stuff in the
        # installation directory.
        supershell("cp $( which echo ) %s" % installation_path)
        if not supershell("%s/echo 'yes'" % installation_path)[0]:
            config_error(_("The installation path (%s) is mounted 'noexec'.") %
                    installation_path)
            return False
        supershell("rm %s/echo" % installation_path)

        # Fetch package database
        if not (supershell("mkdir -p %s/var/lib/pacman" % installation_path)[0]
                and self.update_db()):
            return False

        # Get list of packages in 'base' group, removing those in the
        # list of vetoed packages.
        self.veto_packages = []
        veto_file = config.get("profile") + "/vetopacks"
        if os.path.isfile(veto_file):
            fh = open(veto_file)
            for line in fh:
                line = line.strip()
                if line and (not line.startswith("#")):
                    self.veto_packages.append(line)
            fh.close()
        self.make_pacman_command()
        self.packages = []
        self.add_group('base')

        # The larch-live package and dependencies must be installed
        self.packages.append("larch-live")

        # Add additional packages and groups, from 'addedpacks' file.
        addedpacks_file = config.get("profile") + "/addedpacks"
        fh = open(addedpacks_file)
        for line in fh:
            line = line.strip()
            if (line and (line[0] != '#')):
                if line[0] == '*':
                    self.add_group(line[1:])
                elif line not in self.packages:
                    self.packages.append(line)
        fh.close()

        # Now do the actual installation.
        ok = self.pacmancall("-S", " ".join(self.packages))
        if not ok:
            config_error(_("Package installation failed"))
        else:
            # Some chroot scripts might need /etc/mtab
            supershell(":> %s/etc/mtab" % installation_path)

            # Build the final version of pacman.conf
            self.make_pacman_conf("final")
            supershell("cp -f %s %s" % (
                    config.working_dir + "/pacman.conf",
                    installation_path + "/etc/pacman.conf"))
            # Replace mirrorlist - I think this shouldn't be done!
#            mf = config.working_dir + "/mirrorlist"
#            if not (config.get("usemirrorlist") and os.path.isfile(mf)):
#                mf = "/etc/pacman.d/mirrorlist"
#                if not os.path.isfile(mf):
#                    mf = None
#            if mf:
#                supershell("cp -f %s %s" % (mf,
#                        installation_path + "/etc/pacman.d/mirrorlist"))

        # Make a note of the installation's architecture
        supershell("echo '%s' > %s" % (config.get("platform"),
                installation_path + "/.ARCH"))
        command.enable_install()
        return ok


    def add_group(self, gname):
        """Add the packages belonging to a group to the installaion list,
        removing any in the veto list.
        """
        # In the next line the call could be done as a normal user.
        for line in supershell('%s -Sg %s' % (self.pacman_cmd, gname))[1]:
            l = line.split()
            if l and (l[0] == gname) and (l[1] not in self.veto_packages):
                self.packages.append(l[1])


    def update_db(self):
        """This updates or creates the pacman-db in the installation.
        This is done using using 'pacman ... -Sy' together with
        an appropriate pacman.conf file.
        """
        ok = self.x_pacman("-Sy", mounts=False, check=False)
        if not ok:
            run_error(_("Couldn't synchronize pacman database (pacman -Sy)"))
        return ok


    def x_pacman(self, op, arg="", mounts=True, check=True):
        if check and not command.check_platform():
            return False
        self.make_pacman_conf("local" if config.get("uselocalmirror") else "")
        self.make_pacman_command()
        if mounts:
            return self.pacmancall(op, arg)
        else:
            return supershell("%s %s %s" % (self.pacman_cmd, op, arg))[0]


    def pacmancall(self, op, arg):
        """Mount-bind the sys and proc directories before calling the
        pacman command built by make_pacman_command to perform operation
        'op' (e.g. '-S') with argument(s) 'arg' (a string).
        Then unmount sys and proc and return True if the command succeeded.
        """
        ipath = config.ipath()
        # (a) Prepare the destination environment (bind mounts)
        command.mount("/sys", "%s/sys" % ipath, "--bind")
        command.mount("/proc", "%s/proc" % ipath, "--bind")

        # (b) Call pacman
        # Note that I will probably want incremental output from this.
        ok = supershell("%s %s %s" % (self.pacman_cmd, op, arg))[0]

        # (c) Remove bound mounts
        command.unmount(("%s/sys" % ipath, "%s/proc" % ipath))
        return ok


    def pacmanoptions(self, text):
        """A filter for pacman.conf to remove the repository info.
        """
        texto = ""
        block = ""
        for line in text.splitlines():
            block += line + "\n"
            if line.startswith("#["):
                break
            if line.startswith("[") and not line.startswith("[options]"):
                break
            if not line.strip():
                texto += block
                block = ""
        return texto

