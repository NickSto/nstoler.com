#!/usr/bin/env python3
import argparse
import logging
import os
import pathlib
import sys
import http.client
import urllib.error
try:
    import yaml
except ImportError:
    yaml = None

import urllib.parse
import urllib.request
from typing import Union, Optional, NoReturn

COOKIE_NAME = 'visitors_v1'
DATA_DIR = pathlib.Path('~/.local/share/nbsdata').expanduser()
SILENCE_PATH = DATA_DIR / 'SILENCE'
DESCRIPTION = """Download all the Notepad pages as plain text files and store them in a directory.
"""


def make_argparser():
    parser = argparse.ArgumentParser(add_help=False, description=DESCRIPTION)
    options = parser.add_argument_group('Options')
    options.add_argument('out_dir', type=pathlib.Path,
        help='The directory to store the downloaded files in. Must already exist.')
    options.add_argument('-c', '--cookie',
        help=f'A cookie to use for authentication. This should be a {COOKIE_NAME} cookie, unless '
            "you're giving a different cookie name in --cookie-name.")
    options.add_argument('-C', '--cookie-file', type=pathlib.Path,
        help='A YAML file containing cookies. The file should have a section named after the host '
            '(e.g. "nstoler.com") with a "cookies" mapping inside it.')
    options.add_argument('--cookie-name', default=COOKIE_NAME,
        help=f'The name of the cookie to use for authentication. Default: {COOKIE_NAME}')
    options.add_argument('-u', '--url', default='https://nstoler.com',
        help='The base url of the site. Default: %(default)s')
    options.add_argument('--ignore-silence', action='store_true',
        help='Ignore the presence of the SILENCE file and make a connection anyway.')
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


def main(*argv: str) -> Optional[int]:

    parser = make_argparser()
    args = parser.parse_args(argv[1:])

    logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')

    if not args.ignore_silence and SILENCE_PATH.exists():
        logging.info(f'SILENCE file exists at {SILENCE_PATH}. Exiting without making connections.')
        return None

    if not args.out_dir.is_dir():
        fail(f'{args.out_dir} is not an existing directory.')

    base_url = args.url.rstrip('/')
    cookies = {}
    if args.cookie_file:
        file_cookies = read_cookie_file(args.cookie_file, base_url)
        if file_cookies is not None:
            cookies.update(file_cookies)
    if args.cookie:
        cookies[args.cookie_name] = args.cookie

    page_names = get_page_list(base_url, cookies)
    logging.info(f'Found {len(page_names)} pages.')

    live_local, deleted_local = get_local_pages(args.out_dir)

    successfully_downloaded = set()
    for page_name in page_names:
        if not validate_page_name(page_name):
            continue
        content = get_page_content(base_url, page_name, cookies)
        if content is None:
            continue
        successfully_downloaded.add(page_name)
        path = page_path(args.out_dir, page_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        logging.info(f'Downloaded {page_name}')
        deleted_version = deleted_path_for(path)
        if deleted_version.exists():
            deleted_version.unlink()
            logging.info(f'Removed deleted marker for {page_name}')

    to_delete = live_local - successfully_downloaded
    for page_name in to_delete:
        path = page_path(args.out_dir, page_name)
        deleted_version = deleted_path_for(path)
        path.rename(deleted_version)
        logging.info(f'Marked {page_name} as deleted.')

    return None


def read_cookie_file(cookie_file: pathlib.Path, base_url: str) -> Optional[dict[str,str]]:
    if yaml is None:
        fail('PyYAML is required to use --cookie-file. Install it with: pip install pyyaml')
    hostname = urllib.parse.urlparse(base_url).hostname
    try:
        with open(cookie_file) as f:
            data = yaml.safe_load(f)
    except OSError as error:
        fail(f'Could not read cookie file: {error}')
    except yaml.YAMLError as error:
        fail(f'Could not parse cookie file: {error}')
    if not isinstance(data, dict):
        logging.error(
            f'Expected top-level mapping in cookie file {cookie_file}, got {type(data).__name__}'
        )
        return None
    host_section = data.get(hostname)
    if host_section is None:
        logging.error(f'No section for host {hostname!r} in cookie file {cookie_file}')
        return None
    if not isinstance(host_section, dict):
        logging.error(
            f'Expected a mapping for host {hostname!r} in cookie file {cookie_file}, '
            f'got {type(host_section).__name__}'
        )
        return None
    cookies = host_section.get('cookies')
    if cookies is None:
        logging.error(f'No "cookies" section for host {hostname!r} in cookie file {cookie_file}')
        return None
    if not isinstance(cookies, dict):
        logging.error(f'Expected a mapping under {hostname!r} > "cookies" in {cookie_file}')
        return None
    logging.info(f'Read {len(cookies)} cookies from {cookie_file} for host {hostname!r}')
    return {str(name): str(value) for name, value in cookies.items()}


def fetch(url: str, cookies: dict[str,str]) -> str:
    request = urllib.request.Request(url)
    if cookies:
        cookie_header = '; '.join(f'{name}={value}' for name, value in cookies.items())
        request.add_header('Cookie', cookie_header)
    logging.debug(f'Fetching {url}')
    try:
        with urllib.request.urlopen(request) as response:
            return response.read().decode()
    except http.client.IncompleteRead:
        logging.info(f'Incomplete read, retrying {url}')
        with urllib.request.urlopen(request) as response:
            return response.read().decode()
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'{error.code} {error.reason} from {url}') from error


