#!/usr/bin/env bash

# Output only: deployment progress remains a project-owned, manually maintained record.
deployment_record_path() {
  local owner="${1%/}" name
  name="${owner##*/}"
  if [[ "$name" =~ ^(.+)-tier-[012]$ ]]; then
    printf '%s/%s-architecture/deployments.md\n' "${owner%/*}" "${BASH_REMATCH[1],,}"
  else
    printf '%s\n' '<prefix>-architecture/deployments.md'
  fi
}

print_deployment_record() {
  printf '\nDeployment checklist: %s\n' "$(deployment_record_path "$1")"
  if [[ "${3:-deployment}" == infrastructure ]]; then
    printf '%s\n' 'Infrastructure provisioned; service configuration pending.'
  fi
  printf 'After completing the linked deployment path, manually update the matching entry/option for %s.\n' "$2"
}
