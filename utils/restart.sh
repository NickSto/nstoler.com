#!/usr/bin/env bash
if [ x$BASH = x ] || [ ! $BASH_VERSINFO ] || [ $BASH_VERSINFO -lt 4 ]; then
  echo "Error: Must use bash version 4+." >&2
  exit 1
fi
set -ue

WWW_ROOT_DEFAULT=/var/www
Usage="Usage: \$ $(basename $0) [restart|stop|start [/path/to/www/root]]
Restart, stop, or start Nginx, Postgres, uWSGI, and watch_nginx.py.
All processes are nohup'd and in the background, so no need to do that to this script.
Uses sudo to execute privileged commands.
Default www_root: $WWW_ROOT_DEFAULT"

function main {
  action=restart
  www_root="$WWW_ROOT_DEFAULT"

  if [[ $# -ge 1 ]]; then
    if [[ $1 == '-h' ]] || [[ $1 == '--help' ]]; then
      fail "$Usage"
    fi
    action="$1"
    if [[ $# -ge 2 ]]; then
      www_root="$2"
    fi
  fi

  if [[ $action != restart ]] && [[ $action != stop ]] && [[ $action != start ]]; then
    fail "Error: Unrecognized action \"$action\"."
  fi

  if ! sanity_check "$www_root"; then
    exit 1
  fi

  if [[ $action == stop ]] || [[ $action == restart ]]; then
    stop "$www_root"
  fi

  if [[ $action == start ]] || [[ $action == restart ]]; then
    if log_commit "$www_root"; then
      upgrade=true
    else
      upgrade=
    fi

    if [[ $upgrade ]]; then
      upgrade "$www_root"
    fi

    start "$www_root"
  fi
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
  for file in "$www_root/logs/versions.tsv" \
              "$www_root/nstoler.com/.venv/bin/python" \
              "$www_root/nstoler.com/traffic/watch_nginx.py"; do
    if ! [[ -f "$file" ]]; then
      echo "Error: Missing file \"$file\"." >&2
      okay_to_go=
    fi
  done
  #TODO: Check that all submodules are updated as well!
  if [[ $okay_to_go ]]; then
    return 0
  else
    return 1
  fi
}


function log_commit {
  www_root="$1"
  last_recorded=$(cut -f 2 "$www_root/logs/versions.tsv" | tail -n 1)
  current=$(git --work-tree="$www_root/nstoler.com" --git-dir="$www_root/nstoler.com/.git" \
            log -n 1 --pretty=format:%h)
  if [[ $current == $last_recorded ]]; then
    echo "Git commit unchanged from $last_recorded."
    return 1
  else
    echo "Git commit changed from $last_recorded to $current."
    now=$(date +%s)
    echo -e "$now\t$current" >> "$www_root/logs/versions.tsv"
    return 0
  fi
}


function upgrade {
  www_root="$1"
  manage="$www_root/nstoler.com/manage.py"
  if ! [[ -s $manage ]]; then
    echo "Warning: Could not find $manage. Abandoning upgrade.." >&2
    return 1
  fi
  activate="$www_root/nstoler.com/.venv/bin/activate"
  if [[ -s "$activate" ]]; then
    set +eu
    source $activate
    set -eu
  else
    echo "Warning: Could not find $activate. Abandoning upgrade.." >&2
    return 1
  fi
  # These files get their permissions messed up sometimes.
  sudo chmod g+w "$www_root/logs/django.log"
  sudo chmod g+w "$www_root/logs/django_sql.log"
  # Collect static files.
  python $manage collectstatic --traceback
  # Migrate database.
  printf "\n%s\n%s" "Migrate database?" "Type 'yes' to continue, or 'no' to cancel: "
  read response
  if [[ $response == yes ]]; then
    echo "Starting Postgres.."
    sudo service postgresql start
    python $manage migrate 
  fi
}


function stop {
  www_root="$1"
  set +e
  echo "Killing watch_nginx.py.."
  sudo pkill -9 -f "$www_root/nstoler.com/traffic/watch_nginx.py"
  echo "Killing uwsgi.."
  sudo pkill -9 uwsgi
  set -e
  echo "Stopping Postgres.."
  sudo service postgresql stop
  echo "Stopping Nginx.."
  sudo service nginx stop
}


function start {
  # Start everything back up.
  www_root="$1"
  # These files get their permissions messed up sometimes.
  sudo chmod g+w "$www_root/logs/django.log"
  sudo chmod g+w "$www_root/logs/django_sql.log"
  echo "Starting Nginx.."
  sudo service nginx start
  echo "Starting Postgres.."
  sudo service postgresql start
  echo "Starting uwsgi.."
  cd "$www_root/logs"
  sudo -u www nohup uwsgi --emperor /etc/uwsgi/vassals --uid www --gid www \
    > "$www_root/logs/uwsgi.stdout.log" \
    2> "$www_root/logs/uwsgi.stderr.log" &
  echo "Starting watch_nginx.py.."
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
