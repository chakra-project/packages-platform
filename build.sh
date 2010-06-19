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
_script_name="build(er)"
_build_arch="$_arch"
_cur_repo=`pwd | awk -F '/' '{print $NF}'`
_needed_functions="config_handling messages dependency_handling"
_available_pkglists=`cat _buildscripts/${_cur_repo}-${_build_arch}-pkgs.conf | grep "_" | cut -d "=" -f 1 | awk 'BEGIN {FS="_"} {print $NF}' | sed '/^$/d'`
# load functions
for subroutine in ${_needed_functions}
do
    source _buildscripts/functions/${subroutine}
done

current_repo="$_cur_repo"


#
# main
#
build_it()
{
	_mkpkg_flags=$1
        [ -n "$MODE" ] || error "you need to specify a package list defined in _/buildscripts/${_cur_repo}-${_build_arch}-pkgs.conf\n -> ${_available_pkglists}" && exit

	cd $_build_work

	for module in ${whattodo[*]}
	do
		[[ `echo $module | cut -c1` == '#' ]] && continue
		msg "building $module. makepkg flags: $_mkpkg_flags"
		pushd $module &>/dev/null

			if [ -e "$_build_work/$module/PKGBUILD" ] ; then

				if [ "$_build_autodepends" = "1" ] ; then

					do_makedeps
					do_deps

                    ../makepkg -f $_mkpkg_flags || BUILD_BROKEN="1"

					if [ "$BUILD_BROKEN" = "1" ] ; then
						if [ "$_build_stop" = "1" ] ; then
							echo " "
							echo " "
							echo "ERROR BUILDING $module"
							echo " "
							echo " "
							exit 1
						else
							BROKEN_PKGS="$BROKEN_PKGS $module"
							unset BUILD_BROKEN
						fi
					fi
				else
                    ../makepkg -f $_mkpkg_flags || BUILD_BROKEN="1"

					if [ "$BUILD_BROKEN" = "1" ] ; then
						if [ "$_build_stop" = "1" ] ; then
							echo " "
							echo " "
							echo "ERROR BUILDING $module"
							echo " "
							echo " "
							exit 1
						else
							BROKEN_PKGS="$BROKEN_PKGS $module"
							unset BUILD_BROKEN
						fi
					fi
				fi

			else
				echo " "
				echo "No PKGBUILD found, exiting... :("
				echo " "
				exit 1	
			fi
	
			# Install packages	
			if [ "$_build_autoinstall" = "1" ] ; then
			# Look for the exact package names :

# 				pushd ${_build_work}/${module} &>/dev/null || exit 1
# 
# 				# get the pkgnames, different for an array and a bare string
# 				if [ `grep -e "^pkgname=" PKGBUILD | cut -d'=' -f2 | cut -c1` == "(" ] ; then
# 					# fetch the array
# 					_module_names=`pcregrep -M "^pkgname=\(.*(\n.*[^\)\n])*" PKGBUILD | sed s/"^[^\']*"//g | sed s/[^\']$//`
# 				else
# 					_module_names=("`grep -e "^pkgname=" PKGBUILD | cut -d'=' -f2`")
# 				fi
# 
# 				# version and rel
# 				#_modver=`grep -e "^pkgver=" PKGBUILD | cut -d'=' -f2`
# 				#_modrel=`grep -e "^pkgrel=" PKGBUILD | cut -d'=' -f2`
# 
# 				popd &>/dev/null
# 
# 				# build a list of packages and install them at once
# 				_packages_to_install=
# 				for _m in $_module_names ; do 
# 					#_pkg_full_name=`eval echo $_m-$_modver-$_modrel-*.pkg.*`
# 					_pkg_full_name=`eval echo $_m-*.pkg.*`
# 					_packages_to_install="$_packages_to_install $PKGDEST/$_pkg_full_name"
# 				done
# 				sudo pacman -Uf $_packages_to_install || exit 1

				sudo pacman -U ../_repo/local/${module}-*.pkg.*
			fi

	popd &>/dev/null
	done

	msg "removing debug packages ..."
	sudo pacman -Rcs kdemod-debug --noconfirm &>/dev/null
	echo " "
	echo " "	

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

time build_it f

if [ -z "$BROKEN_PKGS" ] ; then 
	title2 "All done"
else
	title2 "All done"
	title2 "SOME PACKAGES WERE NOT BUILT: $BROKEN_PKGS"
fi

newline
