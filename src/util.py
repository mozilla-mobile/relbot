# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


import datetime, re


from github import Github, GithubException, InputGitAuthor
import yaml
import requests
import xmltodict


AC_MAJOR_VERSION = 63 # TODO This should be discovered dynamically
GV_MAJOR_VERSION = 83 # TODO This should be discovered dynamically


def discover_ac_major_version(repo):
    return AC_MAJOR_VERSION # TODO This should be discovered dynamically


def discover_gv_major_version():
    return GV_MAJOR_VERSION # TODO This should be discovered dynamically


def validate_ac_version(v):
    """Validate that v is in the format of 63.0.2. Returns v or raises an exception."""
    if not re.match(r"^\d+\.\d+\.\d+$", v):
        raise Exception(f"Invalid AC version format {v}")
    return v


def validate_gv_version(v):
    """Validate that v is in the format of 82.0.20201027185343. Returns v or raises an exception."""
    if not re.match(r"^\d{2,}\.\d\.\d{14}$", v):
        raise Exception(f"Invalid GV version {v}")
    return v


def match_gv_version(src, channel):
    """Find the GeckoView Beta version in the contents of the given AndroidComponents.kt file."""
    if channel not in ("beta", "release"):
        raise Exception(f"Invalid channel {channel}")
    if match := re.compile(fr'{channel}_version = "([^"]*)"', re.MULTILINE).search(src):
        return validate_gv_version(match[1])
    raise Exception(f"Could not match the {channel}_version in Gecko.kt")


def get_current_gv_version(repo, release_branch_name, channel):
    """Return the current gv beta version used on the given release branch"""
    if channel not in ("beta", "release"):
        raise Exception(f"Invalid channel {channel}")
    content_file = repo.get_contents("buildSrc/src/main/java/Gecko.kt", ref=release_branch_name)
    return match_gv_version(content_file.decoded_content.decode('utf8'), channel)


def get_current_ac_version(repo, release_branch_name):
    """Return the current ac version used on the given release branch"""
    content_file = repo.get_contents(".buildconfig.yml", ref=release_branch_name)
    build_config = yaml.load(content_file.decoded_content.decode('utf8'), Loader=yaml.Loader)
    return build_config['componentsVersion']


def get_latest_gv_version(gv_major_version, channel):
    """Find the last geckoview beta release version on Maven for the given major version"""
    if channel not in ("beta", "release"):
        raise Exception(f"Invalid channel {channel}")

    # Find the latest release for arm64-v8a

    name = "geckoview"
    if channel != "release":
        name += "-" + channel
    r = requests.get(f"https://maven.mozilla.org/maven2/org/mozilla/geckoview/{name}-arm64-v8a/maven-metadata.xml")
    r.raise_for_status()
    metadata = xmltodict.parse(r.text)

    versions = []
    for version in metadata['metadata']['versioning']['versions']['version']:
        if version.startswith(f"{gv_major_version}."):
            versions.append(version)

    if len(versions) == 0:
        raise Exception(f"Could not find any GeckoView {channel.capitalize()} {gv_major_version} releases")

    versions = sorted(versions)

    # TODO Make sure this release exists for all other architectures

    # TODO Check to make sure they are all present and all the same

    return versions[-1]


def get_next_ac_version(current_version):
    c = current_version.split(".")
    return f"{c[0]}.{c[1]}.{int(c[2])+1}"


def ac_version_from_tag(tag):
    """Return the AC version from a release tag. Like v63.0.2 returns 63.0.2."""
    if tag[0] != "v":
        raise Exception(f"Invalid AC tag format {tag}")
    return validate_ac_version(tag[1:])


def get_recent_ac_releases(repo):
    return [ac_version_from_tag(release.tag_name) for release in repo.get_releases()[:50]]


def ts():
    return str(datetime.datetime.now())
