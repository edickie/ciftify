#!/usr/bin/env python

"""
Calculates fractional amplitude of low-frequency fluctuations (fALFF)

Usage:
    falff_nifti.py <func.nii.gz> <output.nii.gz> [options]

Arguments:
    <func.nii.gz>  The functional 4D nifti files
    <output.nii.gz>  Output filename

Options:
  --min-low-freq 0.01  Min low frequency range value Hz [default: 0.01]
  --max-low-freq 0.08  Max low frequency range value Hz [default: 0.08]
  --min-total-freq 0.00  Min total frequency range value Hz [default: 0.00]
  --max-total-freq 0.25  Max total frequency range value Hz [default: 0.25]
  --mask-file <maskfile.nii.gz>  Input brain mask
  --calc-alff  Calculates amplitude of low frequency fluctuations (ALFF) instead of fALFF
  --debug  Debug logging
  -h,--help  Print help

"""
import logging
import os

from docopt import docopt
import nibabel as nib
import numpy as np
from scipy.fftpack import fft

import ciftify.config
from ciftify.utils import run, TempDir

config_path = os.path.join(os.path.dirname(ciftify.config.find_ciftify_global()), 'bin', "logging.conf")
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))


def main():
    arguments = docopt(__doc__)
    funcfile = arguments['<func.nii.gz>']
    outputname = arguments['<output.nii.gz>']
    min_low_freq = arguments['--min-low-freq']
    max_low_freq = arguments['--max-low-freq']
    min_total_freq = arguments['--min-total-freq']
    max_total_freq = arguments['--max-total-freq']
    maskfile = arguments['--mask-file']
    calc_alff = arguments['--calc-alff']

    logger.setLevel(logging.WARNING)

    if arguments['--debug']:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('ciftify').setLevel(logging.DEBUG)

    logger.info(arguments)

    with ciftify.utils.TempDir() as tmpdir:

        inputfile, maskinput, repetition_time = get_inputs(
            funcfile, maskfile, tmpdir)

        falff_nifti_output = calc_nifti(
            inputfile,
            maskinput,
            min_low_freq,
            max_low_freq,
            min_total_freq,
            max_total_freq,
            tmpdir,
            calc_alff,
            repetition_time
        )

        # Convert nifti output file to cifti output file
        if isinstance(func, nib.Cifti2Image):
            convert_nifti_to_cifti(falff_nifti_output, funcfile, outputname)

        # IF INPUT IS NIFTI FILE
        # If funcfile was not cifti file, save as nifti file to outputname
        if isinstance(func, nib.Nifti1Image):
            run("mv {} {}".format(falff_nifti_output, outputname))


def get_inputs(funcfile, maskfile, tmpdir):
    """Ensure funcfile and maskfile are niftis and get repetition time.
    """
    func = nib.load(funcfile)

    if isinstance(func, nib.Cifti2Image):
        inputfile = convert_cifti_to_nifti(funcfile, tmpdir)
        mask = convert_cifti_to_nifti(maskfile, tmpdir) if maskfile else None
        repetition_time = func.header.get_axis(0).step
    elif isinstance(func, nib.Nifti1Image):
        inputfile = funcfile
        mask = maskfile
        repetition_time = func.header['pixdim'][4]
    else:
        raise IOError("Could not read <func.nii.gz> as nifti or cifti file")

    return inputfile, mask, repetition_time


def convert_cifti_to_nifti(funcfile, tmpdir):
    """ If input is cifti - convert to fake nifti.
    """
    fake_nifti_input = os.path.join(tmpdir, 'input_fake.nii.gz')
    run('wb_command -cifti-convert -to-nifti {} {} '.format(funcfile, fake_nifti_input))
    return fake_nifti_input

# If input is cifti - convert nifti output (falff_nifti_output) back to cifti
# Convert to cifti
def convert_nifti_to_cifti(falff_nifti_output, funcfile, outputname):
    run('wb_command -cifti-convert -from-nifti {} {} {} -reset-scalars'.format(falff_nifti_output, funcfile, outputname))


def calc_nifti(inputfile, maskfile, min_low_freq, max_low_freq, min_total_freq, max_total_freq, tmpdir, calc_alff):
    '''
    calculates falff from nifti input and retruns nifti output

    Takes input files to give to falff function and returns output file
    '''
    # Load in functional data
    func_img = nib.load(inputfile)
    func_data = func_img.get_data()

    # If given input of mask, load in mask file
    # OR if not given input of mask, create mask using std
    if maskfile:
        #1. Given input of mask file
        mask = (nib.load(maskfile)).get_data()
    else:
        #2. Manually create mask
        mask = np.std(func_data, axis=3)

    # Find indices where mask does not = 0
    indx,indy,indz = np.where(mask != 0)

    # Define affine array
    affine = func_img.affine

    # Define x,y,z,t coordinates
    x,y,z,t = func_data.shape

    # Create empty array to save values
    falff_vol = np.zeros((x,y,z))

    # Loop through x,y,z indices, send to calculate_falff function
    for x,y,z in zip(indx,indy,indz):
        falff_vol[x,y,z] = calculate_falff(
            func_data[x, y, z, :],
            min_low_freq,
            max_low_freq,
            min_total_freq,
            max_total_freq,
            calc_alff,
            repetition_time
        )

    # Save falff values to fake nifti output temp file
    output_3D = nib.Nifti1Image(falff_vol, affine)
    falff_nifti_output = os.path.join(tmpdir, 'output_fake.nii.gz') # Make temp directory for nifti output
    output_3D.to_filename(falff_nifti_output)

    return falff_nifti_output

# CALCULATES FALFF
def calculate_falff(timeseries, min_low_freq, max_low_freq, min_total_freq,
                    max_total_freq, calc_alff, repetition_time):
    """This will calculate falff from a timeseries"""

    n = len(timeseries)

    # Takes fast Fourier transform of timeseries
    fft_timeseries = fft(timeseries)
    freq_scale = np.fft.fftfreq(n, repetition_time)
    # Calculates power of fft
    mag = (abs(fft_timeseries))**0.5

    # Finds low frequency range (0.01-0.08) and total frequency range (0.0-0.25)
    low_ind = np.where(
        (float(min_low_freq) <= freq_scale)
        & (freq_scale <= float(max_low_freq))
    )
    total_ind = np.where(
        (float(min_total_freq) <= freq_scale[1:])
        & (freq_scale[1:] <= float(max_total_freq))
    )

    # Indexes power to low frequency index, total frequency range
    low_power = mag[low_ind]
    total_power = mag[1:][total_ind]
    # Calculates sum of lower power and total power
    low_pow_sum = np.sum(low_power)
    total_pow_sum = np.sum(total_power)

    # Calculates alff as the sum of amplitudes within the low frequency range
    if calc_alff:
        calc = low_pow_sum
    # Calculates falff as the sum of power in low frequnecy range divided by sum of power in the total frequency range
    else:
        calc = np.divide(low_pow_sum, total_pow_sum)

    return calc

if __name__=='__main__':
    main()
