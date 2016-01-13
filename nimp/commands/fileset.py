# -*- coding: utf-8 -*-

from nimp.commands._command     import *
from nimp.utilities.ue3         import *
from nimp.utilities.file_mapper import *

from BitTornado.Meta.Info import Info, MetaInfo
from BitTornado.Meta.BTTree import BTTree

def make_torrent(name, files, url, params=None, flag=None,
                 progress=lambda x: None, progress_percent=True):
    """Make a single .torrent file for a given list of items"""

    def splitpath(path):
        d, f = os.path.split(path)
        return splitpath(d) + [f] if d else [f]

    tree_list = [BTTree(f, splitpath(f)) for f, ignored in files() if os.path.isfile(f)]

    info = Info(name, sum(tree.size for tree in tree_list),
                flag=flag, progress=progress,
                progress_percent=progress_percent, **params)
    for tree in tree_list:
        tree.addFileToInfos((info,))

    newparams = { key:val for key, val in params.items() \
                  if key in MetaInfo.typemap }

    metainfo = MetaInfo(announce=url, info=info, **newparams)
    metainfo.write(params['target'])


class FileSetCommand(Command):
    def __init__(self):
        Command.__init__(self, 'fileset', 'Do stuff on a list of files')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('--arg',
                            help    = 'Add a key/value pair for use in string interpolation',
                            metavar = '<KEY>=<VALUE>',
                            nargs   = 1,
                            action  = 'append',
                            default = [])

        parser.add_argument('set_name',
                            help    = 'Set name to load (e.g. binaries, version…)',
                            metavar = '<SET_FILE>')

        parser.add_argument('action',
                            help    = 'Action to execute on listed files (one of: robocopy, delete, checkout, reconcile, reconcile_and_submit, list, torrent)',
                            metavar = '<ACTION>',
                            choices = ['robocopy', 'delete', 'checkout', 'reconcile', 'reconcile_and_submit', 'list', 'torrent'])

        parser.add_argument('--src',
                            help    = 'Source directory',
                            metavar = '<DIR>')

        parser.add_argument('--to',
                            help    = 'Destination, if relevant',
                            metavar = '<DIR>',
                            default = None)

        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        if env.arg is not None:
            for key, value in [x[0].split('=') for x in env.arg]:
                setattr(env, key, value)
        env.standardize_names()

        files = env.map_files()
        files_chain = files
        if env.src is not None:
            files_chain = files_chain.src(env.src)

        if env.to is not None:
            files_chain = files_chain.to(env.to)

        files_chain.load_set(env.set_name)

        if env.action == 'robocopy':
            for source, destination in files():
                robocopy(source, destination)

        elif env.action == 'checkout':
            with p4_transaction('Checkout') as trans:
                map(trans.add, files)

        elif env.action == 'delete':
            for source, destination in files():
                if os.path.isfile(source):
                    log_notification("Removing file {0}", source)
                    force_delete(source)

        elif env.action == 'list':
            for source, destination in files():
                log_notification("{0} => {1}", source, destination)

        elif env.action == 'torrent':
            # FIXME: also add 'private':True once BitTornado supports it
            params = { 'target': 'torrentname.torrent', }
            make_torrent('torrentname', files, url='http://tracker:8020/announce', params=params)

        return True

