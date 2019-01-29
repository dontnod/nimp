# -*- coding: utf-8 -*-
# Copyright © 2014—2019 Dontnod Entertainment

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

''' Git utilities '''

import nimp.sys.process

def get_branch():
    command = 'git branch --contains HEAD'
    result, output, _ = nimp.sys.process.call(command.split(' '), capture_output=True)
    if result != 0:
        return None
    return output[2:].strip()

def get_version():
    from datetime import datetime, timezone
    command = 'git log -10 --date=short --pretty=format:%ct.%h'
    result, output, _ = nimp.sys.process.call(command.split(' '), capture_output=True)
    if result != 0 or '.' not in output:
        return None
    # Parse up to 10 revisions to detect date collisions
    n = 0
    for line in output.split('\n'):
        pair = line.split('.')
        if n == 0:
            date, shorthash = pair
        elif pair[0] != date:
            break
        n += 1
    utc_time = datetime.fromtimestamp(float(date), timezone.utc)
    local_time = utc_time.astimezone()
    return '.'.join([utc_time.astimezone().strftime("%Y%m%d.%H%M"), str(n), shorthash])

