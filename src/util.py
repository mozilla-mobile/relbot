# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


import json
import logging
import os.path
import re
from urllib.parse import quote_plus

import requests
import xmltodict
from github import GithubException
from mozilla_version.mobile import MobileVersion

log = logging.getLogger(__name__)


def get_gecko_file_path(ac_major_version):
    """Return the file path to Gecko.kt"""
    return "android-components/plugins/dependencies/src/main/java/Gecko.kt"


def get_dependencies_file_path(ac_major_version):
    """Return the file path to dependencies file"""
    return "android-components/plugins/dependencies/src/main/java/DependenciesPlugin.kt"


def get_app_services_version_path(ac_major_version):
    """Return the file path to dependencies file"""
    return (
        "android-components/plugins/dependencies/src/main/java/ApplicationServices.kt"
    )


def validate_gv_version(v):
    """Validate that v is in the format of 82.0.20201027185343.
    Returns v or raises an exception."""
    if not re.match(r"^\d{2,}\.\d\.\d{14}$", v):
        raise Exception(f"Invalid GV version {v}")
    return v


def validate_gv_channel(c):
    """Validate that c is release, production or beta"""
    if c not in ("release", "beta", "nightly"):
        raise Exception(f"Invalid GV channel {c}")
    return c


def major_gv_version_from_version(v):
    """Return the major version for the given GV version"""
    c = validate_gv_version(v).split(".")
    return c[0]


def match_ac_version(src):
    if match := re.compile(r'VERSION = "([^"]*)"', re.MULTILINE).search(src):
        version = match[1]
        MobileVersion.parse(version)
        return version
    raise Exception("Could not match the VERSION in AndroidComponents.kt")


def get_current_embedded_ac_version(repo, release_branch_name, target_path=""):
    """Return the current A-C version used on the given branch"""
    content_file = repo.get_contents(
        f"{target_path}buildSrc/src/main/java/AndroidComponents.kt",
        ref=release_branch_name,
    )
    return match_ac_version(content_file.decoded_content.decode("utf8"))


def match_gv_version(src):
    """Find the GeckoView version in the contents of the given Gecko.kt file."""
    if match := re.compile(r'version\(?\)? = "([^"]*)"', re.MULTILINE).search(src):
        return validate_gv_version(match[1])
    raise Exception("Could not match the version in Gecko.kt")


def get_current_gv_version(ac_repo, release_branch_name, ac_major_version):
    """Return the current gv version used on the given release branch"""
    content_file = ac_repo.get_contents(
        get_gecko_file_path(ac_major_version), ref=release_branch_name
    )
    return match_gv_version(content_file.decoded_content.decode("utf8"))


def match_gv_channel(src):
    """Find the GeckoView channel in the contents of the given Gecko.kt file."""
    if match := re.compile(
        r"channel\(?\)? = GeckoChannel.(NIGHTLY|BETA|RELEASE)", re.MULTILINE
    ).search(src):
        return validate_gv_channel(match[1].lower())
    raise Exception("Could not match the channel in Gecko.kt")


def get_current_gv_channel(ac_repo, release_branch_name, ac_major_version):
    """Return the current gv channel used on the given release branch"""
    content_file = ac_repo.get_contents(
        get_gecko_file_path(ac_major_version), ref=release_branch_name
    )
    return match_gv_channel(content_file.decoded_content.decode("utf8"))


def get_current_ac_version(repo, release_branch_name):
    """Return the current ac version used on the given release branch"""
    content_file = repo.get_contents("version.txt", ref=release_branch_name)
    content = content_file.decoded_content.decode("utf8")
    ac_version = content.strip()
    MobileVersion.parse(ac_version)
    log.info(f"Fetched A-C version {ac_version} from {repo.full_name}")
    return ac_version


def get_latest_ac_version_for_major_version(ac_repo, ac_major_version):
    return get_current_ac_version(ac_repo, f"releases_v{ac_major_version}")


MAVEN = "https://maven.mozilla.org/maven2"


def taskcluster_indexed_artifact_url(index_name, artifact_path):
    artifact_path = quote_plus(artifact_path)
    return (
        "https://firefox-ci-tc.services.mozilla.com/"
        f"api/index/v1/task/{index_name}/artifacts/{artifact_path}"
    )


