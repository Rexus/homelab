"""A shared view must not silently drop, invent or reverse engineering content."""

import copy
import json
from pathlib import Path
import sys
import unittest
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/architecture'))
from view_catalog import compile_views, CATALOG
from syson_catalog import coverage, select_catalog


class SharedViewContracts(unittest.TestCase):
    def test_pages_have_distinct_stable_identities_and_selections(self):
        model={'elements':{'A':{},'B':{}},'edges':[{'from':'A','to':'B','kind':'depends-on','id':'E'}]}
        svg='<svg xmlns="http://www.w3.org/2000/svg"><svg data-view="one"><title>First</title><g data-model="A"/></svg><svg data-view="two"><title>Second</title><g data-model="B"/></svg></svg>'
        outputs={Path('architecture/generated/subsystem/concerns.svg'):svg}
        views=compile_views(outputs,model)
        self.assertEqual([v['elements'] for v in views],[['A'],['B']])
        self.assertEqual(len({v['key'] for v in views}),2)
        self.assertTrue(all(v['owner']=='subsystem' for v in views))
        self.assertEqual(json.loads(outputs[CATALOG])['views'],views)
        with self.assertRaisesRegex(ValueError,'unknown model'):
            compile_views({Path('architecture/generated/a.svg'):svg.replace('data-model="A"','data-model="missing"')},model)

    def test_page_order_does_not_change_catalogue_or_native_snapshot(self):
        model={'elements':{'A':{},'B':{}},'edges':[]}
        pages=['<svg data-view="one"><title>First</title><g data-model="A"/></svg>',
               '<svg data-view="two"><title>Second</title><g data-model="B"/></svg>']
        def compile_pages(selected):
            outputs={Path('architecture/generated/subsystem/concerns.svg'):
                     '<svg xmlns="http://www.w3.org/2000/svg">'+''.join(selected)+'</svg>'}
            return compile_views(outputs,model)
        views=compile_pages(pages)
        self.assertEqual(views,compile_pages(list(reversed(pages))))
        raw=[{'declaredShortName':key,'qualifiedName':'System::'+key} for key in ('A','B')]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            path=root/CATALOG
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'views':views}),encoding='utf-8')
            config=root/'scripts/architecture/config/views/syson.json'
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({
                'publication_views':[v['key'] for v in views]}),encoding='utf-8')
            expected=select_catalog(root,raw,model,[])
            path.write_text(json.dumps({'views':list(reversed(views))}),encoding='utf-8')
            self.assertEqual(expected,select_catalog(root,raw,model,[]))

    def test_relabeling_and_moving_a_view_preserves_its_semantic_identity(self):
        model={'elements':{'A':{},'B':{}},'edges':[{'from':'A','to':'B','kind':'depends-on','id':'E'}]}
        source='<svg xmlns="http://www.w3.org/2000/svg" data-view-id="stable-view"><title>Old label</title><g data-model="A"/><g data-model="B"/><path data-relation="E"/></svg>'
        old=compile_views({Path('architecture/generated/subsystem/old.svg'):source},model)[0]
        new=compile_views({Path('architecture/generated/subsystem/solution.svg'):
                           source.replace('Old label','Subsystem | Solution design')},model)[0]
        for field in ('key','owner','subject','elements','relationships','content_sha256'):
            self.assertEqual(old[field],new[field],field)
        self.assertNotEqual(old['name'],new['name'])
        self.assertNotEqual(old['svg'],new['svg'])

    def test_unsupported_nodes_and_navigation_are_gaps(self):
        view={'key':'v','svg':'architecture/generated/v.svg','elements':['V'],'relationships':[]}
        model={'elements':{'V':{'kind':'VerificationCaseDefinition'}}}
        report=coverage([view],[],{'d':{'nodes':[],'edges':[]}},{'v':{'id':'d'}},model)
        self.assertEqual(report['gaps'],1)
        self.assertEqual(report['views'][0]['missing_elements'],['V'])
        view['elements']=[]
        report=coverage([view],[],{'d':{'nodes':[],'edges':[]}},{'v':{'id':'d'}},model)
        self.assertEqual(report['matched'],0)
        self.assertIn('navigation',report['views'][0]['issues'][0])

    def test_visible_relationship_direction_and_visibility_are_checked(self):
        stored=[{'id':k,'data':{'declaredShortName':k}} for k in ('A','B','E')]
        model={'elements':{'A':{},'B':{}}}
        view={'key':'v','svg':'architecture/generated/v.svg','elements':['A','B'],
              'relationships':[{'from':'A','to':'B','kind':'depends-on','id':'E'}]}
        diagram={'nodes':[{'id':k,'targetObjectId':k} for k in ('A','B')],
                 'edges':[{'targetObjectId':'E','sourceId':'A','targetId':'B',
                           'targetObjectKind':'semantic?entity=Dependency','state':'Normal'}]}
        def check(d):return coverage([view],stored,{'d':d},{'v':{'id':'d'}},model)
        self.assertEqual(check(diagram)['matched'],1)
        for change in ({'sourceId':'B','targetId':'A'},{'state':'Hidden'}):
            altered=copy.deepcopy(diagram);altered['edges'][0].update(change)
            self.assertEqual(check(altered)['gaps'],1)


class RelocatedViewIdentity(unittest.TestCase):
    def test_explicit_view_identity_survives_owner_folder_move(self):
        from pathlib import Path
        from view_catalog import compile_views
        svg = '<svg xmlns="http://www.w3.org/2000/svg" data-view-id="VIEW-kept"><title>Logical design</title></svg>'
        model = {'elements': {}, 'edges': []}
        old = compile_views({Path('architecture/generated/subsystem/logical.svg'): svg}, model)[0]
        new = compile_views({Path('architecture/models/subsystem/logical.svg'): svg}, model)[0]
        self.assertEqual(old['key'], new['key'])
        self.assertEqual(old['content_sha256'], new['content_sha256'])


if __name__=='__main__':unittest.main()
