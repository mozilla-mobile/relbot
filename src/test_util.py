# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


import os

import github
import pytest

from util import *


@pytest.fixture
def gh():
    return github.Github(os.getenv("GITHUB_TOKEN"))


GECKO_KT = """
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

internal object GeckoVersions {
    /**
     * GeckoView Nightly Version.
     */
    const val nightly_version = "82.0.20200831091558"

    /**
     * GeckoView Beta Version.
     */
    const val beta_version = "81.0.20200910180444"

    /**
     * GeckoView Release Version.
     */
    const val release_version = "81.0.20201012085804"
}

@Suppress("Unused", "MaxLineLength")
object Gecko {
    const val geckoview_nightly = "org.mozilla.geckoview:geckoview-nightly:${GeckoVersions.nightly_version}"
    const val geckoview_beta = "org.mozilla.geckoview:geckoview-beta:${GeckoVersions.beta_version}"
    const val geckoview_release = "org.mozilla.geckoview:geckoview:${GeckoVersions.release_version}"
}
"""

def test_match_gv_version():
    assert match_gv_version(GECKO_KT, "release") == "81.0.20201012085804"
    assert match_gv_version(GECKO_KT, "beta") == "81.0.20200910180444"


def test_get_current_gv_version(gh):
    repo = gh.get_repo(f"st3fan/android-components")
    assert get_current_gv_version(repo, "master", "nightly") == "88.0.20210301093612"
    assert get_current_gv_version(repo, "releases/57.0", "beta") == "81.0.20200910180444"
    assert get_current_gv_version(repo, "releases/57.0", "release") == "81.0.20201108175212"


ANDROID_COMPONENTS_KT = """
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

object AndroidComponents {
    const val VERSION = "64.0.20201027143116"
}
"""

def test_match_ac_version_in_fenix():
    assert match_ac_version_in_fenix(ANDROID_COMPONENTS_KT) == "64.0.20201027143116"


RB_ANDROID_COMPONENTS_KT = """
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

object AndroidComponents {
    const val VERSION = "69.0.20201203202830"
}
"""

def test_match_ac_version_in_reference_browser():
    assert match_ac_version_in_reference_browser(RB_ANDROID_COMPONENTS_KT) == "69.0.20201203202830"


def test_get_current_ac_version_in_fenix(gh):
    repo = gh.get_repo(f"st3fan/fenix")
    assert get_current_ac_version_in_fenix(repo, "releases/v82.0.0") == "60.0.8"


def test_get_current_ac_version_in_reference_browser(gh):
    repo = gh.get_repo(f"st3fan/reference-browser")
    assert get_current_ac_version_in_fenix(repo, "for-relbot-tests") == "69.0.20201203202830"


def test_get_current_ac_version(gh):
    repo = gh.get_repo(f"st3fan/android-components")
    assert get_current_ac_version(repo, "releases/73.0") == "73.0.3"


def test_validate_gv_version_bad():
    with pytest.raises(Exception):
        validate_gv_version("")
    with pytest.raises(Exception):
        validate_gv_version("lol")
    with pytest.raises(Exception):
        validate_gv_version("81")
    with pytest.raises(Exception):
        validate_gv_version("81.0")
    with pytest.raises(Exception):
        validate_gv_version("81.0.20201012")
    with pytest.raises(Exception):
        validate_gv_version("81.0.202010121122")


def test_validate_gv_version_good():
    assert validate_gv_version("81.0.20201012085804") == "81.0.20201012085804"
    assert validate_gv_version("123.0.20231012085804") == "123.0.20231012085804"


def test_validate_ac_version_bad():
    with pytest.raises(Exception):
        validate_ac_version("")
    with pytest.raises(Exception):
        validate_ac_version("lol")
    with pytest.raises(Exception):
        validate_ac_version("63")
    with pytest.raises(Exception):
        validate_ac_version("63.0")
    with pytest.raises(Exception):
        validate_ac_version("63.0-beta.2")


def test_major_gv_version_from_version_bad():
    with pytest.raises(Exception):
        major_gv_version_from_version("")
    with pytest.raises(Exception):
        major_gv_version_from_version("lol")
    with pytest.raises(Exception):
        major_gv_version_from_version("81")
    with pytest.raises(Exception):
        major_gv_version_from_version("81.0")
    with pytest.raises(Exception):
        major_gv_version_from_version("81.0.20201012")
    with pytest.raises(Exception):
        major_gv_version_from_version("81.0.202010121122")

def test_major_gv_version_from_version_good():
    assert major_gv_version_from_version("81.0.20201012085804") == "81"
    assert major_gv_version_from_version("123.0.20231012085804") == "123"


def test_validate_ac_version_good():
    assert validate_ac_version("64.0.20201027143116") == "64.0.20201027143116"
    assert validate_ac_version("63.0.0") == "63.0.0"
    assert validate_ac_version("63.0.1") == "63.0.1"
    assert validate_ac_version("63.1.2") == "63.1.2"
    assert validate_ac_version("12.34.56") == "12.34.56"


def test_major_ac_version_from_version_bad():
    with pytest.raises(Exception):
        major_ac_version_from_version("")
    with pytest.raises(Exception):
        major_ac_version_from_version("lol")
    with pytest.raises(Exception):
        major_ac_version_from_version("63")
    with pytest.raises(Exception):
        major_ac_version_from_version("63.0")
    with pytest.raises(Exception):
        major_ac_version_from_version("63.0-beta.2")


