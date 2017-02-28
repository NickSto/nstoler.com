#!/usr/bin/env bash
if [ x$BASH = x ] || [ ! $BASH_VERSINFO ] || [ $BASH_VERSINFO -lt 4 ]; then
  echo "Error: Must use bash version 4+." >&2
  exit 1
fi
set -ue

Usage="Usage: \$ $(basename $0)"

function main {
  if [[ $# -ge 1 ]] && [[ $1 == '-h' ]]; then
    fail "$Usage"
  fi

  if ! [[ -f db.sqlite3 ]]; then
    fail "Error: db.sqlite3 not present."
  fi

  if [[ -f db.sqlite3.bak ]]; then
    trash db.sqlite3.bak
  fi
  mv db.sqlite3 db.sqlite3.bak

  trash traffic/migrations/[0-9][0-9][0-9][0-9]_*.py
  trash notepad/migrations/[0-9][0-9][0-9][0-9]_*.py

  python3 manage.py makemigrations traffic
  python3 manage.py makemigrations notepad
  python3 manage.py migrate
}

function fail {
  echo "$@" >&2
  exit 1
}

main "$@"
