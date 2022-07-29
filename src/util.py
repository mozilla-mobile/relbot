# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


import datetime, re, time


from github import Github, GithubException, InputGitAuthor
import requests
import xmltodict
import json


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
        return validate_ac_version(match[1])
    raise Exception(f"Could not match the VERSION in AndroidComponents.kt")


def get_current_embedded_ac_version(repo, release_branch_name):
    """Return the current A-C version used on the given branch"""
    content_file = repo.get_contents(
        "buildSrc/src/main/java/AndroidComponents.kt", ref=release_branch_name
    )
    return match_ac_version(content_file.decoded_content.decode("utf8"))


def match_gv_version(src):
    """Find the GeckoView version in the contents of the given Gecko.kt file."""
    if match := re.compile(fr'version = "([^"]*)"', re.MULTILINE).search(src):
        return validate_gv_version(match[1])
    raise Exception(f"Could not match the {channel}_version in Gecko.kt")


def get_current_gv_version(repo, release_branch_name):
    """Return the current gv version used on the given release branch"""
    content_file = repo.get_contents(
        "buildSrc/src/main/java/Gecko.kt", ref=release_branch_name
    )
    return match_gv_version(content_file.decoded_content.decode("utf8"))


def match_gv_channel(src):
    """Find the GeckoView channel in the contents of the given Gecko.kt file."""
    if match := re.compile(
        r"val channel = GeckoChannel.(NIGHTLY|BETA|RELEASE)", re.MULTILINE
    ).search(src):
        return validate_gv_channel(match[1].lower())
    raise Exception(f"Could not match the channel in Gecko.kt")


def get_current_gv_channel(repo, release_branch_name):
    """Return the current gv channel used on the given release branch"""
    content_file = repo.get_contents(
        "buildSrc/src/main/java/Gecko.kt", ref=release_branch_name
    )
    return match_gv_channel(content_file.decoded_content.decode("utf8"))


def get_current_ac_version(repo, release_branch_name):
    """Return the current ac version used on the given release branch"""
    content_file = repo.get_contents("version.txt", ref=release_branch_name)
    content = content_file.decoded_content.decode("utf8")
    return validate_ac_version(content.strip())


def get_latest_ac_version_for_major_version(ac_repo, ac_major_version):
    return get_current_ac_version(ac_repo, f"releases/{ac_major_version}.0")


MAVEN = "https://maven.mozilla.org/maven2"


def get_latest_glean_version(gv_version, channel):
    name = "geckoview"
    if channel != "release":
        name += "-" + channel
    # A-C builds against geckoview-omni
    # See https://github.com/mozilla-mobile/android-components/commit/0b349f48c91a50bb7b4ffbf40c6c122ed18142d3
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
            f"Could not find unique glean-native capability for GeckoView {channel.capitalize()} {gv_version}"
        )

    return versions[0]


def get_latest_gv_version(gv_major_version, channel):
    """Find the last geckoview beta release version on Maven for the given major version"""
    if channel not in ("nightly", "beta", "release"):
        raise Exception(f"Invalid channel {channel}")

    # Find the latest release in the multi-arch .aar

    name = "geckoview"
    if channel != "release":
        name += "-" + channel
    # A-C builds against geckoview-omni
    # See https://github.com/mozilla-mobile/android-components/commit/0b349f48c91a50bb7b4ffbf40c6c122ed18142d3
    # However, geckoview-omni requires exoplayer2 which comes from the lite build, so check for that too
    name_lite = name
    name += "-omni"

    r = requests.get(
        f"{MAVEN}/org/mozilla/geckoview/{name}/maven-metadata.xml"
    )
    r.raise_for_status()
    metadata = xmltodict.parse(r.text)
    r = requests.get(
        f"{MAVEN}/org/mozilla/geckoview/{name_lite}/maven-metadata.xml"
    )
    r.raise_for_status()
    lite_metadata = xmltodict.parse(r.text)

    versions = [v for v in metadata["metadata"]["versioning"]["versions"]["version"]
                if (gv_major_version is None or v.startswith(f"{gv_major_version}."))
                and v in lite_metadata["metadata"]["versioning"]["versions"]["version"]]

    if len(versions) == 0:
        raise Exception(
            f"Could not find any GeckoView {channel.capitalize()} {gv_major_version} releases"
        )

    latest = max(versions, key=gv_version_sort_key)

    # Make sure this release has been uploaded for all architectures.

    for arch in ("arm64-v8a", "armeabi-v7a", "x86", "x86_64"):
        r = requests.get(
            f"{MAVEN}/org/mozilla/geckoview/{name}-{arch}/{latest}/{name}-{arch}-{latest}.pom"
        )
        r.raise_for_status()

    return latest


