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

  #TODO: Print the git commit to an "updates" log file (when it changes).
  cd "$www_root/logs"
  printf "Restarting Nginx..\n"
  sudo service nginx restart
  # Shut everything down.
  printf "Shutting processes down..\n"
  set +e
  sudo pkill -9 -f "$www_root/nstoler.com/django/traffic/watch_nginx.py"
  sudo pkill -9 uwsgi
  set -e
  # Start everything back up.
  printf "Starting processes back up..\n"
  sudo -u www nohup uwsgi --emperor /etc/uwsgi/vassals --uid www --gid www \
    > "$www_root/logs/uwsgi.stdout.log" \
    2> "$www_root/logs/uwsgi.stderr.log" &
  sudo -u www nohup run-one-constantly \
    "$www_root/nstoler.com/django/.venv/bin/python" \
    "$www_root/nstoler.com/django/traffic/watch_nginx.py" -v html,css,js \
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
