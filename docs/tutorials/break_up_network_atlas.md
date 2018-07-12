# How to build ROI atlas from a Network Atlas

Some altas are made availble in dlabel format. The labels are for the network names.
The networks are a collection of multiple disparate regions of the brain. We may wish to break these networks up into individual ROIs so that we can extract timeseries from each one. Below is some code for doing so.

## The following example breaks up the Yeo et al (2011) 7networks

Recall that inside the RSN-networks.32k_fs_LR.dlabel.nii packaged with the HCP s1200 Average. There are 4 network atlas maps.

Map   Map Name                                                            
  1   7 RSN Networks (YKS11 - Yeo et al., JNP, 2011)                      
  2   17 RSN Networks (YKS11 - Yeo et al., JNP, 2011)                     
  3   RSN consensus communities (holes filled) - PCN11 (Power_Neuron11)   
  4   RSN consensus communities - PCN11 (Power_Neuron11)

```sh
# Map 1: 7 RSN Networks (YKS11 - Yeo et al., JNP, 2011)
input_network_atlas=${CIFTIFY_TEMPLATES}/HCP_S1200_GroupAvg_v1/RSN-networks.32k_fs_LR.dlabel.nii
map_number=1
output_roi_atlas=Yeo_2011_7networks_ROIs.dlabel.nii
va_ratio=0.1  ## will ignore clusters less than 10% the size of the largest cluster change if needed

## point this to the left and right surfaces
left_surface=${CIFTIFY_TEMPLATES}/HCP_S1200_GroupAvg_v1/S1200.L.midthickness_MSMAll.32k_fs_LR.surf.gii
right_surface=${CIFTIFY_TEMPLATES}/HCP_S1200_GroupAvg_v1/S1200.R.midthickness_MSMAll.32k_fs_LR.surf.gii

# modify below to change the location of intermediate files
## this code builds a directory in /tmp
tmpdir=$(mktemp -d tmp.XXXXXX)

# Step 1: convert all network labels to dscalar ROIs
wb_command -cifti-all-labels-to-rois \
 ${input_network_atlas} \
 ${map_number} \
 ${tmpdir}/roi_maps_${map_number}.dscalar.nii

# Step 2: Run -cifti-find-clusters to split the network ROIS into individual ROIs
wb_command -cifti-find-clusters \
 ${tmpdir}/roi_maps_${map_number}.dscalar.nii \
 0.5 5 0.5 5 COLUMN \
 ${tmpdir}/clustered_${map_number}.dscalar.nii \
 -left-surface ${left_surface} \
 -right-surface ${right_surface} \
 -size-ratio ${va_ratio} ${va_ratio}

# Step 3: reduce to one scalar map using the "MAX" operation
wb_command -cifti-reduce \
 ${tmpdir}/clustered_${map_number}.dscalar.nii \
 MAX \
 ${tmpdir}/MAX_${map_number}.dscalar.nii

# Step 4: convert the dscalar to a dlabel with random colors
wb_command -cifti-label-import \
  ${tmpdir}/MAX_${map_number}.dscalar.nii '' ${output_roi_atlas}

rm -r ${tmpdir}
```
