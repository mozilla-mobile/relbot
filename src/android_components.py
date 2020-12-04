# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


import datetime, sys

from util import *


# Helpers

def update_ac_version(ac_repo, old_ac_version, new_ac_version, branch, author):
    contents = ac_repo.get_contents(".buildconfig.yml", ref=branch)
    content = contents.decoded_content.decode("utf-8")
    new_content = content.replace(f"componentsVersion: {old_ac_version}",
                                  f"componentsVersion: {new_ac_version}")
    if content == new_content:
        raise Exception("Update to .buildConfig.yml resulted in no changes: maybe the file was already up to date?")

    ac_repo.update_file(contents.path, f"Set version to {new_ac_version}.", new_content,
                     contents.sha, branch=branch, author=author)


def update_gv_version(ac_repo, old_gv_version, new_gv_version, branch, channel, author):
    if channel not in ("nightly", "beta", "release"):
        raise Exception(f"Invalid channel {channel}")

    contents = ac_repo.get_contents("buildSrc/src/main/java/Gecko.kt", ref=branch)
    content = contents.decoded_content.decode("utf-8")
    new_content = content.replace(f'{channel}_version = "{old_gv_version}"',
                                  f'{channel}_version = "{new_gv_version}"')
    if content == new_content:
        raise Exception("Update to Gecko.kt resulted in no changes: maybe the file was already up to date?")

    ac_repo.update_file(contents.path, f"Update GeckoView ({channel.capitalize()}) to {new_gv_version}.",
                     new_content, contents.sha, branch=branch, author=author)

#
# Update GeckoView Nightly on A-C master. This is a bit of a special
# case since it doesn't care about release branches. It can probably
# be refactored to share more code with update_geckoview() though.
#

def update_geckoview_nightly(ac_repo, fenix_repo, author, debug):
    try:
        channel = "nightly"
        release_branch_name = "master"

        current_gv_version = get_current_gv_version(ac_repo, release_branch_name, channel)
        current_gv_major_version = major_gv_version_from_version(current_gv_version)
        latest_gv_version = get_latest_gv_version(current_gv_major_version, channel)

        #
        # Create a new branch for this update
        #

        release_branch = ac_repo.get_branch(release_branch_name)
        print(f"{ts()} Last commit on {release_branch_name} is {release_branch.commit.sha}")

        pr_branch_name = f"GV-Nightly-{latest_gv_version}"
        ac_repo.create_git_ref(ref=f"refs/heads/{pr_branch_name}", sha=release_branch.commit.sha)
        print(f"{ts()} Created branch {pr_branch_name} on {release_branch.commit.sha}")

        #
        # Update buildSrc/src/main/java/Gecko.kt
        #

        print(f"{ts()} Updating buildSrc/src/main/java/Gecko.kt")
        update_gv_version(ac_repo, current_gv_version, latest_gv_version, pr_branch_name, channel, author)

        #
        # Create the pull request
        #

        print(f"{ts()} Creating pull request")
        pr = ac_repo.create_pull(title=f"GeckoView ({channel.capitalize()}) {latest_gv_version}",
                                 body=f"This (automated) patch updates GV {channel.capitalize()} on master to {latest_gv_version}.",
                                 head=pr_branch_name, base=release_branch_name)
        print(f"{ts()} Pull request at {pr.html_url}")
    except Exception as e:
        print(f"{ts()} Exception: {str(e)}")
        raise e
        # TODO Clean up the mess


#
# Update geckoview in the latest A-C release.
#

