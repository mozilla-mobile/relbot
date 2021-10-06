# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


from util import *


def _update_ac_version(fenix_repo, branch, old_ac_version, new_ac_version, author):
    contents = fenix_repo.get_contents(
        "buildSrc/src/main/java/AndroidComponents.kt", ref=branch
    )
    content = contents.decoded_content.decode("utf-8")
    new_content = content.replace(
        f'VERSION = "{old_ac_version}"', f'VERSION = "{new_ac_version}"'
    )
    if content == new_content:
        raise Exception(
            "Update to AndroidComponents.kt resulted in no changes: maybe the file was already up to date?"
        )
    fenix_repo.update_file(
        contents.path,
        f"Update to Android-Components {new_ac_version}.",
        new_content,
        contents.sha,
        branch=branch,
        author=author,
    )


#
# For the current Fenix release and beta version, find out if there is
# a newer android-components that can be pulled in.
#


def update_android_components_in_fenix(
    ac_repo, fenix_repo, fenix_major_version, author, debug, dry_run
):
    print(f"{ts()} Looking at Fenix {fenix_major_version}")

    # Make sure the release branch for this version exists
    # TODO Temporary fix for transition between branch name conventions
    release_branch_name = (
        f"releases/v{fenix_major_version}.0.0"
        if fenix_major_version < 85
        else f"releases_v{fenix_major_version}.0.0"
    )
    release_branch = fenix_repo.get_branch(release_branch_name)

    print(f"{ts()} Looking at Fenix {fenix_major_version} on {release_branch_name}")

    current_ac_version = get_current_ac_version_in_fenix(
        fenix_repo, release_branch_name
    )
    print(f"{ts()} Current A-C version in Fenix is {current_ac_version}")

    ac_major_version = int(current_ac_version[0:2])  # TODO Util & Test!
    latest_ac_version = get_latest_ac_version(ac_major_version)
    print(f"{ts()} Latest A-C version available is {latest_ac_version}")

    if (
        len(current_ac_version) != 19
        and compare_ac_versions(current_ac_version, latest_ac_version) >= 0
    ):
        print(
            f"{ts()} No need to upgrade; Fenix {fenix_major_version} is on A-C {current_ac_version}"
        )
        return

    print(
        f"{ts()} We are going to upgrade Fenix {fenix_major_version} to Android-Components {latest_ac_version}"
    )

    if dry_run:
        print(f"{ts()} Dry-run so not continuing.")
        return

    # Create a non unique PR branch name for work on this fenix release branch.
    pr_branch_name = f"relbot/fenix-{fenix_major_version}"

    try:
        pr_branch = fenix_repo.get_branch(pr_branch_name)
        if pr_branch:
            print(f"{ts()} The PR branch {pr_branch_name} already exists. Exiting.")
            return
    except GithubException as e:
        # TODO Only ignore a 404 here, fail on others
        pass

    print(f"{ts()} Last commit on {release_branch_name} is {release_branch.commit.sha}")

    print(f"{ts()} Creating branch {pr_branch_name} on {release_branch.commit.sha}")
    fenix_repo.create_git_ref(
        ref=f"refs/heads/{pr_branch_name}", sha=release_branch.commit.sha
    )

    print(
        f"{ts()} Updating AndroidComponents.kt from {current_ac_version} to {latest_ac_version} on {pr_branch_name}"
    )
    _update_ac_version(
        fenix_repo, pr_branch_name, current_ac_version, latest_ac_version, author
    )

    print(f"{ts()} Creating pull request")
    pr = fenix_repo.create_pull(
        title=f"Update to Android-Components {latest_ac_version}.",
        body=f"This (automated) patch updates Android-Components to {latest_ac_version}.",
        head=pr_branch_name,
        base=release_branch_name,
    )
    print(f"{ts()} Pull request at {pr.html_url}")


def update_android_components(ac_repo, fenix_repo, author, debug, dry_run):
    for fenix_version in get_recent_fenix_versions(fenix_repo):
        try:
            update_android_components_in_fenix(
                ac_repo, fenix_repo, fenix_version, author, debug, dry_run
            )
        except Exception as e:
            print(f"{ts()} Failed to update A-C in Fenix {fenix_version}: {str(e)}")


def create_release(ac_repo, fenix_repo, author, debug, dry_run):
    print("Creating Fenix Release")
