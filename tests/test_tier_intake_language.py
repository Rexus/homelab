"""Reject semantic regressions that a successful parser or permissive runner may miss."""

from argparse import Namespace
import os
import unittest
from intake_model_fixture import IntakeModelFixture
from intake_language import check_language
from software_intake import run


class NativeObjectRules(unittest.TestCase):
    def fixture(self):
        # Minimal resolved native-object shapes, using the export fields rather than SysML text.
        objects = {
            'x': {'@id': 'x', '@type': 'ActionDefinition', 'declaredShortName': 'X-HTTP',
                  'ownedFeature': [{'@id': k} for k in ('a-m', 'b-m', 'm-c')]},
            'assignment': {'@id': 'assignment', '@type': 'AssignmentActionUsage', 'referent': {'@id': 'state'}},
            'state': {'@id': 'state', '@type': 'AttributeUsage', 'name': 'count', 'mayTimeVary': True,
                      'isConstant': False, 'ownedMembership': [{'@id': 'initial'}]},
            'initial': {'@id': 'initial', '@type': 'FeatureValue', 'isInitial': True},
            'm': {'@id': 'm', '@type': 'MergeNode', 'name': 'contentReady'},
        }
        for name, source, target in (('a-m', 'a', 'm'), ('b-m', 'b', 'm'), ('m-c', 'm', 'c')):
            objects[name] = {'@id': name, '@type': 'SuccessionAsUsage',
                             'sourceFeature': {'@id': source}, 'targetFeature': [{'@id': target}]}
        objects['c'] = {'@id': 'c', '@type': 'ActionUsage', 'name': 'verify'}
        return objects

    def test_initial_values_and_alternative_merge_are_accepted(self):
        objects = self.fixture()
        result = check_language(objects, set(objects))
        self.assertEqual(result['assignments_checked'], 1)
        self.assertEqual(result['alternative_merges'], ['contentReady'])

    def test_binding_cannot_be_misread_as_initialization(self):
        objects = self.fixture()
        objects['initial']['isInitial'] = False
        with self.assertRaisesRegex(ValueError, 'bound value'):
            check_language(objects, set(objects))

    def test_assignment_requires_changeable_target(self):
        for field, value in (('isConstant', True), ('mayTimeVary', False)):
            objects = self.fixture()
            objects['state'][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'changing values'):
                check_language(objects, set(objects))

    def test_alternatives_cannot_be_conflated_with_join_or_ordinary_action(self):
        for kind in ('JoinNode', 'ActionUsage'):
            objects = self.fixture()
            objects['m']['@type'] = kind
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'explicit merge'):
                check_language(objects, set(objects))


@unittest.skipUnless(all(os.environ.get('SYSML_' + n) for n in ('JAVA', 'KERNEL', 'LIBRARY')),
                     'Native SysML tools required')
class NativeSourceRegressions(IntakeModelFixture):
    def reject(self, before, after, diagnostic):
        self.change('architecture/functions/software-intake/retrieval-execution.sysml', before, after)
        args = Namespace(**{n.lower(): os.environ['SYSML_' + n] for n in ('JAVA', 'KERNEL', 'LIBRARY')})
        with self.assertRaisesRegex(ValueError, diagnostic):
            run(self.root, 'build', args)

    def test_native_bound_counter_regression_is_rejected(self):
        self.reject('out sourceRequests : Integer := 0;', 'out sourceRequests : Integer = 0;', 'bound value')

    def test_native_missing_merge_regression_is_rejected(self):
        self.reject("merge <'XM-content'> contentReady;", "action <'XM-content'> contentReady;", 'explicit merge')


if __name__ == '__main__':
    unittest.main()
