# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# imports
#-------------------------------------------------------------------------------
import json
import jsmin
import os

from utilities.logging  import *
from utilities.files    import *

#-------------------------------------------------------------------------------
# read_json
#-------------------------------------------------------------------------------
def read_json(json_file_name):
    if not os.path.exists(json_file_name):
        log_verbose("Json file {0} don't exists.", json_file_name)
        return None

    json_file = open_readable(json_file_name)

    if(json_file is None):
        log_verbose("Can't open json file {0} for reading", json_file_name)
        return None

    try:
        result = json.loads(jsmin.jsmin(json_file.read()))
        json_file.close()
    except ValueError as value_error:
        log_error("Error while parsing file {0} : {1}.", json_file_name, value_error)
        return None

    return result

#-------------------------------------------------------------------------------
# write_json
#-------------------------------------------------------------------------------
def write_json(object, json_file_name):
    json_file = open_writable(json_file_name)

    if(json_file is None):
        log_verbose("Can't open json file {0} for writing", json_file_name)
        return False

    json.dump(object, json_file, indent = 4)
    json_file.close()
    return True
