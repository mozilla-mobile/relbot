# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


from util import *


def _update_ac_version(rb_repo, branch, old_ac_version, new_ac_version, author):
    contents = rb_repo.get_contents("buildSrc/src/main/java/AndroidComponents.kt", ref=branch)
    content = contents.decoded_content.decode("utf-8")
    new_content = content.replace(f'VERSION = "{old_ac_version}"', f'VERSION = "{new_ac_version}"')
    if content == new_content:
        raise Exception("Update to AndroidComponents.kt resulted in no changes: maybe the file was already up to date?")
    rb_repo.update_file(contents.path, f"Update to Android-Components {new_ac_version}.",
                        new_content, contents.sha, branch=branch, author=author)


def update_android_components(ac_repo, rb_repo, author, debug):
    release_branch_name = "master" # RB Only has master

    current_ac_version = get_current_ac_version_in_reference_browser(rb_repo, release_branch_name)
    print(f"{ts()} Current A-C version in R-B is {current_ac_version}")

    ac_major_version = major_ac_version_from_version(current_ac_version)

    latest_ac_nightly_version = get_latest_ac_nightly_version()

    if compare_ac_versions(current_ac_version, latest_ac_nightly_version) >= 0:
        print(f"{ts()} No need to upgrade; Reference-Browser is on A-C {current_ac_version}")
        return

    print(f"{ts()} We should upgrade Reference Browser to Android-Components {latest_ac_nightly_version}")

    pr_branch_name = f"relbot/AC-Nightly-{latest_ac_nightly_version}"

    try:
        if pr_branch := rb_repo.get_branch(pr_branch_name):
            print(f"{ts()} The PR branch {pr_branch_name} already exists. Exiting.")
            return
    except GithubException as e:
        pass

    release_branch = rb_repo.get_branch(release_branch_name)
    print(f"{ts()} Last commit on {release_branch_name} is {release_branch.commit.sha}")

    print(f"{ts()} Creating branch {pr_branch_name} on {release_branch.commit.sha}")
    rb_repo.create_git_ref(ref=f"refs/heads/{pr_branch_name}", sha=release_branch.commit.sha)

    print(f"{ts()} Updating AndroidComponents.kt from {current_ac_version} to {latest_ac_nightly_version} on {pr_branch_name}")
    _update_ac_version(rb_repo, pr_branch_name, current_ac_version, latest_ac_nightly_version, author)

    print(f"{ts()} Creating pull request")
    pr = rb_repo.create_pull(title=f"Update to Android-Components {latest_ac_nightly_version}.",
                                body=f"This (automated) patch updates Android-Components to {latest_ac_nightly_version}.",
                                head=pr_branch_name, base=release_branch_name)
    print(f"{ts()} Pull request at {pr.html_url}")
