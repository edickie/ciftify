# commands of running the ciftify tests

Right now all the tests really do is run teh functions and hope that nothing error out..

## the abide one

```sh
cd /projects/edickie/code/ciftify/tests/integration
python run_ABIDE_NYU_tests /scratch/edickie/ciftify_integration_tests
run_CNP_recon_all --surf-reg FS /scratch/edickie/ciftify_integration_tests
run_CNP_recon_all --surf-reg FS --resample-to-T1w32k /scratch/edickie/ciftify_integration_tests
run_CNP_recon_all --surf-reg FS --no-symlinks /scratch/edickie/ciftify_integration_tests
run_CNP_recon_all --surf-reg FS --no-symlinks --resample-to-T1w32k /scratch/edickie/ciftify_integration_tests
run_CNP_recon_all --surf-reg MSMSulc /scratch/edickie/ciftify_integration_tests
run_CNP_recon_all --surf-reg MSMSulc --resample-to-T1w32k /scratch/edickie/ciftify_integration_tests
run_CNP_recon_all --surf-reg MSMSulc --no-symlinks /scratch/edickie/ciftify_integration_tests
run_CNP_recon_all --surf-reg MSMSulc --no-symlinks --resample-to-T1w32k /scratch/edickie/ciftify_integration_tests

```


--SmoothingFWHM MM (yes or no) independant
--surf-reg REGNAME (FS or MSMSulc)

vol-reg - is independant
--FLIRT-to-T1w
first_vol median or file              Will register to T1w space (not recommended, see DETAILS)
--func-ref ref              Type/or path of image to use [default: first_vol]
                            as reference for when realigning or resampling images. See DETAILS.
--already-in-MNI            Functional volume has already been registered to MNI
                            space using the same transform in as the ciftified anatomical data
