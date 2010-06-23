
#  /etc/rc.d/functions.d/fbsplash-extras.sh                            #

#  Fbsplash Extras for Chakra GNU/Linux initscripts                          #
#                                                                      #
#  Author: Kurt J. Bosch        <kjb-temp-2009 at alpenjodel dot de>   #
#                                                                      #
#  Based on the work of                                                #
#          Greg Helton                    <gt at fallendusk dot org>   #
#          Thomas Baechler             <thomas at archlinux dot org>   #
#          and others                                                  #
#                                                                      #
#  Distributed under the terms of the GNU General Public License (GPL) #

###  BASH 4 code intended to be sourced by /etc/rc.d/functions       ###

## Functions also callable from outside and dependants

# Get a (rough) list of 'services' to start/stop from given initscript
# for triggering splash progress and events
#
splash_initscript_svcs_get() {        # args: <initscript> [list]
	local fd line msg svc
	exec {fd}<"$1" || return
	while read -u $fd line ; do
		[[ $line =~ (^|[[:space:]])(stat_busy|status)[[:space:]]+(\"([^\"]+)\")? ]] || continue
		msg=${BASH_REMATCH[4]}
		# Sort out skipped
		case $msg
		in *SIGTERM* | *SIGKILL*   ) continue      ### FIXME ###    killall5 should omit the daemon
		;; "Loading Console Font"* ) continue      ### FIXME ###    obsolete as soon as in functions
		esac
		# Print full list
		if [[ ${2} = list ]]; then
			echo $( splash_msg_to_svc "$msg" ) "$msg" 
			continue
		fi
		# Try to sort out inactive
		case $msg
		in "Loading Modules"     ) ! [[ $load_modules = off ]]
		;; *RAID*                ) splash_test_file -r /etc/mdadm.conf 'ARRAY.*'
		;; *LVM*                 ) [[ ${USELVM,,*} = yes ]]
		;; *"encrypted volumes"* ) splash_test_file -r /etc/crypttab
		;; "Setting Hostname"*   ) [[ $HOSTNAME ]]
		;; "Setting NIS Domain Name"* )
			(	[ -r /etc/conf.d/nisdomainname ] && . /etc/conf.d/nisdomainname
				[[ $NISDOMAINNAME ]] )
		;; "Loading Keyboard Map"* ) [[ $KEYMAP ]]
		;; "Setting Consoles to UTF-8 mode"  ) [[ $LOCALE =~ (utf|UTF) ]]
		;; "Setting Consoles to legacy mode" ) ! [[ $LOCALE =~ (utf|UTF) ]]
		;; "Adding persistent cdrom udev rules" ) 
			[ -f /dev/.udev/tmp-rules--70-persistent-cd.rules ]
		;; "Adding persistent network udev rules" )
			[ -f /dev/.udev/tmp-rules--70-persistent-net.rules ]
		esac || continue
		# echo a service name
		splash_msg_to_svc "$msg"
	done
	exec {fd}<&-
}

# Test a file and check if it contains any significant lines
#
splash_test_file() {            # args: <test-operator> <file> [<regex>]
	local regex=${3:-'[[:space:]]*[^#[:space:]].*'}
	test ${1} "${2}" && [[ $( <"${2}" ) =~ (^|$'\n')${regex}($'\n'|$) ]]
}

# Generate a 'service' name from a initscript stat_busy message text
#
splash_msg_to_svc() {           # args: <message>
	local msg=${1}
	msg=${msg,,*}    # make lowercase
	msg=${msg%%:*}   # remove variables part
	local svc
	# Try to get an action and object
	if [[ $msg =~ ^(de|un)?(([a-z]+)ing )?((for|up|down|on|off) )?((.{4,}) to .*|(.{4,}))$ ]]
	then
		local action=${BASH_REMATCH[3]}
		local object=${BASH_REMATCH[7]}${BASH_REMATCH[8]}
		# Drop most of the actions to get good start/stop matching
		case $action
		in (activat|add|bring|configur|initializ|load|lock|remov|sav|sett|start|stop)
			svc=$object
		;; (*)
			svc="$action $object"
		esac
	else
		svc=${msg}
	fi
	# Convert whitespace
	svc=${svc//[ $'\t']/_}
	# Fix remaining non-matches
	case $svc
	in   mount_filesystems ) svc=mount_local_filesystems
	esac
	# Use some 'namespace' to allow distinguishing from daemons
	echo _init_$svc
}

