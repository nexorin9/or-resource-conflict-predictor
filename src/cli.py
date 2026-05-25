"""手术室资源冲突预测系统 - 命令行入口"""

import sys
from typing import Optional

import click

from src.data_loader import load_surgeries, MockDataGenerator
from src.predictor import DurationPredictor, train_predictor
from src.conflict_detector import ConflictDetector
from src.report_generator import generate_report as generate_report_func


def generate_sample_data(n: int):
    """生成模拟数据（便捷函数）"""
    generator = MockDataGenerator()
    return generator.generate_surgeries(n)


@click.group()
@click.version_option(version="1.0.0", prog_name="or-resource-conflict-predictor")
def cli():
    """手术室资源冲突预测系统

    基于历史手术数据预测手术时长波动，提前发现器械/麻醉/主刀冲突，
    输出给科室协调的排程建议。
    """
    pass


@cli.command("predict")
@click.option("--data", "-d", required=True, help="手术数据文件路径 (CSV/Excel)")
@click.option("--output", "-o", default=None, help="预测结果输出文件路径")
@click.option("--format", "-f", type=click.Choice(["csv", "json"]), default="csv", help="输出格式")
def predict(data: str, output: Optional[str], format: str):
    """预测手术时长

    基于历史数据训练模型并预测手术时长。
    """
    click.echo(f"正在加载数据: {data}")

    try:
        surgeries = load_surgeries(data)
        click.echo(f"已加载 {len(surgeries)} 条手术记录")

        # 构建特征
        from src.feature_engineering import FeatureEngineering
        engineer = FeatureEngineering()
        features = engineer.fit_transform(surgeries)

        # 训练预测模型
        click.echo("正在训练预测模型...")
        predictor = DurationPredictor(model_type="linear")
        import pandas as pd
        y = pd.Series([r.actual_duration or r.scheduled_duration for r in surgeries])
        predictor.fit(features, y)

        # 执行预测
        click.echo("正在预测手术时长...")
        predictions = predictor.predict(features)

        click.echo(f"已完成 {len(predictions)} 条预测")

        # 输出结果
        if output:
            if format == "csv":
                from src.report_generator import CSVReportGenerator
                gen = CSVReportGenerator()
                gen.generate_predictions_csv(predictions, output)
                click.echo(f"预测结果已保存到: {output}")
            else:
                import json
                pred_dict = [p.to_dict() for p in predictions]
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(pred_dict, f, ensure_ascii=False, indent=2)
                click.echo(f"预测结果已保存到: {output}")
        else:
            click.echo("\n预测结果摘要:")
            for p in predictions[:10]:
                click.echo(f"  {p.surgery_id}: {p.predicted_duration:.0f} 分钟 "
                          f"(置信区间: [{p.confidence_interval_low:.0f}, {p.confidence_interval_high:.0f}])")
            if len(predictions) > 10:
                click.echo(f"  ... 还有 {len(predictions) - 10} 条预测")

    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


@cli.command("detect-conflicts")
@click.option("--data", "-d", required=True, help="手术数据文件路径 (CSV/Excel)")
@click.option("--output", "-o", default=None, help="冲突报告输出文件路径")
@click.option("--format", "-f", type=click.Choice(["text", "csv", "html"]), default="text", help="报告格式")
def detect_conflicts(data: str, output: Optional[str], format: str):
    """检测手术室资源冲突

    检测器械冲突、麻醉设备冲突、主刀时间冲突等。
    """
    click.echo(f"正在加载数据: {data}")

    try:
        surgeries = load_surgeries(data)
        click.echo(f"已加载 {len(surgeries)} 条手术记录")

        # 检测冲突
        click.echo("正在检测资源冲突...")
        detector = ConflictDetector()
        conflicts = detector.detect_all(surgeries)

        click.echo(f"检测到 {len(conflicts)} 个冲突")

        # 输出结果
        if output:
            if format == "text":
                from src.report_generator import TextReportGenerator
                gen = TextReportGenerator()
                content = gen.generate(surgeries, [], conflicts, detector.get_summary(conflicts))
                gen.save(content, output)
                click.echo(f"冲突报告已保存到: {output}")
            elif format == "html":
                from src.report_generator import HTMLReportGenerator
                gen = HTMLReportGenerator()
                gen.generate(surgeries, [], conflicts, detector.get_summary(conflicts), output)
                click.echo(f"冲突报告已保存到: {output}")
            else:
                from src.report_generator import CSVReportGenerator
                gen = CSVReportGenerator()
                base = output.rsplit('.', 1)[0]
                gen.generate_conflicts_csv(conflicts, f"{base}_conflicts.csv")
                click.echo(f"冲突报告已保存到: {base}_conflicts.csv")
        else:
            summary = detector.get_summary(conflicts)
            click.echo("\n冲突摘要:")
            click.echo(f"  总计: {summary['total']}")
            click.echo(f"  - 严重: {summary['critical']}")
            click.echo(f"  - 高风险: {summary['high']}")
            click.echo(f"  - 中风险: {summary['medium']}")
            click.echo(f"  - 低风险: {summary['low']}")

            click.echo("\n冲突详情 (前10条):")
            for c in conflicts[:10]:
                click.echo(f"  [{c.severity.upper()}] {c.conflict_id}")
                click.echo(f"    类型: {c.conflict_type}")
                click.echo(f"    说明: {c.description}")
                if c.resolution_suggestion:
                    click.echo(f"    建议: {c.resolution_suggestion}")

            if len(conflicts) > 10:
                click.echo(f"  ... 还有 {len(conflicts) - 10} 个冲突")

    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


