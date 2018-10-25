# Copyright © 2018 Dontnod Entertainment
''' Command to update the symbol server '''

import logging
import os
import shutil

import nimp.command
import nimp.system


def _list_files(source):
    all_files = []

    for file_path in os.listdir(source):
        file_path = os.path.join(source, file_path)
        if os.path.isdir(file_path):
            all_files.extend(_list_files(file_path))
        else:
            all_files.append(file_path)

    return all_files


def _copy_file(source, destination, simulate):
    if not simulate:
        destination_directory = os.path.dirname(destination)
        if not os.path.exists(destination_directory):
            os.makedirs(destination_directory)
        shutil.copyfile(source, destination)


class UpdateSymbolServer(nimp.command.Command):
    ''' Update the symbol server '''


    def __init__(self):
        super(UpdateSymbolServer, self).__init__()


    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'free_parameters')
        parser.add_argument('--symbol-type', required = True, metavar = '<type>', help = 'Set the type of symbols to upload')
        parser.add_argument('--platform', metavar = '<platform>', help = 'Set the platform to upload symbols for')
        parser.add_argument("--simulate", action = "store_true", help = "Do a test run without actually uploading files")
        return True


    def is_available(self, env):
        if not hasattr(env, 'symbol_servers'):
            return False, 'symbol_servers is not defined'
        return True, ''


    def run(self, env):

        if env.symbol_type == 'program':
            raise NotImplementedError('Program symbols not handled, use upload command')
        elif env.symbol_type == 'shaders':
            symbol_source = '{root_dir}/{game}/Saved/ShaderDebugInfo'
            symbol_source += '/' + ('SF_PS4/sdb' if env.ue4_platform == 'PS4' else env.ue4_platform)
        else:
            raise ValueError('Unexpected symbol type: ' + env.symbol_type)

        symbol_source = nimp.system.sanitize_path(env.format(symbol_source))
        symbol_destination = nimp.system.sanitize_path(env.format(env.symbol_servers[env.symbol_type]))

        logging.info('Uploading from %s to %s (Simulate: %s)', symbol_source, symbol_destination, env.simulate)

        if not os.path.exists(symbol_source):
            logging.info('Symbol source does not exist: %s', symbol_source)
            return True

        if not os.path.exists(symbol_destination) and not env.simulate:
            os.makedirs(symbol_destination)

        all_files = _list_files(symbol_source)
        for source in all_files:
            destination = os.path.join(symbol_destination, source[ len(symbol_source) + 1 : ])
            logging.info('Copying %s to %s', source, destination)
            nimp.system.try_execute(lambda: _copy_file(source, destination, env.simulate), OSError)

        return True
