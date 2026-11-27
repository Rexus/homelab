"""Protect snapshot import checks against missing, duplicated and disconnected model elements."""

import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/architecture"))
from syson_model import structural_projection, compare, named_elements
from syson_views import select_views, verify_diagrams, hidden_details
from syson_api import objects


class SysONCompatibility(unittest.TestCase):
    def setUp(self):
        self.raw = [
            {"@id": "d", "@type": "PartDefinition", "declaredName": "Provider", "declaredShortName": "DEF"},
            {"@id": "a", "@type": "PartUsage", "declaredName": "consumer", "declaredShortName": "A", "isComposite": True,
             "type": [{"@id": "d"}], "documentation": [{"@id": "doc"}]},
            {"@id": "b", "@type": "PartUsage", "declaredName": "provider", "declaredShortName": "B", "isComposite": True},
            {"@id": "doc", "@type": "Documentation", "body": "Admit before forwarding."},
            {"@id": "edge", "@type": "Dependency", "declaredShortName": "E", "declaredName": "uses",
             "source": [{"@id": "a"}], "target": [{"@id": "b"}]},
        ]
        self.keys = ["DEF", "A", "B", "E"]
        self.expected = structural_projection(self.raw, self.keys)

    def test_native_verification_satisfaction_and_constraint_meaning_cannot_be_lost(self):
        raw = self.raw + [
            {"@id": "r", "@type": "RequirementUsage", "declaredShortName": "REQ",
             "requiredConstraint": [{"@id": "c"}]},
            {"@id": "c", "@type": "ConstraintUsage", "documentation": [{"@id": "doc"}]},
            {"@id": "v", "@type": "VerificationCaseDefinition", "declaredShortName": "VC",
             "verifiedRequirement": [{"@id": "r"}]},
            {"@id": "s", "@type": "SatisfyRequirementUsage", "declaredShortName": "SAT",
             "satisfiedRequirement": {"@id": "r"}, "satisfyingFeature": {"@id": "a"}},
        ]
        keys = self.keys + ["REQ", "VC", "SAT"]
        expected = structural_projection(raw, keys)
        for identity, field in (("r", "requiredConstraint"), ("v", "verifiedRequirement"),
                                ("s", "satisfiedRequirement"), ("s", "satisfyingFeature")):
            with self.subTest(identity=identity, field=field):
                changed = copy.deepcopy(raw)
                next(e for e in changed if e["@id"] == identity).pop(field)
                with self.assertRaisesRegex(ValueError, "compatibility mismatch"):
                    compare(expected, structural_projection(changed, keys))

    def test_uuid_changes_and_text_whitespace_do_not_change_model_meaning(self):
        changed = copy.deepcopy(self.raw)
        changed[3]["body"] = "Admit\r\n before  forwarding."
        changed[0]["@id"] = "different-definition-uuid"
        changed[1]["type"][0]["@id"] = "different-definition-uuid"
        compare(self.expected, structural_projection(changed, self.keys))

    def test_stored_verification_paths_survive_unimplemented_derived_getters(self):
        raw = self.raw + [
            {"@id": "r", "@type": "RequirementUsage", "declaredShortName": "REQ"},
            {"@id": "v", "@type": "VerificationCaseDefinition", "declaredShortName": "VC",
             "ownedRelationship": [{"@id": "objective"}]},
            {"@id": "objective", "@type": "ObjectiveMembership", "ownedRelatedElement": [{"@id": "obj"}]},
            {"@id": "obj", "@type": "RequirementUsage", "ownedRelationship": [{"@id": "verify"}]},
            {"@id": "verify", "@type": "RequirementVerificationMembership",
             "ownedRelatedElement": [{"@id": "ref"}]},
            {"@id": "ref", "@type": "RequirementUsage", "ownedRelationship": [{"@id": "subset"}]},
            {"@id": "subset", "@type": "ReferenceSubsetting", "referencedFeature": {"@id": "r"}},
            {"@id": "s", "@type": "SatisfyRequirementUsage", "declaredShortName": "SAT",
             "ownedRelationship": [{"@id": "subject"}]},
            {"@id": "subject", "@type": "SubjectMembership", "ownedRelatedElement": [{"@id": "feature"}]},
            {"@id": "feature", "@type": "ReferenceUsage", "ownedRelationship": [{"@id": "binding"}]},
            {"@id": "binding", "@type": "FeatureValue", "value": {"@id": "expression"}},
            {"@id": "expression", "@type": "FeatureReferenceExpression", "referent": {"@id": "a"}},
        ]
        keys = self.keys + ["REQ", "VC", "SAT"]
        expected = structural_projection(raw, keys)
        self.assertEqual(expected['VC']['verifiedRequirement'], ['REQ'])
        self.assertEqual(expected['SAT']['satisfyingFeature'], ['A'])
        for identity, field in (("ref", "ownedRelationship"), ("verify", "ownedRelatedElement"),
                                ("feature", "ownedRelationship"), ("expression", "referent")):
            with self.subTest(identity=identity):
                changed = copy.deepcopy(raw)
                next(e for e in changed if e['@id'] == identity).pop(field)
                with self.assertRaisesRegex(ValueError, 'compatibility mismatch'):
                    compare(expected, structural_projection(changed, keys))

    def test_lost_inferred_type_is_rejected(self):
        self.raw[1]["type"] = []
        with self.assertRaisesRegex(ValueError, "mismatch: A"):
            compare(self.expected, structural_projection(self.raw, self.keys))

    def test_changed_contract_is_detected(self):
        self.raw[3]["body"] = "Forward before admission."
        with self.assertRaisesRegex(ValueError, "mismatch: A"):
            compare(self.expected, structural_projection(self.raw, self.keys))

    def test_missing_contract_port_or_note_body_is_rejected(self):
        raw = self.raw + [
            {"@id": "port", "@type": "PortUsage", "declaredName": "listener", "owner": {"@id": "d"},
             "type": [{"@id": "d"}]},
            {"@id": "note", "@type": "Documentation", "declaredShortName": "DOC", "body": "Admit first."},
        ]
        expected = structural_projection(raw, self.keys + ["DOC"])
        changed = copy.deepcopy(raw)
        changed[-1]["body"] = "Forward first."
        with self.assertRaisesRegex(ValueError, "mismatch: DOC"):
            compare(expected, structural_projection(changed, self.keys + ["DOC"]))
        with self.assertRaisesRegex(ValueError, "mismatch: DEF"):
            compare(expected, structural_projection(raw[:-2] + [raw[-1]], self.keys + ["DOC"]))

    def test_missing_and_duplicate_identities_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing model identities"):
            structural_projection(self.raw[:-1], self.keys)
        with self.assertRaisesRegex(ValueError, "Duplicate stable"):
            named_elements(self.raw + [self.raw[0]])

    def test_unresolved_or_reversed_dependency_is_rejected(self):
        self.raw[-1]["target"] = [{"@id": "missing"}]
        with self.assertRaisesRegex(ValueError, "Unresolved relationship"):
            structural_projection(self.raw, self.keys)
        self.raw[-1]["target"] = [{"@id": "a"}]
        self.raw[-1]["source"] = [{"@id": "b"}]
        with self.assertRaisesRegex(ValueError, "mismatch: E"):
            compare(self.expected, structural_projection(self.raw, self.keys))

    def test_diagram_uses_persistence_ids_and_cannot_omit_selected_dependencies(self):
        stored = [{"id": "ui-" + key, "eClass": "sysml:PartUsage",
                   "data": {"declaredShortName": key, "elementId": "api-" + key}} for key in self.keys]
        view = {"key": "view", "name": "Overall", "boxes": {"A": [], "B": []}, "edges": ["E"]}
        diagram = {"nodes": [{"targetObjectId": "ui-A"}, {"targetObjectId": "ui-B"}],
                   "edges": [{"targetObjectId": "ui-E"}]}
        verify_diagrams([view], stored, {"r": diagram}, {"view": {"id": "r"}})
        diagram["edges"] = []
        with self.assertRaisesRegex(ValueError, "Missing diagram relationship"):
            verify_diagrams([view], stored, {"r": diagram}, {"view": {"id": "r"}})
        self.assertEqual(len(list(objects({"content": stored}))), len(stored))

    def test_layout_success_requires_persisted_positions(self):
        stored = [{"id": "ui-A", "data": {"declaredShortName": "A"}}]
        views = [{"key": "view", "name": "Overall", "boxes": {"A": [40, 100, 380, 96]}, "edges": []}]
        diagram = {"nodes": [{"id": "node-A", "targetObjectId": "ui-A"}], "edges": []}
        with self.assertRaisesRegex(ValueError, "Diagram layout mismatch"):
            verify_diagrams(views, stored, {"r": diagram}, {"view": {"id": "r"}}, layout=True)

        diagram["layoutData"] = {"nodeLayoutData": {"node-A": {
            "position": {"x": 40, "y": 100}, "size": {"width": 380, "height": 120}}}}
        verify_diagrams(views, stored, {"r": diagram}, {"view": {"id": "r"}}, layout=True)
        diagram["layoutData"]["nodeLayoutData"]["node-A"]["position"]["x"] = 0
        with self.assertRaisesRegex(ValueError, "Diagram layout mismatch"):
            verify_diagrams(views, stored, {"r": diagram}, {"view": {"id": "r"}}, layout=True)

    def test_impact_cannot_reveal_compartments_or_hide_a_required_root(self):
        stored = [{"id": "ui-A", "eClass": "sysml:PartUsage", "data": {"declaredShortName": "A"}}]
        view = {"key": "v", "name": "Impact", "compact": True, "boxes": {"A": [0,0,100,80]}, "edges": []}
        diagram = {"nodes": [{"id": "n", "targetObjectId": "ui-A", "state": "Normal",
                              "childNodes": [{"id": "details", "state": "Normal"}]}], "edges": [],
                   "layoutData": {"nodeLayoutData": {"n": {"position": {"x":0,"y":0},
                                                              "size": {"width":100,"height":80}}}}}
        with self.assertRaisesRegex(ValueError, 'visibility mismatch'):
            verify_diagrams([view],stored,{'r':diagram},{'v':{'id':'r'}},layout=True)
        diagram['nodes'][0]['childNodes'][0]['state'] = 'Hidden'
        verify_diagrams([view],stored,{'r':diagram},{'v':{'id':'r'}},layout=True)
        diagram['nodes'][0]['state'] = 'Hidden'
        with self.assertRaisesRegex(ValueError, 'selection mismatch'):
            verify_diagrams([view],stored,{'r':diagram},{'v':{'id':'r'}},layout=True)

