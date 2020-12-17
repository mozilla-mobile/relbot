# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


import datetime, re, time


from github import Github, GithubException, InputGitAuthor
import yaml
import requests
import xmltodict


AC_MAJOR_VERSION = 67 # TODO This should be discovered dynamically


def discover_ac_major_version(repo):
    return AC_MAJOR_VERSION # TODO This should be discovered dynamically


def validate_ac_version(v):
    """Validate that v is in the format of 63.0.2. Returns v or raises an exception."""
    if not re.match(r"^\d+\.\d+\.\d+$", v):
        raise Exception(f"Invalid AC version format {v}")
    return v


def major_ac_version_from_version(v):
    """Return the major version for the given AC version"""
    c = validate_ac_version(v).split(".")
    return c[0]


def validate_gv_version(v):
    """Validate that v is in the format of 82.0.20201027185343. Returns v or raises an exception."""
    if not re.match(r"^\d{2,}\.\d\.\d{14}$", v):
        raise Exception(f"Invalid GV version {v}")
    return v

def major_gv_version_from_version(v):
    """Return the major version for the given GV version"""
    c = validate_gv_version(v).split(".")
    return c[0]

def match_ac_version_in_fenix(src):
    if match := re.compile(r'VERSION = "([^"]*)"', re.MULTILINE).search(src):
        return validate_ac_version(match[1])
    raise Exception(f"Could not match the VERSION in AndroidComponents.kt")


def get_current_ac_version_in_fenix(fenix_repo, release_branch_name):
    """Return the current A-C version used on the given Fenix branch"""
    content_file = fenix_repo.get_contents("buildSrc/src/main/java/AndroidComponents.kt", ref=release_branch_name)
    return match_ac_version_in_fenix(content_file.decoded_content.decode('utf8'))


def match_ac_version_in_reference_browser(src):
    if match := re.compile(r'VERSION = "([^"]*)"', re.MULTILINE).search(src):
        return validate_ac_version(match[1])
    raise Exception(f"Could not match the VERSION in AndroidComponents.kt")

def get_current_ac_version_in_reference_browser(rb_repo, release_branch_name):
    """Return the current A-C version used on the given branch"""
    content_file = rb_repo.get_contents("buildSrc/src/main/java/AndroidComponents.kt", ref=release_branch_name)
    return match_ac_version_in_reference_browser(content_file.decoded_content.decode('utf8'))


def match_gv_version(src, channel):
    """Find the GeckoView Beta version in the contents of the given AndroidComponents.kt file."""
    if channel not in ("nightly", "beta", "release"):
        raise Exception(f"Invalid channel {channel}")
    if match := re.compile(fr'{channel}_version = "([^"]*)"', re.MULTILINE).search(src):
        return validate_gv_version(match[1])
    raise Exception(f"Could not match the {channel}_version in Gecko.kt")


def get_current_gv_version(repo, release_branch_name, channel):
    """Return the current gv beta version used on the given release branch"""
    if channel not in ("nightly", "beta", "release"):
        raise Exception(f"Invalid channel {channel}")
    content_file = repo.get_contents("buildSrc/src/main/java/Gecko.kt", ref=release_branch_name)
    return match_gv_version(content_file.decoded_content.decode('utf8'), channel)


def get_current_ac_version(repo, release_branch_name):
    """Return the current ac version used on the given release branch"""
    content_file = repo.get_contents(".buildconfig.yml", ref=release_branch_name)
    build_config = yaml.load(content_file.decoded_content.decode('utf8'), Loader=yaml.Loader)
    return build_config['componentsVersion']


def get_latest_ac_version_for_major_version(ac_repo, ac_major_version):
    return get_current_ac_version(ac_repo, f"releases/{ac_major_version}.0")

MAVEN = "https://maven.mozilla.org/maven2"

def get_latest_gv_version(gv_major_version, channel):
    """Find the last geckoview beta release version on Maven for the given major version"""
    if channel not in ("nightly", "beta", "release"):
        raise Exception(f"Invalid channel {channel}")

    # Find the latest release in the multi-arch .aar

    name = "geckoview"
    if channel != "release":
        name += "-" + channel
    r = requests.get(f"{MAVEN}/org/mozilla/geckoview/{name}/maven-metadata.xml?t={int(time.time())}")
    r.raise_for_status()
    metadata = xmltodict.parse(r.text)

    versions = []
    for version in metadata['metadata']['versioning']['versions']['version']:
        if version.startswith(f"{gv_major_version}."):
            versions.append(version)

    if len(versions) == 0:
        raise Exception(f"Could not find any GeckoView {channel.capitalize()} {gv_major_version} releases")

    versions = sorted(versions, key=gv_version_sort_key)
    latest = versions[-1]

    # Make sure this release has been uploaded for all architectures.

    for arch in ("arm64-v8a", "armeabi-v7a", "x86", "x86_64"):
        r = requests.get(f"{MAVEN}/org/mozilla/geckoview/{name}-{arch}/{latest}/{name}-{arch}-{latest}.pom?t={int(time.time())}")
        r.raise_for_status()

    return latest