def get_latest_glean_version(gv_version, channel):
    name = "geckoview"
    if channel != "release":
        name += "-" + channel
    # A-C builds against geckoview-omni
    # See https://github.com/mozilla-mobile/android-components/commit/0b349f48c91a50bb7b4ffbf40c6c122ed18142d3  # noqa E501
    name += "-omni"

    r = requests.get(
        f"{MAVEN}/org/mozilla/geckoview/{name}/{gv_version}/{name}-{gv_version}.module"
    )
    r.raise_for_status()
    module_data = json.loads(r.text)

    caps = module_data["variants"][0]["capabilities"]
    versions = [
        c["version"]
        for c in caps
        if c["group"] == "org.mozilla.telemetry" and c["name"] == "glean-native"
    ]

    if len(versions) != 1:
        raise Exception(
            "Could not find unique glean-native capability for "
            f"GeckoView {channel.capitalize()} {gv_version}"
        )

    return versions[0]


def get_latest_gv_version(gv_major_version, channel):
    """Find the last geckoview beta release version on Maven
    for the given major version"""
    if channel not in ("nightly", "beta", "release"):
        raise Exception(f"Invalid channel {channel}")

    # Find the latest release in the multi-arch .aar

    name = "geckoview"
    if channel != "release":
        name += "-" + channel
    # A-C builds against geckoview-omni
    # See https://github.com/mozilla-mobile/android-components/commit/0b349f48c91a50bb7b4ffbf40c6c122ed18142d3  # noqa E501
    # However, geckoview-omni requires exoplayer2 which comes
    # from the lite build, so check for that too
    name_lite = name
    name += "-omni"

    r = requests.get(f"{MAVEN}/org/mozilla/geckoview/{name}/maven-metadata.xml")
    r.raise_for_status()
    metadata = xmltodict.parse(r.text)
    r = requests.get(f"{MAVEN}/org/mozilla/geckoview/{name_lite}/maven-metadata.xml")
    r.raise_for_status()
    lite_metadata = xmltodict.parse(r.text)

    versions = [
        v
        for v in metadata["metadata"]["versioning"]["versions"]["version"]
        if (gv_major_version is None or v.startswith(f"{gv_major_version}."))
        and v in lite_metadata["metadata"]["versioning"]["versions"]["version"]
    ]

    if len(versions) == 0:
        raise Exception(
            f"Could not find any GeckoView {channel.capitalize()} "
            f"{gv_major_version} releases"
        )

    latest = max(versions, key=gv_version_sort_key)

    # Make sure this release has been uploaded for all architectures.

    for arch in ("arm64-v8a", "armeabi-v7a", "x86", "x86_64"):
        r = requests.get(
            f"{MAVEN}/org/mozilla/geckoview/{name}-{arch}/"
            f"{latest}/{name}-{arch}-{latest}.pom"
        )
        r.raise_for_status()

    return latest


def get_latest_ac_version(ac_major_version):
    """Find the last android-components release on Maven for the given major version"""
    r = requests.get(
        "https://maven.mozilla.org/maven2/org/mozilla/components/ui-widgets/maven-metadata.xml"  # noqa E501
    )
    r.raise_for_status()

    metadata = xmltodict.parse(r.text)

    versions = []
    for version in metadata["metadata"]["versioning"]["versions"]["version"]:
        if version.startswith(f"{ac_major_version}."):
            versions.append(version)

    if len(versions) == 0:
        raise Exception(
            f"Could not find any Android-Components {ac_major_version} "
            "releases on maven.mozilla.org"
        )

    return max(versions, key=MobileVersion.parse)


def get_latest_ac_nightly_version():
    """Find the last android-components Nightly release on Maven
    for the given major version"""
    r = requests.get(
        "https://nightly.maven.mozilla.org/maven2/org/mozilla/components/ui-widgets/maven-metadata.xml"  # noqa E501
    )
    r.raise_for_status()
    metadata = xmltodict.parse(r.text)
    return metadata["metadata"]["versioning"]["latest"]


def ac_version_from_tag(tag):
    """Return the AC version from a release tag. Like v63.0.2 returns 63.0.2."""
    if not tag.startswith("components-v"):
        return
    version = tag[len("components-v") :]
    MobileVersion.parse(version)
    return version