##

# Don't go on if not boot, shutdown or single-multi-change
[[ $PREVLEVEL == [NS1-5] && $RUNLEVEL == [S0-6] ]] || return 0
# Don't go on if no splash required on kernel line
[[ ,$splash, =~ ,(silent|verbose), ]] || return 0

# /sbin/splash-functions.sh not used here any more
. /sbin/splash-functions-extra.sh
splash_setup

# Export additional config for the daemon scripts
export SPLASH_MSGLOG_BUSY
export SPLASH_MSGLOG_DONE
export SPLASH_MSGLOG_FAIL

declare -A splash_steps_init=()

# Time based splash daemon restart and progress on shutdown
splash_sleep_prekill=2 # time for painting
splash_sleep_sigterm=5 # from rc.shutdown
splash_sleep_sigkill=1 # from rc.shutdown
splash_sleep_total=$(( splash_sleep_prekill+splash_sleep_sigterm+splash_sleep_sigkill ))

# Allow simulation
splash_script_path=${splash_script_path:-${0}}
splash_script=${splash_script_path#/etc/rc.}
splash_var_run_daemons=${splash_var_run_daemons:-/var/run/daemons}

# Mount the in-RAM FS if forced or not already in /proc/mounts
#
splash_mount_tmpfs() {          # args: start|stop [force]
	stat_busy "Preparing Fbsplash Cache"
	splash_cache_prep $*
	local retval=$?
	if [ $retval -eq 0 ]; then
		stat_done
	else
		stat_fail
	fi
	return $retval
}

case ${splash_script}_${PREVLEVEL}
in   single_N )
	# rc.single doesn't do much when booting to single-user
	return
;;   sysinit_? )
	# Mount the in-RAM FS here mainly to catch any error
	splash_mount_tmpfs start force || return 0
;;&  multi_? )
	# The in-RAM FS is not there on single->multi
	if [[ $( </proc/mounts ) != *" "${spl_cachedir}" "* ]]; then
		splash_mount_tmpfs start || return 0
	fi
;;&  sysinit_? | multi_? )
	# Init and start splash
	export splash_action=start
	export splash_action_done=started
	add_hook sysinit_udevlaunched       splash_begin
	add_hook multi_start                splash_begin
;;   shutdown_? | single_? )
	# Mount the in-RAM FS on shutdown too to get/keep a clean cache-dir/root-FS
	splash_mount_tmpfs stop || return 0
	export splash_action=stop
	export splash_action_done=stopped
	add_hook ${splash_script}_start     splash_begin
;; * )
	# Even daemon scripts shall not go on if the in-RAM FS failed to mount
	if [[ $( </proc/mounts ) != *" "$spl_cachedir" "* ]]; then
		return
	fi
esac

