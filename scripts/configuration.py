import subprocess


def load_configuration(environment):
    configuration = {
        "project": "nimp",
        "project_version": { "identifier": "0.14.0" },
        "distribution": "nimp-cli",
    }

    configuration["project_version"]["revision"] = subprocess.check_output([ environment["git_executable"], "rev-parse", "--short=10", "HEAD" ]).decode("utf-8").strip()
    configuration["project_version"]["branch"] = subprocess.check_output([ environment["git_executable"], "rev-parse", "--abbrev-ref", "HEAD" ]).decode("utf-8").strip()
    configuration["project_version"]["numeric"] = "{identifier}".format(**configuration["project_version"])
    configuration["project_version"]["full"] = "{identifier}+{revision}".format(**configuration["project_version"])

    return configuration
