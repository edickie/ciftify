# ciftify_falff

Calculates fractional amplitude of low-frequency fluctuations (fALFF)

## Usage
```
    falff_nifti.py <func.nii.gz> <output.nii.gz> [options]

Arguments:
    <func.nii.gz>  The functional 4D nifti files
    <output.nii.gz>  Output filename

Options:
  --min-low-freq 0.01  Min low frequency range value Hz [default: 0.01]
  --max-low-freq 0.08  Max low frequency range value Hz [default: 0.08]
  --min-total-freq 0.00  Min total frequency range value Hz [default: 0.00]
  --max-total-freq 0.25  Max total frequency range value Hz [default: 0.25]
  --mask-file <maskfile.nii.gz>  Input brain mask
  --calc-alff  Calculates amplitude of low frequency fluctuations (ALFF) instead of fALFF
  --debug  Debug logging
  -h,--help  Print help
  ```
