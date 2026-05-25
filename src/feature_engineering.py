"""手术室资源冲突预测系统 - 特征工程模块"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.models import SurgeryRecord, AnesthesiaType


class FeatureEngineering:
    """特征工程类 - 从手术记录中提取特征"""

    def __init__(self):
        self.surgeon_stats: Dict[str, Dict[str, float]] = {}
        self.department_stats: Dict[str, Dict[str, float]] = {}
        self.surgery_type_stats: Dict[str, Dict[str, float]] = {}
        self.anesthesia_stats: Dict[str, Dict[str, float]] = {}
        self._is_fitted = False

    def fit(self, records: List[SurgeryRecord]) -> 'FeatureEngineering':
        """根据历史数据拟合统计信息"""
        if not records:
            return self

        df = self._records_to_dataframe(records)

        # 计算主刀医生统计
        surgeon_groups = df.groupby('surgeon')['actual_duration'].agg(['mean', 'std', 'count'])
        self.surgeon_stats = {
            row.name: {'mean': row['mean'], 'std': row['std'] if pd.notna(row['std']) else 30, 'count': row['count']}
            for _, row in surgeon_groups.iterrows()
        }

        # 计算科室统计
        dept_groups = df.groupby('department')['actual_duration'].agg(['mean', 'std', 'count'])
        self.department_stats = {
            row.name: {'mean': row['mean'], 'std': row['std'] if pd.notna(row['std']) else 30, 'count': row['count']}
            for _, row in dept_groups.iterrows()
        }

        # 计算手术类型统计
        type_groups = df.groupby('surgery_name')['actual_duration'].agg(['mean', 'std', 'count'])
        self.surgery_type_stats = {
            row.name: {'mean': row['mean'], 'std': row['std'] if pd.notna(row['std']) else 30, 'count': row['count']}
            for _, row in type_groups.iterrows()
        }

        # 计算麻醉方式统计
        anesthesia_groups = df.groupby('anesthesia_type')['actual_duration'].agg(['mean', 'std', 'count'])
        self.anesthesia_stats = {
            row.name: {'mean': row['mean'], 'std': row['std'] if pd.notna(row['std']) else 30, 'count': row['count']}
            for _, row in anesthesia_groups.iterrows()
        }

        self._is_fitted = True
        return self

    def transform(self, records: List[SurgeryRecord]) -> pd.DataFrame:
        """将手术记录转换为特征 DataFrame"""
        if not records:
            return pd.DataFrame()

        df = self._records_to_dataframe(records)
        features = pd.DataFrame()

        # 基础特征
        features['scheduled_duration'] = df['scheduled_duration']
        features['priority'] = df['priority']

        # 手术类型特征 (one-hot)
        surgery_type_dummies = pd.get_dummies(df['surgery_name'], prefix='surgery_type')
        features = pd.concat([features, surgery_type_dummies], axis=1)

        # 科室特征 (one-hot)
        department_dummies = pd.get_dummies(df['department'], prefix='department')
        features = pd.concat([features, department_dummies], axis=1)

        # 主刀医生特征
        features['surgeon_avg_duration'] = df['surgeon'].map(
            lambda x: self.surgeon_stats.get(x, {}).get('mean', 120) if self._is_fitted else 120
        )
        features['surgeon_std_duration'] = df['surgeon'].map(
            lambda x: self.surgeon_stats.get(x, {}).get('std', 30) if self._is_fitted else 30
        )
        features['surgeon_experience'] = df['surgeon'].map(
            lambda x: self.surgeon_stats.get(x, {}).get('count', 1) if self._is_fitted else 1
        )

        # 麻醉方式特征
        features['anesthesia_avg_duration'] = df['anesthesia_type'].map(
            lambda x: self.anesthesia_stats.get(x, {}).get('mean', 90) if self._is_fitted else 90
        )
        features['anesthesia_type_encoded'] = df['anesthesia_type'].map(self._encode_anesthesia)

        # 时段特征
        features['hour_of_day'] = df['scheduled_time'].map(
            lambda x: x.hour if isinstance(x, datetime) else 10
        )
        features['day_of_week'] = df['scheduled_time'].map(
            lambda x: x.weekday() if isinstance(x, datetime) else 0
        )
        features['is_morning'] = features['hour_of_day'].map(lambda x: 1 if 8 <= x < 12 else 0)
        features['is_afternoon'] = features['hour_of_day'].map(lambda x: 1 if 12 <= x < 17 else 0)

        # 交叉特征
        features['surgeon_dept_interaction'] = df['surgeon'].map(
            lambda x: hash(x) % 100
        ) + df['department'].map(lambda x: hash(x) % 100)

        # 器械数量特征
        features['equipment_count'] = df['equipment_needed'].map(len)

        # 助手数量特征
        features['assistant_count'] = df['assistant_count']

        return features

    def fit_transform(self, records: List[SurgeryRecord]) -> pd.DataFrame:
        """拟合并转换"""
        self.fit(records)
        return self.transform(records)

    def _records_to_dataframe(self, records: List[SurgeryRecord]) -> pd.DataFrame:
        """将手术记录列表转换为 DataFrame"""
        data = []
        for r in records:
            data.append({
                'surgery_id': r.surgery_id,
                'surgery_name': r.surgery_name,
                'surgery_type': r.surgery_type,
                'department': r.department,
                'surgeon': r.surgeon,
                'anesthesia_type': r.anesthesia_type.value if isinstance(r.anesthesia_type, AnesthesiaType) else str(r.anesthesia_type),
                'scheduled_duration': r.scheduled_duration,
                'estimated_duration': r.estimated_duration,
                'actual_duration': r.actual_duration or r.scheduled_duration,
                'scheduled_time': r.scheduled_time or datetime.now(),
                'operating_room': r.operating_room,
                'priority': r.priority,
                'equipment_needed': r.equipment_needed,
                'assistant_count': len(r.surgeon_assistants)
            })
        return pd.DataFrame(data)

    def _encode_anesthesia(self, anesthesia_str: str) -> int:
        """编码麻醉方式"""
        encoding_map = {
            '全身麻醉': 7, '复合麻醉': 6, '椎管内麻醉': 5,
            '区域麻醉': 4, '神经阻滞麻醉': 3, '静脉麻醉': 2,
            '吸入麻醉': 1, '局部麻醉': 0, '未知': 0
        }
        return encoding_map.get(anesthesia_str, 0)

    def get_feature_names(self) -> List[str]:
        """获取特征名称列表"""
        return [
            'scheduled_duration', 'priority', 'surgeon_avg_duration',
            'surgeon_std_duration', 'surgeon_experience', 'anesthesia_avg_duration',
            'anesthesia_type_encoded', 'hour_of_day', 'day_of_week',
            'is_morning', 'is_afternoon', 'surgeon_dept_interaction',
            'equipment_count', 'assistant_count'
        ]


def extract_features(records: List[SurgeryRecord], fit: bool = True) -> pd.DataFrame:
    """便捷函数：提取特征

    Args:
        records: 手术记录列表
        fit: 是否用数据拟合统计信息

    Returns:
        特征 DataFrame
    """
    fe = FeatureEngineering()
    if fit:
        return fe.fit_transform(records)
    return fe.transform(records)