def get_recent_ac_releases(repo):
    releases = repo.get_releases()
    if releases.totalCount == 0:
        return []
    return [
        ac_version_from_tag(release.tag_name)
        for release in releases[:50]
        if ac_version_from_tag(release.tag_name)
    ]


def compare_gv_versions(a, b):
    a = a.split(".")
    a = int(a[0]) * 10000000000000000000 + int(a[1]) * 1000000000000000 + int(a[2])
    b = b.split(".")
    b = int(b[0]) * 10000000000000000000 + int(b[1]) * 1000000000000000 + int(b[2])
    return a - b


def gv_version_sort_key(a):
    a = a.split(".")
    return int(a[0]) * 10000000000000000000 + int(a[1]) * 1000000000000000 + int(a[2])


def get_fenix_release_branches(repo):
    return [
        branch.name
        for branch in repo.get_branches()
        if re.match(r"^releases[_/]v\d+$", branch.name)
    ]


def major_version_from_fenix_release_branch_name(branch_name):
    if matches := re.match(r"^releases[_/]v(\d+)$", branch_name):
        return int(matches[1])
    raise Exception(f"Unexpected release branch name: {branch_name}")


def get_recent_fenix_versions(repo):
    major_fenix_versions = [
        major_version_from_fenix_release_branch_name(branch_name)
        for branch_name in get_fenix_release_branches(repo)
    ]
    return sorted(major_fenix_versions, reverse=False)[-2:]


"""
Starting with Fx 114, application-services switched to a new system for
releases and nightlies.  This function checks if we're on an older
android-components version and should therefore use the legacy handling.
"""


def use_legacy_as_handling(ac_major_version):
    return ac_major_version < 114


def validate_as_version(v):
    """Validate that v is in the format of 100.0 Returns v or raises an exception."""

    if match := re.match(r"(^\d+)\.\d+\.\d+$", v):
        # application-services used to have its own 3-component version system,
        # ending with version 97
        if int(match.group(1)) <= 97:
            return v

    if match := re.match(r"(^\d+)\.\d+$", v):
        # Application-services switched to following the 2-component the
        # Firefox version number in v114
        if int(match.group(1)) >= 114:
            return v
    raise Exception(f"Invalid version format {v}")


def validate_as_channel(c):
    """Validate that c is a valid app-services channel."""
    if c in ("staging", "nightly_staging"):
        # These are channels are valid, but only used for preview builds.  We don't have
        # any way of auto-updating them
        raise Exception(f"Can't update AS channel {c}")
    if c not in ("release", "nightly"):
        raise Exception(f"Invalid AS channel {c}")
    return c


def get_current_as_version(ac_repo, release_branch_name, ac_major_version):
    """Return the current as version used on the given release branch"""
    if use_legacy_as_handling(ac_major_version):
        # The version used to be listed in `DependenciesPlugin.kt`
        path = get_dependencies_file_path(ac_major_version)
        regex = re.compile(
            r'const val mozilla_appservices = "([^"]*)"',
            re.MULTILINE,
        )
    else:
        # The version is now stored in `ApplicationServices.kt`
        path = get_app_services_version_path(ac_major_version)
        regex = re.compile(r'val VERSION = "([\d\.]+)"', re.MULTILINE)

    content_file = ac_repo.get_contents(path, ref=release_branch_name)
    src = content_file.decoded_content.decode("utf8")
    if match := regex.search(src):
        return validate_as_version(match[1])
    raise Exception(
        f"Could not find application services version in {os.path.basename(path)}"
    )


def match_as_channel(src):
    """
    Find the ApplicationServicesChannel channel in the contents of the given
    ApplicationServicesChannel.kt file.
    """
    if match := re.compile(
        r"val CHANNEL = ApplicationServicesChannel."
        r"(NIGHTLY|NIGHTLY_STAGING|STAGING|RELEASE)",
        re.MULTILINE,
    ).search(src):
        return validate_as_channel(match[1].lower())
    raise Exception("Could not match the channel in ApplicationServices.kt")


def get_current_as_channel(ac_repo, release_branch_name, ac_major_version):
    """Return the current as channel used on the given release branch"""
    if use_legacy_as_handling(ac_major_version):
        # app-services used to only have a release channel
        return "release"
    else:
        # The channel is now stored in the `ApplicationServices.kt` file
        content_file = ac_repo.get_contents(
            get_app_services_version_path(ac_major_version), ref=release_branch_name
        )
        return match_as_channel(content_file.decoded_content.decode("utf8"))