def get_latest_ac_version(ac_major_version):
    """Find the last android-components release on Maven for the given major version"""
    r = requests.get(
        f"https://maven.mozilla.org/maven2/org/mozilla/components/ui-widgets/maven-metadata.xml"
    )
    r.raise_for_status()

    metadata = xmltodict.parse(r.text)

    versions = []
    for version in metadata["metadata"]["versioning"]["versions"]["version"]:
        if version.startswith(f"{ac_major_version}."):
            versions.append(version)

    if len(versions) == 0:
        raise Exception(
            f"Could not find any Android-Components {ac_major_version} releases on maven.mozilla.org"
        )

    return max(versions, key=ac_version_sort_key)


def get_latest_ac_nightly_version():
    """Find the last android-components Nightly release on Maven for the given major version"""
    r = requests.get(
        f"https://nightly.maven.mozilla.org/maven2/org/mozilla/components/ui-widgets/maven-metadata.xml"
    )
    r.raise_for_status()
    metadata = xmltodict.parse(r.text)
    return metadata["metadata"]["versioning"]["latest"]


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
    a = int(a[0]) * 1000000 + int(a[1]) * 1000 + int(a[2])
    b = b.split(".")
    b = int(b[0]) * 1000000 + int(b[1]) * 1000 + int(b[2])
    return a - b


def compare_gv_versions(a, b):
    a = a.split(".")
    a = int(a[0]) * 10000000000000000000 + int(a[1]) * 1000000000000000 + int(a[2])
    b = b.split(".")
    b = int(b[0]) * 10000000000000000000 + int(b[1]) * 1000000000000000 + int(b[2])
    return a - b


def ac_version_sort_key(a):
    a = a.split(".")
    return int(a[0]) * 1000000 + int(a[1]) * 1000 + int(a[2])


def gv_version_sort_key(a):
    a = a.split(".")
    return int(a[0]) * 10000000000000000000 + int(a[1]) * 1000000000000000 + int(a[2])


def get_fenix_release_branches(repo):
    return [
        branch.name
        for branch in repo.get_branches()
        if re.match(r"^releases[_/]v\d+\.0\.0$", branch.name)
    ]


def major_version_from_fenix_release_branch_name(branch_name):
    if matches := re.match(r"^releases[_/]v(\d+)\.0\.0$", branch_name):
        return int(matches[1])
    raise Exception(f"Unexpected release branch name: {branch_name}")


def get_recent_fenix_versions(repo):
    major_fenix_versions = [
        major_version_from_fenix_release_branch_name(branch_name)
        for branch_name in get_fenix_release_branches(repo)
    ]
    return sorted(major_fenix_versions, reverse=False)[-2:]


#
# Return "relevant" A-C versions that could use a GeckoView update check.
#
# Right now we find these by looking at the last two Fenix releases.
#


def get_relevant_ac_versions(fenix_repo, ac_repo):
    releases = []
    for fenix_version in get_recent_fenix_versions(fenix_repo):
        release_branch_name = f"releases_v{fenix_version}.0.0"
        ac_version = get_current_embedded_ac_version(fenix_repo, release_branch_name)
        releases.append(int(major_ac_version_from_version(ac_version)))
    return sorted(releases)


def validate_as_version(v):
    """Validate that v is in the format of 63.0.2. Returns v or raises an exception."""
    if not re.match(r"^\d+\.\d+\.\d+$", v):
        raise Exception(f"Invalid version format {v}")
    return v


