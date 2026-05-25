"""手术室资源冲突预测系统 - 报告生成模块"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.models import ConflictResult, PredictionResult, SurgeryRecord


class TextReportGenerator:
    """文本格式报告生成器"""

    def generate(
        self,
        surgeries: List[SurgeryRecord],
        predictions: List[PredictionResult],
        conflicts: List[ConflictResult],
        summary: Optional[Dict[str, int]] = None
    ) -> str:
        """生成文本报告

        Args:
            surgeries: 手术记录列表
            predictions: 预测结果列表
            conflicts: 冲突列表
            summary: 冲突统计摘要

        Returns:
            格式化的文本报告
        """
        lines = []
        lines.append("=" * 60)
        lines.append("手术室资源冲突预测报告")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")

        # 概要信息
        lines.append("【概要】")
        lines.append(f"  手术记录数: {len(surgeries)}")
        lines.append(f"  预测手术数: {len(predictions)}")
        lines.append(f"  检测冲突数: {len(conflicts)}")
        if summary:
            lines.append(f"  - 严重冲突: {summary.get('critical', 0)}")
            lines.append(f"  - 高风险冲突: {summary.get('high', 0)}")
            lines.append(f"  - 中风险冲突: {summary.get('medium', 0)}")
            lines.append(f"  - 低风险冲突: {summary.get('low', 0)}")
        lines.append("")

        # 冲突详情
        if conflicts:
            lines.append("【冲突详情】")
            for i, conflict in enumerate(conflicts, 1):
                lines.append(f"\n  [{i}] {conflict.conflict_id}")
                lines.append(f"      类型: {conflict.conflict_type}")
                lines.append(f"      严重程度: {conflict.severity}")
                lines.append(f"      说明: {conflict.description}")
                lines.append(f"      涉及手术: {', '.join(conflict.surgeries_involved)}")
                if conflict.time_overlap_start:
                    lines.append(f"      时间重叠: {conflict.time_overlap_start.strftime('%H:%M')} - {conflict.time_overlap_end.strftime('%H:%M') if conflict.time_overlap_end else '?'}")
                if conflict.resolution_suggestion:
                    lines.append(f"      建议: {conflict.resolution_suggestion}")
            lines.append("")

        # 预测摘要（按手术室分组）
        if predictions:
            lines.append("【手术时长预测摘要】")
            pred_dict = {p.surgery_id: p for p in predictions}
            or_surgeries: Dict[str, List[str]] = {}
            for s in surgeries:
                or_id = s.operating_room or "OR_UNKNOWN"
                if or_id not in or_surgeries:
                    or_surgeries[or_id] = []
                or_surgeries[or_id].append(s.surgery_id)

            for or_id, surgery_ids in or_surgeries.items():
                lines.append(f"\n  手术室 {or_id}:")
                for sid in surgery_ids:
                    if sid in pred_dict:
                        p = pred_dict[sid]
                        lines.append(f"    - {sid}: 预测 {p.predicted_duration:.0f} 分钟 (置信区间: {p.confidence_interval_low:.0f}-{p.confidence_interval_high:.0f} 分钟)")

        lines.append("")
        lines.append("=" * 60)
        lines.append("报告结束")
        lines.append("=" * 60)

        return "\n".join(lines)

    def save(self, content: str, file_path: str) -> None:
        """保存报告到文件"""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)


class CSVReportGenerator:
    """CSV 格式报告生成器"""

    def generate_conflicts_csv(self, conflicts: List[ConflictResult], file_path: str) -> None:
        """生成冲突报告 CSV

        Args:
            conflicts: 冲突列表
            file_path: 输出文件路径
        """
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            # 标题行
            writer.writerow([
                'conflict_id', 'conflict_type', 'severity', 'description',
                'surgeries_involved', 'equipment_involved',
                'time_overlap_start', 'time_overlap_end',
                'resolution_suggestion', 'detected_at'
            ])

            # 数据行
            for c in conflicts:
                writer.writerow([
                    c.conflict_id,
                    c.conflict_type,
                    c.severity,
                    c.description,
                    ';'.join(c.surgeries_involved),
                    ';'.join(c.equipment_involved),
                    c.time_overlap_start.strftime('%Y-%m-%d %H:%M:%S') if c.time_overlap_start else '',
                    c.time_overlap_end.strftime('%Y-%m-%d %H:%M:%S') if c.time_overlap_end else '',
                    c.resolution_suggestion,
                    c.detected_at.strftime('%Y-%m-%d %H:%M:%S')
                ])

    def generate_predictions_csv(self, predictions: List[PredictionResult], file_path: str) -> None:
        """生成预测结果 CSV

        Args:
            predictions: 预测结果列表
            file_path: 输出文件路径
        """
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            # 标题行
            writer.writerow([
                'surgery_id', 'predicted_duration', 'confidence_interval_low',
                'confidence_interval_high', 'confidence_level', 'model_version'
            ])

            # 数据行
            for p in predictions:
                writer.writerow([
                    p.surgery_id,
                    p.predicted_duration,
                    p.confidence_interval_low,
                    p.confidence_interval_high,
                    p.confidence_level,
                    p.model_version
                ])

    def generate_surgeries_csv(self, surgeries: List[SurgeryRecord], file_path: str) -> None:
        """生成手术记录 CSV

        Args:
            surgeries: 手术记录列表
            file_path: 输出文件路径
        """
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            # 标题行
            writer.writerow([
                'surgery_id', 'patient_id', 'surgery_name', 'surgery_type',
                'department', 'surgeon', 'anesthesia_type', 'equipment_needed',
                'scheduled_duration', 'estimated_duration', 'scheduled_time',
                'operating_room', 'priority'
            ])

            # 数据行
            for s in surgeries:
                writer.writerow([
                    s.surgery_id,
                    s.patient_id,
                    s.surgery_name,
                    s.surgery_type,
                    s.department,
                    s.surgeon,
                    s.anesthesia_type.value if hasattr(s.anesthesia_type, 'value') else str(s.anesthesia_type),
                    ','.join(s.equipment_needed),
                    s.scheduled_duration,
                    s.estimated_duration,
                    s.scheduled_time.strftime('%Y-%m-%d %H:%M:%S') if s.scheduled_time else '',
                    s.operating_room,
                    s.priority
                ])


class HTMLReportGenerator:
    """HTML 格式报告生成器"""

    def __init__(self, template_dir: Optional[str] = None):
        """初始化 HTML 报告生成器

        Args:
            template_dir: 模板目录路径，如果为 None 则使用内置模板
        """
        self.template_dir = template_dir
        self._jinja_available = False

        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape
            self._jinja_available = True
            if template_dir:
                self.env = Environment(
                    loader=FileSystemLoader(template_dir),
                    autoescape=select_autoescape(['html', 'xml'])
                )
            else:
                self.env = None
        except ImportError:
            self.env = None

    def generate(
        self,
        surgeries: List[SurgeryRecord],
        predictions: List[PredictionResult],
        conflicts: List[ConflictResult],
        summary: Optional[Dict[str, int]] = None,
        output_path: Optional[str] = None
    ) -> str:
        """生成 HTML 报告

        Args:
            surgeries: 手术记录列表
            predictions: 预测结果列表
            conflicts: 冲突列表
            summary: 冲突统计摘要
            output_path: 输出文件路径

        Returns:
            HTML 内容字符串
        """
        if self.env and self.template_dir:
            try:
                template = self.env.get_template('report.html')
                html_content = template.render(
                    surgeries=surgeries,
                    predictions=predictions,
                    conflicts=conflicts,
                    summary=summary,
                    generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
            except Exception:
                html_content = self._generate_inline_html(surgeries, predictions, conflicts, summary)
        else:
            html_content = self._generate_inline_html(surgeries, predictions, conflicts, summary)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

        return html_content

    def _generate_inline_html(
        self,
        surgeries: List[SurgeryRecord],
        predictions: List[PredictionResult],
        conflicts: List[ConflictResult],
        summary: Optional[Dict[str, int]]
    ) -> str:
        """生成内联 HTML 报告（无 Jinja2 模板时使用）"""
        severity_colors = {
            'critical': '#d32f2f',
            'high': '#f57c00',
            'medium': '#fbc02d',
            'low': '#388e3c'
        }

        conflict_rows = ""
        for c in conflicts:
            color = severity_colors.get(c.severity, '#757575')
            time_range = ""
            if c.time_overlap_start and c.time_overlap_end:
                time_range = f"{c.time_overlap_start.strftime('%H:%M')} - {c.time_overlap_end.strftime('%H:%M')}"
            elif c.time_overlap_start:
                time_range = f"{c.time_overlap_start.strftime('%H:%M')} -"

            conflict_rows += f"""
            <tr>
                <td>{c.conflict_id}</td>
                <td>{c.conflict_type}</td>
                <td><span class="severity-badge" style="background-color: {color}">{c.severity}</span></td>
                <td>{c.description}</td>
                <td>{', '.join(c.surgeries_involved)}</td>
                <td>{time_range}</td>
                <td>{c.resolution_suggestion or '-'}</td>
            </tr>
            """

        summary_html = ""
        if summary:
            summary_html = f"""
            <div class="summary-cards">
                <div class="card total">总计: {summary.get('total', 0)}</div>
                <div class="card critical">严重: {summary.get('critical', 0)}</div>
                <div class="card high">高风险: {summary.get('high', 0)}</div>
                <div class="card medium">中风险: {summary.get('medium', 0)}</div>
                <div class="card low">低风险: {summary.get('low', 0)}</div>
            </div>
            """

        prediction_rows = ""
        pred_dict = {p.surgery_id: p for p in predictions}
        for s in surgeries:
            if s.surgery_id in pred_dict:
                p = pred_dict[s.surgery_id]
                prediction_rows += f"""
                <tr>
                    <td>{s.surgery_id}</td>
                    <td>{s.surgery_name}</td>
                    <td>{s.operating_room or '-'}</td>
                    <td>{s.surgeon}</td>
                    <td>{p.predicted_duration:.0f} 分钟</td>
                    <td>[{p.confidence_interval_low:.0f}, {p.confidence_interval_high:.0f}] 分钟</td>
                    <td>{p.confidence_level:.0%}</td>
                </tr>
                """

        # 构建冲突详情section
        if conflicts:
            conflicts_section = f"""
        <div class="section">
            <h2>冲突详情</h2>
            <table>
                <thead>
                    <tr>
                        <th>冲突ID</th>
                        <th>类型</th>
                        <th>严重程度</th>
                        <th>说明</th>
                        <th>涉及手术</th>
                        <th>时间重叠</th>
                        <th>解决建议</th>
                    </tr>
                </thead>
                <tbody>
                    {conflict_rows}
                </tbody>
            </table>
        </div>"""
        else:
            conflicts_section = """
        <div class="section">
            <h2>冲突详情</h2>
            <p>未检测到冲突</p>
        </div>"""

        # 构建预测section
        if predictions:
            predictions_section = f"""
        <div class="section">
            <h2>手术时长预测</h2>
            <table>
                <thead>
                    <tr>
                        <th>手术ID</th>
                        <th>手术名称</th>
                        <th>手术室</th>
                        <th>主刀医生</th>
                        <th>预测时长</th>
                        <th>置信区间</th>
                        <th>置信度</th>
                    </tr>
                </thead>
                <tbody>
                    {prediction_rows}
                </tbody>
            </table>
        </div>"""
        else:
            predictions_section = """
        <div class="section">
            <h2>手术时长预测</h2>
            <p>无预测数据</p>
        </div>"""

        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>手术室资源冲突预测报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Microsoft YaHei', sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #1976d2, #1565c0); color: white; padding: 30px; border-radius: 8px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0 0 10px 0; }}
        .header p {{ margin: 0; opacity: 0.9; }}
        .section {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .section h2 {{ color: #1976d2; margin-top: 0; border-bottom: 2px solid #1976d2; padding-bottom: 10px; }}
        .summary-cards {{ display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 20px; }}
        .card {{ padding: 15px 25px; border-radius: 8px; color: white; font-weight: bold; font-size: 18px; }}
        .card.total {{ background: #1976d2; }}
        .card.critical {{ background: #d32f2f; }}
        .card.high {{ background: #f57c00; }}
        .card.medium {{ background: #fbc02d; color: #333; }}
        .card.low {{ background: #388e3c; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th {{ background-color: #e3f2fd; color: #1565c0; padding: 12px 8px; text-align: left; font-weight: 600; }}
        td {{ padding: 10px 8px; border-bottom: 1px solid #e0e0e0; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .severity-badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; color: white; font-size: 12px; font-weight: bold; text-transform: uppercase; }}
        .no-data {{ text-align: center; color: #9e9e9e; padding: 40px; font-style: italic; }}
        .footer {{ text-align: center; color: #9e9e9e; margin-top: 20px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>手术室资源冲突预测报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        {summary_html}

        {conflicts_section}

        {predictions_section}

        <div class="footer">
            手术室资源冲突预测系统 v1.0
        </div>
    </div>
</body>
</html>
        """
        return html


