#!/usr/bin/env python
"""
Will use nilearn.image.clean_img to do filtering and confound regression according
to user settings. Optional smoothing can also be added

Usage:
    ciftify_clean_img [options] <func_input>

Options:
  --output_file           Path to output cleaned image
                          (default will append _clean to input)
  --clean-config=<json>   A json file to override/specify all cleaning settings
  --drop-dummy-TRs=<int>  Discard the indicated number of TR's from the begginning before
  --no-cleaning           No filtering, detrending or confound regression steps
  --detrend               If detrending should be not applied to timeseries
  --standardize           If indicated, returned signals not are set to unit variance.
  --confounds-tsv=<FILE>  The path to a confounds file for confound regression
  --cf-cols=<cols>        The column names from the confounds file to include
  --cf-sq-cols=<cols>     Also include the squares (quadratic) of these columns in the confounds file
  --cf-td-cols=<cols>     Also include the temporal derivative of these columns in the confounds file
  --cf-sqtd-cols=<cols>   Also include the squares of the temporal derivative of these columns in the confounds file
  --low-pass=<Hz>         Lowpass filter cut-offs
  --high-pass=<Hz>        Highpass filter cut-offs
  --t_r=<tr>              Indicate the TR for filtering in seconds (default will read from file)
  --smooth_fwhm=<FWHM>    The full width half max of the smoothing kernel if desired
  --left-surface=<gii>    Left surface file (required for smoothing)
  --right-surface=<GII>   Right surface file (required for smoothing)

  -v,--verbose            Verbose logging
  --debug                 Debug logging
  -h, --help              Prints this message

DETAILS:



"""
import os
import pandas
import json
import yaml

import ciftify.niio
from ciftify.meants import NibInput
import ciftify.utils
import nilearn.image

from nibabel import Nifti1Image


class UserSettings(object):
    def __init__(self, arguments):
        args = self.__update_clean_config(arguments)
        self.func = self.__get_input_file(args['<func_input>'])
        self.start_from_tr = self.__get_dummy_trs(args['--drop-dummy-TRs'])
        self.confounds = self.__get_confounds(args)
        self.cf_cols = self.__split_list_arg(args['--cf-cols'])
        self.cf_sq_cols = self.__split_list_arg(args['--cf-sq-cols'])
        self.cf_td_cols = self.__split_list_arg(args['--cf-td-cols'])
        self.cf_sqtd_cols = self.__split_list_arg(args['--cf-sqtd-cols'])
        self.detrend = args['--detrend']
        self.standardize = args['--standardize']
        self.high_pass = self.__parse_bandpass_filter_flag(args['--high_pass'])
        self.low_pass = self.__parse_bandpass_filter_flag(args['--low_pass'])
        self.func.tr = self.__get_tr(args['--t_r'])
        self.smooth = Smoothing(args)
        self.output_func, self.output_json = self.__get_output_file(args['--output_file'])

    def __update_clean_config(self, user_args):
        '''merge a json config, if specified into the user_args dict'''
        if not user_args['--clean-config']:
            return user_args
        try:
            user_config = json.load(user_args['--clean-config'])
        except:
            logger.critical("Could not load the json config file")
        clean_config = merge(user_args, user_config)
        return clean_config

    def __get_input_file(self, user_func_input):
        '''check that input is readable and either cifti or nifti'''
        func = NibInput(user_func_input)
        if func.type == "cifti":
            if not func.path.endswith(".dtseries.nii"):
                logger.warning('cifti input file should be a .dtseries.nii file {} given'.format(func.path))
        if not any(func.type == "cifti", func.type == "nifti"):
            logger.error("ciftify_clean_img only works for nifti or cifti files {} given".format(func.path))
            sys.exit(1)
        return func



    def __get_dummy_trs(self, tr_drop_arg):
        ''' set the first tr for processing according to the tr drop user arg'''
        if tr_drop_arg:
            return int(tr_drop_arg)
        else:
            return 0

    def __split_list_arg(self, list_arg):
        '''split list arguments that were comma separated into lists'''
        if list_arg:
            return list_arg.split(",")
        else:
            return []

    def __get_confounds(self, args):
        '''if confounds args given, parse them else return None
        devide list args into proper lists
        try to read in the input csv
        check that columns indicated are in the input table
        '''
        if not args['--confound-tsv']:
            return None
        try:
            confounddf = pd.read_csv(args['--confound-tsv'], sep='\t')
        except:
            logger.critical("Failed to read confounds tsv {}".format(args['--confounds-tsv']))
            sys.exit(1)
        for args_cols_list in [self.cf_cols, self.cf_sq_cols, self.cf_sq_cols, self.cf_sqtd_cols]:
            for colname_arg in args_cols_list:
                if colname_arg not in confounddf.columns:
                    logger.error('Indicated column {} not in confounds'.format(colname_arg))
                    sys.exit(1)
        return confounddf


    def __get_tr(self, tr_arg):
        '''read tr from func file is not indicated'''
        if tr_arg:
            tr = tr_arg
        else:
            if func.type == "nifti":
                tr_ms = nib.load(filename).header.get_zooms()[3]
                tr = float(tr_ms) / 1000
            if func.type == "cifti":
                tr_out = ciftify.utils.get_stdout(['wb_command','-file-information',
                        '-only-step-interval', self.func.path])
                tr = float(tr_out.strip())
        if tr > 150:
            logger.warning("TR should be specified in seconds, improbable value {} given".format(tr))
        return tr

    def __parse_bandpass_filter_flag(self, user_arg):
        '''import the bandpass filtering argument as float value or None'''
        if not user_arg:
            return None
        try:
            filter_arg = float(user_arg)
        except:
            logger.error("Unable to parse bandpass filtering arg")
            sys.exit(1)
        return(filter_arg)

    def __get_output_file(self, user_output_arg):
        '''if user argument for output specified, check it. If not, define output'''
        if user_output_arg:
            output_file = user_output_arg
            outbase, out_type = NibInput.determine_filetype(output_file)
            if out_type != self.func.type:
                logger.warning('Input and output filetypes do not match!')
            output_json = os.path.join(os.path.dirname(output_file),
                            '{}.json'.format(outbase))
        else:
            output_ext = 'dtseries.nii' if self.func.type == "cifti" else "nii.gz"
            output_file = os.path.join(os.path.dirname(self.func.path),
                                '{}_clean_s{}.{}'.format(self.func.base,
                                                         self.smooth.fwhm,
                                                         output_ext))
            output_json = os.path.join(os.path.dirname(self.func.path),
                                '{}_clean_s{}.json'.format(self.func.base,
                                                           self.smooth.fwhm))
        ciftify.utils.check_output_writable(output_file)
        return output_file, output_json

    def print_settings(self):
        '''write settings to json and log'''
        with open(self.output_json, 'w') as fp:
            json.dump(self.args, fp)
        logger.info(yaml.dump(self.args))

