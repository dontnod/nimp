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
''' Deploys binary files from a zipped archives '''

import logging
import os
import os.path
import stat
import zipfile

import nimp.command
import nimp.environment
import nimp.system

MAGIC = nimp.system.try_import('magic')

class Deploy(nimp.command.Command):
    ''' Deploys compiled binaries to local directory '''
    def __init__(self):
        super(Deploy, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'revision', 'platform')

        parser.add_argument('--max-revision',
                            help = 'Find a revision <= to this',
                            metavar = '<revision>')

        return True

    def is_available(self, env):
        if nimp.system.is_windows():
            return True, ''

        return (MAGIC is not None and hasattr(MAGIC, 'from_file'),
                ('The python-magic module was not found on your system and is '
                 'required by this command.'))

    def run(self, env):
        mapper = nimp.system.map_files(env)
        mapper = mapper.to(env.root_dir)

        logging.debug("Deploying version…")

        if env.revision is None:
            env.revision = nimp.system.get_latest_available_revision(env, env.binaries_archive, **vars(env))

        if env.revision is None:
            return False

        # Now uncompress the archive; it’s simple
        fd = open(nimp.system.sanitize_path(env.format(env.binaries_archive)), 'rb')
        zip_file = zipfile.ZipFile(fd)
        for name in zip_file.namelist():

            logging.info('Extracting %s to %s', name, env.root_dir)
            zip_file.extract(name, nimp.system.sanitize_path(env.format(env.root_dir)))

            # If this is an executable or a script, make it +x
            if MAGIC is not None:
                filename = nimp.system.sanitize_path(os.path.join(env.format(env.root_dir), name))
                filetype = MAGIC.from_file(filename)
                if type(filetype) is bytes:
                    # Older versions of python-magic return bytes instead of a string
                    filetype = filetype.decode('ascii')

                if 'executable' in filetype or 'script' in filetype:
                    try:
                        logging.info('Making executable because of file type: %s', filetype)
                        file_stat = os.stat(filename)
                        os.chmod(filename, file_stat.st_mode | stat.S_IEXEC)
                    except Exception:
                        pass
        fd.close()

        return True

