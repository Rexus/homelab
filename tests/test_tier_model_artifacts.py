"""Portable CI must catch altered deliverables without rerendering platform font geometry."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/architecture'))
from model_artifacts import seal_outputs, verify_outputs


class ModelArtifacts(unittest.TestCase):
    def test_missing_or_changed_generated_output_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outputs = {Path('view.svg'): '<svg>accepted</svg>\n'}
            snapshot = {'outputs_sha256': seal_outputs(outputs)}
            with self.assertRaisesRegex(ValueError, 'missing generated'):
                verify_outputs(root, snapshot)
            (root / 'view.svg').write_text(outputs[Path('view.svg')])
            verify_outputs(root, snapshot)
            (root / 'view.svg').write_text('<svg>wrong element</svg>')
            with self.assertRaisesRegex(ValueError, 'Changed or missing'):
                verify_outputs(root, snapshot)

    def test_absent_manifest_and_escaping_path_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, 'no generated-artifact'):
                verify_outputs(root, {})
            with self.assertRaisesRegex(ValueError, 'Changed or missing'):
                verify_outputs(root, {'outputs_sha256': {'../escape.svg': 'hash'}})

    def test_line_endings_are_portable(self):
        self.assertEqual(seal_outputs({Path('x'): 'a\r\nb\r\n'}), seal_outputs({Path('x'): 'a\nb\n'}))
