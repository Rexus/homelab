# System control path

## Purpose

Use this path for the services that tell you what the platform is doing:
telemetry, syslog, metrics, traces, logs, audit events, dashboards, and archive
handoff.

The first concrete guide is:

- [Observability path](observability.md)

## Default capability

The default `observability` setup deploys a useful starting point instead of an
empty path:

| Capability | Default host or hosts |
| --- | --- |
| telemetry routing | `telemetry-1` |
| syslog and security intake | `syslog-1` |
| live health | `health-1` |
| metrics history | `metrics-1` |
| traces and APM | `apm-1` |
| log and event search | `logs-1` |
| dashboard entry | `telemetry-ui-1` |
| archive writer | `archive-1` |

Scale it by enabling the commented Terraform and inventory examples for
`telemetry-2`, `syslog-2`, and `logs-2`/`logs-3` when the environment needs
more availability or retention.
