#! /bin/bash

#   based on
#   rebuildlist - list packages needing rebuilt for a soname bump
#
#   Copyright (c) 2009 by Allan McRae <allan@archlinux.org>
#   (some destructive) modifications: <jan.mette@berlin.de>
#
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
curdir=`pwd`
repodir="_repo/repo"

_script_name="gen rebuild list"
_build_arch="$_arch"
_cur_repo=`pwd | awk -F '/' '{print $NF}'`
_needed_functions="config_handling messages"
# load functions
for subroutine in ${_needed_functions}
do
    source _buildscripts/functions/${subroutine}
done


#
# startup
#
title "${_script_name}"

check_configs
load_configs



if [ -z "$1" ]; then
	error "Usage: $0 <name of the package to be rebuilt>"
	newline
	exit
fi

package="$1"
liblist=`pacman -Ql $package | grep "\.so" | grep -v "/engines/" | cut -d " " -f 2 | awk 'BEGIN {FS="/"} {print $NF}' | cut -d "." -f 1 | uniq | tr '\n' ' '`

#directory="$curdir/$repodir"
directory="/var/cache/pacman/pkg"

for solib in $liblist; do
	grepexpr="$grepexpr -e ${solib%%.so}.so"
done

if [ -e "$startdir/_temp/rebuildlist-$package.txt" ]; then
	rm -rf $startdir/_temp/rebuildlist-$package.txt
fi

startdir=$(pwd)
tmpdir=$(mktemp -d)
cd $tmpdir

newline
title2 "Scanning packages"
msg "This can take a lot of time"

for pkg in $(ls $directory/*.pkg.*); do
	pkg=${pkg##*\/}
	status_start "Scanning $pkg"
	mkdir $tmpdir/extract
	cp $directory/$pkg $tmpdir/extract
	cd $tmpdir/extract
	tar -xf $directory/$pkg 2>/dev/null
	rm $pkg
	found=$(readelf --dynamic $(find -type f) 2>/dev/null | grep $grepexpr | wc -l)
	if [ $found -ne 0 ]; then
		echo ${pkg%-*-*-*} >> ../rebuildlist-$package.txt
	fi
	cd ..
	rm -rf extract
	status_done
done

status_start "saving _temp/rebuildlist-$package.txt"
	cp $tmpdir/rebuildlist-$package.txt $startdir/_temp/
status_done

newline
title2 "All done, rebuild list created in _temp/"
newline

