# cifti_vis_fmri

Makes pictures for quality assurance of fmri data and pastes them
together into a html pages.

## Usage 
```
    cifti_vis_fmri snaps [options] <NameOffMRI> <subject>
    cifti_vis_fmri index [options]

Arguments:
  <NameOffMRI>         NameOffMRI argument given during ciftify_subject_fmri
  <subject>            Subject ID to process

Options:
  --qcdir PATH             Full path to location of QC directory
  --hcp-data-dir PATH      The directory for HCP subjects (overrides HCP_DATA
                           environment variable)
  --SmoothingFWHM FWHM     SmoothingFWHM argument given during ciftify_subject_fmri
  --smooth-conn FWHM       Add smoothing with this FWHM [default: 8] to connectivity images
                           if no smoothing was during ciftify_subject_fmri
  -v, --verbose            Verbose logging
  --debug                  Debug logging
  --help                   Print help


```
## DETAILS 
Produces visualizations for quality assurance of volume to cortex mapping step
- as well as subcortical resampling. It also produces some

This produces:
 ++ views of the functional data that has been projected to the "cifti space"
 ++ overlays of the functional volume and the pial surface
 ++ seed connectivity from 3 seeds
 ++ this option requires that 2 more arguments are specified
    ++ --NameOffMRI and --SmoothingFWHM -
    ++ these should match what was input in the ciftify_subject_fmri command

The functional to surface QC plots are shown in unsmoothed space.
(i.e. referencing the <NameOffMRI>_Atlas_s0.dtseries.nii file)

Gross patterns of connetivity as more visible with some surface smoothing.
So connectivity are shown either on the smoothed dtseries files indicated by the
"--SmoothingFWHM" option, or they using temporary files smoothed with the kernel
indicated by the ('--smoothed-conn') option (default value 8mm).

Written by Erin W Dickie, Feb 2016