# Start the splash
splash_begin() {
	# avoid override to allow simulation
	if [[ -z $SPLASH_SINGLE ]] ; then
		if [[ ${PREVLEVEL} != N || " "$( </proc/cmdline )" " =~ " "(s|S|single|1)" " ]]
		then SPLASH_SINGLE=1
		else SPLASH_SINGLE=0
		fi
	fi
	local SPLASH_INHIBIT_STAT=1
	local SPLASH_BUSY_MSG=
	local level=$splash_script
	case ${splash_script}_$SPLASH_SINGLE 
	in   multi_0 )
		stat_busy "Continuing Fbsplash"
	;;   multi_1 )
		SPLASH_BUSY_MSG="Entering multi-user mode"
	;;&  single_? )
		level=shutdown
	;;&  * )
		stat_busy "Starting Fbsplash"
	esac
	# Get ordered rough list of initscript 'services' to start/stop
	local -a splash_svclist_init
	case ${splash_script}_$SPLASH_SINGLE
	in   multi_0 )
		splash_svclist_init=( $( splash_initscript_svcs_get /etc/rc.sysinit ) )
	;;   * )
		splash_svclist_init=( $( splash_initscript_svcs_get ${splash_script_path} ) )
	esac
	# Provide pre-rc.local daemon name for splash_rc_local_begin   ### FIXME ###   no hooks
	splash_pre_rc_local_svc=_none_
	SPLASH_SVC_NAME=$splash_pre_rc_local_svc
	# Get ordered list of foreground 'daemons' including '_rc_local'
	local -a daemons
	case ${splash_script}_$SPLASH_SINGLE 
	in   sysinit_0 | multi_* )
		splash_daemons() {
			local daemon
			for daemon in "${DAEMONS[@]}"; do
				daemon=${daemon%% }
				case $daemon
				in   \@$SPLASH_XSERVICE | $SPLASH_XSERVICE )
					return
				;;   \!* | \@* )
					continue
				;;     * )
					daemons+=( $daemon )
					splash_pre_rc_local_svc=$daemon
				esac
			done
			if splash_test_file -x /etc/rc.local; then 
				daemons+=( _rc_local )
			fi
		}
		splash_daemons
	;;   shutdown_* )
		if splash_test_file -x /etc/rc.local.shutdown; then
			daemons+=( _rc_local )
		fi
	;;&  single_* | shutdown_* )
		# 'daemons' NOT in the DAEMONS array are shut down first in reverse order of start
		local daemon
		if [ -d $splash_var_run_daemons ]; then
			for daemon in $( /bin/ls -1t $splash_var_run_daemons ); do
				if ! in_array $daemon ${DAEMONS[@]}; then
					daemons+=( $daemon )
				fi
			done
		fi
		# Reverse order of rc.multi start
		local i daemon
		for (( i=${#DAEMONS[@]}-1; i>=0; i-- )) do
			[[ ${DAEMONS[i]} == \!* ]] && continue
			daemon=${DAEMONS[i]#@}
			if [[ -f $splash_var_run_daemons/$daemon ]]; then
				daemons+=( $daemon )
			fi
		done
	esac
	# Init step counting for progress
	SPLASH_STEPS=0
	SPLASH_STEPS_DONE=0
	local -a svclist
	local -i step_init=1
	case ${splash_script}_$SPLASH_SINGLE
	in   shutdown_* | single_* )
		SPLASH_STEPS+=${#splash_svclist_init[@]}
		# daemons stop very fast, but paint takes time and SIGTERM sleep ages
		SPLASH_STEPS+=splash_sleep_total
		step_init+=splash_sleep_total
		#SPLASH_STEPS+=${#daemons[@]}
		#step_init+=${#daemons[@]}
		svclist=( ${daemons[@]} ${splash_svclist_init[@]} )
	;;   multi_0 )
		SPLASH_STEPS_DONE+=${#splash_svclist_init[@]}
	;;&  sysinit_* | multi_* )
		SPLASH_STEPS+=${#splash_svclist_init[@]}
		SPLASH_STEPS+=${#daemons[@]}
		svclist=( ${splash_svclist_init[@]} ${daemons[@]} )
	esac
	# Provide the theme hooks with the svclist
	echo ${svclist[@]} >| $spl_cachedir/svcs_$splash_action
	# Create a steps dictionary for the ordered but rough part
	local svc
	for svc in ${splash_svclist_init[@]}; do
		[[ ${splash_steps_init[$svc]} ]] || splash_steps_init[$svc]=$step_init
		step_init+=1
	done
	# Avoid loosing fadein when booted with staysilent and Xorg
	case ${level}_$SPLASH_MODE_REQ in ( shutdown_silent )
		if [[ $SPLASH_EFFECTS == *fadein* && $( splash_fgconsole ) = $SPLASH_TTY ]]; then
			chvt 63
		fi
	esac
	# Actually start/continue splash
	splash rc_init $level
	if [ $? -ne 0 ]; then
		stat_fail
		return
	fi
	if [[ ${splash_script}_$SPLASH_SINGLE != multi_0 ]]; then
		# Activate the splash 
		splash_comm_send set mode silent
		# Init splash services states 'inactive'
		splash_profile comm update_svc svc_inactive_$splash_action "[LOOP]"
		local svc
		for svc in ${svclist[@]} ; do
			splash svc_inactive_$splash_action $svc
		done
		# Send any stat_messages we missed to the msglog textbox
		splash_msglog_send
	fi
	# Avoid setfont destroying the splash screen
	SPLASH_CONSOLEFONT=$CONSOLEFONT
	if [[ $SPLASH_MODE_REQ = silent ]]; then
		CONSOLEFONT=
	fi
	stat_done
}

# Send the cached message log to the splash daemon
splash_msglog_send() {
	local file=$spl_cachedir/comm_log
	if [[ -r $file && $( /bin/pidof -o %PPID $spl_daemon ) ]]; then
		splash_profile comm log "[REPLAY]"
		echo "$( <$file )" >$spl_fifo &
#		splash_comm_send repaint
	fi
}

# Trigger service starting/stopping event and export service name
splash_daemon_begin() {
	splash svc_$splash_action $daemon
	export SPLASH_SVC_NAME=$daemon
}

# Trigger service started/stopped event and unset service name
splash_daemon_end() {
	if [ $daemonret -ne 0 ]; then
		SPLASH_BUSY_MSG="'$daemon' exit code: $daemonret"
		splash_stat_fail
	elif ! [[ -f $spl_cachedir/${splash_action}_failed-$daemon ]]; then
		splash svc_$splash_action_done $daemon
	fi
}

splash_rc_local_begin() {
	if [[ $SPLASH_SVC_NAME = $splash_pre_rc_local_svc ]]; then
		splash svc_$splash_action _rc_local
		export SPLASH_SVC_NAME=_rc_local
	fi
}

splash_rc_local_end() {
	if [[ $SPLASH_SVC_NAME = _rc_local &&
		  ! -f $spl_cachedir/${splash_action}_failed-$SPLASH_SVC_NAME ]]; then
		splash svc_$splash_action_done $SPLASH_SVC_NAME
	fi
}

# Increment steps done and update the splash progress
splash_step_done() {
	SPLASH_STEPS_DONE+=1
	splash_update_progress
}

# Get a file descriptor and start a daemon for pushing progress info
# from 'fsck -C$FSCK_FD' into the splash status message line
splash_fsck_forward_d() {
	[[ -w $spl_fifo && $( /bin/pidof -o %PPID $spl_daemon ) ]] || return
	local fsck_fifo=$spl_cachedir/fsck_fifo
	# drop any old fifo and create a new one
	/bin/rm -f $fsck_fifo
	/bin/mkfifo -m 600 $fsck_fifo || return
	(
		base_msg=$( splash_get_boot_message )
		paint_pid=
		fifo_pid=
		fs_phase=
		pgr=-1
		while true; do
			read -t 2 phase step total fs; ret=$?
			if [ $ret -eq 0 ]; then
				if [[ $fs_phase != ${fs}_$phase ]]; then
					fs_phase=${fs}_$phase
					[[ $( /bin/pidof -o %PPID $spl_daemon ) ]] || continue
					if [[ -z $paint_pid ]]; then
						# paint and avoid autoverbose
						( while /bin/sleep 2; do splash_update_progress; done ) &
						paint_pid=$!
					fi
				fi
				new_pgr=$(( 100 * step / total ))
				[ $new_pgr -eq $pgr ] && continue
				pgr=$new_pgr
				pgr_msg="[ ${fs}  phase ${phase}  ${pgr}% ]"
				# avoid delayed messages
				[[ $fifo_pid ]] && kill $fifo_pid 2>/dev/null
				echo "set message ${base_msg} ${pgr_msg}" >"${spl_fifo}" &
				fifo_pid=$!
			elif [ $ret -gt 128 ]; then # timeout
				[ $pgr -lt 100 ] && continue
				# for some FS types the fsck progress file descriptor isn't used
				kill $paint_pid
				paint_pid=
				fs_phase=
				pgr=-1
				splash_update_message
			else
				break
			fi
		done
		kill $paint_pid
	) &>/dev/null <$fsck_fifo &
	exec {FSCK_FD}>$fsck_fifo
}
splash_fsck_begin() {
	if [[ $SPLASH_MODE_REQ = silent && $SPLASH_MESSAGE ]]; then
		SPLASH_INHIBIT_STAT=1 \
			stat_append " (progress forwarded to Fbsplash)"
		echo # newline!
		splash_fsck_forward_d
	fi
}
splash_fsck_end() {
	if [[ $FSCK_FD ]]; then
		exec {FSCK_FD}>&-
		unset FSCK_FD
	fi
	# Handle fsck failure
	if [ ${fsckret} -gt 1 -a ${fsckret} -ne 32 ]; then
		# emergency exit to console for message display and reboot
		splash_comm_send exit
	fi
}

case $splash_script
in sysinit )
	# Forward fsck progress to the status line
	add_hook sysinit_prefsck      splash_fsck_begin
	add_hook sysinit_prefsckloop  splash_fsck_begin
	add_hook sysinit_postfsck     splash_fsck_end
	add_hook sysinit_postfsckloop splash_fsck_end
;; multi )
	# Stop splash before Xorg is started to avoid VT/keyboard struggle
	add_hook pre_daemon_start   splash_end_on_xorg
	add_hook fork_daemon_bkgd   splash_end_on_xorg
	splash_end_on_xorg() {
		if [[ $daemon = $SPLASH_XSERVICE ]]; then
			SPLASH_STAY_SILENT=$RUNLEVEL
			splash_end xorg
		fi
	}
	# Disable splash_update_message
	add_hook pre_daemon_bkgd    splash_unset_message
	splash_unset_message() {
		SPLASH_MESSAGE=
	}
	# Trigger service starting/stooping event and export name for stat_fail
	add_hook pre_daemon_bkgd    splash_daemon_begin        
	add_hook pre_daemon_start   splash_daemon_begin
	# Change to verbose console if user input required
	add_hook pre_daemon_start   splash_daemon_input_begin
	splash_daemon_input_begin() {
		if [[ $daemon = net-profiles ]]; then
			local net
			for net in "${NETWORKS[@]}"; do
				[[ $net = menu ]] || continue
				splash_svc_input=1
				break
			done
		fi
		[[ $splash_svc_input ]] && splash svc_input_begin $daemon
	}
	add_hook post_daemon_start  splash_daemon_input_end
	splash_daemon_input_end() {
		if [[ $splash_svc_input ]]; then
			unset splash_svc_input
			splash svc_input_end $daemon
		fi
	}
	# Trigger service started/stopped event
	add_hook post_daemon_start  splash_daemon_end
	add_hook post_daemon_bkgd   splash_daemon_end
	# Progress
	add_hook post_daemon_start  splash_step_done
	# Handle _rc_local service and stop splash
	if ! in_array "$SPLASH_XSERVICE" "${DAEMONS[@]}"; then
		if splash_test_file -x /etc/rc.local; then    
			                                             ### FIXME ###   no hooks for rc_local
			### use splash_daemon_begin and splash_daemon_end as soon as suitable hooks provided
			add_hook post_daemon_start  splash_rc_local_begin
			add_hook multi_end          splash_rc_local_end
			###
			add_hook multi_end          splash_step_done
		fi
		add_hook multi_end      splash_end
	else
		add_hook multi_end      splash_cache_cleanup
	fi
;; shutdown )
	# Handle _rc_local service
	if splash_test_file -x /etc/rc.local.shutdown; then   
		                                                 ### FIXME ###   no hooks for rc_local_shutdown
		### use splash_daemon_begin and splash_daemon_end as soon as suitable hooks provided
		add_hook shutdown_start   splash_rc_local_begin
		add_hook pre_daemon_stop  splash_rc_local_end
		add_hook stat_busy        splash_rc_local_end
		###
	fi
	# Forward fsck progress to the status line
	add_hook shutdown_prefsck      splash_fsck_begin
	add_hook shutdown_prefsckloop  splash_fsck_begin
	add_hook shutdown_postfsck     splash_fsck_end
	add_hook shutdown_postfsckloop splash_fsck_end
;;& shutdown | single )
	# Trigger service events and progress
	add_hook pre_daemon_stop    splash_daemon_begin
	add_hook post_daemon_stop   splash_daemon_end
