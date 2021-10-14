# Copyright (C) 2021  The AURA developers
# See the AUTHORS file at the top-level directory of this distribution
# SPDX-License-Identifier: GPL-3.0

import argparse
import json


def extract_annotations(annotations_filename: str,
                        output_filename: str):
    """Extract annotations for a single EDF file.
    """

    if not output_filename.endswith(".json"):
        raise ValueError("Invalid output filepath - " + output_filename)
        exit()

    SEIZURE_TAG = "seiz"
    BACKGROUND_TAG = "bckg"

    background_intervals = []
    seizure_intervals = []

    with open(annotations_filename, "r") as f:
        if annotations_filename.endswith("tse_bi"):
            for line in f:
                tokens = line.split(" ")
                if(len(tokens) == 4):
                    if tokens[2] == SEIZURE_TAG:
                        seizure_intervals.append([float(tokens[0]),
                                                  float(tokens[1])])
                    elif tokens[2] == BACKGROUND_TAG:
                        background_intervals.append([float(tokens[0]),
                                                     float(tokens[1])])

    data = {"background": background_intervals,
            "seizure": seizure_intervals}

    with open(output_filename, "w") as out_f:
        json.dump(data, out_f)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='input parameters')
    parser.add_argument('-a',
                        '--annotations_filename',
                        dest='annotations_filename',
                        help="annotations file path",
                        metavar='FILE')
    parser.add_argument('-o',
                        '--output_filename',
                        dest='output_filename',
                        help='output file path',
                        metavar='FILE')
    args = parser.parse_args()

    extract_annotations(
        annotations_filename=args.annotations_filename,
        output_filename=args.output_filename
    )
