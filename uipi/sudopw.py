#!/usr/bin/env python
#
# sudopw.py   --  Simple GUI to get sudo password
#
# (c) Copyright 2009 Michael Towers (larch42 at googlemail dot com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#-------------------------------------------------------------------
# 2009.11.25

"""To use this you need to set the environment variable SUDO_ASKPASS to
/usr/sbin/sudopw (assuming that is where this script is installed), and
call sudo with the -A option.

For example:
export SUDO_ASKPASS=/usr/sbin/sudopw
sudo -A env

Of course you also need to set up your /etc/sudoers file so that the
user concerned is allowed to execute the desired programs (see the man
pages for sudo and sudoers).
"""

from uipi import Uipi
import sys


def done(okpw):
    global ecode
    if okpw[0]:
        print okpw[1]
        ecode = 0
    else:
        ecode = 1


ui = Uipi()
ui.addslot("done", done)
okpw = ui.textLineDialog(sys.argv[1], "sudopw", async="done", pw=True)
ui.mainloop()
exit(ecode)