#	## Progress
#	add_hook post_daemon_stop   splash_step_done
	
	### FIXME ###     killall5 should omit the splash daemon
	
	# Give the splash daemon a chance to paint while doing some progress
	# Restart the splash when terminated                     ### FIXME ###   no post_sigterm hook
	### [PATCH] http://bugs.archlinux.org/task/10287#comment58492
	add_hook ${splash_script}_prekillall  splash_restart_d
	splash_restart_d () {
		local i
		for (( i=0; i<splash_sleep_prekill; i++ )) do
			sleep 1
			splash_step_done
		done
		local -i steps=splash_sleep_sigterm+splash_sleep_sigkill
		(
			trap : SIGTERM
			started=
			for (( i=0; i<steps; i++ )) do
				if [[ ! $started && ! $( /bin/pidof -o %PPID $spl_daemon ) ]]; then
					splash_restart
					started=1
				fi
				sleep 1
				splash_step_done
			done
		) &
		SPLASH_STEPS_DONE+=$steps
	}
	# Restart the splash daemon again
	add_hook ${splash_script}_postkillall splash_restart
	splash_restart() {
		SPLASH_RESTART=1 \
			splash rc_init shutdown
		if [[ -f $spl_cachedir/stop_failed-fbsplash-dummy ]]; then
			splash_comm_send update_svc fbsplash-dummy svc_stop_failed
			splash_comm_send paint
		fi
		splash_msglog_send
	}
	
	###
	
