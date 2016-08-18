#!/bin/bash
MAXAGE="$1"
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
        *s) echo $((${age_in:0:$len - 1} * $min));;
        *) echo $age_in ;;
    esac
    return 0
}

MAXAGE_SECONDS=$(convert_input_age "$MAXAGE")
echo $?
echo $MAXAGE_SECONDS
exit 0
