#!/usr/bin/env bash
# Public staging and serialized ceremonies on a separate, disconnected Linux computer.
set -euo pipefail
umask 077

readonly CLCA_REVISION=d560135cf4bbdc1916fa4c5545012085b96d4a21
readonly CLCA_ARCHIVE_SHA256=a0ca869c3f639b88690db5d6bc23db9ee3ed7b229428cafff01b3b30295353b6
readonly CLCA_PAYLOAD_SHA256=ba0a1c144503496866f1271f7bd553676f1b7710e94cc1f5ca613cf81b10258c
KIT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
readonly KIT_ROOT
readonly INPUTS="$KIT_ROOT/templates/offline-root/orca.conf"
scratch=
cleanup() { [[ -z "$scratch" ]] || rm -rf -- "$scratch"; }
trap cleanup EXIT
die() { printf 'ORCA: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || die "Install $1 on the preparation/ceremony system first."; }

usage() {
    cat <<'EOF'
Usage: bash scripts/offline-root.sh ACTION [ARGUMENTS]
  init                              Create editable templates/offline-root/orca.conf; preserve existing.
  bundle KIT_DIRECTORY              Connected Linux stager: public/policy-only kit; no CA state.
  prepare                           Offline: install pinned tools and initial policy, never keys.
  create                            Offline: one-time encrypted software root creation; typed consent.
  status                            Read-only identity, certificate and pending-operation report.
  sign CSR_FILE APPROVED_KEY_SHA256  Offline: verify CSR public-key hash and pinned root; sign level2.
  crl                               Offline: issue a CRL and export public root/CRL history.
  backup                            Offline: native clca archive encrypted with age to separate custody.

Run from the tier repository for init/bundle, then from the copied kit root offline.
Edit only templates/offline-root/orca.conf. Hashes are 64 hexadecimal digits.
CSR key hash: openssl req -in issuer.csr -pubkey -noout |
  openssl pkey -pubin -outform DER | sha256sum
Passphrases are requested by native clca/OpenSSL, never config or command arguments.
Offline dependencies: bash, GNU coreutils/findutils/tar, openssl, perl, iproute2,
  util-linux (findmnt, lsblk, flock), age. No offline package downloads occur.
EOF
}

read_inputs() {
    [[ -f "$INPUTS" && ! -L "$INPUTS" ]] || die "Run init, then edit templates/offline-root/orca.conf."
    local line key value
    declare -A seen=()
    while IFS= read -r line || [[ -n "$line" ]]; do
        line=${line%$'\r'}
        [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
        [[ "$line" =~ ^(ORCA_[A-Z_]+)=(.*)$ ]] || die "Invalid config line: use KEY=value without shell commands."
        key=${BASH_REMATCH[1]}; value=${BASH_REMATCH[2]}
        case "$key" in
            ORCA_INSTANCE|ORCA_TOOLS|ORCA_TRANSFER|ORCA_BACKUP|ORCA_ORGANIZATION|ORCA_COMMON_NAME|\
            ORCA_PUBLICATION_URL|ORCA_CLCA_SOURCE|ORCA_CLCA_REVISION|ORCA_BACKUP_RECIPIENT|\
            ORCA_ROOT_DAYS|ORCA_ISSUER_DAYS|ORCA_CRL_DAYS|ORCA_ROOT_FINGERPRINT) ;;
            *) die "Unknown configuration field $key." ;;
        esac
        [[ ! ${seen[$key]+yes} ]] || die "Duplicate configuration field $key."
        seen[$key]=yes
        if [[ "$value" == \"*\" || "$value" == \'*\' ]]; then value=${value:1:${#value}-2}; fi
        [[ "$value" != *'$'* && "$value" != *'`'* && "$value" != *\\* ]] || die "Use literal values in $key."
        printf -v "$key" '%s' "$value"
    done < "$INPUTS"
    ORCA_ROOT_DAYS=${ORCA_ROOT_DAYS:-3650}
    ORCA_ISSUER_DAYS=${ORCA_ISSUER_DAYS:-1825}
    ORCA_CRL_DAYS=${ORCA_CRL_DAYS:-90}
    ORCA_ROOT_FINGERPRINT=${ORCA_ROOT_FINGERPRINT:-}
    ORCA_CLCA_SOURCE=${ORCA_CLCA_SOURCE:-}
    for key in ORCA_INSTANCE ORCA_TOOLS ORCA_TRANSFER ORCA_BACKUP ORCA_ORGANIZATION ORCA_COMMON_NAME \
        ORCA_PUBLICATION_URL ORCA_CLCA_REVISION ORCA_BACKUP_RECIPIENT; do
        [[ ${!key:-} ]] || die "Set $key in templates/offline-root/orca.conf."
    done
    [[ "$ORCA_CLCA_REVISION" == "$CLCA_REVISION" ]] || die "Source revision mismatch; use audited pin $CLCA_REVISION."
    for key in ORCA_INSTANCE ORCA_TOOLS ORCA_TRANSFER ORCA_BACKUP; do
        value=${!key}
        [[ "$value" =~ ^/[a-zA-Z0-9_./-]+$ && "$value" != / && "$value" == "$(realpath -m -- "$value")" ]] ||
            die "$key must be a canonical absolute mounted path, without spaces, symlinks or '..'."
    done
    [[ "$ORCA_ORGANIZATION" =~ ^[a-zA-Z0-9][a-zA-Z0-9\ ._()-]*$ &&
       "$ORCA_COMMON_NAME" =~ ^[a-zA-Z0-9][a-zA-Z0-9\ ._()-]*$ ]] ||
        die "Organization/CN: use letters, numbers, spaces, '.', '_', '(', ')' or '-'."
    [[ "$ORCA_PUBLICATION_URL" =~ ^https?://[a-zA-Z0-9.-]+(:[0-9]+)?(/[a-zA-Z0-9._/-]+)?$ ]] ||
        die "Publication URL must be an http(s) base URL without credentials, query or trailing slash."
    [[ "$ORCA_PUBLICATION_URL" != */ ]] || die "Remove the trailing slash from ORCA_PUBLICATION_URL."
    [[ "$ORCA_BACKUP_RECIPIENT" =~ ^age1[0-9a-z]+$ ]] || die "Set an age public recipient from the backup custodian."
    for key in ORCA_ROOT_DAYS ORCA_ISSUER_DAYS ORCA_CRL_DAYS; do
        [[ ${!key} =~ ^[1-9][0-9]{0,4}$ ]] || die "$key must be a positive day count (at most 99999)."
    done
    (( ORCA_ISSUER_DAYS < ORCA_ROOT_DAYS )) || die "Issuer validity must be shorter than root validity."
    [[ -z "$ORCA_ROOT_FINGERPRINT" || "$ORCA_ROOT_FINGERPRINT" =~ ^[a-fA-F0-9]{64}$ ]] ||
        die "ORCA_ROOT_FINGERPRINT must be empty before creation or the accepted 64-digit SHA256."
}

payload_manifest() {
    (cd -- "$1"; find bin lib -type f -print | LC_ALL=C sort | xargs sha256sum; sha256sum LICENSE)
}
verify_payload() {
    [[ -f "$1/bin/clca" && -d "$1/lib" && -f "$1/LICENSE" ]] || die "Incomplete native clca payload."
    [[ -z "$(find "$1/bin" "$1/lib" -type l -print -quit)" && ! -L "$1/LICENSE" ]] || die "Symlinks in clca payload."
    [[ "$(payload_manifest "$1" | sha256sum | cut -d' ' -f1)" == "$CLCA_PAYLOAD_SHA256" ]] ||
        die "Native clca checksum mismatch; use the exact approved source."
}
verify_kit() {
    [[ -f "$KIT_ROOT/manifest.sha256" ]] || die "Use bundle first and run this action from the verified kit."
    (cd -- "$KIT_ROOT"; sha256sum --check --strict manifest.sha256 >/dev/null) || die "Kit integrity check failed."
    verify_payload "$KIT_ROOT/clca"
}

bundle() {
    [[ $# == 1 ]] || die "Usage: bundle <new-kit-directory>; for example bundle artifacts/orca-kit."
    local target source
    target=$(realpath -m -- "$1")
    [[ ! -e "$target" ]] || die "Kit target already exists; choose a new directory."
    for source in "$ORCA_INSTANCE" "$ORCA_TOOLS" "$ORCA_BACKUP" "$ORCA_TRANSFER"; do
        [[ "$target/" != "$source/"* ]] || die "Build the public kit on the connected stager, outside custody paths."
    done
    scratch=$(mktemp -d)
    if [[ -n "$ORCA_CLCA_SOURCE" ]]; then
        need git
        [[ "$(git -C "$ORCA_CLCA_SOURCE" rev-parse HEAD)" == "$CLCA_REVISION" ]] || die "Local clca revision mismatch."
        [[ -z "$(git -C "$ORCA_CLCA_SOURCE" status --porcelain)" ]] || die "Local clca checkout is not clean."
        mkdir "$scratch/native"
        git -C "$ORCA_CLCA_SOURCE" archive "$CLCA_REVISION" bin lib LICENSE |
            tar -xf - -C "$scratch/native"
        source=$scratch/native
    else
        need curl
        curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
            "https://codeload.github.com/openxpki/clca/tar.gz/$CLCA_REVISION" -o "$scratch/clca.tar.gz"
        printf '%s  %s\n' "$CLCA_ARCHIVE_SHA256" "$scratch/clca.tar.gz" | sha256sum -c - >/dev/null ||
            die "Official archive checksum mismatch; do not use it."
        tar -xzf "$scratch/clca.tar.gz" -C "$scratch"
        source=$scratch/clca-$CLCA_REVISION
    fi
    verify_payload "$source"
    mkdir -p "$target/scripts" "$target/templates/offline-root" "$target/clca"
    cp -- "$KIT_ROOT/scripts/offline-root.sh" "$target/scripts/"
    cp -- "$KIT_ROOT/templates/offline-root/"{orca.conf.example,clca.cfg.example,openssl.cnf.example} \
        "$target/templates/offline-root/"
    cp -R -- "$source/bin" "$source/lib" "$source/LICENSE" "$target/clca/"
    # Only recognized, literal public settings enter the kit; never copy arbitrary input files.
    local key
    for key in ORCA_INSTANCE ORCA_TOOLS ORCA_TRANSFER ORCA_BACKUP ORCA_ORGANIZATION ORCA_COMMON_NAME \
        ORCA_PUBLICATION_URL ORCA_CLCA_REVISION ORCA_BACKUP_RECIPIENT ORCA_ROOT_DAYS ORCA_ISSUER_DAYS \
        ORCA_CRL_DAYS ORCA_ROOT_FINGERPRINT; do
        printf '%s="%s"\n' "$key" "${!key}"
    done > "$target/templates/offline-root/orca.conf"
    printf 'Source: https://github.com/openxpki/clca\nRevision: %s\nArchive-SHA256: %s\nPayload-SHA256: %s\n' \
        "$CLCA_REVISION" "$CLCA_ARCHIVE_SHA256" "$CLCA_PAYLOAD_SHA256" > "$target/source.txt"
    (cd -- "$target"; find scripts templates clca -type f ! -name orca.conf -print0 |
        LC_ALL=C sort -z | xargs -0 sha256sum; sha256sum source.txt) > "$target/manifest.sha256"
    printf 'Public kit: %s\nRecord this manifest hash separately and verify it offline:\n' "$target"
    sha256sum "$target/manifest.sha256"
}

offline_guard() {
    local links routes4 routes6
    links=$(ip -o link show up) || die "Cannot inspect network links."
    routes4=$(ip -4 route show table all default) || die "Cannot inspect IPv4 routing."
    routes6=$(ip -6 route show table all default) || die "Cannot inspect IPv6 routing."
    [[ -z "$(printf '%s\n' "$links" | awk -F': ' 'NF > 1 && $2 !~ /^lo(@|$)/')" &&
        -z "$routes4" && -z "$routes6" ]] ||
        die "Disconnect/disable all non-loopback links and default routes before an offline ceremony."
}

# Return the actual mounted filesystem's device, requiring encrypted block ancestry for state/tools.
media_device() {
    local path=$1 encrypted=$2 probe source mount types
    probe=$path
    while [[ ! -e "$probe" ]]; do probe=$(dirname -- "$probe"); done
    source=$(findmnt -n -o SOURCE --target "$probe") || die "Cannot identify mounted media for $path."
    mount=$(findmnt -n -o TARGET --target "$probe") || die "Cannot identify mount for $path."
    [[ "$mount" != / && "$source" == /dev/* ]] || die "$path must use mounted removable/block media, not the system root."
    source=${source%%\[*}
    if [[ "$encrypted" == yes ]]; then
        types=$(lsblk -s -n -r -o TYPE -- "$source") || die "Cannot prove encryption backing $path."
        grep -qx crypt <<< "$types" || die "$path must be on an unlocked encrypted block volume."
    fi
    findmnt -n -o MAJ:MIN --target "$probe"
}

check_media() {
    local work tools transfer backup
    work=$(media_device "$ORCA_INSTANCE" yes)
    tools=$(media_device "$ORCA_TOOLS" yes)
    transfer=$(media_device "$ORCA_TRANSFER" no)
    backup=$(media_device "$ORCA_BACKUP" no)
    [[ -d "$ORCA_TRANSFER" && -d "$ORCA_BACKUP" ]] || die "Mount the transfer and independent backup directories first."
    [[ "$work" == "$tools" ]] || die "Instance and tools must be on the same encrypted working volume."
    [[ "$work" != "$transfer" && "$work" != "$backup" && "$transfer" != "$backup" ]] ||
        die "Working, transfer and backup must be three distinct mounted filesystems."
    # Different partitions/LUKS mappings on the same disk are not independent custody.
    local path source disks disk
    declare -A owners=()
    for path in "$ORCA_INSTANCE" "$ORCA_TRANSFER" "$ORCA_BACKUP"; do
        local probe=$path
        while [[ ! -e "$probe" ]]; do probe=$(dirname -- "$probe"); done
        source=$(findmnt -n -o SOURCE --target "$probe"); source=${source%%\[*}
        disks=$(lsblk -s -n -r -o MAJ:MIN,TYPE -- "$source" | awk '$2 == "disk" {print $1}')
        [[ -n "$disks" ]] || die "Cannot prove independent physical backing for $path."
        while read -r disk; do
            [[ ! ${owners[$disk]+yes} ]] || die "Custody media share a physical disk; use independent devices."
            owners[$disk]=$path
        done <<< "$disks"
    done
    [[ "$ORCA_INSTANCE/" != "$ORCA_TOOLS/"* && "$ORCA_TOOLS/" != "$ORCA_INSTANCE/"* ]] ||
        die "Tools and instance must be separate directories on working media."
}

lock_instance() {
    local parent
    parent=$(dirname -- "$ORCA_INSTANCE")
    [[ -d "$parent" ]] || die "Create the instance parent directory on encrypted working media first: $parent"
    exec 9>>"$parent/.orca-$(basename -- "$ORCA_INSTANCE").lock"
    flock --nonblock 9 || die "Another ceremony is using this instance; wait for it to finish."
}
binding() {
    printf '%s\n' "$ORCA_INSTANCE" "$ORCA_TOOLS" "$ORCA_ORGANIZATION" "$ORCA_COMMON_NAME" \
        "$ORCA_PUBLICATION_URL" "$CLCA_REVISION" "$ORCA_ROOT_DAYS" "$ORCA_ISSUER_DAYS" "$ORCA_CRL_DAYS" |
        sha256sum | cut -d' ' -f1
}
policy_manifest() { (cd -- "$ORCA_INSTANCE"; sha256sum etc/clca.cfg etc/openssl.cnf); }
check_instance_policy() {
    [[ -f "$ORCA_INSTANCE/.orca-binding" ]] || die "Run prepare with this kit before creating a root."
    [[ "$(cat "$ORCA_INSTANCE/.orca-binding")" == "$(binding)" ]] ||
        die "Retained instance/config binding differs; restore its original inputs, never reinitialize it."
    (cd -- "$ORCA_INSTANCE"; sha256sum -c .orca-policy.sha256 >/dev/null) || die "Retained CA policy has changed; stop for review."
}
check_instance() {
    check_instance_policy
    verify_payload "$ORCA_TOOLS"
}
native() {
    offline_guard
    (cd -- "$ORCA_INSTANCE"; env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin \
        TMPDIR="$ORCA_INSTANCE" LC_ALL=C bash "$ORCA_TOOLS/bin/clca" "$@")
}
assert_root() {
    [[ -s "$ORCA_INSTANCE/private/cakey.pem" && -f "$ORCA_INSTANCE/ca/index.txt" &&
        -s "$ORCA_INSTANCE/ca/cacert.pem" && -f "$ORCA_INSTANCE/.orca-created" ]] ||
        die "Root creation is incomplete or absent. Recover the original instance; do not regenerate."
    if [[ -L "$ORCA_INSTANCE/private/cakey.pem" ]] ||
        ! grep -q 'BEGIN ENCRYPTED PRIVATE KEY' "$ORCA_INSTANCE/private/cakey.pem"; then
        die "Retained root key must be a local, encrypted native software key."
    fi
    local actual
    actual=$(openssl x509 -in "$ORCA_INSTANCE/ca/cacert.pem" -outform DER | sha256sum | cut -d' ' -f1)
    [[ "${ORCA_ROOT_FINGERPRINT,,}" == "$actual" ]] ||
        die "Set independently verified ORCA_ROOT_FINGERPRINT=$actual in the public config before continuing."
    openssl verify -check_ss_sig -no_check_time -CAfile "$ORCA_INSTANCE/ca/cacert.pem" \
        "$ORCA_INSTANCE/ca/cacert.pem" >/dev/null
}
confirm() {
    local answer
    printf '%s\nType exactly: %s\n> ' "$1" "$2" >&2
    IFS= read -r answer || die "Confirmation required."
    [[ "$answer" == "$2" ]] || die "Confirmation did not match; no key operation performed."
}
begin_operation() {
    [[ ! -e "$ORCA_INSTANCE/.orca-pending" ]] || die "A prior operation is incomplete; inspect status and recover before mutating."
    printf '%s %s\n' "$1" "$(date -u +%FT%TZ)" > "$ORCA_INSTANCE/.orca-pending"
}
end_operation() {
    rm -- "$ORCA_INSTANCE/.orca-pending"
    sync -f "$ORCA_INSTANCE"
    printf '%s\n' 'Root state changed. Run backup now; retain this current database and CRL history.'
}

prepare() {
    verify_kit
    local retained_instance=no
    if [[ -e "$ORCA_INSTANCE" || -L "$ORCA_INSTANCE" ]]; then
        # Validate retained custody before reinstalling public tools during cold recovery.
        check_instance_policy
        retained_instance=yes
    fi
    if [[ -e "$ORCA_TOOLS" || -L "$ORCA_TOOLS" ]]; then verify_payload "$ORCA_TOOLS"; else
        mkdir "$ORCA_TOOLS"; cp -R -- "$KIT_ROOT/clca/"{bin,lib,LICENSE} "$ORCA_TOOLS/"
        verify_payload "$ORCA_TOOLS"
    fi
    if [[ "$retained_instance" == yes ]]; then
        printf '%s\n' 'Original pinned tools verified/restored. Existing CA instance and policy preserved byte-for-byte.'
        return
    fi
    mkdir -p "$ORCA_INSTANCE/etc" "$ORCA_INSTANCE/history" "$ORCA_INSTANCE/requests"
    cp -- "$KIT_ROOT/templates/offline-root/clca.cfg.example" "$ORCA_INSTANCE/etc/clca.cfg"
    sed -i "s/^CA_VALIDITY=.*/CA_VALIDITY=$ORCA_ROOT_DAYS/;s/^BATCH=.*/BATCH=1/" "$ORCA_INSTANCE/etc/clca.cfg"
    sed -e "s/REPLACE_WITH_APPROVED_ORGANIZATION/$ORCA_ORGANIZATION/" \
        -e "s/REPLACE_WITH_APPROVED_ROOT_CA_NAME/$ORCA_COMMON_NAME/" \
        -e "s|http://pki.example.invalid/download|$ORCA_PUBLICATION_URL|g" \
        -e "s/^default_days = .*/default_days = $ORCA_ISSUER_DAYS/" \
        -e "s/^default_crl_days = .*/default_crl_days = $ORCA_CRL_DAYS/" \
        "$KIT_ROOT/templates/offline-root/openssl.cnf.example" > "$ORCA_INSTANCE/etc/openssl.cnf"
    binding > "$ORCA_INSTANCE/.orca-binding"
    policy_manifest > "$ORCA_INSTANCE/.orca-policy.sha256"
    cp -- "$KIT_ROOT/source.txt" "$ORCA_INSTANCE/history/source.txt"
    printf '%s\n' 'Pinned tools and initial policy prepared. No root key exists. Next: create.'
}

create() {
    check_instance
    [[ ! -e "$ORCA_INSTANCE/.orca-create-started" && ! -e "$ORCA_INSTANCE/private" &&
        ! -e "$ORCA_INSTANCE/ca" && ! -e "$ORCA_INSTANCE/certs" && ! -e "$ORCA_INSTANCE/crl" ]] ||
        die "Root key/state or previous creation attempt exists. Restore it; create will never repeat initialization."
    confirm "Create a NEW offline software root for $ORCA_ORGANIZATION?" "$ORCA_COMMON_NAME"
    begin_operation create
    date -u +%FT%TZ > "$ORCA_INSTANCE/.orca-create-started"
    native genkey --protect passphrase
    grep -q 'BEGIN ENCRYPTED PRIVATE KEY' "$ORCA_INSTANCE/private/cakey.pem" || die "Encrypted key proof failed."
    native initialize
    policy_manifest > "$ORCA_INSTANCE/.orca-policy.sha256"
    touch "$ORCA_INSTANCE/.orca-created"
    end_operation
    printf 'Record in templates/offline-root/orca.conf:\nORCA_ROOT_FINGERPRINT=%s\n' \
        "$(openssl x509 -in "$ORCA_INSTANCE/ca/cacert.pem" -outform DER | sha256sum | cut -d' ' -f1)"
    printf '%s\n' 'Then issue crl and backup; transfer media receives only public certificates and CRLs.'
}

status() {
    printf 'Instance: %s\nPinned clca: %s\nConfigured organization: %s\nConfigured root CN: %s\n' \
        "$ORCA_INSTANCE" "$CLCA_REVISION" "$ORCA_ORGANIZATION" "$ORCA_COMMON_NAME"
    if [[ -f "$ORCA_INSTANCE/.orca-pending" ]]; then
        printf 'INCOMPLETE operation: '; cat "$ORCA_INSTANCE/.orca-pending"
    fi
    if [[ -s "$ORCA_INSTANCE/ca/cacert.pem" ]]; then
        openssl x509 -in "$ORCA_INSTANCE/ca/cacert.pem" -noout -subject -issuer -dates -fingerprint -sha256
        printf 'ORCA_ROOT_FINGERPRINT=%s\n' \
            "$(openssl x509 -in "$ORCA_INSTANCE/ca/cacert.pem" -outform DER | sha256sum | cut -d' ' -f1)"
        local actual
        actual=$(openssl x509 -in "$ORCA_INSTANCE/ca/cacert.pem" -outform DER | sha256sum | cut -d' ' -f1)
        if [[ "${ORCA_ROOT_FINGERPRINT,,}" == "$actual" ]]; then
            printf '%s\n' 'Configured fingerprint matches the retained root certificate.'
        else printf '%s\n' 'Config fingerprint is absent/different; verify identity independently before mutation.'; fi
    else printf '%s\n' 'No root certificate. prepare never generates keys.'; fi
    printf '%s\n' 'Read-only status; no keys, tools, configuration or database changed.'
}

export_public() {
    local release
    release=$(mktemp -d "$ORCA_TRANSFER/public-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")
    openssl x509 -in "$ORCA_INSTANCE/ca/cacert.pem" -outform DER -out "$release/root.cer"
    openssl x509 -in "$ORCA_INSTANCE/ca/cacert.pem" -out "$release/root.pem"
    if [[ -f "$ORCA_INSTANCE/crl/ca.crl" ]]; then
        openssl crl -in "$ORCA_INSTANCE/crl/ca.crl" -outform DER -out "$release/root.crl"
        openssl crl -in "$ORCA_INSTANCE/crl/ca.crl" -out "$release/root-crl.pem"
    fi
    if [[ $# == 1 ]]; then openssl x509 -in "$1" -out "$release/issuer.pem"; fi
    (cd -- "$release"; sha256sum ./* > manifest.sha256)
    printf 'Public return directory: %s\nPublish root.cer and root.crl at %s\n' "$release" "$ORCA_PUBLICATION_URL"
}

sign() {
    [[ $# == 2 && "$2" =~ ^[a-fA-F0-9]{64}$ ]] || die "Usage: sign <PEM-CSR-file> <approved-public-key-sha256>."
    assert_root
    local csr approved request_hash output key_hash start end
    csr=$(realpath -e -- "$1"); approved=${2,,}
    [[ "$csr" == "$ORCA_TRANSFER/"* && -f "$csr" ]] || die "CSR must be a regular file on mounted transfer media."
    # Review and sign the same retained snapshot, even if transfer media is changed during approval.
    scratch=$(mktemp -d "$(dirname -- "$ORCA_INSTANCE")/.orca-review-XXXXXX")
    openssl req -in "$csr" -out "$scratch/request.pem"
    csr=$scratch/request.pem
    openssl req -in "$csr" -verify -noout
    key_hash=$(openssl req -in "$csr" -pubkey -noout | openssl pkey -pubin -outform DER | sha256sum | cut -d' ' -f1)
    [[ "$approved" == "$key_hash" ]] || die "CSR public-key fingerprint mismatch; compare with requester out of band."
    request_hash=$(openssl req -in "$csr" -outform DER | sha256sum | cut -d' ' -f1)
    output=$ORCA_INSTANCE/history/issuer-$request_hash.pem
    [[ ! -e "$output" && ! -e "$ORCA_INSTANCE/requests/$request_hash.pem" ]] || die "This CSR was already processed; inspect retained history."
    openssl x509 -in "$ORCA_INSTANCE/ca/cacert.pem" -checkend "$(( ORCA_ISSUER_DAYS * 86400 ))" -noout ||
        die "Issuer validity exceeds remaining root life. Stop for an approved renewal/policy change."
    openssl req -in "$csr" -noout -subject -text
    printf 'Approved public key SHA256: %s\nPinned root SHA256: %s\n' "$key_hash" "$ORCA_ROOT_FINGERPRINT"
    confirm 'Approve this subordinate CA subject, public key and level2 policy?' "SIGN $approved WITH $ORCA_COMMON_NAME"
    begin_operation sign
    openssl req -in "$csr" -out "$ORCA_INSTANCE/requests/$request_hash.pem"
    start=$(date -u +%Y%m%d%H%M%S)
    end=$(date -u -d "+$ORCA_ISSUER_DAYS days" +%Y%m%d%H%M%S)
    native certify --profile level2 --startdate "$start" --enddate "$end" --out "$output" \
        "$ORCA_INSTANCE/requests/$request_hash.pem"
    openssl verify -CAfile "$ORCA_INSTANCE/ca/cacert.pem" "$output"
    export_public "$output"
    end_operation
}

crl() {
    assert_root
    [[ ! -e "$ORCA_INSTANCE/crl/$(date +%Y%m%d%H%M%S).crl" ]] || die "Wait one second; preserve the existing CRL history."
    begin_operation crl
    native issuecrl
    openssl crl -in "$ORCA_INSTANCE/crl/ca.crl" -CAfile "$ORCA_INSTANCE/ca/cacert.pem" -verify -noout
    export_public
    end_operation
}

backup() {
    need age
    assert_root
    scratch=$(mktemp -d "$(dirname -- "$ORCA_INSTANCE")/.orca-backup-XXXXXX")
    local archive=$scratch/root.tar.gz listing file target
    native backup "$archive"
    listing=$(tar -tzf "$archive")
    for file in private/cakey.pem ca/index.txt ca/serial ca/crlnumber.txt ca/cacert.pem etc/clca.cfg etc/openssl.cnf; do
        [[ -f "$ORCA_INSTANCE/$file" && ! -L "$ORCA_INSTANCE/$file" ]] || die "Retained $file is not a regular file."
        grep -Fxq "./$file" <<< "$listing" || die "Native archive is missing $file; do not accept it."
    done
    target="$ORCA_BACKUP/orca-$(date -u +%Y%m%dT%H%M%SZ)-$(basename "$scratch").tar.gz.age"
    [[ ! -e "$target" ]] || die "Backup target exists."
    age --recipient "$ORCA_BACKUP_RECIPIENT" --output "$target.partial" "$archive"
    mv -- "$target.partial" "$target"
    (cd -- "$ORCA_BACKUP"; sha256sum "$(basename -- "$target")") > "$target.sha256"
    cp -- "$target.sha256" "$ORCA_INSTANCE/history/$(basename -- "$target").sha256"
    sync -f "$target"
    sync -f "$ORCA_INSTANCE"
    printf 'Encrypted native archive: %s\nVerify decryption and recovery separately with the backup custodian.\n' "$target"
}

action=${1:-help}; [[ $# == 0 ]] || shift
case "$action" in
    help|--help|-h) usage; exit 0 ;;
    init)
        [[ $# == 0 ]] || die "init takes no arguments."
        if [[ -e "$INPUTS" || -L "$INPUTS" ]]; then printf '%s\n' 'Existing templates/offline-root/orca.conf preserved.'; else
            cp -- "$KIT_ROOT/templates/offline-root/orca.conf.example" "$INPUTS"
            printf '%s\n' 'Edit templates/offline-root/orca.conf, then run bundle on the connected stager.'
        fi
        exit 0 ;;
    bundle|prepare|create|status|sign|crl|backup) ;;
    *) usage >&2; die "Unknown action $action." ;;
esac
[[ $(uname -s) == Linux ]] || die "Run on Linux; use a separate disconnected ceremony computer for root operations."
for command in realpath sha256sum find tar openssl; do need "$command"; done
# All supported inputs come from the one public file, never ambient environment overrides.
while IFS= read -r variable; do unset "$variable"; done < <(compgen -v ORCA_)
read_inputs
if [[ "$action" == bundle ]]; then bundle "$@"; exit 0; fi
[[ "$action" == sign || $# == 0 ]] || die "$action takes no arguments."
if [[ "$action" == status ]]; then status; exit 0; fi
for command in ip findmnt lsblk flock perl; do need "$command"; done
offline_guard
check_media
lock_instance
if [[ "$action" == prepare ]]; then prepare; else
    # Incomplete initialization can also have changed native paths in openssl.cnf.
    # Report the interrupted ceremony before its policy checksum error during backup.
    if [[ "$action" == backup && -e "$ORCA_INSTANCE/.orca-pending" ]]; then
        die "Incomplete operation recorded; resolve/recover retained state before accepting a backup."
    fi
    check_instance
    "$action" "$@"
fi