class Smoothing(object):
    '''
    a class holding smoothing as both FWHM and Sigma value
    will be nested inside the settings

    Initialized with the user arg of FWHM or None
    '''
    def __init__(self, smoothing_arg, func_type, left_surf_arg, right_surf_arg):
        self.fwhm = 0
        self.sigma = 0
        self.left_surface = left_surf_arg
        self.right_surface = right_surf_arg
        if smoothing_arg:
            self.fwhm = smoothing_arg
            if float(smoothing_arg) > 6:
                logger.warning('Smoothing kernels greater than 6mm FWHM are not '
                  'recommended by the HCP, {} specified'.format(self.fwhm))
            self.sigma = ciftify.utils.FWHM2Sigma(float(self.fwhm))
            if func_type == "cifti":
                for surf in [self.left_surface, self.right_surface]:
                    if surf:
                        check_input_readable(surf)
                    else:
                        logger.error("For cifti smoothing, --left-surface and --right-surface inputs are required! Exiting")
                        sys.exit(1)

def run_ciftify_clean_img(arguments,tmpdir):

    settings = UserSettings()
    settings.log_settings()

    # check the confounds define the true confounds for nilearn
    confound_signals = mangle_confounds(settings)

    # if input is cifti - we convert to fake nifti
    ## convert to nifti
    if settings.func.type == "cifti":
        input_nifti = os.path.join(tempdir,'func_fnifti.nii.gz')
        run(['wb_command','-cifti-convert','-to-nifti',settings.func.path, func_fnifti])
    else:
        input_nifti = settings.func.path

    # load image as nilearn image
    nib_image = nilearn.image.load_img(input_nifti)

    if settings.start_from_tr > 0:
        trimmed_nifti = image_drop_dummy_trs(nib_image, settings.start_from_tr)
    else:
        trimmed_nifti = nib_image

    # the nilearn cleaning step..
    clean_output = clean_image_with_nilearn(nib_image, confound_signals, settings)

    # or nilearn image smooth if nifti input
    if settings.func.type == "nifti":
        if settings.smooth.fwhm > 0 :
            smoothed_vol = nilearn.image.smooth_img(clean_output, fwhm)
            smoothed_vol.to_filename(settings.output_file)
        else:
            clean_output.to_filename(settings.output_file)

    # if input cifti - convert back to nifti
    if settings.func.type == "cifti":
        clean_output_nifti = os.path.join(tmpdir, 'clean_fnifti.nii.gz')
        clean_output.to_filename(clean_output_nifti)

        if settings.smooth.fwhm > 0:
            clean_output_cifti = os.path.join(tmpdir, 'cleaned.dtseries.nii')
        else:
            clean_output_cifti = settings.output_file

        ## convert back not need a template with the same dimensions as the output
        run(['wb_command','-cifti-convert','-from-nifti',
            clean_output_nifti,
            settings.func.path,
            clean_output_cifti])

        if settings.smooth.fwhm > 0:
            run(['wb_command', '-cifti-smoothing',
                clean_output_cifti,
                settings.smooth.sigma,
                settings.smooth.sigma,
                'COLUMN',
                settings.output_file,
                '-left-surface', settings.smooth.left_surface,
                '-right-surface', settings.smooth.right_surface])