def test_major_ac_version_from_version_good():
    assert major_ac_version_from_version("63.0.0") == "63"
    assert major_ac_version_from_version("64.0.1") == "64"
    assert major_ac_version_from_version("65.1.2") == "65"
    assert major_ac_version_from_version("123.0.8") == "123"


def test_get_latest_gv_version_release():
    assert get_latest_gv_version(81, "release") == "81.0.20201108175212"


def test_get_latest_gv_version_beta():
    assert get_latest_gv_version(82, "beta") == "82.0.20201008183927"


def test_get_latest_gv_version_release_too_new():
    with pytest.raises(Exception):
        get_latest_gv_version(500, "release")


def test_get_latest_gv_version_beta_too_new():
    with pytest.raises(Exception):
        get_latest_gv_version(500, "beta")


def test_get_next_ac_version():
    assert get_next_ac_version("1.0.0") == "1.0.1"
    assert get_next_ac_version("57.0.1") == "57.0.2"


def test_ac_version_from_tag_good():
    assert ac_version_from_tag("v63.0.0") == "63.0.0"
    assert ac_version_from_tag("v63.0.1") == "63.0.1"
    assert ac_version_from_tag("v63.1.2") == "63.1.2"
    assert ac_version_from_tag("v12.34.56") == "12.34.56"


def test_ac_version_from_tag_bad():
    with pytest.raises(Exception):
        ac_version_from_tag("")
    with pytest.raises(Exception):
        ac_version_from_tag("lol")
    with pytest.raises(Exception):
        ac_version_from_tag("63")
    with pytest.raises(Exception):
        ac_version_from_tag("63.0")
    with pytest.raises(Exception):
        ac_version_from_tag("63.0-beta.2")


def test_get_recent_ac_releases(gh):
    # No releases on the test repo
    assert get_recent_ac_releases(gh.get_repo(f"st3fan/android-components")) == []
    # But plenty releases on the actual repo
    assert get_recent_ac_releases(gh.get_repo(f"mozilla-mobile/android-components")) != []


def test_compare_ac_versions():
    assert compare_ac_versions("63.0.0", "63.0.0") == 0
    assert compare_ac_versions("63.0.1", "63.0.0") > 0
    assert compare_ac_versions("63.0.1", "63.0.2") < 0
    assert compare_ac_versions("63.0.10", "63.0.9") > 0
    assert compare_ac_versions("63.0.9", "63.0.10") < 0


def test_compare_gv_versions():
    assert compare_gv_versions("82.0.20201008183927", "82.0.20201008183927") == 0
    assert compare_gv_versions("82.0.20191008183927", "82.0.20201008183927") < 0
    assert compare_gv_versions("82.0.20201008183927", "82.0.20191008183927") > 0
    assert compare_gv_versions("82.9.20201008183927", "82.10.20191008183927") < 0
    assert compare_gv_versions("82.10.20201008183927", "82.9.20201008183927") > 0
    assert compare_gv_versions("123.567.20201008183927", "123.567.20191008183927") > 0
    assert compare_gv_versions("123.567.20201008183927", "123.567.20201008183927") == 0
    assert compare_gv_versions("123.567.20191008183927", "123.567.20201008183927") < 0


def test_get_latest_ac_version():
    assert get_latest_ac_version(56) == "56.0.0"
    assert get_latest_ac_version(57) == "57.0.9"
    assert get_latest_ac_version(58) == "58.0.0"
    assert get_latest_ac_version(59) == "59.0.0"
    assert get_latest_ac_version(60) == "60.0.8"

def test_get_latest_ac_nightly_version():
    assert get_latest_ac_nightly_version() is not None


def test_get_fenix_release_branches(gh):
    assert get_fenix_release_branches(gh.get_repo(f"st3fan/fenix")) == ["releases/v79.0.0",
                                                                        "releases/v82.0.0",
                                                                        "releases/v83.0.0",
                                                                        "releases/v84.0.0",
                                                                        "releases_v85.0.0",
                                                                        "releases_v86.0.0",
                                                                        "releases_v87.0.0"]


def test_major_version_from_fenix_release_branch_name():
    assert major_version_from_fenix_release_branch_name("releases/v79.0.0") == 79
    assert major_version_from_fenix_release_branch_name("releases/v83.0.0") == 83
    with pytest.raises(Exception):
        major_version_from_fenix_release_branch_name("releases/v83.1.0")
    with pytest.raises(Exception):
        major_version_from_fenix_release_branch_name("releases/Cheese")
    with pytest.raises(Exception):
        major_version_from_fenix_release_branch_name("releases/v84.0.0-beta.1")
    # New style branch names
    assert major_version_from_fenix_release_branch_name("releases_v79.0.0") == 79
    assert major_version_from_fenix_release_branch_name("releases_v83.0.0") == 83
    with pytest.raises(Exception):
        major_version_from_fenix_release_branch_name("releases_v83.1.0")
    with pytest.raises(Exception):
        major_version_from_fenix_release_branch_name("releases_Cheese")
    with pytest.raises(Exception):
        major_version_from_fenix_release_branch_name("releases_v84.0.0-beta.1")


def test_get_recent_fenix_versions(gh):
    assert get_recent_fenix_versions(gh.get_repo(f"st3fan/fenix")) == [86, 87]


def test_get_relevant_ac_versions(gh):
    assert get_relevant_ac_versions(gh.get_repo(f"st3fan/fenix"), gh.get_repo(f"st3fan/android-components")) == [72, 73]
