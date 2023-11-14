# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


import logging
import re

from github import GithubException
from mozilla_version.mobile import MobileVersion

from util import (
    compare_as_versions,
    compare_gv_versions,
    get_app_services_version_path,
    get_current_ac_version,
    get_current_as_channel,
    get_current_as_version,
    get_current_glean_version,
    get_current_gv_channel,
    get_current_gv_version,
    get_dependencies_file_path,
    get_gecko_file_path,
    get_latest_as_version,
    get_latest_glean_version,
    get_latest_gv_version,
    get_recent_fenix_versions,
    major_as_version_from_version,
    major_gv_version_from_version,
    use_legacy_as_handling,
)

log = logging.getLogger(__name__)

#
# Helpers
#


def _update_ac_buildconfig(ac_repo, old_ac_version, new_ac_version, branch, author):
    contents = ac_repo.get_contents("android-components/.buildconfig.yml", ref=branch)

    content = contents.decoded_content.decode("utf-8")
    new_content = re.sub(
        r"componentsVersion: \d+\.\d+\.\d+",
        f"componentsVersion: {new_ac_version}",
        content,
    )
    if content == new_content:
        log.warning(
            "Update to .buildConfig.yml resulted in no changes: "
            "maybe the file was already up to date?"
        )

    ac_repo.update_file(
        contents.path,
        f"Set version to {new_ac_version}.",
        new_content,
        contents.sha,
        branch=branch,
        author=author,
    )


def _update_ac_version(ac_repo, old_ac_version, new_ac_version, branch, author):
    contents = ac_repo.get_contents("version.txt", ref=branch)

    content = contents.decoded_content.decode("utf-8")
    new_content = content.replace(old_ac_version, new_ac_version)
    if content == new_content:
        raise Exception(
            "Update to version.txt resulted in no changes: "
            "maybe the file was already up to date?"
        )

    ac_repo.update_file(
        contents.path,
        f"Set version.txt to {new_ac_version}.",
        new_content,
        contents.sha,
        branch=branch,
        author=author,
    )


def _update_gv_version(
    ac_repo, old_gv_version, new_gv_version, branch, channel, author, ac_major_version
):
    contents = ac_repo.get_contents(get_gecko_file_path(ac_major_version), ref=branch)
    content = contents.decoded_content.decode("utf-8")
    new_content = content.replace(
        f'const val version = "{old_gv_version}"',
        f'const val version = "{new_gv_version}"',
    )
    new_content = new_content.replace(
        f'fun version() = "{old_gv_version}"',
        f'fun version() = "{new_gv_version}"',
    )

    if content == new_content:
        raise Exception(
            "Update to Gecko.kt resulted in no changes: "
            "maybe the file was already up to date?"
        )

    ac_repo.update_file(
        contents.path,
        f"Update GeckoView ({channel.capitalize()}) to {new_gv_version}.",
        new_content,
        contents.sha,
        branch=branch,
        author=author,
    )


def _update_as_version(
    ac_repo, old_as_version, new_as_version, branch, author, ac_major_version
):
    if use_legacy_as_handling(ac_major_version):
        path = get_dependencies_file_path(ac_major_version)
        current_version_string = f'mozilla_appservices = "{old_as_version}"'
        new_version_string = f'mozilla_appservices = "{new_as_version}"'
    else:
        path = get_app_services_version_path(ac_major_version)
        current_version_string = f'val VERSION = "{old_as_version}"'
        new_version_string = f'val VERSION = "{new_as_version}"'
    log.info(f"Updating app-services version in {path}")

    contents = ac_repo.get_contents(path, ref=branch)
    content = contents.decoded_content.decode("utf-8")
    new_content = content.replace(current_version_string, new_version_string)
    if content == new_content:
        raise Exception(
            "Update to DependenciesPlugin.kt resulted in no changes: "
            "maybe the file was already up to date?"
        )

    ac_repo.update_file(
        contents.path,
        f"Update A-S to {new_as_version}.",
        new_content,
        contents.sha,
        branch=branch,
        author=author,
    )


