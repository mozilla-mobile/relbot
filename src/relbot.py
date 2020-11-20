#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/

#
# First iteration: requires some manual configuration:
#
#  AC_MAJOR_VERSION
#  GV_MAJOR_VERSION
#
# General strategy to make this code robust:
#
#  * factor out mini tasks into functions
#  * main code should be as simple as possible
#  * check pre-conditions
#  * validate all the things
#  * throw an exception when something unexpected happens
#  * clean up in the finally block
#


import os, sys

from github import Github, InputGitAuthor, enable_console_debug_logging

import android_components, fenix


DEFAULT_ORGANIZATION = "st3fan"
DEFAULT_AUTHOR_NAME = "Stefan Arentz"
DEFAULT_AUTHOR_EMAIL = "stefan@arentz.ca"


def main(argv, ac_repo, fenix_repo, author, debug=False):
    if len(argv) < 2:
        print("usage: relbot <android-components|fenix> command...")
        sys.exit(1)

    # Android Components
    if argv[1] == "android-components":
        if argv[2] == "update-geckoview-beta":
            android_components.update_geckoview(ac_repo, fenix_repo, "beta", author, debug)
        elif argv[2] == "update-geckoview-release":
            android_components.update_geckoview(ac_repo, fenix_repo, "release", author, debug)
        elif argv[2] == "create-release":
            android_components.create_release(ac_repo, fenix_repo, author, debug)
        else:
            print("usage: relbot android-components <update-geckoview-beta|update-geckoview-release|create-release>")
            sys.exit(1)

    # Fenix
    elif argv[1] == "fenix":
        if argv[2] == "update-android-components":
            fenix.update_android_components(ac_repo, fenix_repo, author, debug)
        elif argv[2] == "create-fenix-release":
            fenix.create_release(ac_repo, fenix_repo, author, debug)
        else:
            print("usage: relbot fenix <update-android-components|create-release>")
            sys.exit(1)

    else:
        print("usage: relbot <android-components|fenix> command...")
        sys.exit(1)


if __name__ == "__main__":

    debug = os.getenv("DEBUG") is not None
    if debug:
        enable_console_debug_logging()

    github_access_token = os.getenv("GITHUB_TOKEN")
    if not github_access_token:
        print("No GITHUB_TOKEN set. Exiting.")
        sys.exit(1)

    github = Github(github_access_token)
    if github.get_user() is None:
        print("Could not get authenticated user. Exiting.")
        sys.exit(1)

    organization = os.getenv("GITHUB_ORGANIZATION") or DEFAULT_ORGANIZATION

    ac_repo = github.get_repo(f"{organization}/android-components")
    fenix_repo = github.get_repo(f"{organization}/fenix")

    author_name = os.getenv("AUTHOR_NAME") or DEFAULT_AUTHOR_NAME
    author_email = os.getenv("AUTHOR_EMAIL") or DEFAULT_AUTHOR_EMAIL
    author = InputGitAuthor(author_name, author_email)

    print(f"This is relbot working on https://github.com/{organization} as {author_email} / {author_name}")

    main(sys.argv, ac_repo, fenix_repo, author, debug)
