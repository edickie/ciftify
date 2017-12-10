# HCP with HPC tutorial code

Presented at the Compute Ontario Summer School July 2017

## Building a ciftify python env in your own SciNet home..

```sh
module load anaconda3
conda create -n ciftify_v1.0.0 python=3.6
source activate ciftify_v1.0.0
conda install pandas
conda install scikit-learn
export LC_ALL=en_US.UTF-8
pip install https://github.com/edickie/ciftify/archive/v1.0.0.tar.gz
pip install qbatch    ## not a part of ciftify..but I use it the examples for submitting ciftify jobs to the queue
pip install nilearn   ##  not necessary for ciftify.. but cool for some later analysis
conda install jupyter ## not necessary, but useful for interactive python 
```

## project a map from neursyth to the surface
```sh
source /scinet/course/ss2017/21_hcpneuro/ciftify_env.sh
rsync -r /scinet/course/ss2017/21_hcpneuro/data/neurosynth_maps $SCRATCH/
ciftify_vol_result HCP_S900_GroupAvg ${SCRATCH}/neurosynth_maps/working_memory_pFgA_z_FDR_0.01.nii.gz \
 ${SCRATCH}/neurosynth_maps/working_memory_pFgA_z_FDR_0.01.dscalar.nii
```

#### We need to know the path to our scratch to do the next bit..

```sh
echo $SCRATCH
```

## from your home terminal - rsync the outputs to your local computer
```sh
rsync -a <USERNAME>@login.scinet.utoronto.ca:<SCRATCH>/neurosynth_maps ~/neurosynth_maps
```

