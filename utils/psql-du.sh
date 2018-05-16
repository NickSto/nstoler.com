#!/usr/bin/env bash
if [ "x$BASH" = x ] || [ ! "$BASH_VERSINFO" ] || [ "$BASH_VERSINFO" -lt 4 ]; then
  echo "Error: Must use bash version 4+." >&2
  exit 1
fi
set -ue

Usage="Usage: \$ $(basename "$0") [-t] [-a]
Print the disk usage of each Postgres table.
-a: Include metadata tables (ones starting with \"django_\" and \"auth_\"). 
-t: Print as tab-delimited format, with 3 columns: timestamp, table name, and size in bytes."

function main {

  # Get arguments.
  all=
  human="true"
  while getopts ":ath" opt; do
    case "$opt" in
      a) all="true";;
      t) human="";;
      h) fail "$Usage";;
    esac
  done
  pos1="${@:$OPTIND:1}"
  pos2="${@:$OPTIND+1:1}"

  now=$(date +%s)

  if [[ "$human" ]]; then
    format='pg_size_pretty('
    format_end=')'
  else
    format=
    format_end=
  fi

  echo "
    SELECT relname AS \"relation\", ${format}pg_total_relation_size(C.oid)$format_end AS \"size\"
    FROM pg_class C
    LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
    WHERE nspname NOT IN ('pg_catalog', 'information_schema')
      AND C.relkind <> 'i'
      AND nspname !~ '^pg_toast'
    ORDER BY pg_total_relation_size(C.oid) DESC;" \
    | psql -qtA -F $'\t' -d django \
    | awk -F _ '"'"$all"'" || ($1 != "django" && $1 != "auth")' \
    | awk '{if (!"'"$human"'") {printf("%d\t", '"$now"')} print $0}'
}

function fail {
  echo "$@" >&2
  exit 1
}

main "$@"
