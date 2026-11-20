"""Focused views must preserve native subjects, obligations, allocations and element identity."""

import copy
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET
from intake_model_fixture import IntakeModelFixture
from focused_views import outputs, functions
from model_style import decorate, category
from view_catalog import compile_views
from diagram_notation import tag


class FocusedViewContracts(IntakeModelFixture):
    def test_system_goals_keep_their_own_subjects_and_participation(self):
        rendered=outputs(self.root,self.model)
        svg=ET.fromstring(rendered[Path('architecture/views/use-cases.svg')])
        subjects={e.get('data-subject') for e in svg.iter(tag('svg'))}
        self.assertTrue({'UC-supply','UC-clone-host'}<=subjects)
        relations=[r for e in svg.iter() for r in json.loads(e.get('data-relationships','[]'))]
        for key in ('UC-update','UC-clone'):
            expected=[e for e in self.model['edges'] if e['from']==key and e['kind'] in ('has-actor','has-subject')]
            self.assertTrue(all(e in relations for e in expected))

    def test_tests_show_actual_verify_and_scenario_relations(self):
        svg=ET.fromstring(outputs(self.root,self.model)[Path('architecture/views/software-intake/tests.svg')])
        shown={e.get('data-model') for e in svg.iter()}
        self.assertTrue(set(self.model['verification'])<=shown)
        relations=[r for e in svg.iter() for r in json.loads(e.get('data-relationships','[]'))]
        expected=[e for e in self.model['edges'] if e['from'] in self.model['verification']
                  and (e['kind']=='verifies' or e['to'] in self.model['scenarios'])]
        self.assertEqual({json.dumps(e,sort_keys=True) for e in expected},
                         {json.dumps(e,sort_keys=True) for e in relations})

    def test_native_allocation_changes_the_function_view(self):
        changed=copy.deepcopy(self.model)
        changed['edges']=[e for e in changed['edges'] if e.get('id')!='ALLOC-F-cache-1']
        svg=ET.fromstring(functions(changed,'intake'))
        relations=[r for e in svg.iter() for r in json.loads(e.get('data-relationships','[]'))]
        self.assertNotIn('ALLOC-F-cache-1',{r.get('id') for r in relations})
        self.assertIn('ALLOC-F-cache-0',{r.get('id') for r in relations})

    def test_colour_follows_kind_across_views_not_subsystem_name(self):
        svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 600" data-engineering-view="true"><g data-model="SYS-trust"><rect/></g><g data-model="SYS-intake"><rect/></g><g data-model="P-servers"><rect/></g></svg>'
        rendered={Path('architecture/views/example.svg'):svg}
        decorate(self.root,self.model,rendered)
        parsed=ET.fromstring(next(iter(rendered.values())))
        nodes={n.get('data-model'):n for n in parsed.iter(tag('g'))}
        self.assertEqual(nodes['SYS-trust'][0].get('style'),nodes['SYS-intake'][0].get('style'))
        self.assertEqual(nodes['P-servers'].get('data-category'),'physical')
        self.assertNotEqual(nodes['P-servers'][0].get('style'),nodes['SYS-intake'][0].get('style'))
        keys={n.get('data-category-key') for n in parsed.iter() if n.get('data-category-key')}
        self.assertEqual(keys,{'logical','physical'})

    def test_catalogue_does_not_promote_supporting_reports_or_missing_views(self):
        svg='<svg xmlns="http://www.w3.org/2000/svg"><title>View</title><g data-model="SYS-intake"/></svg>'
        selected='architecture/views/selected.svg'
        rendered={Path(selected):svg,Path('architecture/views/report.svg'):svg}
        views=compile_views(rendered,self.model,[selected])
        self.assertEqual([v['svg'] for v in views],[selected])
        with self.assertRaisesRegex(ValueError,'Selected engineering view is missing'):
            compile_views({Path(selected):svg},self.model,['architecture/views/missing.svg'])

    def test_classification_frames_are_not_model_parts_or_external_implementations(self):
        self.assertFalse({'L-T2','L-DMZ','R-T2','R-Edge'} & set(self.model['elements']))
        self.assertFalse(self.model['elements']['L-Sources']['composite'])
        svg=ET.parse(self.root/'architecture/views/software-intake/logical.svg')
        source=svg.find('.//*[@data-model="L-Sources"]')
        proxy=svg.find('.//*[@data-model="L-Proxy"]')
        frame=svg.find('.//*[@id="T2"]')
        self.assertEqual(source.get('data-category'),'external')
        self.assertEqual(proxy.get('data-category'),'logical')
        self.assertEqual(frame.get('data-boundary-kind'),'tier')
        self.assertIsNone(frame.get('data-model'))
        self.assertNotEqual(source.find(tag('rect')).get('style'),proxy.find(tag('rect')).get('style'))
        self.assertNotEqual(frame.find(tag('rect')).get('style'),proxy.find(tag('rect')).get('style'))

    def test_native_part_kind_alone_does_not_mean_software(self):
        notation=json.loads((self.root/'architecture/views/notation.json').read_text())
        self.assertEqual(category(self.model,'L-context',notation),'external')
        self.assertEqual(category(self.model,'PAYLOAD',notation),'information')
        self.assertEqual(category(self.model,'P-IF-physical',notation),'interface')
        self.assertEqual(category(self.model,'P-fabric',notation),'logical')

    def test_allocations_use_unique_components_and_unambiguous_routes(self):
        for scope in ('system','intake'):
            svg=ET.fromstring(functions(self.model,scope))
            boxes={}
            for node in svg.iter(tag('g')):
                shape=node.find(tag('rect'))
                if node.get('data-model') and shape is not None:
                    key=node.get('data-model')
                    self.assertNotIn(key,boxes,'A model element must appear only once in this view')
                    boxes[key]=tuple(float(shape.get(a)) for a in ('x','y','width','height'))
            shown=[]; routes=[]
            for path in svg.iter(tag('path')):
                for relation in json.loads(path.get('data-relationships','[]')):
                    self.assertEqual(relation['kind'],'allocated-to')
                    route=path.get('d')
                    self.assertRegex(route,r'^M[\d.]+ [\d.]+(?: [HV][\d.]+)+$',
                                     'Allocation routes must use horizontal/vertical segments')
                    values=re.findall(r'[MHV]|[\d.]+',route)
                    points=[(float(values[1]),float(values[2]))]
                    for i in range(3,len(values),2):
                        x,y=points[-1];v=float(values[i+1])
                        points.append((v,y) if values[i]=='H' else (x,v))
                    sx,sy=points[0];ex,ey=points[-1]
                    x,y,w,h=boxes[relation['from']]
                    self.assertEqual(sx,x+w);self.assertTrue(y<sy<y+h)
                    x,y,w,h=boxes[relation['to']]
                    self.assertEqual(ex,x);self.assertTrue(y<ey<y+h)
                    routes.append(list(zip(points,points[1:])));shown.append(relation)
            # Axis-aligned segments intersect exactly when both coordinate intervals overlap.
            # Separate arrows may neither cross, touch nor share a routing segment here.
            for i,segments in enumerate(routes):
                for other in routes[i+1:]:
                    for a,b in segments:
                        for c,d in other:
                            intersects=all(max(min(a[k],b[k]),min(c[k],d[k]))
                                           <=min(max(a[k],b[k]),max(c[k],d[k])) for k in (0,1))
                            self.assertFalse(intersects,'Independent allocation routes cross or merge')
            expected=[e for e in self.model['edges'] if e['kind']=='allocated-to'
                      and e['from'] in self.model['functions']]
            self.assertCountEqual(shown,expected)
            self.assertEqual(set(boxes),set(self.model['functions'])|{e['to'] for e in expected})

    def test_storage_and_stored_content_are_distinct_native_elements_in_both_views(self):
        from intake_views import render
        from intake_sources import selected_inputs
        pairs=[('L-Cache','L-cached-content')]+[
            ('DISK-'+name,'CONTENT-'+name) for name in selected_inputs(self.root)['members']]
        edges={(e['from'],e['to'],e['kind']) for e in self.model['edges']}
        for storage,content in pairs:
            self.assertEqual(self.model['elements'][storage]['kind'],'PartUsage')
            self.assertEqual(self.model['elements'][content]['kind'],'ItemUsage')
            self.assertIn((storage,content,'contains'),edges)
            self.assertIn((content,'DEF-cached-content','typed-by'),edges)
            self.assertFalse(any(e['kind']=='allocated-to' and e['to']==content
                                 for e in self.model['edges']))
        rendered={Path(f'architecture/views/software-intake/{kind}.svg'):
                  render(self.root,self.model,selected_inputs(self.root),kind)
                  for kind in ('logical','placement')}
        decorate(self.root,self.model,rendered)
        nodes={node.get('data-model'):node for value in rendered.values()
               for node in ET.fromstring(value).iter() if node.get('data-model')}
        for storage,content in pairs:
            self.assertEqual(nodes[storage].get('data-category'),'logical')
            self.assertEqual(nodes[content].get('data-category'),'information')
            self.assertIn(nodes[content],list(nodes[storage].iter()))

    def test_view_cannot_invent_storage_content_ownership(self):
        from intake_views import render
        from intake_sources import selected_inputs
        changed=copy.deepcopy(self.model)
        changed['edges']=[e for e in changed['edges']
            if (e['from'],e['to'],e['kind'])!=('L-Cache','L-cached-content','contains')]
        with self.assertRaisesRegex(ValueError,'Wrong model containment for L-cached-content'):
            render(self.root,changed,selected_inputs(self.root),'logical')

    def test_native_item_kind_does_not_always_mean_information(self):
        notation=json.loads((self.root/'architecture/views/notation.json').read_text())
        changed=copy.deepcopy(self.model)
        changed['elements']['MATERIAL']={'kind':'ItemDefinition','name':'Raw material'}
        self.assertNotEqual(category(changed,'MATERIAL',notation),'information')
        self.assertEqual(category(changed,'DEF-cached-content',notation),'information')