Go [to this page](https://github.com/edickie/ciftify/wiki/wb_view-example) for instructions on building a visualization with this dataset.. 

--------

## submitting recon-all for all subjects

Note: when you download from the public server the nifti file is deep in a directory tree..
abide_nii/Pitt_50002/Pitt_50002/scans/anat/resources/NIfTI/files/mprage.nii
abide_nii/Pitt_50002/Pitt_50002/scans/rest/resources/NIfTI/files/rest.nii

```sh
#load the environment
module load use.experimental freesurfer/6.0.0
module load anaconda3
source activate /scinet/course/ss2017/16_mripython/conda_envs/mripython3.6 ## contains qbatch
module load gnu-parallel/20140622

## get the subjects list from the NIIDIR
NIIDIR=/scinet/course/ss2017/21_hcpneuro/data/abide_nii
SUBJECTS=`cd ${NIIDIR}; ls -1d Pitt_5????`

## make the $SUBJECTS_DIR if it does not already exist
export SUBJECTS_DIR=${SCRATCH}/hcp_course/FS6/
mkdir -p $SUBJECTS_DIR

## add now the magicks happen...pipes the subject list to the fs2hcp command to qbatch...
cd $SUBJECTS_DIR
parallel "echo recon-all -subject {} -i ${NIIDIR}/{}/{}/scans/anat/resources/NIfTI/files/mprage.nii -sd ${SUBJECTS_DIR} -all -parallel" ::: $SUBJECTS | \
  qbatch --walltime 16:00:00 -c 2 -j 2 --ppj 8 -N fs_abide -
```

## using qbatch to run ciftify_recon_all on all subjects
```sh
source /scinet/course/ss2017/21_hcpneuro/ciftify_env.sh
export QBATCH_PPJ=8                   # requested processors per job
export QBATCH_CHUNKSIZE=$QBATCH_PPJ    # commands to run per job
export QBATCH_CORES=$QBATCH_PPJ        # commonds to run in parallel per job
export QBATCH_SYSTEM="pbs"             # queuing system to use ("pbs", "sge", or "slurm")
export QBATCH_NODES=1                  # (PBS-only) nodes to request per job

module unload gnu-parallel
module load gnu-parallel/20140622

export SUBJECTS_DIR=/scinet/course/ss2017/21_hcpneuro/data/freesurfer/
export HCP_DATA=${SCRATCH}/hcp_course/hcp/

mkdir -p ${HCP_DATA}
SUBJECTS=`cd $SUBJECTS_DIR; ls -1d Pitt_5????`
cd $HCP_DATA

parallel "echo ciftify_recon_all {}" ::: $SUBJECTS | \
    qbatch --walltime 1:00:00 -c 4 -j 4 --ppj 8 -N fs62hcp -
```
-------

## running fs2hcp on one subject
```sh
source /scinet/course/ss2017/21_hcpneuro/ciftify_env.sh ## only if this has not been done
ciftify_recon_all --debug \
  --fs-subjects-dir /scinet/course/ss2017/21_hcpneuro/data/freesurfer/ \
  --hcp-data-dir ${SCRATCH}/hcp_course/hcp/ \
  Pitt_50002
```

```sh
#load the environment
module load use.experimental freesurfer/6.0.0
module load anaconda3
source activate /scinet/course/ss2017/16_mripython/conda_envs/mripython3.6 ## contains qbatch
module load gnu-parallel/20140622

## get the subjects list from the NIIDIR
NIIDIR=/scinet/course/ss2017/21_hcpneuro/data/abide_nii
SUBJECTS=`cd ${NIIDIR}; ls -1d Pitt_5????`

## make the $SUBJECTS_DIR if it does not already exist
export SUBJECTS_DIR=${SCRATCH}/hcp_course/FS6/
mkdir -p $SUBJECTS_DIR

## add now the magicks happen...pipes the subject list to the fs2hcp command to qbatch...
cd $SUBJECTS_DIR
parallel "echo recon-all -subject {} -i ${NIIDIR}/{}/{}/scans/anat/resources/NIfTI/files/mprage.nii -sd ${SUBJECTS_DIR} -all -parallel" ::: $SUBJECTS | \
  qbatch --walltime 16:00:00 -c 2 -j 2 --ppj 8 -N fs_abide -
```

-------

## running recon-all qc
```sh
cifti_vis_recon_all snaps MNIfsaverage32k Pitt_50002
cifti_vis_recon_all snaps native Pitt_50002
cifti_vis_recon_all index native
cifti_vis_recon_all index MNIfsaverage32k
```

## submitting a little script to run them all..
```sh
source /scinet/course/ss2017/21_hcpneuro/ciftify_env.sh
module load gnu-parallel/20140622
bash /scinet/course/ss2017/21_hcpneuro/scripts/run_recon_all_qc_scinet.sh
```
--------

## running func2hcp on one subject (Pitt_50002)..
```sh
export HCP_DATA=${SCRATCH}/hcp_course/hcp/
FUNC_DIR=/scinet/course/ss2017/21_hcpneuro/data/native_func
SUBJECT=Pitt_50002

ciftify_subject_fmri --debug\
  --FLIRT-template ${FUNC_DIR}/Pitt_50002/anat_EPI_brain.nii.gz \
  ${FUNC_DIR}/Pitt_50002/PITT_Pitt_50002_01_01_REST_00_rest_filtered.nii.gz \
  Pitt_50002 \
  rest \
  2
```



## running all the subjects in the example dir
```sh
source /scinet/course/ss2017/21_hcpneuro/ciftify_env.sh
export QBATCH_PPJ=8                   # requested processors per job
export QBATCH_CHUNKSIZE=$QBATCH_PPJ    # commands to run per job
export QBATCH_CORES=$QBATCH_PPJ        # commonds to run in parallel per job
export QBATCH_SYSTEM="pbs"             # queuing system to use ("pbs", "sge", or "slurm")
export QBATCH_NODES=1                  # (PBS-only) nodes to request per job

module unload gnu-parallel
module load gnu-parallel/20150822

## note this bit needs gnu-parallel and qbatch...
export HCP_DATA=${SCRATCH}/hcp_course/hcp/
FUNC_DIR=/scinet/course/ss2017/21_hcpneuro/data/native_func

cd ${HCP_DATA}
SUBJECTS=`ls -1d Pitt_5????`

parallel "echo ciftify_subject_fmri --FLIRT-template ${FUNC_DIR}/{}/anat_EPI_brain.nii.gz ${FUNC_DIR}/{}/PITT_{}_01_01_REST_00_rest_filtered.nii.gz {} rest 2" ::: $SUBJECTS |\
    qbatch --walltime 1:00:00 -c 4 -j 4 --ppj 8 -N func2hcp -
```

## running fmri qc
```sh
cifti_vis_fmri snaps rest 2 Pitt_50002
cifti_vis_fmri index
```

## running the little script for all of them..
```sh
source /scinet/course/ss2017/21_hcpneuro/ciftify_env.sh
module load gnu-parallel/20140622
bash /scinet/course/ss2017/21_hcpneuro/scripts/run_fmri_qc_scinet.sh
```
----------------------

# Section 2: doing stuff with cifti files

## prepping for and running palm

### step 1 if to concatenate your data

```sh
### step one..combine them...
wb_shortcuts -cifti-concatenate -map 1 $SCRATCH/hcp_course/dmn_concat.dscalar.nii /scinet/course/ss2017/21_hcpneuro/data/DMN_seedmaps/*_net7.dscalar.nii

## let's also create a mean image while were at it..
wb_command -cifti-reduce \
  $SCRATCH/hcp_course/dmn_concat.dscalar.nii \
  MEAN \
  $SCRATCH/hcp_course/dmn_mean.dscalar.nii  
```

## setting up for your palm run

To threshold our cluster by their size, we need to calculate mean vertexwise surface area maps for our population,
We are going to use the midthickness files from the 32k surfaces that of the same subjects. The steps are

1. calculate the surface area for each subject in your dataset
2. concatenate those subject surface area files together 
3. use "reduce" to average across subjects

```sh
## create the output directory
mkdir $SCRATCH/hcp_course/palm

## calculate the vertex areas for each subject
mkdir $SCRATCH/hcp_course/palm/tmp ## temporary directoy


HCP_DATA=${SCRATCH}/hcp_course/hcp/ #change this shared outputs..

## step one..calculate surface area for each subject
SUBJECTS=`cd $HCP_DATA; ls -1d Pitt_5????`
parallel "wb_command -surface-vertex-areas ${HCP_DATA}/{1}/MNINonLinear/fsaverage_LR32k/{1}.{2}.midthickness.32k_fs_LR.surf.gii ${SCRATCH}/hcp_course/palm/tmp/{1}_{2}_midthick_va.shape.gii" ::: $SUBJECTS ::: 'L' 'R'

## step two..concatenate subjects 
parallel -j 2 "wb_shortcuts -metric-concatenate -map 1  ${SCRATCH}/hcp_course/palm/tmp/concat_{}_midthick_va.func.gii ${SCRATCH}/hcp_course/palm/tmp/*_{}_midthick_va.shape.gii" ::: 'L' 'R'

## calculate the average from the concatenated file
parallel -j 2 "wb_command -metric-reduce ${SCRATCH}/hcp_course/palm/tmp/concat_{}_midthick_va.func.gii   MEAN ${SCRATCH}/hcp_course/palm/mean_{}_midthick_va.func.gii" ::: 'L' 'R'
```

### ok we have are ready for our analysis! Separate -> Run -> Recombine

```
## separate the stuffs..
cp $SCRATCH/hcp_course/dmn_concat.dscalar.nii $SCRATCH/hcp_course/palm/
cd $SCRATCH/hcp_course/palm/
wb_command -cifti-separate dmn_concat.dscalar.nii COLUMN \
  -volume-all dmn_concat_sub.nii \
  -metric CORTEX_LEFT dmn_concat_L.func.gii \
  -metric CORTEX_RIGHT dmn_concat_R.func.gii

## we need to change the encoding on the gifti surfaces
parallel -j 2 "wb_command -gifti-convert BASE64_BINARY dmn_concat_{}.func.gii dmn_concat_{}.func.gii" ::: 'L' 'R'

## ok also we need average surfaces...we'll copy the S900 average of ciftify
cp $CIFTIFY_TEMPLATES/HCP_S900_GroupAvg_v1/S900.*.midthickness_MSMAll.32k_fs_LR.surf.gii  $SCRATCH/hcp_course/palm/

## loading the palm software
# module unload intel
# module load intel/15.0.2 gcc hdf5 octave/3.8.1
module load gcc intel/16.0.0 gnuplot/4.6.1 hdf5 gotoblas octave/3.4.3
export PATH:${PATH}:/scinet/course/ss2017/21_hcpneuro/palm/palm-alpha106/

## run a one sample t-test in palm
palm -i dmn_concat_sub.nii -o results_sub -T -logp -n 10
for hemi in L; do
/scinet/course/ss2017/21_hcpneuro/palm/palm-alpha106/palm \
  -i dmn_concat_${hemi}.func.gii \
  -o results_${hemi}_cort \
  -T -tfce2D \
  -s S900.${hemi}.midthickness_MSMAll.32k_fs_LR.surf.gii mean_${hemi}_midthick_va.func.gii \
  -logp -n 10
done

## recombine a palm output into cifti files
wb_command -cifti-create-dense-from-template \
  dmn_concat.dscalar.nii results_merged_tfce_tstat_fwep_c1.dscalar.nii \
  -volume-all results_sub_tfce_tstat_fwep_c1.nii \
  -metric CORTEX_LEFT results_L_cort_tfce_tstat_fwep_c1.gii \
  -metric CORTEX_RIGHT results_R_cort_tfce_tstat_fwep_c1.gii

```

## Here's some bonus code for adding extra smoothing after the fact  

```sh
#load the epitome enviroment
module unload gnu-parallel
module load gnu-parallel/20140622
source ${HOME}/myscripts/corr/ciftify_env_nodatapaths.sh
module load qbatch

OriginalSmoothingFWHM="2"
FinalSmoothingFWHM="8"

AdditionalSmoothingFWHM=`echo "sqrt(( $FinalSmoothingFWHM ^ 2 ) - ( $OriginalSmoothingFWHM ^ 2 ))" | bc -l`

AdditionalSigma=`echo "$AdditionalSmoothingFWHM / ( 2 * ( sqrt ( 2 * l ( 2 ) ) ) )" | bc -l`

HCP_BASE=${SCRATCH}/CORR/hcp_fs6/

cd ${HCP_BASE}
for site in UPSM Utah LMU_2 NYU_2; do
  HCP_DATA=${HCP_BASE}/${site}
  cd ${HCP_DATA}
  for dtseriesfile in `ls */MNINonLinear/Results/*/*s${OriginalSmoothingFWHM}.dtseries.nii`; do
    subid=$(basename $(dirname $(dirname $(dirname $(dirname $dtseriesfile)))))
    nameoffmri=$(basename $(dirname ${dtseriesfile}))
    echo wb_command -cifti-smoothing\
      ${HCP_DATA}/${dtseriesfile} \
      ${AdditionalSigma} ${AdditionalSigma} COLUMN\
      ${HCP_DATA}/${subid}/MNINonLinear/Results/${nameoffmri}/${nameoffmri}_Atlas_s${FinalSmoothingFWHM}.dtseries.nii \
      -left-surface ${HCP_DATA}/${subid}/MNINonLinear/fsaverage_LR32k/${subid}.L.midthickness.32k_fs_LR.surf.gii \
      -right-surface ${HCP_DATA}/${subid}/MNINonLinear/fsaverage_LR32k/${subid}.R.midthickness.32k_fs_LR.surf.gii
  done | qbatch --walltime 00:30:00 -c 16 -j 16 --ppj 8 -N sm${FinalSmoothingFWHM}${site} -
done
```