esac

## Update/log message, trigger service events, do initscript progress and handle stat_fail

add_hook stat_busy   splash_stat_busy   
splash_stat_busy() {
	[[ $SPLASH_INHIBIT_STAT ]] && return
	SPLASH_BUSY_MSG=$statmsg
	splash_update_message
	splash_msglog_add "$SPLASH_MSGLOG_BUSY"
#	# force rendering of messages
#	splash_comm_send repaint
	case $splash_script in ( sysinit | shutdown | single )
		SPLASH_SVC_NAME=$( splash_msg_to_svc "$statmsg" )
		splash svc_$splash_action $SPLASH_SVC_NAME
	esac
}
add_hook stat_append splash_stat_append 
splash_stat_append() {
	[[ $SPLASH_INHIBIT_STAT ]] && return
	SPLASH_BUSY_MSG+=$statmsg
	splash_update_message
#	# force rendering of messages
#	splash_comm_send repaint
}
add_hook stat_fail   splash_stat_fail   
splash_stat_fail() {
	[[ $SPLASH_INHIBIT_STAT ]] && return
	# Daemon status
	if [[ $SPLASH_SVC_NAME &&
	      ! -f $spl_cachedir/${splash_action}_failed-$SPLASH_SVC_NAME ]]; then
		splash svc_${splash_action}_failed $SPLASH_SVC_NAME
		: >| $spl_cachedir/${splash_action}_failed-$SPLASH_SVC_NAME
	fi
	# General failure status fake service
	# avoid running theme hooks, but respect verbose on errors
	splash_svc_fail fbsplash-dummy $splash_action
	: >| $spl_cachedir/${splash_action}_failed-fbsplash-dummy
	# Log message
	splash_msglog_add "$SPLASH_MSGLOG_FAIL"
	# initscript progress
	case $splash_script in ( sysinit | shutdown | single )
		splash_step_done_init
	esac
}
add_hook stat_done   splash_stat_done   
splash_stat_done() {
	[[ $SPLASH_INHIBIT_STAT ]] && return
	splash_msglog_add "$SPLASH_MSGLOG_DONE"
	case $splash_script in ( sysinit | shutdown | single )
		if [[ ! -f $spl_cachedir/${splash_action}_failed-$SPLASH_SVC_NAME ]]; then
			splash svc_$splash_action_done $SPLASH_SVC_NAME
		fi
		splash_step_done_init
	esac
}

