#!/usr/bin/env python3

import imp
import os

SETTINGS_FILE = '.pytagtimerc'
SETTINGS_PATH = os.path.expanduser(os.path.join('~', SETTINGS_FILE))
# use .pytagtimerc for now so as not to interfere with the old perl
# config

DEFAULTS = {}

def import_from_path(path):
    globals = {}
    with open(path, 'r') as f:
        contents = f.read()
    exec(contents, globals)
    return globals

class Settings:

    def __init__(self, srcpath=SETTINGS_PATH):
        self._srcpath = srcpath
        self._dict = import_from_path(self._srcpath)

    def __getattr__(self, key):
        if key and key[0] != '_' and key in self._dict:
            return self._dict[key]
        raise AttributeError('no such attribute {}'.format(key))

if __name__ != '__main__':
    settings = Settings()
