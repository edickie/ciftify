# ciftify_PINT_vertices

Beta version of script find PINT (Personal Instrisic Network Topolography)

## Usage 
```
  ciftify_PINT_vertices [options] <func.dtseries.nii> <left-surface.gii> <right-surface.gii> <input-vertices.csv> <outputprefix>

Arguments:
    <func.dtseries.nii>    Paths to directory source image
    <left-surface.gii>     Path to template for the ROIs of network regions
    <right-surface.gii>    Surface file .surf.gii to read coordinates from
    <input-vertices.csv>   Table of template vertices from which to Start
    <outputprefix>         Output csv file

Options:
  --pcorr                Use maximize partial correlation within network
                         (instead of pearson).
  --outputall            Output vertices from each iteration.
  --sampling-radius MM   Radius [default: 6] in mm of sampling rois
  --search-radius MM     Radius [default: 6] in mm of search rois
  --padding-radius MM    Radius [default: 12] in mm for min distance between roi centers
  --roi-limits ROIFILE   To limit rois, input a 4D dscalar file with one roi per roiidx
  -v,--verbose           Verbose logging
  --debug                Debug logging in Erin's very verbose style
  -h,--help              Print help


```
## DETAILS 
TBA

Written by Erin W Dickie, April 2016
