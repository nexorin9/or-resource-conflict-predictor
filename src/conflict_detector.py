"""手术室资源冲突预测系统 - 冲突检测引擎"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from src.models import ConflictResult, SurgeryRecord


class ConflictDetector:
    """手术室资源冲突检测器"""

    def __init__(self):
        self.conflicts: List[ConflictResult] = []

    def detect_all(
        self,
        surgeries: List[SurgeryRecord],
        equipment_map: Optional[Dict[str, List[str]]] = None
    ) -> List[ConflictResult]:
        """检测所有类型的冲突

        Args:
            surgeries: 手术记录列表
            equipment_map: 器械归属映射 {手术ID: [器械ID列表]}

        Returns:
            冲突列表
        """
        self.conflicts = []

        # 按时间排序
        sorted_surgeries = sorted(
            surgeries,
            key=lambda s: s.scheduled_time or datetime.now()
        )

        # 检测各类冲突
        self._detect_equipment_conflicts(sorted_surgeries, equipment_map or {})
        self._detect_anesthesia_conflicts(sorted_surgeries)
        self._detect_surgeon_conflicts(sorted_surgeries)
        self._detect_room_conflicts(sorted_surgeries)
        self._detect_time_overlap_conflicts(sorted_surgeries)

        # 按严重程度排序
        return self._sort_by_severity(self.conflicts)

    def _detect_equipment_conflicts(
        self,
        surgeries: List[SurgeryRecord],
        equipment_map: Dict[str, List[str]]
    ) -> None:
        """检测器械冲突"""
        # 按器械分组，同一时段使用同一器械的手术
        equipment_usage: Dict[str, List[Tuple[SurgeryRecord, datetime, datetime]]] = {}

        for surgery in surgeries:
            if not surgery.scheduled_time:
                continue

            start = surgery.scheduled_time
            end = start + timedelta(minutes=surgery.estimated_duration or 120)

            equipment_ids = equipment_map.get(surgery.surgery_id, surgery.equipment_needed)

            for eq_id in equipment_ids:
                if eq_id not in equipment_usage:
                    equipment_usage[eq_id] = []
                equipment_usage[eq_id].append((surgery, start, end))

        # 检测同一器械的时间重叠
        for eq_id, usages in equipment_usage.items():
            for i in range(len(usages)):
                for j in range(i + 1, len(usages)):
                    surgery_i, start_i, end_i = usages[i]
                    surgery_j, start_j, end_j = usages[j]

                    # 检查时间重叠
                    overlap = self._calculate_overlap(start_i, end_i, start_j, end_j)
                    if overlap > timedelta(minutes=0):
                        conflict = ConflictResult(
                            conflict_id=f"EQ_{eq_id}_{surgery_i.surgery_id}_{surgery_j.surgery_id}",
                            conflict_type="equipment",
                            description=f"器械 {eq_id} 在 {overlap.total_seconds() / 60:.0f} 分钟内被同时预约",
                            severity=self._calculate_severity(overlap, 30),
                            surgeries_involved=[surgery_i.surgery_id, surgery_j.surgery_id],
                            equipment_involved=[eq_id],
                            time_overlap_start=max(start_i, start_j),
                            time_overlap_end=min(end_i, end_j),
                            resolution_suggestion=f"建议将手术 {surgery_j.surgery_id} 调整至 {surgery_i.surgery_id} 之后"
                        )
                        self.conflicts.append(conflict)

    def _detect_anesthesia_conflicts(
        self,
        surgeries: List[SurgeryRecord]
    ) -> None:
        """检测麻醉设备冲突"""
        # 需要麻醉设备的手术：全身麻醉、区域麻醉等
        anesthesia_types = {
            'GENERAL', 'REGIONAL', 'SPINAL', 'NERVE_BLOCK', 'COMBINED'
        }

        # 按手术室分组
        or_surgeries: Dict[str, List[Tuple[SurgeryRecord, datetime, datetime]]] = {}

        for surgery in surgeries:
            if not surgery.scheduled_time:
                continue
            if surgery.anesthesia_type.value not in anesthesia_types:
                continue

            start = surgery.scheduled_time
            end = start + timedelta(minutes=surgery.estimated_duration or 120)

            or_id = surgery.operating_room or "OR_UNKNOWN"
            if or_id not in or_surgeries:
                or_surgeries[or_id] = []
            or_surgeries[or_id].append((surgery, start, end))

        # 检测同一手术室内麻醉准备时间冲突
        for or_id, usages in or_surgeries.items():
            for i in range(len(usages)):
                for j in range(i + 1, len(usages)):
                    surgery_i, start_i, end_i = usages[i]
                    surgery_j, start_j, end_j = usages[j]

                    # 需要清洁/准备时间（假设15分钟）
                    prep_time = timedelta(minutes=15)
                    overlap = self._calculate_overlap(
                        end_i + prep_time, end_i + prep_time + timedelta(minutes=10),
                        start_j, end_j
                    )

                    if overlap > timedelta(minutes=0):
                        conflict = ConflictResult(
                            conflict_id=f"ANES_{or_id}_{surgery_i.surgery_id}_{surgery_j.surgery_id}",
                            conflict_type="anesthesia",
                            description=f"手术室 {or_id} 在麻醉设备准备时间上冲突",
                            severity="medium",
                            surgeries_involved=[surgery_i.surgery_id, surgery_j.surgery_id],
                            time_overlap_start=max(end_i + prep_time, start_j),
                            time_overlap_end=min(end_i + prep_time + timedelta(minutes=10), end_j),
                            resolution_suggestion=f"建议 {surgery_j.surgery_id} 延后 {prep_time.total_seconds() / 60:.0f} 分钟开始"
                        )
                        self.conflicts.append(conflict)

    def _detect_surgeon_conflicts(
        self,
        surgeries: List[SurgeryRecord]
    ) -> None:
        """检测主刀时间冲突"""
        surgeon_schedules: Dict[str, List[Tuple[SurgeryRecord, datetime, datetime]]] = {}

        for surgery in surgeries:
            if not surgery.scheduled_time or not surgery.surgeon:
                continue

            start = surgery.scheduled_time
            end = start + timedelta(minutes=surgery.estimated_duration or 120)

            surgeon = surgery.surgeon
            if surgeon not in surgeon_schedules:
                surgeon_schedules[surgeon] = []
            surgeon_schedules[surgeon].append((surgery, start, end))

        # 检测同一主刀的时间重叠
        for surgeon, usages in surgeon_schedules.items():
            for i in range(len(usages)):
                for j in range(i + 1, len(usages)):
                    surgery_i, start_i, end_i = usages[i]
                    surgery_j, start_j, end_j = usages[j]

                    overlap = self._calculate_overlap(start_i, end_i, start_j, end_j)
                    if overlap > timedelta(minutes=0):
                        severity = "critical" if overlap.total_seconds() / 60 > 30 else "high"
                        conflict = ConflictResult(
                            conflict_id=f"SURG_{surgeon}_{surgery_i.surgery_id}_{surgery_j.surgery_id}",
                            conflict_type="surgeon",
                            description=f"主刀医生 {surgeon} 在 {overlap.total_seconds() / 60:.0f} 分钟内被安排两台手术",
                            severity=severity,
                            surgeries_involved=[surgery_i.surgery_id, surgery_j.surgery_id],
                            time_overlap_start=max(start_i, start_j),
                            time_overlap_end=min(end_i, end_j),
                            resolution_suggestion=f"建议将 {surgery_j.surgery_id} 调整到 {surgery_i.surgery_id} 结束之后"
                        )
                        self.conflicts.append(conflict)

    def _detect_room_conflicts(
        self,
        surgeries: List[SurgeryRecord]
    ) -> None:
        """检测手术室冲突"""
        or_schedules: Dict[str, List[Tuple[SurgeryRecord, datetime, datetime]]] = {}

        for surgery in surgeries:
            if not surgery.scheduled_time:
                continue

            start = surgery.scheduled_time
            end = start + timedelta(minutes=surgery.estimated_duration or 120)

            or_id = surgery.operating_room or "OR_UNKNOWN"
            if or_id not in or_schedules:
                or_schedules[or_id] = []
            or_schedules[or_id].append((surgery, start, end))

        # 检测同一手术室时间重叠
        for or_id, usages in or_schedules.items():
            for i in range(len(usages)):
                for j in range(i + 1, len(usages)):
                    surgery_i, start_i, end_i = usages[i]
                    surgery_j, start_j, end_j = usages[j]

                    overlap = self._calculate_overlap(start_i, end_i, start_j, end_j)
                    if overlap > timedelta(minutes=0):
                        conflict = ConflictResult(
                            conflict_id=f"ROOM_{or_id}_{surgery_i.surgery_id}_{surgery_j.surgery_id}",
                            conflict_type="room",
                            description=f"手术室 {or_id} 在时间段重叠",
                            severity="critical" if overlap.total_seconds() / 60 > 15 else "high",
                            surgeries_involved=[surgery_i.surgery_id, surgery_j.surgery_id],
                            time_overlap_start=max(start_i, start_j),
                            time_overlap_end=min(end_i, end_j),
                            resolution_suggestion=f"建议将其中一台手术调整到其他手术室"
                        )
                        self.conflicts.append(conflict)

    def _detect_time_overlap_conflicts(
        self,
        surgeries: List[SurgeryRecord]
    ) -> None:
        """检测时间过度紧凑冲突（手术间隔不足）"""
        for i in range(len(surgeries)):
            for j in range(i + 1, len(surgeries)):
                surgery_i = surgeries[i]
                surgery_j = surgeries[j]

                if not surgery_i.scheduled_time or not surgery_j.scheduled_time:
                    continue
                if surgery_i.operating_room != surgery_j.operating_room:
                    continue

                end_i = surgery_i.scheduled_time + timedelta(minutes=surgery_i.estimated_duration or 120)
                start_j = surgery_j.scheduled_time

                gap = (start_j - end_i).total_seconds() / 60  # 分钟

                # 假设最小间隔需要20分钟（整理、消毒等）
                if 0 < gap < 20:
                    conflict = ConflictResult(
                        conflict_id=f"TIME_{surgery_i.surgery_id}_{surgery_j.surgery_id}",
                        conflict_type="time",
                        description=f"手术室 {surgery_i.operating_room} 连续手术间隔仅 {gap:.0f} 分钟，可能准备不足",
                        severity="medium" if gap >= 10 else "high",
                        surgeries_involved=[surgery_i.surgery_id, surgery_j.surgery_id],
                        time_overlap_start=end_i,
                        time_overlap_end=start_j,
                        resolution_suggestion=f"建议在 {surgery_i.surgery_id} 和 {surgery_j.surgery_id} 之间预留足够间隔"
                    )
                    self.conflicts.append(conflict)

    def _calculate_overlap(
        self,
        start1: datetime,
        end1: datetime,
        start2: datetime,
        end2: datetime
    ) -> timedelta:
        """计算两个时间段的 overlap"""
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)

        if overlap_start < overlap_end:
            return overlap_end - overlap_start
        return timedelta(0)

    def _calculate_severity(self, overlap: timedelta, threshold_minutes: int) -> str:
        """根据重叠时长计算严重程度"""
        overlap_minutes = overlap.total_seconds() / 60

        if overlap_minutes > 60:
            return "critical"
        elif overlap_minutes > 30:
            return "high"
        elif overlap_minutes > 15:
            return "medium"
        return "low"

    def _sort_by_severity(self, conflicts: List[ConflictResult]) -> List[ConflictResult]:
        """按严重程度排序"""
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        return sorted(
            conflicts,
            key=lambda c: (
                severity_order.get(c.severity, 4),
                len(c.surgeries_involved),
                -(c.time_overlap_end - c.time_overlap_start).total_seconds() if c.time_overlap_end and c.time_overlap_start else 0
            )
        )

    def get_conflicts_by_type(self, conflicts: List[ConflictResult], conflict_type: str) -> List[ConflictResult]:
        """按类型筛选冲突"""
        return [c for c in conflicts if c.conflict_type == conflict_type]

    def get_conflicts_by_surgery(self, conflicts: List[ConflictResult], surgery_id: str) -> List[ConflictResult]:
        """按手术ID筛选冲突"""
        return [c for c in conflicts if surgery_id in c.surgeries_involved]

    def get_summary(self, conflicts: List[ConflictResult]) -> Dict[str, int]:
        """获取冲突摘要统计"""
        summary = {
            "total": len(conflicts),
            "critical": len([c for c in conflicts if c.severity == "critical"]),
            "high": len([c for c in conflicts if c.severity == "high"]),
            "medium": len([c for c in conflicts if c.severity == "medium"]),
            "low": len([c for c in conflicts if c.severity == "low"]),
            "equipment": len([c for c in conflicts if c.conflict_type == "equipment"]),
            "anesthesia": len([c for c in conflicts if c.conflict_type == "anesthesia"]),
            "surgeon": len([c for c in conflicts if c.conflict_type == "surgeon"]),
            "room": len([c for c in conflicts if c.conflict_type == "room"]),
            "time": len([c for c in conflicts if c.conflict_type == "time"])
        }
        return summary