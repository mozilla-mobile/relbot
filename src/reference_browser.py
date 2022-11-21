# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


from util import *


def update_android_components_in_rb(ac_repo, rb_repo, author, debug):
    release_branch_name = "master"  # RB Only has master

    return update_android_components_nightly(
        ac_repo,
        rb_repo,
        target_path="",
        author=author,
        debug=debug,
        release_branch_name=release_branch_name,
        dry_run=False,
    )
