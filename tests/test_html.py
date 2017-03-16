import unittest

from mock import MagicMock, mock_open, patch

from ciftify import html

class TestWriteNavbar(unittest.TestCase):

    brand_name = 'subject_1234'
    nav_list = [{'href': '', 'label': 'View:'},
                {'href': 'some_item.html', 'label': 'item1'}]

    def test_no_items_marked_active_if_activelink_not_set(self):
        html_page = MagicMock(spec=file)

        html.write_navbar(html_page, self.brand_name, self.nav_list)
        for call in html_page.write.call_args_list:
            assert 'class="active"' not in call[0]

    def test_items_marked_active_if_activelink_set(self):
        html_page = MagicMock(spec=file)
        active_item = self.nav_list[1]['href']

        html.write_navbar(html_page, self.brand_name, self.nav_list,
                activelink=active_item)

        for call in html_page.call_args_list:
            html_string = call[0]
            if active_item in html_string:
                assert 'class="active"' in html_string

class TestWriteImageIndex(unittest.TestCase):

    qc_dir = '/some/path/qc'
    subjects = ['subject1', 'subject2']
    page_subject = 'testing'
    image_name = 'test'

    @patch('ciftify.html.add_page_header')
    @patch("__builtin__.open")
    def test_title_added_when_given(self, mock_open, mock_header):
        # Set up
        # fake page to 'open' and write to
        html_page = MagicMock(spec=file)
        mock_open.return_value.__enter__.return_value = html_page
        # qc_config.Config stub
        class MockQCConfig(object):
            def __init__(self):
                pass
        title = "TEST HEADER"

        # Call
        html.write_image_index(self.qc_dir, self.subjects, MockQCConfig(),
                self.page_subject, self.image_name, title=title)

        # Assert
        for call in html_page.write.call_args_list:
            # If an h1 header line is being written, the given title should
            # be the contents.
            if '<h1>' in call[0]:
                assert title in call[0]
        # Title should be in the list of keyword arguments passed to
        # add_page_header
        assert mock_header.call_count == 1
        header_kword_args = mock_header.call_args_list[0][1]
        assert 'title' in header_kword_args.keys()
        assert header_kword_args['title'] == title

    @patch('ciftify.html.add_page_header')
    @patch('__builtin__.open')
    def test_title_not_added_when_not_given(self, mock_open, mock_header):
        # Set up
        # fake page to 'open' and write to
        html_page = MagicMock(spec=file)
        mock_open.return_value.__enter__.return_value = html_page
        # qc_config.Config stub
        class MockQCConfig(object):
            def __init__(self):
                pass

        # Call
        html.write_image_index(self.qc_dir, self.subjects, MockQCConfig(),
                self.page_subject, self.image_name)

        # Assert
        for call in html_page.write.call_args_list:
            assert '<h1>' not in call[0]
        assert mock_header.call_count == 1
        header_kword_args = mock_header.call_args_list[0][1]
        assert 'title' in header_kword_args.keys()
        assert header_kword_args['title'] == None

    @patch('ciftify.html.add_image_and_subject_page_link')
    @patch('__builtin__.open')
    def test_image_and_subject_page_linked_for_each_subject(self, mock_open,
            mock_link):
        # Set up
        html_page = MagicMock(spec=file)
        mock_open.return_value.__enter__.return_value = html_page
        class MockQCConfig(object):
            def __init__(self):
                pass
            def get_navigation_list(self, path):
                return []

        # Call
        html.write_image_index(self.qc_dir, self.subjects, MockQCConfig(),
                self.page_subject, self.image_name)

        # Assert
        assert mock_link.call_count == len(self.subjects)
