
#  /sbin/splash-functions-extra.sh                                     #

#  Improved functions for Fbsplash                                     #
#                                                                      #
#  Author: Kurt J. Bosch        <kjb-temp-2009 at alpenjodel dot de>   #
#                                                                      #
#  Written for Chakra GNU/Linux and Fbsplash (aka splashutils) 1.5.4.3 #
#                                                                      #
#  Based on the work of                                                #
#          Michal Januszewski              <spock at gentoo dot org>   #
#          Greg Helton                    <gt at fallendusk dot org>   #
#          and others                                                  #
#                                                                      #
#  Distributed under the terms of the GNU General Public License v2    #

###  BASH 4 code to be sourced by splash-functions.sh or directly    ###

### This doesn't do anything usefull if no boot/shutdown/runlevel-change
### or no splash required on the kernel line
### Plain splash-functions.sh is even better when splash_setup() is
### needed to set fbcondecor after boot
[[ ${PREVLEVEL}_${RUNLEVEL} == ?_?    ]] || return 0
[[ ,${splash}, =~ ,(silent|verbose),  ]] || return 0

#### Basic environment
export spl_cachesize=4096
export spl_cachetype=tmpfs
export spl_cachedir=/lib/splash/cache
export spl_tmpdir=/lib/splash/tmp
export spl_fifo=${spl_cachedir}/.splash
export spl_pidfile=${spl_cachedir}/daemon.pid
export spl_util=/sbin/splash_util.static
export spl_daemon=/sbin/fbsplashd.static
export spl_decor=/sbin/fbcondecor_ctl.static
export spl_bindir=/lib/splash/bin

#### Exported runtime variables
typeset -ix SPLASH_STEPS
typeset -ix SPLASH_STEPS_DONE

#### Functions

# Setup parameters
#
## Don't use non local variables
## Init additional parameters
## Use kernel exported variable for simplicity
## (dropped support for multiple splash=... kernel line args)
#
splash_setup() {                # args: [force]
	# don't waste time on parsing the config files again
	if [[ $SPLASH_THEME && $SPLASH_TTY && ${1} != force ]]; then
		return
	fi
	# Set up defaults
	export SPLASH_EFFECTS=
	export SPLASH_SANITY=
	export SPLASH_TEXTBOX=no
	export SPLASH_MODE_REQ=off
	export SPLASH_PROFILE=off
	export SPLASH_THEME=default
	export SPLASH_TTY=16
	export SPLASH_KDMODE=TEXT
	export SPLASH_AUTOVERBOSE=0
	export SPLASH_BOOT_MESSAGE='Booting the system ($progress%)... Press F2 for verbose mode.'
	export SPLASH_SHUTDOWN_MESSAGE='Shutting down the system ($progress%)... Press F2 for verbose mode.'
	export SPLASH_REBOOT_MESSAGE='Rebooting the system ($progress%)... Press F2 for verbose mode.'
	export SPLASH_XSERVICE=xdm
	# additional configuration parameters
	export SPLASH_VERBOSE_ON_ERRORS=no
	export SPLASH_STAY_SILENT=
	export SPLASH_MESSAGE
	export SPLASH_MESSAGE_SINGLE
	export SPLASH_MESSAGE_BOOTED
	# Get in config files
	local file
	for file in /etc/splash/splash /etc/conf.d/{splash,fbcondecor,fbsplash-extras}
	do
		[ -f $file ] && . $file
	done
	# Get in parameters exported from the kernel cmdline
	local option
	for option in ${splash//,/ }; do
		case $option
		in theme:*    ) SPLASH_THEME=${option#*:}
		;; tty:*      ) SPLASH_TTY=${option#*:}
		;; silent     ) SPLASH_MODE_REQ=silent
		;; verbose    ) SPLASH_MODE_REQ=verbose
		;; kdgraphics ) SPLASH_KDMODE=GRAPHICS
		;; profile    ) SPLASH_PROFILE=on
		;; insane     ) SPLASH_SANITY=insane
		;; fadein | fadeout ) SPLASH_EFFECTS+=,$option
		esac
	done
	SPLASH_EFFECTS=${SPLASH_EFFECTS#,}
}

