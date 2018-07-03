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
  --confounds-cols=<cols>  The column names from the confounds file to include
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

import ciftify.niio
from ciftify.meants import NibInput


class UserSettings(object):
    def __init__(self, arguments):
        args = update_clean_config(self, arguments)
        self.func = self.__get_input_file(self, args['<func_input>'])
        self.output_file = self.__get_output_file(self, args['--output_file'])
        self.confounds = self.__get_confounds(self, args)
        self.detrend = args['--detrend']
        self.standardize = args['--standardize']
        self.high_pass = float(args['--high_pass'])
        self.low_pass = float(args['--low_pass'])
        self.func.tr = self.__get_tr(self, args['--t_r'])
        self.smooth = self.__get_soothing_settings(self, args)

    def __get_input_file(self, user_func_input):
        '''check that input is readable and either cifti or nifti'''
        func = NibInput(user_func_input)
        if func.type == "cifti":
            if not func.path.endswith(".dtseries.nii"):
                logger.warning('cifti input file should be a .dtseries.nii file {} given'.format(func.path))
        if func.type not "cifti" or "nifti":
            logger.error("ciftify_clean_img only works for nifti or cifti files {} given".format(func.path))
            sys.exit(1)
        return func

    def __get_output_file(self, user_output_arg):
        '''if user argument for output specified, check it. If not, define output'''
        if user_output_arg:
            output_file = user_output_arg
        else:
            output_ext = 'dtseries.nii' if self.func.type == "cifti" else "nii.gz"
            output_file = os.path.join(os.path.dirname(self.func.path),
                                '{}.{}'.format(self.func.base, output_ext))
        ciftify.utils.check_output_writable(output_file)
        return(output_file)

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
        tasks_to_analyze = tasks_user_arg.split(",")
        for colname_arg in args_cols_list:
            if 'colname' not in confounddf.columns:
                logger.error('')


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

    def print_settings(self):

def run_ciftify_clean_img(arguments,tmpdir):

    settings = UserSettings()
    settings.log_settings()

    # check the confounds define the true confounds for nilearn
    confound_signals = mangle_confounds(settings)

    # if input is cifti - we convert to fake nifti
    ## convert to nifti
    if settings.func.type == "cifti":
        clean_input = os.path.join(tempdir,'func_fnifti.nii.gz')
        run(['wb_command','-cifti-convert','-to-nifti',settings.func.path, func_fnifti])
    else: clean_input = settings.func.path

    # the nilearn cleaning step..
    clean_output = nilearn.image.clean_img(clean_input,
                        detrend=settings.detrend,
                        standardize=settings.standardize,
                        confounds=confound_signals,
                        low_pass=settings.low_pass,
                        high_pass=settings.high_pass,
                        t_r=settings.func.tr
    clean_output.to_filename(clean_output_file)

    # if input cifti - convert back to nifti
    if settings.func.type == "cifti":
        run(['wb_command', '-cifti-reduce', settings.func.path, 'MIN', os.path.join(tmpdir, 'template.dscalar.nii')])

        ## convert back
        run(['wb_command','-cifti-convert','-from-nifti',
            clean_output_file,
            os.path.join(tempdir, 'template.dscalar.nii'),
            '{}.dscalar.nii'.format(settings.output_prefix)])

    # if smoothing


    # or nilearn image smooth if nifti input
    nilearn.image.smooth_img(imgs, fwhm)


    # cifti smoothing for cifti inputs
       wb_command -cifti-smoothing
      <cifti> - the input cifti
      <surface-kernel> - the sigma for the gaussian surface smoothing kernel,
         in mm
      <volume-kernel> - the sigma for the gaussian volume smoothing kernel, in
         mm
      <direction> - which dimension to smooth along, ROW or COLUMN
      <cifti-out> - output - the output cifti
      -left-surface <left-surface>
      -right-surface <right-surface>

def update_clean_config(user_args):
    '''merge a json config, if specified into the user_args dict'''
    if user_args['--clean-config']:
        try:
            user_config = json.load(user_args['--clean-config'])
        except:
            logger.critical("Could not load the json config file")
    clean_config = merge(user_args, user_config)
    return(clean_config)

def merge(dict_1, dict_2):
    """Merge two dictionaries.
    Values that evaluate to true take priority over falsy values.
    `dict_1` takes priority over `dict_2`.
    """
    return dict((str(key), dict_1.get(key) or dict_2.get(key))
                for key in set(dict_2) | set(dict_1))

def mangle_confouds(settings):
    '''mangle the confounds according to user settings
    insure that output matches length of func input and NA's are not present..'''




if __name__ == '__main__':
    main()
