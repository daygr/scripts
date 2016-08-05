#!/bin/bash
# === Authors
# Greg Day <gday@cryptic.li>
#
# === Description
# This script is designed to be able to find processes of a supplied name that
# are older than a supplied age, in seconds. It is a bash script so portability
# is not guaranteed. It is designed to be called by Zabbix and will only return
# a maximum of one integer with the -c option. -o and -k do not return anything
# Requires: pgrep, awk, ps
#
# === Usage
USAGE="Usage: prockiller.sh -a=AGE -p=PROCESS_STRING {-c|-o|-k}"
#
# === Changelog
# 05/30/2016 - added document header and abstracted to_seconds function

PATH=/bin:/usr/bin:/usr/sbin

if [ $# -eq 0 ]; then
    echo "$USAGE"
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
        *)
            #unknown option
            shift
            ;;
    esac
done

if [ -z "$PROCESS" ]; then
    echo "Must supply a --process"
    exit 1
fi
if [ -z "$MAXAGE" ]; then
    echo "Must supply an --age"
    exit 1
fi

# Some awk magic to convert the etime format from ps into seconds
function to_seconds {
    seconds=$(echo "$1" | awk '{ gsub(" |-",":",$0); print }' | awk -F: '{ time=0; m=1  } { for (i=0; i < NF; i++) { seconds += $(NF-i)*m; m *= i >= 2 ? 24 : 60 } } { print seconds }')
    echo "$seconds"
}

if [ "$COUNT" ]; then
    procs=0
    for j in $(pgrep -f "$PROCESS"); do
        age=$(to_seconds "$(ps -o 'etime=' -p "$j")")
        if [ "$age" -gt  "$MAXAGE" ]; then
            let "procs++"
        fi
    done
    echo "$procs"
    exit 0
fi

if [ "$KILLOLDEST" ]; then
    pid_to_kill="$(pgrep -o -f "$PROCESS")"
    if [ "$(to_seconds "$(ps -o 'etime=' -p "$pid_to_kill")")" -gt "$MAXAGE" ]; then
        kill "$pid_to_kill"
    fi
    exit 0
fi

if [ "$KILLALL" ]; then
    for j in "$(pgrep -f "$PROCESS")"; do
        if [ "$(to_seconds "$(ps -o 'etime=' -p "$j")")" -gt "$MAXAGE" ]; then
            kill "$j"
        fi
    done
    exit 0
fi