# Ensure the in-RAM filesystem is mounted
# Use 'force' on sysinit before /proc is available
#
## Allow to mount before rc_init
## Don't try to write to /etc/mtab - this is a temporary mount anyway
#
splash_cache_prep() {           # args: start|stop [force]
	# avoid double mount when called again on splash rc_init sysinit
	if [[ ${2} != force && $( </proc/mounts ) == *" "$spl_cachedir" "* ]]; then
		return
	fi
	# Mount an in-RAM filesystem at spl_cachedir
	/bin/mount -ns -t $spl_cachetype cachedir $spl_cachedir \
		-o rw,mode=0644,size=${spl_cachesize}k
	local retval=$?
	if [ $retval -ne 0 ]; then
		splash_err "Unable to mount splash cache filesystem - switching to verbose."
		splash_verbose
		return $retval
	fi
}

#### Main function for handling splash events
#  Known events and parameters
# Start the splash system or with 'boot', just enter multi-user mode
#  rc_init sysinit|boot|shutdown
# Stop the splash system
#  rc_exit
# Splash system error
#  critical
# Change to the verbose console for user input and back
#  svc_input_begin <name>
#  svc_input_end <name>
# Service is supposed to be started/stopped
#  svc_inactive_start <name>
#  svc_inactive_stop <name>
# Service is starting/stopping
#  svc_start <name>
#  svc_stop <name>
# Service has been started/stopped
#  svc_started <name>
#  svc_stopped <name>
# Service has failed to start/stop
#  svc_start_failed <name>
#  svc_stop_failed <name>
splash() {                      # args: <event> [arg...]
	local event=${1}
	shift
	# Reload the splash settings in rc_init to avoid incomplete setup
	if [[ $event = rc_init ]]; then
		splash_setup force
	else
		splash_setup
	fi
	# Do nothing if splash off required
	[[ $SPLASH_MODE_REQ = off ]] && return
	# Prepare for running any hook script
	local hook_args
	case $event
	in   rc_init )
		# Allways mount a in-RAM FS if not there or error if no /proc/mounts
		# Splash_cache_prep force should be called before this event if needed.
		splash_cache_prep || return
		hook_args="${1} $RUNLEVEL"
	;;   rc_exit )
		hook_args=$RUNLEVEL
	;;   svc_started | svc_stopped )
		# Provide error code for old themes
		hook_args="${1} 0"
	;;   * )
		hook_args=${1}
	esac
	# Profiling
	splash_profile pre $event $hook_args
	# Handle pre event hooks
	if [[ -x /etc/splash/$SPLASH_THEME/scripts/$event-pre ]]; then
		/etc/splash/"$SPLASH_THEME"/scripts/"$event"-pre $hook_args
	fi
	# Handle event
	local retval=0
	case $event
	in   critical )
		splash_verbose
	;;   svc_input_begin )
		if [[ $( splash_fgconsole ) = $SPLASH_TTY ]]; then
			splash_verbose
			export SPL_SVC_INPUT_SILENT=${1}
		fi
	;;   svc_input_end )
		if [[ $SPL_SVC_INPUT_SILENT = ${1} ]]; then
			splash_silent
			unset SPL_SVC_INPUT_SILENT
		fi
	;;   svc_start_failed )
		splash_svc_fail "${1}" start
	;;   svc_stop_failed )
		splash_svc_fail "${1}" stop
	;;   svc_started )
		# Avoid gpm garbling the splash
		if [[ ${1} = gpm ]]; then
			splash_comm_send set gpm
			splash_comm_send repaint
		fi
	;;&  svc_* )
		splash_comm_send update_svc "${1}" $event
		splash_comm_send paint
	;;   rc_init )
		splash_init ${1} || retval=1
	;;   rc_exit )
		splash_exit
	;;   * )
		splash_err "Unknown splash event '$event'"
	esac
	# Profiling
	splash_profile post $event $hook_args
	# Handle post event hooks
	if [ -x /etc/splash/"$SPLASH_THEME"/scripts/"$event"-post ]; then
		/etc/splash/"$SPLASH_THEME"/scripts/"$event"-post $hook_args
	fi
	return $retval
}

splash_err() {                  # args: <text>...
    echo "$@" >&2
}

splash_profile() {              # args: <text>...
    if [[ $SPLASH_PROFILE = on ]]; then
        local uptime idle
        read uptime idle </proc/uptime &&
        echo $uptime: $* >> $spl_cachedir/profile
    fi
}

