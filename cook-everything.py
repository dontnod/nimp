#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import subprocess

maps = [
    "whatif.umap",
    "whatif_menu.umap",
    "e1_1a.umap",
    #"e1_5a.umap",
    #"e1_5b.umap",
]

args = [
    "--noexpansion",
]

platforms = [
    "PCConsole",
    #"Win64",
    "PS3",
    "PS4",
    "Xbox360",
    "XboxOne",
]

configs = [
    #"release",
    "test",
]

languages = [
    "INT",
    "FRA",
    #"DEU",
    "ESN",
]

def ue3_cook(maps, args, platform, config):
    print "Platform:", platform, "Config:", config
    cmdline = "nimp.py --verbose ue3-cook"
    cmdline += " " + " ".join(maps)
    cmdline += " " + " ".join(args)
    cmdline += " -p " + platform
    cmdline += " -c " + config
    cmdline += " -l " + " ".join(languages)
    print cmdline
    subprocess.call(cmdline, shell = True)

for p in platforms:
    for c in configs:
        ue3_cook(maps, args, p, c)

