# NetBox change-audit collection

**Stage route:** [Stage 6, Step 2](../README.md#step-2-add-operational-tools), after NetBox installation.
**Return:** to Step 2 after proving real changes reach protected intake; then complete Headlamp access.

**Working repository:** `<prefix>-tier-0`. NetBox and protected logging already exist.
The selected collector runs on the independently prepared Tier 0 monitoring host;
it is not a new VM or another syslog receiver.

**Prerequisites:** a healthy NetBox API, protected forwarding for this host,
retained source history and an external dead-man monitor.
First complete [monitoring host preparation](independent-monitoring.md#step-1-prepare-the-monitoring-runtime):
managed `mon-1` or an accepted existing host in `infrastructure_monitoring`, verified SSH/sudo
and protected forwarding. Managed `mon-1` uses the foundation IP map; an external host uses
`ansible/host_vars/<monitor-host>.yml`. Netdata need not be installed yet.

## Contents

- [Step 1: Prepare read-only access](#step-1-prepare-read-only-access)
- [Step 2: Install and connect collection](#step-2-install-and-connect-collection)
- [Step 3: Verify history and faults](#step-3-verify-history-and-faults)

## Step 1: Prepare read-only access

1. Create a noninteractive NetBox account allowed only to view **Object changes**,
   across the intended audit scope. Do not grant add/change/delete, superuser or API write privileges.
2. Create a read-only API token. The selected NetBox version uses
   `/api/core/object-changes/`; older supported installations can explicitly select the
   `extras` endpoint and `Token` authentication. Version 2 tokens use `Bearer`. [1][2]
3. Store its token and verified server CA outside Git. Set `NETBOX_AUDIT_TOKEN_FILE`
   and `NETBOX_AUDIT_CA_FILE` to their absolute local paths.

In the protected execution shell, run from **`<prefix>-tier-0/`**:

```bash
read -r -e -p 'Protected read-only NetBox token file: ' NETBOX_AUDIT_TOKEN_FILE
read -r -e -p 'Trusted NetBox CA file: ' NETBOX_AUDIT_CA_FILE
export NETBOX_AUDIT_TOKEN_FILE NETBOX_AUDIT_CA_FILE
```

Retain change records in NetBox longer than the longest planned collection outage plus repair time.
Set `control_applications_netbox_changelog_retention` in the application's owned inputs;
the native chart values map it to `CHANGELOG_RETENTION`, initially 90 days. Keep the
collector's `netbox_audit_retention_days` review contract aligned. Permission changes or source pruning can hide uncollected
events, so verify coverage using a real allowed/denied event test.

## Step 2: Install and connect collection

The implementation is the [Tier 0 recipe](../../../../tier-0/ansible/playbooks/deployment/netbox-audit.yml),
[role](../../../../tier-0/ansible/roles/netbox_audit) and
[input example](../../../../tier-0/ansible/group_vars/netbox_audit.yml.example).

1. Retain the existing host in `infrastructure_monitoring`. Add a `netbox-changes`
   **security** file stream for `/var/lib/netbox-audit/events/*.jsonl` to its existing
   [producer settings](../../stage-2-logging/procedures/sources.md). Prepare its reviewed client certificate
   and register it in the receiver catalogue; never replace the host's OS/audit streams.
2. From the Tier 0 root, create local inputs:

Run from **`<prefix>-tier-0/`**.

```bash
cp -n ansible/group_vars/netbox_audit.yml.example ansible/group_vars/netbox_audit.yml
```

Edit in **`<prefix>-tier-0/`**.

- `ansible/group_vars/netbox_audit.yml`: API endpoint, local credential/TLS inputs and audit acceptance
  gates.

3. Edit `ansible/group_vars/netbox_audit.yml`: stable instance name, exact HTTPS API,
   source retention and polling budget. Verify the view-only token and protected forwarding
   before setting the two acceptance inputs true. Then install:

Run from **`<prefix>-tier-0/`**.

```bash
read -r -p 'Prepared monitoring inventory host: ' AUDIT_HOST
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  --limit "localhost,${AUDIT_HOST:?Select the prepared host}" \
  ansible/playbooks/deployment/netbox-audit.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/foundation.yml \
  -e @ansible/group_vars/netbox_audit.yml
```

Keep `localhost` in the limit: the first play checks that exactly one monitoring host is assigned.
For an existing external host, append `-e "@ansible/host_vars/$AUDIT_HOST.yml"` so its address/account
override the common inputs. Stop if the selected remote host is skipped.
For a named environment, load `all.<env>.yml` and the complete `foundation.<env>.yml` after their base files.

The timer issues GET requests only, with validated TLS and no redirects. It scans retained
history in ascending-ID pages instead of relying on an ID high-water cursor: transactions can
commit out of order. A create-only, flushed local ledger deduplicates previously seen events;
an altered event or changed instance/endpoint fails closed. No source writes/deletes occur.
Full retained-history scans intentionally favor simplicity at homelab scale. Exceeding the reviewed
record budget fails the health check; qualify a different collection design before scaling beyond it.

## Step 3: Verify history and faults

| Test | Required outcome |
| --- | --- |
| Create/update/delete a test object | All three changes retain user, request ID and before/after data in protected intake |
| Read-only credential | API mutations denied; object changes remain visible across the intended scope |
| API or receiver outage | External missing-success alert; later polls/native forwarding replay retained records |
| Collector restart | No partial published event; repeated API results do not erase or replace the first observation |
| Source alteration | Conflicting existing event raises an error, not silent replacement |
| Retention/capacity | Source history exceeds repair window; local ledger and sender disk budget have monitored headroom |

The ledger contains sensitive inventory snapshots. It stays in Tier 0 with no developer access.
Ordinary application stdout is not this audit trail. Polling cannot prove events that a privileged
source administrator removed before collection, and is not a synchronous lossless audit transaction.
Preserve original instance identity, ledger and forwarding state during recovery; never silently
reset the ledger against a different database.

Return to [Stage 6](../README.md#step-2-add-operational-tools).

## References

1. [NetBox object-change API source](https://github.com/netbox-community/netbox/blob/v4.6.1/netbox/core/api/urls.py).
2. [NetBox REST API authentication](https://netbox.readthedocs.io/en/stable/integrations/rest-api/).
