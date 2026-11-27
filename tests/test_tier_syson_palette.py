"""Shared palette correspondence and opt-in isolation from accepted native views."""

import copy
import json
import re
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/architecture'))
from syson_style import shared_colours, style_palette, palette_gaps
from syson_annotations import read_annotations
from model_style import geometry


class SharedNativePalette(unittest.TestCase):
    def test_palette_matches_the_generated_svg_shapes(self):
        catalog = json.loads((ROOT / 'artifacts/architecture/catalog.json').read_text(encoding='utf-8'))
        view = copy.deepcopy(next(v for v in catalog['views'] if v['key'] == 'VIEW-software-intake-logical'))
        source = ROOT / view['svg']
        config = json.loads((ROOT / 'scripts/architecture/config/views/syson.json').read_text(encoding='utf-8'))
        view['annotations'] = read_annotations(source, view, config['interconnection_views'][view['key']]['annotations'])
        colours = shared_colours(ROOT, source, view)
        nodes = {n.get('data-model'): n for n in ET.parse(source).getroot().iter() if n.get('data-model')}
        css = '\n'.join(n.text or '' for n in ET.parse(source).getroot().iter() if n.tag.endswith('}style'))
        for key, expected in colours['elements'].items():
            shape = next(e for e in geometry(nodes[key]) if e.get('fill') != 'none')
            actual = dict(item.split(':', 1) for item in shape.get('style', '').split(';') if ':' in item)
            self.assertEqual((actual['fill'], actual['stroke']), (expected['fill'], expected['stroke']), key)
            rule = re.search(r'\.' + re.escape(nodes[key].get('class')) + r'\s*\{([^}]+)\}', css)
            declaration = re.search(r'(?:^|;)\s*color\s*:\s*([^;]+)', rule[1]) if rule else None
            inline = dict(item.split(':', 1) for item in nodes[key].get('style', '').split(';') if ':' in item)
            foreground = inline.get('color', declaration[1].strip() if declaration else nodes[key].get('color'))
            self.assertEqual(expected['color'], foreground, key)
        frames = {n.get('id'): n for n in ET.parse(source).getroot().iter() if n.get('data-explanatory') == 'true'}
        for annotation in view['annotations']:
            shape = next(e for e in frames[annotation['id']] if e.tag.endswith('}rect'))
            actual = dict(item.split(':', 1) for item in shape.get('style', '').split(';') if ':' in item)
            self.assertEqual((actual['fill'], actual['stroke']),
                             (annotation['colours']['fill'], annotation['colours']['stroke']))

    def test_realized_software_palette_is_reusable_by_the_native_adapter(self):
        catalog = json.loads((ROOT / 'artifacts/architecture/catalog.json').read_text())
        view = next(v for v in catalog['views'] if v['svg']=='architecture/generated/software-intake/solution/SoftwareIntakeSolutionDesign.svg')
        actual = shared_colours(ROOT, ROOT/view['svg'], view)['elements']
        palette = json.loads((ROOT/'docs/08-reference/diagrams/palette.json').read_text())['roles']
        self.assertEqual(actual['RUN-cache-1'],palette['modelSoftware'])
        self.assertEqual(actual['DISK-cache-1'],palette['modelLogical'])
        self.assertEqual(actual['CONTENT-cache-1'],palette['modelInformation'])

    def test_unselected_profile_cannot_recolour_system_overall(self):
        client = Mock()
        style_palette(client, 'context', {'id': 'overall'}, {'key': 'VIEW-system-overall'}, {}, [])
        client.mutate.assert_not_called()
        self.assertEqual(palette_gaps({'key': 'VIEW-system-overall'}, {}, {}, []), [])

    def test_saved_colour_drift_is_detected(self):
        colours = {'fill': '#e7f0fc', 'stroke': '#4d719b', 'color': '#203a5b'}
        view = {'colours': {'elements': {'A': colours}}}
        node = {'id': 'n', 'targetObjectId': 'a', 'type': 'node:rectangle',
                'style': {'background': colours['fill'], 'borderColor': colours['stroke']},
                'insideLabel': {'style': {'color': colours['color']}}}
        self.assertEqual(palette_gaps(view, {'edges': []}, {'A': {'id': 'a'}}, [node]), [])
        node['style']['background'] = '#ffffff'
        self.assertEqual(palette_gaps(view, {'edges': []}, {'A': {'id': 'a'}}, [node]), ['n'])


if __name__ == '__main__':
    unittest.main()
