#!/usr/bin/env python3
# MIT License
# 
# Copyright 2026 Broad Institute
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import argparse
import re
from pathlib import Path
from typing import List, Optional, Tuple

from util import gcs_util as gcs_util


class LaunchSnRnaError(Exception):
    """A user-facing problem with the launch arguments, manifest, or cloud metadata."""


class HiddenArguments:
    """Options hidden from --help, and a --help-full option that shows them.

    An option is hidden by passing help=argparse.SUPPRESS
    (https://docs.python.org/3/library/argparse.html#help); its real help is kept here."""

    def __init__(self) -> None:
        self._hidden: List[Tuple[argparse.Action, str]] = []

    def add_argument(self, container, *flags: str, help: str, **kwargs) -> argparse.Action:
        """Like container.add_argument(), but hidden from --help.  container is a parser or argument group."""
        action = container.add_argument(*flags, help=argparse.SUPPRESS, **kwargs)
        self._hidden.append((action, help))
        return action

    def add_help_full_argument(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--help-full", action=_ShowFullHelpAction, hidden=self._hidden,
                            help="show this help message, including hidden options, and exit")


class _ShowFullHelpAction(argparse.Action):
    """Like the built-in --help, but first restores the help of options hidden with help=argparse.SUPPRESS."""

    def __init__(self, option_strings: List[str], hidden: List[Tuple[argparse.Action, str]],
                 dest: str = argparse.SUPPRESS, default: str = argparse.SUPPRESS, help: Optional[str] = None) -> None:
        super().__init__(option_strings=option_strings, dest=dest, default=default, nargs=0, help=help)
        self.hidden = hidden

    def __call__(self, parser, namespace, values, option_string=None) -> None:
        for action, help_text in self.hidden:
            action.help = help_text
        parser.print_help()
        parser.exit()


# passed to the argparse `type` argument to validate that an argument is valid
def gcs_path_type(value: str) -> str:
    if not gcs_util.GCS_PATH_RE.match(value):
        raise argparse.ArgumentTypeError(f"not a gs:// path: '{value}'")
    return value


def email_type(value: str) -> str:
    if not EMAIL_RE.match(value):
        raise argparse.ArgumentTypeError(f"not a valid email address: '{value}'")
    return value


def manifest_path_type(value: str) -> Path:
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"manifest file not found: '{path}'")
    return path


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
