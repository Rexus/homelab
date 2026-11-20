"""A focused goal preserves native roles without expanding supporting design internals."""

import copy
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
from tier_repo_test_support import UPSTREAM
from bootstrap_use_case import outputs, VIEW
from diagram_notation import tag
from intake_explorer import target_for
from view_catalog import selections


class BootstrapUseCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = json.loads((UPSTREAM / 'architecture/generated/software-intake/model-index.json')
                               .read_text(encoding='utf-8'))['model']

    def test_native_roles_and_focus_survive_projection(self):
        svg = ET.fromstring(outputs(UPSTREAM, self.model)[VIEW])
        nodes, relations, subject = selections(svg, self.model)
        self.assertEqual(set(nodes), {'UC-clone', 'UC-clone-host', 'ACT-operator', 'ACT-intake'})
        self.assertEqual(subject, 'UC-clone-host')
        self.assertEqual({r['kind'] for r in relations}, {'has-actor', 'has-subject'})
        self.assertEqual(len(relations), 3)
        self.assertEqual(self.model['use_cases']['UC-clone']['bindings']['ACT-intake'], 'SYS-intake')
        self.assertTrue(any(e['from'] == 'UC-clone' and e['to'] == 'SC-https'
                            and e['kind'] == 'depends-on' for e in self.model['edges']))

    def test_supporting_service_opens_design_and_goal_has_own_view(self):
        svg = ET.fromstring(outputs(UPSTREAM, self.model)[VIEW])
        anchor = next(a for a in svg.iter(tag('a'))
                      if a.find(tag('g') + "[@data-model='ACT-intake']") is not None)
        self.assertEqual((VIEW.parent / anchor.get('href')).as_posix(),
                         'architecture/views/platform/hosting/../../software-intake/logical.svg')
        self.assertEqual(target_for(self.model, [], 'UC-clone'), str(VIEW).replace('\\', '/'))

    def test_bootstrap_configuration_traces_back_to_its_goal(self):
        from intake_sources import trace_map
        from intake_reverse import review
        result = review(self.model, trace_map(UPSTREAM),
                        'tier-0/ansible/playbooks/deployment/bootstrap-software-intake.yml')
        self.assertIn('UC-clone', result['use_cases'])
        from intake_reverse_view import model_link
        self.assertEqual(model_link('UC-clone'), VIEW.as_posix())
        self.assertEqual(next(row['state'] for row in result['direct'] if row['element'] == 'UC-clone'), 'documented-context')

    def test_foundation_destination_rejects_the_wrong_part(self):
        import tempfile
        from bootstrap_reference import SOURCE, VIEW as FOUNDATION, validate_reference
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for asset in (SOURCE, FOUNDATION):
                target = root / asset
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text((UPSTREAM / asset).read_text(encoding='utf-8'), encoding='utf-8')
            validate_reference(root)
            target = root / FOUNDATION
            target.write_text(target.read_text(encoding='utf-8').replace(
                'data-model="BOOT-host"', 'data-model="L-Consumers"'), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'bound boot-1 participant'):
                validate_reference(root)

    def test_wrong_supporting_subject_binding_is_rejected(self):
        model = copy.deepcopy(self.model)
        model['use_cases']['UC-clone']['bindings']['ACT-intake'] = 'BOOT-host'
        with self.assertRaisesRegex(ValueError, 'native subject and actor bindings'):
            outputs(UPSTREAM, model)


if __name__ == '__main__':
    unittest.main()