def get_latest_ac_version(ac_major_version):
    """Find the last android-components release on Maven for the given major version"""
    r = requests.get(f"https://maven.mozilla.org/maven2/org/mozilla/components/ui-widgets/maven-metadata.xml?t={int(time.time())}")
    r.raise_for_status()

    metadata = xmltodict.parse(r.text)

    versions = []
    for version in metadata['metadata']['versioning']['versions']['version']:
        if version.startswith(f"{ac_major_version}."):
            versions.append(version)

    if len(versions) == 0:
        raise Exception(f"Could not find any Android-Components {ac_major_version} releases on maven.mozilla.org")

    versions = sorted(versions, key=ac_version_sort_key)
    return versions[-1]


def get_latest_ac_nightly_version():
    """Find the last android-components Nightly release on Maven for the given major version"""
    r = requests.get(f"https://nightly.maven.mozilla.org/maven2/org/mozilla/components/ui-widgets/maven-metadata.xml?t={int(time.time())}")
    r.raise_for_status()
    metadata = xmltodict.parse(r.text)
    return metadata['metadata']['versioning']['latest']


def get_next_ac_version(current_version):
    c = current_version.split(".")
    return f"{c[0]}.{c[1]}.{int(c[2])+1}"


def ac_version_from_tag(tag):
    """Return the AC version from a release tag. Like v63.0.2 returns 63.0.2."""
    if tag[0] != "v":
        raise Exception(f"Invalid AC tag format {tag}")
    return validate_ac_version(tag[1:])


def get_recent_ac_releases(repo):
    releases = repo.get_releases()
    if releases.totalCount == 0:
        return []
    return [ac_version_from_tag(release.tag_name) for release in releases[:50]]


def ts():
    return str(datetime.datetime.now())


def compare_ac_versions(a, b):
    a = a.split(".")
    a = int(a[0])*1000000 + int(a[1])*1000 + int(a[2])
    b = b.split(".")
    b = int(b[0])*1000000 + int(b[1])*1000 + int(b[2])
    return a-b


def compare_gv_versions(a, b):
    a = a.split(".")
    a = int(a[0])*10000000000000000000 + int(a[1])*1000000000000000 + int(a[2])
    b = b.split(".")
    b = int(b[0])*10000000000000000000 + int(b[1])*1000000000000000 + int(b[2])
    return a-b

def ac_version_sort_key(a):
    a = a.split(".")
    return int(a[0])*1000000 + int(a[1])*1000 + int(a[2])

def gv_version_sort_key(a):
    a = a.split(".")
    return int(a[0])*10000000000000000000 + int(a[1])*1000000000000000 + int(a[2])


def get_fenix_release_branches(repo):
    return [branch.name for branch in repo.get_branches() if re.match(r"^releases[_/]v\d+\.0\.0$", branch.name)]


def major_version_from_fenix_release_branch_name(branch_name):
    if matches := re.match(r"^releases[_/]v(\d+)\.0\.0$", branch_name):
        return int(matches[1])
    raise Exception(f"Unexpected release branch name: {branch_name}")


def get_recent_fenix_versions(repo):
    major_fenix_versions = [major_version_from_fenix_release_branch_name(branch_name)
                            for branch_name in get_fenix_release_branches(repo)]
    return sorted(major_fenix_versions, reverse=False)[-2:]

#
# Return "relevant" A-C versions that could use a GeckoView update check.
#
# Right now we find these by looking at the last two Fenix releases.
#

def get_relevant_ac_versions(fenix_repo, ac_repo):
    releases = []
    for fenix_version in get_recent_fenix_versions(fenix_repo):
        # TODO Temporary fix for transition between branch name conventions
        release_branch_name = f"releases/v{fenix_version}.0.0" if fenix_version < 85 else f"releases_v{fenix_version}.0.0"
        ac_version = get_current_ac_version_in_fenix(fenix_repo, release_branch_name)
        releases.append(int(major_ac_version_from_version(ac_version)))
    return sorted(releases)