def validate_glean_version(v):
    """Validate that v is in the format of 63.0.2. Returns v or raises an exception."""
    if not re.match(r"^\d+\.\d+.\d+$", v):
        raise Exception(f"Invalid version format {v}")
    return v


def match_glean_version(src):
    """Find the Glean version in the contents of the given
    DependenciesPlugin.kt file."""
    if match := re.compile(r'const val mozilla_glean = "([^"]*)"', re.MULTILINE).search(
        src
    ):
        return validate_glean_version(match[1])
    raise Exception("Could not match glean in DependenciesPlugin.kt")


def get_current_glean_version(ac_repo, release_branch_name, ac_major_version):
    """Return the current Glean version used on the given release branch"""
    content_file = ac_repo.get_contents(
        get_dependencies_file_path(ac_major_version),
        ref=release_branch_name,
    )
    return match_glean_version(content_file.decoded_content.decode("utf8"))


def major_as_version_from_version(v):
    """Return the major version for the given A-S version"""
    c = validate_as_version(v).split(".")
    return c[0]


def as_version_sort_key(v):
    a = v.split(".")
    return int(a[0]) * 1000000 + int(a[1]) * 1000 + int(a[2])


def get_latest_as_version(as_major_version, as_channel):
    """Find the last A-S version on Maven for the given major version"""

    if int(as_major_version) <= 97:
        return get_latest_as_version_legacy(as_major_version)

    if as_channel == "nightly":
        r = requests.get(
            taskcluster_indexed_artifact_url(
                "project.application-services.v2.nightly.latest",
                "public/build/nightly.json",
            )
        )
        r.raise_for_status()
        return r.json()["version"]
    else:
        raise NotImplementedError("Only the AS nightly channel is currently supported")


def get_latest_as_version_legacy(as_major_version):
    # For App-services versions up until v97, we need to get the version number
    # from the multi-arch .aar

    # TODO What is the right package to check here? full-megazord metadata seems broken.
    r = requests.get(f"{MAVEN}/org/mozilla/appservices/nimbus/maven-metadata.xml")
    r.raise_for_status()
    metadata = xmltodict.parse(r.text)

    versions = []
    for version in metadata["metadata"]["versioning"]["versions"]["version"]:
        if version.startswith(f"{as_major_version}."):
            versions.append(version)

    if len(versions) == 0:
        raise Exception(f"Could not find any A-S {as_major_version} releases")

    latest = max(versions, key=as_version_sort_key)

    # TODO Make sure this release has been uploaded for all architectures.

    return latest


def compare_as_versions(a, b):
    # Tricky cmp()-style function for application services versions.  Note that
    # this works with both 2-component versions and 3-component ones, Since
    # python compares tuples element by element.
    a = tuple(int(x) for x in validate_as_version(a).split("."))
    b = tuple(int(x) for x in validate_as_version(b).split("."))
    return (a > b) - (a < b)


def _update_ac_version(
    repo, branch, old_ac_version, new_ac_version, author, target_path=""
):
    contents = repo.get_contents(
        f"{target_path}buildSrc/src/main/java/AndroidComponents.kt", ref=branch
    )
    content = contents.decoded_content.decode("utf-8")
    new_content = content.replace(
        f'VERSION = "{old_ac_version}"', f'VERSION = "{new_ac_version}"'
    )
    if content == new_content:
        raise Exception(
            "Update to AndroidComponents.kt resulted in no changes: "
            "maybe the file was already up to date?"
        )
    repo.update_file(
        contents.path,
        f"Update to Android-Components {new_ac_version}.",
        new_content,
        contents.sha,
        branch=branch,
        author=author,
    )


