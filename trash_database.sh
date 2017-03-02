#!/usr/bin/env bash
if [ x$BASH = x ] || [ ! $BASH_VERSINFO ] || [ $BASH_VERSINFO -lt 4 ]; then
  echo "Error: Must use bash version 4+." >&2
  exit 1
fi
set -ue

Usage="Usage: \$ $(basename $0)"

APPS="traffic myadmin notepad"

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

  for app in $APPS; do
    echo "Deleting migrations for $app.."
    for migration in $app/migrations/[0-9][0-9][0-9][0-9]_*.py; do
      if [[ -f $migration ]]; then
        echo "Deleting $migration.."
        trash $app/migrations/[0-9][0-9][0-9][0-9]_*.py
      fi
    done
  done

  for app in $APPS; do
    echo "Making migration for $app.."
    python3 manage.py makemigrations $app
  done

  echo "Migrating database.."
  python3 manage.py migrate
}

function fail {
  echo "$@" >&2
  exit 1
}

main "$@"
