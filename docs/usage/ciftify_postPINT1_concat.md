# ciftify_postPINT1_concat

Will concatenate PINT output summaries into one concatenated file.
Also, calculates all distances from template vertex on standard surface

## Usage 
```
  ciftify_postPINT1_concat [options] <concatenated-pint> <PINT_summary.csv>...

Arguments:
    <concatenated-pint>    The concatenated PINT output to write
    <PINT_summary.csv>     The PINT summary files (repeatable)

Options:
  --surfL SURFACE            The left surface on to measure distances on (see details)
  --surfR SURFACE            The right surface to to measure distances on (see details)
  --no-distance-calc         Will not calculate the distance from the template vertex
  --debug                    Debug logging in Erin's very verbose style
  -n,--dry-run               Dry run
  --help                     Print help


```
## DETAILS 
If surfL and surfR are not given, measurements will be done on the
HCP s900 Average mid-surface.

Written by Erin W Dickie, April 28, 2017
