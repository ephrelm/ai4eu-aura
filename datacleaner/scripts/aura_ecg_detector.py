import numpy as np
# install from https://pypi.org/project/py-ecg-detectors/
from ecgdetectors import Detectors
from wfdb import processing
import biosppy.signals.ecg as bsp_ecg
import argparse
import json
import pyedflib
import os


# We consider two matching QRS as QRS frames within a 50 milliseconds window
MATCHING_QRS_FRAMES_TOLERANCE = 50
# We consider the laximum duration of a beat in milliseconds - 33bpm
MAX_SINGLE_BEAT_DURATION = 1800


# List of RR detection algorithms


def detect_qrs_swt(ecg_data, fs):
    qrs_frames = []
    try:
        detectors = Detectors(fs)  # Explain why
        qrs_frames = detectors.swt_detector(ecg_data)
    except:
        # raise ValueError("swt")
        print("Exception in detect_qrs_swt")
    return qrs_frames


def detect_qrs_xqrs(ecg_data, fs):
    qrs_frames = []
    try:
        qrs_frames = processing.xqrs_detect(sig=ecg_data, fs=fs, verbose=False)
    except:
        print("Exception in detect_qrs_xqrs")
    # return qrs_frames.tolist()
    return qrs_frames


def detect_qrs_gqrs(ecg_data, fs):
    qrs_frames = []
    try:
        qrs_frames = processing.qrs.gqrs_detect(sig=ecg_data, fs=fs)
    except:
        print("Exception in detect_qrs_gqrs")
    return qrs_frames.tolist()


def detect_qrs_hamilton(ecg_data, fs):
    qrs_frames = []
    try:
        qrs_frames = bsp_ecg.hamilton_segmenter(
            signal=np.array(ecg_data),
            sampling_rate=fs)[0]

    except:
        # raise ValueError("xqrs")
        print("Exception in detect_qrs_hamilton")
    return qrs_frames

# Centralising function


def get_cardiac_infos(ecg_data, fs, method):
    if method == "xqrs":
        qrs_frames = detect_qrs_xqrs(ecg_data, fs)
    elif method == "gqrs":
        qrs_frames = detect_qrs_gqrs(ecg_data, fs)
    elif method == "swt":
        qrs_frames = detect_qrs_gqrs(ecg_data, fs)
    elif method == "hamilton":
        qrs_frames = detect_qrs_hamilton(ecg_data, fs)

    rr_intervals = np.zeros(0)
    hr = np.zeros(0)
    if len(qrs_frames):
        rr_intervals = to_rr_intervals(qrs_frames, fs)
        hr = to_hr(rr_intervals)
    return qrs_frames, rr_intervals, hr


# UTILITIES

def to_rr_intervals(frame_data, fs):
    rr_intervals = np.zeros(len(frame_data) - 1)
    for i in range(0, (len(frame_data) - 1)):
        rr_intervals[i] = (frame_data[i+1] - frame_data[i]) * 1000.0 / fs

    return rr_intervals


def to_hr(rr_intervals):
    hr = np.zeros(len(rr_intervals))
    for i in range(0, len(rr_intervals)):
        hr[i] = (int)(60 * 1000 / rr_intervals[i])

    return hr


def compute_qrs_frames_correlation(fs, qrs_frames_1, qrs_frames_2):
    single_frame_duration = 1./fs

    frame_tolerance = MATCHING_QRS_FRAMES_TOLERANCE * (
        0.001 / single_frame_duration)
    max_single_beat_frame_duration = MAX_SINGLE_BEAT_DURATION * (
        0.001 / single_frame_duration)

    # Catch complete failed QRS detection
    if (len(qrs_frames_1) == 0 or len(qrs_frames_2) == 0):
        return 0, 0, 0

    i = 0
    j = 0
    matching_frames = 0

    previous_min_qrs_frame = min(qrs_frames_1[0], qrs_frames_2[0])
    missing_beats_frames_count = 0

    while i < len(qrs_frames_1) and j < len(qrs_frames_2):
        min_qrs_frame = min(qrs_frames_1[i], qrs_frames_2[j])
        # Get missing detected beats intervals
        if (min_qrs_frame - previous_min_qrs_frame) > (
                max_single_beat_frame_duration):
            missing_beats_frames_count += (min_qrs_frame -
                                           previous_min_qrs_frame)

        # Matching frames

        if abs(qrs_frames_2[j] - qrs_frames_1[i]) < frame_tolerance:
            matching_frames += 1
            i += 1
            j += 1
        else:
            # increment first QRS in frame list
            if min_qrs_frame == qrs_frames_1[i]:
                i += 1
            else:
                j += 1
        previous_min_qrs_frame = min_qrs_frame

    correlation_coefs = 2 * matching_frames / (len(qrs_frames_1) +
                                               len(qrs_frames_2))

    missing_beats_duration = missing_beats_frames_count * single_frame_duration
    correlation_coefs = round(correlation_coefs, 2)
    return correlation_coefs, matching_frames, missing_beats_duration


