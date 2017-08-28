#!/usr/bin/env bash
if [ x$BASH = x ] || [ ! $BASH_VERSINFO ] || [ $BASH_VERSINFO -lt 4 ]; then
  echo "Error: Must use bash version 4+." >&2
  exit 1
fi
set -ue

WWW_ROOT_DEFAULT=/var/www
Usage="Usage: \$ $(basename $0) [/path/to/www/root]
Restart Nginx, uWSGI, and watch_nginx.py.
All processes are nohup'd and in the background, so no need to do that to this script.
Uses sudo to execute privileged commands.
Default www_root: $WWW_ROOT_DEFAULT"

function main {
  if [[ $# -ge 1 ]]; then
    if [[ $1 == '-h' ]] || [[ $1 == '--help' ]]; then
      fail "$Usage"
    fi
    www_root="$1"
  else
    www_root="$WWW_ROOT_DEFAULT"
  fi

  sanity_check "$www_root"

  print_commit "$www_root"

  restart "$www_root"
}


function sanity_check {
  www_root="$1"
  # Check everything is as expected, before doing anything.
  okay_to_go=true
  # Check for required commands.
  for cmd in nohup uwsgi run-one-constantly; do
    if ! which $cmd >/dev/null 2>/dev/null; then
      echo "Error: Missing command \"$cmd\"." >&2
      okay_to_go=
    fi
  done
  # Check for required files/directories.
  for dir in /etc/uwsgi/vassals "$www_root/logs"; do
    if ! [[ -d "$dir" ]]; then
      echo "Error: Missing directory \"$dir\"." >&2
      okay_to_go=
    fi
  done
  for file in "$www_root/nstoler.com/.venv/bin/python" "$www_root/logs/versions.tsv" \
              "$www_root/nstoler.com/traffic/watch_nginx.py"; do
    if ! [[ -f "$file" ]]; then
      echo "Error: Missing file \"$file\"." >&2
      okay_to_go=
    fi
  done
  #TODO: Check that all submodules are updated as well!
  if ! [[ $okay_to_go ]]; then
    exit 1
  fi
}


function print_commit {
  www_root="$1"
  last_recorded=$(cut -f 2 "$www_root/logs/versions.tsv" | tail -n 1)
  current=$(git --work-tree="$www_root/nstoler.com" --git-dir="$www_root/nstoler.com/.git" \
            log -n 1 --pretty=format:%h)
  if [[ $current == $last_recorded ]]; then
    echo "Git commit unchanged from $last_recorded."
  else
    echo "Git commit changed from $last_recorded to $current."
    now=$(date +%s)
    echo -e "$now\t$current" >> "$www_root/logs/versions.tsv"
  fi
}


function restart {
  www_root="$1"
  cd "$www_root/logs"
  printf "Restarting Nginx..\n"
  sudo service nginx restart
  # Shut everything down.
  printf "Shutting processes down..\n"
  set +e
  sudo pkill -9 -f "$www_root/nstoler.com/traffic/watch_nginx.py"
  sudo pkill -9 uwsgi
  set -e
  # Start everything back up.
  printf "Starting processes back up..\n"
  sudo -u www nohup uwsgi --emperor /etc/uwsgi/vassals --uid www --gid www \
    > "$www_root/logs/uwsgi.stdout.log" \
    2> "$www_root/logs/uwsgi.stderr.log" &
  sudo -u www nohup run-one-constantly \
    "$www_root/nstoler.com/.venv/bin/python" \
    "$www_root/nstoler.com/traffic/watch_nginx.py" -v html,css,js \
    -l "$www_root/logs/watch_nginx.log" \
    "$www_root/logs/traffic2.log" \
    > "$www_root/logs/watch_nginx.stdout.log" \
    2> "$www_root/logs/watch_nginx.stderr.log" &
}


function fail {
  echo "$@" >&2
  exit 1
}


main "$@"
