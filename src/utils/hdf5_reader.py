# -*- coding: utf-8 -*-
import h5py
import numpy as np
from typing import Dict, List, Any, Tuple, Optional, Union


class HDF5Reader:
    """用于读取HDF5文件的工具类"""
    
    def __init__(self, file_path: str):
        """
        初始化HDF5Reader
        
        Args:
            file_path: HDF5文件路径
        """
        self.file_path = file_path
        self.file = None
        self.open_file()
        
    def open_file(self):
        """打开HDF5文件"""
        try:
            self.file = h5py.File(self.file_path, 'r+')
        except Exception as e:
            print(f"打开文件失败: {e}")
            raise
            
    def close_file(self):
        """关闭HDF5文件"""
        if self.file:
            self.file.close()
            self.file = None
            
    def __enter__(self):
        """支持with语句"""
        if not self.file:
            self.open_file()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句自动关闭文件"""
        self.close_file()
    
    def get_keys(self) -> List[str]:
        """
        获取HDF5文件的所有顶级键
        
        Returns:
            包含所有顶级键的列表
        """
        return list(self.file.keys())
    
    def get_all_keys(self, include_groups: bool = True) -> List[str]:
        """
        递归获取HDF5文件中的所有键
        
        Args:
            include_groups: 是否包含组键
            
        Returns:
            包含所有键的列表
        """
        keys = []
        
        def visit_item(name, obj):
            if include_groups or isinstance(obj, h5py.Dataset):
                keys.append(name)
        
        self.file.visititems(visit_item)
        return keys
    
    def get_image_keys(self) -> List[str]:
        """
        获取所有图像数据集的键
        
        Returns:
            包含所有图像数据集键的列表
        """
        image_keys = []
        
        def is_image_dataset(dataset):
            # 图像数据集通常是3D或4D数组，最后一维是通道数(通常为3或4)
            return (len(dataset.shape) >= 3 and 
                    (dataset.shape[-1] == 3 or dataset.shape[-1] == 4) and
                    dataset.dtype in [np.uint8, np.int8])
        
        def visit_item(name, obj):
            if isinstance(obj, h5py.Dataset) and is_image_dataset(obj):
                image_keys.append(name)
        
        self.file.visititems(visit_item)
        return image_keys
    
    def get_dataset_info(self, key: str) -> Dict[str, Any]:
        """
        获取数据集的信息
        
        Args:
            key: 数据集的键
            
        Returns:
            包含数据集信息的字典
        """
        dataset = self.file[key]
        return {
            'shape': dataset.shape,
            'dtype': str(dataset.dtype),
            'size': dataset.size,
            'dims': len(dataset.shape)
        }
    
    def get_data(self, key: str, index: Optional[int] = None) -> np.ndarray:
        """
        获取数据集的数据
        
        Args:
            key: 数据集的键
            index: 如果数据集是多维的，可以指定索引
            
        Returns:
            数据集的值
        """
        dataset = self.file[key]
        
        if index is not None and len(dataset.shape) > 1:
            return dataset[index]
        else:
            return dataset[()]
            
    def set_subtask(self, start_idx: int, end_idx: int, description: str):
        """
        设置一段帧的subtask描述
        
        Args:
            start_idx: 起始帧索引
            end_idx: 结束帧索引
            description: subtask描述
        """
        if 'subtask' not in self.file:
            # 如果subtask不存在，创建它
            frame_count = self.get_frame_count()
            self.file.create_dataset('subtask', (frame_count, 1), dtype=h5py.string_dtype(encoding='utf-8'))
        
        # 确保索引在有效范围内
        subtask_data = self.file['subtask']
        frame_count = subtask_data.shape[0]
        
        start_idx = max(0, min(start_idx, frame_count - 1))
        end_idx = max(0, min(end_idx, frame_count - 1))
        
        # 设置subtask描述
        for i in range(start_idx, end_idx + 1):
            subtask_data[i] = description
    
    def get_frame_count(self) -> int:
        """
        获取帧数
        
        Returns:
            文件中的帧数
        """
        # 通常使用第一个带有帧维度的数据集来确定总帧数
        for key in self.get_keys():
            dataset = self.file[key]
            if isinstance(dataset, h5py.Dataset) and len(dataset.shape) > 0:
                return dataset.shape[0]
        
        # 如果没有找到适合的数据集，返回0
        return 0 