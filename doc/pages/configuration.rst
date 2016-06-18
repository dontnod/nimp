*************
Configuration
*************

.nimp.conf
==========
When launched, nimp walks the parent directories up until finding a file named
.nimp.conf. All the commands launched by nimp will have the directory containing
this file as their starting directory. Wich allows to forgot about absolute
paths. Additionnaly, several configuration values can be defined in this file.
Some are global, others are command-specific. Each command-specific
configuration value is documented on the page of the said command, in the
"Configuration values" section.

Global Configuration Values
---------------------------
* *project_type* : Sets this project's type. For now, only 'UE4' is supported.

Project commands
================

Filesets
========

Hooks
=====
