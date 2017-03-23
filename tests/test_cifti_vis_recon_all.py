import unittest
import logging
import importlib
import random

from mock import patch, MagicMock, mock_open
from nose.tools import raises

recon = importlib.import_module('bin.cifti_vis_recon_all')

logging.disable(logging.CRITICAL)

class TestWriteSingleQCPage(unittest.TestCase):

    @patch('bin.cifti_vis_recon_all.generate_qc_page')
    @patch('os.path.exists')
    def test_exits_without_doing_work_if_page_exists(self, mock_exists,
            mock_generate):
        mock_exists.return_value = True
        class SettingsStub(object):
            def __init__(self):
                self.qc_dir = '/some/path/qc'
                self.subject = 'subject_1'
                self.hcp_dir = '/some/other/path/hcp'

        recon.write_single_qc_page(SettingsStub(), None)

        assert mock_generate.call_count == 0

class TestPersonalizeTemplate(unittest.TestCase):

    @raises(SystemExit)
    def test_exits_gracefully_when_template_cannot_be_read(self):
        template = '/some/path/fake_file.scene'
        recon.personalize_template(template, None, None)
        # Should never reach this line
        assert False

    @raises(SystemExit)
    @patch('__builtin__.open')
    def test_exits_gracefully_when_template_is_empty(self, mock_open):
        template_contents = MagicMock(spec=file)
        template_contents.read.return_value = []
        mock_open.return_value.__enter__.return_value = template_contents

        recon.personalize_template('/some/file/template.scene',
                '/some/other/dir', None)
        # Should never reach this line
        assert False

    @patch('__builtin__.open')
    def test_modifies_base_template(self, mock_open):
        # Set up:
        # Fake template file contents with a single key inserted to be modified
        # A 'settings' stub that provides only the values needed by the function
        mock_file = MagicMock(spec=file)
        mock_file.return_value = get_template_contents(['SUBJID'])
        mock_open.return_value.__enter__.return_value = mock_file
        class Settings(object):
            def __init__(self):
                self.qc_mode = 'some_mode'
                self.hcp_dir = '/some/path/hcp'
                self.subject = 'some_subject'

        recon.personalize_template('/some/template.scene', '/some/dir',
                Settings())

        assert mock_file.write.call_count == 1

class TestModifyTemplateContents(unittest.TestCase):

    original_vals = ['HCP_DATA_PATH', 'SUBJID']

    def test_expected_strings_are_replaced(self):
        settings = self.get_settings()
        template_contents = get_template_contents(self.original_vals)
        modified_text = recon.modify_template_contents(template_contents,
                settings)
        for val in self.original_vals:
            assert val not in modified_text

    def get_settings(self):
        class SettingsStub(object):
            def __init__(self):
                self.hcp_dir = '/path/num1'
                self.subject = 'subject_id'
        return SettingsStub()


def get_template_contents(keys):
    # Not a stroke, just randomly generated text
    mock_contents = ['Behind sooner dining so window excuse he summer.',
            ' Breakfast met certainty and fulfilled propriety led. ',
            ' Waited get either are wooded little her. Contrasted ',
            'unreserved as mr particular collecting it everything as ',
            'indulgence. Seems ask meant merry could put. Age old begin ',
            'had boy noisy table front whole given.']
    mock_contents.extend(keys)
    random.shuffle(mock_contents)
    template_contents = ' '.join(mock_contents)
    return template_contents
