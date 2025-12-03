# -*- coding: utf-8 -*-
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import h5py
from PIL import Image
import cv2


class HDF5Model:
    """HDF5数据模型，用于管理和处理HDF5数据"""
    
    def __init__(self, file_path: str):
        """
        初始化HDF5模型
        
        Args:
            file_path: HDF5文件路径
        """
        self.file_path = file_path
        self.file = None
        self.frame_count = 0
        self.image_keys = []
        self.data_keys = []
        self.languages = {}
        self.compressed = False
        self.compress_len = None
        
        # 打开文件并初始化
        self._open_file()
        self._initialize()
        
    def _open_file(self):
        """打开HDF5文件"""
        try:
            self.file = h5py.File(self.file_path, 'r+')
        except Exception as e:
            raise RuntimeError(f"无法打开HDF5文件: {e}")
    
    def _check_compression(self):
        """检测HDF5文件是否使用了图像压缩"""
        try:
            # 检查是否有compress属性
            self.compressed = self.file.attrs.get('compress', False)
            
            if self.compressed:
                # 如果是压缩数据集，加载压缩长度信息
                if 'compress_len' in self.file:
                    self.compress_len = self.file['compress_len'][()]
                    print(f"检测到压缩数据集，压缩长度信息形状: {self.compress_len.shape}")
                else:
                    print("警告: 检测到compress=True但未找到compress_len数据集")
                    self.compressed = False
            else:
                print("检测到非压缩数据集")
                
        except Exception as e:
            print(f"检测压缩信息时出错: {e}")
            self.compressed = False
            self.compress_len = None
    
    def _initialize(self):
        """初始化模型数据"""
        # 检测是否为压缩数据集
        self._check_compression()
        
        # 获取帧数 - 优先从图像数据集获取
        self.frame_count = 0
        
        # 首先尝试从observations/images路径获取帧数（适用于压缩数据集）
        try:
            if 'observations' in self.file and 'images' in self.file['observations']:
                images_group = self.file['observations/images']
                for cam_name in images_group.keys():
                    dataset = images_group[cam_name]
                    if isinstance(dataset, h5py.Dataset) and len(dataset.shape) > 0:
                        self.frame_count = dataset.shape[0]
                        print(f"从图像数据集 {cam_name} 获取帧数: {self.frame_count}")
                        break
        except Exception as e:
            print(f"从图像组获取帧数时出错: {e}")
        
        # 如果没有从图像获取到帧数，从其他数据集获取
        if self.frame_count == 0:
            for key in self.file.keys():
                try:
                    dataset = self.file[key]
                    if isinstance(dataset, h5py.Dataset) and len(dataset.shape) > 0:
                        # 跳过明显是标量或小数据集的键
                        if dataset.shape[0] > 1:  # 至少要有2帧
                            self.frame_count = dataset.shape[0]
                            print(f"从数据集 {key} 获取帧数: {self.frame_count}")
                            break
                except Exception as e:
                    continue
        
        # 如果仍然没有帧数，设置默认值
        if self.frame_count == 0:
            self.frame_count = 1
            print("警告: 无法确定帧数，设置默认值为1")
        
        print(f"最终确定的帧数: {self.frame_count}")
        
        # 获取图像键和数据键
        self._find_keys()
        
        # 加载已有的language
        self._load_languages()
    
    def _find_keys(self):
        """查找图像键和数据键"""
        self.image_keys = []
        self.data_keys = []

        def visit_item(name, obj):
            if isinstance(obj, h5py.Dataset):
                # 判断是否为图像数据集
                if self._is_image_dataset(obj):
                    self.image_keys.append(name)
                else:
                    self.data_keys.append(name)

        self.file.visititems(visit_item)
    
    def _is_image_dataset(self, dataset):
        """
        判断数据集是否为图像
        
        Args:
            dataset: HDF5数据集
            
        Returns:
            是否为图像数据集
        """
        # 检查数据集名称路径，看是否在 images 目录下
        dataset_name = dataset.name
        if '/images/' in dataset_name:
            # 如果在images目录下，进一步检查数据类型和维度
            if dataset.dtype == np.uint8:
                if len(dataset.shape) == 2:
                    # 二维uint8数组，很可能是压缩图像数据
                    return True
                elif len(dataset.shape) >= 3 and (dataset.shape[-1] == 3 or dataset.shape[-1] == 4):
                    # 三维或四维数组，最后一维是通道数，是未压缩图像
                    return True
        
        # 原有的检测逻辑（兼容其他情况）
        return (len(dataset.shape) >= 3 and 
                (dataset.shape[-1] == 3 or dataset.shape[-1] == 4) and
                dataset.dtype in [np.uint8, np.int8])
    
    def _load_languages(self):
        """加载已有的language"""
        self.languages = {}  # 重置languages字典，这将是一个二级字典: {key: {(start, end): description}}
        
        # 获取所有可能的language键
        language_keys = self.get_language_keys()
        
        # 为每个language键加载数据
        for key in language_keys:
            if key in self.file:
                self._load_language_for_key(key)
    
    def _load_language_for_key(self, key: str):
        """为指定键加载language数据"""
        key_languages = {}
        
        try:
            language_data = self.file[key]
            print(f"加载{key}数据集，形状: {language_data.shape}, 类型: {language_data.dtype}")
            
            # 遍历所有帧，标记已有的language
            current_task = None
            start_idx = None
            
            for i in range(self.frame_count):
                # 处理编码，确保可以正确处理中文
                try:
                    if i < language_data.shape[0] and (len(language_data.shape) == 1 or language_data.shape[1] > 0):
                        # 尝试直接获取字符串
                        if len(language_data.shape) == 1:
                            # 一维数组
                            task_value = language_data[i]
                        else:
                            # 二维数组
                            task_value = language_data[i, 0]
                        
                        # 处理可能的字节对象
                        if isinstance(task_value, bytes):
                            task = task_value.decode('utf-8', errors='replace')
                        elif isinstance(task_value, str):
                            task = task_value
                        elif isinstance(task_value, (int, float)):
                            task = str(task_value)
                        else:
                            task = str(task_value)
                        
                        # 去除前后空白
                        task = task.strip()
                        
                        # 处理特殊格式，如果显示为 b'...'
                        if task.startswith("b'") and task.endswith("'"):
                            try:
                                task = task[2:-1]
                            except:
                                pass
                    else:
                        task = ""
                except Exception as e:
                    print(f"解码帧 {i} 的{key}时出错: {e}")
                    task = ""
                
                if task and task != "0" and task != 0:  # 忽略空值和0值
                    if current_task is None or task != current_task:
                        # 新任务开始或任务变更
                        if current_task is not None and start_idx is not None:
                            # 保存上一个任务
                            key_languages[(start_idx, i - 1)] = current_task
                        
                        current_task = task
                        start_idx = i
                    # 若任务未变更，继续追踪当前任务，无需操作
                elif current_task is not None:
                    # 任务结束
                    if start_idx is not None:
                        key_languages[(start_idx, i - 1)] = current_task
                    current_task = None
                    start_idx = None
            
            # 保存最后一个任务
            if current_task is not None and start_idx is not None:
                key_languages[(start_idx, self.frame_count - 1)] = current_task
            
            # 保存到缓存
            self.languages[key] = key_languages
            
            # 打印加载的language信息
            print(f"加载了 {len(key_languages)} 个{key}段")
            for (start, end), desc in key_languages.items():
                print(f"{key}段: {start}-{end}, 描述: '{desc}'")
                
        except Exception as e:
            print(f"加载{key}数据时出错: {e}")
            self.languages[key] = {}
    
    def close(self):
        """关闭HDF5文件"""
        if self.file:
            self.file.close()
            self.file = None
    
    def __del__(self):
        """析构函数，确保文件被关闭"""
        self.close()
    
    def is_compressed(self) -> bool:
        """
        检查数据集是否使用了图像压缩
        
        Returns:
            如果数据集使用了压缩返回True，否则返回False
        """
        return self.compressed
    
    def get_frame_count(self) -> int:
        """
        获取帧数
        
        Returns:
            总帧数
        """
        return self.frame_count
    
    def get_image_keys(self) -> List[str]:
        """
        获取所有图像键
        
        Returns:
            图像键列表
        """
        return self.image_keys
    
    def get_data_keys(self) -> List[str]:
        """
        获取所有数据键

        Returns:
            数据键列表
        """
        return self.data_keys

    def get_annotation_compatible_keys(self) -> List[str]:
        """
        获取适合保存标注的字段（字符串类型或可以转换为字符串的字段）

        Returns:
            适合标注的字段列表
        """
        compatible_keys = []

        for key in self.data_keys:
            try:
                if key in self.file:
                    dataset = self.file[key]
                    dtype = dataset.dtype

                    # 检查是否是字符串类型或可变长度字符串
                    if (dtype.kind in ['S', 'U'] or  # 固定长度字符串或Unicode字符串
                        h5py.check_string_dtype(dtype) is not None or  # 可变长度字符串
                        'string' in str(dtype).lower()):  # 其他字符串类型
                        compatible_keys.append(key)
                        print(f"字段 '{key}' 适合保存标注 (类型: {dtype})")
                    else:
                        print(f"字段 '{key}' 不适合保存标注 (类型: {dtype})")

            except Exception as e:
                print(f"检查字段 '{key}' 时出错: {e}")

        return compatible_keys
    
    def get_image(self, key: str, frame_idx: int) -> np.ndarray:
        """
        获取指定帧的图像，自动处理压缩和非压缩的情况
        
        Args:
            key: 图像键
            frame_idx: 帧索引
            
        Returns:
            图像数据
        """
        if key not in self.image_keys or not (0 <= frame_idx < self.frame_count):
            return None
        
        # 获取原始图像数据
        raw_image_data = self.file[key][frame_idx]
        
        # 如果不是压缩数据集，直接返回
        if not self.compressed:
            return raw_image_data
        
        # 处理压缩图像
        return self._decode_compressed_image(key, frame_idx, raw_image_data)
    
    def _decode_compressed_image(self, key: str, frame_idx: int, compressed_data: np.ndarray) -> np.ndarray:
        """
        解码压缩的图像数据
        
        Args:
            key: 图像键
            frame_idx: 帧索引
            compressed_data: 压缩的图像数据
            
        Returns:
            解码后的图像数据
        """
        try:
            # 检查是否是深度图像，深度图像通常不压缩
            if "_depth" in key:
                return compressed_data
            
            # 获取该相机的索引
            image_keys = self.get_image_keys()
            
            # 过滤出非深度图像键，并按键名排序以确保一致的索引
            non_depth_keys = [k for k in image_keys if "_depth" not in k]
            non_depth_keys.sort()  # 排序确保一致性
            
            if key not in non_depth_keys:
                print(f"警告: 键 {key} 不在非深度图像键列表中: {non_depth_keys}")
                return compressed_data
            
            cam_id = non_depth_keys.index(key)
            
            if self.compress_len is None:
                print(f"警告: 无法找到压缩长度信息，键: {key}")
                return compressed_data
            
            # 检查compress_len的形状和索引
            if cam_id >= self.compress_len.shape[0] or frame_idx >= self.compress_len.shape[1]:
                print(f"警告: 索引超出范围，cam_id: {cam_id}, frame_idx: {frame_idx}, compress_len形状: {self.compress_len.shape}")
                return compressed_data
            
            # 获取该帧的压缩长度
            compressed_length = int(self.compress_len[cam_id, frame_idx])

            # 检查压缩长度是否合理
            max_reasonable_length = len(compressed_data)
            if compressed_length <= 0 or compressed_length > max_reasonable_length:
                print(f"警告: 无效的压缩长度: {compressed_length}，数据长度: {len(compressed_data)}")
                # 对于无效的压缩长度，尝试使用整个数据长度
                if len(compressed_data) > 0:
                    print(f"尝试使用完整数据长度: {len(compressed_data)}")
                    compressed_length = len(compressed_data)
                else:
                    return None
            
            # 提取有效的压缩数据（去除填充）
            valid_compressed_data = compressed_data[:compressed_length]
            
            # 使用OpenCV解码JPEG图像
            decoded_image = cv2.imdecode(valid_compressed_data, cv2.IMREAD_COLOR)

            if decoded_image is None:
                print(f"警告: 无法解码图像，键: {key}, 帧: {frame_idx}")
                return None
            
            # 根据测试结果，OpenCV的BGR格式在PyQt5中显示正确
            # 不需要进行颜色转换
            print(f"解码图像形状: {decoded_image.shape}, BGR格式（直接使用）")
            
            return decoded_image
            
        except Exception as e:
            print(f"解码压缩图像时出错，键: {key}, 帧: {frame_idx}, 错误: {e}")
            return None
    
    def get_data(self, key: str, frame_idx: Optional[int] = None) -> Any:
        """
        获取指定帧的数据，安全处理各种数据集类型
        
        Args:
            key: 数据键
            frame_idx: 帧索引，如果为None则返回整个数据集
            
        Returns:
            数据
        """
        if key not in self.file:
            return None
        
        dataset = self.file[key]
        
        try:
            # 检查数据集是否为标量（0维）
            if len(dataset.shape) == 0:
                # 标量数据集，直接返回值，不支持索引
                return dataset[()]
            
            # 检查数据集是否为空
            if dataset.size == 0:
                return None
            
            if frame_idx is not None:
                # 确保frame_idx在有效范围内
                if frame_idx < 0 or frame_idx >= self.frame_count:
                    return None
                
                # 检查frame_idx是否在数据集范围内
                if frame_idx >= dataset.shape[0]:
                    # 如果frame_idx超出数据集范围，但数据集不为空
                    # 返回数据集的最后一个有效值
                    if dataset.shape[0] > 0:
                        last_idx = dataset.shape[0] - 1
                        return dataset[last_idx]
                    else:
                        return None
                
                # 正常索引访问
                return dataset[frame_idx]
            else:
                # 返回整个数据集
                return dataset[()]
                    
        except Exception as e:
            print(f"获取数据 {key} 时出错: {e}, 数据集形状: {dataset.shape}")
            # 发生错误时的安全处理
            try:
                # 尝试直接获取标量值
                return dataset[()]
            except:
                return None
    
    def get_data_info(self, key: str) -> Dict[str, Any]:
        """
        获取数据集信息，安全处理各种异常情况
        
        Args:
            key: 数据键
            
        Returns:
            数据集信息
        """
        try:
            if key in self.file:
                dataset = self.file[key]
                return {
                    'shape': dataset.shape,
                    'dtype': str(dataset.dtype),
                    'dims': len(dataset.shape),
                    'size': dataset.size
                }
        except Exception as e:
            print(f"获取数据集 {key} 信息时出错: {e}")
            return {
                'shape': '未知',
                'dtype': '未知',
                'dims': 0,
                'size': 0,
                'error': str(e)
            }
        return {}
    
    def set_language(self, start_idx: int, end_idx: int, description: str) -> bool:
        """
        设置一段帧的language描述（兼容旧接口）
        
        Args:
            start_idx: 起始帧索引
            end_idx: 结束帧索引
            description: language描述
            
        Returns:
            是否设置成功
        """
        return self.set_language_for_key("language", start_idx, end_idx, description)
    
    def get_languages(self) -> Dict[Tuple[int, int], str]:
        """
        获取所有language（兼容旧接口）
        
        Returns:
            所有language，格式为{(start_idx, end_idx): description}
        """
        return self.get_languages_for_key("language")
    
    def get_non_zero_frames(self, key: str) -> List[int]:
        """
        获取指定键的非零帧索引
        
        Args:
            key: 数据键
            
        Returns:
            非零帧索引列表
        """
        if key not in self.file:
            return []
        
        dataset = self.file[key]
        non_zero_frames = []
        
        # 确保数据集形状与帧数兼容
        if len(dataset.shape) == 0 or dataset.shape[0] == 0:
            return []
            
        # 确定实际使用的帧数
        actual_frames = min(self.frame_count, dataset.shape[0])
        
        # 检查数据集维度
        if len(dataset.shape) == 1:
            # 一维数据集
            for i in range(actual_frames):
                if dataset[i]:
                    non_zero_frames.append(i)
        elif len(dataset.shape) == 2:
            # 二维数据集，检查每一行是否有非零值
            for i in range(actual_frames):
                if np.any(dataset[i]):
                    non_zero_frames.append(i)
        else:
            # 高维数据集，检查每一帧是否有非零值
            for i in range(actual_frames):
                if np.any(dataset[i]):
                    non_zero_frames.append(i)
        
        return non_zero_frames
    
    def get_continuous_segments(self, key: str) -> List[Tuple[int, int]]:
        """
        获取指定键的连续非零段
        
        Args:
            key: 数据键
            
        Returns:
            连续非零段列表，格式为[(start_idx, end_idx), ...]
        """
        non_zero_frames = self.get_non_zero_frames(key)
        segments = []
        
        if not non_zero_frames:
            return segments
        
        start_idx = non_zero_frames[0]
        prev_idx = start_idx
        
        for i in range(1, len(non_zero_frames)):
            idx = non_zero_frames[i]
            if idx > prev_idx + 1:
                # 不连续，添加一个段
                segments.append((start_idx, prev_idx))
                start_idx = idx
            prev_idx = idx
        
        # 添加最后一个段
        segments.append((start_idx, prev_idx))
        
        return segments
    
    def get_value_based_segments(self, key: str) -> List[Tuple[int, int, Any]]:
        """
        获取指定键基于实际数据值的连续段
        
        Args:
            key: 数据键
            
        Returns:
            基于值的连续段列表，格式为[(start_idx, end_idx, value), ...]
        """
        if key not in self.file:
            return []
        
        dataset = self.file[key]
        segments = []
        
        # 确保数据集形状与帧数兼容
        if len(dataset.shape) == 0 or dataset.shape[0] == 0:
            return []
            
        # 确定实际使用的帧数
        actual_frames = min(self.frame_count, dataset.shape[0])
        
        if actual_frames == 0:
            return []
        
        # 获取第一帧的值作为起始
        current_value = self._get_frame_value(dataset, 0)
        start_idx = 0
        
        for i in range(1, actual_frames):
            frame_value = self._get_frame_value(dataset, i)
            
            # 检查值是否发生变化
            if not self._values_equal(current_value, frame_value):
                # 值发生变化，结束当前段（如果当前值不为空/零）
                if self._is_valid_value(current_value):
                    segments.append((start_idx, i - 1, current_value))
                
                # 开始新段
                current_value = frame_value
                start_idx = i
        
        # 添加最后一个段（如果值有效）
        if self._is_valid_value(current_value):
            segments.append((start_idx, actual_frames - 1, current_value))
        
        return segments
    
    def _get_frame_value(self, dataset, frame_idx: int) -> Any:
        """
        获取指定帧的数据值，处理不同的数据类型
        
        Args:
            dataset: HDF5数据集
            frame_idx: 帧索引
            
        Returns:
            处理后的数据值
        """
        try:
            if len(dataset.shape) == 1:
                # 一维数据集
                raw_value = dataset[frame_idx]
            elif len(dataset.shape) == 2:
                # 二维数据集，取第一列
                raw_value = dataset[frame_idx, 0] if dataset.shape[1] > 0 else None
            else:
                # 高维数据集，取第一个元素
                raw_value = dataset[frame_idx].flat[0] if dataset[frame_idx].size > 0 else None
            
            # 处理不同类型的值
            if isinstance(raw_value, bytes):
                try:
                    return raw_value.decode('utf-8', errors='replace').strip()
                except:
                    return str(raw_value)
            elif isinstance(raw_value, np.bytes_):
                try:
                    return raw_value.decode('utf-8', errors='replace').strip()
                except:
                    return str(raw_value)
            elif isinstance(raw_value, (np.integer, np.floating)):
                return raw_value.item()  # 转换为Python原生类型
            elif isinstance(raw_value, str):
                return raw_value.strip()
            else:
                return raw_value
                
        except Exception as e:
            print(f"获取帧 {frame_idx} 的值时出错: {e}")
            return None
    
    def _values_equal(self, value1: Any, value2: Any) -> bool:
        """
        比较两个值是否相等，处理不同数据类型
        
        Args:
            value1: 第一个值
            value2: 第二个值
            
        Returns:
            是否相等
        """
        # 处理None值
        if value1 is None and value2 is None:
            return True
        if value1 is None or value2 is None:
            return False
        
        # 处理数值类型
        if isinstance(value1, (int, float, np.integer, np.floating)) and \
           isinstance(value2, (int, float, np.integer, np.floating)):
            try:
                return abs(float(value1) - float(value2)) < 1e-10
            except:
                return False
        
        # 处理字符串类型
        if isinstance(value1, (str, bytes)) and isinstance(value2, (str, bytes)):
            str1 = str(value1).strip()
            str2 = str(value2).strip()
            return str1 == str2
        
        # 其他类型直接比较
        try:
            return value1 == value2
        except:
            return str(value1) == str(value2)
    
    def _is_valid_value(self, value: Any) -> bool:
        """
        检查值是否有效（非空、非零）
        
        Args:
            value: 要检查的值
            
        Returns:
            是否为有效值
        """
        if value is None:
            return False
        
        # 处理字符串类型
        if isinstance(value, (str, bytes)):
            str_value = str(value).strip()
            return str_value != "" and str_value != "0" and str_value != "b''" and str_value != "b'0'"
        
        # 处理数值类型
        if isinstance(value, (int, float, np.integer, np.floating)):
            try:
                return float(value) != 0.0
            except:
                return False
        
        # 处理布尔类型
        if isinstance(value, (bool, np.bool_)):
            return bool(value)
        
        # 其他类型，检查是否为"真值"
        try:
            return bool(value)
        except:
            return False
    
    def get_language_keys(self) -> List[str]:
        """
        获取所有可能的language键
        
        Returns:
            language键列表
        """
        language_keys = []
        
        print(f"检测HDF5文件中的language类型键，文件包含的所有键: {list(self.file.keys())}")
        
        # 查找所有可能是language类型的键
        for key in self.file.keys():
            dataset = self.file[key]
            if isinstance(dataset, h5py.Dataset):
                print(f"检查键 '{key}': 形状={dataset.shape}, 数据类型={dataset.dtype}")
                # 检查是否是字符串类型的数据集
                if (dataset.dtype.kind in ['S', 'U', 'O'] or  # 字节字符串、Unicode字符串、对象
                    h5py.check_string_dtype(dataset.dtype) is not None):
                    language_keys.append(key)
                    print(f"添加语言键: '{key}'")
        
        # 确保"language"键在列表中（如果存在）
        if "language" in self.file and "language" not in language_keys:
            language_keys.append("language")
            print("添加默认的'language'键")
        
        # 如果没有找到任何language键，检查是否有其他文本相关的键
        if not language_keys:
            print("没有找到字符串类型的键，检查其他可能的文本键...")
            # 查找包含"language", "text", "description", "label"等词的键
            text_related_keywords = ['language', 'text', 'description', 'label', 'instruction', 'task']
            for key in self.file.keys():
                key_lower = key.lower()
                if any(keyword in key_lower for keyword in text_related_keywords):
                    language_keys.append(key)
                    print(f"添加文本相关键: '{key}'")
        
        # 如果仍然没有找到任何键，创建一个默认的"language"键
        if not language_keys:
            print("没有找到任何language类型的键，将创建默认的'language'键")
            # 不在这里创建，而是返回默认键名，让调用者决定是否创建
            language_keys.append("language")
        
        print(f"最终返回的language键列表: {language_keys}")
        return sorted(language_keys)
    
    def create_language_key(self, key: str) -> bool:
        """
        创建新的language键
        
        Args:
            key: 新的键名
            
        Returns:
            是否创建成功
        """
        if key in self.file:
            print(f"键 '{key}' 已存在")
            return False
        
        try:
            # 创建新的数据集，使用可变长度的UTF-8字符串类型
            string_dt = h5py.string_dtype(encoding='utf-8')
            self.file.create_dataset(key, (self.frame_count, 1), dtype=string_dt, fillvalue="")
            
            # 更新数据键列表
            if key not in self.data_keys:
                self.data_keys.append(key)
            
            print(f"成功创建language键 '{key}'")
            return True
        except Exception as e:
            print(f"创建language键 '{key}' 失败: {e}")
            return False
    
    def set_language_for_key(self, key: str, start_frame: int, end_frame: int, description: str) -> bool:
        """
        为指定键设置language描述

        Args:
            key: 键名
            start_frame: 起始帧
            end_frame: 结束帧
            description: 描述

        Returns:
            是否设置成功
        """
        try:
            # 如果键不存在，先创建
            if key not in self.file:
                success = self.create_language_key(key)
                if not success:
                    print(f"创建键 {key} 失败")
                    return False

            # 获取数据集
            dataset = self.file[key]
            frame_count = dataset.shape[0]

            # 检查帧范围
            if start_frame < 0 or end_frame >= frame_count or start_frame > end_frame:
                print(f"帧范围无效: {start_frame}-{end_frame}, 总帧数: {frame_count}")
                return False

            # 检查数据集类型并相应处理
            dtype = dataset.dtype
            print(f"数据集 '{key}' 的类型: {dtype}")

            # 设置范围内的所有帧
            for frame in range(start_frame, end_frame + 1):
                try:
                    if dtype.kind in ['S', 'U'] or h5py.check_string_dtype(dtype) is not None:
                        # 字符串类型数据集
                        if len(dataset.shape) == 1:
                            dataset[frame] = description
                        else:
                            dataset[frame, 0] = description
                    else:
                        # 非字符串类型，尝试转换
                        print(f"警告：字段 '{key}' 不是字符串类型 ({dtype})，无法保存文本标注")
                        return False

                except Exception as frame_error:
                    print(f"设置帧 {frame} 失败: {frame_error}")
                    return False

            print(f"成功设置 {key} 帧 {start_frame}-{end_frame}: {description}")

            # 更新缓存 - 修复bug：确保缓存字典中的key存在
            if key not in self.languages:
                self.languages[key] = {}
            self.languages[key][(start_frame, end_frame)] = description

            # 确保数据写入文件
            self.file.flush()

            return True

        except Exception as e:
            print(f"设置 {key} 失败: {e}")
            return False
    
    def set_string_key_for_all_frames(self, key_name: str, value: str) -> bool:
        """
        为所有帧设置指定的字符串键值
        
        Args:
            key_name: 键名称
            value: 要设置的字符串值
            
        Returns:
            是否设置成功
        """
        try:
            frame_count = self.get_frame_count()
            if frame_count == 0:
                print("文件中没有帧数据")
                return False
            
            # 如果键已存在，询问是否覆盖
            if key_name in self.file:
                print(f"键 '{key_name}' 已存在，将被覆盖")
                del self.file[key_name]
            
            # 编码值为bytes
            value_bytes = value.encode('utf-8')
            
            # 创建新的数据集
            # 使用可变长度字符串类型
            string_dtype = h5py.special_dtype(vlen=str)
            
            try:
                # 尝试使用字符串类型
                dataset = self.file.create_dataset(
                    key_name,
                    (frame_count,),
                    dtype=string_dtype,
                    fillvalue=""
                )
                
                # 设置所有帧的值
                for i in range(frame_count):
                    dataset[i] = value
                    
                print(f"成功创建字符串键 '{key_name}' 并设置所有 {frame_count} 帧为: '{value}'")
                
            except Exception as e:
                print(f"使用字符串类型失败，尝试使用字节类型: {e}")
                
                # 如果字符串类型失败，使用字节类型
                max_len = max(50, len(value_bytes) + 10)  # 预留一些空间
                dataset = self.file.create_dataset(
                    key_name,
                    (frame_count, 1),
                    dtype=f'S{max_len}',
                    fillvalue=b''
                )
                
                # 设置所有帧的值
                for i in range(frame_count):
                    dataset[i, 0] = value_bytes
                    
                print(f"成功创建字节键 '{key_name}' 并设置所有 {frame_count} 帧为: '{value}'")
            
            # 确保数据写入文件
            self.file.flush()
            
            return True
            
        except Exception as e:
            print(f"设置字符串键失败: {e}")
            return False
    
    def get_languages_for_key(self, key: str) -> Dict[Tuple[int, int], str]:
        """
        获取指定键的所有language段
        
        Args:
            key: 键名
            
        Returns:
            所有language段，格式为{(start_idx, end_idx): description}
        """
        # 如果缓存中已经有这个key的数据，直接返回缓存
        if key in self.languages:
            return self.languages[key].copy()
        
        # 对于新键，需要动态加载
        languages = {}
        
        if key not in self.file:
            return languages
        
        try:
            language_data = self.file[key]
            print(f"加载{key}数据集，形状: {language_data.shape}, 类型: {language_data.dtype}")
            
            # 遍历所有帧，标记已有的language
            current_task = None
            start_idx = None
            
            for i in range(self.frame_count):
                # 处理编码，确保可以正确处理中文
                try:
                    if i < language_data.shape[0]:
                        # 尝试直接获取字符串
                        if len(language_data.shape) == 1:
                            # 一维数组
                            task_value = language_data[i]
                        else:
                            # 二维数组
                            task_value = language_data[i, 0] if language_data.shape[1] > 0 else ""
                        
                        # 处理可能的字节对象
                        if isinstance(task_value, bytes):
                            task = task_value.decode('utf-8', errors='replace')
                        elif isinstance(task_value, str):
                            task = task_value
                        elif isinstance(task_value, (int, float)):
                            task = str(task_value)
                        else:
                            task = str(task_value)
                        
                        # 去除前后空白
                        task = task.strip()
                        
                        # 处理特殊格式，如果显示为 b'...'
                        if task.startswith("b'") and task.endswith("'"):
                            try:
                                task = task[2:-1]
                            except:
                                pass
                    else:
                        task = ""
                except Exception as e:
                    print(f"解码帧 {i} 的{key}时出错: {e}")
                    task = ""
                
                if task and task != "0" and task != 0:  # 忽略空值和0值
                    if current_task is None or task != current_task:
                        # 新任务开始或任务变更
                        if current_task is not None and start_idx is not None:
                            # 保存上一个任务
                            languages[(start_idx, i - 1)] = current_task
                        
                        current_task = task
                        start_idx = i
                    # 若任务未变更，继续追踪当前任务，无需操作
                elif current_task is not None:
                    # 任务结束
                    if start_idx is not None:
                        languages[(start_idx, i - 1)] = current_task
                    current_task = None
                    start_idx = None
            
            # 保存最后一个任务
            if current_task is not None and start_idx is not None:
                languages[(start_idx, self.frame_count - 1)] = current_task
                
            # 打印加载的language信息
            print(f"加载了 {len(languages)} 个{key}段")
            for (start, end), desc in languages.items():
                print(f"{key}段: {start}-{end}, 描述: '{desc}'")
            
            # 将加载的数据缓存起来
            self.languages[key] = languages
                
        except Exception as e:
            print(f"加载{key}数据时出错: {e}")
        
        return languages 