# Switch to silent mode
splash_silent() {
    splash_comm_send set mode silent
}

# Switch to verbose mode
splash_verbose() {
    chvt 1
}

# Switch to given VT
chvt() {
    if [ -x /usr/bin/chvt ] ; then
        /usr/bin/chvt ${1}
    else
        printf "\e[12;${1}]"
    fi
}

# Get the active VT
splash_fgconsole() {
	# kbd fgconsole seemed to be more reliable then miscsplashutils one
	# but is only available if /usr mounted
	if [ -x /usr/bin/fgconsole ]; then
		/usr/bin/fgconsole
	else
		$spl_bindir/fgconsole
	fi
}

# Handle service failed
#
## don't write ugly generic log messages
## don't update progress here - we don't count backgrounded and replayed svcs; just paint
## don't omit stuff here when switching to verbose
#
splash_svc_fail() {             # args: <svc> start|stop
	splash_comm_send update_svc ${1} svc_${2}_failed
	splash_comm_send paint
	if [[ $SPLASH_VERBOSE_ON_ERRORS = yes ]]; then
		splash_verbose
	fi
}

# Send a command to the splash daemon
#
## don't try to use /usr/bin/basename
#
splash_comm_send() {            # args: <command> [arg...]
	if [[ $( /bin/pidof -o %PPID $spl_daemon ) ]]; then
		splash_profile comm "$@"
		echo "$@" >$spl_fifo &
	else
		return 1
	fi
}

# Wait until timeout or given binary finishes fadein/fadeout and dies
#
splash_fade_wait() {            # args: <binary-path>
	# broken systems and weird configurations having all of fadein,
	# blendin, blendout and fadeout may take very long
	local -i i=20
	while [[ i-- -gt 0 && $( /bin/pidof -o %PPID "${1}" ) ]]; do
		sleep 1
	done
}

# This is called when an 'rc_init' event takes place,
# i.e. when the runlevel is changed.
#
splash_init() {                 # args: sysinit|boot|shutdown
	if [[ $( /bin/pidof -o %PPID $spl_daemon ) ]]; then
		# Just grab the keyboard
		splash_set_event_dev
		return 0
	fi
	if [[ $SPLASH_MODE_REQ = silent ]]; then
		case ${1}
		in sysinit )
			# Prepare device nodes needed for starting the daemon
			if [[ $( /bin/pidof -o %PPID /sbin/udevd ) ]]; then
				/sbin/udevadm trigger --subsystem-match={tty,graphics,input}
			fi
			# Wait for any fbcondecor fadein from initcpio to finish
			splash_fade_wait fbcondecor_helper
			# Wait for udev to finish
			if [[ $( /bin/pidof -o %PPID /sbin/udevd ) ]]; then
				/sbin/udevadm settle
			fi
		esac
	fi
	# Start the splash
	PROGRESS=$( splash_get_progress ) \
		splash_start
	return $?
}

