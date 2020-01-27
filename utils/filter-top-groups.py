#!/usr/bin/env python3
import argparse
import collections
import logging
import pathlib
import sys
assert sys.version_info.major >= 3, 'Python 3 required'

DESCRIPTION = """Filter a grouped table to the N groups with the highest values."""


def make_argparser():
  parser = argparse.ArgumentParser(add_help=False, description=DESCRIPTION)
  options = parser.add_argument_group('Options')
  options.add_argument('input', metavar='data.tsv', type=pathlib.Path,
    help='Input data. Tab-delimited.')
  options.add_argument('-n', '--limit', type=int, default=10,
    help='Output the top N groups. Default: %(default)s')
  options.add_argument('-g', '--group-col', type=int, default=1,
    help='Column containing the group label. Default: %(default)s')
  options.add_argument('-y', '--value-col', type=int, default=3,
    help='Column containing the values. Default: %(default)s')
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

  top_groups = get_top_groups(args.input, args.group_col, args.value_col, args.limit)

  for line_raw in filter_file(args.input, args.group_col, top_groups):
    print(line_raw, end='')


def get_top_groups(input_path, group_col, value_col, limit):
  # Read input and find the maximum value for each group.
  max_values = collections.defaultdict(int)
  for line_num, line_raw in enumerate(read_file(input_path)):
      group, value = parse_line(line_raw, group_col, value_col, line_num)
      max_values[group] = max(value, max_values[group])
  # Get a list of the top `limit` groups.
  top_groups = set()
  for group, value in sorted(max_values.items(), reverse=True, key=lambda item: item[1]):
    if len(top_groups) >= limit:
      break
    top_groups.add(group)
  return top_groups


def parse_line(line_raw, group_col, value_col, line_num):
  fields = line_raw.split('\t')
  if len(fields) < group_col or len(fields) < value_col:
    fail(
      f'Line {line_num+1} has fewer columns than --group-col ({group_col}) and/or --value-col '
      f'({value_col}).'
    )
  group = fields[group_col-1]
  try:
    value = int(fields[value_col-1])
  except ValueError:
    try:
      value = float(fields[value_col-1])
    except ValueError:
      fail(f'{fields[value_col-1]!r} on line {line_num+1} is not a valid number.')
  return group, value


def filter_file(input_path, group_col, top_groups):
  for line_raw in read_file(input_path):
    fields = line_raw.split('\t')
    group = fields[group_col-1]
    if group in top_groups:
      yield line_raw


def read_file(input_path):
  with input_path.open() as input_file:
    for line_raw in input_file:
      if line_raw.strip():
        yield line_raw


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
