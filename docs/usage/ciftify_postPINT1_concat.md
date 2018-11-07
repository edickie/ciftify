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
  --pvertex-col COLNAME      The column [default: pvertex] to read the personlized vertices
  --debug                    Debug logging in Erin's very verbose style
  -n,--dry-run               Dry run
  --help                     Print help


```
## DETAILS 
If surfL and surfR are not given, measurements will be done on the
HCP S1200 Average mid-surface.

In old versions of PINT (2017 and earlier) the pvertex colname was "ivertex".
Use the option "--pvertex-col ivertex" to process these files.

Written by Erin W Dickie, April 28, 2017