def get_ecg_labels(signal_labels):
    ecg_labels = [l for l in signal_labels if (
        "EKG" in l.upper() or "ECG" in l.upper())]
    return ecg_labels


def detect_ecg(input_filename: str,
               output_filename: str) -> dict:

    data = {"infos": {"sampling_freq": None,
                      "start_datetime": None,
                      "exam_duration": None,
                      "ref_file": None
                      },
            "gqrs": {"qrs": None,
                     "rr_intervals": None,
                     "hr": None
                     },
            "xqrs": {"qrs": None,
                     "rr_intervals": None,
                     "hr": None
                     },
            "swt": {"qrs": None,
                    "rr_intervals": None,
                    "hr": None
                    },
            "hamilton": {"qrs": None,
                         "rr_intervals": None,
                         "hr": None
                         },
            "score": {"corrcoefs":
                      {"gqrs": None,
                       "xqrs": None,
                       "swt": None
                       },
                      "matching_frames":
                      {"gqrs": None,
                       "xqrs": None,
                       "swt": None
                       },
                      "missing_beats_duration":
                      {"gqrs": None,
                       "xqrs": None,
                       "swt": None
                       }
                      }
            }

    f = pyedflib.EdfReader(input_filename)

    # Get general informations
    start_datetime = f.getStartdatetime()
    exam_duration = f.getFileDuration()
    ref_file = os.path.basename(input_filename)

    # get ECG channel
    signal_labels = f.getSignalLabels()
    ecg_labels = get_ecg_labels(signal_labels)
    n_ecg_channels = len(ecg_labels)
    if n_ecg_channels != 1:
        raise ValueError("Invalid ECG channels - " + str(n_ecg_channels))

    ecg_label = ecg_labels[0]
    ecg_channel_index = signal_labels.index(ecg_label)

    # get ECG data and attributes
    ecg_data = f.readSignal(ecg_channel_index)
    fs = f.getSampleFrequency(ecg_channel_index)

    beginning_frame = 0

    qrs_frames_gqrs, rr_intervals_gqrs, hr_gqrs = \
        get_cardiac_infos(ecg_data, fs*2, "gqrs")  # Explain
    qrs_frames_xqrs, rr_intervals_xqrs, hr_xqrs = \
        get_cardiac_infos(ecg_data, fs, "xqrs")
    qrs_frames_swt, rr_intervals_swt, hr_swt = \
        get_cardiac_infos(ecg_data, fs*2, "swt")  # Explain
    qrs_frames_hamilton, rr_intervals_hamilton, hr_hamilton = \
        get_cardiac_infos(ecg_data, fs, "hamilton")

    hr_gqrs = hr_gqrs/2  # Explain
    hr_swt = hr_swt/2  # Explain

    qrs_frames_gqrs = beginning_frame + np.array(qrs_frames_gqrs)/fs
    qrs_frames_xqrs = beginning_frame + np.array(qrs_frames_xqrs)/fs
    qrs_frames_swt = beginning_frame + np.array(qrs_frames_swt)/fs
    qrs_frames_hamilton = beginning_frame + np.array(
        qrs_frames_hamilton)/fs

    frame_correl_1, matching_frames_1, missing_beats_duration_1 = \
        compute_qrs_frames_correlation(fs,
                                       qrs_frames_gqrs,
                                       qrs_frames_xqrs)
    frame_correl_2, matching_frames_2, missing_beats_duration_2 = \
        compute_qrs_frames_correlation(fs,
                                       qrs_frames_gqrs,
                                       qrs_frames_swt)
    frame_correl_3, matching_frames_3, missing_beats_duration_3 = \
        compute_qrs_frames_correlation(fs,
                                       qrs_frames_xqrs,
                                       qrs_frames_swt)
    frame_correl_4, matching_frames_4, missing_beats_duration_4 = \
        compute_qrs_frames_correlation(fs,
                                       qrs_frames_gqrs,
                                       qrs_frames_hamilton)
    frame_correl_5, matching_frames_5, missing_beats_duration_5 = \
        compute_qrs_frames_correlation(fs,
                                       qrs_frames_xqrs,
                                       qrs_frames_hamilton)
    frame_correl_6, matching_frames_6, missing_beats_duration_6 = \
        compute_qrs_frames_correlation(fs,
                                       qrs_frames_swt,
                                       qrs_frames_hamilton)

    data = {"infos": {"sampling_freq": fs,
                      "start_datetime": start_datetime.strftime(
                          "%Y/%m/%d %H:%M:%S"),
                      "exam_duration": exam_duration,
                      "ref_file": ref_file
                      },
            "gqrs": {"qrs": qrs_frames_gqrs.tolist(),
                     "rr_intervals": rr_intervals_gqrs.tolist(),
                     "hr": hr_gqrs.tolist()
                     },
            "xqrs": {"qrs": qrs_frames_xqrs.tolist(),
                     "rr_intervals": rr_intervals_xqrs.tolist(),
                     "hr": hr_xqrs.tolist()
                     },
            "swt": {"qrs": qrs_frames_swt.tolist(),
                    "rr_intervals": rr_intervals_swt.tolist(),
                    "hr": hr_swt.tolist()
                    },
            "hamilton": {"qrs": qrs_frames_hamilton.tolist(),
                         "rr_intervals": rr_intervals_hamilton.
                         tolist(),
                         "hr": hr_hamilton.tolist()
                         },
            "score": {"corrcoefs":
                      {"gqrs": [1, frame_correl_1, frame_correl_2,
                                frame_correl_4],
                       "xqrs": [frame_correl_1, 1, frame_correl_3,
                                frame_correl_5],
                       "swt": [frame_correl_2, frame_correl_3, 1,
                               frame_correl_6],
                       "hamilton": [frame_correl_4, frame_correl_5,
                                    frame_correl_6, 1]
                       },
                      "matching_frames":
                      {"gqrs": [1,
                                matching_frames_1,
                                matching_frames_2,
                                matching_frames_4],
                       "xqrs": [matching_frames_1,
                                1,
                                matching_frames_3,
                                matching_frames_5],
                       "swt": [matching_frames_2,
                               matching_frames_3,
                               1,
                               matching_frames_6],
                       "hamilton": [matching_frames_4,
                                    matching_frames_5,
                                    matching_frames_6,
                                    1]
                       },
                      "missing_beats_duration":
                          {"gqrs": [1,
                                    missing_beats_duration_1,
                                    missing_beats_duration_2,
                                    missing_beats_duration_4],
                           "xqrs": [missing_beats_duration_1,
                                    1,
                                    missing_beats_duration_3,
                                    missing_beats_duration_5],
                           "swt": [missing_beats_duration_2,
                                   missing_beats_duration_3,
                                   1,
                                   missing_beats_duration_6],
                           "hamilton": [missing_beats_duration_4,
                                        missing_beats_duration_5,
                                        missing_beats_duration_6,
                                        1]
                           }
                      }
            }

    json.dump(data, open(output_filename, "w"))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='input parameters')
    parser.add_argument('-i',
                        '--input_file',
                        dest='input_filename',
                        help='input file path')
    parser.add_argument('-o',
                        '--output_file',
                        dest='output_filename',
                        help='output file path')
    args = parser.parse_args()

    detect_ecg(input_filename=args.input_filename,
               output_filename=args.output_filename)
