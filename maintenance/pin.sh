#!/usr/bin/env bash
set -ex

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_DIR="$(dirname -- "$SCRIPT_DIR")"

PYTHON_VERSION='3.9'

# shellcheck disable=SC2046
read -ra REQUIREMENTS <<<$(find "$REPO_DIR/requirements" -name '*.in' -exec basename {} '.in' \;)
PIP_COMMANDS="pip install pip-compile-multi && pip-compile-multi --allow-unsafe ${REQUIREMENTS[*]/#/--generate-hashes }"

docker pull "python:$PYTHON_VERSION"
docker run \
	--tty \
	--volume "$PWD:/src" \
	--workdir /src \
	"python:$PYTHON_VERSION" \
	bash -cx "$PIP_COMMANDS"
