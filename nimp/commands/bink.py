# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
import re
import tempfile

from nimp.commands._command                  import *

from nimp.utilities.files                    import *
from nimp.utilities.hashing                  import *
from nimp.utilities.paths                    import *
from nimp.utilities.perforce                 import *
from nimp.utilities.processes                import *

FFMPEG_PATH = "ffmpeg/bin/ffmpeg.exe"
BINKC_PATH  = "RadTools/binkc.exe"
BMP_FILES   = "MovieFrame%05d.bmp"

#-------------------------------------------------------------------------------
class BinkCommand(Command):

    def __init__(self):
        Command.__init__(self, 'bink', 'Records a matinee to a bink2 video.')

    #---------------------------------------------------------------------------
    # configure_arguments
    def configure_arguments(self, context, parser):
        parser.add_argument('bink_name',
                        metavar = '<BINK_NAME>',
                        type    = str)

        parser.add_argument('actions',
                            help    = 'Actions to perform',
                            metavar = '<ACTIONS>',
                            nargs   = '+',
                            choices   = ["shoot", "encode-avi", "update-video", "update-audio"])

        parser.add_argument('-r',
                        '--resolution',
                        help    = 'Resolution',
                        metavar = '<Resolution>',
                        default = "1920x1080")

        parser.add_argument('-f',
                        '--framerate',
                        help    = 'Framerate',
                        metavar = '<FRAMERATE>',
                        default = "30.0")

        return True

    #---------------------------------------------------------------------------
    # run
    def run(self, context):
        settings    = context.settings
        arguments   = context.arguments

        if not check_bink_config(context):
            return False

        actions = arguments.actions

        if "shoot" in actions:
            if not shoot_matinee(context):
                return False

        if "encode-avi" in actions:
            if not encode_avi(context):
                return False

        log_notification("Encoding 1920x1080 bink video")
        if "update-video" in actions:
            if not update_video(context):
                return False


        return True

#-------------------------------------------------------------------------------
def parse_resolution(arguments):
    resolution_match = re.search("([0-9]+)x([0-9]+)", arguments.resolution)

    if resolution_match is None:
        return None

    return resolution_match.group(1), resolution_match.group(2)

#-------------------------------------------------------------------------------
def get_binkc_path(settings):
    return os.path.join(settings.external_tools_path, BINKC_PATH)

#-------------------------------------------------------------------------------
def get_ffmpeg_path(settings):
    return os.path.join(settings.external_tools_path, FFMPEG_PATH)

#-------------------------------------------------------------------------------
def check_bink_config(context):
    settings  = context.settings
    arguments = context.arguments

    if not check_config_value(settings,    "screenshots_directory")\
       or not check_config_value(settings, "external_tools_path")\
       or not check_config_value(settings, "high_res_binks_directory")\
       or not check_config_value(settings, "low_res_binks_directory")\
       or not check_config_value(settings, "binks_avi_directory")\
       or not check_config_value(settings, "ue3_executable"):
        return False

    screenshots_directory = settings.screenshots_directory
    ue3_executable        = settings.ue3_executable
    binkc_path            = get_binkc_path(settings)
    ffmpeg_path           = get_ffmpeg_path(settings)

    if not os.path.exists(binkc_path):
        log_error("Unable to find Bink compression tool at {0}.", os.path.abspath(binkc_path))
        return False

    if not os.path.exists(ffmpeg_path):
        log_error("Unable to find ffmpeg at {0}.", os.path.abspath(ffmpeg_path))
        return False

    if not os.path.exists(ue3_executable):
        log_error("Unable to find Unreal Engine executable at {0}.", os.path.abspath(ue3_executable))
        return False

    if parse_resolution(arguments) is None:
        log_error("Invalid resolution format")
        return False

    if not os.path.exists(screenshots_directory):
        log_warning("Screenshots directory {0} doesn't exists, creating it", os.path.abspath(screenshots_directory))
        mkdir(screenshots_directory)

    return True

#-------------------------------------------------------------------------------
def shoot_matinee(context):
    settings                = context.settings
    arguments               = context.arguments
    ue3_executable          = settings.ue3_executable
    resx, resy              = parse_resolution(arguments)
    screenshots_directory   = settings.screenshots_directory

    log_notification("Cleaning screenshots directory")
    regex_delete_files(screenshots_directory, ".*\.bmp")

    log_notification("Capturing matinee")
    if call_process(".", [ue3_executable, "WhatIf_ShootBink",  "-resx=1920",  "-resy=1080", "-dumpmovie",  "-benchmark",  "-NOTEXTURESTREAMING", "-MAXQUALITYMODE"]) != 0:

        return False
    return True

#-------------------------------------------------------------------------------
def encode_avi(context):
    settings                = context.settings
    arguments               = context.arguments

    bink_name               = arguments.bink_name
    ffmpeg_path             = get_ffmpeg_path(settings)
    screenshots_directory   = settings.screenshots_directory
    input                   = "{0}/{1}".format(screenshots_directory, BMP_FILES)
    output_directory        = os.path.join(settings.binks_avi_directory, bink_name)
    output                  = os.path.join(output_directory, "{0}.Avi".format(bink_name))

    mkdir(output_directory)

    log_notification("Encoding .avi n {0}", output)
    if call_process(".", [ffmpeg_path, "-r", arguments.framerate, "-i",  input, "-vcodec", "huffyuv", output]) != 0:
        return False

    return True

#-----------------------------------------------------------------------------
def update_video(context):
    settings  = context.settings
    arguments = context.arguments

    bink_name   = arguments.bink_name
    binkc_path  = get_binkc_path(settings)
    input       = os.path.join(settings.binks_avi_directory, bink_name, "{0}.Avi".format(bink_name))
    output      = os.path.join(settings.high_res_binks_directory, "{0}.bik".format(bink_name))

    input   = input.replace("/", "\\")
    output  = output.replace("/", "\\")

    with PerforceTransaction("Updated {0} BIK movie".format(bink_name), output) as transaction:
        if call_process(".", [binkc_path, input, output, "/F{0}".format(arguments.framerate), "/O", "/#"]) != 0:
            transaction.abort()
            return False

    return True
