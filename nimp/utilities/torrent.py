# -*- coding: utf-8 -*-

from nimp.utilities.file_mapper import *

from BitTornado.Meta.Info import Info, MetaInfo
from BitTornado.Meta.BTTree import BTTree
from BitTornado.Meta.bencode import bencode


def _splitpath(path):
    d, f = os.path.split(path)
    return _splitpath(d) + [f] if d else [f]


def make_torrent(name, tracker, files):
    """Make a single .torrent file for a given list of items"""

    # Build a list of everything we want in the torrent; only files for
    # now but the code below would work with directories, too.
    tree_list = [BTTree(f, _splitpath(f)) for f, ignored in files() if os.path.isfile(f)]

    # XXX: BitTornado doesn’t support this yet
    params = { 'private': True }

    info = Info(name, sum(tree.size for tree in tree_list),
                flag=None, progress=lambda x: None,
                progress_percent=True, **params)
    for tree in tree_list:
        tree.addFileToInfos((info,))

    infoparams = { key:val for key, val in params.items() \
                   if key in MetaInfo.typemap }
    metainfo = MetaInfo(announce=tracker, info=info, **infoparams)
    return bencode(metainfo)

