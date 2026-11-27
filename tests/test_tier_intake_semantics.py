"""Engineering meaning, external evidence and model-backed alternative evaluation."""
import copy
import json
import os
from argparse import Namespace
from pathlib import Path
import unittest
from intake_model_fixture import IntakeModelFixture
from intake_semantics import case_plan, project_semantics
from intake_model import impact
from intake_reverse import review
from intake_sources import trace_map
from view_catalog import selections
import xml.etree.ElementTree as ET
from software_intake import run


class IntakeEngineeringSemantics(IntakeModelFixture):
    def test_native_objective_allocation_satisfaction_and_verification_are_distinct(self):
        edges={(e['from'],e['kind'],e['to']) for e in self.model['edges']}
        self.assertTrue({('UC-update','requires','REQ-policy'),('F-admit','allocated-to','L-Proxy'),
            ('L-Proxy','satisfies','REQ-policy'),('L-Consumers','satisfies','REQ-integrity'),('VC-http-denied','verifies','REQ-policy')}<=edges)
        self.assertEqual({e['to'] for e in self.model['edges'] if e['kind']=='satisfies'},{'REQ-policy','REQ-integrity'})
        self.assertTrue(all(r['constraints'] for r in self.model['requirements'].values()))

    def test_native_acceptance_is_the_only_plan_source(self):
        self.assertEqual(case_plan(self.model),json.loads((self.root/'artifacts/architecture/evidence/software-intake/cases.json').read_text()))
        model=copy.deepcopy(self.model)
        model['verification']['VC-http-denied']['acceptance']='New native acceptance criterion'
        self.assertEqual(case_plan(model)['SC-http-denied']['acceptance'],'New native acceptance criterion')
        del model['verification']['VC-http-denied']
        with self.assertRaisesRegex(ValueError,'Missing native'):case_plan(model)

    def test_requirement_change_reaches_native_verification(self):
        affected=set(impact(self.model,'REQ-policy'))
        self.assertTrue({'UC-update','F-admit','VC-http-denied','AN-admission'}<=affected)

    def test_test_asset_reaches_its_verification_and_correct_guardrail(self):
        result=review(self.model,trace_map(self.root),'tests/test_tier_package_policy.py')
        self.assertIn('VC-integrity',result['verification_cases'])
        self.assertNotIn('VC-http-denied',result['verification_cases'])
        self.assertEqual(set(result['requirements']),{'REQ-integrity'})

    def test_drawing_cannot_invent_a_missing_relation(self):
        svg=ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg"/>')
        svg.set('data-relationships',json.dumps([{'from':'REQ-policy','to':'L-Proxy','kind':'satisfies'}]))
        with self.assertRaisesRegex(ValueError,'invented'):selections(svg,self.model)


@unittest.skipUnless(all(os.environ.get('SYSML_'+n) for n in ('JAVA','KERNEL','LIBRARY')),'Native SysML tools required')
class IntakeNativeEngineeringChange(IntakeModelFixture):
    def test_native_verify_edit_changes_projection_and_requirements_view(self):
        name='architecture/models/software-intake/SoftwareIntakeVerification.sysml'
        self.change(name,'subject cache : DisposableCache;\n        objective { verify independentRecovery; }',
            'subject client : UpdateClient;\n        objective { verify noBypass; }')
        args=Namespace(**{n.lower():os.environ['SYSML_'+n] for n in ('JAVA','KERNEL','LIBRARY')})
        model=run(self.root,'build',args)
        self.assertEqual(model['verification']['VC-custody']['requirements'],['REQ-egress'])
        self.assertNotEqual(self.model['verification']['VC-custody'],model['verification']['VC-custody'])
        table=(self.root/'architecture/generated/software-intake/SoftwareIntakeVerification.md').read_text(encoding='utf-8')
        row=next(line for line in table.splitlines() if line.startswith('| <a id="VC-custody"'))
        self.assertIn('Requirements.md#REQ-egress',row)
        self.assertNotIn('Requirements.md#REQ-custody',row)


if __name__=='__main__':unittest.main()
