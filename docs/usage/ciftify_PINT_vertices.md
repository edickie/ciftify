# ciftify_PINT_vertices

Beta version of script find PINT (Personal Instrisic Network Topography)

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
  --outputall            Output vertices from each iteration.

  --pre-smooth FWHM      Add smoothing [default: 0] for PINT iterations. See details.
  --sampling-radius MM   Radius [default: 6] in mm of sampling rois
  --search-radius MM     Radius [default: 6] in mm of search rois
  --padding-radius MM    Radius [default: 12] in mm for min distance between roi centers

  --pcorr                Use maximize partial correlation within network (instead of pearson).
  --corr                 Use full correlation instead of partial (default debehviour is --pcorr)

  -v,--verbose           Verbose logging
  --debug                Debug logging in Erin's very verbose style
  -h,--help              Print help


```
## DETAILS :
The pre-smooth option will add smoothing in order to make larger resting state gradients
more visible in noisy data. Final extration of the timeseries use the original (un-smoothed)
functional input.

Written by Erin W Dickie, April 2016