def match_as_version(src):
    """Find the A-S version in the contents of the given Dependencies.kt file."""
    if match := re.compile(
        r'const val mozilla_appservices = "([^"]*)"', re.MULTILINE
    ).search(src):
        return validate_as_version(match[1])
    raise Exception(f"Could not match mozilla_appservices in Dependencies.kt")


def get_current_as_version(ac_repo, release_branch_name):
    """Return the current as version used on the given release branch"""
    content_file = ac_repo.get_contents(
        "buildSrc/src/main/java/Dependencies.kt", ref=release_branch_name
    )
    return match_as_version(content_file.decoded_content.decode("utf8"))


def match_glean_version(src):
    """Find the Glean version in the contents of the given Dependencies.kt file."""
    if match := re.compile(
        rf'const val mozilla_glean = "([^"]*)"', re.MULTILINE
    ).search(src):
        return validate_as_version(match[1])
    raise Exception(f"Could not match glean in Dependencies.kt")


def get_current_glean_version(ac_repo, release_branch_name):
    """Return the current Glean version used on the given release branch"""
    content_file = ac_repo.get_contents(
        "buildSrc/src/main/java/Dependencies.kt", ref=release_branch_name
    )
    return match_glean_version(content_file.decoded_content.decode("utf8"))


def major_as_version_from_version(v):
    """Return the major version for the given A-S version"""
    c = validate_as_version(v).split(".")
    return c[0]


def as_version_sort_key(v):
    a = v.split(".")
    return int(a[0]) * 1000000 + int(a[1]) * 1000 + int(a[2])


def get_latest_as_version(as_major_version):
    """Find the last A-S version on Maven for the given major version"""

    # Find the latest release in the multi-arch .aar

    # TODO What is the right package to check here? full-megazord metadata seems broken.
    r = requests.get(
        f"{MAVEN}/org/mozilla/appservices/nimbus/maven-metadata.xml"
    )
    r.raise_for_status()
    metadata = xmltodict.parse(r.text)

    versions = []
    for version in metadata["metadata"]["versioning"]["versions"]["version"]:
        if version.startswith(f"{as_major_version}."):
            versions.append(version)

    if len(versions) == 0:
        raise Exception(f"Could not find any A-S {as_major_version} releases")

    latest = max(versions, key=as_version_sort_key)

    # Make sure this release has been uploaded for all architectures.

    # TODO Do we need to do this?

    # for arch in ("arm64-v8a", "armeabi-v7a", "x86", "x86_64"):
    #    r = requests.get(f"{MAVEN}/org/mozilla/geckoview/{name}-{arch}/{latest}/{name}-{arch}-{latest}.pom")
    #    r.raise_for_status()

    return latest


def compare_as_versions(a, b):
    a = validate_as_version(a).split(".")
    a = int(a[0]) * 1000000 + int(a[1]) * 1000 + int(a[2])
    b = validate_as_version(b).split(".")
    b = int(b[0]) * 1000000 + int(b[1]) * 1000 + int(b[2])
    return a - b


