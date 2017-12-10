# epi_hcpexport

Grabs the processed T1 from HCP folder. These are actually freesurfer outputs that
have already been converted to nifty and reoriented. So they match the outputs of
epi-fsexport. This to use as a standard anatomical this is
slow, but provides the highest-quality registration target. This also allows us
to take advantage of the high-quality freesurfer segmentations for nuisance time
series regression, if desired.

## Usage 
```
    epi_hcpexport [options] <path> <experiment>

Arguements:
     <path>         Path to epitome data directory.
     <experiment>   Name of the epitome experiment.

Options:
      --non-epi-subid          Subject ID in the HCP_DATA does not have experiment and session in it
      --debug                  Debug logging in Erin's very verbose style
      -n,--dry-run             Dry run
      --help                   prints this message.
