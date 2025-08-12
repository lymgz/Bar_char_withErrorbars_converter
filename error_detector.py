#!/usr/bin/env python3
"""
误差线类型检测器
自动识别和验证误差线类型
"""

import math
from typing import Tuple, Optional, List

class ErrorBarDetector:
    def __init__(self):
        self.supported_types = {
            'SE': '标准误差',
            'SD': '标准差',
            'CI95': '95%置信区间',
            'CI99': '99%置信区间',
            '2SE': '2倍标准误差',
            'ASYMMETRIC': '非对称误差线',  # 新增非对称误差线类型
            'SEM': '标准误差',  # 别名
            'STD': '标准差',   # 别名
            'STDERR': '标准误差'  # 别名
        }
        
        # 类型映射（标准化）
        self.type_mapping = {
            'SEM': 'SE',
            'STD': 'SD',
            'STDERR': 'SE',
            'ASYM': 'ASYMMETRIC',  # 别名
            'ASYMM': 'ASYMMETRIC'  # 别名
        }
    
    def detect_error_type(self, mean: Optional[float], error_bar: Optional[float], 
                         declared_type: str, sample_size: Optional[int]) -> Tuple[str, float]:
        """
        检测误差线类型
        
        Args:
            mean: 均值
            error_bar: 误差线数值
            declared_type: 声明的误差线类型
            sample_size: 样本量
            
        Returns:
            (detected_type, confidence): 检测到的类型和置信度
        """
        if not all([mean is not None, error_bar is not None, sample_size is not None]):
            return 'UNKNOWN', 0.0
        
        # 标准化声明类型
        normalized_declared = self._normalize_type(declared_type)
        
        # 如果声明类型有效且合理，直接使用
        if normalized_declared in self.supported_types:
            confidence = self._validate_declared_type(
                mean, error_bar, normalized_declared, sample_size
            )
            if confidence > 0.5:
                return normalized_declared, confidence
        
        # 自动检测类型
        detected_type, confidence = self._auto_detect_type(mean, error_bar, sample_size)
        
        # 如果自动检测置信度低，但声明类型有效，使用声明类型
        if confidence < 0.7 and normalized_declared in self.supported_types:
            return normalized_declared, 0.6
        
        return detected_type, confidence
    
    def _normalize_type(self, declared_type: str) -> str:
        """标准化类型名称"""
        if not declared_type:
            return 'UNKNOWN'
        
        normalized = declared_type.upper().strip()
        return self.type_mapping.get(normalized, normalized)
    
    def _validate_declared_type(self, mean: float, error_bar: float, 
                               declared_type: str, sample_size: int) -> float:
        """验证声明的误差线类型是否合理"""
        try:
            # 基本合理性检查
            if error_bar <= 0 or sample_size <= 0:
                return 0.0
            
            # 误差线不应该比均值大太多（除非是特殊情况）
            if error_bar > abs(mean) * 3:
                return 0.3
            
            # 根据类型进行特定验证
            if declared_type == 'SD':
                # 标准差通常比标准误差大
                expected_se = error_bar / math.sqrt(sample_size)
                if expected_se > 0 and expected_se < error_bar:
                    return 0.9
                return 0.6
            
            elif declared_type == 'SE':
                # 标准误差应该相对较小
                expected_sd = error_bar * math.sqrt(sample_size)
                if expected_sd > error_bar and expected_sd < abs(mean) * 2:
                    return 0.9
                return 0.6
            
            elif declared_type in ['CI95', 'CI99']:
                # 置信区间应该是合理范围
                if declared_type == 'CI95':
                    expected_se = error_bar / 1.96
                else:  # CI99
                    expected_se = error_bar / 2.576
                
                expected_sd = expected_se * math.sqrt(sample_size)
                if expected_sd > 0 and expected_sd < abs(mean) * 2:
                    return 0.8
                return 0.5
            
            elif declared_type == '2SE':
                # 2倍标准误差
                se = error_bar / 2
                expected_sd = se * math.sqrt(sample_size)
                if expected_sd > 0 and expected_sd < abs(mean) * 2:
                    return 0.8
                return 0.5
            
            return 0.7
            
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    def _auto_detect_type(self, mean: float, error_bar: float, 
                         sample_size: int) -> Tuple[str, float]:
        """自动检测误差线类型"""
        try:
            # 计算各种可能的转换结果
            candidates = []
            
            # 假设是标准差
            if error_bar > 0:
                se_from_sd = error_bar / math.sqrt(sample_size)
                candidates.append(('SD', self._score_sd_assumption(mean, error_bar, se_from_sd)))
            
            # 假设是标准误差
            if error_bar > 0:
                sd_from_se = error_bar * math.sqrt(sample_size)
                candidates.append(('SE', self._score_se_assumption(mean, error_bar, sd_from_se)))
            
            # 假设是95%置信区间
            if error_bar > 0:
                se_from_ci95 = error_bar / 1.96
                sd_from_ci95 = se_from_ci95 * math.sqrt(sample_size)
                candidates.append(('CI95', self._score_ci_assumption(mean, error_bar, se_from_ci95, sd_from_ci95)))
            
            # 假设是99%置信区间
            if error_bar > 0:
                se_from_ci99 = error_bar / 2.576
                sd_from_ci99 = se_from_ci99 * math.sqrt(sample_size)
                candidates.append(('CI99', self._score_ci_assumption(mean, error_bar, se_from_ci99, sd_from_ci99)))
            
            # 假设是2倍标准误差
            if error_bar > 0:
                se_from_2se = error_bar / 2
                sd_from_2se = se_from_2se * math.sqrt(sample_size)
                candidates.append(('2SE', self._score_se_assumption(mean, se_from_2se, sd_from_2se)))
            
            # 选择得分最高的类型
            if candidates:
                best_type, best_score = max(candidates, key=lambda x: x[1])
                return best_type, best_score
            
            return 'UNKNOWN', 0.0
            
        except (ValueError, ZeroDivisionError):
            return 'UNKNOWN', 0.0
    
    def _score_sd_assumption(self, mean: float, sd: float, se: float) -> float:
        """评估标准差假设的合理性"""
        score = 0.5  # 基础分
        
        # 标准差应该比标准误差大
        if sd > se:
            score += 0.2
        
        # 标准差不应该过大
        if sd < abs(mean) * 1.5:
            score += 0.2
        elif sd < abs(mean) * 2:
            score += 0.1
        
        # 变异系数检查 (CV = SD/Mean)
        if mean != 0:
            cv = abs(sd / mean)
            if 0.1 <= cv <= 1.0:  # 合理的变异系数范围
                score += 0.1
        
        return min(score, 1.0)
    
    def _score_se_assumption(self, mean: float, se: float, sd: float) -> float:
        """评估标准误差假设的合理性"""
        score = 0.5  # 基础分
        
        # 标准误差应该比标准差小
        if se < sd:
            score += 0.2
        
        # 标准误差应该相对较小
        if se < abs(mean) * 0.5:
            score += 0.2
        elif se < abs(mean):
            score += 0.1
        
        # 标准差的合理性
        if mean != 0:
            cv = abs(sd / mean)
            if 0.1 <= cv <= 1.0:
                score += 0.1
        
        return min(score, 1.0)
    
    def _score_ci_assumption(self, mean: float, ci_half_width: float, 
                           se: float, sd: float) -> float:
        """评估置信区间假设的合理性"""
        score = 0.4  # 基础分（置信区间相对少见）
        
        # 置信区间应该是合理大小
        if ci_half_width > se and ci_half_width < abs(mean):
            score += 0.3
        elif ci_half_width < abs(mean) * 1.5:
            score += 0.2
        
        # 检查推导的标准差是否合理
        if mean != 0:
            cv = abs(sd / mean)
            if 0.1 <= cv <= 1.0:
                score += 0.2
        
        # 置信区间通常用于较小样本
        return min(score, 0.8)  # 最高0.8，因为不如直接的SE/SD常见
    
    def get_conversion_method(self, error_type: str) -> str:
        """获取转换方法描述"""
        methods = {
            'SD': 'direct_sd',
            'SE': 'se_to_sd',
            'CI95': 'ci95_to_sd',
            'CI99': 'ci99_to_sd',
            '2SE': '2se_to_sd'
        }
        return methods.get(error_type, 'unknown')
    
    def validate_conversion_input(self, mean: float, error_bar: float, 
                                error_type: str, sample_size: int) -> Tuple[bool, str]:
        """验证转换输入的有效性"""
        if sample_size <= 0:
            return False, "样本量必须大于0"
        
        if error_bar <= 0:
            return False, "误差线数值必须大于0"
        
        if error_type not in self.supported_types and error_type != 'UNKNOWN':
            return False, f"不支持的误差线类型: {error_type}"
        
        # 检查数值的合理性
        if abs(mean) < 1e-10 and error_bar > 1:
            return False, "均值接近0但误差线很大，请检查数据"
        
        if error_bar > abs(mean) * 5:
            return False, "误差线过大，可能存在数据错误"
        
        return True, "验证通过"
    
    def suggest_improvements(self, mean: float, error_bar: float, 
                           error_type: str, sample_size: int) -> List[str]:
        """提供数据改进建议"""
        suggestions = []
        
        # 检查样本量
        if sample_size < 10:
            suggestions.append("样本量较小，建议增加样本量以提高统计功效")
        
        # 检查误差线类型一致性
        if error_type == 'UNKNOWN':
            suggestions.append("建议明确标注误差线类型（SE、SD、CI95等）")
        
        # 检查数据质量
        if error_bar > abs(mean):
            suggestions.append("误差线较大，建议检查数据质量或考虑数据转换")
        
        # 检查变异系数
        if error_type == 'SD' and mean != 0:
            cv = abs(error_bar / mean)
            if cv > 1.0:
                suggestions.append("变异系数较大，建议检查数据分布或考虑对数转换")
        
        return suggestions
