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
_script_name="increase pkgrels"
_build_arch="$_arch"
_cur_repo=`pwd | awk -F '/' '{print $NF}'`
_needed_functions="config_handling helpers messages"
_available_pkglists=`cat _buildscripts/${_cur_repo}-${_build_arch}-pkgs.conf | grep "_" | cut -d "=" -f 1 | awk 'BEGIN {FS="_"} {print $NF}' | sed '/^$/d'`
# load functions
for subroutine in ${_needed_functions}
do
    source _buildscripts/functions/${subroutine}
done

#
# main
#
increase_pkgrels() {
        [ -n "$MODE" ] || error "you need to specify a package list defined in _/buildsystem/${_cur_repo}-${_build_arch}-pkgs.conf\n -> ${_available_pkglists}"
	
	case "$MODE" in
	
		all)
			title2 "Increasing all pkgrels"
			for module in ${whattodo[*]}
			do
			status_start "$module"
			pushd $module &>/dev/null
				sed -i -e 's/\<pkgrel=20\>/pkgrel=21/g' PKGBUILD
				sed -i -e 's/\<pkgrel=19\>/pkgrel=20/g' PKGBUILD
				sed -i -e 's/\<pkgrel=18\>/pkgrel=19/g' PKGBUILD
				sed -i -e 's/\<pkgrel=17\>/pkgrel=18/g' PKGBUILD
				sed -i -e 's/\<pkgrel=16\>/pkgrel=17/g' PKGBUILD
				sed -i -e 's/\<pkgrel=15\>/pkgrel=16/g' PKGBUILD
				sed -i -e 's/\<pkgrel=14\>/pkgrel=15/g' PKGBUILD
				sed -i -e 's/\<pkgrel=13\>/pkgrel=14/g' PKGBUILD
				sed -i -e 's/\<pkgrel=12\>/pkgrel=13/g' PKGBUILD
				sed -i -e 's/\<pkgrel=11\>/pkgrel=12/g' PKGBUILD
				sed -i -e 's/\<pkgrel=10\>/pkgrel=11/g' PKGBUILD
				sed -i -e 's/\<pkgrel=9\>/pkgrel=10/g' PKGBUILD
				sed -i -e 's/\<pkgrel=8\>/pkgrel=9/g' PKGBUILD
				sed -i -e 's/\<pkgrel=7\>/pkgrel=8/g' PKGBUILD
				sed -i -e 's/\<pkgrel=6\>/pkgrel=7/g' PKGBUILD
				sed -i -e 's/\<pkgrel=5\>/pkgrel=6/g' PKGBUILD
				sed -i -e 's/\<pkgrel=4\>/pkgrel=5/g' PKGBUILD
				sed -i -e 's/\<pkgrel=3\>/pkgrel=4/g' PKGBUILD
				sed -i -e 's/\<pkgrel=2\>/pkgrel=3/g' PKGBUILD
				sed -i -e 's/\<pkgrel=1\>/pkgrel=2/g' PKGBUILD
			popd &>/dev/null
			status_done
			done
		;;
		
		fixit)
			title2 "Increasing support pkgrels"
			for module in ${whattodo[*]}
			do
			status_start "$module"
			pushd $module &>/dev/null
				sed -i -e 's/\<pkgrel=20\>/pkgrel=21/g' PKGBUILD
				sed -i -e 's/\<pkgrel=19\>/pkgrel=20/g' PKGBUILD
				sed -i -e 's/\<pkgrel=18\>/pkgrel=19/g' PKGBUILD
				sed -i -e 's/\<pkgrel=17\>/pkgrel=18/g' PKGBUILD
				sed -i -e 's/\<pkgrel=16\>/pkgrel=17/g' PKGBUILD
				sed -i -e 's/\<pkgrel=15\>/pkgrel=16/g' PKGBUILD
				sed -i -e 's/\<pkgrel=14\>/pkgrel=15/g' PKGBUILD
				sed -i -e 's/\<pkgrel=13\>/pkgrel=14/g' PKGBUILD
				sed -i -e 's/\<pkgrel=12\>/pkgrel=13/g' PKGBUILD
				sed -i -e 's/\<pkgrel=11\>/pkgrel=12/g' PKGBUILD
				sed -i -e 's/\<pkgrel=10\>/pkgrel=11/g' PKGBUILD
				sed -i -e 's/\<pkgrel=9\>/pkgrel=10/g' PKGBUILD
				sed -i -e 's/\<pkgrel=8\>/pkgrel=9/g' PKGBUILD
				sed -i -e 's/\<pkgrel=7\>/pkgrel=8/g' PKGBUILD
				sed -i -e 's/\<pkgrel=6\>/pkgrel=7/g' PKGBUILD
				sed -i -e 's/\<pkgrel=5\>/pkgrel=6/g' PKGBUILD
				sed -i -e 's/\<pkgrel=4\>/pkgrel=5/g' PKGBUILD
				sed -i -e 's/\<pkgrel=3\>/pkgrel=4/g' PKGBUILD
				sed -i -e 's/\<pkgrel=2\>/pkgrel=3/g' PKGBUILD
				sed -i -e 's/\<pkgrel=1\>/pkgrel=2/g' PKGBUILD
			popd &>/dev/null
			status_done
			done
		;;

		qt)
			title2 "Increasing Qt pkgrels"
			for module in ${whattodo[*]}
			do
			status_start "$module"
			pushd $module &>/dev/null
				sed -i -e 's/\<pkgrel=20\>/pkgrel=21/g' PKGBUILD
				sed -i -e 's/\<pkgrel=19\>/pkgrel=20/g' PKGBUILD
				sed -i -e 's/\<pkgrel=18\>/pkgrel=19/g' PKGBUILD
				sed -i -e 's/\<pkgrel=17\>/pkgrel=18/g' PKGBUILD
				sed -i -e 's/\<pkgrel=16\>/pkgrel=17/g' PKGBUILD
				sed -i -e 's/\<pkgrel=15\>/pkgrel=16/g' PKGBUILD
				sed -i -e 's/\<pkgrel=14\>/pkgrel=15/g' PKGBUILD
				sed -i -e 's/\<pkgrel=13\>/pkgrel=14/g' PKGBUILD
				sed -i -e 's/\<pkgrel=12\>/pkgrel=13/g' PKGBUILD
				sed -i -e 's/\<pkgrel=11\>/pkgrel=12/g' PKGBUILD
				sed -i -e 's/\<pkgrel=10\>/pkgrel=11/g' PKGBUILD
				sed -i -e 's/\<pkgrel=9\>/pkgrel=10/g' PKGBUILD
				sed -i -e 's/\<pkgrel=8\>/pkgrel=9/g' PKGBUILD
				sed -i -e 's/\<pkgrel=7\>/pkgrel=8/g' PKGBUILD
				sed -i -e 's/\<pkgrel=6\>/pkgrel=7/g' PKGBUILD
				sed -i -e 's/\<pkgrel=5\>/pkgrel=6/g' PKGBUILD
				sed -i -e 's/\<pkgrel=4\>/pkgrel=5/g' PKGBUILD
				sed -i -e 's/\<pkgrel=3\>/pkgrel=4/g' PKGBUILD
				sed -i -e 's/\<pkgrel=2\>/pkgrel=3/g' PKGBUILD
				sed -i -e 's/\<pkgrel=1\>/pkgrel=2/g' PKGBUILD
			popd &>/dev/null
			status_done
			done
		;;
		
		kde)
			title2 "Increasing KDE pkgrels"
			for module in ${whattodo[*]}
			do
			status_start "$module"
			pushd $module &>/dev/null
				sed -i -e 's/\<pkgrel=20\>/pkgrel=21/g' PKGBUILD
				sed -i -e 's/\<pkgrel=19\>/pkgrel=20/g' PKGBUILD
				sed -i -e 's/\<pkgrel=18\>/pkgrel=19/g' PKGBUILD
				sed -i -e 's/\<pkgrel=17\>/pkgrel=18/g' PKGBUILD
				sed -i -e 's/\<pkgrel=16\>/pkgrel=17/g' PKGBUILD
				sed -i -e 's/\<pkgrel=15\>/pkgrel=16/g' PKGBUILD
				sed -i -e 's/\<pkgrel=14\>/pkgrel=15/g' PKGBUILD
				sed -i -e 's/\<pkgrel=13\>/pkgrel=14/g' PKGBUILD
				sed -i -e 's/\<pkgrel=12\>/pkgrel=13/g' PKGBUILD
				sed -i -e 's/\<pkgrel=11\>/pkgrel=12/g' PKGBUILD
				sed -i -e 's/\<pkgrel=10\>/pkgrel=11/g' PKGBUILD
				sed -i -e 's/\<pkgrel=9\>/pkgrel=10/g' PKGBUILD
				sed -i -e 's/\<pkgrel=8\>/pkgrel=9/g' PKGBUILD
				sed -i -e 's/\<pkgrel=7\>/pkgrel=8/g' PKGBUILD
				sed -i -e 's/\<pkgrel=6\>/pkgrel=7/g' PKGBUILD
				sed -i -e 's/\<pkgrel=5\>/pkgrel=6/g' PKGBUILD
				sed -i -e 's/\<pkgrel=4\>/pkgrel=5/g' PKGBUILD
				sed -i -e 's/\<pkgrel=3\>/pkgrel=4/g' PKGBUILD
				sed -i -e 's/\<pkgrel=2\>/pkgrel=3/g' PKGBUILD
				sed -i -e 's/\<pkgrel=1\>/pkgrel=2/g' PKGBUILD
			popd &>/dev/null
			status_done
			done
		;;
		
		tools)
			title2 "Increasing tool pkgrels"
			for module in ${whattodo[*]}
			do
			status_start "$module"
			pushd $module &>/dev/null
				sed -i -e 's/\<pkgrel=20\>/pkgrel=21/g' PKGBUILD
				sed -i -e 's/\<pkgrel=19\>/pkgrel=20/g' PKGBUILD
				sed -i -e 's/\<pkgrel=18\>/pkgrel=19/g' PKGBUILD
				sed -i -e 's/\<pkgrel=17\>/pkgrel=18/g' PKGBUILD
				sed -i -e 's/\<pkgrel=16\>/pkgrel=17/g' PKGBUILD
				sed -i -e 's/\<pkgrel=15\>/pkgrel=16/g' PKGBUILD
				sed -i -e 's/\<pkgrel=14\>/pkgrel=15/g' PKGBUILD
				sed -i -e 's/\<pkgrel=13\>/pkgrel=14/g' PKGBUILD
				sed -i -e 's/\<pkgrel=12\>/pkgrel=13/g' PKGBUILD
				sed -i -e 's/\<pkgrel=11\>/pkgrel=12/g' PKGBUILD
				sed -i -e 's/\<pkgrel=10\>/pkgrel=11/g' PKGBUILD
				sed -i -e 's/\<pkgrel=9\>/pkgrel=10/g' PKGBUILD
				sed -i -e 's/\<pkgrel=8\>/pkgrel=9/g' PKGBUILD
				sed -i -e 's/\<pkgrel=7\>/pkgrel=8/g' PKGBUILD
				sed -i -e 's/\<pkgrel=6\>/pkgrel=7/g' PKGBUILD
				sed -i -e 's/\<pkgrel=5\>/pkgrel=6/g' PKGBUILD
				sed -i -e 's/\<pkgrel=4\>/pkgrel=5/g' PKGBUILD
				sed -i -e 's/\<pkgrel=3\>/pkgrel=4/g' PKGBUILD
				sed -i -e 's/\<pkgrel=2\>/pkgrel=3/g' PKGBUILD
				sed -i -e 's/\<pkgrel=1\>/pkgrel=2/g' PKGBUILD
			popd &>/dev/null
			status_done
			done
		;;
	esac         
}

