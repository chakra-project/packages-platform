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
_script_name="sync complete"
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
sync_complete()
{
	title2 "syncing down"
        export RSYNC_PASSWORD=`echo $_rsync_pass`
        rsync -avh --progress $_rsync_user@$_rsync_server::$_rsync_dir/* _repo/remote/
	
	# move new packages from $ROOT/repos/$REPO/build into thr repo dir 
        title2 "adding new packages"
        mv -v _repo/local/*.pkg.* _repo/remote/

        # run repo-clean on it
        title2 "running repo-clean"
        repo-clean -m c -s _repo/remote/

        # create new pacman database
        title2 "creating pacman database"
	rm -rf _repo/remote/*.db.tar.gz
        pushd _repo/remote/
        repo-add $_cur_repo.db.tar.gz *.pkg.*
        popd

        # sync local -> server
        title2 "syncing up"
        rsync -avh --progress --delay-updates --delete-after _repo/remote/ $_rsync_user@$_rsync_server::$_rsync_dir
}

#
# startup
#
title "${_script_name} - $_cur_repo"

check_configs
load_configs

check_rsync
check_accounts

time sync_complete
newline

title "All done"
newline
