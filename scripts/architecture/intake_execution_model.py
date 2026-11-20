"""Project the native executable refinement and fixed experiments, without interpreting SysML."""

import json
from intake_sources import require


def project_execution(objects, names, model):
    definitions = [uid for uid, key in names.items() if key == 'X-HTTP']
    if not definitions:
        return
    definition = objects[definitions[0]]
    actions = {}
    for ref in definition.get('ownedFeature', []):
        element = objects[ref['@id']]
        key = names.get(ref['@id'], '')
        if not key.startswith(('X-', 'XD-', 'XM-')):
            continue
        targets = [e['to'] for e in model['edges'] if e['from'] == key and e['kind'] == 'depends-on']
        if key.startswith('X-'):
            require(len(targets) == 1 and model['elements'][targets[0]]['kind'] == 'FlowUsage',
                    key + ': executable action needs one native sequence correspondence')
        actions[key] = {'name': element['declaredName'], 'message': targets[0] if targets else None}
    require(len({a['name'] for a in actions.values()}) == len(actions), 'Ambiguous execution action names')
    runs = {}
    for uid, key in names.items():
        if not key.startswith('RUN-') or objects[uid]['@type'] != 'ActionUsage':
            continue
        element = objects[uid]
        require(element['@type'] == 'ActionUsage' and definitions[0] in
                {r['@id'] for r in element.get('type', [])}, key + ': run must use the executable refinement')
        inputs = {}
        for ref in element.get('ownedFeature', []):
            feature = objects[ref['@id']]
            if feature.get('direction') != 'in':
                continue
            values = [objects[r['@id']] for r in feature.get('ownedMembership', [])
                      if objects[r['@id']]['@type'] == 'FeatureValue']
            require(len(values) == 1, key + ': run input needs one value')
            value = objects[values[0]['value']['@id']]
            require(value['@type'] == 'LiteralBoolean', key + ': experiment inputs must be Boolean')
            inputs[feature['name']] = value['value']
        docs = {objects[r['@id']].get('declaredName'): objects[r['@id']]['body']
                for r in element.get('documentation', [])}
        expected = json.loads(docs['Expected'])
        scenarios = [e['to'] for e in model['edges'] if e['from'] == key and e['kind'] == 'depends-on'
                     and e['to'] in model['scenarios']]
        require(len(scenarios) == 1, key + ': run needs one expected scenario')
        require(len(inputs) == 6, key + ': bind every environment input explicitly')
        runs[key] = {'name': element['declaredName'], 'qualified_name': element['qualifiedName'],
                     'inputs': inputs, 'expected': expected, 'scenario': scenarios[0]}
        model['edges'].append({'from': key, 'to': 'X-HTTP', 'kind': 'typed-by'})
    model['execution'] = {'definition': 'X-HTTP', 'actions': actions, 'runs': dict(sorted(runs.items()))}
