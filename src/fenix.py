# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/

import logging

from util import *

log = logging.getLogger(__name__)


# For the current Fenix versions, find out if there is
# a newer android-components that can be pulled in.
def update_android_components(ac_repo, fenix_repo, author, debug, dry_run):
    update_android_components_nightly(
        ac_repo,
        fenix_repo,
        target_path="",
        author=author,
        debug=debug,
        release_branch_name="main",
        dry_run=dry_run,
    )
    for fenix_version in get_recent_fenix_versions(fenix_repo):
        release_branch_name = f"releases_v{fenix_version}.0.0"
        update_android_components_release(
            ac_repo,
            fenix_repo,
            target_path="",
            target_product="fenix",
            target_branch=release_branch_name,
            major_version=fenix_version,
            author=author,
            debug=debug,
            dry_run=dry_run,
        )
