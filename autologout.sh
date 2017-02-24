#!/bin/bash
# autologout.sh
# @author Greg Day <gday@cryptic.li>
#
# === Description
# This script will logout sessions that are idle for more than MAXTIME minutes.
# This is primarily needed for sessions open in vcenter virtual consoles.
# It was written for CentOS 7 in bash, and will likely not work as intended
# in other environments.
#

# Restrict PATH
PATH=/bin:/usr/bin:/usr/sbin

# Trap errors and report to syslog, then exit
trap "{ err Internal command error; exit 1 }" ERR

# Set maximum time in minutes
readonly MAXTIME=15 # 15 minutes matches SSHD session timeouts

# Set up logging to syslog, also echo to stdout / stderr
readonly SCRIPT_NAME=$(basename $0)
log() {
  echo "$@"
  logger -p user.info -t $SCRIPT_NAME "$@"
}
warn() {
  echo "$@"
  logger -p user.warn -t $SCRIPT_NAME "$@"
}
err() {
  echo "$@" >&2
  logger -p user.error -t $SCRIPT_NAME "$@"
}

# Helper function that returns the list of process IDs of login sessions
# with idle time over 15 minutes
# The first awk varies with the date format `who` uses
get_idle_pids() {
    local pid_list=$(
        who -u                | # -u flag prints idle time
        awk '{print $5" "$6}' | # on CentOS, gets idle time and pid
        sed 's/old/99:99/'    | # replace 'old' with arbitrary 99:99 for >24hr
        sed 's/\./00:00/'     | # replace '.' with arbitrary 00:00 for <1 min
        sed 's/ /:/'          | # replace spaces with ':' for next awk line
        awk -v MAXTIME="$MAXTIME" -F: '$1>0 || $2>MAXTIME {print $3}'
        # check if hours > 0 or minutes > MAXTIME and then print pid if true
    )
    printf "$pid_list"
}

# Helper function that attempts to send SIGHUP to processes
safe_kill_pids() {
    local exit_code=0
    local pid_list=$@
    for pid in $pid_list; do
        warn "Sending SIGHUP to login shell with pid $pid"
        timeout 10 kill -HUP $pid
        if [[ "$?" -ne "0" ]]; then
            let "exit_code+=1"
            err "Login shell with pid $pid did not respond to SIGHUP"
        else
            warn "Login shell with pid $pid killed with SIGHUP"
        fi
    done
    return "$exit_code"
}

main() {
    log "Beginning autologout script"
    safe_kill_pids $(get_idle_pids)
    local pids_failed=$?
    if [[ "$pids_failed" -ne "0" ]]; then
        err "Autologout script failed to kill $pids_failed pids"
        return 1
    else
        log "Autologout script completed"
        return 0
    fi
}

main
exit $?
