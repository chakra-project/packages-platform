#!/bin/bash

#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>

#
# setup
#
_script_name="sync down"
_build_arch="$_arch"
_cur_repo=`pwd | awk -F '/' '{print $NF}'`
_needed_functions="config_handling helpers messages"
# load functions
for subroutine in ${_needed_functions}
do
    source _buildscripts/functions/${subroutine}
done

#
# main
#
sync_down()
{
	title2 "syncing down"
        export RSYNC_PASSWORD=`echo $_rsync_pass`
        rsync -avh --progress $_rsync_user@$_rsync_server::$_rsync_dir/* _repo/remote/ 
}

#
# startup
#
title "${_script_name} - $_cur_repo"

check_configs
load_configs

check_rsync
check_accounts

time sync_down
newline

title "All done"
newline