class SysONViewSelection(unittest.TestCase):
    def test_new_consumers_change_only_impact_and_overall_selection_is_preserved(self):
        root = Path(__file__).resolve().parents[1]
        overall = json.loads((root / "scripts/architecture/config/views/system-overall.json").read_text())['views'][0]
        keys = [n['key'] for n in overall['nodes']] + ['DEF-proxy', 'DOC-proxy-contract', 'consumer-1']
        raw = [{'@id': k, '@type': 'PartUsage', 'declaredShortName': k,
                'qualifiedName': 'Example::' + k} for k in keys]
        raw[-3]['@type'] = 'PartDefinition'
        raw[-2].update({'@type': 'Documentation', 'owner': {'@id': 'DEF-proxy'}})
        model = {'edges': [{'from': 'consumer-1', 'to': 'DEF-proxy', 'kind': 'typed-by'}]}
        before, _ = select_views(root, raw, model)
        raw.append({'@id': 'new', '@type': 'PartUsage', 'declaredShortName': 'consumer-2',
                    'qualifiedName': 'Example::newConsumer'})
        model['edges'].append({'from': 'consumer-2', 'to': 'DEF-proxy', 'kind': 'typed-by'})
        after, _ = select_views(root, raw, model)
        self.assertEqual(before[:2], after[:2])
        self.assertEqual(after[0]['boxes'], {n['key']: n['box'] for n in overall['nodes']})
        self.assertEqual(after[0]['edges'], [e['id'] for e in overall['edges']])
        self.assertEqual(set(after[1]['boxes']), {'DEF-proxy'})
        self.assertEqual(after[1]['documentation'], 'DOC-proxy-contract')
        self.assertEqual(set(after[2]['consumers']), {'consumer-1', 'consumer-2'})
        raw[-3]['owner'] = {'@id': 'another-definition'}
        with self.assertRaisesRegex(ValueError, 'Contract text must be owned'):
            select_views(root, raw, model)



if __name__ == "__main__":
    unittest.main()
