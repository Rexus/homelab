#!/usr/bin/env bash

# Python and Ansible cannot install themselves through Ansible. Keep only that
# bootstrap here; prepare-template-runtime.yml owns subsequent dependencies.
template_runtime_bootstrap_packages() {
  local selected_python="${1:-}" ID="" ID_LIKE="" VERSION_ID=""
  local packages=() privilege=()
  [[ -r /etc/os-release ]] || { echo "Cannot detect bootstrap OS; preinstall Python 3.12–3.14." >&2; return 1; }
  source /etc/os-release
  if [[ "$ID $ID_LIKE" =~ (rhel|fedora|rocky|almalinux|centos) ]]; then
    if [[ "${VERSION_ID%%.*}" -ge 10 || "$ID" == fedora ]]; then
      packages=(dnf install -y python3 python3-pip)
    else
      packages=(dnf install -y python3.12 python3.12-pip)
    fi
  elif [[ "$ID $ID_LIKE" =~ (debian|ubuntu) ]]; then
    if [[ -n "$selected_python" ]]; then
      packages=(apt-get install -y "python$selected_python-venv" python3-pip)
    else
      packages=(apt-get install -y python3 python3-venv python3-pip)
    fi
  else
    echo "Automatic Python bootstrap supports DNF/APT hosts; preinstall Python 3.12–3.14 on this host." >&2
    return 1
  fi
  if (( EUID != 0 )); then
    command -v sudo >/dev/null || { echo "Missing bootstrap OS packages require root or sudo." >&2; return 1; }
    privilege=(sudo)
    [[ -t 0 && -z "${CI:-}" ]] || privilege+=(-n)
  fi
  echo "==> Installing missing Python bootstrap packages from configured OS repositories"
  "${privilege[@]}" "${packages[@]}"
}

prepare_template_runtime() {
  local runtime_repo="$1" runtime_action="$2" runtime_mode="${TEMPLATE_RUNTIME_MODE:-auto}"
  local runtime_python="" candidate runtime_version runtime_dir
  local runtime_need_qemu=false runtime_become=()
  case "$runtime_mode" in
    check) return 0 ;;
    auto) ;;
    *) echo "TEMPLATE_RUNTIME_MODE must be auto or check." >&2; return 1 ;;
  esac
  # An older activated Python environment must not shadow the isolated runtime.
  unset PYTHONHOME PYTHONPATH

  for candidate in "${TEMPLATE_PYTHON:-}" python3 python3.14 python3.13 python3.12; do
    [[ -n "$candidate" ]] || continue
    if command -v "$candidate" >/dev/null && "$candidate" -c 'import sys; sys.exit(not ((3, 12) <= sys.version_info[:2] < (3, 15)))' 2>/dev/null; then
      runtime_python="$(command -v "$candidate")"
      break
    fi
    if [[ -n "${TEMPLATE_PYTHON:-}" && "$candidate" == "$TEMPLATE_PYTHON" ]]; then
      echo "TEMPLATE_PYTHON must select an installed Python 3.12–3.14 interpreter." >&2
      return 1
    fi
  done
  if [[ -z "$runtime_python" ]]; then
    template_runtime_bootstrap_packages || return 1
    for candidate in python3 python3.14 python3.13 python3.12; do
      if command -v "$candidate" >/dev/null && "$candidate" -c 'import sys; sys.exit(not ((3, 12) <= sys.version_info[:2] < (3, 15)))' 2>/dev/null; then
        runtime_python="$(command -v "$candidate")"
        break
      fi
    done
    [[ -n "$runtime_python" ]] || {
      echo "Configured OS repositories do not supply Python 3.12–3.14; use a supported bootstrap host or TEMPLATE_PYTHON." >&2
      return 1
    }
  fi
  runtime_version="$("$runtime_python" -c 'import sys; print("%s.%s" % sys.version_info[:2])')"
  if ! "$runtime_python" -c 'import venv, ensurepip' 2>/dev/null; then
    template_runtime_bootstrap_packages "$runtime_version" || return 1
  fi
  runtime_dir="$runtime_repo/.venv/proxmox-templates-py$runtime_version"
  if [[ ! -x "$runtime_dir/bin/python" ]]; then
    echo "==> Creating isolated template runtime with Python $runtime_version"
    "$runtime_python" -m venv "$runtime_dir" || return 1
  fi
  echo "==> Preparing template runtime: $runtime_dir"
  "$runtime_dir/bin/python" -m pip install --disable-pip-version-check \
    -r "$runtime_repo/ansible/runtime-requirements.txt" || return 1
  export VIRTUAL_ENV="$runtime_dir"
  export PATH="$runtime_dir/bin:$PATH"
  export ANSIBLE_COLLECTIONS_PATH="$runtime_repo/.venv/collections${ANSIBLE_COLLECTIONS_PATH:+:$ANSIBLE_COLLECTIONS_PATH}"
  hash -r

  if [[ "$runtime_action" == setup || "$runtime_action" == replace-disk ]] && ! command -v qemu-img >/dev/null; then
    runtime_need_qemu=true
    if (( EUID != 0 )) && ! sudo -n true 2>/dev/null; then
      if [[ -t 0 && -z "${CI:-}" ]] && command -v sudo >/dev/null; then
        runtime_become+=(--ask-become-pass)
      else
        echo "Installing qemu-img requires root or noninteractive sudo in CI; provision it in the runner image." >&2
        return 1
      fi
    fi
  fi
  ansible-playbook -i localhost, -c local "$runtime_repo/ansible/playbooks/prepare-template-runtime.yml" \
    --extra-vars "template_runtime_install_qemu=$runtime_need_qemu" "${runtime_become[@]}"
}
