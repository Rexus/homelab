"""Project native requirement/case semantics, retaining explicit engineering relation kinds."""

from intake_sources import require


def project_semantics(objects, names, model):
    requirements, verification, analyses, views = {}, {}, {}, {}

    def docs(element):
        return {objects[r['@id']].get('declaredName', ''): objects[r['@id']]['body'].strip()
                for r in element.get('documentation', [])}

    def identified(ref):
        return names.get((ref or {}).get('@id'))

    def subject_type(element):
        subject = objects.get((element.get('subjectParameter') or {}).get('@id'), {})
        return [names[t['@id']] for t in subject.get('type', []) if t['@id'] in names]

    def edge(source, target, kind):
        require(target in model['elements'], f'{source}: unresolved {kind} target')
        model['edges'].append({'from': source, 'to': target, 'kind': kind})

    for uid, key in names.items():
        e = objects[uid]
        if e['@type'] == 'PartUsage':
            model['elements'][key]['composite'] = e.get('isComposite', False)
        if e['@type'] == 'RequirementUsage' and key.startswith('REQ-'):
            constraints = [objects[r['@id']] for r in e.get('requiredConstraint', [])]
            descriptions = [' '.join(docs(c).values()) for c in constraints]
            require(descriptions and all(descriptions), key + ': missing required constraint')
            requirements[key] = {'subject_types': subject_type(e), 'constraints': descriptions,
                                 'satisfaction_review': docs(e).get('SatisfactionReview', '')}
            if not model['elements'][key]['docs']:
                model['elements'][key]['docs'] = descriptions
        if e['@type'] == 'UseCaseDefinition':
            objective = objects[(e['objectiveRequirement'])['@id']]
            for r in objective.get('ownedMembership', []):
                m = objects[r['@id']]
                if m['@type'] == 'RequirementConstraintMembership':
                    target = identified(m.get('referencedConstraint'))
                    if target:
                        edge(key, target, 'requires')
        if e['@type'] == 'VerificationCaseDefinition':
            targets = [identified(r) for r in e.get('verifiedRequirement', [])]
            require(targets and all(targets), key + ': no native verified requirement')
            detail = docs(e)
            require(detail.get('Acceptance'), key + ': missing acceptance intent')
            require(all(detail.get(field) for field in ('Method','Setup','Action')),
                    key + ': verification needs a method, setup and action')
            require(detail['Method'] in ('Inspection','Analysis','Demonstration','Test'),
                    key + ': unsupported verification method')
            scenarios = [r['to'] for r in model['edges'] if r['from'] == key
                         and r['kind'] == 'depends-on' and r['to'] in model['scenarios']]
            verification[key] = {'requirements': targets, 'subject_types': subject_type(e),
                'scenarios': scenarios, 'acceptance': detail['Acceptance'],
                'method': detail['Method'], 'setup': detail['Setup'], 'action': detail['Action'],
                **({'manual': detail['Manual']} if detail.get('Manual') else {})}
            for target in targets:
                edge(key, target, 'verifies')
        if e['@type'] == 'AnalysisCaseDefinition':
            analyses[key] = {'subject_types': subject_type(e)}
        if e['@type'] == 'ViewUsage':
            views[key] = sorted(names[r['@id']] for r in e.get('exposedElement', []) if r['@id'] in names)
        if e['@type'] == 'SatisfyRequirementUsage':
            requirement = identified(e.get('satisfiedRequirement'))
            feature = e.get('satisfyingFeature')
            if feature:
                f = objects[feature['@id']]
                chained = f.get('chainingFeature', [])
                source = identified(chained[-1] if chained else feature)
                require(source and requirement, key + ': unresolved satisfaction')
                model['edges'].append({'from':source,'to':requirement,'kind':'satisfies','id':key})
    model.update(requirements=requirements, verification=verification, analyses=analyses, views=views)
    for key, case in verification.items():
        for target in case['requirements']:
            require(set(case['subject_types']) & set(requirements[target]['subject_types']),
                    key + ': verification subject does not match requirement subject')


def case_plan(model):
    """Compatibility projection for existing scenario views; semantic ownership is SysML."""
    plan = {}
    for key, case in model['verification'].items():
        for scenario in case['scenarios']:
            require(scenario not in plan, 'Multiple acceptance owners for ' + scenario)
            plan[scenario] = {k:case[k] for k in ('acceptance','manual') if k in case}
    require(set(plan) == set(model['scenarios']), 'Missing native scenario acceptance case')
    return plan
