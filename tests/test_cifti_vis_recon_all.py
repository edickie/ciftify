import unittest
import logging
import importlib
import random

from mock import patch, MagicMock, mock_open
from nose.tools import raises

recon = importlib.import_module('ciftify.bin.cifti_vis_recon_all')

logging.disable(logging.CRITICAL)

class TestUserSettings(unittest.TestCase):

    @raises(SystemExit)
    def test_exits_gracefully_when_user_supplies_undefined_qc_mode(self):
        arguments = {'<subject>': 'some_subject',
                     '<QCmode>': 'new_mode'}
        recon.UserSettings(arguments)
        assert False

class TestWriteSingleQCPage(unittest.TestCase):

    @patch('ciftify.bin.cifti_vis_recon_all.generate_qc_page')
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
