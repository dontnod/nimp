nimp build - Compiles a project
===============================

Compiles an Unreal Engine or Visual Studio project.

Usage
-----

::

    nimp build [-h] [-p <platform>] [-c <configuration>] [-t <target>]
               [--bootstrap] [--disable-unity] [--fastbuild]
    
    optional arguments:
      -h, --help            show this help message and exit
      -p <platform>, --platform <platform>
                            Platform
      -c <configuration>, --configuration <configuration>
                            Configuration
      -t <target>, --target <target>
                            Target
      --bootstrap           bootstrap or regenerate project files, if applicable
      --disable-unity       disable unity build
      --fastbuild           activate FASTBuild (implies --disable-unity for now)

Project discovery
-----------------

To determine what should be built, the build command first checks for the
*project_type* configuration value in .nimp.conf. If it's found, it will build
the project accordingly. If not and the executing platform is Windows, it will
search for the first .sln file in the current directory and build it using 
devenv. 

Project settings
-----------------
 * **project_type**
   
   Sets the project type. For now, the only supported value is
   'UE4'. This used to differentiate Unreal 4 projects from now legacy Unreal 3.
   This option is keeped for future use.
