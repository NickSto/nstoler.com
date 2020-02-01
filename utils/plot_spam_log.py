#!/usr/bin/env python3
import argparse
import collections
import datetime
import logging
import math
import os
import pathlib
import subprocess
import sys
import time
from matplotlib import pyplot
try:
  from utillib import datelib
except ModuleNotFoundError:
  script_dir = pathlib.Path(__file__).resolve().parent
  sys.path.append(str(script_dir.parent))
  from utillib import datelib
assert sys.version_info.major >= 3, 'Python 3 required'

DESCRIPTION = """Plot the spam log."""

BAR_WIDTH = 20*60*60
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
  options.add_argument('plots', metavar='plot_type spam.png', nargs='+',
    help='What type(s) of plot(s) to make and where to put them. Plot types include "timeline" and '
      '"bar".')
  options.add_argument('-m', '--include-me', action='store_true')
  options.add_argument('-w', '--watch', action='store_true',
    help='Sit and watch the log file, re-rendering the plot when it changes.')
  options.add_argument('-h', '--help', action='help',
    help='Print this argument help text and exit.')
  logs = parser.add_argument_group('Logging')
  logs.add_argument('-l', '--err-log', type=argparse.FileType('w'), default=sys.stderr,
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

  logging.basicConfig(stream=args.err_log, level=args.volume, format='%(message)s')

  plots = parse_outputs(args.plots)

  while True:
    spams = read_log(args.log)
    if not args.include_me:
      spams = [spam for spam in spams if not spam.is_me]
    for plot_type, plot_path in plots:
      if plot_type == 'timeline':
        timeline_plot(spams, plot_path)
      elif plot_type == 'bar':
        bar_plot(spams, plot_path)
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


def parse_outputs(out_args):
  if len(out_args) % 2 != 0:
    plot_args = ', '.join([repr(arg) for arg in out_args])
    fail(f'Wrong number of plot arguments. Must give a multiple of two. Saw {plot_args}')
  plots = []
  for i in range(0, len(out_args), 2):
    plot_type = out_args[i]
    plot_path = pathlib.Path(out_args[i+1])
    plots.append((plot_type, plot_path))
  return plots


########## TIMELINE PLOT ##########

def timeline_plot(spams, out_path):
  cmd = PLOT_CMD + [out_path]
  logging.info('+ $ '+' '.join([str(arg) for arg in cmd]), file=sys.stderr)
  process = subprocess.Popen(cmd, stdin=subprocess.PIPE, encoding='utf8')
  lines = 0
  for line in make_timeline_data(spams):
    process.stdin.write(line)
    lines += 1
  process.stdin.close()


def make_timeline_data(spams):
  for spam in spams:
    if spam.is_boring:
      label = 'Basic'
      y = 0.4
    else:
      label = 'Unusual'
      y = 0.6
    yield f'{spam.timestamp}\t{y}\t{label}\n'


########## BAR PLOT ##########

def bar_plot(spams, out_path):
  spam_by_day = bin_spam_by_day(spams)
  bar_data = make_bar_data(spam_by_day)
  do_bar_plotting(*bar_data)
  pyplot.savefig(out_path)


def bin_spam_by_day(spams):
  spam_by_day = collections.defaultdict(list)
  for spam in spams:
    day = timestamp_to_day(spam.timestamp)
    spam_by_day[day].append(spam)
  return spam_by_day


def make_bar_data(spam_by_day):
  basic_counts = []
  unusual_counts = []
  timestamps = []
  for day in sorted(spam_by_day.keys()):
    timestamps.append(day_to_timestamp(day))
    spams = spam_by_day[day]
    basic_count = 0
    unusual_count = 0
    for spam in spams:
      if spam.is_boring:
        basic_count += 1
      else:
        unusual_count += 1
    basic_counts.append(basic_count)
    unusual_counts.append(unusual_count)
  return timestamps, basic_counts, unusual_counts


def do_bar_plotting(timestamps, basic_counts, unusual_counts):
  figure = pyplot.figure(figsize=(8,6))
  axes = figure.add_subplot(1,1,1)
  basic_plot = axes.bar(timestamps, basic_counts, BAR_WIDTH, color='#1f77b4')
  unusual_plot = axes.bar(timestamps, unusual_counts, BAR_WIDTH, color='#ff7f0e', bottom=basic_counts)
  xticks, xlabels = get_time_ticks(timestamps[0], timestamps[-1], max_ticks=5)
  axes.set_xticks(xticks)
  axes.set_xticklabels(xlabels)
  axes.legend((unusual_plot, basic_plot), ('Unusual', 'Basic'))


def timestamp_to_day(timestamp):
  return (timestamp-18000) // (24*60*60)


def day_to_timestamp(day_num):
  return (day_num*24*60*60) + 18000


def get_time_ticks(time_min, time_max, min_ticks=5, max_ticks=15):
  time_unit, multiple = get_tick_size(time_min, time_max, min_ticks, max_ticks)
  min_dt = datetime.datetime.fromtimestamp(time_min)
  dt = datelib.floor_datetime(min_dt, time_unit)
  first_tick_dt = datelib.increment_datetime(dt, time_unit)
  first_tick_value = int(first_tick_dt.timestamp())
  tick_values = []
  tick_labels = []
  tick_dt = first_tick_dt
  tick_value = first_tick_value
  while tick_value < time_max:
    tick_values.append(tick_value)
    tick_label = tick_dt.strftime(time_unit.format_rounded.replace(' ', '\n'))
    tick_labels.append(tick_label)
    tick_dt = datelib.increase_datetime(tick_dt, time_unit, multiple)
    tick_value = int(tick_dt.timestamp())
  return tick_values, tick_labels


def get_tick_size(time_min, time_max, min_ticks, max_ticks):
  """Find a tick size for the time axis that gives between a min and max number of ticks.
  Determines what multiple of which TimeUnit and returns (time_unit, multiple)."""
  time_period = time_max - time_min
  min_multiple = sys.maxsize
  min_multiple_unit = None
  for time_unit in datelib.TIME_UNITS:
    ticks = time_period / time_unit.seconds
    if ticks < min_ticks:
      multiple = 1
    elif ticks > max_ticks:
      multiple = math.ceil(ticks/max_ticks)
    else:
      return time_unit, 1
    ticks = time_period / (time_unit.seconds*multiple)
    if min_ticks <= ticks <= max_ticks and multiple < min_multiple:
      min_multiple = multiple
      min_multiple_unit = time_unit
  return min_multiple_unit, min_multiple


########## UTILITIES ##########

def read_log(log_path):
  spams = []
  with log_path.open() as log_file:
    for line_num, line_raw in enumerate(log_file):
      fields = line_raw.rstrip('\r\n').split('\t')
      if len(fields) < 3:
        fail(f'Line {line_num+1} has too few fields ({line_raw!r}).')
      spams.append(Spam(*fields))
  return spams


def intnull(raw_value):
  if raw_value == 'None':
    return None
  else:
    return int(raw_value)


def boolish(raw_value):
  if isinstance(raw_value, bool):
    return raw_value
  elif raw_value == 'True':
    return True
  elif raw_value == 'False':
    return False
  elif raw_value == 'None':
    return None
  else:
    raise ValueError(f'Invalid boolish: {raw_value}')


class Spam:
  FIELDS = (
    {'name':'timestamp', 'type':intnull},
    {'name':'is_me', 'type':boolish},
    {'name':'is_boring', 'type':boolish},
    {'name':'captcha_version', 'type':intnull},
    {'name':'captcha_failed', 'type':boolish},
    {'name':'js_enabled', 'type':boolish},
    {'name':'solved_grid', 'type':boolish},
    {'name':'grid_autofilled', 'type':boolish},
    {'name':'honeypot_len', 'type':intnull},
    {'name':'content_len', 'type':intnull},
  )
  def __init__(self, *fields):
    for field, meta in zip(fields, self.FIELDS):
      value = meta['type'](field)
      setattr(self, meta['name'], value)


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
