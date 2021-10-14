# ai4eu-aura

Implementation of the aura workflow dedicated to AI4EU Experiments.



## Data cleaner

Dockerfile and scripts are located in `datacleaner/`. This image runs the data preparation steps for a directory.
A set of data samples is provided

### Sequence:

Search for all `.edf` files within the input directory, and for each file run:
  - the ecg detector (`aura_ecg_detector.py`),
  - the annotation extractor (`aura_annotation_extractor.py`),
  - the feature extraction (`aura_features_computation.py`).

### Building and Testing

The image is based off a python image and embeds the scripts to clean the data. It is self-sufficient.

Build the image. In the repository's root directory, run:

```
docker build datacleaner/ -t ai4eu-aura/aura-datacleaner
```

Run the image. For a test drive, you can use the default data sample found in `test/data`:

```
docker run -v $(pwd)/test/data/01_tcp_ar/:/data_in -v $(pwd)/export/:/data_out ai4eu-aura/aura-datacleaner
```

All exports will be stored, in this example, in the `export/` local directory.

Example:

```
boris@castalia:ai4eu-aura$ docker build datacleaner/ -t ai4eu-aura/aura-datacleaner
Sending build context to Docker daemon  60.42kB
Step 1/9 : FROM python:3.8
 ---> 2e2712906942
 [SNIP]
Step 9/9 : ENTRYPOINT ["/scripts/aura_clean_process_dir.sh", "-i", "/data_in", "-o", "/data_out"]
 ---> Using cache
 ---> 0a2f97587210
Successfully built 0a2f97587210
Successfully tagged ai4eu-aura/aura-datacleaner:latest
boris@castalia:ai4eu-aura$ docker run -v $(pwd)/test/data/01_tcp_ar/:/data_in -v $(pwd)/export/:/data_out ai4eu-aura/aura-datacleaner
Start Executing script
* Working on file [/data_in/002/00009578/00009578_s006_t001.edf]
    EDF file [/data_in/002/00009578/00009578_s006_t001.edf]
    ECG /data_out//res_00009578_s006_t001.json - Fail
    TSE file [/data_out//00009578_s006_t001.tse_bi]
    ANNOT /data_out//annot_00009578_s006_t001.json - OK
    FEATS /data_out//feats_hamilton_00009578_s006_t001.json - Fail
* Working on file [/data_in/002/00009578/00009578_s002_t001.edf]
    EDF file [/data_in/002/00009578/00009578_s002_t001.edf]
    ECG /data_out//res_00009578_s002_t001.json - Fail
    TSE file [/data_out//00009578_s002_t001.tse_bi]
    ANNOT /data_out//annot_00009578_s002_t001.json - OK
    FEATS /data_out//feats_hamilton_00009578_s002_t001.json - Fail
```
