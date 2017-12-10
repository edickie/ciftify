# Helper functions in ciftify

The ciftify package also contains several utilities to assist in CIFTI-based surface-level analyses.

These utilities are not meant as a replacement for the functionality in Connectome Workbench. In many cases they are, in fact, simple utilities that chain together a couple of calls to Connectome Workbench. In these cases, commands can be echoed to the user when these utilities are run in with the “--verbose” or “--debug” flags. In some cases (such as the ciftify_meants), data is read into NumPy arrays using the NiBabel package.


## [ ciftify_meants ](usage/ciftify_meants)

Produces a comma separated values (.csv) file mean voxel/vertex timeseries from a functional file <func> within a seed mask <seed>. <func> functional data input can be NIFTI or CIFTI (.dscalar.nii or .dtseries.nii).  Seed mask input can be in NIFTI, CIFTI (.dlabel.nii or .dscalar.nii) or GIFTI.

## [ ciftify_seed_corr ](usage/ciftify_seed_corr)

Produces a seed correlation map of the mean timeseries within the seed with every voxel in the functional file. Uses `ciftify_meants` to calculate the mean time series and therefore can take a combination of NIFTI, CIFTI or GIFTI inputs. The output seed correlation map matches the file type (NIFTI or CIFTI) of the input functional file.

## [ ciftify_surface_rois ](usage/ciftify_surface_rois)

Builds circular (geodesic) ROIs on a specified cortical surface according to information read from a table in a comma separated values (.csv) input file. Makes heavy use of wb_command -surface-geodesic-rois functionality.

## [ ciftify_peaktable ](usage/ciftify_peaktable)

Creates a tabular statistical report from an input (.dscalar.nii) map.  
