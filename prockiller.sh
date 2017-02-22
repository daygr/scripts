#!/bin/bash
# === Authors
# Greg Day <gday@wayfair.com>
#
# === Description
# This script is designed to be able to find processes of a supplied name that
# are older than a supplied age, in seconds. It is a bash script so portability
# is not guaranteed. It is designed to be called by Zabbix and will only return
# a maximum of one integer with the -c option. -o and -k do not return anything
# Requires: pgrep, awk, ps
#
# === Usage
HELPMSG=$(cat <<ENDHELP
Usage: prockiller.sh [-a=AGE] -p=PROCESS_STRING [-c] [-o|-k]

If no AGE is supplied, it is assumed to be 0

Arguments:
    Arguments can be passed in any order.
    Arguments that take a parameter can be passed that parameter with = or ' '
            i.e. -a=20d or -a 20d

-c|--count       Return the total number of --process older than supplied --age
                     This count happens before killing any processes
-o|--killoldest  Kill the oldest matching --process
-k|--killall     Kill all --process older than supplied --age
-h|--help        Print this help message
ENDHELP
)
#

# Restrict PATH
PATH=/bin:/usr/bin:/usr/sbin

if [ $# -eq 0 ]; then
    echo "$HELPMSG"
    exit 0
fi

# Get arguments
for i in "$@";
do
    i="$1";
    shift;
    case "$i" in
        "--" ) break 2;;
        "-p="*|"--process="*)
            PROCESS="${i#*=}"
            ;;
        -p|--process)
            PROCESS="$1"
            shift
            ;;
        "-a="*|"--age="*)
            MAXAGE="${i#*=}"
            ;;
        -a|--age)
            MAXAGE="$1"
            shift
            ;;
        -c|--count)
            COUNT=true
            ;;
        -o|--killoldest)
            KILLOLDEST=true
            ;;
        -k|--killall)
            KILLALL=true
            ;;
        -h|--help)
            HELP=true
            ;;
        *)
            #unknown option
            shift
            ;;
    esac
done

if [ "$HELP" ]; then
    echo "$HELPMSG"
    exit 0
fi
if [ -z "$PROCESS" ]; then
    echo "--process is required"
    exit 1
fi

# If no age supplied, set age to 0, catching all processes
if [ -z "$MAXAGE" ]; then
    MAXAGE=0
fi

# Sanitize age input and convert to seconds (allows y for year, d for day, h for hour, m for minute, or s for second)
function convert_input_age() {
    local year="31557600"
    local day="86400"
    local hour="3600"
    local min="60"
    local second="1"
    local age_in="$1"
    local len=${#age_in}
    case "$age_in" in
        *y) echo $((${age_in:0:$len - 1} * $year)) ;;
        *d) echo $((${age_in:0:$len - 1} * $day)) ;;
        *h) echo $((${age_in:0:$len - 1} * $hour)) ;;
        *m) echo $((${age_in:0:$len - 1} * $min));;
        *s) echo $((${age_in:0:$len - 1} * $second));;
        *) echo $age_in ;;
    esac
}

MAXAGE_SECONDS="$(convert_input_age "$MAXAGE")"

# Some awk magic to convert the etime format from ps into seconds
function etime_to_seconds {
    seconds=$(echo "$1" | awk '{ gsub(" |-",":",$0); print }' | awk -F: '{ time=0; m=1  } { for (i=0; i < NF; i++) { seconds += $(NF-i)*m; m *= i >= 2 ? 24 : 60 } } { print seconds }')
    echo "$seconds"
}

main() {
    if [[ "$COUNT" ]] || [[ "$KILLALL" ]]; then
        local proclist=("$(pgrep -f "$PROCESS")")
        local procs=0
        for j in $proclist; do
            local age=$(etime_to_seconds "$(ps -o 'etime=' -p "$j")")
            if [[ "$age" -gt  "$MAXAGE_SECONDS" ]]; then
                let "procs++"
                if [[ "$KILLALL" ]]; then
                    kill -9 "$j"
                fi
            fi
        done
        if [[ "$COUNT" ]]; then
            echo "$procs"
        fi
    fi

    if [[ "$KILLOLDEST" ]]; then
        local pid_to_kill="$(pgrep -o -f "$PROCESS")"
        if [ "$(etime_to_seconds "$(ps -o 'etime=' -p "$pid_to_kill")")" -gt "$MAXAGE_SECONDS" ]; then
            kill -9 "$pid_to_kill"
        fi
    fi
}

main
exit $?
