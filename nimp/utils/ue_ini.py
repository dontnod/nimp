# -*- coding: utf-8 -*-
# Copyright (c) 2014-2023 Dontnod Entertainment

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

''' UE .ini related utilities '''

import configparser
import glob
import re
import typing

def ue_ini_parser():
    config_parser = configparser.ConfigParser(strict=False)
    # ConfigParser will load keys (and thus write) as case-insensitive by default
    # setting `optionxform` to `str` will make it case-sensitive
    config_parser.optionxform = str
    return config_parser


def get_ini_value(file_path, key):
    ''' Retrieves a value from a ini file '''
    with open(file_path) as ini_file:
        ini_content = ini_file.read()
    match = re.search('^' + key + r'=(?P<value>.*?)$', ini_content, re.MULTILINE)
    if not match:
        raise KeyError('Key {key} was not found in {file_path}'.format(**locals()))
    return match.group('value')


def enumerate_unreal_configs(env):
    # lookup unreal project conf
    # order matters: from deepest ini to broadest (deep<-variant<-platform<-game)
    config_files_patterns = []
    if hasattr(env, 'variant') and env.variant:
        config_files_patterns.extend([
            '{uproject_dir}/Config/Variants/Active/{cook_platform}/{cook_platform}Game.ini',
            '{uproject_dir}/Config/Variants/{variant}/{cook_platform}/{cook_platform}Game.ini',
            '{uproject_dir}/Config/Variants/Active/DefaultGame.ini',
            '{uproject_dir}/Config/Variants/{variant}/DefaultGame.ini'
        ])
    config_files_patterns.extend([
        '{uproject_dir}/Platforms/{cook_platform}/Config/DefaultGame.ini',
        '{uproject_dir}/Config/DefaultGame.ini',
    ])
    for config_files_pattern in config_files_patterns:
        for file in glob.glob(env.format(config_files_pattern)):
            yield file

def _find_section_indexes(ini_content: list, needle: str):
    return next((index for index, line in enumerate(ini_content) if re.match(rf'^\[{needle}]', line)), None)

def update_ini_file(ini_content: list[str], section: str,
                    *keys: tuple[str, typing.Any]):
    '''
    this helper function updates an active ini file with given section/keys

    This is needed as UE ini files are non-standard which cause some data-loss if using configparser.ConfigParser
    eg. UE ini allow to extend a key's value with +key=xxx and there can be multiple line like this.
    configparser.ConfigParser does not allow multiple values like this and will only keep the last one
    '''

    if not keys:
        return ini_content

    section_idx = _find_section_indexes(ini_content, section)
    if section_idx is None:
        section_idx = len(ini_content)

    section_end_idx = None
    next_section_rel_idx = _find_section_indexes(ini_content[section_idx+1:], '.*')
    if next_section_rel_idx is not None:
        section_end_idx = section_idx + 1 + next_section_rel_idx
    else:
        section_end_idx = len(ini_content)

    new_section_content = []
    # Re create the section replacing key if necessary
    for line in ini_content[section_idx:section_end_idx]:
        key, value = next(((k, v) for (k, v) in keys if re.match(rf'^{k}=.*$', line) is not None), (None, None))
        if key is not None:
            new_section_content.append(f"{key}={value if value is not None else ''}\n")
        else:
            new_section_content.append(line)

    return ini_content[:section_idx] + new_section_content + ini_content[section_end_idx:]