def _update_ac_version(repo, branch, old_ac_version, new_ac_version, author):
    contents = repo.get_contents(
        "buildSrc/src/main/java/AndroidComponents.kt", ref=branch
    )
    content = contents.decoded_content.decode("utf-8")
    new_content = content.replace(
        f'VERSION = "{old_ac_version}"', f'VERSION = "{new_ac_version}"'
    )
    if content == new_content:
        raise Exception(
            "Update to AndroidComponents.kt resulted in no changes: maybe the file was already up to date?"
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
    ac_repo, target_repo, author, debug, release_branch_name, dry_run
):

    current_ac_version = get_current_embedded_ac_version(
        target_repo, release_branch_name
    )
    print(f"{ts()} Current A-C version in {target_repo} is {current_ac_version}")

    latest_ac_nightly_version = get_latest_ac_nightly_version()

    if compare_ac_versions(current_ac_version, latest_ac_nightly_version) >= 0:
        print(
            f"{ts()} No need to upgrade; {target_repo} is on A-C {current_ac_version}"
        )
        return

    print(
        f"{ts()} We should upgrade {target_repo} to Android-Components {latest_ac_nightly_version}"
    )

    if dry_run:
        print(f"{ts()} Dry-run so not continuing.")
        return

    pr_branch_name = f"relbot/AC-Nightly-{latest_ac_nightly_version}"

    try:
        if pr_branch := target_repo.get_branch(pr_branch_name):
            print(f"{ts()} The PR branch {pr_branch_name} already exists. Exiting.")
            return
    except GithubException as e:
        pass

    release_branch = target_repo.get_branch(release_branch_name)
    print(f"{ts()} Last commit on {release_branch_name} is {release_branch.commit.sha}")

    print(f"{ts()} Creating branch {pr_branch_name} on {release_branch.commit.sha}")
    target_repo.create_git_ref(
        ref=f"refs/heads/{pr_branch_name}", sha=release_branch.commit.sha
    )

    print(
        f"{ts()} Updating AndroidComponents.kt from {current_ac_version} to {latest_ac_nightly_version} on {pr_branch_name}"
    )
    _update_ac_version(
        target_repo,
        pr_branch_name,
        current_ac_version,
        latest_ac_nightly_version,
        author,
    )

    print(f"{ts()} Creating pull request")
    pr = target_repo.create_pull(
        title=f"Update to Android-Components {latest_ac_nightly_version}.",
        body=f"This (automated) patch updates Android-Components to {latest_ac_nightly_version}.",
        head=pr_branch_name,
        base=release_branch_name,
    )
    print(f"{ts()} Pull request at {pr.html_url}")


def update_android_components_release(
    ac_repo,
    target_repo,
    target_product,
    target_branch,
    major_version,
    author,
    debug,
    dry_run,
):
    print(f"{ts()} Looking at {target_product} {major_version}")

    # Make sure the release branch for this version exists
    release_branch = target_repo.get_branch(target_branch)

    print(f"{ts()} Looking at {target_product} {major_version} on {target_branch}")

    current_ac_version = get_current_embedded_ac_version(target_repo, target_branch)
    print(f"{ts()} Current A-C version in {target_product} is {current_ac_version}")

    ac_major_version = int(current_ac_version.split(".", 1)[0])  # TODO Util & Test!
    latest_ac_version = get_latest_ac_version(ac_major_version)
    print(f"{ts()} Latest A-C version available is {latest_ac_version}")

    if (
        len(current_ac_version) != 19
        and compare_ac_versions(current_ac_version, latest_ac_version) >= 0
    ):
        print(
            f"{ts()} No need to upgrade; {target_product} {major_version} is on A-C {current_ac_version}"
        )
        return

    print(
        f"{ts()} We are going to upgrade {target_product} {major_version} to Android-Components {latest_ac_version}"
    )

    if dry_run:
        print(f"{ts()} Dry-run so not continuing.")
        return

    # Create a non unique PR branch name for work on this release branch.
    pr_branch_name = f"relbot/{target_product}-{major_version}"

    try:
        pr_branch = target_repo.get_branch(pr_branch_name)
        if pr_branch:
            print(f"{ts()} The PR branch {pr_branch_name} already exists. Exiting.")
            return
    except GithubException as e:
        # TODO Only ignore a 404 here, fail on others
        pass

    print(f"{ts()} Last commit on {target_branch} is {release_branch.commit.sha}")

    print(f"{ts()} Creating branch {pr_branch_name} on {release_branch.commit.sha}")
    target_repo.create_git_ref(
        ref=f"refs/heads/{pr_branch_name}", sha=release_branch.commit.sha
    )

    print(
        f"{ts()} Updating AndroidComponents.kt from {current_ac_version} to {latest_ac_version} on {pr_branch_name}"
    )
    _update_ac_version(
        target_repo, pr_branch_name, current_ac_version, latest_ac_version, author
    )

    print(f"{ts()} Creating pull request")
    pr = target_repo.create_pull(
        title=f"Update to Android-Components {latest_ac_version}.",
        body=f"This (automated) patch updates Android-Components to {latest_ac_version}.",
        head=pr_branch_name,
        base=target_branch,
    )
    print(f"{ts()} Pull request at {pr.html_url}")
