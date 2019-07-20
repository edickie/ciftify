#!/usr/bin/env python3
import os
import unittest
import logging
import shutil
import tempfile
import ciftify.config
from ciftify.utils import run

from pytest import raises
from unittest.mock import patch
import pytest

def get_test_data_path():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

@pytest.fixture(scope = "function")
def output_dir():
    with ciftify.utils.TempDir() as outputdir:
        yield outputdir

test_dtseries = os.path.join(get_test_data_path(),
        'sub-50005_task-rest_Atlas_s0.dtseries.nii')
test_nifti = os.path.join(get_test_data_path(),
        'sub-50005_task-rest_bold_space-MNI152NLin2009cAsym_preproc.nii.gz')


def test_ciftify_falff_dtseries(output_dir):
    output_nii = os.path.join(output_dir, 'output_falff.dscalar.nii')
    run(['ciftify_falff', test_dtseries, output_nii])
    assert os.path.isfile(output_nii)


def test_ciftify_falff_nifti(output_dir):
    output_nii = os.path.join(output_dir, 'output_falff.nii.gz')
    run(['ciftify_falff', test_nifti, output_nii])
    assert os.path.isfile(output_nii)