# Actually start Fbsplash
#
## Use splash type 'shutdown' when changing form multi to single user
## Avoid gpm garbling the splash if already running
## Don't do 'set mode silent' here
#
splash_start() {
	# Enable a nice fbcondecor background if possible
	case $SPLASH_MODE_REQ
	in   verbose )
		$spl_decor -c on 2>/dev/null
		return
	;;   silent )
		$spl_decor -c on 2>/dev/null
	;;   * )
		return
	esac
	# Check if the system is configured to display init messages on tty1
	if [[ $SPLASH_SANITY != insane ]]; then
		if [[ $( < /proc/cmdline ) =~ (^| )CONSOLE=/dev/tty1( |$) ]]; then
			# Check if /dev/tty1 was there on kernel load
			mount -n --bind / $spl_tmpdir
			[ -c $spl_tmpdir/dev/tty1 ]
			local checkval=$?
			umount -n $spl_tmpdir
			if [ $checkval -ne 0 ]; then
				splash_err "Fbsplash: ' CONSOLE=/dev/tty1 ' in kernel command line but /dev/tty1 missing in *root FS*"
				splash_verbose
				return 1
			fi
		elif ! [[ $( < /proc/cmdline ) =~ (^| )console=tty1( |$) ]]; then
			splash_err "Fbsplash requires ' console=tty1 ' or ' CONSOLE=/dev/tty1 ' in kernel command line"
			splash_verbose
			return 1
		fi
	fi
	# Remove any old pid file
	rm -f $spl_pidfile
	# Prepare the communications FIFO
	rm -f $spl_fifo
	mkfifo $spl_fifo
	# Start the splash daemon using the initial status message
	local args
	case ${PREVLEVEL}_$RUNLEVEL
	in *_0 | [^N]_[S1] ) args=--type=shutdown
	;; *_6             ) args=--type=reboot
	;; *               ) args=--type=bootup
	esac
	[[ $SPLASH_KDMODE = GRAPHICS ]] && args+=" "--kdgraphics
	[[ $SPLASH_EFFECTS           ]] && args+=" "--effects=$SPLASH_EFFECTS
	[[ $SPLASH_TEXTBOX = yes     ]] && args+=" "--textbox
	BOOT_MSG=$( splash_get_boot_message ) \
		$spl_daemon --theme=$SPLASH_THEME --pidfile=$spl_pidfile $args
	# Fallback to console
	if [ $? -ne 0 ]; then
		splash_err "Failed to start Fbsplash daemon"
		splash_verbose
		return 1
	fi
	# Avoid gpm garbling the splash if already running
	splash_comm_send set gpm
	# Repaint in case we are already on SPLASH_TTY
	splash_comm_send repaint
	# Get the keyboard
	splash_set_event_dev
	# Set the silent TTY
	splash_comm_send set tty silent $SPLASH_TTY
	# Set autoverbose timeout
	splash_comm_send set autoverbose $SPLASH_AUTOVERBOSE
	return 0
}

# Set the input device if it exists
# This will make it possible to use F2 to switch from verbose to silent
#
## code copied from /sbin/splash-function.sh
splash_set_event_dev() {
	local t="$(grep -Hsi keyboard /sys/class/input/input*/name | sed -e 's#.*input\([0-9]*\)/name.*#event\1#')"
	if [ -z "${t}" ]; then
		t="$(grep -Hsi keyboard /sys/class/input/event*/device/driver/description | grep -o 'event[0-9]\+')"
		if [ -z "${t}" ]; then
			for i in /sys/class/input/input* ; do
				if [ "$((0x$(cat $i/capabilities/ev) & 0x100002))" = "1048578" ]; then
					t="$(echo $i | sed -e 's#.*input\([0-9]*\)#event\1#')"
				fi
			done

			if [ -z "${t}" ]; then
				# Try an alternative method of finding the event device. The idea comes
				# from Bombadil <bombadil(at)h3c.de>. We're couting on the keyboard controller
				# being the first device handled by kbd listed in input/devices.
				t="$(/bin/grep -s -m 1 '^H: Handlers=kbd' /proc/bus/input/devices | grep -o 'event[0-9]*')"
			fi
		fi
	fi
	[ -n "${t}" ] && splash_comm_send "set event dev /dev/input/${t}"
}
##

# Get main status message text
splash_get_boot_message() {
	local msg
	# Get the configured status message text depending on runlevel
	case ${PREVLEVEL}_$RUNLEVEL
	in    *_0    ) msg=$SPLASH_SHUTDOWN_MESSAGE
	;;    *_6    ) msg=$SPLASH_REBOOT_MESSAGE
	;; [^N]_[S1] ) msg=$SPLASH_SINGLE_MESSAGE
	;;    *      ) msg=$SPLASH_BOOT_MESSAGE
	esac
	# Provide an updated customizable message
	if [[ $SPLASH_MESSAGE ]]; then
		local BUSY_MSG=$SPLASH_BUSY_MSG
		local SCRIPT=${0##*/}
		local PROGRESS=\$progress # the splash daemon knows this
		local RUNLEVEL_MSG=$msg
		eval msg="\"$SPLASH_MESSAGE\""
	fi
	# Avoid blank message string killing the splash daemon (weird)
	if [[ -z ${msg%% } ]]; then
		echo $'\302\240' # UTF-8 no-break space
	else
		echo "$msg"
	fi
}

# Update the splash main status message
splash_update_message() {
	if [[ $SPLASH_MESSAGE ]]; then
		splash_comm_send set message "$( splash_get_boot_message )"
		splash_comm_send paint
		# avoid autoverbose
		splash_update_progress
	fi
}

