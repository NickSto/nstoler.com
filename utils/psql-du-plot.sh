#!/usr/bin/env bash
if [ "x$BASH" = x ] || [ ! "$BASH_VERSINFO" ] || [ "$BASH_VERSINFO" -lt 4 ]; then
  echo "Error: Must use bash version 4+." >&2
  exit 1
fi
set -ue

DefaultOutfile=/var/www/nstoler.com/static/img/du-postgres.png
Usage="Usage: \$ $(basename "$0") [options] du-postgres.tsv [outfile.png]
Plot the growth in disk usage over time of the (current) largest postgres table."

function main {

  # Get arguments.
  flag=
  num=0
  while getopts ":fn:h" opt; do
    case "$opt" in
      f) flag="true";;
      n) num="$OPTARG";;
      h) fail "$Usage";;
    esac
  done
  log="${@:$OPTIND:1}"
  outfile="${@:$OPTIND+1:1}"

  if ! [[ "$log" ]]; then
    fail "$Usage"
  fi
  if [[ "$outfile" ]]; then
    out_args="-o $outfile"
  else
    out_args=
  fi

  max_table=$(awk -F '\t' '{if ($3 > max) {max=$3; max_table=$2}} END {print max_table}' "$log")

  awk -F '\t' '$2 == "'"$max_table"'" {print $1, $3/1024/1024}' "$log" \
    | ~/bin/scatterplot.py -u x -U days -T "Disk Usage: $max_table" -Y MB $out_args
}

function fail {
  echo "$@" >&2
  exit 1
}

main "$@"
