#!/usr/bin/env bash
set -euo pipefail
umask 077

# Opt-in trusted CI, not the bounded Tier 2 request API.
# Guide: docs/deployment/stage-9-development/procedures/handover.md
if [[ $# != 1 || ! "$1" =~ ^(plan|apply)$ ]]; then
  echo "Usage: bash ../<prefix>-shared/scripts/gitlab-iac.sh {plan|apply}" >&2
  exit 1
fi
action="$1"
for name in IAC_TRUST_CI_CONTROL_PLANE IAC_REPOSITORY_DIR IAC_SHARED_DIR IAC_SHARED_REVISION \
  IAC_SETUP IAC_ENV_FILE VAULT_ADDR VAULT_CACERT VAULT_ROLE VAULT_SECRET_PATH VAULT_ID_TOKEN \
  CI_COMMIT_SHA CI_PIPELINE_ID CI_COMMIT_REF_PROTECTED; do
  [[ -n "${!name:-}" ]] || { echo "Missing $name" >&2; exit 1; }
done
for name in TF_VAR_proxmox_api_url TF_VAR_proxmox_api_token_id TF_VAR_proxmox_api_token_secret; do
  if [[ -n "${!name:-}" ]]; then
    echo "Unset $name: trusted CI obtains provider credentials exclusively from Vault." >&2
    exit 1
  fi
done
if [[ "$IAC_TRUST_CI_CONTROL_PLANE" != true || "$CI_COMMIT_REF_PROTECTED" != true \
  || ! "$CI_PIPELINE_ID" =~ ^[0-9]+$ || ! "$CI_COMMIT_SHA" =~ ^[a-f0-9]{40,64}$ \
  || ! "$IAC_SHARED_REVISION" =~ ^[a-f0-9]{40,64}$ || ! "$IAC_SETUP" =~ ^[a-z0-9-]+$ \
  || ! "$VAULT_SECRET_PATH" =~ ^kv/ci/[a-zA-Z0-9_-]+$ || "$VAULT_ADDR" != https://* ]]; then
  echo "Rejected untrusted or malformed CI execution context." >&2
  exit 1
fi
if [[ "${CI_DEBUG_TRACE:-false}" == true || "${VAULT_SKIP_VERIFY:-false}" != false ]]; then
  echo "Disable debug tracing and Vault TLS bypass before privileged execution." >&2
  exit 1
fi
repo="$(realpath -e -- "$IAC_REPOSITORY_DIR")"
shared="$(realpath -e -- "$IAC_SHARED_DIR")"
[[ "$PWD" == "$repo" && -f "$repo/.deployment-setups" && -f "$IAC_ENV_FILE" ]] || {
  echo "Run from the restored, persistent owning-tier workspace with its approved environment file." >&2
  exit 1
}
[[ "$(git -C "$shared" rev-parse HEAD)" == "$IAC_SHARED_REVISION" ]] || {
  echo "Shared automation must match its independently reviewed revision." >&2
  exit 1
}
git -C "$shared" diff --quiet
git -C "$shared" diff --cached --quiet
git diff --quiet
git diff --cached --quiet
if [[ "$(git rev-parse HEAD)" != "$CI_COMMIT_SHA" ]]; then
  git fetch --no-tags origin "$CI_COMMIT_SHA"
  git switch --detach "$CI_COMMIT_SHA"
fi
[[ "$(git rev-parse HEAD)" == "$CI_COMMIT_SHA" ]]

temporary="$(mktemp -d)"
cleanup() {
  if [[ -n "${VAULT_TOKEN:-}" ]]; then vault token revoke -self >/dev/null 2>&1 || true; fi
  rm -rf -- "$temporary"
}
trap cleanup EXIT
export VAULT_TOKEN
VAULT_TOKEN="$(printf '%s' "$VAULT_ID_TOKEN" | vault write -field=token auth/gitlab-ci/login role="$VAULT_ROLE" jwt=-)"
unset VAULT_ID_TOKEN
export PROXMOX_API_URL PROXMOX_API_TOKEN_ID PROXMOX_API_TOKEN_SECRET ANSIBLE_PRIVATE_KEY_FILE
PROXMOX_API_URL="$(vault kv get -field=proxmox_api_url "$VAULT_SECRET_PATH")"
PROXMOX_API_TOKEN_ID="$(vault kv get -field=proxmox_api_token_id "$VAULT_SECRET_PATH")"
PROXMOX_API_TOKEN_SECRET="$(vault kv get -field=proxmox_api_token_secret "$VAULT_SECRET_PATH")"
export TF_VAR_proxmox_api_url="$PROXMOX_API_URL"
export TF_VAR_proxmox_api_token_id="$PROXMOX_API_TOKEN_ID"
export TF_VAR_proxmox_api_token_secret="$PROXMOX_API_TOKEN_SECRET"
export IAC_REQUIRE_VAULT_PROVIDER=true
ANSIBLE_PRIVATE_KEY_FILE="$temporary/ssh"
vault kv get -field=ssh_private_key "$VAULT_SECRET_PATH" > "$ANSIBLE_PRIVATE_KEY_FILE"
chmod 600 "$ANSIBLE_PRIVATE_KEY_FILE"
plan=".terraform/plans/ci-$CI_PIPELINE_ID-$IAC_SETUP.tfplan"
args=("$IAC_SETUP" --env-file "$IAC_ENV_FILE" --plan-file "$plan")
if [[ "$action" == plan ]]; then args+=(--plan-only); fi
export DEPLOYMENT_REPO_DIR="$repo"
bash "$shared/scripts/deploy.sh" "${args[@]}"
