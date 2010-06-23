
#  /etc/rc.d/functions.d/fbsplash.sh                                       #

#  Chakra GNU/Linux initscripts extras for Fbsplash - Bare Minimum Variant #
#                                                                          #
#  Author: Kurt J. Bosch        <kjb-temp-2009 at alpenjodel dot de>       #
#                                                                          #
#  Based on the work of                                                    #
#          Greg Helton                    <gt at fallendusk dot org>       #
#          Thomas Baechler             <thomas at archlinux dot org>       #
#          and others                                                      #
#                                                                          #
#  Distributed under the terms of the GNU General Public License (GPL)     #

# Don't go on if not boot or shutdown
[[ ${PREVLEVEL}_$RUNLEVEL == N_[S2-5] || ${PREVLEVEL}_$RUNLEVEL == [^S]_[06] ]] || return 0
# Don't go on if no splash required on kernel line
[[ ,$splash, =~ ,(silent|verbose), ]] || return 0
# Don't go on if full featured scripts are installed
[ -r /etc/rc.d/functions.d/fbsplash-extras.sh ] && return

# Also sourced by this at least once:
# /sbin/splash-functions-*.sh
# /etc/splash/splash
# /etc/conf.d/splash
# /etc/conf.d/fbcondecor
. /sbin/splash-functions.sh

# export these too, like the other config paramters
export SPLASH_DAEMON
export SPLASH_VERBOSE_ON_ERRORS

case $0
in   /etc/rc.single )
	return
;;   /etc/rc.sysinit | /etc/rc.multi )
	add_hook sysinit_udevlaunched deferre_setfont
	deferre_setfont() {
		if [[ ,$splash, == *,silent,* &&
			! " "$( </proc/cmdline )" " =~ " "(s|S|single|1)" " ]]; then
			CONSOLEFONT=""
		fi
	}
	if [[ $SPLASH_DAEMON != no ]]; then
		add_hook sysinit_udevlaunched splash_begin
		splash_begin() {
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
			# Start splash
			splash rc_init sysinit
		}
		add_hook sysinit_udevsettled splash_progress
		add_hook sysinit_premount    splash_progress
		add_hook sysinit_end         splash_progress
		SPLASH_STEPS=4
		SPLASH_STEPS_DONE=0
		if [[ $0 = /etc/rc.multi ]]; then
			SPLASH_STEPS_DONE=3
		fi
	fi
	add_hook sysinit_end         splash_end
	add_hook multi_end           splash_end
	add_hook multi_end           deferred_setfont
	deferred_setfont() {
		if [[ ,$splash, == *,silent,* &&
			! " "$( </proc/cmdline )" " =~ " "(s|S|single|1)" " ]]; then
			set_consolefont
		fi
	}
esac

splash_end() {
	case $RUNLEVEL
	in S     )
		# Keep the splash daemon for rc.multi
		if ! [[ " $( </proc/cmdline ) " =~ " "(s|S|single|1)" " ]]; then
			SPLASH_EXIT_TYPE=keep
		fi
	;; [056] )
		# Don't chvt
		SPLASH_EXIT_TYPE=staysilent
	esac
	if [[ $SPLASH_DAEMON != no ]]; then
		splash rc_exit
	elif [[ ! $SPLASH_EXIT_TYPE ]]; then
		chvt 1
	fi
}

stat_fail() {
	deltext
	printf "   ${C_OTHER}[${C_FAIL}FAIL${C_OTHER}]${C_CLEAR} \n"
	
	if [[ $SPLASH_DAEMON = no ]]; then
		if [[ $SPLASH_VERBOSE_ON_ERRORS = yes ]]; then
			chvt 1
		fi
		return
	fi

	if [ $PREVLEVEL = N ]; then
		splash_action_failed=start_failed
	else
		splash_action_failed=stop_failed
	fi
	splash svc_$splash_action_failed ${0##*/}
	splash_comm_send update_svc fbsplash-dummy svc_$splash_action_failed
	splash_comm_send paint
	: >| $spl_cachedir/$splash_action_failed-fbsplash-dummy
}

case $0
in   /etc/rc.shutdown )
	if [[ $SPLASH_DAEMON = no ]]; then
		add_hook shutdown_start splash_helper
		splash_helper() {
			if [[ $SPLASH_MODE_REQ = silent ]]; then
				case $RUNLEVEL
				in   6 ) BOOT_MSG=$SPLASH_REBOOT_MESSAGE
				;;   * ) BOOT_MSG=$SPLASH_SHUTDOWN_MESSAGE
				esac
				export BOOT_MSG
				/sbin/fbcondecor_helper 2 init 0 0 $SPLASH_THEME
			fi
		}
		return
	fi
	add_hook shutdown_start splash_begin
	splash_begin() {
		splash rc_init shutdown
		splash_comm_send set gpm
		splash_comm_send repaint
	}
	add_hook shutdown_prekillall  splash_progress
	add_hook shutdown_postkillall splash_progress
				  ## killall5 should omit the daemon ##    ### FIXME ###
	add_hook shutdown_prekillall  splash_paint_sleep
	splash_paint_sleep() {
		sleep 2
		splash_progress
	}
	add_hook shutdown_postkillall splash_restart
	splash_restart() {
		[ "$( /usr/bin/fgconsole )" = "$SPLASH_TTY" ] || return 0
		splash_start
		if [ -f $spl_cachedir/stop_failed-fbsplash-dummy ]; then
			splash_comm_send update_svc fbsplash-dummy svc_stop_failed-fbsplash-dummy
			splash_comm_send paint
		fi
	}
	add_hook shutdown_poweroff    splash_end
	SPLASH_STEPS=4
	SPLASH_STEPS_DONE=0
	rm -f $spl_cachedir/stop_failed-fbsplash-dummy
esac

if [[ $SPLASH_DAEMON = no ]]; then
	return
fi

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

splash_progress() {
	export PROGRESS=$(( 65535*++SPLASH_STEPS_DONE/SPLASH_STEPS ))
	splash_comm_send progress $PROGRESS
	splash_comm_send paint
}

# Callback for 'splash rc_exit'
#
splash_exit() {                 # args: <runlevel>
	if [[ $SPLASH_EXIT_TYPE = keep ]]; then
		return
	fi
	splash_comm_send progress 65535
	splash_comm_send paint
	sleep 1
	splash_comm_send exit $SPLASH_EXIT_TYPE
	# Wait for the daemon to exit
	splash_fade_wait $spl_daemon
	# This kills any splash daemon the hard way (blackscreen)
	splash_cache_cleanup
}

start_daemon() {
	if [ $1 = "$SPLASH_XSERVICE" ]; then
		RUNLEVEL=5 splash_end
	fi
	/etc/rc.d/$1 start
	if [ $1 = gpm ]; then
		splash_comm_send set gpm
		splash_comm_send repaint
	fi
}

stat_busy() {
	printf "${C_OTHER}${PREFIX_REG} ${C_MAIN}${1}${C_CLEAR} "
	printf "${SAVE_POSITION}"
	deltext
	printf "   ${C_OTHER}[${C_BUSY}BUSY${C_OTHER}]${C_CLEAR} "
	
	splash_comm_send set message "${1}"
	splash_comm_send paint
}

# EOF #
