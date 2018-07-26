#!/usr/bin/env python3
import os
import unittest
import logging
import shutil
import random

from nose.tools import raises
from mock import patch

import ciftify.niio as niio

logging.disable(logging.CRITICAL)

class TestDetermineFiletype(unittest.TestCase):

    def test_recognizes_dtseries(self):
        file_name = "subject1_data.dtseries.nii"

        mr_type, mr_base = niio.determine_filetype(file_name)

        assert mr_type == 'cifti'
        assert mr_base == 'subject1_data'

    def test_recognizes_dscalar(self):
        file_name = "subject1_data.dscalar.nii"

        mr_type, mr_base = niio.determine_filetype(file_name)

        assert mr_type == 'cifti'
        assert mr_base == 'subject1_data'

    def test_recognizes_dlabel(self):
        file_name = "subject1_data.dlabel.nii"

        mr_type, mr_base = niio.determine_filetype(file_name)

        assert mr_type == 'cifti'
        assert mr_base == 'subject1_data'

    def test_recognizes_nifti(self):
        file1 = "subject1_data.nii"
        file2 = "subject1_data.nii.gz"

        mr_type1, mr_base1 = niio.determine_filetype(file1)
        mr_type2, mr_base2 = niio.determine_filetype(file2)

        assert mr_type1 == 'nifti'
        assert mr_type2 == 'nifti'
        assert mr_base1 == mr_base2

    def test_recognizes_gifti_files(self):
        gifti1 = 'subject1_data.shape.gii'
        gifti2 = 'subject1_data.func.gii'
        gifti3 = 'subject1_data.surf.gii'
        gifti4 = 'subject1_data.label.gii'
        gifti5 = 'subject1_data.gii'

        giftis = [gifti1, gifti2, gifti3, gifti4, gifti5]

        for gifti_type in giftis:
            mr_type, mr_base = niio.determine_filetype(gifti_type)
            assert mr_type == 'gifti'
            assert mr_base == 'subject1_data'

    def test_doesnt_mangle_dot_delimited_file_names(self):
        dot_name1 = 'subject.aparc.dlabel.nii'
        dot_name2 = 'subject.R.pial.gii'

        mr_type1, mr_base1 = niio.determine_filetype(dot_name1)
        mr_type2, mr_base2 = niio.determine_filetype(dot_name2)

        assert mr_type1 == 'cifti'
        assert mr_base1 == 'subject.aparc'
        assert mr_type2 == 'gifti'
        assert mr_base2 == 'subject.R.pial'

    def test_returns_basename_even_when_full_path_given(self):
        file_name = '/some/path/subject1_data.dlabel.nii'

        mr_type, mr_base = niio.determine_filetype(file_name)

        assert mr_type == 'cifti'
        assert mr_base == 'subject1_data'

    @raises(SystemExit)
    def test_raises_exception_with_unrecognized_filetype(self):
        file_name = 'subject1_data.txt'

        mr_type, mr_base = niio.determine_filetype(file_name)

class TestLoadNii(unittest.TestCase):

    @raises(SystemExit)
    def test_exits_gracefully_if_nifti_cannot_be_read(self):
        path = '/some/path/fake_nifti.nii.gz'

        niio.load_nifti(path)

        # Should never reach here
        assert False

class TestLoadCifti(unittest.TestCase):

    @raises(SystemExit)
    def test_exits_gracefully_if_cifti_cannot_be_read(self):
        path = '/some/path/subject.data.dscalar.nii'

        niio.load_cifti(path)
        assert False

class TestLoadGiiData(unittest.TestCase):

    @raises(SystemExit)
    def test_exits_gracefully_if_gifti_cannot_be_read(self):
        path = '/some/path/subject.data.shape.gii'

        niio.load_gii_data(path)
        assert False
