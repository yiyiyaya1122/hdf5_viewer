import os
import h5py
import numpy as np
import argparse
from pathlib import Path
from collections import defaultdict

def get_action_length(hdf5_path):
    """
    Opens an HDF5 file and returns the length from the 'compress_len' dataset.
    """
    try:
        with h5py.File(hdf5_path, 'r') as f:
            if 'action/base_vel' in f:
                data = f['action/base_vel']
                return len(data)
            # 如果没有，再检查 /action
            elif 'action' in f:
                data = f['action']
                return len(data)
            elif 'state/joint_position/left' in f:
                data = f['state/joint_position/left']
                return len(data)
            elif 'subtask' in f:
                data = f['subtask']
                return len(data)
            else:
                print(f"[WARN] Neither '/action/base_vel' nor '/action' found in {hdf5_path}")
                return 0
    except Exception as e:
        print(f"[ERROR] Failed to process {hdf5_path}: {e}")
        return 0


def get_all_durations(folders, fps):
    """Gathers all durations from a list of folders."""
    all_durations = []
    for folder in folders:
        hdf5_files = list(folder.rglob("*.hdf5"))
        for hdf5_file in hdf5_files:
            action_length = get_action_length(hdf5_file)
            if action_length > 0:
                duration = action_length / fps
                all_durations.append(duration)
    return all_durations

def print_category_stats(category_name, durations, fps):
    """Calculates and prints statistics for a category of folders."""
    print(f"\n--- Statistics for Category: {category_name} ---")
    
    if not durations:
        print("No valid data found for this category.")
        print("------------------------------------------")
        return

    total_files = len(durations)
    total_duration = np.sum(durations)
    average_duration = np.mean(durations)
    median_duration = np.median(durations)

    print(f"FPS used for calculation: {fps}")
    print(f"Total number of HDF5 files processed: {total_files}")
    print(f"Total duration: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
    print(f"Average duration: {average_duration:.2f} seconds")
    print(f"Median duration: {median_duration:.2f} seconds")
    print("------------------------------------------")

def main():
    parser = argparse.ArgumentParser(description="Calculate duration statistics for HDF5 files in a folder (with or without subfolders).")
    parser.add_argument("--data_folder", type=str, default="/Volumes/eai_15/data/pants_data/mobile_aloha_4_wheels", help="Path to the folder containing HDF5 files.")
    parser.add_argument("--fps", type=int, default=15, help="Frames per second (FPS) of the data.")
    args = parser.parse_args()

    data_folder = Path(args.data_folder)
    fps = args.fps

    if not data_folder.is_dir():
        print(f"[ERROR] The specified folder does not exist: {data_folder}")
        return

    # 查找当前目录及所有子目录下的hdf5文件（递归）
    hdf5_files = list(data_folder.rglob("*.hdf5"))
    if not hdf5_files:
        print(f"[INFO] No HDF5 files found in {data_folder}.")
        return

    all_durations = []
    for hdf5_file in hdf5_files:
        action_length = get_action_length(hdf5_file)
        if action_length > 0:
            duration = action_length / fps
            all_durations.append(duration)

    print_category_stats("All Files", all_durations, fps)
    print("\nProcessing finished.\n")

if __name__ == "__main__":
    main()

