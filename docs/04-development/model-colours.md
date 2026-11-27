# Engineering-role colours

The connected model views use a project-independent personal colour profile. Exact colours live in
[palette.json](../08-reference/diagrams/palette.json); native model classification and frame styles live
in [notation.json](../../scripts/architecture/config/views/notation.json). This is not an OMG standard colour code.

| Colour | Role | Examples across domains |
| --- | --- | --- |
| Blue | Logical responsibility or virtual resource | Access control, motion control, virtual disk |
| Green | Software implementation | Cache process, web service, controller firmware, simulator program |
| Warm yellow | Physical equipment | Server, switch, sensor, actuator, airframe |
| Peach | Behavior / function | Authorize a request, move to target |
| Rose | Information / content | Cached response, order data, trajectory |
| Violet | Use case / requirement | Checkout goal, safety constraint |
| Teal | Verification | Authentication test, simulation assertion |

In software intake, the abstract `PolicyProxy` contract and logical responsibility remain blue.
The proxy software inside each virtual member is green. A reviewed rule selects native `PartUsage`
objects of type `DEF-proxy` owned by a `DEF-member` usage/definition; it does not depend on member count,
ID prefixes or the words Squid/keepalived. Virtual disks remain blue, stored content remains rose,
and the actual platform hardware is yellow. VM/runtime frames keep their separate light treatment.

Every element retains its role across views. Green does not mean healthy or verified, and yellow does
not mean offline or protected. Those properties need explicit labels. Accepted legacy operations
figures keep their separate custody palette; do not silently combine its meanings with this profile.
Not every view should contain every colour. In particular, the compact System Overall is conceptual.

## Reproduce and check

Regenerate with the [native model workflow](../01-architecture/07-software-intake/02-connected-model.md).
The SVG renderer and [SysON adapter](syson.md) read the same project palette. Native publication remains
limited to its explicit selected views; adding a colour or SVG does not publish another diagram.
Tests cover classification under changed ownership, future member names, paired foreground/fill/border
and adapter correspondence. Match roles and preserve meaning; do not promise arbitrary renderer styles
will survive a model round trip.

## Checked pilot

On 2026-11-20, 16 focused-view and native-palette adapter tests passed. Browser checks confirmed
computed software/storage/content/hardware colours and captured 16 previews across four figures,
two widths and light/dark backgrounds. All model-role text pairs exceed 8:1 contrast; borders exceed
3:1. These checks do not establish complete accessibility or native live-view parity.

The existing SysON review was not republished by this palette pass. Its appearance remains its saved
baseline until the normal review/publication workflow applies the shared profile. The selected native
view set is unchanged, and documented renderer limitations remain in force.

## References

Reviewed 2026-11-20. SysML defines more than logical and physical structure and permits user-defined
views; this presentation layer preserves the model's actual types and relationships. [1]
SysON supports themes and manual colour overrides through appearance settings. [2]

1. [OMG SysML 2.0 Language, §§7.11, 7.17, 7.20–7.26 and 8.2.3.1](https://www.omg.org/spec/SysML/2.0/Language/PDF).
2. [Eclipse SysON: Interconnection view, Theme](https://doc.mbse-syson.org/syson/main/user-manual/features/interconnection-view.html#_syson_theme).
