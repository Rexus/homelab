"""Prevent mass publication and loss of nested parts, flow direction or saved placement."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/architecture'))
from syson_catalog import select_catalog, coverage, verify_representation_set
from syson_nested import verify_nested


class CompactPublication(unittest.TestCase):
    def test_publication_is_explicit_and_not_expanded_by_catalogue_growth(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'architecture/views'
            folder.mkdir(parents=True)
            entries = [{'key': k, 'name': k, 'owner': '.', 'svg': k+'.svg',
                        'elements': ['A'], 'relationships': [], 'content_sha256': 'selection'}
                       for k in ('chosen', 'report')]
            (folder/'catalog.json').write_text(json.dumps({'views': entries}))
            config = {'publication_views': ['chosen']}
            (folder/'syson.json').write_text(json.dumps(config))
            raw = [{'declaredShortName': 'A', 'qualifiedName': 'System::A'}]
            views, text = select_catalog(root, raw, {}, [])
            self.assertEqual([v['key'] for v in views], ['chosen'])
            self.assertNotIn("view <'report'>", text)
            config['interconnection_views'] = {'chosen': {'boxes': {'A': [0,0,300,200]}, 'ports': {}}}
            (folder/'syson.json').write_text(json.dumps(config))
            views, text = select_catalog(root, raw, {}, [])
            self.assertIn('StandardViewDefinitions::InterconnectionView', text)
            self.assertEqual(views[0]['representation_description'], 'Interconnection View')
            for selected in ([], ['unknown'], ['chosen', 'chosen']):
                config['publication_views'] = selected
                (folder/'syson.json').write_text(json.dumps(config))
                with self.assertRaisesRegex(ValueError, 'explicit, unique selection'):
                    select_catalog(root, raw, {}, [])

    def test_known_item_gap_keeps_selection_without_exposing_unsupported_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'architecture/views'; folder.mkdir(parents=True)
            entry = {'key': 'chosen', 'name': 'chosen', 'owner': '.', 'svg': 'chosen.svg',
                     'elements': ['A', 'D'], 'relationships': [], 'content_sha256': 'selection'}
            (folder/'catalog.json').write_text(json.dumps({'views': [entry]}))
            config = {'publication_views': ['chosen'], 'interconnection_views': {'chosen': {
                'boxes': {'A': [0,0,300,200], 'D': [20,42,100,80]}, 'ports': {},
                'rendering_gaps': {'D': {'kind': 'ItemUsage', 'reason': 'Release limitation'}}}}}
            (folder/'syson.json').write_text(json.dumps(config))
            raw = [{'declaredShortName': key, 'qualifiedName': 'System::'+key} for key in ('A','D')]
            model = {'elements': {'A': {'kind': 'PartUsage'}, 'D': {'kind': 'ItemUsage'}}}
            views, text = select_catalog(root, raw, model, [])
            self.assertEqual(views[0]['elements'], ['A', 'D'])
            self.assertIn('expose System::A;', text)
            self.assertNotIn('expose System::D;', text)
            model['elements']['D']['kind'] = 'PartUsage'
            with self.assertRaisesRegex(ValueError, 'Invalid scoped native item gap'):
                select_catalog(root, raw, model, [])

    def setUp(self):
        self.stored = [{'id': k, 'data': {'declaredShortName': k}} for k in ('A','B','C','F')]
        self.model = {'elements': {k: {} for k in ('A','B','C')}}
        self.view = {'key': 'v', 'name': 'Compact', 'svg': 'compact.svg', 'elements': ['A','B','C'],
                     'relationships': [{'from':'A','to':'B','kind':'contains'},
                                       {'from':'C','to':'B','kind':'flow','id':'F'}],
                     'nested_boxes': {'A':[0,0,300,300], 'B':[20,42,100,80], 'C':[400,0,100,80]},
                     'ports': {'B':{'access':[-5,35,10,10]}, 'C':{'access':[-5,35,10,10]}},
                     'edges':['F']}
        def node(identity, label=''):
            return {'id':identity,'targetObjectId':identity,'state':'Normal',
                    'insideLabel':{'text':label},'childNodes':[],'borderNodes':[]}
        a,b,c = [node(k) for k in ('A','B','C')]
        compartment = node('compartment', 'interconnection')
        compartment['targetObjectId'] = 'A'
        a['childNodes'] = [compartment]
        compartment['childNodes'] = [b]
        for part in (b,c):
            port=node(part['id']+'-port')
            port.update(insideLabel=None, borderNode=True, targetObjectLabel='access')
            part['borderNodes']=[port]
        positions={'A':[0,0,300,300], 'compartment':[1,60,298,239], 'B':[20,42,100,80],
                   'C':[400,0,100,80], 'B-port':[-5,35,10,10], 'C-port':[-5,35,10,10]}
        self.diagram={'id':'d','nodes':[a,c], 'edges':[{'id':'edge','targetObjectId':'F',
                      'sourceId':'C-port','targetId':'B-port','targetObjectKind':'semantic?entity=FlowUsage'}],
                      'layoutData':{'nodeLayoutData':{k:{'position':{'x':x,'y':y},
                       'size':{'width':w,'height':h}} for k,(x,y,w,h) in positions.items()}}}

    def check(self, diagram):
        verify_nested([self.view],self.stored,{'d':diagram},{'v':{'id':'d'}},self.model)

    def test_nested_compartment_and_owned_ports_match_the_shared_selection(self):
        self.check(self.diagram)

    def test_explanatory_frames_are_reported_without_inventing_composition(self):
        self.view['annotations']=[{'id':'zone','label':'Example zone'}]
        self.check(self.diagram)
        report=coverage([self.view],self.stored,{'d':self.diagram},{'v':{'id':'d'}},self.model)
        self.assertEqual(report['views'][0]['model_content_status'],'matched')
        self.assertEqual(report['views'][0]['unrendered_annotations'],self.view['annotations'])
        self.assertEqual(report['gaps'],1)

    def test_additional_native_representations_cannot_pass_reuse(self):
        verify_representation_set([self.view],{'d':self.diagram},{'v':{'id':'d'}})
        with self.assertRaisesRegex(ValueError,'explicit publication selection'):
            verify_representation_set([self.view],{'d':self.diagram,'extra':{}},{'v':{'id':'d'}})

    def test_flattening_nested_parts_is_not_equivalent(self):
        altered=copy.deepcopy(self.diagram)
        children=altered['nodes'][0]['childNodes'][0]['childNodes']
        altered['nodes'].append(children.pop())
        with self.assertRaisesRegex(ValueError, 'Nested content mismatch'):
            self.check(altered)

    def test_declared_item_gap_stays_visible_and_cannot_excuse_other_losses(self):
        self.model['elements']['D'] = {'kind': 'ItemUsage'}
        self.view['elements'].append('D')
        self.view['relationships'].append({'from': 'A', 'to': 'D', 'kind': 'contains'})
        self.view['rendering_gaps'] = {'D': {'kind': 'ItemUsage', 'reason': 'Release limitation'}}
        self.check(self.diagram)
        report = coverage([self.view], self.stored, {'d': self.diagram}, {'v': {'id': 'd'}}, self.model)
        self.assertEqual(report['views'][0]['status'], 'gap')
        self.assertEqual(report['views'][0]['missing_elements'], ['D'])
        altered = copy.deepcopy(self.diagram)
        altered['edges'][0]['state'] = 'Hidden'
        with self.assertRaisesRegex(ValueError, 'Nested content mismatch'):
            self.check(altered)
        altered = copy.deepcopy(self.diagram)
        altered['nodes'][0]['childNodes'][0]['childNodes'][0]['state'] = 'Hidden'
        with self.assertRaisesRegex(ValueError, 'Nested content mismatch'):
            self.check(altered)

    def test_hidden_or_reversed_flows_are_rejected(self):
        for change in ({'state':'Hidden'}, {'sourceId':'B-port','targetId':'C-port'}):
            altered=copy.deepcopy(self.diagram)
            altered['edges'][0].update(change)
            with self.assertRaisesRegex(ValueError, 'Nested content mismatch'):
                self.check(altered)

    def test_correct_semantics_do_not_excuse_a_child_outside_its_container(self):
        altered=copy.deepcopy(self.diagram)
        altered['layoutData']['nodeLayoutData']['B']['position']['x']=500
        with self.assertRaisesRegex(ValueError, 'Nested saved layout mismatch'):
            self.check(altered)

    def test_extra_native_flow_is_rejected(self):
        altered=copy.deepcopy(self.diagram)
        extra=copy.deepcopy(altered['edges'][0]);extra['targetObjectId']='unexpected'
        altered['edges'].append(extra)
        with self.assertRaisesRegex(ValueError, 'Nested flow selection mismatch'):
            self.check(altered)


if __name__ == '__main__':
    unittest.main()
