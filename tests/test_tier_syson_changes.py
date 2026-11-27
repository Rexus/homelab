"""Protect source ownership, unsupported-change refusal and semantic return-path checks."""

from argparse import Namespace
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/architecture"))
from syson_api import objects
from syson_change_model import Graph, changed_roots, compare_roots
from syson_change_source import index_source, propose, edited_sources, sha
from syson_change_workspace import checked_path, replace_sources, runtime_inputs
from intake_intent import intent_report, case_target


def obj(identity, kind, **data):
    return {"id": identity, "eClass": "sysml:" + kind, "data": {"elementId": "semantic-" + identity, **data}}


def requirement(key="REQ-one", suffix=""):
    return obj("r"+suffix, "RequirementUsage", reqId=key, declaredName="admission"+suffix,
        ownedRelationship=[obj("m"+suffix, "OwningMembership", ownedRelatedElement=[
            obj("d"+suffix, "Documentation", body="Deny before fetching.")])])


def fixture():
    return obj("pkg", "Package", declaredName="Requirements", ownedRelationship=[
        obj("root-member", "OwningMembership", ownedRelatedElement=[requirement()]),
        obj("part-member", "OwningMembership", ownedRelatedElement=[
            obj("part", "PartUsage", declaredShortName="L-proxy", declaredName="proxy")])])


def flat(tree):
    return list(objects(tree))


class SemanticChangeBoundary(unittest.TestCase):
    def test_no_change_and_documentation_change(self):
        before = fixture()
        self.assertEqual(changed_roots(flat(before), flat(before)), ([], []))
        after = copy.deepcopy(before)
        next(o for o in objects(after) if o["id"] == "d")["data"]["body"] = "Deny before cache lookup."
        self.assertEqual(changed_roots(flat(before), flat(after)), (["REQ-one"], []))
        with self.assertRaisesRegex(ValueError, "semantic round trip"):
            compare_roots(flat(after), flat(before), ["REQ-one"])

    def test_addition_and_private_membership_refusal(self):
        before, after = fixture(), fixture()
        wrapper = obj("new-member", "OwningMembership", ownedRelatedElement=[requirement("REQ-two", "2")])
        after["data"]["ownedRelationship"].append(wrapper)
        self.assertEqual(changed_roots(flat(before), flat(after)), (["REQ-two"], ["REQ-two"]))
        wrapper["data"]["visibility"] = "private"
        with self.assertRaisesRegex(ValueError, "unsupported membership"):
            changed_roots(flat(before), flat(after))

    def test_documentation_whitespace_remains_a_supported_edit(self):
        before, after = fixture(), fixture()
        next(o for o in objects(after) if o['id'] == 'd')['data']['body'] = '  Deny before fetching.\n'
        self.assertEqual(changed_roots(flat(before), flat(after)), (['REQ-one'], []))
        compare_roots(flat(before), flat(after), ['REQ-one'])

    def test_unidentified_new_element_is_not_silently_dropped(self):
        before, after = fixture(), fixture()
        after["data"]["ownedRelationship"].append(obj("new-member", "OwningMembership",
            ownedRelatedElement=[obj("new", "UseCaseDefinition", declaredName="Unidentified")]))
        with self.assertRaisesRegex(ValueError, "unsupported semantic change"):
            changed_roots(flat(before), flat(after))

    def test_unsupported_part_edit_blocks_the_whole_import(self):
        before, after = fixture(), fixture()
        next(o for o in objects(after) if o["id"] == "part")["data"]["declaredName"] = "changed"
        next(o for o in objects(after) if o["id"] == "d")["data"]["body"] = "New criterion"
        with self.assertRaisesRegex(ValueError, "L-proxy: unsupported"):
            changed_roots(flat(before), flat(after))

    def test_deletion_or_identity_change_is_refused(self):
        before = fixture()
        for mode in ("delete", "rename-id"):
            with self.subTest(mode=mode):
                after = copy.deepcopy(before)
                if mode == "delete":
                    after["data"]["ownedRelationship"].pop(0)
                else:
                    next(o for o in objects(after) if o["id"] == "r")["data"]["reqId"] = "REQ-changed"
                with self.assertRaisesRegex(ValueError, "deleted or stable identity"):
                    changed_roots(flat(before), flat(after))

    def test_uuid_replacement_preserves_semantics_but_not_changed_bindings(self):
        before = fixture()
        next(o for o in objects(before) if o["id"] == "r")["data"]["related"] = "part"
        ids = {o["id"] for o in objects(before)}
        def remap(value):
            if isinstance(value, dict): return {k: remap(v) for k,v in value.items()}
            if isinstance(value, list): return [remap(v) for v in value]
            return "new-"+value if isinstance(value, str) and value in ids else value
        after = remap(before)
        compare_roots(flat(before), flat(after), ["REQ-one"])
        next(o for o in objects(after) if o["id"] == "new-r")["data"]["related"] = "new-pkg"
        with self.assertRaisesRegex(ValueError, "semantic round trip"):
            compare_roots(flat(before), flat(after), ["REQ-one"])

    def test_duplicate_identity_is_rejected(self):
        tree = fixture()
        tree["data"]["ownedRelationship"].append(obj("new-member", "OwningMembership",
            ownedRelatedElement=[requirement("REQ-one", "2")]))
        with self.assertRaisesRegex(ValueError, "Duplicate stable identity"):
            Graph(flat(tree))


