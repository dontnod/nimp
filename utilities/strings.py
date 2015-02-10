# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
def capitalize_name(name):
    name_parts      = name.split("_")
    upper_case_name = ""
    for name_part in name_parts:
        upper_case_name = upper_case_name + name_part.title()
    return upper_case_name