def merge(dict_1, dict_2):
    """Merge two dictionaries.
    Values that evaluate to true take priority over falsy values.
    `dict_1` takes priority over `dict_2`.
    """
    return dict((str(key), dict_1.get(key) or dict_2.get(key))
                for key in set(dict_2) | set(dict_1))

def image_drop_dummy_trs(nib_image, start_from_tr):
    ''' use nilearn to drop the number of trs from the image'''
    data_out = nib_image.get_data()[:,:,:, start_from_tr:]
    img_out = nilearn.image.new_image_like(nib_image, data_out, nib_image.copy(), copy_header = True)
    return img_out

def mangle_confounds(settings):
    '''mangle the confounds according to user settings
    insure that output matches length of func input and NA's are not present..'''
    # square a column in pandas df['c'] = df['b']**2
    # or np.square(x) (is faster) pandas.Series.diff for lags
    # start by removing the tr's
    if settings.confounds is None:
        return None
    start_tr = settings.start_from_tr
    df = settings.confounds.iloc[start_tr:, :]
    # then select the columns of interest
    outdf = df[settings.cf_cols]
    # then add the squares
    for colname in settings.cf_sq_cols:
        outdf['{}_sq'.format(colname)] = df[colname]**2
    # then add the lags
    for colname in settings.cf_td_cols:
        outdf['{}_lag'.format(colname)] = df[colname].diff()
    # then add the squares of the lags
    for colname in settings.cf_sqtd_cols:
        df['{}_lag'.format(colname)] = df[colname].diff()
        outdf['{}_sqlag'.format(colname)] = df['{}_lag'.format(colname)]**2
    return outdf

def clean_image_with_nilearn(input_img, confound_signals, settings):
    '''clean the image with nilearn.image.clean()
    '''
    # first determiner if cleaning is required
    if any((settings.detrend == True,
           settings.standardize == True,
           confound_signals != None,
           settings.high_pass != None,
           settings.low_pass != None)):

        # the nilearn cleaning step..
        clean_output = nilearn.image.clean_img(input_img,
                            detrend=settings.detrend,
                            standardize=settings.standardize,
                            confounds=confound_signals,
                            low_pass=settings.low_pass,
                            high_pass=settings.high_pass,
                            t_r=settings.func.tr)
        return clean_output
    else:
        return input_img

def main():
    arguments = docopt(__doc__)
    debug = arguments['--debug']
    verbose = arguments['--verbose']

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)

    if verbose:
        ch.setLevel(logging.INFO)

    if debug:
        ch.setLevel(logging.DEBUG)

    logger.addHandler(ch)

    ## set up the top of the log
    logger.info('{}{}'.format(ciftify.utils.ciftify_logo(),
        ciftify.utils.section_header('Starting ciftify_clean_img')))

    with ciftify.utils.TempDir() as tmpdir:
        logger.info('Creating tempdir:{} on host:{}'.format(tmpdir,
                    os.uname()[1]))
        ret = run_ciftify_seed_corr(arguments, tmpdir)

    logger.info(ciftify.utils.section_header('Done ciftify_clean_img'))
    sys.exit(ret)

if __name__ == '__main__':
    main()
