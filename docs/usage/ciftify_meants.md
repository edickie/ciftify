# ciftify_meants

Produces a csv file mean voxel/vertex time series from a functional file <func>
within a seed mask <seed>.

## Usage
```
    ciftify_meants [options] <func> <seed>

Arguments:
    <func>          functional data can be (nifti or cifti)
    <seed>          seed mask (nifti, cifti or gifti)

Options:
    --outputcsv PATH     Specify the output filename
    --outputlabels PATH  Specity a file to print the ROI row ids to.
    --mask FILE          brainmask (file format should match seed)
    --roi-label INT      Specify the numeric label of the ROI you want a seedmap for
    --weighted           Compute weighted average timeseries from the seed map
    --hemi HEMI          If the seed is a gifti file, specify the hemisphere (R or L) here
    -v,--verbose         Verbose logging
    --debug              Debug logging
    -h, --help           Prints this message


```
## DETAILS :
The default output filename is `<func>_<seed>_meants.csv` inside the same directory
as the <func> file. This can be changed by specifying the full path after
the '--outputcsv' option. The integer labels for the seeds extracted can be printed
to text using the '--outputlabels' option.

If the seed file contains multiple interger values (i.e. an altas). One row will
be written for each integer value. If you only want a timeseries from one roi in
an atlas, you can specify the integer with the --roi-label option.

A weighted avereage can be calculated from a continuous seed if the --weighted
flag is given.

If a mask is given, the intersection of this mask and the seed mask will be taken.

If a nifti seed if given for a cifti functional file, wb_command -cifti separate will
try extract the subcortical cifti data and try to work with that.

Written by Erin W Dickie, March 17, 2016
