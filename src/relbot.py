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


import logging
import os
import sys

from github import Github, InputGitAuthor, enable_console_debug_logging

import android_components
import reference_browser

log = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s.%(funcName)s:%(lineno)s - %(levelname)s - %(message)s",  # noqa E501
    level=logging.INFO,
)


DEFAULT_ORGANIZATION = "st3fan"
DEFAULT_AUTHOR_NAME = "MickeyMoz"
DEFAULT_AUTHOR_EMAIL = "sebastian@mozilla.com"
USAGE = "usage: relbot <android-components|reference-browser> command..."  # noqa E501


def main(
    argv, firefox_repo, rb_repo, author, debug=False, dry_run=False
):
    if len(argv) < 2:
        print(USAGE)
        sys.exit(1)

    # Android Components
    if argv[1] == "android-components":
        if argv[2] == "update-main":
            android_components.update_main(firefox_repo, author, dry_run)
        elif argv[2] == "update-releases":
            android_components.update_releases(firefox_repo, author, dry_run)
        else:
            print(
                "usage: relbot android-components <update-{main,releases}>"  # noqa E501
            )
            sys.exit(1)

    # Reference Browser
    elif argv[1] == "reference-browser":
        if argv[2] == "update-android-components":
            reference_browser.update_android_components_in_rb(
                firefox_repo, rb_repo, author, debug
            )
        else:
            print("usage: relbot reference-browser <update-android-components>")
            sys.exit(1)

    else:
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    debug = os.getenv("DEBUG") is not None
    if debug:
        enable_console_debug_logging()

    github_access_token = os.getenv("GITHUB_TOKEN")
    if not github_access_token:
        log.error("No GITHUB_TOKEN set. Exiting.")
        sys.exit(1)

    github = Github(github_access_token)
    if github.get_user() is None:
        log.error("Could not get authenticated user. Exiting.")
        sys.exit(1)

    dry_run = os.getenv("DRY_RUN") == "True"

    organization = os.getenv("GITHUB_REPOSITORY_OWNER") or DEFAULT_ORGANIZATION

    repo_name_prefix = "staging-" if organization == "mozilla-releng" else ""

    firefox_repo = github.get_repo(f"{organization}/{repo_name_prefix}firefox-android")
    rb_repo = github.get_repo(f"{organization}/{repo_name_prefix}reference-browser")

    author_name = os.getenv("AUTHOR_NAME") or DEFAULT_AUTHOR_NAME
    author_email = os.getenv("AUTHOR_EMAIL") or DEFAULT_AUTHOR_EMAIL
    author = InputGitAuthor(author_name, author_email)

    log.info(
        f"This is relbot working on https://github.com/{organization} "
        f"as {author_email} / {author_name}"
    )

    main(sys.argv, firefox_repo, rb_repo, author, debug, dry_run)
