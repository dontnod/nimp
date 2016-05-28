# -*- coding: utf-8 -*-

from nimp.utilities.system import *

from BitTornado.Meta.Info import Info, MetaInfo
from BitTornado.Meta.BTTree import BTTree
from BitTornado.Meta.bencode import bencode


def make_torrent(root, tracker, publish):
    """Make a single .torrent file for a given list of items"""

    # Only publish files, and can’t create an empty torrent
    tree_list = [BTTree(src, path_to_array(dst)) for src, dst in sorted(set(publish())) if os.path.isfile(src)]
    if not tree_list:
        return None

    # If there is only one file in the list, the torrent will not have any
    # subdirectories so the root name should be the file name.
    if len(tree_list) == 1:
        root = tree_list[0].path[-1]

    # XXX: BitTornado doesn’t support this yet
    params = { 'private': True }

    info = Info(root, sum(tree.size for tree in tree_list),
                flag=None, progress=lambda x: None,
                progress_percent=True, **params)
    for tree in tree_list:
        log_verbose('Adding “{0}” as “{1}”', tree.loc, '/'.join(tree.path))
        tree.addFileToInfos((info,))

    infoparams = { key:val for key, val in params.items() \
                   if key in MetaInfo.typemap }
    metainfo = MetaInfo(announce=tracker, info=info, **infoparams)
    return bencode(metainfo)