def _update_glean_version(
    ac_repo, old_glean_version, new_glean_version, branch, author, ac_major_version
):
    contents = ac_repo.get_contents(
        get_dependencies_file_path(ac_major_version), ref=branch
    )
    content = contents.decoded_content.decode("utf-8")
    new_content = content.replace(
        f'mozilla_glean = "{old_glean_version}"',
        f'mozilla_glean = "{new_glean_version}"',
    )
    if content == new_content:
        raise Exception(
            "Update to DependenciesPlugin.kt resulted in no changes: "
            "maybe the file was already up to date?"
        )

    ac_repo.update_file(
        contents.path,
        f"Update Glean to {new_glean_version}.",
        new_content,
        contents.sha,
        branch=branch,
        author=author,
    )


def _update_geckoview(
    ac_repo, release_branch_name, ac_major_version, author, dry_run=False
):
    try:
        log.info(f"Updating GeckoView on A-C {ac_repo.full_name}:{release_branch_name}")

        gv_channel = get_current_gv_channel(
            ac_repo, release_branch_name, ac_major_version
        )
        log.info(f"Current GV channel is {gv_channel}")

        current_gv_version = get_current_gv_version(
            ac_repo, release_branch_name, ac_major_version
        )
        log.info(
            f"Current GV {gv_channel.capitalize()} version in A-C "
            f"{ac_repo.full_name}:{release_branch_name} is {current_gv_version}"
        )

        if release_branch_name == "main":
            # We always want to be on the latest geckoview version on the main branch
            current_gv_major_version = None
        else:
            current_gv_major_version = major_gv_version_from_version(current_gv_version)
        latest_gv_version = get_latest_gv_version(current_gv_major_version, gv_channel)
        log.info(
            f"Latest GV {gv_channel.capitalize()} version available "
            f"is {latest_gv_version}"
        )

        current_glean_version = get_current_glean_version(
            ac_repo, release_branch_name, ac_major_version
        )
        log.info(
            f"Current Glean version in A-C {ac_repo.full_name}:{release_branch_name} "
            f"is {current_glean_version}"
        )
        latest_glean_version = get_latest_glean_version(latest_gv_version, gv_channel)
        log.info(f"Latest bundled Glean version available is {latest_glean_version}")

        if compare_gv_versions(current_gv_version, latest_gv_version) >= 0:
            log.warning(
                f"No newer GV {gv_channel.capitalize()} release found. Exiting."
            )
            return

        log.info(
            f"We should update A-C {release_branch_name} with GV "
            f"{gv_channel.capitalize()} {latest_gv_version}"
        )

        if dry_run:
            log.warning("Dry-run so not continuing.")
            return

        #
        # Check if the branch already exists
        #

        short_version = (
            "main" if release_branch_name == "main" else f"{ac_major_version}"
        )

        # Create a non unique PR branch name for work on this ac release branch.
        pr_branch_name = f"relbot/upgrade-geckoview-ac-{short_version}"

        try:
            pr_branch = ac_repo.get_branch(pr_branch_name)
            if pr_branch:
                log.warning(f"The PR branch {pr_branch_name} already exists. Exiting.")
                return
        except GithubException:
            # TODO Only ignore a 404 here, fail on others
            pass

        #
        # Create a new branch for this update
        #

        release_branch = ac_repo.get_branch(release_branch_name)
        log.info(f"Last commit on {release_branch_name} is {release_branch.commit.sha}")

        ac_repo.create_git_ref(
            ref=f"refs/heads/{pr_branch_name}", sha=release_branch.commit.sha
        )
        log.info(f"Created branch {pr_branch_name} on {release_branch.commit.sha}")

        log.info(
            "Updating android-components/plugins/dependencies/src/main/java/Gecko.kt"
        )
        _update_gv_version(
            ac_repo,
            current_gv_version,
            latest_gv_version,
            pr_branch_name,
            gv_channel,
            author,
            ac_major_version,
        )

        if current_glean_version != latest_glean_version:
            log.info(
                "Updating android-components/plugins/dependencies/src/"
                "main/java/DependenciesPlugin.kt"
            )
            _update_glean_version(
                ac_repo,
                current_glean_version,
                latest_glean_version,
                pr_branch_name,
                author,
                ac_major_version,
            )
        #
        # Create the pull request
        #

        log.info("Creating pull request")
        pr = ac_repo.create_pull(
            title=f"Update to GeckoView {gv_channel.capitalize()} {latest_gv_version} "
            f"on {release_branch_name}",
            body=f"This (automated) patch updates GV {gv_channel.capitalize()} "
            f"on main to {latest_gv_version}.",
            head=pr_branch_name,
            base=release_branch_name,
        )
        log.info(f"Pull request at {pr.html_url}")
    except Exception as e:
        # TODO Clean up the mess
        raise e


