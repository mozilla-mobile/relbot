# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


import datetime, sys

from util import *


#
# Helpers
#

def _update_ac_version(ac_repo, old_ac_version, new_ac_version, branch, author):
    contents = ac_repo.get_contents("version.txt", ref=branch)

    content = contents.decoded_content.decode("utf-8")
    new_content = content.replace(old_ac_version, new_ac_version)
    if content == new_content:
        raise Exception("Update to version.txt resulted in no changes: maybe the file was already up to date?")

    ac_repo.update_file(contents.path, f"Set version.txt to {new_ac_version}.", new_content,
                        contents.sha, branch=branch, author=author)


def _update_gv_version(ac_repo, old_gv_version, new_gv_version, branch, channel, author):
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
# Update GeckoView $gv_channel in A-C $ac_release. if ac_release is None then we
# update master. Otherwise it should be a major release version for which a
# release branch exists.
#

def _update_geckoview(ac_repo, fenix_repo, gv_channel, ac_major_version, author, debug, dry_run=False):
    try:
        if gv_channel not in ("nightly", "beta", "release"):
            raise Exception(f"Invalid channel {channel}")

        release_branch_name = "master" if ac_major_version is None else f"releases/{ac_major_version}.0"
        print(f"{ts()} Updating GeckoView {gv_channel.capitalize()} on A-C {release_branch_name}")

        current_gv_version = get_current_gv_version(ac_repo, release_branch_name, gv_channel)
        print(f"{ts()} Current GV {gv_channel.capitalize()} version in A-C is {current_gv_version}")

        current_gv_major_version = major_gv_version_from_version(current_gv_version)
        latest_gv_version = get_latest_gv_version(current_gv_major_version, gv_channel)
        print(f"{ts()} Latest GV {gv_channel.capitalize()} version available is {latest_gv_version}")

        if compare_gv_versions(current_gv_version, latest_gv_version) >= 0:
            print(f"{ts()} No newer GV {gv_channel.capitalize()} release found. Exiting.")
            return

        print(f"{ts()} We should update A-C {release_branch_name} with GV {gv_channel.capitalize()} {latest_gv_version}")

        if dry_run:
            print(f"{ts()} Dry-run so not continuing.")
            return

        #
        # Check if the branch already exists
        #

        short_version = "master" if ac_major_version is None else f"{ac_major_version}"

        # Create a non unique PR branch name for work on this ac release branch.
        pr_branch_name = f"relbot/ac-{short_version}"

        try:
            pr_branch = ac_repo.get_branch(pr_branch_name)
            if pr_branch:
                print(f"{ts()} The PR branch {pr_branch_name} already exists. Exiting.")
                return
        except GithubException as e:
            # TODO Only ignore a 404 here, fail on others
            pass

        #
        # Create a new branch for this update
        #

        release_branch = ac_repo.get_branch(release_branch_name)
        print(f"{ts()} Last commit on {release_branch_name} is {release_branch.commit.sha}")

        ac_repo.create_git_ref(ref=f"refs/heads/{pr_branch_name}", sha=release_branch.commit.sha)
        print(f"{ts()} Created branch {pr_branch_name} on {release_branch.commit.sha}")

        #
        # Update buildSrc/src/main/java/Gecko.kt
        #

        print(f"{ts()} Updating buildSrc/src/main/java/Gecko.kt")
        _update_gv_version(ac_repo, current_gv_version, latest_gv_version, pr_branch_name, gv_channel, author)

        #
        # If we are updating a release branch then update also update .buildConfig to increment
        # the patch version.
        #

        if release_branch_name != "master":
            current_ac_version = get_current_ac_version(ac_repo, release_branch_name)
            next_ac_version = get_next_ac_version(current_ac_version)

            print(f"{ts()} Create an A-C {next_ac_version} release with GV {gv_channel.capitalize()} {latest_gv_version}")

            print(f"{ts()} Updating .buildConfig.yml")
            _update_ac_version(ac_repo, current_ac_version, next_ac_version, pr_branch_name, author)

        #
        # Create the pull request
        #

        print(f"{ts()} Creating pull request")
        pr = ac_repo.create_pull(title=f"Update to GeckoView {gv_channel.capitalize()} {latest_gv_version} on {release_branch_name}",
                                 body=f"This (automated) patch updates GV {gv_channel.capitalize()} on master to {latest_gv_version}.",
                                 head=pr_branch_name, base=release_branch_name)
        print(f"{ts()} Pull request at {pr.html_url}")
    except Exception as e:
        # TODO Clean up the mess
        raise e


#
# High Level Tasks
#


#
# Update GeckoView Nightly, Release and Beta on A-C master. This will create three
# separate pull requests.
#

def update_master(ac_repo, fenix_repo, author, debug, dry_run):
    for gv_channel in ('nightly', 'beta', 'release'):
        try:
            _update_geckoview(ac_repo, fenix_repo, gv_channel, None, author, debug, dry_run)
        except Exception as e:
            print(f"{ts()} Exception while updating GeckoView {gv_channel.capitalize()} on A-C master: {str(e)}")
        print()

#
# Update GeckoView Release and Beta in all "relevant" A-C releases.
#

def update_releases(ac_repo, fenix_repo, author, debug, dry_run):
    for ac_version in get_relevant_ac_versions(fenix_repo, ac_repo):
        for gv_channel in ("beta", "release"):
            try:
                _update_geckoview(ac_repo, fenix_repo, gv_channel, ac_version, author, debug, dry_run)
            except Exception as e:
                print(f"{ts()} Exception while updating GeckoView {gv_channel.capitalize()} on A-C master: {str(e)}")
            print()


#
# Update GeckoView Beta in the currently most recent A-C release. This
# will result in a PR to update Gecko.kt and also a version increment
# in .buildconfig.yml
#

def update_geckoview_beta(ac_repo, fenix_repo, author, debug, dry_run):
    try:
        ac_major_version = discover_ac_major_version(ac_repo)
        _update_geckoview(ac_repo, fenix_repo, "beta", ac_major_version, author, debug, dry_run)
    except Exception as e:
        print(f"{ts()} Exception while updating GeckoView Beta on A-C master: {str(e)}")


#
# Update GeckoView Release in the currently most recent A-C release. This
# will result in a PR to update Gecko.kt and also a version increment
# in .buildconfig.yml
#

def update_geckoview_release(ac_repo, fenix_repo, author, debug, dry_run):
    try:
        ac_major_version = discover_ac_major_version(ac_repo)
        _update_geckoview(ac_repo, fenix_repo, "release", ac_major_version, author, debug, dry_run)
    except Exception as e:
        print(f"{ts()} Exception while updating GeckoView Release on A-C master: {str(e)}")


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
