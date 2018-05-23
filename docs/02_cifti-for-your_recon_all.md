# **cifti**-**f**or-**y**our **recon_all** outputs

## ciftify_recon_all

ciftify_recon_all will convert any freesurfer recon-all output folder into an HCP style folder structure.

This is adapted from sections of Human Connectome Projects Minimal Processing Pipeline described [in this article](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3720813/) and [available in this github repo](https://github.com/Washington-University/Pipelines/releases).

The Minimal Processing Pipeline scripts require that a minimum number of HCP standard acquisitions (i.e. T1w, High Resolution T2w, etc) are present. ciftify_recon_all has been adapted from these scripts to convert ANY freesurfer output into an HCP like folder structure.  It also output less intermediate (unnecessary) files in the process and does standard logging to an ciftify_recon_all.log file.

### Usage

```
Usage:
  ciftify_recon_all [options] <subject>

Arguments:
    <subject>               The Subject ID in the HCP data folder

Options:
  --hcp-data-dir PATH         Path to the HCP_DATA directory (overides the HCP_DATA environment variable)
  --fs-subjects-dir PATH      Path to the freesurfer SUBJECTS_DIR directory (overides the SUBJECTS_DIR environment variable)
  --resample-LowRestoNative   Resample the 32k Meshes to Native Space (creates additional output files)
  -v,--verbose                Verbose logging
  --debug                     Debug logging
  -h,--help                   Print help
```

##### Required Inputs

Three arguments are required for ciftify_recon_all to run:
+ The freesurfer `SUBJECTS_DIR` is the top directory structure holding all freesurfer outputs for a sample. It can be defined either by setting the `$SUBJECTS_DIR` environment variable or using optional `--fs-subjects-dir` argument
+ The `CIFTIFY_WORKDIR` directory is top directory holding the HCP outputs. It can be defined either by setting the `$CIFTIFY_WORKDIR` environment variable or using the optional `--ciftify-work-dir` argument
   + Note: in previous versions, this was referred to as `HCP_DATA` or `--hcp-data-dir`
+ The subject id of the participant to process. I needs to match the folder name for that subject within the freesurfer `SUBJECTS_DIR`.

### Examples

Run ciftify_recon_all after defining environment variables

```sh
export SUBJECTS_DIR=/path/to/freesurfer/outputs
export HCP_DATA=/path/for/hcp/outputs            ## will be created by fs2hcp if is does not exist
ciftify_recon_all Subject001
```

Running the same command without first defining environment variables
```sh
ciftify_recon_all --fs-subjects-dir /path/to/freesurfer/outputs --hcp-data-dir /path/for/hcp/outputs Subject001
```

### Surface Registration Options

There are currently too methods for between subject surface-based registration available with ciftify.

The default option (`MSMSulc`) matches the behaviour of the currently release of the HCPPipelines.

There are two things that users should be aware of when using this method:

1. Its a very resource intensive step (it takes hours to run on a 12GB RAM machine)
2. It requires the newest version of the MSM software (i.e. a version newer that available with FSL)
    + visit [this link]() for the download and install instructions
    + this version is installed into the ciftify docker container
    + note: this software is licensed for acedemic use

An alternative is to instead use the freesurfer (fsaverage) surface registration, by using the `--surf-reg` flag with the FS input:

```sh
ciftify_recon_all --surf-reg FS --fs-subjects-dir /path/to/freesurfer/outputs --hcp-data-dir /path/for/hcp/outputs Subject001
```

### Understanding the Outputs

```
0025362s1r1
├── ciftify_recon_all.log
├── MNINonLinear
│   ├── 0025362s1r1.164k_fs_LR.wb.spec
│   ├── 0025362s1r1.aparc.164k_fs_LR.dlabel.nii
│   ├── 0025362s1r1.aparc.a2009s.164k_fs_LR.dlabel.nii
│   ├── 0025362s1r1.aparc.DKTatlas.164k_fs_LR.dlabel.nii
│   ├── 0025362s1r1.ArealDistortion_FS.164k_fs_LR.dscalar.nii
│   ├── 0025362s1r1.BA_exvivo.164k_fs_LR.dlabel.nii
│   ├── 0025362s1r1.curvature.164k_fs_LR.dscalar.nii
│   ├── 0025362s1r1.L.atlasroi.164k_fs_LR.shape.gii -> ../../zz_templates/L.atlasroi.164k_fs_LR.shape.gii
│   ├── 0025362s1r1.L.flat.164k_fs_LR.surf.gii -> ../../zz_templates/colin.cerebral.L.flat.164k_fs_LR.surf.gii
│   ├── 0025362s1r1.L.inflated.164k_fs_LR.surf.gii
│   ├── 0025362s1r1.L.midthickness.164k_fs_LR.surf.gii
│   ├── 0025362s1r1.L.pial.164k_fs_LR.surf.gii
│   ├── 0025362s1r1.L.sphere.164k_fs_LR.surf.gii -> ../../zz_templates/fsaverage.L_LR.spherical_std.164k_fs_LR.surf.gii
│   ├── 0025362s1r1.L.very_inflated.164k_fs_LR.surf.gii
│   ├── 0025362s1r1.L.white.164k_fs_LR.surf.gii
│   ├── 0025362s1r1.R.atlasroi.164k_fs_LR.shape.gii -> ../../zz_templates/R.atlasroi.164k_fs_LR.shape.gii
│   ├── 0025362s1r1.R.flat.164k_fs_LR.surf.gii -> ../../zz_templates/colin.cerebral.R.flat.164k_fs_LR.surf.gii
│   ├── 0025362s1r1.R.inflated.164k_fs_LR.surf.gii
│   ├── 0025362s1r1.R.midthickness.164k_fs_LR.surf.gii
│   ├── 0025362s1r1.R.pial.164k_fs_LR.surf.gii
│   ├── 0025362s1r1.R.sphere.164k_fs_LR.surf.gii -> ../../zz_templates/fsaverage.R_LR.spherical_std.164k_fs_LR.surf.gii
│   ├── 0025362s1r1.R.very_inflated.164k_fs_LR.surf.gii
│   ├── 0025362s1r1.R.white.164k_fs_LR.surf.gii
│   ├── 0025362s1r1.sulc.164k_fs_LR.dscalar.nii
│   ├── 0025362s1r1.thickness.164k_fs_LR.dscalar.nii
│   ├── aparc.a2009s+aseg.nii.gz
│   ├── aparc+aseg.nii.gz
│   ├── brainmask_fs.nii.gz
│   ├── fsaverage_LR32k
│   │   ├── 0025362s1r1.32k_fs_LR.wb.spec
│   │   ├── 0025362s1r1.aparc.32k_fs_LR.dlabel.nii
│   │   ├── 0025362s1r1.aparc.a2009s.32k_fs_LR.dlabel.nii
│   │   ├── 0025362s1r1.aparc.DKTatlas.32k_fs_LR.dlabel.nii
│   │   ├── 0025362s1r1.ArealDistortion_FS.32k_fs_LR.dscalar.nii
│   │   ├── 0025362s1r1.BA_exvivo.32k_fs_LR.dlabel.nii
│   │   ├── 0025362s1r1.curvature.32k_fs_LR.dscalar.nii
│   │   ├── 0025362s1r1.L.atlasroi.32k_fs_LR.shape.gii -> ../../../zz_templates/L.atlasroi.32k_fs_LR.shape.gii
│   │   ├── 0025362s1r1.L.flat.32k_fs_LR.surf.gii -> ../../../zz_templates/colin.cerebral.L.flat.32k_fs_LR.surf.gii
│   │   ├── 0025362s1r1.L.inflated.32k_fs_LR.surf.gii
│   │   ├── 0025362s1r1.L.midthickness.32k_fs_LR.surf.gii
│   │   ├── 0025362s1r1.L.pial.32k_fs_LR.surf.gii
│   │   ├── 0025362s1r1.L.sphere.32k_fs_LR.surf.gii -> ../../../zz_templates/L.sphere.32k_fs_LR.surf.gii
│   │   ├── 0025362s1r1.L.very_inflated.32k_fs_LR.surf.gii
│   │   ├── 0025362s1r1.L.white.32k_fs_LR.surf.gii
│   │   ├── 0025362s1r1.R.atlasroi.32k_fs_LR.shape.gii -> ../../../zz_templates/R.atlasroi.32k_fs_LR.shape.gii
│   │   ├── 0025362s1r1.R.flat.32k_fs_LR.surf.gii -> ../../../zz_templates/colin.cerebral.R.flat.32k_fs_LR.surf.gii
│   │   ├── 0025362s1r1.R.inflated.32k_fs_LR.surf.gii
│   │   ├── 0025362s1r1.R.midthickness.32k_fs_LR.surf.gii
│   │   ├── 0025362s1r1.R.pial.32k_fs_LR.surf.gii
│   │   ├── 0025362s1r1.R.sphere.32k_fs_LR.surf.gii -> ../../../zz_templates/R.sphere.32k_fs_LR.surf.gii
│   │   ├── 0025362s1r1.R.very_inflated.32k_fs_LR.surf.gii
│   │   ├── 0025362s1r1.R.white.32k_fs_LR.surf.gii
│   │   ├── 0025362s1r1.sulc.32k_fs_LR.dscalar.nii
│   │   └── 0025362s1r1.thickness.32k_fs_LR.dscalar.nii
│   ├── Native
│   │   ├── 0025362s1r1.aparc.a2009s.native.dlabel.nii
│   │   ├── 0025362s1r1.aparc.DKTatlas.native.dlabel.nii
│   │   ├── 0025362s1r1.aparc.native.dlabel.nii
│   │   ├── 0025362s1r1.ArealDistortion_FS.native.dscalar.nii
│   │   ├── 0025362s1r1.BA_exvivo.native.dlabel.nii
│   │   ├── 0025362s1r1.curvature.native.dscalar.nii
│   │   ├── 0025362s1r1.L.inflated.native.surf.gii
│   │   ├── 0025362s1r1.L.midthickness.native.surf.gii
│   │   ├── 0025362s1r1.L.pial.native.surf.gii
│   │   ├── 0025362s1r1.L.roi.native.shape.gii
│   │   ├── 0025362s1r1.L.sphere.native.surf.gii
│   │   ├── 0025362s1r1.L.sphere.reg.native.surf.gii
│   │   ├── 0025362s1r1.L.sphere.reg.reg_LR.native.surf.gii
│   │   ├── 0025362s1r1.L.very_inflated.native.surf.gii
│   │   ├── 0025362s1r1.L.white.native.surf.gii
│   │   ├── 0025362s1r1.native.wb.spec
│   │   ├── 0025362s1r1.R.inflated.native.surf.gii
│   │   ├── 0025362s1r1.R.midthickness.native.surf.gii
│   │   ├── 0025362s1r1.R.pial.native.surf.gii
│   │   ├── 0025362s1r1.R.roi.native.shape.gii
│   │   ├── 0025362s1r1.R.sphere.native.surf.gii
│   │   ├── 0025362s1r1.R.sphere.reg.native.surf.gii
│   │   ├── 0025362s1r1.R.sphere.reg.reg_LR.native.surf.gii
│   │   ├── 0025362s1r1.R.very_inflated.native.surf.gii
│   │   ├── 0025362s1r1.R.white.native.surf.gii
│   │   ├── 0025362s1r1.sulc.native.dscalar.nii
│   │   └── 0025362s1r1.thickness.native.dscalar.nii
│   ├── Results
│   ├── ROIs
│   │   ├── Atlas_ROIs.2.nii.gz -> ../../../zz_templates/Atlas_ROIs.2.nii.gz
│   │   └── ROIs.2.nii.gz
│   ├── T1w.nii.gz
│   ├── wmparc.nii.gz
│   └── xfms
│       ├── NonlinearReg_fromlinear.log
│       ├── Standard2T1w_warp_noaffine.nii.gz
│       ├── T1w2StandardLinear.mat
│       └── T1w2Standard_warp_noaffine.nii.gz
└── T1w
    ├── aparc.a2009s+aseg.nii.gz
    ├── aparc+aseg.nii.gz
    ├── brainmask_fs.nii.gz
    ├── Native
    │   ├── 0025362s1r1.L.inflated.native.surf.gii
    │   ├── 0025362s1r1.L.midthickness.native.surf.gii
    │   ├── 0025362s1r1.L.pial.native.surf.gii
    │   ├── 0025362s1r1.L.very_inflated.native.surf.gii
    │   ├── 0025362s1r1.L.white.native.surf.gii
    │   ├── 0025362s1r1.native.wb.spec
    │   ├── 0025362s1r1.R.inflated.native.surf.gii
    │   ├── 0025362s1r1.R.midthickness.native.surf.gii
    │   ├── 0025362s1r1.R.pial.native.surf.gii
    │   ├── 0025362s1r1.R.very_inflated.native.surf.gii
    │   └── 0025362s1r1.R.white.native.surf.gii
    ├── T1w_brain.nii.gz
    ├── T1w.nii.gz
    └── wmparc.nii.gz

8 directories, 106 files
```

## cifti_vis_recon_all

### Prerequisites

Before building recon-all qc pages you will need to:

1. Run Freesurfer's recon-all on your dataset
2. Run ciftify_recon_all on your dataset to convert your data to cifti format.

### Running cifti_vis_recon-all

cifti_vis_recon_all is run in two steps:
1. the *snaps* step is used to create qc images for one subject
   + this step needs to be repeated for each subject in your dataset
2. the *index* step is used to write summary html pages where all subjects from your dataset can be viewed together
   + this step is very fast, but requires the outputs of the first "snaps" step.

#### Generating snaps for one subject

Assuming your `HCP_DATA` folder contrains outputs of ciftify_recon_all are organised like this.

```
/path/to/my/HCP_DATA
├── subject_01
├── subject_02
...
└── subject_n
```
We would run generate QC outputs for `subject_01`, after setting the HCP_DATA environment variable using the following command.

```sh
export HCP_DATA=/path/to/my/HCP_DATA   ## set the HCP_DATA environment variable
cifti_vis_recon_all snaps subject_01
```

#### To run all subjects in the dataset and then build the index..

```
export HCP_DATA=/path/to/my/HCP_DATA   ## set the HCP_DATA environment variable

## make a subject list
subject_list=`cd ${HCP_DATA}; ls -1d subject*`

## make snaps for all subjects
for subject in ${subject_list};
  do
  cifti_vis_recon_all snaps ${subject}
done

## make the index pages
cifti_vis_recon_all index
```

#### Optional Arguments

Alternatively, the `HCP_DATA` directory location can be specified as an optional argument. This will override the `$HCP_DATA` environment variable.

```sh
cifti_vis_recon_all snaps --hcp-data-dir /path/to/my/HCP_DATA subject_01
```

By default, the qc visualizations will be written to a folder called `qc_recon_all` inside the `HCP_DATA` directory. Alternatively, the location of qc outputs can be set using the `--qcdir` option

```sh
cifti_vis_recon_all snaps MNIfsaverage32k --qcdir /path/to/my/qc_outputs subject_01
```


#### A little fancier, running on a cluster using gnu-parallel

cifti_vis_recon_all is pretty input-output intensive. Which tends to make everything slower on a large cluster. (and cluster administrators very mad at you).  So this script first write the files to "ramdisk" (super fast local storage, at /dev/shm) then tars up all the qc images before writing them to disk.

```sh
#!/bin/bash
#PBS -l nodes=1:ppn=8,walltime=5:00:00
#PBS -j oe

#load the enviroment
module load gnu-parallel/20140622             # needed to run the "parallel" command below
source ${HOME}/myscripts/abide/ciftify_env.sh # loading the ciftify environment
module load ImageMagick                       # required by QC page generator

export SUBJECTS_DIR=${SCRATCH}/myproject/FSout/
export HCP_DATA=${SCRATCH}/myproject/hcp/

## get the subjects list from the HCP_DATA list
cd ${HCP_DATA}
subjects=`ls -1d subject*` ## EDIT THIS LINE with pattern for your subject ids

## Add a projectname to the output directory
projectname="myprojectname" ## EDIT THIS LINE with your projectname

###############
## this part is bash magik for creating a tmp directory that get's deleted if/when the job dies

tmpdir=$(mktemp --tmpdir=/dev/shm -d tmp.XXXXXX)

function cleanup_ramdisk {
    echo -n "Cleaning up ramdisk directory ${tmpdir} on "
    date
    rm -rf ${tmpdir}
    echo -n "done at "
    date
}

#trap the termination signal, and call the function 'trap_term' when
# that happens, so results may be saved.
trap cleanup_ramdisk EXIT

####################

# This part write all the QC snaps and html pages to tmp directory...than tars is all up and copies it to the file system

## run the QC - note it's a little faster because we are running the snaps generation in parallel across subjects
qcdir="qc_${projectname}_recon_all"
parallel -j 4 "cifti_vis_recon_all snaps --qcdir ${tmpdir}/${qcdir} {}" ::: $subjects
cifti_vis_recon_all index --qcdir ${tmpdir}/${qcdir}

## move the data from the ramdisk back to HCP_DATA
cd ${tmpdir}
tar -cf ${HCP_DATA}/${qcdir}.tar ${qcdir}/
rm -r ${tmpdir}/${qcdir}
cd ${HCP_DATA}

```
## Looking at cifit_vis_recon_all outputs

We will start with the outputs from "MNIfsaverage32k" qcmode. In these views, the surfaces have been transformed into MNI space using FSL fnirt.  

This is actually quite useful for visual QC because:
1. All subjects are oriented the same way - which makes outliers easier to spot.
2. Some errors in tissue classification will get exaggerated by the MNI transform - making them easier to spot here.  

#### My QC workflow

If the qc pages are on your local system you can view them using your browser

```sh
firefox /path/to/hcp/data/qc_MNIfsaverage32k/index.html
```
My QC workflow is:
1. Scroll through the [CombineView Index Pages](#the-combined-qc-view)
   + if any image looks odd, click on that subject to view the [single subject view](#single-subject-view) and investigate further
2. Scroll through the [Sagittal Surface Outline View](#the-sagittal-surface-outline-view)
   + if any image looks odd, click on that subject to view the [single subject view](#single-subject-view) and investigate further

Throughout this process. Make notes about any poor scans in a separate document.

### Single Subject View

The single subject views shows all snapshots taken from this subject in one page. The views are (from top to bottom).

1. **aparc**: A surface reconstruction (medial and lateral views)
2. **SurfOutlineAxial**: Axial anatomical slices with the surfaces shown (white surface - blue, pial surface - lime green)
3. **SurfOutlineCoronal**: Coronal anatomical slices with the surfaces shown  (white surface - blue, pial surface - lime green)
4. **SurfOutlineSagittal**:  Sagittal anatomical slices with the surfaces shown (white surface - blue, pial surface - lime green)
5. **CombinedView**: the surface reconstruction on top of the anatomical. Lateral (L and R) and Dorsal and Vental views.
![singlesubjectview](https://github.com/edickie/docpics/blob/master/recon-all-qc/SingleSubject_demoview.png?raw=true)

### The combined QC view

This index page shows the surface reconstruction of the brain (labeled using the aparc atlas) with the T1w Image. You see the brain from the 1) Left Side, 2) Right Side 3) Top View 4) Bottom View

Every line is a separate subject. The freesurfer subject ID is printed below the image. To look at any subject in more detail - click on the image.

![CombineView](https://github.com/edickie/docpics/blob/master/recon-all-qc/CombinedView_demo.png)

In the image above all subjects pass visual QC.

### Examples of QC fails

If recon-all did not finish. The surface files might not exist... so they are not plotted.  
![didnotfinish](https://github.com/edickie/docpics/blob/master/recon-all-qc/combineview_didnotfinish.png?raw=true)

A completely black image may be seen is recon-all failed very early in the pipeline..
![black](https://github.com/edickie/docpics/blob/master/recon-all-qc/aparc.png?raw=true)
For a very poor quality anatomical. The surface will look shrivelled up.
![really bad](https://github.com/edickie/docpics/blob/master/recon-all-qc/combined_kindask.png?raw=true)

Sometimes when brain masking fails during recon-all in a part of the brain, than area of the brain will be stretched strangely in the underlying image. (image to come)

If the gray matter is missing part of the occipital lobe, the back of the brain will look split apart on the bottom view (far right)
![bad occipital](https://github.com/edickie/docpics/blob/master/recon-all-qc/combined_backbad.png?raw=true)


#### The Sagittal Surface Outline View

The is the second place to look. Like the Combined View - index page, here we see one line per subject, with the the Freesurfer subject id printed below. Also, like all index pages, you can go to the single subject view by clicking on any subject's image.

![SagView](https://github.com/edickie/docpics/blob/master/recon-all-qc/SagOutline_demoView.png?raw=true)

In the above image, all of the participants pass visual QC.

##### Examples of QC fails

A key place to look are the two temporal poles. Surface reconstruction in these area can fail.
![temporalpole](https://github.com/edickie/docpics/blob/master/recon-all-qc/largetemporalpoleloss.png?raw=true)

![jaggedsaggitall](https://github.com/edickie/docpics/blob/master/recon-all-qc/temporalpole_orjaggedfrontal.png?raw=true)
For this participant, the surface reconstruction in the aparc view looks jagged (especially in the orbital frontal cortex)
![jaggedfrontal](https://github.com/edickie/docpics/blob/master/recon-all-qc/jagged_frontal_pole.png?raw=true)

##### Examples of QC - not ideal

The temporal pole is not ideal.

![righttemporalpole](https://github.com/edickie/docpics/blob/master/recon-all-qc/anothertemporalpole.png?raw=true)
![temporalpole](https://github.com/edickie/docpics/blob/master/recon-all-qc/maybe_temporal_pole_off.png?raw=true)
![sligthoff](https://github.com/edickie/docpics/blob/master/recon-all-qc/temporalpole_slightoff.png?raw=true)