def _update_application_services(
    ac_repo, release_branch_name, ac_major_version, author, dry_run=False
):
    try:
        log.info(f"Updating A-S on {ac_repo.full_name}:{release_branch_name}")

        as_channel = get_current_as_channel(
            ac_repo, release_branch_name, ac_major_version
        )
        log.info(f"Current A-S channel is {as_channel}")

        current_as_version = get_current_as_version(
            ac_repo, release_branch_name, ac_major_version
        )
        log.info(
            f"Current A-S {as_channel.capitalize()} version in A-C "
            f"{ac_repo.full_name}:{release_branch_name} is {current_as_version}"
        )

        latest_as_version = get_latest_as_version(
            major_as_version_from_version(current_as_version),
            as_channel,
        )
        log.info(
            f"Latest A-S {as_channel.capitalize()} version available "
            f"is {latest_as_version}"
        )

        if compare_as_versions(current_as_version, latest_as_version) >= 0:
            log.warning(
                f"No newer A-S {as_channel.capitalize()} release found. Exiting."
            )
            return

        log.info(
            f"We should update A-C {release_branch_name} with A-S "
            f"{as_channel.capitalize()} {latest_as_version}"
        )

        if dry_run:
            log.warning("Dry-run so not continuing.")
            return

        #
        # Check if the branch already exists
        #

        short_version = "main" if ac_major_version is None else f"{ac_major_version}"

        # Create a non unique PR branch name for work on this ac release branch.
        pr_branch_name = f"relbot/update-as/ac-{short_version}"

        try:
            pr_branch = ac_repo.get_branch(pr_branch_name)
            if pr_branch:
                log.warning(f"The PR branch {pr_branch_name} already exists. Exiting.")
                return
        except GithubException:
            # TODO Only ignore a 404 here, fail on others
            pass

        #
        # Create a new branch for this update
        #

        release_branch = ac_repo.get_branch(release_branch_name)
        log.info(f"Last commit on {release_branch_name} is {release_branch.commit.sha}")

        ac_repo.create_git_ref(
            ref=f"refs/heads/{pr_branch_name}", sha=release_branch.commit.sha
        )
        log.info(f"Created branch {pr_branch_name} on {release_branch.commit.sha}")

        _update_as_version(
            ac_repo,
            current_as_version,
            latest_as_version,
            pr_branch_name,
            author,
            ac_major_version,
        )

        #
        # Create the pull request
        #

        log.info("Creating pull request")
        pr = ac_repo.create_pull(
            title=f"Update to A-S {latest_as_version} on {release_branch_name}",
            body=f"This (automated) patch updates A-S to {latest_as_version}.",
            head=pr_branch_name,
            base=release_branch_name,
        )
        log.info(f"Pull request at {pr.html_url}")

        #
        # Leave a note for bors to run ui tests
        #

        log.info("Asking Bors to run a try build")
        issue = ac_repo.get_issue(pr.number)
        issue.create_comment("bors try")
    except Exception as e:
        # TODO Clean up the mess
        raise e


#
# High Level Tasks
#


#
# Update GeckoView Nightly, Release and Beta on A-C main. This will create three
# separate pull requests.
#


def update_main(ac_repo, author, dry_run):
    branch_name = "main"
    current_ac_version = get_current_ac_version(ac_repo, branch_name)
    ac_major_version = MobileVersion.parse(current_ac_version).major_number
    _update_application_services(
        ac_repo, branch_name, ac_major_version, author, dry_run
    )
    _update_geckoview(ac_repo, branch_name, ac_major_version, author, dry_run)


#
# Update GeckoView Release and Beta in all "relevant" A-C releases.
#


def update_releases(firefox_repo, author, dry_run):
    for ac_version in get_recent_fenix_versions(firefox_repo):
        release_branch_name = f"releases_v{ac_version}"
        _update_geckoview(
            firefox_repo, release_branch_name, ac_version, author, dry_run
        )
