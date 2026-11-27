"""Native use-case membership edges must remain visible, directed and kind-correct."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/architecture'))
from syson_catalog import CASE_EDGE_KINDS, coverage, unwanted_details


class CaseViews(unittest.TestCase):
    def test_case_membership_kinds_and_direction_are_not_inferred_from_endpoints(self):
        objects = [{'id': k, 'data': {'declaredShortName': k}} for k in ('UC', 'ACT', 'SUB', 'SC')]
        nodes = [{'id': k, 'targetObjectId': k} for k in ('UC', 'ACT', 'SUB', 'SC')]
        targets = {'has-actor': 'ACT', 'has-subject': 'SUB', 'contains': 'SC'}
        edges = [{'id': kind, 'targetObjectId': 'UC', 'sourceId': 'UC', 'targetId': targets[kind],
                  'targetObjectKind': 'semantic?entity=UseCaseDefinition', 'state': 'Normal',
                  'descriptionId': 'native?sourceElementId=' + identity}
                 for identity, kind in CASE_EDGE_KINDS.items()]
        view = {'key': 'v', 'svg': 'v.svg', 'elements': list(targets.values()) + ['UC'],
                'relationships': [{'from': 'UC', 'to': target, 'kind': kind} for kind, target in targets.items()]}
        diagram = {'nodes': nodes, 'edges': edges}
        model = {'elements': {k: {} for k in ('UC', 'ACT', 'SUB', 'SC')}}
        def report(value): return coverage([view], objects, {'d': value}, {'v': {'id': 'd'}}, model)
        self.assertEqual(unwanted_details(view, diagram, objects), [])
        self.assertEqual(report(diagram)['matched'], 1)
        for alteration in ({'state': 'Hidden'}, {'sourceId': 'SC', 'targetId': 'UC'},
                           {'descriptionId': 'unknown-renderer-version'}):
            broken = copy.deepcopy(diagram)
            broken['edges'][0].update(alteration)
            self.assertEqual(report(broken)['gaps'], 1)
        selected = copy.deepcopy(view)
        selected['relationships'] = [r for r in view['relationships'] if r['kind'] != 'has-actor']
        self.assertIn('has-actor', unwanted_details(selected, diagram, objects))



class GeneralLayout(unittest.TestCase):
    def test_actor_seed_and_browser_resizing_are_both_checked(self):
        from syson_general import verify_general_geometry
        view = {'key': 'v', 'boxes': {'ACT': [10,20,41,92]}}
        node = {'id': 'actor', 'targetObjectId': 'a', 'type': 'node:image',
                'style': {'imageURL': 'images/actor.svg'}}
        cell = {'position': {'x':10,'y':20}, 'size': {'width':41,'height':92}}
        diagram = {'nodes': [node], 'layoutData': {'nodeLayoutData': {'actor':cell}}}
        verify_general_geometry(view, diagram, {'a':'ACT'})
        bad = copy.deepcopy(view); bad['boxes']['ACT'][2:] = [300,100]
        headless = copy.deepcopy(diagram)
        headless['layoutData']['nodeLayoutData']['actor']['size'] = {'width':300,'height':100}
        with self.assertRaisesRegex(ValueError, 'Actor aspect ratio'):
            verify_general_geometry(bad, headless, {'a':'ACT'})
        cell['size']['height'] = 673
        with self.assertRaisesRegex(ValueError, 'saved layout mismatch'):
            verify_general_geometry(view, diagram, {'a':'ACT'})

    def test_body_overlap_and_lost_outside_label_positions_fail(self):
        from syson_general import verify_general_geometry, actor_labels
        view = {'key':'v', 'boxes':{'A':[0,0,100,100], 'B':[50,50,100,100]}}
        nodes = [{'id':k,'targetObjectId':k} for k in ('A','B')]
        diagram = {'nodes':nodes,'layoutData':{'nodeLayoutData':{k:{
            'position':{'x':x,'y':y},'size':{'width':w,'height':h}}
            for k,(x,y,w,h) in view['boxes'].items()}}}
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            verify_general_geometry(view, diagram, {'A':'A','B':'B'})
        view = {'key':'v','boxes':{'A':[0,0,41,92]},'actor_label_offsets':{'A':[300,-92]}}
        nodes[0].update(type='node:image',style={'imageURL':'images/actor.svg'},outsideLabels=[{'id':'label'}])
        diagram = {'nodes':nodes[:1], 'layoutData':{'nodeLayoutData':{
            'A':{'position':{'x':0,'y':0},'size':{'width':41,'height':92}}}}}
        with self.assertRaisesRegex(ValueError, 'Actor label position'):
            verify_general_geometry(view, diagram, {'A':'A'})
        diagram['layoutData']['labelLayoutData']={'label':actor_labels(view,diagram,{'A':'A'})[0]}
        verify_general_geometry(view, diagram, {'A':'A'})

    def test_ownership_uses_native_ancestry_for_every_view_concern(self):
        from syson_general import verify_view_owners
        def member(identity, child):
            return {'id':identity,'eClass':'sysml:OwningMembership','data':{'ownedRelatedElement':[child]}}
        def package(identity, name, children):
            return {'id':identity,'eClass':'sysml:Package','data':{'declaredName':name,'ownedRelationship':children}}
        overall={'id':'o','eClass':'sysml:ViewUsage','data':{'declaredShortName':'OVERALL'}}
        case={'id':'c','eClass':'sysml:ViewUsage','data':{'declaredShortName':'CASE'}}
        function={'id':'f','eClass':'sysml:ViewUsage','data':{'declaredShortName':'FUNCTION'}}
        subsystem=package('s','subsystem',[member('mc',case),member('mf',function)])
        tree=package('root','Views',[member('mo',overall),member('ms',subsystem)])
        from syson_api import objects
        views=[{'key':'OVERALL','owner':'.'},{'key':'CASE','owner':'subsystem'},
               {'key':'FUNCTION','owner':'subsystem'}]
        verify_view_owners(views,list(objects(tree)))
        views[1]['owner']='.'
        with self.assertRaisesRegex(ValueError,'ownership mismatch'):
            verify_view_owners(views,list(objects(tree)))
        tree['data']['declaredName']='Unrelated'
        with self.assertRaisesRegex(ValueError,'no Views package'):
            verify_view_owners(views,list(objects(tree)))

    def test_actor_and_subject_connectors_face_their_neighbours(self):
        from syson_general import facing_handles
        view={'boxes':{'ACT':[0,0,41,92],'UC':[200,0,200,100],'SUB':[600,0,200,100]}}
        indexed={k:{'id':k} for k in view['boxes']}
        diagram={'nodes':[{'id':k,'targetObjectId':k} for k in view['boxes']], 'edges':[
            {'id':'actor','sourceId':'UC','targetId':'ACT'},
            {'id':'subject','sourceId':'UC','targetId':'SUB'}]}
        handles=facing_handles(view,diagram,indexed)
        self.assertEqual({h['edgeId']:h['handlePosition'] for h in handles['UC']},
                         {'actor':'left','subject':'right'})
        self.assertEqual(handles['ACT'][0]['handlePosition'],'right')
        self.assertEqual(handles['SUB'][0]['handlePosition'],'left')
        self.assertEqual(handles['ACT'][0]['position']['x'],41)
        self.assertTrue(all(h['type']=='source' for h in handles['UC']))


if __name__ == '__main__': unittest.main()
