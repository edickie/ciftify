## ciftify_subject_fmri

  + Will project a nifti functional scan to a cifti .dtseries.nii in that subjects hcp analysis directory
  + The subject's hcp analysis directory is created by runnning fs2hcp on that participants freesurfer output
  + will do fancy outlier removal to optimize the mapping in the process and then smooth the data in cifti space

## Inputs/Outputs

### Inputs

 + **func.nii.gz**: the input (4D) preprossed fMRI data file (in nifti format)
 + **subject**: the subject id (in the hcp folder)
   + corresponds to the name of folder inside the `HCP_DATA` directory for that subject
   + *Note: The HCP folder for this subject should have already been created using fs2hcp.py!!*
 + **NameOffMRI**: an output prefix for the fMRI data in the HCP folder

### Outputs (default settings):

The main output is a cifti dtseries.nii file ending with the following naming, in the following location within the HCP folder directory

```
<HCP_DATA>
└── <subject>
    └── MNINonLinear
        └── Results
            ├── <NameOffMRI>
                ├── <NameOffMRI>_Atlas_s<SmoothingFWHM>.dtseries.nii  # the cifti output!
                ├── <NameOffMRI>.nii.gz                               # the MNI transformed func.nii.gz
                ├── ciftify_subject_fmri.log                          # a useful log
                └── native
                    ├── mat_EPI_to_T1.mat                # the linear transform to the native T1w image
                    └── mat_EPI_to_TAL.mat               # the linear transform to the MNI template
```

## Some examples

#### 1. the default

Running ciftify_subject_fmri when you have after defining an `HCP_DATA` environment variable

```sh
export HCP_DATA=/path/to/top/hcp/directory/
ciftify_subject_fmri <func.nii.gz> <Subject> <NameOffMRI>
```
#### 2. Without an HCP_DATA environment variable

```sh
ciftify_subject_fmri --ciftify-work-dir /path/to/top/hcp/directory/ <func.nii.gz> <Subject> <NameOffMRI>
```

## Adding an extra "dilation" step

This is an option that I added myself, but is totally optional.  It identifies those areas where the surface projection is poorer and adds extra "dilation" (i.e. smoothing) into those areas.  The "poorer" areas are defined as those where the signal intensity is below a specified percentile rank, in comparison with the intensities across the rest of the surface. This has been applied to the ABIDE sample hcp preprocessing with a specified percentile of 4.

```sh
## run extra smoothing for voxels with an intensity below the 4th percentile
ciftify_subject_fmri --DilateBelowPct 4 <func.nii.gz> <Subject> <NameOffMRI>
```

## Specifying settings for the transform to MNI space

fs2hcp.py (by default) takes an input in "native" space. It uses FSL's FLIRT to register the image to the "native" space anatomical, and concatenates these transforms registrations already in the hcp folder (created by fs2hcp.py). The concatenated transforms are applied to the functional data and data is resampled to 2x2x2mm before projection for the HCP surfaces.

You can use the following options to adjust the registration settings.

#### 1. Specify a 3D image to use for registration

In this option is not specified, fs2hcp will use the temporal mean the input 4D fMRI image and use that for registration to the T1w Image. This may not be the ideal case because the preprocessed fMRI image may have less contrast between grey matter/white matter/CSF that earlier steps of your preprocessing pipeline (due to signal rescaling during your preprocessing). You can specific an image for registration using the `--FLIRT-template` option.

```sh
## where func_for_registation.nii.gz is the 3D image to use for registration
ciftify_subject_fmri --FLIRT-template func_for_registation.nii.gz <func.nii.gz> <Subject> <NameOffMRI>
```

#### 2. Change the FLIRT settings

The options `--FLIRT-dof` and `--FLIRT-cost` can be used to change the FLIRT degree of freedom and cost functions

example...run flirt using 6 degrees of freedom (default is 12)
```sh
ciftify_subject_fmri --FLIRT-dof 6 <func.nii.gz> <Subject> <NameOffMRI>
```

#### 3. Skip MNI transformation all together.

If your functional data (<func.nii.gz>) is already in MNI space. You can skip the MNI transform stage.
*Note: this is not recommended for novice users. You want to insure that your MNI transformed functional data is aligned (as well as possible) with the MNI transformed T1w image in the HCP folder (<HCP_DATA>/<subject>/MNINonLinear/T1w.nii.gz)*

```sh
ciftify_subject_fmri --already-in-MNI <func.nii.gz> <Subject> <NameOffMRI>
```
