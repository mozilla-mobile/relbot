# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


from util import *


def _update_ac_version(fenix_repo, fenix_branch, old_ac_version, new_ac_version, author):
    if channel not in ("beta", "release"):
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
# For the current Fenix release and beta version, find out if there is
# a newer android-components that can be pulled in.
#

def update_android_components(ac_repo, fenix_repo, author, debug):
    print(f"{ts()} Updating A-C in Fenix")
    for channel in ("beta", "release"):
        fenix_major_version = discover_fenix_major_version(channel)
        fenix_branch = f"releases/v{fenix_major_version}.0.0"
        print(f"{ts()} Looking at Fenix {channel.capitalize()} on {fenix_branch}")

        current_ac_version = get_current_ac_version_in_fenix(fenix_repo, fenix_branch)
        print(f"{ts()} Current A-C version is {current_ac_version}")

        ac_major_version = int(current_ac_version[0:2]) # TODO Util & Test!
        latest_ac_version = get_latest_ac_version_for_major_version(ac_repo, ac_major_version)

        if latest_ac_version > current_ac_version:
            print(f"{ts()} Should upgrade to {latest_ac_version}")
            #_update_ac_version(fenix_repo, fenix_branch, current_ac_version, latest_ac_version, author)
        else:
            print(f"{ts()} No need to upgrade; Fenix {channel.capitalize()} is on A-C {current_ac_version}")



def create_release(ac_repo, fenix_repo, author, debug):
    print("Creating Fenix Release")
