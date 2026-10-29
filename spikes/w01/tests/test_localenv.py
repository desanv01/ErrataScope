"""No real keys or provider requests; isolated configuration behavior checks."""
import os
import uuid
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
import importlib.util
from contextlib import redirect_stdout
import io

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from erratascope_w01.localenv import LocalEnvError, load_nebius_key


class LocalEnvTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[3] / '.local' / 'config-tests'
        directory = parent / uuid.uuid4().hex
        directory.mkdir(parents=True)
        self.path = directory / '.env.local'
        self.addCleanup(directory.rmdir)
        self.addCleanup(self.path.unlink, missing_ok=True)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_missing_or_empty_is_not_configured(self):
        self.assertEqual(load_nebius_key(self.path), 'missing')
        self.path.write_text('NEBIUS_API_KEY=\n')
        self.assertEqual(load_nebius_key(self.path), 'missing')

    def test_local_key_and_quotes(self):
        self.path.write_text('# comment\nOTHER=ignored\nNEBIUS_API_KEY="fake-test-key"\n')
        self.assertEqual(load_nebius_key(self.path), 'project_env_local')
        self.assertEqual(os.environ['NEBIUS_API_KEY'], 'fake-test-key')
        self.assertNotIn('OTHER', os.environ)

    def test_existing_environment_wins(self):
        os.environ['NEBIUS_API_KEY'] = 'existing-test-key'
        self.path.write_text('NEBIUS_API_KEY=file-test-key\n')
        self.assertEqual(load_nebius_key(self.path), 'process_environment')
        self.assertEqual(os.environ['NEBIUS_API_KEY'], 'existing-test-key')

    def test_duplicate_rejected_without_secret_in_error(self):
        self.path.write_text('NEBIUS_API_KEY=private-test-value\nNEBIUS_API_KEY=second-value\n')
        with self.assertRaises(LocalEnvError) as caught:
            load_nebius_key(self.path)
        self.assertNotIn('private-test-value', str(caught.exception))
        self.assertNotIn('NEBIUS_API_KEY', os.environ)

    def test_invalid_quoting_rejected_without_value(self):
        self.path.write_text('NEBIUS_API_KEY="private-test-value\n')
        with self.assertRaises(LocalEnvError) as caught:
            load_nebius_key(self.path)
        self.assertNotIn('private-test-value', str(caught.exception))

    def test_no_shell_or_environment_interpolation(self):
        self.path.write_text('NEBIUS_API_KEY=$(not-a-command)\n')
        load_nebius_key(self.path)
        self.assertEqual(os.environ['NEBIUS_API_KEY'], '$(not-a-command)')

    def test_cli_check_loads_file_without_showing_key_or_logging(self):
        spec = importlib.util.spec_from_file_location('localenv_cli_test', Path(__file__).resolve().parents[1] / 'run.py')
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        self.path.write_text('NEBIUS_API_KEY=private-cli-test-value\n')
        output = io.StringIO()
        with patch.object(cli.config, 'PROJECT_ROOT', self.path.parent), patch.object(cli.config, 'REPAIR_BASELINE_PATH', self.path.parent / 'baseline.json'), patch.object(cli, '_log_command') as log, redirect_stdout(output):
            self.assertEqual(cli.main(['check-key']), 0)
        self.assertEqual(output.getvalue().strip(), 'NEBIUS_API_KEY: CONFIGURED')
        log.assert_not_called()


if __name__ == '__main__':
    unittest.main()