def get_page_list(base_url: str, cookies: dict[str,str]) -> list[str]:
    url = f'{base_url}/notepad/monitor?format=plain'
    try:
        text = fetch(url, cookies)
    except Exception as error:
        fail(error)
    return [line for line in text.splitlines() if line.strip()]


def get_page_content(base_url: str, page_name: str, cookies: dict[str,str]) -> Optional[str]:
    quoted_name = urllib.parse.quote(page_name, safe='/')
    url = f'{base_url}/{quoted_name}?format=plain'
    try:
        return fetch(url, cookies)
    except Exception as error:
        logging.warning(f'Failed to fetch page {page_name!r}: {error}')
        return None


def get_local_pages(out_dir: pathlib.Path) -> tuple[set[str], set[str]]:
    live = set()
    deleted = set()
    for dirpath_str, dirnames, filenames in os.walk(out_dir):
        dirpath = pathlib.Path(dirpath_str)
        for filename in filenames:
            filepath = dirpath / filename
            rel = filepath.relative_to(out_dir)
            rel_str = str(rel)
            if rel_str.endswith('.deleted.txt'):
                page_name = rel_str[:-len('.deleted.txt')]
                deleted.add(page_name)
            elif rel_str.endswith('.txt'):
                page_name = rel_str[:-len('.txt')]
                live.add(page_name)
            elif not rel_str.endswith('.bak'):
                logging.warning(f'Unexpected file in output directory: {filepath}')
    return live, deleted


def validate_page_name(page_name: str) -> bool:
    if not page_name:
        logging.warning('Empty page name, skipping.')
        return False
    if page_name.startswith('/'):
        logging.warning(f'Page name starts with /, skipping: {page_name!r}')
        return False
    for component in page_name.split('/'):
        if component == '..':
            logging.warning(f'Page name contains .., skipping: {page_name!r}')
            return False
    return True


def page_path(out_dir: pathlib.Path, page_name: str) -> pathlib.Path:
    return out_dir / (page_name + '.txt')


def deleted_path_for(txt_path: pathlib.Path) -> pathlib.Path:
    return txt_path.with_suffix('.deleted.txt')


def fail(error: Union[str,BaseException], code: int = 1) -> NoReturn:
    if __name__ == '__main__':
        logging.critical(f'Error: {error}')
        sys.exit(code)
    elif isinstance(error, BaseException):
        raise error
    else:
        raise RuntimeError(error)


if __name__ == '__main__':
    try:
        sys.exit(main(*sys.argv))
    except BrokenPipeError:
        pass
