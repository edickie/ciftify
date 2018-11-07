# ciftify_peaktable

Takes a cifti map ('dscalar.nii') and outputs a csv of results

## Usage
```
    ciftify_peaktable [options] <func.dscalar.nii>

Arguments:
    <func.dscalar.nii>    Input map.

Options:
    --min-threshold MIN    the largest value [default: -2.85] to consider for being a minimum
    --max-threshold MAX    the smallest value [default: 2.85] to consider for being a maximum
    --area-threshold MIN   threshold [default: 20] for surface cluster area, in mm^2
    --surface-distance MM  minimum distance in mm [default: 20] between extrema of the same type.
    --volume-distance MM   minimum distance in mm [default: 20] between extrema of the same type.

    --outputbase prefix    Output prefix (with path) to output documents
    --no-cluster-dlabel    Do not output a dlabel map of the clusters

    --left-surface GII     Left surface file (default is HCP S1200 Group Average)
    --right-surface GII    Right surface file (default is HCP S1200 Group Average)
    --left-surf-area GII   Left surface vertex areas file (default is HCP S1200 Group Average)
    --right-surf-area GII  Right surface vertex areas file (default is HCP S1200 Group Average)

    --debug                Debug logging
    -n,--dry-run           Dry run
    -h, --help             Prints this message


```
## DETAILS
Note: at the moment generates separate outputs for surface.
Uses -cifti-separate in combination with FSL's clusterize to get information from
the subcortical space.

Ouptputs a results csv with several headings:
  + clusterID: Integer for the cluster this peak is from (corresponds to dlabel.nii)
  + hemisphere: Hemisphere the peak is in (L or R)
  + vertex: The vertex id
  + x,y,z: The nearest x,y,z coordinates to the vertex
  + value: The intensity (value) at that vertex in the func.dscalar.nii
  + area: The surface area of the cluster (i.e. clusterID)
  + DKT: The label from the freesurfer anatomical atlas (aparc) at the vertex
  + DKT_overlap: The proportion of the cluster (clusterID) that overlaps with the DKT atlas label
  + Yeo7: The label from the Yeo et al 2011 7 network atlas at this peak vertex
  + Yeo7_overlap: The proportion of the cluster (clusterID) that overlaps with this Yeo7 network label
  + MMP: The label from the Glasser et al (2016) Multi-Modal Parcellation
  + MMP_overlap: The proportion of the cluster (clusterID) that overlaps with the MMP atlas label

If no surfaces of surface area files are given. The midthickness surfaces from
the HCP S1200 Group Mean will be used, as well as it's vertex-wise
surface area infomation.

Default name for the output csv taken from the input file.
i.e. func.dscalar.nii --> func_peaks.csv

Unless the '--no-cluster-dlabel' flag is given, a map of the clusters with be
be written to the same folder as the outputcsv to aid in visualication of the results.
This dlable map with have a name ending in `_clust.dlabel.nii`.
(i.e. func_peaks.csv & func_clust.dlabel.nii)

Atlas References:
Yeo, BT. et al. 2011. 'The Organization of the Human Cerebral Cortex
Estimated by Intrinsic Functional Connectivity.' Journal of Neurophysiology
106 (3): 1125-65.

Desikan, RS.et al. 2006. 'An Automated Labeling System for Subdividing the
Human Cerebral Cortex on MRI Scans into Gyral Based Regions of Interest.'
NeuroImage 31 (3): 968-80.

Glasser, MF. et al. 2016. 'A Multi-Modal Parcellation of Human Cerebral Cortex.'
Nature 536 (7615): 171-78.

Written by Erin W Dickie, Last updated August 27, 2017
