# -*- coding: utf-8 -*-

import os
import subprocess

from nimp.utilities.processes import *
from nimp.utilities.paths import *


def git_cat(path, repository, branch = 'master'):

    p = subprocess.Popen('git archive --remote=%s %s %s | tar -xOf -' % (repository, branch, path),
                         shell = True, stdout=subprocess.PIPE)
    return p.stdout.read()


# FIXME: this is rather inefficient since it transfers the whole tree instead of the filenames
def git_find(path, repository, branch = 'master'):
    p = subprocess.Popen('git archive --remote=%s %s %s | tar -tf -' % (repository, branch, path),
                         shell = True, stdout=subprocess.PIPE)
    return [l.strip().decode('utf-8') for l in p.stdout.readlines()]

