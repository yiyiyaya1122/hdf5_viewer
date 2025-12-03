import os
import argparse

def get_all_files_with_parents(root_path, ext):
    file_set = set()
    for dirpath, dirnames, filenames in os.walk(root_path):
        for filename in filenames:
            if filename.lower().endswith(ext):
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, root_path)
                parts = rel_path.split(os.sep)
                # 获取上两级文件夹和文件名（不含扩展名）
                if len(parts) >= 3:
                    key = os.path.join(parts[-3], parts[-2], os.path.splitext(parts[-1])[0])
                elif len(parts) == 2:
                    key = os.path.join(parts[-2], os.path.splitext(parts[-1])[0])
                else:
                    key = os.path.splitext(parts[-1])[0]
                file_set.add(key)
    return file_set

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="找出hdf5文件夹中有但json文件夹中没有的文件（按文件名和上两级文件夹匹配）。")
    parser.add_argument("--hdf5_folder", type=str, default="/media/jz08/HDD/cyf/data/test/hdf5", help="hdf5文件夹路径")
    parser.add_argument("--json_folder", type=str, default="/media/jz08/HDD/cyf/data/test/json", help="json文件夹路径")
    args = parser.parse_args()

    hdf5_names = get_all_files_with_parents(args.hdf5_folder, ".hdf5")
    json_names = get_all_files_with_parents(args.json_folder, ".json")

    only_in_hdf5 = sorted(hdf5_names - json_names)
    print(f"在hdf5文件夹中但不在json文件夹中的文件（共{len(only_in_hdf5)}个）：")
    for name in only_in_hdf5:
        print(name)

