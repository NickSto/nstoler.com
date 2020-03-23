#!/usr/bin/env bash
if [ "x$BASH" = x ] || [ ! "$BASH_VERSINFO" ] || [ "$BASH_VERSINFO" -lt 4 ]; then
  echo "Error: Must use bash version 4+." >&2
  exit 1
fi
set -ue
unset CDPATH

Usage="Usage: \$ $(basename "$0") submodule
Automatically do the module.lnk/module.dir swap, commit new changes, and undo the swap.
Just give the name of the submodule's directory.
You can run this when the 'module' directory is module.lnk or module.dir, and
it will do the right thing."

function main {

  if [[ "$#" -lt 1 ]] || ( [[ "$1" == '-h' ]] || [[ "$1" == '--help' ]] ); then
    fail "$Usage"
  fi

  module="$1"

  if ! ([[ -e "$module" ]] || [[ -e "$module.lnk" ]] || [[ -e "$module.dir" ]]); then
    fail "Error: unrecognized submodule '$module'."
  fi

  trap cleanup ERR

  if [[ -h "$module" ]] && ! [[ -e "$module.lnk" ]] && [[ -d "$module.dir" ]]; then
    # The $module dir is currently the link. Swap it with the directory.
    echo "Switching $module/ to the directory.."
    mv "$module" "$module.lnk"
    mv "$module.dir" "$module"
  fi

  if ! [[ -d "$module" ]] || [[ -e "$module.dir" ]] || [[ -h "$module" ]] || ! [[ -h "$module.lnk" ]]; then
    # At this point, $module should be the directory, not the link. If not, something went wrong.
    fail "Error in setup of $module/$module.lnk directories."
  fi

  # Update the submodule.
  cd "$module"
  git pull origin master
  cd ..

  # Make the commit to the parent repo.
  git add -p "$module"
  git commit

  # Swap the link and directory back.
  echo "Switching $module/ back to the link.."
  mv "$module" "$module.dir"
  mv "$module.lnk" "$module"

  echo "Remember to git push origin master!"
}

function cleanup {
  # Undo any changes made by the script, in case it failed in the middle.
  if [[ -d "$module" ]] && ! [[ -e "$module.dir" ]]; then
    mv "$module" "$module.dir"
  fi
  if [[ -h "$module.lnk" ]] && ! [[ -e "$module" ]]; then
    mv "$module.lnk" "$module"
  fi
}

function fail {
  echo "$@" >&2
  exit 1
}

main "$@"
