## ciftify_subject_fmri

  + Will project a nifti functional scan to a cifti .dtseries.nii in that subjects' `ciftify_work_dir` analysis directory
    + The subject's `ciftify_work_dir` analysis directory is created by running `ciftify_recon_all` on that participants freesurfer outputs
  + will do fancy outlier removal to optimize the mapping in the process and (is specified) will smooth the data in cifti space

## Inputs/Outputs

### Inputs

 + **func.nii.gz**: the input (4D) preprossed fMRI data file (in nifti format)
 + **subject**: the subject id (in the hcp folder)
   + corresponds to the name of folder inside the `CIFTIFY_WORKDIR` directory for that subject
   + *Note: The ciftify working directory for this subject should have already been created using ciftify_recon_all!!*
 + **<task_label>**: an output prefix for the fMRI data in the subject's ciftified folder
    + *Note: It is recommended that this label contain all relavant information about the scan other than the subject id (including session/timepoint, type of task, and run number*

### Outputs (default settings):

The main output is a cifti dtseries.nii file ending with the following naming, in the following location within the HCP folder directory

```
<CIFTIFY_WORKDIR>
└── <subject>
    └── MNINonLinear
        └── Results
            ├── <task_label>
                ├── <task_label>_Atlas_s0.dtseries.nii                # the cifti output! (no smoothing)
                ├── <task_label>_Atlas_s<SmoothingFWHM>.dtseries.nii  # the cifti output! (smoothed, if asked for)
                ├── <task_label>.nii.gz                               # the MNI transformed func.nii.gz
                ├── ciftify_subject_fmri.log                          # a useful log
                └── native
                    ├── mat_EPI_to_T1.mat                # the linear transform to the native T1w image
                    └── mat_EPI_to_TAL.mat               # the linear transform to the MNI template
```

## Some examples

#### 1. the default

Running `ciftify_subject_fmri` when you have after defining an `CIFTIFY_WORKDIR` environment variable

```sh
export CIFTIFY_WORKDIR=/path/to/top/ciftify/directory/
ciftify_subject_fmri <func.nii.gz> <Subject> <task_label>
```
#### 2. Without an HCP_DATA environment variable

```sh
ciftify_subject_fmri --ciftify-work-dir /path/to/top/hcp/directory/ <func.nii.gz> <Subject> <task_label>
```

## MNI transform steps

The preferred (now default) usage of ciftify_subject_fmri assumes that the <func.nii.gz> input has already been registered with the T1w anatomical input. This is the case if the data has been preprocessed with FMRIPREP (i.e. "space-T1w_bold_preproc.nii.gz" derivatives). This file is then transformed to MNI space using the FNIRT transform that has been applied to the participants surface _BEFORE_ the surface projection takes place.

If this is not the case. ciftify_subject_fmri can perform an FSL FLIRT transform between the fmri input and the anatomical data in ciftify outputs. _Note: this is not the ideal transform_

This option is indicated with the `--FLIRT-to-T1w` flag:

```sh
## where func_for_registation.nii.gz is the 3D image to use for registration
ciftify_subject_fmri --FLIRT-to-T1w <func.nii.gz> <Subject> <task_label>
```

The following sections concern arguments to define that transform.  

## Specifying settings for the transform to MNI space

`ciftify_subject_fmri` takes an input in "native" space. If specified, it uses FSL's FLIRT to register the image to the "native" space anatomical, and concatenates these transforms registrations already in the `ciftify_work_dir` subjects folder (created by `ciftify_subject_fmri`). The concatenated transforms are applied to the functional data and data is resampled to 2x2x2mm before projection for the HCP surfaces.

You can use the following options to adjust the registration settings.

#### Specify a 3D image to use for registration

There are three possible options for an intermediate that is registered to the T1w image:

1. The first volume of the `<func.nii.gz>` input  (default)
2. The temporal median of the `<func.nii.gz` input

```sh
ciftify_subject_fmri --FLIRT-to-T1w --func-ref median <func.nii.gz> <Subject> <task_label>
```

3. A user specified file

```sh
## where func_for_registation.nii.gz is the 3D image to use for registration
ciftify_subject_fmri --FLIRT-to-T1w --func-ref func_for_registation.nii.gz <func.nii.gz> <Subject> <task_label>
```

#### 3. Skip MNI transformation all together.

If your functional data (<func.nii.gz>) is already in MNI space. You can skip the MNI transform stage.
*Note: this is not recommended for novice users. You want to insure that your MNI transformed functional data is aligned (as well as possible) with the MNI transformed T1w image in the HCP folder (<HCP_DATA>/<subject>/MNINonLinear/T1w.nii.gz)
THIS WILL NOT BE THE CASE IF DIFFERENT MNI TRANSFORM ALGORITHM WAS APPLIED TO THE FUNCTIONAL DATA*

```sh
ciftify_subject_fmri --already-in-MNI <func.nii.gz> <Subject> <task_label>
```

## DEPRECATED - Adding an extra "dilation" step

This option was added as a poor extra correction for bad volume-to-surface mapping.
Hopefully it is no longer needed with the improve fMRI to T1w registration of
version 2.0.

This is an option that I added myself, but is totally optional.  It identifies those areas where the surface projection is poorer and adds extra "dilation" (i.e. smoothing) into those areas.  The "poorer" areas are defined as those where the signal intensity is below a specified percentile rank, in comparison with the intensities across the rest of the surface. This has been applied to the ABIDE sample hcp preprocessing with a specified percentile of 4.

```sh
## run extra smoothing for voxels with an intensity below the 4th percentile
ciftify_subject_fmri --DilateBelowPct 4 <func.nii.gz> <Subject> <task_label>
```