def generate_report(
    surgeries: List[SurgeryRecord],
    predictions: List[PredictionResult],
    conflicts: List[ConflictResult],
    summary: Optional[Dict[str, int]] = None,
    output_path: Optional[str] = None,
    format: str = "text"
) -> str:
    """便捷函数：生成报告

    Args:
        surgeries: 手术记录列表
        predictions: 预测结果列表
        conflicts: 冲突列表
        summary: 冲突统计摘要
        output_path: 输出文件路径
        format: 报告格式，"text"、"csv" 或 "html"

    Returns:
        报告内容（text/html）或空字符串（csv）
    """
    if format == "text":
        generator = TextReportGenerator()
        content = generator.generate(surgeries, predictions, conflicts, summary)
        if output_path:
            generator.save(content, output_path)
        return content

    elif format == "html":
        generator = HTMLReportGenerator()
        return generator.generate(surgeries, predictions, conflicts, summary, output_path)

    elif format == "csv":
        generator = CSVReportGenerator()
        if output_path:
            base = output_path.rsplit('.', 1)[0]
            generator.generate_conflicts_csv(conflicts, f"{base}_conflicts.csv")
            generator.generate_predictions_csv(predictions, f"{base}_predictions.csv")
            generator.generate_surgeries_csv(surgeries, f"{base}_surgeries.csv")
        return ""

    else:
        raise ValueError(f"不支持的报告格式: {format}")