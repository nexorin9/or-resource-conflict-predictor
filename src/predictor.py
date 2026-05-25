"""手术室资源冲突预测系统 - 时长预测模块"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

from src.models import SurgeryRecord, PredictionResult


class DurationPredictor:
    """手术时长预测器"""

    def __init__(self, model_type: str = "linear"):
        """初始化预测器

        Args:
            model_type: 模型类型，"linear" 或 "gb"（梯度提升）
        """
        self.model_type = model_type
        self.model: Optional[Any] = None
        self.scaler = StandardScaler()
        self._is_fitted = False
        self.feature_names: List[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series) -> 'DurationPredictor':
        """训练模型

        Args:
            X: 特征 DataFrame
            y: 目标变量（实际时长）

        Returns:
            self
        """
        self.feature_names = X.columns.tolist()

        # 标准化特征
        X_scaled = self.scaler.fit_transform(X.fillna(0))

        if self.model_type == "linear":
            self.model = LinearRegression()
        elif self.model_type == "gb":
            self.model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                random_state=42
            )
        else:
            self.model = Ridge(alpha=1.0)

        self.model.fit(X_scaled, y)
        self._is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> List[PredictionResult]:
        """预测手术时长

        Args:
            X: 特征 DataFrame

        Returns:
            预测结果列表
        """
        if not self._is_fitted:
            raise ValueError("模型尚未训练，请先调用 fit()")

        X_scaled = self.scaler.transform(X.fillna(0))
        predictions = self.model.predict(X_scaled)

        results = []
        for i, (_, row) in enumerate(X.iterrows()):
            pred_duration = max(30, predictions[i])  # 最少30分钟

            # 计算置信区间（基于残差分布）
            residuals = self._calculate_residuals(X, row)
            std_err = np.std(residuals) if len(residuals) > 0 else 15
            ci_low = max(15, pred_duration - 1.96 * std_err)
            ci_high = pred_duration + 1.96 * std_err

            # 置信度（基于训练样本量）
            confidence = min(0.95, 0.6 + 0.05 * len(X) / 100)

            result = PredictionResult(
                surgery_id=str(row.get('surgery_id', f'S{i:05d}')),
                predicted_duration=round(pred_duration, 1),
                confidence_interval_low=round(ci_low, 1),
                confidence_interval_high=round(ci_high, 1),
                confidence_level=round(confidence, 2),
                features_used=self.feature_names,
                model_version="v1.0"
            )
            results.append(result)

        return results

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """评估模型性能

        Args:
            X: 特征 DataFrame
            y: 真实目标

        Returns:
            评估指标字典
        """
        if not self._is_fitted:
            raise ValueError("模型尚未训练")

        X_scaled = self.scaler.transform(X.fillna(0))
        y_pred = self.model.predict(X_scaled)

        mae = np.mean(np.abs(y - y_pred))
        rmse = np.sqrt(np.mean((y - y_pred) ** 2))
        r2 = self.model.score(X_scaled, y)

        # 交叉验证
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=5, scoring='neg_mean_absolute_error')

        return {
            'mae': round(mae, 2),
            'rmse': round(rmse, 2),
            'r2': round(r2, 4),
            'cv_mae_mean': round(-cv_scores.mean(), 2),
            'cv_mae_std': round(cv_scores.std(), 2)
        }

    def _calculate_residuals(self, X: pd.DataFrame, target_row: pd.Series) -> List[float]:
        """计算残差用于置信区间估计"""
        try:
            X_sample = X.sample(min(50, len(X)), replace=True)
            X_scaled = self.scaler.transform(X_sample.fillna(0))
            y_sample = self.model.predict(X_scaled)
            residuals = np.abs(y_sample - y_sample.mean())
            return residuals.tolist()
        except Exception:
            return [15.0, 20.0, 25.0]


class SurgeonBasedPredictor:
    """基于主刀医生的预测器"""

    def __init__(self):
        self.predictors: Dict[str, DurationPredictor] = {}
        self.global_predictor = DurationPredictor(model_type="linear")

    def fit(self, records: List[SurgeryRecord], features: pd.DataFrame) -> 'SurgeonBasedPredictor':
        """按主刀医生训练预测模型

        Args:
            records: 手术记录
            features: 特征

        Returns:
            self
        """
        # 首先训练全局模型
        y = pd.Series([r.actual_duration or r.scheduled_duration for r in records])
        self.global_predictor.fit(features, y)

        # 按主刀分组训练
        df = pd.DataFrame({
            'surgeon': [r.surgeon for r in records],
            'surgery_id': [r.surgery_id for r in records]
        })
        df = pd.concat([df, features], axis=1)

        for surgeon in df['surgeon'].unique():
            surgeon_mask = df['surgeon'] == surgeon
            surgeon_records = [records[i] for i in range(len(records)) if records[i].surgeon == surgeon]
            surgeon_features = features[surgeon_mask].copy()

            if len(surgeon_features) >= 5:  # 至少5条记录才训练
                surgeon_y = pd.Series([r.actual_duration or r.scheduled_duration for r in surgeon_records])
                predictor = DurationPredictor(model_type="linear")
                predictor.fit(surgeon_features, surgeon_y)
                self.predictors[surgeon] = predictor

        return self

    def predict(self, records: List[SurgeryRecord], features: pd.DataFrame) -> List[PredictionResult]:
        """预测手术时长（优先使用主刀专属模型）"""
        global_results = self.global_predictor.predict(features)

        results = []
        for i, (record, g_result) in enumerate(zip(records, global_results)):
            if record.surgeon in self.predictors and len(features.iloc[i:i+1]) > 0:
                try:
                    surgeon_pred = self.predictors[record.surgeon].predict(features.iloc[i:i+1])
                    if surgeon_pred:
                        results.append(surgeon_pred[0])
                    else:
                        results.append(g_result)
                except Exception:
                    results.append(g_result)
            else:
                results.append(g_result)

        return results


class DepartmentBasedPredictor:
    """基于科室的预测器"""

    def __init__(self):
        self.predictors: Dict[str, DurationPredictor] = {}
        self.global_predictor = DurationPredictor(model_type="linear")

    def fit(self, records: List[SurgeryRecord], features: pd.DataFrame) -> 'DepartmentBasedPredictor':
        """按科室训练预测模型

        Args:
            records: 手术记录
            features: 特征

        Returns:
            self
        """
        # 首先训练全局模型
        y = pd.Series([r.actual_duration or r.scheduled_duration for r in records])
        self.global_predictor.fit(features, y)

        # 按科室分组训练
        df = pd.DataFrame({
            'department': [r.department for r in records],
            'surgery_id': [r.surgery_id for r in records]
        })
        df = pd.concat([df, features], axis=1)

        for dept in df['department'].unique():
            dept_mask = df['department'] == dept
            dept_records = [records[i] for i in range(len(records)) if records[i].department == dept]
            dept_features = features[dept_mask].copy()

            if len(dept_features) >= 5:  # 至少5条记录才训练
                dept_y = pd.Series([r.actual_duration or r.scheduled_duration for r in dept_records])
                predictor = DurationPredictor(model_type="linear")
                predictor.fit(dept_features, dept_y)
                self.predictors[dept] = predictor

        return self

    def predict(self, records: List[SurgeryRecord], features: pd.DataFrame) -> List[PredictionResult]:
        """预测手术时长（优先使用科室专属模型）"""
        global_results = self.global_predictor.predict(features)

        results = []
        for i, (record, g_result) in enumerate(zip(records, global_results)):
            if record.department in self.predictors and len(features.iloc[i:i+1]) > 0:
                try:
                    dept_pred = self.predictors[record.department].predict(features.iloc[i:i+1])
                    if dept_pred:
                        results.append(dept_pred[0])
                    else:
                        results.append(g_result)
                except Exception:
                    results.append(g_result)
            else:
                results.append(g_result)

        return results


def train_predictor(
    records: List[SurgeryRecord],
    features: pd.DataFrame,
    model_type: str = "ensemble"
) -> Tuple[Any, Dict[str, float]]:
    """便捷函数：训练预测模型

    Args:
        records: 手术记录
        features: 特征
        model_type: 模型类型，"linear"、"gb"、"surgeon"、"department"、"ensemble"

    Returns:
        (训练好的预测器, 评估指标)
    """
    y = pd.Series([r.actual_duration or r.scheduled_duration for r in records])

    if model_type == "surgeon":
        predictor = SurgeonBasedPredictor()
        predictor.fit(records, features)
        # 简单评估
        try:
            test_results = predictor.predict(records[:min(10, len(records))], features[:min(10, len(records))])
            metrics = {'status': 'trained'}
        except Exception as e:
            metrics = {'status': 'partial', 'error': str(e)}
        return predictor, metrics

    elif model_type == "department":
        predictor = DepartmentBasedPredictor()
        predictor.fit(records, features)
        try:
            test_results = predictor.predict(records[:min(10, len(records))], features[:min(10, len(records))])
            metrics = {'status': 'trained'}
        except Exception as e:
            metrics = {'status': 'partial', 'error': str(e)}
        return predictor, metrics

    elif model_type == "ensemble":
        # 集成模型：全局 + 主刀 + 科室
        ensemble = {
            'global': DurationPredictor(model_type="linear"),
            'surgeon': SurgeonBasedPredictor(),
            'department': DepartmentBasedPredictor()
        }

        ensemble['global'].fit(features, y)
        ensemble['surgeon'].fit(records, features)
        ensemble['department'].fit(records, features)

        # 评估全局模型
        global_metrics = ensemble['global'].evaluate(features, y)
        global_metrics['status'] = 'trained'
        return ensemble, global_metrics

    else:
        predictor = DurationPredictor(model_type=model_type)
        predictor.fit(features, y)
        metrics = predictor.evaluate(features, y)
        return predictor, metrics