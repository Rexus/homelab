"""Render observed native runs with the same participant, message and function identities."""

from copy import deepcopy
import json
from intake_execution import EVIDENCE, VIEW, GUIDE, load_evidence
from intake_scenario_views import scenario_views
from design_context import scopes
from svg_pages import page, grid, card, assets, finish, book, SCENARIOS


def execution_outputs(root, model, records, sources, report=None):
    if 'execution' not in model:
        return {}
    status = "Native model execution; supplied availability and trust outcomes, no live traffic."
    if report is None:
        report, status = load_evidence(root, model, sources)
    origin = VIEW.as_posix()
    svg, y, nav = page(origin, 'HTTP retrieval | native execution', status, GUIDE)
    rows = []
    scenario_order = json.loads((root/'scripts/architecture/config/views/software-intake/use-cases.json').read_text())['scenarios']
    order = sorted(model['execution']['runs'], key=lambda k: scenario_order.index(model['execution']['runs'][k]['scenario']))
    for key in order:
        run = model['execution']['runs'][key]
        result = report['runs'][key] if report else None
        detail = ('Observed: ' + result['values']['outcome'] + '. Source attempts: ' +
                  str(result['values']['sourceRequests']) + '; client checks: ' +
                  str(result['values']['verificationChecks']) + '.') if result else 'Expected scenario: ' + run['scenario']
        rows.append((run['name'], detail, origin+'#'+key if result else SCENARIOS+'#'+run['scenario'], key))
    y = grid(svg, origin, y, rows)
    y += card(svg, origin, 30, y, 900, 'Compare with real software',
        'Observed Squid cache results and APT verification, compared with these same expectations.',
        'docs/01-architecture/07-software-intake/06-implementation-comparison.md') + 12
    y = assets(svg, origin, y, [('Native model and experiments', [
        'architecture/models/software-intake/analysis/SoftwareIntakeRetrievalAnalysis.sysml',
        'architecture/models/software-intake/analysis/SoftwareIntakeRetrievalAnalysis.sysml',
        'architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml']), ('Evidence and scope',
        [GUIDE] + ([EVIDENCE.as_posix()] if report or (root/EVIDENCE).is_file() else []))])
    nav[2] = ('Expected HTTP', SCENARIOS+'#SC-http-miss')
    pages = [('index', finish(svg, origin, y, nav))]
    if report:
        observed_model = deepcopy(model)
        plan = {}
        observations = {}
        for key, result in report['runs'].items():
            scenario = deepcopy(model['scenarios'][result['scenario']])
            scenario['messages'] = [event['message'] for event in result['events']]
            scenario['docs'] = {
                'Trigger': model['execution']['runs'][key]['name'] + '.',
                'Preconditions': scenario['docs']['Preconditions'],
                'Outcome': 'Observed ' + result['values']['outcome'] + '. Cache lookups: ' +
                    str(result['values']['cacheLookups']) + '; source attempts: ' + str(result['values']['sourceRequests']) +
                    '; client verification checks: ' + str(result['values']['verificationChecks']) + '.',
            }
            observed_model['scenarios'][key] = scenario
            plan[key] = {'acceptance': 'Executed actions and outputs match the modeled scenario. Trust and source availability are supplied inputs; this is not product or deployed-network verification.'}
            observations[key] = {'scenario': result['scenario'], 'events': result['events']}
        pages += scenario_views(root, observed_model, scopes(root), records, plan,
            origin=origin, order=order, observed=observations, return_pages=True)
    return {VIEW: book(pages)}
