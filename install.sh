#! /usr/bin/env bash
#
# Installs the `bin/braingentx.py` script into the `.local/bin` directory,
# removing the `.py` extension and replacing any existing installation.

set -euo pipefail

# Determine the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SOURCE_SCRIPT="${SCRIPT_DIR}/bin/braingentx.py"
TARGET_DIR="${HOME}/.local/bin"
TARGET_SCRIPT="${TARGET_DIR}/braingentx"

log_info() {
	echo "ℹ️  $*"
}

log_error() {
	echo "⚠️  $*" >&2
}

if [[ ! -f "${SOURCE_SCRIPT}" ]]; then
	log_error "Source script not found: ${SOURCE_SCRIPT}"
	exit 1
fi

mkdir -p "${TARGET_DIR}"

# Replace an existing installation, if present.
rm -f "${TARGET_SCRIPT}"

ln -nfs "${SOURCE_SCRIPT}" "${TARGET_SCRIPT}"

log_info "Installed ${TARGET_SCRIPT} from ${SOURCE_SCRIPT}"
