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
from intake_engineering_view import graph
from software_intake import run


class IntakeEngineeringSemantics(IntakeModelFixture):
    def test_native_objective_allocation_satisfaction_and_verification_are_distinct(self):
        edges={(e['from'],e['kind'],e['to']) for e in self.model['edges']}
        self.assertTrue({('UC-update','requires','REQ-policy'),('F-admit','allocated-to','L-Proxy'),
            ('L-Proxy','satisfies','REQ-policy'),('VC-http-denied','verifies','REQ-policy')}<=edges)
        self.assertEqual({e['to'] for e in self.model['edges'] if e['kind']=='satisfies'},{'REQ-policy'})
        self.assertTrue(all(r['constraints'] for r in self.model['requirements'].values()))

    def test_native_acceptance_is_the_only_plan_source(self):
        self.assertEqual(case_plan(self.model),json.loads((self.root/'architecture/test/software-intake/cases.json').read_text()))
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

    def test_drawing_cannot_invent_or_expose_a_missing_relation(self):
        with self.assertRaisesRegex(ValueError,'invented'):
            graph(self.root,self.model,['L-Proxy','REQ-policy'],[{'from':'REQ-policy','to':'L-Proxy','kind':'satisfies'}])
        model=copy.deepcopy(self.model);model['views']['VIEW-engineering'].remove('L-Proxy')
        with self.assertRaisesRegex(ValueError,'unexposed'):
            graph(self.root,model,['L-Proxy'],[])


@unittest.skipUnless(all(os.environ.get('SYSML_'+n) for n in ('JAVA','KERNEL','LIBRARY')),'Native SysML tools required')
class IntakeNativeEngineeringChange(IntakeModelFixture):
    def test_native_verify_edit_changes_projection_and_requirements_view(self):
        name='architecture/test/software-intake/verification.sysml'
        self.change(name,'subject cache : DisposableCache;\n        objective { verify independentRecovery; }',
            'subject client : UpdateClient;\n        objective { verify noBypass; }')
        args=Namespace(**{n.lower():os.environ['SYSML_'+n] for n in ('JAVA','KERNEL','LIBRARY')})
        model=run(self.root,'build',args)
        self.assertEqual(model['verification']['VC-custody']['requirements'],['REQ-egress'])
        self.assertNotEqual(self.model['verification']['VC-custody'],model['verification']['VC-custody'])
        self.assertIn('VC-custody',(self.root/'architecture/generated/software-intake/engineering-REQ-egress.dot').read_text())
        self.assertNotIn('VC-custody',(self.root/'architecture/generated/software-intake/engineering-REQ-custody.dot').read_text())


if __name__=='__main__':unittest.main()
