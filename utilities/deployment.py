# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
from datetime import date

import os
import stat
import os.path
import tempfile;
import shutil
import stat

from utilities.perforce     import *
from utilities.files        import *


#-------------------------------------------------------------------------------
def deploy(source, target):
    """ Copy the content of the given source directory, checkouting local files
        if necesseray
    """
    with PerforceTransaction("Binaries checkout") as transaction:
        for root, directories, files in os.walk(source, topdown=False):
            for file in files:
                source_file     = os.path.join(root, file)
                local_directory = os.path.relpath(root, source)
                local_file      = os.path.join(target, local_directory, file)

                log_verbose("{0} => {1}", source_file, local_file)

                if not os.path.exists(local_directory):
                    mkdir(local_directory)

                transaction.add(local_file)

                if os.path.exists(local_file):
                    os.chmod(local_file, stat.S_IWRITE)
                shutil.copy(source_file, local_file)
    return True

#------------------------------------------------------------------------------
class FilePublisher:
    def __init__(self, destination, project, game, platform, configuration, dlc, language, revision):
        self._project       = project
        self._game          = game
        self._platform      = platform
        self._configuration = configuration
        self._dlc           = dlc
        self._language      = language
        self._revision      = revision
        self._destination   = self._format(destination)

    def delete_destination(self):
        def _onerror(func, path, exc_info):
            if not os.access(path, os.W_OK):
                os.chmod(path, stat.S_IWUSR)
                func(path)
            else:
                raise
        if os.path.exists(self._destination):
            shutil.rmtree(self._destination, onerror = _onerror)

    def add(self, source, include = ['*'], exclude = [], recursive = True):
        for i in range(0, len(include)):
            include[i] = self._format(include[i])
        for i in range(0, len(exclude)):
            exclude[i] = self._format(exclude[i])

        source = self._format(source)
        if os.path.isfile(source):
            target              = os.path.join(self._destination, os.path.relpath(source, '.'))
            target_directory    = os.path.dirname(target)

            if not os.path.exists(target_directory):
                os.makedirs(target_directory)

            log_verbose("{0} => {1}", source, target)
            shutil.copy(source, target)
            os.chmod(target, stat.S_IWUSR)
        else:
            def _copy_callback(source, destination):
                os.chmod(destination, stat.S_IWUSR)
            if recursive:
                recursive_glob_copy(source, self._destination, include, exclude, copy_callback = _copy_callback)
            else:
                glob_copy(source, self._destination, include, exclude, copy_callback = _copy_callback)
    def _format(self, str):
        return str.format(project          = self._project,
                          game             = self._game,
                          platform         = self._platform,
                          configuration    = self._configuration,
                          dlc              = self._dlc,
                          language         = self._language,
                          revision         = self._revision)