def update_geckoview(ac_repo, fenix_repo, channel, author, debug):
    try:
        ac_major_version = discover_ac_major_version(ac_repo)
        gv_major_version = discover_gv_major_version()
        release_branch_name = f"releases/{ac_major_version}.0"
        current_ac_version = get_current_ac_version(ac_repo, release_branch_name)
        current_gv_version = get_current_gv_version(ac_repo, release_branch_name, channel)
        latest_gv_version = get_latest_gv_version(gv_major_version, channel)

        if not latest_gv_version.startswith(f"{gv_major_version}."):
            raise Exception(f"Latest GV {channel.capitalize()} is not same major release. Exiting.")

        if compare_gv_versions(current_gv_version, latest_gv_version) >= 0:
            raise Exception(f"No newer GV {channel.capitalize()} release found. Exiting.")

        next_ac_version = get_next_ac_version(current_ac_version)
        print(f"{ts()} We should create an A-C {next_ac_version} release with GV {channel.capitalize()} {latest_gv_version}")

        pr_branch_name = f"GV-Beta-{latest_gv_version}"

        try:
            pr_branch = ac_repo.get_branch(pr_branch_name)
            if pr_branch:
                raise Exception(f"The PR branch {pr_branch_name} already exists. Exiting.")
        except GithubException as e:
            pass
        #
        # Create a new branch for this update
        #

        release_branch = ac_repo.get_branch(release_branch_name)
        print(f"{ts()} Last commit on {release_branch_name} is {release_branch.commit.sha}")

        ac_repo.create_git_ref(ref=f"refs/heads/{pr_branch_name}", sha=release_branch.commit.sha)
        print(f"{ts()} Created branch {pr_branch_name} on {release_branch.commit.sha}")

        #
        # Update .buildConfig and buildSrc/src/main/java/Gecko.kt
        #

        print(f"{ts()} Updating .buildConfig.yml")
        update_ac_version(ac_repo, current_ac_version, next_ac_version, pr_branch_name, author)

        print(f"{ts()} Updating buildSrc/src/main/java/Gecko.kt")
        update_gv_version(ac_repo, current_gv_version, latest_gv_version, pr_branch_name, channel, author)

        #
        # Create the pull request
        #

        print(f"{ts()} Creating pull request")
        pr = ac_repo.create_pull(title=f"Version {next_ac_version} with GV {channel.capitalize()} {latest_gv_version}.",
                         body=f"This (automated) patch updates GV {channel.capitalize()} to {latest_gv_version}.",
                         head=pr_branch_name, base=release_branch_name)
        pr.add_to_labels("🛬 needs landing")
        print(f"{ts()} Pull request at {pr.html_url}")
    except Exception as e:
        print(f"{ts()} Exception: {str(e)}")
        # TODO Clean up the mess


#
# Create an Android-Components release on the current release branch,
# if it does not already exist. The logic is as follows:
#
#  - Determine the latest release branch (currently hardcoded)
#  - Check the version by looking at .buildconfig.yaml
#  - If no github release exists, create it
#
# This basically means the trigger for a release is a change of the
# `componentsVersion` field in `.buildconfig.yml`.
#
# This can be run periodically, manually or triggered by a change
# on .builconfig.yml.
#
# TODO Instead of looking at the latest release branch, check all
# relevant branches - those used by live products?
#

def create_release(ac_repo, fenix_repo, author, debug):
    ac_major_version = discover_ac_major_version(ac_repo)
    release_branch_name = f"releases/{ac_major_version}.0"
    current_version = get_current_ac_version(ac_repo, release_branch_name)
    release_branch = ac_repo.get_branch(release_branch_name)

    if current_version.endswith(".0"):
        print(f"{ts()} Current version {current_version} is not a dot release. Exiting. ")
        sys.exit(0)

    print(f"{ts()} Checking if android-components release {current_version} already exists.")

    releases = get_recent_ac_releases(ac_repo)
    if len(releases) == 0:
        print(f"{ts()} No releases found. Exiting. ")
        sys.exit(0)

    if current_version in releases:
        print(f"{ts()} Release {current_version} already exists. Exiting. ")
        sys.exit(0)

    print(f"{ts()} Creating android-components release {current_version}")
    ac_repo.create_git_tag_and_release(f"v{current_version}", current_version,
        current_version, f"Release {current_version}", release_branch.commit.sha, "commit")

