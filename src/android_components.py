# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


import datetime, sys

from util import *


#
# Helpers
#

def _update_ac_buildconfig(ac_repo, old_ac_version, new_ac_version, branch, author):
    contents = ac_repo.get_contents(".buildconfig.yml", ref=branch)

    content = contents.decoded_content.decode("utf-8")
    new_content = re.sub(r"componentsVersion: \d+\.\d+\.\d+", f"componentsVersion: {new_ac_version}", content)
    if content == new_content:
        print(f"{ts()} Update to .buildConfig.yml resulted in no changes: maybe the file was already up to date?")

    ac_repo.update_file(contents.path, f"Set version to {new_ac_version}.", new_content,
                     contents.sha, branch=branch, author=author)


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


def _update_gv_version_new(ac_repo, old_gv_version, new_gv_version, branch, channel, author):
    contents = ac_repo.get_contents("buildSrc/src/main/java/Gecko.kt", ref=branch)
    content = contents.decoded_content.decode("utf-8")
    new_content = content.replace(f'const val version = "{old_gv_version}"',
                                  f'const val version = "{new_gv_version}"')
    if content == new_content:
        raise Exception("Update to Gecko.kt resulted in no changes: maybe the file was already up to date?")

    ac_repo.update_file(contents.path, f"Update GeckoView ({channel.capitalize()}) to {new_gv_version}.",
                     new_content, contents.sha, branch=branch, author=author)


def _update_as_version(ac_repo, old_as_version, new_as_version, branch, author):
    contents = ac_repo.get_contents("buildSrc/src/main/java/Dependencies.kt", ref=branch)
    content = contents.decoded_content.decode("utf-8")
    new_content = content.replace(f'mozilla_appservices = "{old_as_version}"',
                                  f'mozilla_appservices = "{new_as_version}"')
    if content == new_content:
        raise Exception("Update to Dependencies.kt resulted in no changes: maybe the file was already up to date?")

    ac_repo.update_file(contents.path, f"Update A-S to {new_as_version}.",
                     new_content, contents.sha, branch=branch, author=author)


#
# Update GeckoView $gv_channel in A-C $ac_release. if ac_release is None then we
# update master. Otherwise it should be a major release version for which a
# release branch exists.
#

def _update_geckoview_new(ac_repo, fenix_repo, ac_major_version, author, debug, dry_run=False):
    try:
        if ac_major_version != "master":
            raise Exception(f"Unsupported A-C Version {ac_major_version}. This is work in progress.")

        release_branch_name = "master" if ac_major_version is "master" else f"releases/{ac_major_version}.0"
        print(f"{ts()} Updating GeckoView on A-C {ac_repo.full_name}:{release_branch_name}")

        gv_channel = get_current_gv_channel(ac_repo, release_branch_name)
        print(f"{ts()} Current GV channel is {gv_channel}")

        current_gv_version = get_current_gv_version_new(ac_repo, release_branch_name)
        print(f"{ts()} Current GV {gv_channel.capitalize()} version in A-C {ac_repo.full_name}:{release_branch_name} is {current_gv_version}")

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

        short_version = "master" if ac_major_version is "master" else f"{ac_major_version}"

        # Create a non unique PR branch name for work on this ac release branch.
        pr_branch_name = f"relbot/upgrade-geckoview-ac-{short_version}"

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
        _update_gv_version_new(ac_repo, current_gv_version, latest_gv_version, pr_branch_name, gv_channel, author)

        #
        # If we are updating a release branch then update also update
        # version.txt to increment the patch version.
        #

        if release_branch_name != "master":
            current_ac_version = get_current_ac_version(ac_repo, release_branch_name)
            next_ac_version = get_next_ac_version(current_ac_version)

            print(f"{ts()} Create an A-C {next_ac_version} release with GV {gv_channel.capitalize()} {latest_gv_version}")

            print(f"{ts()} Updating version.txt")
            _update_ac_version(ac_repo, current_ac_version, next_ac_version, pr_branch_name, author)

            # TODO Also update buildconfig until we do not need it anymore
            print(f"{ts()} Updating buildconfig.yml")
            _update_ac_buildconfig(ac_repo, current_ac_version, next_ac_version, pr_branch_name, author)

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
        # If we are updating a release branch then update also update
        # version.txt to increment the patch version.
        #

        if release_branch_name != "master":
            current_ac_version = get_current_ac_version(ac_repo, release_branch_name)
            next_ac_version = get_next_ac_version(current_ac_version)

            print(f"{ts()} Create an A-C {next_ac_version} release with GV {gv_channel.capitalize()} {latest_gv_version}")

            print(f"{ts()} Updating version.txt")
            _update_ac_version(ac_repo, current_ac_version, next_ac_version, pr_branch_name, author)

            # TODO Also update buildconfig until we do not need it anymore
            print(f"{ts()} Updating buildconfig.yml")
            _update_ac_buildconfig(ac_repo, current_ac_version, next_ac_version, pr_branch_name, author)

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