class SourceChangeBoundary(unittest.TestCase):
    def test_tooling_snapshot_includes_kerml_library_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'java').write_text('java')
            (root/'kernel.jar').write_text('kernel')
            (root/'library').mkdir()
            library = root/'library/ScalarValues.kerml'
            library.write_text('original')
            args = Namespace(java=str(root/'java'),kernel=str(root/'kernel.jar'),library=str(root/'library'))
            before = runtime_inputs(args)
            library.write_text('changed')
            self.assertNotEqual(before, runtime_inputs(args))

    def test_three_way_conflict_and_unrelated_text_preservation(self):
        source = "prefix\nrequirement <'REQ-one'> old;\nsuffix\n"
        statement = "requirement <'REQ-one'> old;"
        row = {"file":"requirements.sysml", "start":7, "end":7+len(statement), "text":statement,
               "package":"Requirements"}
        baseline = {"keys":{"REQ-one":row}, "packages":{}}
        current = copy.deepcopy(baseline)
        tool = "requirement <'REQ-one'> updated;"
        index = {"elements":[{"key":"REQ-one", "start":0, "end":len(tool)}], "errors":[]}
        edits = propose(baseline, current, tool, index, Graph(flat(fixture())), ["REQ-one"], [])
        self.assertEqual(edited_sources({"requirements.sysml":source}, edits)["requirements.sysml"],
                         "prefix\n"+tool+"\nsuffix\n")
        current["keys"]["REQ-one"]["text"] = "requirement <'REQ-one'> concurrent;"
        with self.assertRaisesRegex(ValueError, "Git and SysON both changed"):
            propose(baseline, current, tool, index, Graph(flat(fixture())), ["REQ-one"], [])
        current["keys"]["REQ-one"]["text"] = tool
        self.assertEqual(propose(baseline, current, tool, index, Graph(flat(fixture())), ["REQ-one"], []), {})

    def test_source_replacement_refuses_concurrent_edit_without_writing_any_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'a.sysml').write_text('original')
            (root/'b.sysml').write_text('original')
            before={n:sha(root/n) for n in ('a.sysml','b.sysml')}
            (root/'b.sysml').write_text('concurrent')
            with self.assertRaisesRegex(ValueError, "changed before application"):
                replace_sources(root, {'a.sysml':'proposed','b.sysml':'proposed'}, before)
            self.assertEqual((root/'a.sysml').read_text(), 'original')
            self.assertEqual((root/'b.sysml').read_text(), 'concurrent')
            self.assertFalse(list(root.glob('*.tmp')))

    def test_paths_cannot_escape_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'Escaping'):
                checked_path(Path(directory), '../outside.sysml')

    @unittest.skipUnless(os.environ.get('SYSML_JAVA') and os.environ.get('SYSML_KERNEL'), 'Pinned native parser required')
    def test_native_spans_handle_unicode_crlf_and_braces_in_documentation(self):
        source="package P {\r\n requirement <'REQ-one'> r { doc /* \U0001f9ea { not syntax } */ }\r\n}\r\n"
        normalized=source.replace('\r\n','\n')
        with tempfile.TemporaryDirectory() as directory:
            index=index_source(ROOT,source,Path(directory)/'index.json',Namespace(
                java=os.environ['SYSML_JAVA'],kernel=os.environ['SYSML_KERNEL']))
        self.assertFalse(index['errors'])
        row=next(r for r in index['elements'] if r.get('key')=='REQ-one')
        self.assertEqual(normalized[row['start']:row['end']], "requirement <'REQ-one'> r { doc /* \U0001f9ea { not syntax } */ }")


class ImportedIntentCoverage(unittest.TestCase):
    def test_unverified_requirement_and_new_use_case_remain_discoverable(self):
        model={'requirements':{'REQ-new':{'constraints':['Deny before fetching.']}},
               'use_cases':{'UC-new':{'subject':'subject','actors':['actor'],'bindings':{'subject':'L-proxy'}}},
               'elements':{'REQ-new':{'name':'Admission'},'UC-new':{'name':'Denied retrieval'}},
               'verification':{},'scenarios':{},'edges':[{'from':'UC-new','to':'REQ-new','kind':'requires'}]}
        report=intent_report(model)
        self.assertIn('verification is uncovered',report)
        self.assertIn('REQ-new',report)
        self.assertIn('scenario detail is pending',report)
        self.assertEqual(case_target('UC-new',{}), 'artifacts/architecture/generated/software-intake/intent.md#uc-new')


if __name__ == '__main__':
    unittest.main()
