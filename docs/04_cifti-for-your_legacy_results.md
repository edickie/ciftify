# ciftify your legacy results

## see [ **ciftify_vol_result Usage** ]( usage/ciftify_vol_result.md)

## Examples

### Project a map from neursyth to the HCP S1200 Average Surface

We could use any map in this case (even one of your own data). For this example we will download the "working memory" term map from [ neurosynth.org ](neurosynth.org). This map represents the results of an automated "term-based" meta-analysis of working memory.

```sh
ciftify_vol_result \
 HCP_S1200_GroupAvg \
 working_memory_pFgA_z_FDR_0.01.nii.gz \ neurosynth_maps/working_memory_pFgA_z_FDR_0.01.dscalar.nii
```

### The result of this projection is plotted below

![Pretty Figure](https://github.com/edickie/docpics/blob/master/wb_view_demo/final_figure.png?raw=true)

**Check out [ this tutorial ](tutorials/wb_view-example.md) for instructions for building this figure using connectome-workbench.**

Note in this figure that the location of the HCP S1200 Average Group Surfaces may not overlap with the locations of cortical gray matter in many subjects...We will come back to this.

If we want a better handle on an individual participant's anatomy, we should project our data to individual subjects.  This is how ciftify_vol_result is intended to be used.

### Project an MNI space atlas map to an individual subject's surface

Let's say we have an atlas or mask in MNI space and we want to understand how this mask overlaps with the cortical areas of a set of individual subjects. For each subject, we can project the atlas to their own anatomy.

To do so, we need to run `ciftify_vol_result` using the `--integer-labels` option. This indicates that the surface projection should use that "ENCLOSING VOXEL" method.

Also note that the basepath to the data needs to be indicated. This can either be set using the  `HCP_DATA` enviroment variable, or using the `--ciftify-work-dir` option. The `--hcp-data-dir` option has been deprecated.

```sh
export CIFTIFY_WORKDIR=/path/to/ciftified/data   #set the path to the hcp data
ciftify_vol_result --integer-labels subject_id atlas.nii.gz atlas.dscalar.nii
```

or (with `CIFTIFY_WORKDIR` set within the command)

```sh
ciftify_vol_result --integer-labels \
  --ciftify-work-dir /path/to/ciftified/data \
  subject_id my_atlas.nii.gz my_atlas.dscalar.nii
```

For example (using sub-50004 from the CNP dataset examples [here](tutorials/example-usage.md))

```sh
ciftify_vol_result --integer-labels \
--ciftify-work-dir /path/to/ciftified/data \
sub-50004 my_atlas.nii.gz my_atlas.dscalar.nii
```

**Tip:** after mapping an altas or mask, I highly recommend that you convert the .dscalar.nii output to a .dlabel.nii file.  This *dense label* will open up some cool functionality in connectome-workbench. In the example below, we convert it to a label with random colours.

```sh
wb_command -cifti-label-import my_atlas.dscalar.nii '' my_atlas.dlabel.nii
```
