# Linux Host Security

Apply the opt-in `linux-host-v1` profile to an ordinary Linux service VM. It installs
key-only SSH, chrony, an inbound default-deny firewalld policy and persistent audit
rules. Successful configuration is not evidence of complete hardening or central log retention.

**Working repository:** the consuming `<prefix>-tier-0`, `<prefix>-tier-1` or
`<prefix>-tier-2` (upstream `tier-0/`, `tier-1/`, `tier-2/`). Shared owns the stateless
[`host_security` role](../../../shared/ansible/roles/host_security/tasks/main.yml).
Inventory, selected hosts, access policy and acceptance records remain tier-owned.

**First deployment choice:** [Stage 1, option 4b](../../03-deployment/stage-1-software-intake/README.md#4b-apply-the-linux-security-profile--optional),
after the cache VMs and their package access exist. Later Linux service deployments can reuse this recipe
at their own post-install step. Return to that stage's verification after applying the profile.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Step 1: Select the profile](#select-the-profile)
- [Step 2: Review and apply](#review-and-apply)
- [Policy and Ownership](#policy-and-ownership)
- [Step 3: Accept and return](#acceptance)
- [References](#references)

## Prerequisites

- EL 9/10 on AlmaLinux, Rocky or RHEL, or Debian 12/13; x86_64 or aarch64; systemd.
  These are supported code branches; qualify each actual image before wider deployment.
- An existing non-root automation account with working key-only SSH and sudo. The
  role does not create users, grant sudo, migrate an SSH port or enable root access.
- A tested independent console, a backup of current configuration, and explicit
  authority to replace SSH, chrony and the complete firewalld `public` zone.
- Static guest addressing, approved reachable NTP endpoints and working package
  sources. For Debian, migrate timesyncd/ntp from the console first: the role refuses
  enabled competing daemons. Repository proxy setup remains in the existing baseline.
- A leaf host: no Proxmox, Kubernetes, routing, NAT, alternate active firewall zones,
  source-zone assignments, custom active firewalld policies or non-firewalld nft tables.
  NetworkManager profiles must use `public` or inherit the default. Review persistent
  firewall configuration before first activation. Legacy iptables policy requires a separate migration.
- Current audit configuration must retain local recording at
  `/var/log/audit/audit.log`, without immutable or `never,task` suppression policy.

Activate the accepted controller virtual environment from
[local setup](../../04-development/local-setup.md). Prepare the Python dependencies from
the owning tier's `ansible/` directory on the execution host: `<prefix>-tier-0/ansible/`,
`<prefix>-tier-1/ansible/` or `<prefix>-tier-2/ansible/`.

```bash
python3 -m pip install -r requirements.txt
```

Install the shared collections from `<prefix>-shared/` on the execution host, with the same venv active:

```bash
ansible-galaxy collection install -r ansible/requirements.yml
```

The controller needs OpenSSH `ssh-keygen`, `ansible.utils` and `netaddr`; managed
hosts get distro-native firewalld/Python bindings, OpenSSH, chrony and audit packages.
On Debian, Ansible's package service-start guard prevents a new package from
activating a firewall before its approved configuration is written. [1]
In the upstream kit, the same collection manifest is under `shared/ansible/requirements.yml`.

<a id="select-the-profile"></a>

## Step 1: Select the profile

From the generated tier's **`ansible/` directory**, create a private input file:

Run from **`<prefix>-tier-0/ansible/`**, **`<prefix>-tier-1/ansible/`** or
**`<prefix>-tier-2/ansible/`** on the execution host.

```bash
install -d -m 0700 "$HOME/.config/homelab"
cp -n group_vars/host_security.yml.example "$HOME/.config/homelab/host-security.yml"
chmod 600 "$HOME/.config/homelab/host-security.yml"
```

Edit **`$HOME/.config/homelab/host-security.yml`** using the fields below. Existing
files are preserved. The file is passed explicitly, not loaded for ordinary hosts.
Keep keys outside Git; `public_key_files` contains local absolute paths, not key text.
Complete [bootstrap SSH setup](../../03-deployment/foundation/bootstrap/README.md#step-3-prepare-the-execution-accounts-ssh-key)
first if no usable execution key/agent exists.

| Input | Required Selection |
| --- | --- |
| `host_security_enabled` | Boolean `true`; shipped default is `false` |
| `host_security_profile` | `linux-host-v1` |
| `host_security_hosts` | One pilot inventory name initially; default group is absent |
| `host_security_operator_sources` | Non-default-route IPv4/IPv6 CIDRs; include the source seen by the guest after NAT/jump routing |
| `host_security_ssh_users` | Existing non-root names and nonempty `public_key_files` lists; include the current Ansible user |
| `host_security_time_servers` | Reachable NTP DNS names or addresses; no implicit public pool |
| `host_security_service_rules` | Explicit inbound `{source, port, protocol}` entries; `[]` for an SSH-only host |
| `host_security_vrrp_peers` | Explicit keepalived peer source `/32` or `/128` CIDRs; `[]` only without keepalived |
| `host_security_acknowledgement` | `apply-linux-host-v1`, supplied explicitly for apply |
| `host_security_console_verified` | Boolean `true` only after console login succeeds |
| `host_security_key_access_verified` | Boolean `true` after testing the selected key and sudo in a separate connection |
| `host_security_config_ownership_verified` | Boolean `true` after reviewing full config ownership |

For example, the private input file for an SSH-only pilot might contain:

```yaml
host_security_enabled: true
host_security_profile: linux-host-v1
host_security_hosts: pilot-1
host_security_operator_sources: [192.0.2.10/32]
host_security_ssh_users:
  - name: automation
    public_key_files: [/home/operator/.ssh/homelab.pub]
host_security_time_servers: [192.0.2.123]
host_security_service_rules: []
host_security_console_verified: true
host_security_key_access_verified: true
host_security_config_ownership_verified: true
```

Replace documentation addresses and names with actual private inputs. A service
allow might be `{source: 192.0.2.32/28, port: 443, protocol: tcp}`. Include DNS,
directory, telemetry, backup and application listeners this particular host needs.
Service allows cannot reuse the SSH port; only operator sources may open it.

For a cache or other keepalived VIP host, supply every approved remote peer's
actual unicast source address in `host_security_vrrp_peers`, for example
`[192.0.2.21/32]` on its partner. Do not use the VIP, a whole subnet or a UDP port:
VRRP is IP protocol 112. [6] The role emits only source-scoped VRRP rich rules and
refuses apply with no peers when keepalived is running or enabled. It never copies
an existing unrestricted VRRP allow into the new zone. [4]

<a id="review-and-apply"></a>

## Step 2: Review and apply

Use a Linux controller or WSL. From the generated tier's `ansible/` directory:

Run from **`<prefix>-tier-0/ansible/`**, **`<prefix>-tier-1/ansible/`** or
**`<prefix>-tier-2/ansible/`** on the execution host.

```bash
ansible-playbook -i localhost, playbooks/deployment/host-security.yml -c local \
  -e "@$HOME/.config/homelab/host-security.yml" \
  -e host_security_hosts=localhost -e host_security_action=render \
  -e host_security_output_dir=/tmp/host-security-review \
  -e ansible_os_family=RedHat -e ansible_distribution=AlmaLinux \
  -e ansible_distribution_major_version=10 -e ansible_architecture=x86_64
```

For Debian, select `Debian` for both family and distribution and its actual major
version. Render only writes the review directory. Review `sshd_config`,
`chrony.conf`, `public.xml` and `50-host-security.rules` against the host's services.
Native syntax validation also runs during apply; `--check` is deliberately rejected
for apply because it cannot establish a fresh authenticated connection or enforce a firewall.

Run from the owning tier's **`ansible/`** directory on the execution host: `<prefix>-tier-0/ansible/`,
`<prefix>-tier-1/ansible/` or `<prefix>-tier-2/ansible/`.

```bash
ansible-playbook playbooks/deployment/host-security.yml --limit pilot-1 -e "@$HOME/.config/homelab/host-security.yml" -e host_security_acknowledgement=apply-linux-host-v1
```

Keep the console open. Execution is serial and stops the play on the first host
failure. Before mutation, it verifies the observed SSH source/user/port and parses
each public-key file. After SSH reload it opens a new connection, then validates
and activates firewalld and opens another new connection. There is **no automatic
timed rollback**; use the console recovery procedure in
[host security operations](host-security.md).

## Policy and Ownership

| Area | Applied Policy and Boundary |
| --- | --- |
| SSH | Owns `/etc/ssh/sshd_config`; public-key authentication only; root, passwords, keyboard-interactive, agent/TCP/X11 forwarding and tunnels denied; explicit `AllowUsers` |
| Keys | Root-owned `/etc/ssh/host-security-keys/<user>`; complete approved batch per user; ordinary home `authorized_keys` are no longer consulted [2] |
| Time | Owns distro chrony config; selected servers only; client only; startup correction may step time; waits for synchronization [3] |
| Firewall | Owns `/etc/firewalld/zones/public.xml`; default `public` target `DROP`; source/port and exact-peer VRRP allows cover IPv4/IPv6; no broad `ssh` service, protocols or zone ports [4] |
| Traffic | Unsolicited inbound traffic denied except explicit allows; established replies and firewalld's essential control traffic remain; outbound initiation remains allowed |
| Audit | Adds `/etc/audit/rules.d/50-host-security.rules`; account/SSH/firewall/time changes, clock syscalls and elevated exec; merges persistent fragments; enables EL 10's separate audit rule loader [5] |
| Logs | Existing journal, OS logger, auditd config/plugins and `/var/log/audit/audit.log` are retained; central intake is a separate deployment |

The complete SSH configuration replaces custom Includes, Match blocks, SSH CA/directory
authorization and forwarding exceptions. Do not apply to a FreeIPA SSH integration,
jump host or service with those requirements until a compatible profile is implemented.
EL retains its OS crypto-policy backend Include; other algorithm selection follows
the installed OpenSSH defaults. This is not a
CIS/STIG claim, egress firewall, patch scheduler, MAC-policy installer or immutable audit policy.

<a id="acceptance"></a>

## Step 3: Accept and return

1. Confirm a new operator SSH connection and sudo work; test password/root denial.
2. Test each approved service from its allowed source and denial from an unrelated
   source, for every enabled IP family. A successful Ansible connection is not this test.
   On VIP hosts, verify exactly one owner and peer failover after hardening each member.
3. Confirm `chronyc tracking` and `chronyc sources -v` show an approved synchronized source.
4. Confirm `auditctl -s` shows enabled recording and zero lost records; inspect
   `auditctl -l`, exercise one account/config change and verify its local audit record.
5. After service commissioning, test journal/audit forwarding and protected intake
   using the separate [security logging procedure](../06-resilience/protected-logging.md).
6. Reboot the pilot, repeat access/firewall/time/audit tests, then rerun the
   maintenance recipe. Record actual image versions and evidence before expanding scope.

Return to [Stage 1 verification](../../03-deployment/stage-1-software-intake/README.md#step-5-test-the-selected-intake-path)
when qualifying the disposable clone. Service deployments use their own tier-owned
host-security inputs; do not reuse an SSH-only pilot policy on a listening service.

## References

1. [Ansible apt and service-start guard](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/apt_module.html).
2. [Ansible authorized_key batch and path semantics](https://docs.ansible.com/projects/ansible/latest/collections/ansible/posix/authorized_key_module.html)
   and [OpenSSH sshd_config](https://man.openbsd.org/sshd_config).
3. [Chrony configuration](https://chrony-project.org/doc/4.7/chrony.conf.html).
4. [Firewalld zone configuration](https://firewalld.org/documentation/man-pages/firewalld.zone.html).
5. [Linux Audit augenrules](https://github.com/linux-audit/audit-userspace/blob/master/docs/augenrules.8).
6. [IANA assigned IP protocol numbers](https://www.iana.org/assignments/protocol-numbers).

Sources checked 2026-10-26; VRRP references checked 2026-10-27.
