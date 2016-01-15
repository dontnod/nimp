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

    # If name is e.g. "foo/bar" then BitTornado will consider it an illegal
    # name for security reasons. We simply replace it with "foo" and prepend
    # "bar" to the actual paths inside the torrent.
    subdir = _splitpath(name)
    name = subdir[0]
    subdir = subdir[1:]

    tree_list = [BTTree(f, subdir + _splitpath(f)) for f in files]

    # XXX: BitTornado doesn’t support this yet
    params = { 'private': True }

    info = Info(name, sum(tree.size for tree in tree_list),
                flag=None, progress=lambda x: None,
                progress_percent=True, **params)
    for tree in tree_list:
        log_verbose('Adding “{0}”', tree.loc)
        tree.addFileToInfos((info,))

    infoparams = { key:val for key, val in params.items() \
                   if key in MetaInfo.typemap }
    metainfo = MetaInfo(announce=tracker, info=info, **infoparams)
    return bencode(metainfo)

