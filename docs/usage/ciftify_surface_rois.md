# ciftify_surface_rois

Runs wb_command -surface-geodesic-rois to make rois on left and right surfaces then combines
them into one dscalar file.

## Usage 
```
    ciftify_surface_rois [options] <inputcsv> <radius> <L.surf.gii> <R.surf.gii> <output.dscalar.nii>

Arguments:
    <inputcsv>            csv to read vertex list and hemisphere (and optional labels) from
    <radius>              radius for geodesic rois (mm)
    <L.surf.gii>          Corresponding Left surface
    <R.surf.gii>          Corresponding Right surface file
    <output.dscalar.nii>  output dscalar file

Options:
    --vertex-col COLNAME   Column name [default: vertex] for column with vertices
    --hemi-col COLNAME     Column name [default: hemi] where hemisphere is given as L or R
    --labels-col COLNAME   Values in this column will be multiplied by the roi
    --overlap-logic LOGIC  Overlap logic [default: ALLOW] for wb_command
    --gaussian             Build a gaussian instead of a circular ROI.
    --probmap              Divide the map by the number to inputs so that the sum is meaningful.
    --debug                Debug logging
    -v,--verbose           Verbose logging
    -h, --help             Prints this message


```
## DETAILS 
This reads the vertex ids, from which to center ROIs from a csv file (with a header)
with two required columns ("vertex", and "hemi").

Example:
  vertex, hemi,
  6839, L
  7980, R
  ...

The column (header) names can be indicated with the (--vertex-col, and --hemi-col)
arguments. Additionally, a third column can be given of interger labels to apply to
these ROIs, indicated by the "--labels-col" option.

The  argument to -overlap-logic must be one of ALLOW, CLOSEST, or EXCLUDE.
 ALLOW is the default, and means that ROIs are treated independently and may overlap.
 CLOSEST means that ROIs may not overlap, and that no ROI contains vertices that are closer to a different seed vertex.
 EXCLUDE means that ROIs may not overlap, and that any vertex within range of more than one ROI does not belong to any ROI.

Written by Erin W Dickie, June 3, 2016
