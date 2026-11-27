"""Focused views must preserve native subjects, obligations, allocations and element identity."""

import copy
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET
from intake_model_fixture import IntakeModelFixture
from focused_views import outputs, functions
from intake_matrices import outputs as matrices, REQUIREMENTS, SYSTEM, VERIFICATION
from model_style import decorate, category
from view_catalog import compile_views
from diagram_notation import tag


class FocusedViewContracts(IntakeModelFixture):
    def test_requirement_matrices_follow_native_constraints_and_keep_navigation(self):
        changed=copy.deepcopy(self.model)
        changed['requirements']['REQ-policy']['constraints']=['Only explicitly admitted requests may proceed.']
        rendered=matrices(self.root,changed)
        for path in (SYSTEM,REQUIREMENTS):
            table=rendered[path]
            self.assertIn('Only explicitly admitted requests may proceed.',table)
            self.assertNotIn(self.model['requirements']['REQ-policy']['constraints'][0],table)
            for key in changed['requirements']:self.assertIn('id="'+key+'"',table)
            self.assertIn('SoftwareIntakeVerification.md#VC-http-denied',table)
            self.assertIn('Design satisfaction assertion',table)
            self.assertIn('None recorded',table)

    def test_matrices_distinguish_scoped_passes_from_unverified_site_obligations(self):
        from intake_matrices import status_summary
        self.assertEqual(status_summary([
            {'scope':'isolated','status':'passed'}, {'scope':'site','status':'missing'}]),
            'Overall: missing; isolated: passed; site: missing')
        table=matrices(self.root,self.model)[REQUIREMENTS]
        for key in ('REQ-integrity','REQ-custody','REQ-egress'):
            self.assertIn(self.model['requirements'][key]['satisfaction_review'].replace('\n',' '),table)
        self.assertTrue(any(e['from']=='L-Consumers' and e['to']=='REQ-integrity'
                            and e['kind']=='satisfies' for e in self.model['edges']))
        self.assertFalse(any(e['kind']=='satisfies' and e['to'] in ('REQ-custody','REQ-egress')
                             for e in self.model['edges']))

    def test_system_goals_keep_their_own_subjects_and_participation(self):
        rendered=outputs(self.root,self.model)
        svg=ET.fromstring(rendered[Path('architecture/generated/HomelabUseCases.svg')])
        subjects={e.get('data-subject') for e in svg.iter(tag('svg'))}
        self.assertTrue({'UC-supply','UC-clone-host'}<=subjects)
        relations=[r for e in svg.iter() for r in json.loads(e.get('data-relationships','[]'))]
        for key in ('UC-update','UC-clone'):
            expected=[e for e in self.model['edges'] if e['from']==key and e['kind'] in ('has-actor','has-subject')]
            self.assertTrue(all(e in relations for e in expected))

    def test_verification_matrix_exposes_native_procedures_and_traces(self):
        table=matrices(self.root,self.model)[VERIFICATION]
        for key,case in self.model['verification'].items():
            row=next(line for line in table.splitlines() if line.startswith('| <a id="'+key+'"'))
            for field in ('method','setup','action','acceptance'):self.assertIn(case[field],row)
            for req in case['requirements']:self.assertIn('Requirements.md#'+req,row)
            for scenario in case['scenarios']:self.assertIn('UseCases.svg#'+scenario,row)
        self.assertNotIn('| passed |',table)

    def test_native_allocation_changes_the_function_view(self):
        changed=copy.deepcopy(self.model)
        changed['edges']=[e for e in changed['edges'] if e.get('id')!='ALLOC-F-cache-1']
        svg=ET.fromstring(functions(changed,'intake'))
        relations=[r for e in svg.iter() for r in json.loads(e.get('data-relationships','[]'))]
        self.assertNotIn('ALLOC-F-cache-1',{r.get('id') for r in relations})
        self.assertIn('ALLOC-F-cache-0',{r.get('id') for r in relations})

    def test_colour_follows_kind_across_views_not_subsystem_name(self):
        svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 600" data-engineering-view="true"><g data-model="SYS-trust"><rect/></g><g data-model="SYS-intake"><rect/></g><g data-model="P-servers"><rect/></g></svg>'
        rendered={Path('architecture/generated/example.svg'):svg}
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
        selected='architecture/generated/selected.svg'
        rendered={Path(selected):svg,Path('architecture/generated/report.svg'):svg}
        views=compile_views(rendered,self.model,[selected])
        self.assertEqual([v['svg'] for v in views],[selected])
        with self.assertRaisesRegex(ValueError,'Selected engineering view is missing'):
            compile_views({Path(selected):svg},self.model,['architecture/generated/missing.svg'])

    def test_classification_frames_are_not_model_parts_or_external_implementations(self):
        self.assertFalse({'L-T2','L-DMZ','R-T2','R-Edge'} & set(self.model['elements']))
        self.assertFalse(self.model['elements']['L-Sources']['composite'])
        svg=ET.parse(self.root/'architecture/generated/software-intake/SoftwareIntakeLogicalDesign.svg')
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
        notation=json.loads((self.root/'scripts/architecture/config/views/notation.json').read_text())
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
        rendered={Path(f'architecture/generated/software-intake/{kind}.svg'):
                  render(self.root,self.model,selected_inputs(self.root),kind)
                  for kind in ('logical','solution')}
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
        notation=json.loads((self.root/'scripts/architecture/config/views/notation.json').read_text())
        changed=copy.deepcopy(self.model)
        changed['elements']['MATERIAL']={'kind':'ItemDefinition','name':'Raw material'}
        self.assertNotEqual(category(changed,'MATERIAL',notation),'information')
        self.assertEqual(category(changed,'DEF-cached-content',notation),'information')

    def test_software_role_follows_native_ownership_without_recolouring_the_contract(self):
        notation=json.loads((self.root/'scripts/architecture/config/views/notation.json').read_text())
        self.assertEqual(category(self.model,'L-Proxy',notation),'logical')
        self.assertEqual(category(self.model,'DEF-proxy',notation),'logical')
        self.assertEqual(category(self.model,'RUN-cache-1',notation),'software')
        self.assertEqual(category(self.model,'DISK-cache-1',notation),'logical')
        changed=copy.deepcopy(self.model)
        # A differently named future realization gets the same role through native relationships.
        changed['elements']['arbitrary-host']={'name':'Any guest','kind':'PartUsage'}
        changed['elements']['arbitrary-app']={'name':'Any implementation','kind':'PartUsage'}
        changed['edges'] += [
            {'from':'arbitrary-host','to':'DEF-member','kind':'typed-by'},
            {'from':'arbitrary-app','to':'DEF-proxy','kind':'typed-by'},
            {'from':'arbitrary-host','to':'arbitrary-app','kind':'contains'}]
        self.assertEqual(category(changed,'arbitrary-app',notation),'software')
        changed['edges']=[e for e in changed['edges'] if
                          (e['from'],e['to'],e['kind'])!=('arbitrary-host','arbitrary-app','contains')]
        self.assertEqual(category(changed,'arbitrary-app',notation),'logical')
