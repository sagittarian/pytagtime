#!/usr/bin/env python3

import util

import os
import shlex
import subprocess

SETTINGS_FILE = '.pytagtimerc'
SETTINGS_PATH = os.path.expanduser(os.path.join('~', SETTINGS_FILE))
# use .pytagtimerc for now so as not to interfere with the old perl
# config

DEFAULTS = {
    'user': os.environ['USER'],

    # Pings from more than this many seconds ago get autologged with tags
    # "afk" and "RETRO". (Pings can be overdue either because the
    # computer was off or tagtime was waiting for you to answer a
    # previous ping. If the computer was off, the tag "off" is also
    # added.)
    'retrothresh': 60,

    'gap': 30,#45*60,     # Average number of seconds between pings
                      # (eg, 60*60 = 1 hour).

    'seed': 666,      # For pings not in sync with others,
                      # change this (NB: > 0).

    'catchup': False, # Whether it beeps for old pings, ie, should it beep
                      # a bunch of times in a row when the computer wakes
                      # from sleep.

    'linelen': 79,    # Try to keep log lines at most this long.

    'enforcenums': False,  # Whether it forces you to include a number in your
                           # ping response (include tag non or nonXX where XX
                           # is day of month to override).
                           # This is for task editor integration.

    # System command that will play a sound for pings.
    # Often "play" or "playsound" on Linux, or "afplay" on Mac osx.
    # 'playsound': "afplay ${path}sound/blip-twang.wav",
    # 'playsound': "echo -e '\a'", # this is the default if $playsound not defined.
    # 'playsound': None,  # makes tagtime stay quiet.
    'playsound': "echo -e '\a'",
    'quiet': False
}

def import_from_path(path, namespace=None):
    globals = {} if namespace is None else namespace
    with open(path, 'r') as f:
        contents = f.read()
    exec(contents, globals)
    return globals

def default_property(func):
    name = func.__name__
    def attr(self):
        if name in self._dict:
            return self._dict[name]
        return func(self)
    return property(attr)

class Settings:

    @staticmethod
    def get_default_namespace():
        namespace = dict(DEFAULTS)

        path = os.path.abspath(os.path.dirname(__file__))
        xt = subprocess.getoutput('which xterm')
        ed = subprocess.getoutput('which emacs')

        namespace.update(path=path, xt=xt, ed=ed)

        return namespace

    def get_xt_cmd(self, t, *args):
        # if 'xt_cmd' in self._dict:
        #     return shlex.split(self._dict['xt_cmd'])

        result = [self.xt, '-T', t, '-fg', 'white', '-bg', 'red',
                  '-cr', 'MidnightBlue', '-bc', '-rw', '-e']
        result.extend(args)
        return result

    @property
    def edit_cmd(self):
        if 'edit_cmd' in self._dict:
            return shlex.split(self._dict['edit_cmd'])

        return self.get_xt_cmd('{t}', self.ed, '{f}')

    @default_property
    def logf(self):
        return os.path.join(self.path, "{}.log".format(self.user))

    def get_edit_cmd(self, f, t):
        return [item.format(f=f, t=t) for item in self.edit_cmd]

    def __init__(self, srcpath=SETTINGS_PATH, defaults=DEFAULTS):
        self._srcpath = srcpath
        self._dict = import_from_path(self._srcpath,
                                      self.get_default_namespace())

        self.rand = util.Random(gap=self.gap, seed=self.seed)
        self.logger = util.Logger(logf=self.logf, linelen=self.linelen)

    def __getattr__(self, key):
        if key and key[0] != '_' and key in self._dict:
            return self._dict[key]
        raise AttributeError('no such attribute {}'.format(key))

if __name__ != '__main__':
    settings = Settings()