splash_step_done_init() {
	local step=${splash_steps_init[$SPLASH_SVC_NAME]}
	if [[ $SPLASH_STEPS_DONE -lt $step ]]; then
		SPLASH_STEPS_DONE=$step
		splash_update_progress
	fi
}

# Evaluate a log line, send it to the msglog textbox and add it to the cache file
#
splash_msglog_add() {              # arg: <string-expression>
	local SCRIPT=${0##*/}
	local BUSY_MSG=$SPLASH_BUSY_MSG
	local msg
	eval msg="\"${1}\""
	# avoid blank log lines - would even kill the splash daemon
	if [[ ${msg%% } ]]; then
		local cmd="log $msg"
		splash_comm_send "$cmd"
		echo "$cmd" >> $spl_cachedir/comm_log
	fi
}

## Stop splash or if sysinit, just release the keyboard
#
add_hook sysinit_end       splash_end
add_hook shutdown_poweroff splash_end
add_hook single_end        splash_end
splash_end() {                  # args: [xorg]
	local SPLASH_INHIBIT_STAT=1
	case ${splash_script}_$SPLASH_SINGLE
	in sysinit_0 )
		# This should just release the keyboard and run any theme hooks
		splash rc_exit
	;; * )
		stat_busy "Stopping Fbsplash"
		# Stop splash
		splash rc_exit
		# Make sure to get rid of the daemon and umount the in-RAM FS
		if [[ ${1} != xorg ]]; then
			splash_cache_cleanup
		fi
		stat_done
	;;& sysinit_1 | multi_* )
		# Set consolefont
		if [[ $SPLASH_MODE_REQ = silent ]]; then
			CONSOLEFONT=$SPLASH_CONSOLEFONT
			set_consolefont
		fi
	esac
}

# EOF #
