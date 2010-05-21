#!/usr/bin/env python
#
# medium.py
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
# 2010.03.14

import os


class Medium:
    """This class manages writing a built larch system to a boot medium.
    """
    def __init__(self):
        pass


    def _bootdir(self, btype, device, partsel, label):
        command.log("# Preparing boot directory, %s." % btype)
        # Clean out any old boot stuff
        supershell("rm -rf %s/{boot,grub,syslinux,isolinux}" % self.medium)

        # The idea is that a basic boot directory for each boot-loader is
        # provided in larch at cd-root/{grub0,isolinux0}. Individual files
        # can be added or substituted by supplying them in the profile at
        # cd-root/{grub,isolinux}.
        # It is also possible to completely replace the basic boot directory
        # by having cd-root/{grub0,isolinux0} in the profile - then the default
        # larch versions will not be used.

        if btype:
            if btype == "boot":
                # GRUB
                d0 = "grub"
                configfile = "grub/menu.lst"
            else:
                # syslinux/isolinux
                d0 = "isolinux"
                configfile = "isolinux.cfg"

            source0 = "%s/cd-root/%s0" % (self.profile, d0)
            if not os.path.isdir(source0):
                source0 = "%s/cd-root/%s0" % (base_dir, d0)
            supershell("cp -r %s %s/%s" % (source0, self.medium, d0))

            # Copy any additional profile stuff
            psource = "%s/cd-root/%s" % (self.profile, d0)
            if os.path.isdir(psource):
                supershell("cp -rf %s %s" % (psource, self.medium))

            # Compose the bootloader config file (insert 'bootlines' file)
            bootlines = self.profile + "/bootlines"
            insert = config.working_dir + "/bootlines_"
            if not os.path.isfile(bootlines):
                bootlines = base_dir + "/cd-root/bootlines"

            # Convert and complete the bootlines file
            # - add boot partition to options
            if partsel == "uuid":
                bootp = "uuid=" + supershell("blkid -c /dev/null -o value -s UUID %s"
                    % device).result[0].strip()
            elif partsel == "label":
                if not label:
                    config_error(_("Can't boot to label - no label supplied"))
                    return False
                bootp = "label=" + label
            elif partsel == "partition":
                bootp = "root=" + device
            else:
                bootp = ""

            # - convert bootfiles to the correct format, inserting necessary info
            fhi = open(bootlines)
            fho = open(insert, "w")
            i = 0
            block = ""
            title = ""
            options = ""
            for line in fhi:
                line = line.strip()
                if not line:
                    if title:
                        i += 1
                        # A block is ready

                        if btype == "boot":
                            # GRUB
                            block += "title %s\n" % title
                            block += "kernel /boot/larch.kernel %s %s\n" % (bootp, options)
                            block += "initrd /boot/larch.img\n"

                        else:
                            # isolinux/syslinux
                            block += "label %02d\n" % i
                            block += "MENU LABEL %s\n" % title
                            block += "kernel larch.kernel\n"
                            block += "append initrd=larch.img %s %s\n" % (bootp, options)

                        if i > 1:
                            fho.write("\n")
                        fho.write(block)
                    block = ""
                    title = ""
                    options = ""

                elif line.startswith("comment:"):
                    block += "#%s\n" % (line.split(":", 1)[1])

                elif line.startswith("title:"):
                    title = line.split(":", 1)[1].lstrip()

                elif line.startswith("options:"):
                    options = line.split(":", 1)[1].lstrip()

            fho.close()
            fhi.close()

            # - insert the resulting file into the bootloader config file
            # This doesn't work, maybe one day I'll find out why ...
            #supershell("sed '/###LARCH/ { r %s\n  d }' -i %s/%s/%s" %
            #        (insert, self.medium, d0, configfile))
            configtmp = config.working_dir + "/bootconfig_"
            configpath = "%s/%s/%s" % (self.medium, d0, configfile)
            fhi = open(configpath)
            fho = open(configtmp, "w")
            for line in fhi:
                if line.startswith("###LARCH"):
                    fhr = open(insert)
                    fho.write(fhr.read())
                    fhr.close()
                else:
                    fho.write(line)
            fho.close()
            fhi.close()
            supershell("cp -f %s %s && rm {%s,%s}" %
                    (configtmp, configpath, configtmp, insert))

            if btype != "isolinux":
                # Rename the boot directory
                supershell("mv %s/%s %s/%s" % (self.medium, d0,
                        self.medium, btype))
                if btype == "syslinux":
                    # Rename isolinux.cfg to syslinux.cfg
                    supershell("mv %s/syslinux/isolinux.cfg %s/syslinux/syslinux.cfg"
                            % (self.medium, self.medium))
                elif btype == "boot":
                    # Copy the grub boot files to the medium's grub directory
                    supershell("cp %s/* %s/boot/grub" %
                            (config.ipath("usr/lib/grub/i386-pc"), self.medium))

            # Copy bootloader independent stuff
            source0 = "%s/cd-root/boot0" % self.profile
            if not os.path.isdir(source0):
                source0 = "%s/cd-root/boot0" % base_dir
            supershell("cp -r %s/* %s/%s &>/dev/null" %
                    (source0, self.medium, btype))

            # Copy any additional profile stuff
            psource = "%s/cd-root/boot" % self.profile
            if os.path.isdir(psource):
                supershell("cp -rf %s/* %s/%s" % (psource, self.medium, btype))


        else:
            # No bootloader
            btype = "boot"
            supershell("mkdir %s/%s" % (self.medium, btype))

        # Copy the stuff from the larchify stage (kernel, initcpio, etc.)
        supershell("cp -r %s/tmp/boot/* %s/%s" %
                (self.larch_dir, self.medium, btype))
        return True


    def make(self, btype, device, label, partsel, format, larchboot):
        # btype is "boot" (grub), "syslinux", "isolinux" or "" (no bootloader)
        # For cd/dvd (iso), device is ""
        # partsel = "uuid", "label", "partition", or ""
        # For boot iso,

        # Location for the live medium image
        self.medium = config.ipath(config.medium_dir)
        self.larch_dir = config.ipath(config.larch_build_dir)
        self.profile = config.get("profile")

        grub = "lin" not in btype
        if format and device:
            if command.script("larch-format %s %s %s" % (device,
                    "ext2" if grub else "vfat", label)):
                run_error(_("Couldn't format %s") % device)
                return False

        # The medium's initial "boot" dir, with kernel and initcpio, is
        # at self.larch_dir + "/tmp/boot"
        if not self._bootdir(btype, device, partsel, label): return False

        # Replace any existing larch/copy directory
        supershell("rm -rf %s/larch/copy" % self.medium)
        if os.path.isdir(self.profile + "/cd-root/larch/copy"):
            supershell("cp -r %s/cd-root/larch/copy %s/larch" %
                    (self.profile, self.medium))

        # Replace any existing larch/extra directory
        supershell("rm -rf %s/larch/extra" % self.medium)
        if os.path.isdir(self.profile + "/cd-root/larch/extra"):
            supershell("cp -r %s/cd-root/larch/extra %s/larch" %
                    (self.profile, self.medium))

        # To boot in 'search' mode the file larch/larchboot must be present
        # (though at present this is only relevant for partitions, CDs will
        # be booted even without this file).
        # To enable session saving the file larch/save must be present
        # (only relevant if not building an iso).
        supershell("rm -f %s/larch/{larchboot,save}" % self.medium)
        if larchboot:
            lbfile = (r"The presence of the file 'larch/larchboot' enables\n"
                        r"booting the device in 'search' mode.\n")
            supershell("echo -e '%s' >%s/larch/larchboot" % (lbfile, self.medium))

        if device:
#TODO: Is this really the best way to handle the 'save' file?
            if not os.path.isfile(self.profile + "/nosave"):
                savefile = (r"The presence of the file 'larch/save'"
                        r"enables session saving.\n")
                supershell("echo -e '%s' >%s/larch/save" % (savefile, self.medium))

            self._build_partition(btype, device, grub, label, format)

        else:
            # iso
            if btype == "boot":
                return _mkiso("-b boot/grub/stage2_eltorito")
            if getisolinuxbin(self.medium):
                return _mkiso("-b isolinux/isolinux.bin -c isolinux/isolinux.boot")
            else:
                return False


    def _build_partition(self, btype, device, grub, label, format):
        if not format:
            ok, lines = supershell("blkid -c /dev/null -o value -s TYPE %s"
                    % device)
            if ok and label:
                fstype = lines[0]
                if grub:
                    if not fstype.startswith("ext"):
                        config_error(_("GRUB is at present only supported on extN"))
                        return False
                    command.chroot("e2label %s %s" % (device, label), ["dev"])

                else:
                    if fstype != "vfat":
                        config_error(_("syslinux is only supported on vfat"))
                        return False
                    command.chroot("mlabel -i %s ::%s" % (device, label),
                            ["dev"])

#reiserfs: reiserfstune -l <label> /dev/XXX
#jfs: jfs_tune -L <label> /dev/XXX
#xfs: xfs_admin -L <label> /dev/XXX
#reiser4: ??? (are reiser4 labels even recognized?)
#ntfs: ntfslabel /dev/XXX <label> or change it using Windows. (found in ntfsprogs)

        # Mount partition and remove larch dir
        mp = config.working_dir + "/mnt"
        if not os.path.isdir(mp):
            os.mkdir(mp)
        if not command.mount(device, mp):
            config_error(_("Couldn't mount larch partition, %s") % device)
            return False
        supershell("rm -rf %s/larch" % mp)

        # If doing bootloader remove boot and syslinux dirs
        if btype:
            supershell("rm -rf %s/larch{boot,syslinux}" % mp)
        else:
            supershell("mkdir -p %s/boot" % mp)

        # Copy files and unmount partition
        supershell("cp -a %s/* %s" % (self.medium, mp))
        command.unmount(mp)

        # Now set up bootloader in MBR
        if btype == "boot":
            command.script("larch-mbr-grub %s %s" %
                    (config.ipath(), device))

        elif btype == "syslinux":
            command.script("larch-mbr-syslinux %s %s" %
                    (config.ipath(), device))
        return True


    def mkbootiso(self, device):
        """Make a boot iso for the given device.
        """
        # Mount partition and copy required files to temporary directory
        mp = config.working_dir + "/mnt"
        if not os.path.isdir(mp):
            os.mkdir(mp)
        if not command.mount(device, mp):
            config_error(_("Couldn't mount larch partition, %s") % device)
            return False
        isodir0 = config.larch_build_dir + "/bootiso"
        isodir = config.ipath(isodir0)
        supershell("rm -rf %s && mkdir %s" % (isodir, isodir))
        if os.path.isdir(mp + "/boot"):
            # GRUB boot
            supershell("cp -r %s/boot %s" % (mp, isodir))
            ok = _mkiso("-b boot/grub/stage2_eltorito",
                    "grubboot.iso", isodir0)

        elif os.path.isdir(mp + "/syslinux"):
            # isolinux boot
            ok = True
            supershell("cp -r %s/syslinux %s/isolinux" % (mp, isodir))
            supershell("mv %s/isolinux/syslinux.cfg %s/isolinux/isolinux.cfg"
                    % (isodir, isodir))
            if getisolinuxbin(isodir):
                ok = _mkiso("-b isolinux/isolinux.bin -c isolinux/isolinux.boot",
                        "isoboot.iso", isodir0)
            else:
                config_error(_("'syslinux' must be installed."))
                ok = False

        else:
            run_error(_("Device has neither a /boot nor a /syslinux directory"))
            ok = False

        command.unmount(mp)
        supershell("rm -rf %s" % isodir)
        return ok


def getisolinuxbin(medium):
    path = config.ipath("usr/lib/syslinux/isolinux.bin")
    if os.path.isfile(path):
        supershell("cp %s %s/isolinux" % (path, medium))
        return True
    else:
        config_error(_("%s not found -\n"
                "   'syslinux' must be installed on live system")
                % path)
        return False


def _mkiso(parms, iso="mylivecd.iso", source=None):
    if not source:
        source = config.medium_dir
    path = config.larch_build_dir + "/" + iso
    if command.chroot(("mkisofs -r -l %s -no-emul-boot -boot-load-size 4"
            " -boot-info-table -input-charset=UTF-8"
            " -publisher '%s'"
            " -A '%s'"
            " -o '%s' '%s'") % (parms, config.get("isopublisher"),
                    config.get("isoA") ,path, source)):
        ui.infoDialog(_("Your larch iso, %s, was successfully created")
                % config.ipath(path))
        return True
    else:
        run_error("iso build failed")
        return False