@cli.command("generate-report")
@click.option("--data", "-d", required=True, help="手术数据文件路径 (CSV/Excel)")
@click.option("--output", "-o", default=None, help="报告输出文件路径")
@click.option("--format", "-f", type=click.Choice(["text", "csv", "html"]), default="text", help="报告格式")
@click.option("--predict/--no-predict", "do_predict", default=True, help="是否包含时长预测")
@click.option("--conflicts/--no-conflicts", "do_conflicts", default=True, help="是否包含冲突检测")
def generate_report(data: str, output: Optional[str], format: str, do_predict: bool, do_conflicts: bool):
    """生成综合报告

    包含手术时长预测和资源冲突检测的综合报告。
    """
    click.echo(f"正在加载数据: {data}")

    try:
        surgeries = load_surgeries(data)
        click.echo(f"已加载 {len(surgeries)} 条手术记录")

        predictions = []
        all_conflicts = []
        summary = None

        if do_predict:
            click.echo("正在训练预测模型并预测...")
            from src.feature_engineering import FeatureEngineering
            engineer = FeatureEngineering()
            features = engineer.fit_transform(surgeries)

            predictor = DurationPredictor(model_type="linear")
            import pandas as pd
            y = pd.Series([r.actual_duration or r.scheduled_duration for r in surgeries])
            predictor.fit(features, y)
            predictions = predictor.predict(features)
            click.echo(f"已完成 {len(predictions)} 条预测")

        if do_conflicts:
            click.echo("正在检测资源冲突...")
            detector = ConflictDetector()
            all_conflicts = detector.detect_all(surgeries)
            summary = detector.get_summary(all_conflicts)
            click.echo(f"检测到 {len(all_conflicts)} 个冲突")

        # 生成报告
        click.echo(f"正在生成 {format} 格式报告...")
        content = generate_report_func(
            surgeries, predictions, all_conflicts, summary, output, format
        )

        if output:
            click.echo(f"报告已保存到: {output}")
        else:
            click.echo("\n" + content)

        click.echo("\n报告生成完成!")

    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


@cli.command("demo")
def demo():
    """运行演示程序

    使用模拟数据演示系统功能。
    """
    click.echo("=" * 60)
    click.echo("手术室资源冲突预测系统 - 演示模式")
    click.echo("=" * 60)

    try:
        click.echo("\n正在生成模拟数据...")
        generator = MockDataGenerator()
        surgeries = generator.generate_surgeries(50)
        click.echo(f"已生成 {len(surgeries)} 条模拟手术记录")

        # 预测
        click.echo("\n正在训练预测模型...")
        from src.feature_engineering import FeatureEngineering
        engineer = FeatureEngineering()
        features = engineer.fit_transform(surgeries)

        predictor = DurationPredictor(model_type="linear")
        import pandas as pd
        y = pd.Series([r.actual_duration or r.scheduled_duration for r in surgeries])
        predictor.fit(features, y)
        predictions = predictor.predict(features)
        click.echo(f"已完成 {len(predictions)} 条时长预测")

        # 冲突检测
        click.echo("\n正在检测资源冲突...")
        detector = ConflictDetector()
        all_conflicts = detector.detect_all(surgeries)
        summary = detector.get_summary(all_conflicts)
        click.echo(f"检测到 {len(all_conflicts)} 个冲突")

        # 打印摘要
        click.echo("\n" + "=" * 60)
        click.echo("冲突摘要")
        click.echo("=" * 60)
        click.echo(f"  总计: {summary['total']}")
        click.echo(f"  - 严重: {summary['critical']}")
        click.echo(f"  - 高风险: {summary['high']}")
        click.echo(f"  - 中风险: {summary['medium']}")
        click.echo(f"  - 低风险: {summary['low']}")

        if all_conflicts:
            click.echo("\n前5个冲突详情:")
            for i, c in enumerate(all_conflicts[:5], 1):
                click.echo(f"\n  [{i}] {c.conflict_id}")
                click.echo(f"      类型: {c.conflict_type}")
                click.echo(f"      严重程度: {c.severity}")
                click.echo(f"      说明: {c.description}")
                if c.resolution_suggestion:
                    click.echo(f"      建议: {c.resolution_suggestion}")

        click.echo("\n" + "=" * 60)
        click.echo("演示完成!")
        click.echo("=" * 60)

    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


def main():
    """主入口点"""
    cli()


if __name__ == "__main__":
    main()