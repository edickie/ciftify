#!/bin/bash

# Makes an eroded white matter mask and an eroded ventricle mask.
# SESS should point to the MNINonLinear folder for a subject
# Expected inputs:
#   In MNINonLinear folder: aparc+aseg.nii.gz and brainmask_fs.nii.gz

if [ ! $# -eq 2 ]
then
  echo "Creates an eroded white matter mask and eroded ventricle mask for a subject"
  echo "Usage: "
  echo "      $(basename $0) <MNINonLinear> <output_path>"
  echo "Arguments:"
  echo "      <MNINonLinear>      The full path to one subject's MNINonLinear"
  echo "                          folder (from the HCP pipeline outputs)."
  echo "      <output_path>       Full path to the location to deposit all outputs"
  exit 1
fi

SESS=$1
OUT=$2

mask=brainmask_fs.nii.gz

# eroded white matter mask
if [ ! -f ${OUT}/anat_wm_ero.nii.gz ]; then
    # Grab the relevant segments
    wb_command \
        -volume-math "x == 2 || \
                      x == 7 || \
                      x == 41 || \
                      x == 46 || \
                      x == 251 || \
                      x == 252 || \
                      x == 253 || \
                      x == 254 || \
                      x == 255" \
        ${OUT}/anat_wm.nii.gz \
        -var x ${SESS}/aparc+aseg.nii.gz > /dev/null 2>&1

    # Erode the mask a little bit
    wb_command -volume-erode \
        ${OUT}/anat_wm.nii.gz 0.5 \
        ${OUT}/anat_wm_ero.nii.gz

    # Zero any voxels in anat_wm_ero that dont overlap with brainmask_fs
    wb_command -volume-math \
        "a*b" ${OUT}/anat_wm_ero.nii.gz \
        -var a ${OUT}/anat_wm_ero.nii.gz \
        -var b ${SESS}/${mask} > /dev/null 2>&1
fi

# eroded ventricle mask
if [ ! -f ${OUT}/anat_vent_ero.nii.gz ]; then
    wb_command \
        -volume-math "x == 4 || \
                      x == 43" \
        ${OUT}/anat_vent.nii.gz \
        -var x ${SESS}/aparc+aseg.nii.gz > /dev/null 2>&1

    wb_command \
        -volume-math "x == 10 || \
                      x == 11 || \
                      x == 26 || \
                      x == 49 || \
                      x == 50 || \
                      x == 58" \
        ${OUT}/anat_tmp_nonvent.nii.gz \
        -var x ${SESS}/aparc+aseg.nii.gz > /dev/null 2>&1

    wb_command -volume-dilate \
        ${OUT}/anat_tmp_nonvent.nii.gz 0.5 NEAREST \
        ${OUT}/anat_tmp_nonvent_dia.nii.gz

    wb_command \
        -volume-math "a - a*b*c" \
        ${OUT}/anat_vent_ero.nii.gz \
        -var a ${OUT}/anat_vent.nii.gz \
        -var b ${OUT}/anat_tmp_nonvent_dia.nii.gz \
        -var c ${SESS}/${mask} > /dev/null 2>&1
fi
