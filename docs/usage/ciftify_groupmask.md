# ciftify_groupmask

Makes a group mask (excluding low signal voxels) for statistical comparisons
from input cifti files.

## Usage
```
  ciftify_groupmask [options] <output.dscalar.nii> <input.dtseries.nii>...

Arguments:
    <output.dscalar.nii>  Output cifti mask
    <input.dtseries.nii>  Input cifti files

Options:
  --percent-thres <Percent>  Lower threshold [default: 5] applied to all files to make mask.
  --cifti-column <column>    Lower threshold [default: 1] applied to all files to make mask.
  --debug                    Debug logging in Erin's very verbose style
  --help                     Print help


```
## DETAILS

Take the specified column from each input file and threshold and binarizes it get
a mask, for each subject, of valid voxels (i.e. voxels of signal above the percentile cut-off).

Then, for each voxel/vertex we take the minimum value across the population.
Therefore our mask contains 1 for each vertex that is valid for all participants and 0 otherwise.

Written by Erin W Dickie, April 15, 2016
