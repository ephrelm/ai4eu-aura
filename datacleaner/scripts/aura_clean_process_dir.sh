#!/bin/bash
# Copyright (C) 2021  The AURA developers
# See the AUTHORS file at the top-level directory of this distribution
# SPDX-License-Identifier: GPL-3.0

# QRS_DETECTORS=("gqrs" "xqrs" "hamilton" "engelsee" "swt")
QRS_DETECTORS=("hamilton")

## Option - select input directory to be copied from and output directory to copy into
while getopts ":i:o:" option; do
    case "${option}" in
	i) dir_edf=${OPTARG};;
	o) dir_out=${OPTARG};;
    esac
done

dir_script=$(dirname "$0")
LOG=$dir_out/process_directory_$(date +"%Y%m%d-%H%M%S").log

# Check script input integrity
if [[ $dir_edf ]] || [[ $dir_out ]]; then
  echo "Start Executing script"
else
  echo "No Input directory: $dir_edf or Target directory: $dir_out, use -i,-o options" >&2
  exit 1
fi


# Create dir_out if needed
mkdir -p $dir_out

## List all EDF files in dir_edf ##
for edf_file in $(find $dir_edf/ -type f -name "*.edf" ); do

    echo "* Working on file [$edf_file]" | tee -a $LOG

    # Get relative path and out file name
    edf_path="$(dirname "$edf_file")"
    relative_path="${path_edf#$dir_edf}"
    dir_out_full="${dir_out}/${relative_path}"
    # Create destination directory if it doesn't exist
    mkdir -p -- "$dir_out_full"

    # Get file name without extension
    edf_name="$(basename "$edf_file")"
    base_name=${edf_name%.edf}

    # Extract rr-intervals.
    file_out_ecg="${dir_out_full}/res_${base_name}.json"
    echo "    EDF file [$edf_file]" | tee -a $LOG
    python3 ${dir_script}/aura_ecg_detector.py \
	    -i $edf_file \
	    -o $file_out_ecg >> $LOG 2>&1
    if [ $? -eq 0 ]; then
      echo "    ECG $file_out_ecg - OK" | tee -a $LOG
    else
      echo "    ECG $file_out_ecg - Fail" | tee -a $LOG
    fi

    # Extract annotations.
    tse_file="$dir_out_full/${base_name}.tse_bi"
    file_out_annot="${dir_out_full}/annot_${base_name}.json"
    echo "    TSE file [$tse_file]" | tee -a $LOG
    python3 ${dir_script}/aura_annotation_extractor.py \
	    -a $edf_file \
	    -o $file_out_annot >> $LOG 2>&1
    if [ $? -eq 0 ]; then
      echo "    ANNOT $file_out_annot - OK" | tee -a $LOG
    else
      echo "    ANNOT $file_out_annot - Fail" | tee -a $LOG
    fi

    # Extract features.
    for qrs_detector in ${QRS_DETECTORS[@]}; do
	file_out_feats="${dir_out_full}/feats_${qrs_detector}_${base_name}.json"
	python3 ${dir_script}/aura_features_computation.py \
		-i $file_out_ecg \
		-a $file_out_annot \
		-o $file_out_feats \
		-q $qrs_detector >> $LOG 2>&1
	if [ $? -eq 0 ]; then
	    echo "    FEATS $file_out_feats - OK" | tee -a $LOG
	else
	    echo "    FEATS $file_out_feats - Fail" | tee -a $LOG
	fi
    done
done

exit 0
