"""手术室资源冲突预测系统 - 数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class AnesthesiaType(Enum):
    """麻醉方式枚举"""
    GENERAL = "全身麻醉"
    REGIONAL = "区域麻醉"
    LOCAL = "局部麻醉"
    SPINAL = "椎管内麻醉"
    NERVE_BLOCK = "神经阻滞麻醉"
    IV = "静脉麻醉"
    INHALATION = "吸入麻醉"
    COMBINED = "复合麻醉"
    UNKNOWN = "未知"


@dataclass
class Equipment:
    """器械类"""
    equipment_id: str
    name: str
    category: str  # 手术器械、麻醉设备、监护设备等
    department: str = ""
    status: str = "available"  # available, in_use, maintenance, retired


@dataclass
class SurgeryRecord:
    """手术记录"""
    surgery_id: str
    patient_id: str
    surgery_name: str
    surgery_type: str  # 普外科、骨科、神经外科等
    department: str  # 手术科室
    surgeon: str  # 主刀医生
    surgeon_assistants: List[str] = field(default_factory=list)  # 助手
    anesthesia_type: AnesthesiaType = AnesthesiaType.UNKNOWN
    equipment_needed: List[str] = field(default_factory=list)  # 需要的器械ID列表
    scheduled_duration: int = 0  # 计划时长（分钟）
    estimated_duration: int = 0  # 预估时长（分钟）
    actual_duration: Optional[int] = None  # 实际时长（分钟）
    scheduled_time: Optional[datetime] = None  # 计划开始时间
    operating_room: str = ""  # 手术室
    priority: int = 1  # 优先级 1-5
    notes: str = ""

    def __post_init__(self):
        if isinstance(self.anesthesia_type, str):
            for at in AnesthesiaType:
                if at.value == self.anesthesia_type:
                    self.anesthesia_type = at
                    break


@dataclass
class ConflictResult:
    """冲突检测结果"""
    conflict_id: str
    conflict_type: str  # equipment, anesthesia, surgeon, room, time
    description: str
    severity: str = "medium"  # low, medium, high, critical
    surgeries_involved: List[str] = field(default_factory=list)  # 涉及手术ID列表
    equipment_involved: List[str] = field(default_factory=list)  # 涉及器械ID列表
    time_overlap_start: Optional[datetime] = None
    time_overlap_end: Optional[datetime] = None
    resolution_suggestion: str = ""  # 解决建议
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type,
            "severity": self.severity,
            "description": self.description,
            "surgeries_involved": self.surgeries_involved,
            "equipment_involved": self.equipment_involved,
            "time_overlap_start": self.time_overlap_start.isoformat() if self.time_overlap_start else None,
            "time_overlap_end": self.time_overlap_end.isoformat() if self.time_overlap_end else None,
            "resolution_suggestion": self.resolution_suggestion,
            "detected_at": self.detected_at.isoformat()
        }


@dataclass
class PredictionResult:
    """预测结果"""
    surgery_id: str
    predicted_duration: float  # 预测时长（分钟）
    confidence_interval_low: float
    confidence_interval_high: float
    confidence_level: float  # 置信度 0-1
    features_used: List[str] = field(default_factory=list)
    model_version: str = "v1.0"

    def to_dict(self) -> dict:
        return {
            "surgery_id": self.surgery_id,
            "predicted_duration": self.predicted_duration,
            "confidence_interval": [self.confidence_interval_low, self.confidence_interval_high],
            "confidence_level": self.confidence_level,
            "features_used": self.features_used,
            "model_version": self.model_version
        }