#
# startup
#
title "${_script_name}"

check_configs
load_configs

MODE=`echo $1`

# we take the repo name + the job/stage to reconstruct the variable name
# in $repo_pkgs.cfg and echo its contents... damn, eval is evil ;)
	if [ "$_cur_repo" = "core" ] ; then
	whattodo=($(eval echo "\${_build_core_${MODE}[@]}"))

	elif [ "$_cur_repo" = "core-testing" ] ; then
	whattodo=($(eval echo "\${_build_core_testing_${MODE}[@]}"))

	elif [ "$_cur_repo" = "platform" ] ; then
	whattodo=($(eval echo "\${_build_platform_${MODE}[@]}"))

	elif [ "$_cur_repo" = "platform-testing" ] ; then
	whattodo=($(eval echo "\${_build_platform_testing_${MODE}[@]}"))

	elif [ "$_cur_repo" = "desktop" ] ; then
	whattodo=($(eval echo "\${_build_desktop_${MODE}[@]}"))

	elif [ "$_cur_repo" = "desktop-testing" ] ; then
	whattodo=($(eval echo "\${_build_desktop_testing_${MODE}[@]}"))

	elif [ "$_cur_repo" = "apps" ] ; then
	whattodo=($(eval echo "\${_build_apps_${MODE}[@]}"))

	elif [ "$_cur_repo" = "apps-testing" ] ; then
	whattodo=($(eval echo "\${_build_apps_testing_${MODE}[@]}"))

	fi

increase_pkgrels

title "All done"
newline
