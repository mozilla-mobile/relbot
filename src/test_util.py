# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


import github
import pytest

from util import *

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


def test_get_current_gv_version():
    repo = github.Github().get_repo(f"st3fan/android-components")
    assert get_current_gv_version(repo, "releases/57.0", "beta") == "81.0.20200910180444"
    assert get_current_gv_version(repo, "releases/57.0", "release") == "81.0.20201012085804"


def test_get_current_ac_version():
    repo = github.Github().get_repo(f"st3fan/android-components")
    assert get_current_ac_version(repo, "releases/57.0") == "57.0.8"


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


def test_validate_ac_version_good():
    assert validate_ac_version("63.0.0") == "63.0.0"
    assert validate_ac_version("63.0.1") == "63.0.1"
    assert validate_ac_version("63.1.2") == "63.1.2"
    assert validate_ac_version("12.34.56") == "12.34.56"


def test_get_latest_gv_version_release():
    assert get_latest_gv_version(81, "release") == "81.0.20201012085804"


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

def test_get_all_ac_releases():
    repo = github.Github().get_repo(f"st3fan/android-components")
    releases = get_all_ac_releases(repo)
    assert releases == []

