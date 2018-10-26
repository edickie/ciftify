# ciftify_postPINT2_sub2sub

Will measure the distance from one subjects rois to all other subjects in mm on specified surfaces.

## Usage
```
  ciftify_postPINT2_sub2sub [options] <concatenated-pint> <output_sub2sub.csv>

Arguments:
    <concatenated-pint>    The concatenated PINT outputs (csv file)
    <output_sub2sub.csv>   The outputfile name

Options:
  --surfL SURFACE        The left surface on to measure distances on (see details)
  --surfR SURFACE        The right surface to to measure distances on (see details)
  --roiidx INT           Measure distances for only this roi (default will loop over all ROIs)
  --pvertex-col COLNAME  The column [default: pvertex] to read the personlized vertices
  --debug                Debug logging in Erin's very verbose style
  -n,--dry-run           Dry run
  --help                 Print help


```
## DETAILS

Requires that all PINT summary files have already been comdined into one
"concatenated" input. by ciftify_postPINT1_concat.py

If surfL and surfR are not given, measurements will be done on the
HCP S1200 Average mid-surface.

Will output a csv with four columns. 'subid1', 'subid2', 'roiidx', 'distance'

Written by Erin W Dickie, May 5, 2017
