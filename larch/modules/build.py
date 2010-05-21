#!/usr/bin/env python
#
# build.py
#
# (c) Copyright 2009 Michael Towers (larch42 at googlemail dot com)
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
# 2010.03.22

import os, sys
from glob import glob
from subprocess import Popen, PIPE, STDOUT
from ConfigParser import SafeConfigParser
import random, crypt

# Default list of 'additional' groups for a new user
BASEGROUPS = 'video,audio,optical,storage,scanner,power,camera'
# User table fields (apart from the first column - the login name)
USERINFO = ['pw', 'maingroup', 'uid', 'skel', 'xgroups', 'expert']

class Builder:
    """This class manages 'larchifying' an Arch Linux installation.
    """
    def __init__(self):
        pass

    def oldsqf_available(self):
        self.installation_dir = config.ipath()
        # Define the working area - it must be inside the installation
        # because of the use of chroot for some functions
        self.larch_dir = config.ipath(config.larch_build_dir)
        # Location for the live medium image
        self.medium = config.ipath(config.medium_dir)

        self.system_sqf = config.ipath(config.system_sqf)
        if os.path.isfile(self.medium + "/larch/system.sqf"):
            return True
        else:
            return os.path.isfile(self.system_sqf)


    def ssh_available(self):
        return os.path.isfile(config.ipath("usr/bin/ssh-keygen"))


    def build(self, sshgen, useoldsqf):
        self.installation0 = self.installation_dir if self.installation_dir != "/" else ""
        if not (self.installation0 or ui.confirmDialog(_(
                    "Building a larch live medium from the running system is\n"
                    "an error prone process. Changes to the running system\n"
                    "made while running this function may be only partially\n"
                    "incorporated into the compressed system images.\n\n"
                    "Do you wish to continue?"))):
                return False

        self.profile = config.get("profile")
        self.overlay = config.ipath(config.overlay_build_dir)
        command.log("#Initializing larchify process")

        if useoldsqf:
            if os.path.isfile(self.medium + "/larch/system.sqf"):
                supershell("mv %s/larch/system.sqf %s" %
                        (self.medium, self.larch_dir))
        else:
            supershell("rm -f %s" % self.system_sqf)

        # Clean out temporary area and create overlay directory
        supershell("rm -rf %s/tmp && mkdir -p %s" %
                (self.larch_dir, self.overlay))

        if not self.find_kernel():
            return False

        if not self.system_check():
            return False

        command.log("#Beginning to build larch medium files")
        # Clear out the directory
        supershell("rm -rf %s && mkdir -p %s/{boot,larch}" %
                (self.medium, self.medium))

        # kernel
        supershell("cp -f %s/boot/%s %s/boot/larch.kernel" %
                (self.installation0, self.kname, self.medium))
        # Remember file name (to ease update handling)
        supershell("echo '%s' > %s/larch/kernelname"
                % (self.kname, self.medium))

        # if no saved system.sqf, squash the Arch installation at self.installation_dir
        if not os.path.isfile(self.system_sqf):
            command.log("#Generating system.sqf")
            # root directories which are not included in the squashed system.sqf
            ignoredirs = "boot dev mnt media proc sys tmp .livesys "
            ignoredirs += config.larch_build_dir.lstrip("/")
            # /var stuff
            ignoredirs += " var/log var/tmp var/lock var/cache/pacman/pkg"
            # others
            ignoredirs += " usr/lib/locale"

            # Additional directories to ignore can also be specified in the
            # profile. This is a nasty option. It was requested, and might
            # be useful under certain special circumstances, but I recommend
            # not using it unless you are really sure what you are doing.
            veto_file = self.profile + '/vetodirs'
            if os.path.isfile(veto_file):
                fh = open(veto_file)
                for line in fh:
                    line = line.strip()
                    if line and (line[0] != '#'):
                        ignoredirs += ' ' + line.lstrip('/')
                fh.close()

            if not command.chroot("/sbin/mksquashfs '/' '%s' -e %s"
                    % (config.system_sqf, ignoredirs)):
                command.error("Warning", _("Squashing system.sqf failed"))
                return False
            # remove execute attrib
            supershell("chmod oga-x %s" % self.system_sqf)

        # move system.sqf to medium directory
        supershell("mv %s %s/larch" % (self.system_sqf, self.medium))

        # prepare overlay
        command.log("#Generating larch overlay")
        # Copy over the overlay from the selected profile
        if os.path.isdir("%s/rootoverlay" % self.profile):
            supershell("cp -rf %s/rootoverlay/* %s" % (self.profile, self.overlay))
        # Ensure there is an /etc directory in the overlay
        supershell("mkdir -p %s/etc" % self.overlay)
        # fix sudoers if any
        if os.path.isfile("%s/etc/sudoers" % self.overlay):
            supershell("chmod 0440  %s/etc/sudoers" % self.overlay)
            supershell("chown root:root %s/etc/sudoers" % self.overlay)

        # Prepare inittab
        inittab = self.overlay + "/etc/inittab"
        itsave = inittab + ".larchsave"
        it0 = self.installation0 + "/etc/inittab"
        itl = self.overlay + "/etc/inittab.larch"
        if not os.path.isfile(itl):
            itl = self.installation0 + "/etc/inittab.larch"
            if not os.path.isfile(itl):
                itl = None
        # Save the original inittab if there is an inittab.larch file,
        #   ... if there isn't already a saved one
        if itl:
            if ((not os.path.isfile(it0 + ".larchsave"))
                    and (not os.path.isfile(itsave))):
                supershell("cp %s %s" % (it0, itsave))
            # Use the .larch version in the live system
            supershell("cp -f %s %s" % (itl, inittab))

        command.log("#Generating larch initcpio")
        if not self.gen_initramfs():
            return False

        command.log("#Generating glibc locales")
        command.script("larch-locales '%s' '%s'" % (self.installation0,
                self.overlay))

        if sshgen:
            # ssh initialisation - done here so that it doesn't need to
            # be done when the live system boots
            command.log("#Generating ssh keys to overlay")
            sshdir = config.overlay_build_dir + "/etc/ssh"
            supershell("mkdir -p %s" % config.ipath(sshdir))
            for k, f in [("rsa1", "ssh_host_key"), ("rsa", "ssh_host_rsa_key"),
                    ("dsa", "ssh_host_dsa_key")]:
                command.chroot("ssh-keygen -t %s -N '' -f %s/%s >/dev/null"
                        % (k, sshdir, f), ["dev"])

        # Ensure the hostname is in /etc/hosts
        command.script("larch-hosts %s %s" % (self.installation0, self.overlay))

        # Handle /mnt
        supershell("mkdir -p %s/mnt" % self.overlay)
        for d in os.listdir("%s/mnt" % self.installation0):
            if os.path.isdir("%s/mnt/%s" % (self.installation0, d)):
                supershell("mkdir %s/mnt/%s" % (self.overlay, d))

        # Ensure there is a /boot directory
        supershell("mkdir -p %s/boot" % self.overlay)

        # Run customization script
        tweak = self.profile + '/build-tweak'
        if os.path.isfile(tweak):
            command.log("#(WARNING): Running user's build customization script")
            if supershell(tweak + ' %s %s' % (self.installation0,
                    self.overlay))[0]:
                command.log("#Customization script completed")
            else:
                command.error("Warning", _("Build customization script failed"))
                return False

        # Add users
        if self.installation0 and not self.add_users():
            return False

        command.log("#Squashing mods.sqf")
        if not command.chroot("/sbin/mksquashfs '%s' '%s/larch/mods.sqf'"
                % (config.overlay_build_dir, config.medium_dir)):
            command.error("Warning", _("Squashing mods.sqf failed"))
            return False
        # remove execute attrib
        supershell("chmod oga-x %s/larch/mods.sqf" % self.medium)

        supershell("rm -rf %s" % self.overlay)
        # The medium boot directory needs to be kept outside of the medium
        # directory to allow multiple, different media to be built easily.
        supershell("mv %s/boot %s/tmp" % (self.medium, self.larch_dir))


    def getusers(self):
        """Read user information by means of a SafeConfigParser instance.
        This is then available as self.userconf.
        """
        self.userconf = SafeConfigParser({'pw':'', 'maingroup':'', 'uid':'',
                'skel':'', 'xgroups':BASEGROUPS, 'expert':''})
        users = config.get("profile") + '/users'
        if os.path.isfile(users):
            try:
                self.userconf.read(users)
            except:
                config_error(_("Invalid 'users' file"))

    def allusers(self):
        self.getusers()
        return self.userconf.sections()

    def userinfo(self, user, fields):
        """Get an ordered list of the given field data for the given user.
        """
        return [self.userconf.get(user, f) for f in fields]

    def userset(self, uname, field, text):
        self.userconf.set(uname, field, text)

    def newuser(self, user):
        try:
            self.userconf.add_section(user)
            return self.saveusers()
        except:
            run_error(_("Couldn't add user '%s'") % user)
            return False

    def deluser(self, user):
        try:
            self.userconf.remove_section(user)
            return self.saveusers()
        except:
            run_error(_("Couldn't remove user '%s'") % user)
            return False

    def saveusers(self):
        """Save the user configuration data (in 'INI' format)
        """
        try:
            fh = None
            fh = open(config.get("profile") + '/users', 'w')
            self.userconf.write(fh)
            fh.close()
            return True
        except:
            if fh:
                fh.close()
            config_error(_("Couldn't save 'users' file"))
            self.getusers()
            return False

    def add_users(self):
        self.getusers()
        userlist = []
        for user in self.allusers():
            if (command.script('user-exists %s %s'
                    % (self.installation_dir, user)) != ''):
                # Only include if the user does not yet exist
                userlist.append(user)
            else:
                command.log("#(WARNING): User '%s' exists already"
                                % user)

        # Only continue if there are new users in the list
        if userlist == []:
            return True

        # Save system files and replace them by the overlay versions
        savedir = self.larch_dir + '/tmp/save_etc'
        supershell('rm -rf %s' % savedir)
        supershell('mkdir -p %s/default' % savedir)
        savelist = 'group,gshadow,passwd,shadow,login.defs,skel'
        supershell('cp -a %s/etc/{%s} %s'
                % (self.installation0, savelist, savedir))
        supershell('cp -a %s/etc/default/useradd %s/default'
                % (self.installation0, savedir))
        for f in ('group', 'gshadow', 'passwd', 'shadow', 'login.defs'):
            if os.path.isfile(self.overlay + '/etc/%s'):
                supershell('cp %s/etc/%s %s/etc'
                        % (self.overlay, f, self.installation0))
        if os.path.isfile(self.overlay + '/etc/default/useradd'):
            supershell('cp %s/etc/default/useradd %s/etc/default'
                    % (self.overlay, self.installation0))
        if os.path.isdir(self.overlay + '/etc/skel'):
            supershell('cp -r %s/etc/skel %s/etc'
                    % (self.overlay, self.installation0))

        # Build the useradd command
        userdir0 = '/tmp/users'
        userdir = self.larch_dir + userdir0
        userdirs = []
        clist = []
        supershell('mkdir -p %s/home' % self.overlay)
        for u in userlist:
            cline = 'useradd -m'
            pgroup = self.userconf.get(u, 'maingroup')
            if pgroup:
                cline += ' -g ' + pgroup
            uid = self.userconf.get(u, 'uid')
            if uid:
                cline += ' -u ' + uid
            xgroups = self.userconf.get(u, 'xgroups')
            if xgroups:
                cline += ' -G ' + xgroups
            pw = self.userconf.get(u, 'pw')
            if (pw == ''):
                # Passwordless login
                pwcrypt = ''
            else:
                # Normal MD5 password
                pwcrypt = encryptPW(pw)
            cline += " -p '%s'" % pwcrypt
            skeldir = self.userconf.get(u, 'skel')
            if skeldir:
                # Custom home initialization directories in the profile
                # always start with 'skel_'
                skel = 'skel_' + skeldir
                if skel not in userdirs:
                    userdirs.append(skel)
                cline += ' -k %s/%s' % (config.larch_build_dir + userdir0, skel)
            # Allow for expert tweaking
            cline += ' ' + self.userconf.get(u, 'expert')
            # The user and the command to be run
            clist.append((u, cline))

        if userdirs:
            # Copy custom 'skel' directories to temporary area in build space
            supershell('rm -rf %s' % userdir)
            supershell('mkdir -p %s' % userdir)
            for ud in userdirs:
                supershell('cp -r %s/%s %s/%s' %
                        (self.profile, ud, userdir, ud))

        for u, cmd in clist:
            if not command.chroot(cmd + ' ' + u):
                run_error(_("User creation (%s) failed") % u[0])
                return False

            if os.path.isdir('%s/home/%s' % (self.installation0, u)):
                supershell('mv %s/home/%s %s/home'
                        % (self.installation0, u, self.overlay))

        # Move changed /etc/{group,gshadow,passwd,shadow} to overlay
        supershell('mv %s/etc/{group,gshadow,passwd,shadow} %s/etc'
                % (self.installation0, self.overlay))
        # Restore system files in base installation
        supershell('rm -rf %s/etc/skel' % self.installation0)
        supershell('cp -a %s/* %s/etc' % (savedir, self.installation0))
        return True


    def system_check(self):
        command.log("#Testing for necessary packages and kernel modules")
        fail = ""
        warn = ""
        nplist = ["larch-live"]

        mdep = config.ipath("lib/modules/%s/modules.dep" % self.kversion)
        if Popen(["grep", "/squashfs.ko", mdep], stdout=PIPE, stderr=STDOUT).wait() != 0:
            fail += _("No squashfs module found\n")

        if Popen(["grep", "/aufs.ko", mdep], stdout=PIPE, stderr=STDOUT).wait() == 0:
            self.ufs='_aufs'
            nplist.append("aufs2-util")

        elif Popen(["grep", "/unionfs.ko", mdep], stdout=PIPE, stderr=STDOUT).wait() == 0:
            self.ufs='_unionfs'

        else:
            fail += _("No aufs or unionfs module found\n")

        for p in nplist:
            if not self.haspack(p):
                fail += _("Package '%s' is needed by larch systems\n") % p

        if not self.haspack("syslinux"):
            warn += _("Without package 'syslinux' you will not be able\n"
                    "to create syslinux or isolinux booting media\n")

        if (not self.haspack("cdrkit")) and (not self.haspack("cdrtools")):
            warn += _("Without package 'cdrkit' (or 'cdrtools') you will\n"
                    "not be able to create CD/DVD media\n")

        if not self.haspack("eject"):
            warn += _("Without package 'eject' you will have problems\n"
                    "using CD/DVD media\n")

        if warn:
            cont = ui.confirmDialog(_("WARNING:\n%s"
                    "\n    Continue building?") % warn)
        else:
            cont = True

        if fail:
            ui.infoDialog(_("ERROR:\n%s") % fail)
            return False

        return cont


    def haspack(self, package):
        """Check whether the given package is installed.
        """
        for p in os.listdir(config.ipath("var/lib/pacman/local")):
            if p.rsplit("-", 2)[0] == package:
                return True
        return False


    def find_kernel(self):
        # The uncomfortable length of this function is deceptive,
        # most of it is for dealing with errors.
        command.log("#Seeking kernel information")
        script = "%s/kernel" % self.profile
        if os.path.isfile(script):
            p = Popen([script], stdout=PIPE, stderr=STDOUT)
            r = p.communicate()[0]
            if p.returncode == 0:
                self.kname, self.kversion = r.split()

            else:
                fatal_error(_("Problem running %s:\n  %s") % (script, r))
                return False
        else:
            kernels = glob(config.ipath("boot/vmlinuz*"))
            if len(kernels) > 1:
                fatal_error(_("More than one kernel found:\n  %s") %
                        "\n  ".join(kernels))
                return False
            elif not kernels:
                fatal_error(_("No kernel found"))
                return False
            self.kname = os.path.basename(kernels[0])

            self.kversion = None
            for kv in os.listdir(config.ipath("lib/modules")):
                if os.path.isfile(config.ipath("lib/modules/%s/modules.dep" % kv)):
                    if self.kversion:
                        fatal_error(_("More than one set of kernel modules in %s")
                                % config.ipath("lib/modules"))
                        return False
                    self.kversion = kv
                else:
                    kmpath = config.ipath("lib/modules/%s" % kv)
                    command.log("#Unexpected kernel files at %s" % kmpath)
                    # Try to find packages concerned
                    p = Popen(["find", ".", "-name", "*.ko"], cwd=kmpath,
                            stdout=PIPE, stderr=STDOUT)
                    r = p.communicate()[0]
                    if p.returncode == 0:
                        packs = []
                        for km in r.split():
                            a = command.chroot("pacman -Qoq /lib/modules/%s/%s"
                                    % (kv, km))

                            if a:
                                pack = "-".join(a[0].split())
                                if pack not in packs:
                                    packs.append(pack)
                                    command.log("# Package: %s" % pack)

                    else:
                        command.log("#Couldn't determine guilty packages")

                    if not ui.confirmDialog(_("WARNING:\n"
                            "  You seem to have installed a package containing modules\n"
                            "which aren't compatible with your kernel (see log).\n"
                            "Please check that this won't cause problems.\n"
                            "Maybe you need the corresponding package for your kernel?\n"
                            "\n    Continue building?")):
                        return False

        if not self.kversion:
            fatal_error(_("Couldn't find kernel modules"))
            return False

        command.log("#Kernel: %s   -   version: %s" % (self.kname, self.kversion))
        command.chroot("depmod %s" % self.kversion)
        return True


    def gen_initramfs(self):
        # Fix up larch mkinitcpio.conf for unionfs/aufs
        conf = self.overlay + "/etc/mkinitcpio.conf.larch"
        if os.path.isfile(conf + "0"):
            conf0 = conf + "0"
        else:
            conf0 = self.installation0 + "/etc/mkinitcpio.conf.larch0"
        supershell("sed 's|___aufs___|%s|g' <%s >%s" % (self.ufs, conf0, conf))

        presets = [os.path.basename(f) for f in glob(
                self.installation0 + "/etc/mkinitcpio.d/kernel26*.preset")]
        if len(presets) != 1:
            run_error(_("Couldn't find usable mkinitcpio preset: %s") %
                    self.installation0 + "/etc/mkinitcpio.d/kernel26*.preset")
            return False

        # Save original preset file (unless a '*.larchsave' is already present)
        idir = self.installation0 + "/etc/mkinitcpio.d"
        oldir = self.overlay + "/etc/mkinitcpio.d"
        if not os.path.isfile("%s/%s.larchsave" % (idir, presets[0])):
            supershell("mkdir -p %s" % oldir)
            supershell("cp %s/%s %s/%s.larchsave" %
                    (idir, presets[0], oldir, presets[0]))

        # Adjust larch.preset file for custom kernels
        supershell("sed 's|___|%s|' <%s/larch.preset0 >%s/larch.preset" %
                (presets[0].rsplit(".", 1)[0], idir, oldir))

        # Replace 'normal' preset in overlay
        supershell("cp %s/larch.preset %s/%s" % (oldir, oldir, presets[0]))

        # Generate initramfs
        return command.chroot("mkinitcpio -k %s -c %s -g %s" %
                (self.kversion,
                 config.overlay_build_dir + "/etc/mkinitcpio.conf.larch",
                 config.medium_dir + "/boot/larch.img"))


def encryptPW(pw):
    salt = '$1$'
    for i in range(8):
        salt += random.choice("./0123456789abcdefghijklmnopqrstuvwxyz"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return crypt.crypt(pw, salt)

