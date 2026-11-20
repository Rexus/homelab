"""Boundary annotations must retain SVG membership without adding model composition."""

import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/architecture'))
from syson_annotations import read_annotations, annotation_text, annotation_gaps


class AnnotationFrames(unittest.TestCase):
    def setUp(self):
        self.item = {'id': 'zone', 'label': 'Zone grouping', 'members': ['A'], 'parent': None,
                     'frame_key': 'v-annotation-zone', 'caption_key': 'v-caption-zone',
                     'frame': [0, 0, 400, 300], 'caption': [20, 2, 360, 70], 'border_color': '#999999'}
        self.view = {'key': 'v', 'elements': ['A', 'B'], 'annotations': [self.item]}
        self.indexed = {key: {'id': key, 'eClass': 'sysml:PartUsage'} for key in ('A', 'B')}
        self.diagram = {'nodes': [], 'layoutData': {'nodeLayoutData': {}}}
        cells = [('A', [50, 100, 200, 100]), ('B', [500, 100, 200, 100])]
        for role in ('frame', 'caption'):
            key = self.item[role + '_key']
            self.indexed[key] = {'id': key, 'eClass': 'sysml:Comment', 'data': {'body': self.item['label']}}
            cells.append((key, self.item[role]))
        for key, (x, y, w, h) in cells:
            frame = key == self.item['frame_key']
            self.diagram['nodes'].append({'id': key, 'targetObjectId': key, 'type': 'customnode:sysmlnote',
                'style': {'background': 'transparent', 'borderColor': '#999999', 'borderSize': 2 if frame else 0},
                'insideLabel': {'text': self.item['label'], 'style': {'visibility': 'hidden' if frame else 'visible'}}})
            self.diagram['layoutData']['nodeLayoutData'][key] = {
                'position': {'x': x, 'y': y}, 'size': {'width': w, 'height': h}}

    def gaps(self):
        return annotation_gaps(self.view, self.diagram, self.indexed)

    def test_comments_and_visual_membership_match(self):
        self.assertEqual(self.gaps(), [])

    def test_declared_item_omission_preserves_checks_on_visible_frame_members(self):
        self.view['elements'].append('content')
        self.item['members'].append('content')
        self.view['rendering_gaps'] = {'content': {'kind': 'ItemUsage', 'reason': 'Release limitation'}}
        self.assertEqual(self.gaps(), [])
        self.diagram['nodes'][0]['state'] = 'Hidden'
        self.assertEqual(self.gaps(), [self.item])

    def test_frame_cannot_be_a_part(self):
        self.indexed[self.item['frame_key']]['eClass'] = 'sysml:PartUsage'
        self.assertEqual(self.gaps(), [self.item])

    def test_missing_caption_or_opaque_frame_is_not_parity(self):
        original = copy.deepcopy(self.diagram)
        self.diagram['nodes'] = self.diagram['nodes'][:-1]
        self.assertTrue(self.gaps())
        self.diagram = original
        self.diagram['nodes'][2]['style']['background'] = '#ffffff'
        self.assertTrue(self.gaps())

    def test_moving_an_unselected_part_into_frame_is_detected(self):
        self.diagram['layoutData']['nodeLayoutData']['B']['position']['x'] = 80
        self.assertTrue(self.gaps())

    def test_svg_owns_members_labels_and_nested_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'view.svg'
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><g id="tier" data-explanatory="true">'
                            '<text>Tier</text><g id="zone" data-explanatory="true"><text>Zone</text>'
                            '<g data-model="A"/></g></g><g data-model="B"/></svg>')
            layout = {key: {'frame': [0,0,400,300], 'caption': [20,2,360,70], 'border_color': '#999999'}
                      for key in ('tier', 'zone')}
            annotations = read_annotations(path, self.view, layout)
            self.assertEqual(annotations[1]['parent'], 'tier')
            self.assertEqual([a['members'] for a in annotations], [['A'], ['A']])
            self.assertEqual([a['label'] for a in annotations], ['Tier', 'Zone'])
            text = '\n'.join(annotation_text({**self.view, 'annotations': annotations}))
            self.assertEqual(text.count('comment '), 4)
            self.assertNotIn('part ', text)
            self.assertNotIn('about ', text)
            with self.assertRaisesRegex(ValueError, 'differs from SVG'):
                read_annotations(path, self.view, {'invented': layout['tier']})
            layout['tier']['caption'][3] = 65
            with self.assertRaisesRegex(ValueError, 'minimum height of 70'):
                read_annotations(path, self.view, layout)


if __name__ == '__main__':
    unittest.main()
