# ciftify_seed_corr

Produces a correlation map of the mean time series within the seed with
every voxel in the functional file.

## Usage
```
    ciftify_seed_corr [options] <func> <seed>

Arguments:
    <func>          functional data (nifti or cifti)
    <seed>          seed mask (nifti, cifti or gifti)

Options:
    --outputname STR   Specify the output filename
    --output-ts        Also output write the from the seed to text
    --roi-label INT    Specify the numeric label of the ROI you want a seedmap for
    --hemi HEMI        If the seed is a gifti file, specify the hemisphere (R or L) here
    --mask FILE        brainmask
    --fisher-z         Apply the fisher-z transform (arctanh) to the correlation map
    --weighted         compute weighted average timeseries from the seed map
    --use-TRs FILE     Only use the TRs listed in the file provided (TR's in file starts with 1)
    -v,--verbose       Verbose logging
    --debug            Debug logging
    -h, --help         Prints this message


```
## DETAILS :
The default output filename is created from the <func> and <seed> filenames,
(i.e. func.dscalar.nii + seed.dscalar.nii --> func_seed.dscalar.nii)
and written to same folder as the <func> input. Use the --outputname
argument to specify a different outputname. The output datatype matches the <func>
input.

The mean timeseries is calculated using ciftify_meants, --roi-label, --hemi,
--mask, and --weighted arguments are passed to it. See ciftify_meants --help for
more info on their usage. The timeseries output (`*_meants.csv`) of this step can be
saved to disk using the --output-ts option.

If a mask is provided with the (--mask) option. (Such as a brainmask) it will be
applied to both the seed and functional file.

The '--use-TRs' argument allows you to calcuate the correlation maps from specific
timepoints (TRs) in the timeseries. This option can be used to exclude outlier
timepoints or to limit the calculation to a subsample of the timecourse
(i.e. only the beggining or end). It expects a text file containing the integer numbers
TRs to keep (where the first TR=1).

Written by Erin W Dickie
