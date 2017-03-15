#!/usr/bin/env bash
if [ x$BASH = x ] || [ ! $BASH_VERSINFO ] || [ $BASH_VERSINFO -lt 4 ]; then
  echo "Error: Must use bash version 4+." >&2
  exit 1
fi
set -ue

VENV_NAME='.venv'

Usage="Usage: \$ $(basename $0) logfile.log [watch_nginx.py [watch_nginx.log]]"

function main {
  if [[ $# -lt 1 ]] || [[ $1 == '-h' ]]; then
    fail "$Usage"
  fi

  logfile="$1"
  if [[ $# -ge 2 ]]; then
    watch_nginx="$2"
  else
    script_dir=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
    watch_nginx="$script_dir/watch_nginx.py"
  fi

  watch_nginx_log_args=
  if [[ $# -ge 3 ]]; then
    watch_nginx_log_args="-l $3"
  fi

  # Locate and activate virtualenv necessary for watch_nginx.py.
  venv_activate="$(dirname $(dirname "$watch_nginx"))/$VENV_NAME/bin/activate"
  if ! [[ -f "$venv_activate" ]]; then
    fail "Error: virtualenv script not present at $venv_activate."
  fi
  export PS1='dummy$ '  # Having no $PS1 set throws an error in activate b/c of set -u.
  source "$venv_activate"

  tail -n 0 --follow=name "$logfile" | python3 "$watch_nginx" $watch_nginx_log_args

}

function fail {
  echo "$@" >&2
  exit 1
}

main "$@"
