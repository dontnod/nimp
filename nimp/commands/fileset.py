# -*- coding: utf-8 -*-

from nimp.commands.command import *
from nimp.ue3 import *
from nimp.system import *
from nimp.torrent import *


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
            torrent_file = env.torrent_file if hasattr(env, 'torrent_file') else 'torrent.torrent'
            torrent_dir = env.torrent_dir if hasattr(env, 'torrent_dir') else 'torrent'
            torrent_tracker = env.torrent_tracker if hasattr(env, 'torrent_tracker') else 'http://tracker/announce'

            # Build a list of everything we want in the torrent; only files for
            # now but the code below would work with directories, too.
            data = make_torrent(torrent_dir, torrent_tracker,
                                (f for f, ignored in files() if os.path.isfile(f)))
            with open(torrent_file, 'wb') as fd:
                fd.write(data)

        return True

