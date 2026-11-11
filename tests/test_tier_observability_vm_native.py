"""Validate VM product inputs with the same pinned native parsers as the cluster path."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

from test_tier_observability_vm import ObservabilityVMTests
from test_tier_observability_platform import DATA_PREPPER_CHECK


class NativeVmProductConfiguration(unittest.TestCase):
    def setUp(self):
        self.fixture = ObservabilityVMTests('test_all_yaml_and_task_includes_parse')
        self.fixture.setUp()

    @unittest.skipUnless(os.environ.get('OTELCOL_BINARY'), 'Requires the pinned native Collector')
    def test_collector_accepts_persistent_dual_writes_and_separate_source_scopes(self):
        with tempfile.TemporaryDirectory(prefix='vm-collector-') as directory:
            path = Path(directory) / 'collector.yml'
            path.write_text(self.fixture.render('collector.yml.j2'))
            result = subprocess.run([os.environ['OTELCOL_BINARY'], 'validate', '--config', str(path)],
                capture_output=True, text=True, timeout=30,
                env=dict(os.environ, VM_USERNAME='synthetic', VM_PASSWORD='synthetic',
                         DP_USERNAME='synthetic', DP_PASSWORD='synthetic'))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(os.environ.get('DATA_PREPPER_HOME'), 'Requires the pinned native Data Prepper')
    def test_data_prepper_accepts_native_sources_authentication_buffers_and_sinks(self):
        home = Path(os.environ['DATA_PREPPER_HOME'])
        jdk = next((home / 'openjdk').glob('*/bin'))
        classpath = str(home / 'lib' / '*')
        pipelines = yaml.safe_load(self.fixture.render('prepper.yml.j2'))
        with tempfile.TemporaryDirectory(prefix='vm-prepper-') as directory:
            source = Path(directory) / 'DataPrepperConfigCheck.java'
            source.write_text(DATA_PREPPER_CHECK)
            inputs = Path(directory) / 'pipelines.json'
            inputs.write_text(json.dumps(pipelines))
            result = subprocess.run([str(jdk / 'javac'), '-cp', classpath, '-d', directory, str(source)],
                capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(jdk / 'java'), '-cp', directory + os.pathsep + classpath,
                'org.opensearch.dataprepper.plugin.DataPrepperConfigCheck', str(inputs)],
                capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('configurations accepted: 12', result.stdout)
