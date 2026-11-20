"""Bounded semantic checks over native SysML objects, not a source-language parser.

OMG SysML 2.0 §§7.13.4, 7.17.3, 7.17.9. The fan-in rule is a project
restriction for the single-path retrieval experiment, not a universal language rule.
"""

from collections import defaultdict
from intake_sources import require


def check_language(objects, scoped_ids):
    assignments, targets = 0, set()
    for uid in scoped_ids:
        action = objects[uid]
        if action['@type'] != 'AssignmentActionUsage':
            continue
        referent = objects[action['referent']['@id']]
        target = objects[referent.get('featureTarget', {'@id': referent['@id']})['@id']]
        label = target.get('qualifiedName') or target.get('name') or target['@id']
        require(target.get('mayTimeVary') and not target.get('isConstant'),
                label + ': assignment target must allow changing values')
        values = [objects[r['@id']] for r in target.get('ownedMembership', [])
                  if objects[r['@id']]['@type'] == 'FeatureValue']
        # In this executable subset, assigned state must not also have a bound value.
        # Supporting an intentionally consistent bound expression needs separate analysis.
        require(all(value['isInitial'] for value in values),
                label + ': assigned state has a bound value; use initial := rather than =')
        targets.add(label)
        assignments += 1

    merges = []
    for uid in scoped_ids:
        definition = objects[uid]
        if definition.get('declaredShortName') != 'X-HTTP':
            continue
        incoming, outgoing = defaultdict(list), defaultdict(list)
        for ref in definition.get('ownedFeature', []):
            succession = objects[ref['@id']]
            if succession['@type'] not in ('SuccessionAsUsage', 'SuccessionUsage'):
                continue
            source = succession['sourceFeature']['@id']
            for target in succession['targetFeature']:
                incoming[target['@id']].append(source)
                outgoing[source].append(target['@id'])
        for target, sources in incoming.items():
            element = objects[target]
            if len(sources) > 1:
                require(element['@type'] == 'MergeNode',
                        'X-HTTP::' + element['name'] + ': alternative paths need an explicit merge')
                require(len(outgoing[target]) == 1,
                        'X-HTTP::' + element['name'] + ': merge needs one outgoing succession')
                merges.append(element.get('declaredShortName', element['name']))
    return {'scope': 'Assigned state and explicit convergence in the single-path HTTP experiment; not full conformance',
            'assignments_checked': assignments, 'assigned_features': sorted(targets),
            'alternative_merges': sorted(merges)}
