# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
import  sys
import  time
from    datetime        import *

from    utilities.units    import *

#-------------------------------------------------------------------------------
# Constants
#-------------------------------------------------------------------------------
STREAM = sys.stdout

#-------------------------------------------------------------------------------
# StandardProgressBar
#-------------------------------------------------------------------------------
class StandardProgressBar():

    #---------------------------------------------------------------------------
    # Fields
    _label              = ''
    _width              = 32
    _total              = None
    _start              = 0
    _template           = ""
    _position_formatter = None
    _total_formatter    = None
    _speed_formatter    = None

    #---------------------------------------------------------------------------
    # __init__
    def __init__(self,
                 total,
                 template,
                 position_formatter,
                 total_formatter,
                 speed_formatter,
                 label              = '',
                 width              = 30):
        self._label = label
        self._width = width
        self._total = total
        self._start = datetime.now()
        self._template = template
        self._position_formatter = position_formatter
        self._total_formatter    = total_formatter
        self._speed_formatter    = speed_formatter

    #---------------------------------------------------------------------------
    # update
    def update(self, position, step_name):
        time_elapsed            = (datetime.now() - self._start).total_seconds()

        items_left              = self._total - position

        if(time_elapsed != 0):
            average_speed           = position/time_elapsed
            if(average_speed != 0):
                seconds_left            = items_left/average_speed
            else:
                seconds_left = 3600*23
            time_left               = time(int(seconds_left/3600), int(seconds_left/60 % 60), int(seconds_left % 60))
            formatted_time_left     = time_left.strftime('%H:%M:%S')
        else:
            average_speed = 0
            formatted_time_left = "Inf."

        def format_value(formatter, value):
            if(formatter is not None):
                return formatter(value)
            else:
                return str(value)

        formatted_speed     = format_value(self._speed_formatter, average_speed)
        formatted_position  = format_value(self._position_formatter, position)
        formatted_total     = format_value(self._total_formatter, self._total)

        x                       = int(self._width*position/self._total)
        empty_chars             = " " * int(self._width - x)
        filled_chars            = "#" * int(x)

        templated_progress_bar  = self._template.format(label          = self._label,
                                                        filled_chars   = filled_chars,
                                                        empty_chars    = empty_chars,
                                                        position       = formatted_position,
                                                        total          = formatted_total,
                                                        time_left      = formatted_time_left,
                                                        speed          = formatted_speed,
                                                        step_name      = step_name)
        templated_progress_bar_size = len(templated_progress_bar)
        templated_progress_bar      = templated_progress_bar + (79 - templated_progress_bar_size) * " " + "\r"
        return templated_progress_bar
