"""手术室资源冲突预测系统 - 数据加载模块"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Optional

import pandas as pd

from src.models import SurgeryRecord, AnesthesiaType


class DataLoader:
    """数据加载器基类"""

    def load(self, file_path: str) -> List[SurgeryRecord]:
        raise NotImplementedError


class CSVLoader(DataLoader):
    """CSV 格式数据加载器"""

    def load(self, file_path: str) -> List[SurgeryRecord]:
        """从 CSV 文件加载手术记录"""
        records = []
        df = pd.read_csv(file_path)

        for _, row in df.iterrows():
            try:
                # 解析麻醉方式
                anesthesia_str = row.get('anesthesia_type', '未知')
                anesthesia_type = AnesthesiaType.UNKNOWN
                for at in AnesthesiaType:
                    if at.value == anesthesia_str or at.name == anesthesia_str:
                        anesthesia_type = at
                        break

                # 解析时间
                scheduled_time = None
                if pd.notna(row.get('scheduled_time')):
                    try:
                        scheduled_time = pd.to_datetime(row['scheduled_time'])
                    except Exception:
                        pass

                # 解析器械列表
                equipment_needed = []
                if pd.notna(row.get('equipment_needed')):
                    equipment_str = str(row['equipment_needed'])
                    if equipment_str and equipment_str != 'nan':
                        equipment_needed = [e.strip() for e in equipment_str.split(',')]

                # 解析助手列表
                surgeon_assistants = []
                if pd.notna(row.get('surgeon_assistants')):
                    assistants_str = str(row['surgeon_assistants'])
                    if assistants_str and assistants_str != 'nan':
                        surgeon_assistants = [a.strip() for a in assistants_str.split(',')]

                record = SurgeryRecord(
                    surgery_id=str(row['surgery_id']),
                    patient_id=str(row['patient_id']),
                    surgery_name=str(row['surgery_name']),
                    surgery_type=str(row['surgery_type']),
                    department=str(row['department']),
                    surgeon=str(row['surgeon']),
                    surgeon_assistants=surgeon_assistants,
                    anesthesia_type=anesthesia_type,
                    equipment_needed=equipment_needed,
                    scheduled_duration=int(row.get('scheduled_duration', 0)),
                    estimated_duration=int(row.get('estimated_duration', 0)),
                    actual_duration=int(row['actual_duration']) if pd.notna(row.get('actual_duration')) else None,
                    scheduled_time=scheduled_time,
                    operating_room=str(row.get('operating_room', '')),
                    priority=int(row.get('priority', 1)),
                    notes=str(row.get('notes', ''))
                )
                records.append(record)
            except Exception as e:
                print(f"警告: 解析第 {len(records) + 1} 条记录时出错: {e}")
                continue

        return records


class ExcelLoader(DataLoader):
    """Excel 格式数据加载器"""

    def load(self, file_path: str, sheet_name: Optional[str] = None) -> List[SurgeryRecord]:
        """从 Excel 文件加载手术记录"""
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            df = pd.read_excel(file_path)
        # 转换为 CSV 格式处理
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            df.to_csv(f.name, index=False, encoding='utf-8')
            csv_path = f.name
        try:
            records = CSVLoader().load(csv_path)
        finally:
            os.unlink(csv_path)
        return records


class MockDataGenerator:
    """模拟数据生成器"""

    # 科室列表
    DEPARTMENTS = ['普外科', '骨科', '神经外科', '心外科', '泌尿外科', '胸外科', '妇产科', '眼科', '耳鼻喉科', '口腔科']

    # 手术类型
    SURGERY_TYPES = {
        '普外科': ['胆囊切除术', '阑尾切除术', '疝修补术', '胃切除术', '结肠切除术'],
        '骨科': ['骨折内固定术', '关节置换术', '脊柱手术', '韧带修复术', '骨肿瘤切除术'],
        '神经外科': ['颅内血肿清除术', '脑肿瘤切除术', '脑血管畸形手术', '脊髓手术', '癫痫手术'],
        '心外科': ['心脏搭桥术', '心脏瓣膜置换术', '先天性心脏病手术', '主动脉手术', '心包手术'],
        '泌尿外科': ['肾切除术', '膀胱手术', '前列腺手术', '输尿管手术', '结石取出术'],
        '胸外科': ['肺叶切除术', '食管手术', '纵隔手术', '胸壁手术', '胸腔镜手术'],
        '妇产科': ['子宫切除术', '卵巢手术', '剖宫产术', '人流手术', '妇科肿瘤手术'],
        '眼科': ['白内障手术', '青光眼手术', '视网膜手术', '斜视手术', '眼睑手术'],
        '耳鼻喉科': ['鼻窦炎手术', '扁桃体切除术', '喉部手术', '中耳手术', '眩晕手术'],
        '口腔科': ['拔牙术', '口腔肿瘤手术', '颌面手术', '牙种植术', '唇腭裂手术']
    }

    # 主刀医生
    SURGEONS = [
        '张伟', '李娜', '王强', '刘芳', '陈军', '赵敏', '黄磊', '周涛', '吴静', '郑鑫',
        '孙超', '钱伟', '冯雪', '董琳', '曹鹏', '彭飞', '蒋欢', '蔡明', '余倩', '谢华'
    ]

    # 麻醉方式
    ANESTHESIA_TYPES = [
        (AnesthesiaType.GENERAL, 40),
        (AnesthesiaType.SPINAL, 20),
        (AnesthesiaType.REGIONAL, 15),
        (AnesthesiaType.IV, 10),
        (AnesthesiaType.NERVE_BLOCK, 8),
        (AnesthesiaType.COMBINED, 5),
        (AnesthesiaType.LOCAL, 2)
    ]

    # 手术室
    OPERATING_ROOMS = ['OR1', 'OR2', 'OR3', 'OR4', 'OR5', 'OR6', 'OR7', 'OR8']

    # 器械类别
    EQUIPMENT_CATEGORIES = [
        '手术器械', '麻醉设备', '监护设备', '腹腔镜设备', '电刀设备',
        '输血设备', '吸引设备', '手术灯', '手术床', '影像设备'
    ]

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def generate_surgeries(self, count: int = 100, start_date: Optional[datetime] = None) -> List[SurgeryRecord]:
        """生成模拟手术记录"""
        if start_date is None:
            start_date = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

        surgeries = []
        base_date = start_date

        for i in range(count):
            # 选择科室和手术类型
            department = random.choice(self.DEPARTMENTS)
            surgery_type = random.choice(self.SURGERY_TYPES.get(department, ['其他手术']))
            surgery_name = surgery_type

            # 选择主刀医生
            surgeon = random.choice(self.SURGEONS)

            # 选择麻醉方式
            anesthesia_type = self._weighted_choice(self.ANESTHESIA_TYPES)

            # 生成手术时长（基于科室和手术类型估算）
            base_duration = self._get_base_duration(surgery_type)
            scheduled_duration = base_duration + random.randint(-20, 30)
            estimated_duration = base_duration + random.randint(-15, 20)

            # 实际时长（用于训练数据）
            actual_duration = scheduled_duration + random.randint(-30, 45)

            # 计划时间（每天8:00-17:00）
            day_offset = i // 8  # 每天约8台手术
            slot = i % 8
            scheduled_time = base_date + timedelta(days=day_offset, hours=slot)

            # 手术室分配
            operating_room = random.choice(self.OPERATING_ROOMS)

            # 器械需求
            num_equipment = random.randint(2, 5)
            equipment_needed = [f"EQ{random.randint(1, 50):03d}" for _ in range(num_equipment)]

            # 助手
            num_assistants = random.randint(0, 2)
            assistants = []
            for _ in range(num_assistants):
                assistant = random.choice([s for s in self.SURGEONS if s != surgeon])
                if assistant not in assistants:
                    assistants.append(assistant)

            # 优先级
            priority = random.choices([1, 2, 3, 4, 5], weights=[60, 20, 10, 6, 4])[0]

            record = SurgeryRecord(
                surgery_id=f"S{i + 1:05d}",
                patient_id=f"P{random.randint(1, 5000):06d}",
                surgery_name=surgery_name,
                surgery_type=department,
                department=department,
                surgeon=surgeon,
                surgeon_assistants=assistants,
                anesthesia_type=anesthesia_type,
                equipment_needed=equipment_needed,
                scheduled_duration=scheduled_duration,
                estimated_duration=estimated_duration,
                actual_duration=actual_duration,
                scheduled_time=scheduled_time,
                operating_room=operating_room,
                priority=priority,
                notes=""
            )
            surgeries.append(record)

        return surgeries

    def generate_csv(self, file_path: str, count: int = 100):
        """生成 CSV 文件"""
        surgeries = self.generate_surgeries(count)

        data = []
        for s in surgeries:
            data.append({
                'surgery_id': s.surgery_id,
                'patient_id': s.patient_id,
                'surgery_name': s.surgery_name,
                'surgery_type': s.surgery_type,
                'department': s.department,
                'surgeon': s.surgeon,
                'surgeon_assistants': ','.join(s.surgeon_assistants),
                'anesthesia_type': s.anesthesia_type.value if isinstance(s.anesthesia_type, AnesthesiaType) else s.anesthesia_type,
                'equipment_needed': ','.join(s.equipment_needed),
                'scheduled_duration': s.scheduled_duration,
                'estimated_duration': s.estimated_duration,
                'actual_duration': s.actual_duration,
                'scheduled_time': s.scheduled_time.isoformat() if s.scheduled_time else '',
                'operating_room': s.operating_room,
                'priority': s.priority,
                'notes': s.notes
            })

        df = pd.DataFrame(data)
        df.to_csv(file_path, index=False, encoding='utf-8-sig')

    def _weighted_choice(self, choices: list) -> Any:
        """加权随机选择"""
        items, weights = zip(*choices)
        return random.choices(items, weights=weights, k=1)[0]

    def _get_base_duration(self, surgery_type: str) -> int:
        """根据手术类型获取基础时长（分钟）"""
        duration_map = {
            '胆囊切除术': 90, '阑尾切除术': 60, '疝修补术': 75, '胃切除术': 180, '结肠切除术': 150,
            '骨折内固定术': 120, '关节置换术': 150, '脊柱手术': 240, '韧带修复术': 120, '骨肿瘤切除术': 180,
            '颅内血肿清除术': 180, '脑肿瘤切除术': 300, '脑血管畸形手术': 360, '脊髓手术': 240, '癫痫手术': 300,
            '心脏搭桥术': 360, '心脏瓣膜置换术': 300, '先天性心脏病手术': 300, '主动脉手术': 360, '心包手术': 180,
            '肾切除术': 120, '膀胱手术': 90, '前列腺手术': 120, '输尿管手术': 90, '结石取出术': 60,
            '肺叶切除术': 180, '食管手术': 240, '纵隔手术': 150, '胸壁手术': 90, '胸腔镜手术': 90,
            '子宫切除术': 120, '卵巢手术': 90, '剖宫产术': 60, '人流手术': 30, '妇科肿瘤手术': 180,
            '白内障手术': 30, '青光眼手术': 60, '视网膜手术': 90, '斜视手术': 60, '眼睑手术': 45,
            '鼻窦炎手术': 60, '扁桃体切除术': 45, '喉部手术': 90, '中耳手术': 60, '眩晕手术': 120,
            '拔牙术': 30, '口腔肿瘤手术': 120, '颌面手术': 180, '牙种植术': 60, '唇腭裂手术': 120,
        }
        return duration_map.get(surgery_type, 90)


def load_surgeries(file_path: str) -> List[SurgeryRecord]:
    """便捷函数：根据文件扩展名自动选择加载器"""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == '.csv':
        return CSVLoader().load(file_path)
    elif suffix in ['.xlsx', '.xls']:
        return ExcelLoader().load(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}")