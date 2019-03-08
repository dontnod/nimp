import subprocess


def load_configuration(environment):
    configuration = {
        "project": "nimp",
        "project_version": { "identifier": "0.9.6" },
        "distribution": "nimp-cli",
    }

    revision = subprocess.run([ environment["git_executable"], "rev-parse", "--short=10", "HEAD" ], check = True, capture_output = True).stdout.decode("utf-8").strip()
    branch = subprocess.run([ environment["git_executable"], "rev-parse", "--abbrev-ref", "HEAD" ], check = True, capture_output = True).stdout.decode("utf-8").strip()

    configuration["project_version"]["revision"] = revision
    configuration["project_version"]["branch"] = branch
    configuration["project_version"]["numeric"] = "{identifier}".format(**configuration["project_version"])
    configuration["project_version"]["full"] = "{identifier}+{revision}".format(**configuration["project_version"])

    return configuration