def _update_application_services(ac_repo, fenix_repo, ac_major_version, author, debug, dry_run=False):
    try:
        release_branch_name = "master" if ac_major_version is None else f"releases/{ac_major_version}.0"
        print(f"{ts()} Updating A-S on {ac_repo.full_name}:{release_branch_name}")

        current_as_version = get_current_as_version(ac_repo, release_branch_name)
        print(f"{ts()} Current A-S version on A-C {release_branch_name} is {current_as_version}")

        latest_as_version = get_latest_as_version(major_as_version_from_version(current_as_version))
        print(f"{ts()} Latest A-S version available is {latest_as_version}")

        if compare_as_versions(current_as_version, latest_as_version) >= 0:
            print(f"{ts()} No newer A-S release found. Exiting.")
            return

        print(f"{ts()} We should update A-C {release_branch_name} with A-S {latest_as_version}")

        if dry_run:
            print(f"{ts()} Dry-run so not continuing.")
            return

        #
        # Check if the branch already exists
        #

        short_version = "master" if ac_major_version is None else f"{ac_major_version}"

        # Create a non unique PR branch name for work on this ac release branch.
        pr_branch_name = f"relbot/update-as/ac-{short_version}"

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

        print(f"{ts()} Updating buildSrc/src/main/java/Dependencies.kt")
        _update_as_version(ac_repo, current_as_version, latest_as_version, pr_branch_name, author)

        #
        # Create the pull request
        #

        print(f"{ts()} Creating pull request")
        pr = ac_repo.create_pull(title=f"Update to A-S {latest_as_version} on {release_branch_name}",
                                 body=f"This (automated) patch updates A-S to {latest_as_version}.",
                                 head=pr_branch_name, base=release_branch_name)
        print(f"{ts()} Pull request at {pr.html_url}")

        #
        # Leave a note for bors to run ui tests
        #

        print(f"{ts()} Asking Bors to run a try build")
        issue = ac_repo.get_issue(pr.number)
        issue.create_comment("bors try")
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
    try:
        _update_application_services(ac_repo, fenix_repo, None, author, debug, dry_run)
    except Exception as e:
        print(f"{ts()} Exception while updating A-S on A-C {ac_repo.full_name}:master: {str(e)}")

    try:
        _update_geckoview_new(ac_repo, fenix_repo, "master", author, debug, dry_run)
    except Exception as e:
        print(f"{ts()} Exception while updating GeckoView on A-C {ac_repo.full_name}:master: {str(e)}")

#
# Update GeckoView Release and Beta in all "relevant" A-C releases.
#

def update_releases(ac_repo, fenix_repo, author, debug, dry_run):
    for ac_version in get_relevant_ac_versions(fenix_repo, ac_repo):
        # TODO This is disabled for now so that we can test this code on A-C Nightly first.
        # try:
        #     _update_application_services(ac_repo, fenix_repo, ac_version, author, debug, dry_run)
        # except Exception as e:
        #     print(f"{ts()} Exception while updating A-S on A-C {ac_version}: {str(e)}")

        for gv_channel in ("beta", "release"):
            try:
                _update_geckoview(ac_repo, fenix_repo, gv_channel, ac_version, author, debug, dry_run)
            except Exception as e:
                print(f"{ts()} Exception while updating GeckoView {gv_channel.capitalize()} on A-C master: {str(e)}")


#
# Create an Android-Components release on the current release branch,
# if it does not already exist. The logic is as follows:
#
#  - Determine the "relevant" release branches
#  - Check the version by looking at version.txt
#  - If no github release exists, create it
#
# This basically means the trigger for a release is a change of the
# version.txt file.
#
# This can be run periodically, manually or triggered by a change
# on version.txt.
#
# TODO Instead of looking at the latest release branch, check all
# relevant branches - those used by live products?
#

def _create_release(ac_repo, fenix_repo, ac_major_version, author, debug, dry_run):
    release_branch_name = f"releases/{ac_major_version}.0"
    current_version = get_current_ac_version(ac_repo, release_branch_name)
    release_branch = ac_repo.get_branch(release_branch_name)

    if current_version.endswith(".0"):
        print(f"{ts()} Current version {current_version} is not a dot release. Exiting. ")
        return

    print(f"{ts()} Checking if android-components release {current_version} already exists.")

    releases = get_recent_ac_releases(ac_repo)
    if len(releases) == 0:
        print(f"{ts()} No releases found. Exiting. ")
        return

    if current_version in releases:
        print(f"{ts()} Release {current_version} already exists. Exiting. ")
        return

    print(f"{ts()} Creating android-components release {current_version}")

    if dry_run:
        print(f"{ts()} Dry-run so not continuing.")
        return

    ac_repo.create_git_tag_and_release(f"v{current_version}", current_version,
        current_version, f"Release {current_version}", release_branch.commit.sha, "commit")


def create_releases(ac_repo, fenix_repo, author, debug, dry_run):
    for ac_version in get_relevant_ac_versions(fenix_repo, ac_repo):
        try:
            _create_release(ac_repo, fenix_repo, ac_version, author, debug, dry_run)
        except Exception as e:
            print(f"{ts()} Exception while creating Android-Components release for {ac_version}: {str(e)}")
        print()