# Update the splash progress
splash_update_progress() {
	local PROGRESS
	PROGRESS=$( splash_get_progress ) || return 0
	splash_comm_send progress $PROGRESS
	splash_comm_send paint
}

# Calculate progress value
splash_get_progress() {
	if [[ -z $SPLASH_STEPS_DONE || ! $SPLASH_STEPS -gt 0 ]]; then
		return 1
	fi
	if [[ $SPLASH_STEPS_DONE -lt $SPLASH_STEPS ]]; then
		echo $(( 65535 * $SPLASH_STEPS_DONE / $SPLASH_STEPS ))
	else
		echo 65535 # 100%
	fi
}

# This function is called when an 'rc_exit' event takes place,
# i.e. at the end of processes all initscript from a runlevel.
#
## Don't do splash_cache_cleanup here
#
splash_exit() {                 # args: <runlevel>
	# Keep the daemon for entering multi-user mode to avoid any blendin
	# but release the keyboard to be save if rc.multi should not come
	case ${PREVLEVEL}_${RUNLEVEL}_$SPLASH_SINGLE
	in N_S_ | N_S_0 )
		splash_comm_send set event dev /dev/null
		return
	esac
	# Final status message for fadeout
	local msg action
	case ${PREVLEVEL}_$RUNLEVEL
	in N_S    ) SPLASH_MESSAGE='${SPLASH_MESSAGE_SINGLE}'
	;; *_[S1] ) SPLASH_MESSAGE='${SPLASH_MESSAGE_SINGLE}'; action=stop
	;; *_[06] ) SPLASH_BUSY_MSG=                         ; action=stop
	;; *      ) SPLASH_MESSAGE='${SPLASH_MESSAGE_BOOTED}'; action=start
	esac
	splash_update_message
	# 100% progress
	SPLASH_STEPS_DONE=$SPLASH_STEPS
	splash_update_progress
	# Force rendering
#	splash_comm_send repaint
	# Stop the splash daemon
	case ${PREVLEVEL}_${RUNLEVEL}_$SPLASH_STAY_SILENT
	in *_[06]_* )
		splash_comm_send exit staysilent
	;; *_5_yes ) # old config way
		splash_comm_send exit staysilent
	;; * )
		# new config way
		if [[ " "$SPLASH_STAY_SILENT" " == *" "$RUNLEVEL" "* ]]
		then splash_comm_send exit staysilent
		else splash_comm_send exit
		fi
	esac
	# Give it some time
	splash_fade_wait $spl_daemon
}

# Umount the in-RAM filesystem saving any profile and given files and dirs
#
## Don't create the tmpdir - should already be there
## Kill the splash daemon even if not mounted
## Umount even if /etc not writable
## Don't use /etc/mtab
## Don't skip copy silently if cachedir is readonly, but error
#
splash_cache_cleanup() {        # args: [<file>|<dir>]...
	# Make sure to get rid of the daemon
	local pid
	if pid=$( /bin/pidof -o %PPID $spl_daemon ); then
		kill -SIGKILL $pid
		sleep 1
	fi
	# Don't try to clean anything up if the cachedir is not mounted
	if ! [[ $( </proc/mounts ) == *" "$spl_cachedir" "* ]]; then
		return
	fi
	local mountpoint=$spl_cachedir
	if
		/bin/mount -n --move $mountpoint $spl_tmpdir
	then
		mountpoint=$spl_tmpdir
		if [[ $SPLASH_PROFILE != off ]]; then
			set profile "$@"
		fi
		if [ $# -gt 0 ]; then
			( cd $spl_tmpdir/ && /bin/cp -a "${@}" $spl_cachedir/ )
		fi
	fi
	/bin/umount -n -l $mountpoint
}

# Get the list of services to be started/stopped
#
splash_svclist_get() {          # args: start|stop
    if [[ -r $spl_cachedir/svcs_${1} ]]; then
		echo "$( <$spl_cachedir/svcs_${1} )"
	fi
}

### Only export functions essential for theme hook scripts and dependant
#   to gain more speed

#export -f splash
#export -f splash_setup
#export -f splash_get_boot_message
#export -f splash_start
#export -f splash_cache_prep
#export -f splash_cache_cleanup
export -f splash_comm_send
#export -f chvt
#export -f splash_verbose
#export -f splash_silent
export -f splash_profile
#export -f splash_set_event_dev
export -f splash_svclist_get

# EOF #