def update_android_components_nightly(
    ac_repo, target_repo, target_path, author, debug, release_branch_name, dry_run
):
    current_ac_version = get_current_embedded_ac_version(
        target_repo, release_branch_name, target_path
    )
    log.info(f"Current A-C version in {target_repo} is {current_ac_version}")

    latest_ac_nightly_version = get_latest_ac_nightly_version()

    parsed_current_ac = MobileVersion.parse(current_ac_version)
    parsed_latest_ac = MobileVersion.parse(latest_ac_nightly_version)

    if parsed_current_ac >= parsed_latest_ac:
        log.warning(f"No need to upgrade; {target_repo} is on A-C {current_ac_version}")
        return

    log.info(
        f"We should upgrade {target_repo} to Android-Components "
        f"{latest_ac_nightly_version}"
    )

    if dry_run:
        log.warning("Dry-run so not continuing.")
        return

    pr_branch_name = f"relbot/AC-Nightly-{latest_ac_nightly_version}"

    try:
        if target_repo.get_branch(pr_branch_name):
            log.warning(f"The PR branch {pr_branch_name} already exists. Exiting.")
            return
    except GithubException:
        pass

    release_branch = target_repo.get_branch(release_branch_name)
    log.info(f"Last commit on {release_branch_name} is {release_branch.commit.sha}")

    log.info(f"Creating branch {pr_branch_name} on {release_branch.commit.sha}")
    target_repo.create_git_ref(
        ref=f"refs/heads/{pr_branch_name}", sha=release_branch.commit.sha
    )

    log.info(
        f"Updating AndroidComponents.kt from {current_ac_version} to "
        f"{latest_ac_nightly_version} on {pr_branch_name}"
    )
    _update_ac_version(
        target_repo,
        pr_branch_name,
        current_ac_version,
        latest_ac_nightly_version,
        author,
        target_path,
    )

    log.info("Creating pull request")
    pr = target_repo.create_pull(
        title=f"Update to Android-Components {latest_ac_nightly_version}.",
        body="This (automated) patch updates Android-Components to "
        f"{latest_ac_nightly_version}.",
        head=pr_branch_name,
        base=release_branch_name,
    )
    log.info(f"Pull request at {pr.html_url}")


def update_android_components_release(
    ac_repo,
    target_repo,
    target_path,
    target_product,
    target_branch,
    major_version,
    author,
    debug,
    dry_run,
):
    log.info(f"Looking at {target_product} {major_version}")

    # Make sure the release branch for this version exists
    release_branch = target_repo.get_branch(target_branch)

    log.info(f"Looking at {target_product} {major_version} on {target_branch}")

    current_ac_version = get_current_embedded_ac_version(
        target_repo, target_branch, target_path
    )
    log.info(f"Current A-C version in {target_product} is {current_ac_version}")

    parsed_current_ac = MobileVersion.parse(current_ac_version)
    latest_ac_version = get_latest_ac_version(parsed_current_ac.major_number)
    log.info(f"Latest A-C version available is {latest_ac_version}")

    parsed_latest_ac = MobileVersion.parse(latest_ac_version)
    if len(current_ac_version) != 19 and parsed_current_ac >= parsed_latest_ac:
        log.warning(
            f"No need to upgrade; {target_product} {major_version} is on A-C"
            f"{current_ac_version}"
        )
        return

    log.info(
        f"We are going to upgrade {target_product} {major_version} to "
        f"Android-Components {latest_ac_version}"
    )

    if dry_run:
        log.warning("Dry-run so not continuing.")
        return

    # Create a non unique PR branch name for work on this release branch.
    pr_branch_name = f"relbot/{target_product}-{major_version}"

    try:
        pr_branch = target_repo.get_branch(pr_branch_name)
        if pr_branch:
            log.warning(f"The PR branch {pr_branch_name} already exists. Exiting.")
            return
    except GithubException:
        # TODO Only ignore a 404 here, fail on others
        pass

    log.info(f"Last commit on {target_branch} is {release_branch.commit.sha}")

    log.info(f"Creating branch {pr_branch_name} on {release_branch.commit.sha}")
    target_repo.create_git_ref(
        ref=f"refs/heads/{pr_branch_name}", sha=release_branch.commit.sha
    )

    log.info(
        f"Updating AndroidComponents.kt from {current_ac_version} to "
        f"{latest_ac_version} on {pr_branch_name}"
    )
    _update_ac_version(
        target_repo,
        pr_branch_name,
        current_ac_version,
        latest_ac_version,
        author,
        target_path,
    )

    log.info("Creating pull request")
    pr = target_repo.create_pull(
        title=f"Update to Android-Components {latest_ac_version}.",
        body=f"This (automated) patch updates Android-Components "
        f"to {latest_ac_version}.",
        head=pr_branch_name,
        base=target_branch,
    )
    log.info(f"Pull request at {pr.html_url}")
