# -*- coding: utf-8 -*-

from nimp.utilities.file_mapper import *

from BitTornado.Meta.Info import Info, MetaInfo
from BitTornado.Meta.BTTree import BTTree
from BitTornado.Meta.bencode import bencode


def _splitpath(path):
    d, f = os.path.split(path)
    return _splitpath(d) + [f] if d else [f]


def make_torrent(name, tracker, publish):
    """Make a single .torrent file for a given list of items"""

    # Only publish files, and can’t create an empty torrent
    tree_list = [BTTree(src, _splitpath(dst)) for src, dst in sorted(set(publish())) if os.path.isfile(src)]
    if not tree_list:
        return None

    # XXX: BitTornado doesn’t support this yet
    params = { 'private': True }

    info = Info(name, sum(tree.size for tree in tree_list),
                flag=None, progress=lambda x: None,
                progress_percent=True, **params)
    for tree in tree_list:
        log_verbose('Adding “{0}” as “{1}”', tree.loc, '/'.join(tree.path))
        tree.addFileToInfos((info,))

    infoparams = { key:val for key, val in params.items() \
                   if key in MetaInfo.typemap }
    metainfo = MetaInfo(announce=tracker, info=info, **infoparams)
    return bencode(metainfo)

