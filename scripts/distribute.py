import glob
import logging
import os
import shutil

import configuration
import environment


def main():
    environment.configure_logging(logging.INFO)
    environment_instance = environment.load_environment()
    configuration_instance = configuration.load_configuration(environment_instance)

    artifact_repository = os.path.normpath(environment_instance["artifact_repository"])
    artifact_repository = os.path.join(artifact_repository, configuration_instance["project"], configuration_instance["project_version"]["branch"])
    upload(artifact_repository, configuration_instance["distribution"], configuration_instance["project_version"], False)


def upload(artifact_repository, distribution, version, simulate):
    logging.info("Uploading distribution package")

    archive_name = distribution + "-" + version["full"]
    source_path = os.path.join("dist", archive_name + ".zip")
    destination_path = os.path.join(artifact_repository, "packages", distribution, archive_name + ".zip")

    existing_distribution_pattern = distribution + "-" + version["identifier"] + "+*.zip"
    existing_distribution = next((x for x in glob.glob(os.path.join(artifact_repository, "packages",distribution, existing_distribution_pattern))), None)
    if existing_distribution is not None:
        raise ValueError("Version %s already exists: '%s'" % (version["identifier"], os.path.basename(existing_distribution)))

    logging.info("Uploading '%s' to '%s'", source_path, destination_path)

    if not simulate:
        os.makedirs(os.path.dirname(destination_path), exist_ok = True)
        shutil.copyfile(source_path, destination_path + ".tmp")
        shutil.move(destination_path + ".tmp", destination_path)


if __name__ == "__main__":
    main()
