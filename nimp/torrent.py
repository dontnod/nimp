# -*- coding: utf-8 -*-
# Copyright © 2014—2016 Dontnod Entertainment

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
''' Torrent related utilities '''

import os
import logging

import nimp.system

BT_INFO = nimp.system.try_import('BitTornado.Meta.Info')
BT_BTTREE = nimp.system.try_import('BitTornado.Meta.BTTree')
BT_BENCODE = nimp.system.try_import('BitTornado.Meta.bencode')

def make_torrent(root, tracker, publish):
    ''' Make a single .torrent file for a given list of items '''

    # Only publish files, and can’t create an empty torrent
    tree_list = [BT_BTTREE.BTTree(src, nimp.system.path_to_array(dst)) for src, dst in sorted(set(publish())) if os.path.isfile(src)]
    if not tree_list:
        return None

    # If there is only one file in the list, the torrent will not have any
    # subdirectories so the root name should be the file name.
    if len(tree_list) == 1:
        root = tree_list[0].path[-1]

    # XXX: BitTornado doesn’t support this yet
    params = { 'private': True }

    info = BT_INFO.Info(root, sum(tree.size for tree in tree_list),
                        flag=None, progress=lambda x: None,
                        progress_percent=True, **params)
    for tree in tree_list:
        logging.debug('Adding “%s” as “%s”', tree.loc, '/'.join(tree.path))
        tree.addFileToInfos((info,))

    infoparams = { key:val for key, val in params.items() \
                   if key in BT_INFO.MetaInfo.typemap }
    metainfo = BT_INFO.MetaInfo(announce=tracker, info=info, **infoparams)
    return BT_BENCODE.bencode(metainfo)

