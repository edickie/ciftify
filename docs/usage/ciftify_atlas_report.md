# ciftify_atlas_report

Takes a atlas or cluster map ('dlabel.nii') and outputs a csv of results

## Usage 
```
    ciftify_atlas_report [options] <clust.dlabel.nii>

Arguments:
    <clust.dlabel.nii>    Input atlas or cluster map.

Options:
    --outputcsv PATH    Path for csv report. (defaults to location of input)

    --left-surface GII     Left surface file (default is HCP S1200 Group Average)
    --right-surface GII    Right surface file (default is HCP S1200 Group Average)
    --left-surf-area GII   Left surface vertex areas file (default is HCP S1200 Group Average)
    --right-surf-area GII  Right surface vertex areas file (default is HCP S1200 Group Average)

    --map-number INT    The map number [default: 1] within the dlabel file to report on.

    --debug                Debug logging
    -n,--dry-run           Dry run
    -h, --help             Prints this message


```
## DETAILS :

If an outputcsv argument is not given, the output will be set to the location of dlabel input.
