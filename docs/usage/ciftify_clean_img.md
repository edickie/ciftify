# ciftify_clean_img

Will use nilearn.image.clean_img to do filtering and confound regression according
to user settings. Optional smoothing can also be added

## Usage 
```
    ciftify_clean_img [options] <func_input>

Options:
  --output-file=<filename>  Path to output cleaned image
                            (default will append _clean to input)
  --clean-config=<json>     A json file to override/specify all cleaning settings
  --drop-dummy-TRs=<int>    Discard the indicated number of TR's from the begginning before
  --no-cleaning             No filtering, detrending or confound regression steps
  --detrend                 If detrending should be not applied to timeseries
  --standardize             If indicated, returned signals not are set to unit variance.
  --confounds-tsv=<FILE>    The path to a confounds file for confound regression
  --cf-cols=<cols>          The column names from the confounds file to include
  --cf-sq-cols=<cols>       Also include the squares (quadratic) of these columns in the confounds file
  --cf-td-cols=<cols>       Also include the temporal derivative of these columns in the confounds file
  --cf-sqtd-cols=<cols>     Also include the squares of the temporal derivative of these columns in the confounds file
  --low-pass=<Hz>           Lowpass filter cut-offs
  --high-pass=<Hz>          Highpass filter cut-offs
  --tr=<tr>                Indicate the TR for filtering in seconds (default will read from file)
  --smooth-fwhm=<FWHM>      The full width half max of the smoothing kernel if desired
  --left-surface=<gii>      Left surface file (required for smoothing)
  --right-surface=<GII>     Right surface file (required for smoothing)

  -v,--verbose              Verbose logging
  --debug                   Debug logging
  -h, --help                Prints this message


```
## DETAILS :
