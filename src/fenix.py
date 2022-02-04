# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


from util import *


# For the current Fenix release and beta version, find out if there is
# a newer android-components that can be pulled in.
#
def update_android_components(ac_repo, fenix_repo, author, debug, dry_run):
    for fenix_version in get_recent_fenix_versions(fenix_repo):
        release_branch_name = f"releases_v{fenix_version}.0.0"
        try:
            update_android_components_release(
                ac_repo,
                fenix_repo,
                "fenix",
                release_branch_name,
                fenix_version,
                author,
                debug,
                dry_run,
            )
        except Exception as e:
            print(f"{ts()} Failed to update A-C in Fenix {fenix_version}: {str(e)}")
