# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
UNIT_SIZE_KEY           = "UnitSizeKey"
UNIT_ABBREVIATION_KEY   = "UnitAbbreviationKey"
UNIT_NB_DECIMALS_KEY    = "UnitNbDecimals"
UNIT_MAXIMUM_SIZE       = "UnitMaximumSize"

#-------------------------------------------------------------------------------
OCTET_PER_SECOND_UNITS  = [ { UNIT_SIZE_KEY         : 1,
                              UNIT_ABBREVIATION_KEY : "o/s",
                              UNIT_NB_DECIMALS_KEY  : 2,
                              UNIT_MAXIMUM_SIZE     : 1024},

                            { UNIT_SIZE_KEY         : 1024,
                              UNIT_ABBREVIATION_KEY : "Ko/s",
                              UNIT_NB_DECIMALS_KEY  : 2,
                              UNIT_MAXIMUM_SIZE     : 1024},

                            { UNIT_SIZE_KEY         : 1024*1024,
                              UNIT_ABBREVIATION_KEY : "Mo/s",
                              UNIT_NB_DECIMALS_KEY  : 2,
                              UNIT_MAXIMUM_SIZE     : 1024},

                            { UNIT_SIZE_KEY         : 1024*1024*1024,
                              UNIT_ABBREVIATION_KEY : "Go/s",
                              UNIT_NB_DECIMALS_KEY  : 2,
                              UNIT_MAXIMUM_SIZE     : 1000000000000} ]

OCTET_UNITS             = [ { UNIT_SIZE_KEY         : 1,
                              UNIT_ABBREVIATION_KEY : "o",
                              UNIT_NB_DECIMALS_KEY  : 2,
                              UNIT_MAXIMUM_SIZE     : 1024},

                            { UNIT_SIZE_KEY         : 1024,
                              UNIT_ABBREVIATION_KEY : "Ko",
                              UNIT_NB_DECIMALS_KEY  : 2,
                              UNIT_MAXIMUM_SIZE     : 1024},

                            { UNIT_SIZE_KEY         : 1024*1024,
                              UNIT_ABBREVIATION_KEY : "Mo",
                              UNIT_NB_DECIMALS_KEY  : 2,
                              UNIT_MAXIMUM_SIZE     : 1024},

                            { UNIT_SIZE_KEY         : 1024*1024*1024,
                              UNIT_ABBREVIATION_KEY : "Go",
                              UNIT_NB_DECIMALS_KEY  : 2,
                              UNIT_MAXIMUM_SIZE     : 1000000000000} ]

#-------------------------------------------------------------------------------
def format_octet(value, width = 7, alignement = ">"):
    return format_unit(value, OCTET_UNITS, width, alignement)

#-------------------------------------------------------------------------------
def format_octet_per_second(value, width = 7, alignement = ">"):
    return format_unit(value, OCTET_PER_SECOND_UNITS, width, alignement)

#-------------------------------------------------------------------------------
def format_unit(value, units, width=7, alignement = ">"):
    value = float(value)
    for unit_it in units:
        unit_size           = unit_it[UNIT_SIZE_KEY]
        unit_abbreviation   = unit_it[UNIT_ABBREVIATION_KEY]
        unit_nb_decimal     = unit_it[UNIT_NB_DECIMALS_KEY]
        unit_maximum_size   = unit_it[UNIT_MAXIMUM_SIZE]
        unit_value          = value/unit_size
        if(unit_value < unit_maximum_size):
            unit_format = "{: " + alignement;
            if(width is not None):
                unit_format += str(width);
            unit_format += "." + str(unit_nb_decimal) + "f} " + unit_abbreviation
            unit_str = unit_format.format(unit_value)
            return unit_str
    return ""
