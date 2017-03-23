import unittest

from mock import MagicMock, mock_open, patch

from ciftify import html

class TestWriteIndexPages(unittest.TestCase):

    @patch('ciftify.html.write_image_index')
    @patch('ciftify.html.add_image_and_subject_index')
    @patch('ciftify.html.add_page_header')
    @patch('__builtin__.open')
    def test_writes_images_to_index(self, mock_open, mock_add_header,
            mock_add_img_subj, mock_index):
        mock_file = MagicMock(spec=file)
        mock_open.return_value.__enter__.return_value = mock_file
        qc_config = self.get_config_stub()
        settings = self.get_settings()

        html.write_index_pages(settings, qc_config)

        expected_writes = len(qc_config.images)
        assert mock_index.call_count == expected_writes

    @patch('ciftify.html.write_image_index')
    @patch('ciftify.html.add_image_and_subject_index')
    @patch('ciftify.html.add_page_header')
    @patch('__builtin__.open')
    def test_doesnt_write_images_if_make_index_is_false(self, mock_open,
            mock_add_header, mock_add_img_subj, mock_index):
        mock_file = MagicMock(spec=file)
        mock_open.return_value.__enter__.return_value = mock_file
        qc_config = self.get_config_stub(make_all=False)
        settings = self.get_settings()

        html.write_index_pages(settings, qc_config)

        # One image in the list should have 'make_index' = False
        expected_writes = len(qc_config.images) - 1
        assert mock_index.call_count == expected_writes

    def get_config_stub(self, make_all=True):
        class ImageStub(object):
            def __init__(self, make):
                self.make_index = make
                self.name = "some_name"

        class QCConfigStub(object):
            def __init__(self):
                self.qc_dir = '/some/path/qc'
                if make_all:
                    self.images = [ImageStub(True), ImageStub(True),
                            ImageStub(True)]
                else:
                    self.images = [ImageStub(True), ImageStub(False),
                            ImageStub(True)]
        return QCConfigStub()

    def get_settings(self):
        class Settings(object):
            def __init__(self):
                self.qc_dir = '/some/path/qc'
                self.qc_mode = 'some_mode'
        return Settings()

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

class TestAddImageAndSubjectIndex(unittest.TestCase):

    def test_adds_all_expected_images_to_page(self):
        html_page = MagicMock(spec=file)
        image1 = self.__make_image_stub('temporal')
        image2 = self.__make_image_stub('medial')
        images = [image1, image2]

        html.add_image_and_subject_index(html_page, images, [], 'test')

        image_link = '<a href="{}.html">'
        for image in images:
            assert self.call_found(html_page.write.call_args_list,
                    image_link.format(image.name))

    def test_image_not_added_to_index_if_image_settings_exclude_it(self):
        html_page = MagicMock(spec=file)
        image1 = self.__make_image_stub('temporal')
        image2 = self.__make_image_stub('medial', make=False)
        image3 = self.__make_image_stub('mpfc')
        images = [image1, image2, image3]

        html.add_image_and_subject_index(html_page, images, [], 'test')

        image_link = '<a href="{}.html">'.format(image2.name)
        assert html_page.write.call_count > 1
        for call in html_page.write.call_args_list:
            assert image_link not in call[0]

    def test_adds_qc_page_for_all_subjects_in_list(self):
        html_page = MagicMock(spec=file)
        subjects = ['subject1', 'subject2', 'subject3']
        html_string = '<a href="{}/qc.html">'

        html.add_image_and_subject_index(html_page, [], subjects, 'test')

        args_list = html_page.write.call_args_list

        for subject in subjects:
            assert self.call_found(html_page.write.call_args_list,
                    html_string.format(subject))

    def call_found(self, call_list, item):
        found = False
        for call in call_list:
            # Access the string from the tuple stored in each call
            if item in call[0][0]:
                found = True
                break
        return found

    def __make_image_stub(self, name, make=True):
        class Image(object):
            def __init__(self, name, make):
                self.make_index = make
                self.name = name
        return Image(name, make)

class TestAddPageHeader(unittest.TestCase):

    subject = "subject_1234"
    page_subject = "testing page"

    def test_page_subject_set_as_title_when_none_given(self):
        html_page = MagicMock(spec=file)
        qc_config = self.get_config_stub()

        html.add_page_header(html_page, qc_config, self.page_subject)

        for call in html_page.write.call_args_list:
            if '<TITLE>' in call[0]:
                assert self.page_subject in call[0]

    def test_title_used_when_given(self):
        html_page = MagicMock(spec=file)
        qc_config = self.get_config_stub()
        title = 'THIS IS MY TITLE'

        html.add_page_header(html_page, qc_config, self.page_subject,
                title=title)

        for call in html_page.write.call_args_list:
            if '<TITLE>' in call[0]:
                assert title in call[0]
                assert self.page_subject not in call[0]

    def test_subject_added_to_title_when_given(self):
        html_page = MagicMock(spec=file)
        qc_config = self.get_config_stub()

        html.add_page_header(html_page, qc_config, self.page_subject,
                subject=self.subject)

        for call in html_page.write.call_args_list:
            if '<TITLE>' in call[0]:
                assert self.subject in call[0]

    def test_QC_header_line_added_when_subject_given(self):
        html_page = MagicMock(spec=file)
        qc_config = self.get_config_stub()

        html.add_page_header(html_page, qc_config, self.page_subject,
                subject=self.subject)

        for call in html_page.write.call_args_list:
            if '<h1>' in call[0]:
                assert self.subject in call[0]

    def test_header_line_not_added_when_subject_not_given(self):
        html_page = MagicMock(spec=file)
        qc_config = self.get_config_stub()

        html.add_page_header(html_page, qc_config, self.page_subject)

        for call in html_page.write.call_args_list:
            assert '<h1>' not in call[0]

    def get_config_stub(self):
        class ConfigStub(object):
            def __init__(self):
                pass
            def get_navigation_list(self, path):
                return []
        return ConfigStub()
