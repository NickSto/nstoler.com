#!/usr/bin/env python3
import argparse
import logging
import os
import pathlib
import subprocess
import sys
import time
assert sys.version_info.major >= 3, 'Python 3 required'

DESCRIPTION = """Plot the spam log."""

PLOT_EXE = pathlib.Path('~/bin/scatterplot.py').expanduser()
PLOT_CMD = [
  PLOT_EXE, '--tag-field', '3', '--unix-time', 'x', '--date', '--y-range', '0', '1',
  '--y-label', '', '--width', '640', '--height', '200', '--feature-scale', '2.25', '--out-file',
]


def make_argparser():
  parser = argparse.ArgumentParser(add_help=False, description=DESCRIPTION)
  options = parser.add_argument_group('Options')
  options.add_argument('log', metavar='spam.tsv', type=pathlib.Path,
    help='Spam log export file.')
  options.add_argument('plot', metavar='spam.png', type=pathlib.Path,
    help='Where to write the plot to.')
  options.add_argument('-m', '--include-me', action='store_true')
  options.add_argument('-w', '--watch', action='store_true',
    help='Sit and watch the log file, re-rendering the plot when it changes.')
  options.add_argument('-h', '--help', action='help',
    help='Print this argument help text and exit.')
  logs = parser.add_argument_group('Logging')
  logs.add_argument('-l', '--log', type=argparse.FileType('w'), default=sys.stderr,
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  volume = logs.add_mutually_exclusive_group()
  volume.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL,
    default=logging.WARNING)
  volume.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
  volume.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)
  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')

  while True:
    plot_spam_log(args.log, args.plot, include_me=args.include_me)
    if not args.watch:
      break
    wait_on_file(args.log)


def wait_on_file(path):
  """Wait until the file changes.
  Based on the date modified. If the file doesn't exist, or ceases to exist while this is waiting,
  it will wait until it exists, then resume checking the date modified."""
  modified = original_modified = get_mtime_or_wait(path)
  while modified == original_modified:
    time.sleep(1)
    modified = get_mtime_or_wait(path)


def get_mtime_or_wait(path):
  while not path.exists():
    time.sleep(1)
  return os.path.getmtime(path)


def plot_spam_log(log_path, out_path, include_me=False):
  cmd = PLOT_CMD + [out_path]
  logging.info('+ $ '+' '.join([str(arg) for arg in cmd]), file=sys.stderr)
  process = subprocess.Popen(cmd, stdin=subprocess.PIPE, encoding='utf8')
  lines = 0
  for line in transform_log(log_path, include_me=include_me):
    process.stdin.write(line)
    lines += 1
  process.stdin.close()


def transform_log(log_path, include_me=False):
  for time_str, is_me_str, is_boring_str in read_log(log_path):
    if is_me_str == 'True' and not include_me:
      continue
    if is_boring_str == 'True':
      label = 'Basic'
      y = 0.4
    else:
      label = 'Unusual'
      y = 0.6
    yield f'{time_str}\t{y}\t{label}\n'


def read_log(log_path):
  with log_path.open() as log_file:
    for line_num, line_raw in enumerate(log_file):
      fields = line_raw.split('\t')
      if len(fields) < 3:
        fail(f'Line {line_num+1} has too few fields ({line_raw!r}).')
      yield fields[0], fields[1], fields[2]


def fail(message):
  logging.critical('Error: '+str(message))
  if __name__ == '__main__':
    sys.exit(1)
  else:
    raise Exception(message)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except BrokenPipeError:
    pass
