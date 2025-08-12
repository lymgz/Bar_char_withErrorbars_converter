#!/usr/bin/env python3
"""
统计转换引擎
执行各种误差线类型到Mean±SD的转换
"""

import math
from typing import Dict, Optional

class StatisticalEngine:
    def __init__(self):
        self.conversion_methods = {
            'SD': self._convert_from_sd,
            'SE': self._convert_from_se,
            'CI95': self._convert_from_ci95,
            'CI99': self._convert_from_ci99,
            '2SE': self._convert_from_2se,
            'ASYMMETRIC': self._convert_from_asymmetric
        }
    
    def convert_to_mean_sd(self, mean: float, error_bar: float, 
                          error_type: str, sample_size: int) -> Dict:
        """
        将误差线数据转换为Mean±SD格式
        
        Args:
            mean: 均值
            error_bar: 误差线数值
            error_type: 误差线类型
            sample_size: 样本量
            
        Returns:
            转换结果字典
        """
        if error_type not in self.conversion_methods:
            raise ValueError(f"不支持的误差线类型: {error_type}")
        
        # 执行转换
        conversion_func = self.conversion_methods[error_type]
        result = conversion_func(mean, error_bar, sample_size)
        
        # 添加元数据
        result.update({
            'original_mean': mean,
            'original_error_bar': error_bar,
            'original_error_type': error_type,
            'sample_size': sample_size,
            'method_used': self._get_method_name(error_type)
        })
        
        return result
    
    def _convert_from_sd(self, mean: float, sd: float, sample_size: int) -> Dict:
        """从标准差转换（直接使用）"""
        se = sd / math.sqrt(sample_size)
        
        return {
            'mean': round(mean, 6),
            'sd': round(sd, 6),
            'se': round(se, 6),
            'conversion_factor': 1.0,
            'conversion_formula': 'SD = SD (直接使用)',
            'quality_score': 1.0  # 最高质量，因为是直接数据
        }
    
    def _convert_from_se(self, mean: float, se: float, sample_size: int) -> Dict:
        """从标准误差转换"""
        sd = se * math.sqrt(sample_size)
        conversion_factor = math.sqrt(sample_size)
        
        return {
            'mean': round(mean, 6),
            'sd': round(sd, 6),
            'se': round(se, 6),
            'conversion_factor': round(conversion_factor, 6),
            'conversion_formula': f'SD = SE × √n = {se:.4f} × √{sample_size}',
            'quality_score': 0.95  # 高质量转换
        }
    
    def _convert_from_ci95(self, mean: float, ci_half_width: float, sample_size: int) -> Dict:
        """从95%置信区间转换"""
        # CI95 = Mean ± 1.96 × SE
        se = ci_half_width / 1.96
        sd = se * math.sqrt(sample_size)
        conversion_factor = math.sqrt(sample_size) / 1.96
        
        return {
            'mean': round(mean, 6),
            'sd': round(sd, 6),
            'se': round(se, 6),
            'conversion_factor': round(conversion_factor, 6),
            'conversion_formula': f'SE = CI95/1.96, SD = SE × √n = {ci_half_width:.4f}/1.96 × √{sample_size}',
            'quality_score': 0.85  # 良好质量转换
        }
    
    def _convert_from_ci99(self, mean: float, ci_half_width: float, sample_size: int) -> Dict:
        """从99%置信区间转换"""
        # CI99 = Mean ± 2.576 × SE
        se = ci_half_width / 2.576
        sd = se * math.sqrt(sample_size)
        conversion_factor = math.sqrt(sample_size) / 2.576
        
        return {
            'mean': round(mean, 6),
            'sd': round(sd, 6),
            'se': round(se, 6),
            'conversion_factor': round(conversion_factor, 6),
            'conversion_formula': f'SE = CI99/2.576, SD = SE × √n = {ci_half_width:.4f}/2.576 × √{sample_size}',
            'quality_score': 0.85  # 良好质量转换
        }
    
    def _convert_from_2se(self, mean: float, two_se: float, sample_size: int) -> Dict:
        """从2倍标准误差转换"""
        se = two_se / 2
        sd = se * math.sqrt(sample_size)
        conversion_factor = math.sqrt(sample_size) / 2
        
        return {
            'mean': round(mean, 6),
            'sd': round(sd, 6),
            'se': round(se, 6),
            'conversion_factor': round(conversion_factor, 6),
            'conversion_formula': f'SE = 2SE/2, SD = SE × √n = {two_se:.4f}/2 × √{sample_size}',
            'quality_score': 0.90  # 高质量转换
        }
    
    def _convert_from_asymmetric(self, mean: float, error_bar: float, sample_size: int) -> Dict:
        """从非对称误差线转换（使用误差线半宽作为近似值）"""
        # 对于非对称误差线，如果只提供了一个数值，我们假设它是误差线的半宽
        # 这保持了与现有功能的兼容性
        sd = error_bar * math.sqrt(sample_size)
        se = error_bar  # 对于非对称情况，SE就是提供的误差线值
        conversion_factor = math.sqrt(sample_size)
        
        return {
            'mean': round(mean, 6),
            'sd': round(sd, 6),
            'se': round(se, 6),
            'conversion_factor': round(conversion_factor, 6),
            'conversion_formula': f'SD = Error_Bar × √n = {error_bar:.4f} × √{sample_size} (非对称近似)',
            'quality_score': 0.75,  # 中等质量，因为是近似值
            'asymmetric_approximation': True
        }
    
    def _get_method_name(self, error_type: str) -> str:
        """获取转换方法名称"""
        method_names = {
            'SD': 'direct_sd',
            'SE': 'se_to_sd',
            'CI95': 'ci95_to_sd',
            'CI99': 'ci99_to_sd',
            '2SE': '2se_to_sd'
        }
        return method_names.get(error_type, 'unknown')
    
    def calculate_confidence_interval(self, mean: float, sd: float, sample_size: int, 
                                    confidence_level: float = 0.95) -> Dict:
        """计算置信区间"""
        se = sd / math.sqrt(sample_size)
        
        # 获取对应的z分数
        z_scores = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576
        }
        z_score = z_scores.get(confidence_level, 1.96)
        
        margin_of_error = z_score * se
        ci_lower = mean - margin_of_error
        ci_upper = mean + margin_of_error
        
        return {
            'confidence_level': confidence_level,
            'margin_of_error': round(margin_of_error, 6),
            'ci_lower': round(ci_lower, 6),
            'ci_upper': round(ci_upper, 6),
            'z_score': z_score
        }
    
    def calculate_effect_size(self, mean1: float, sd1: float, n1: int,
                            mean2: float, sd2: float, n2: int) -> Dict:
        """计算效应量"""
        # Cohen's d
        pooled_sd = math.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / (n1 + n2 - 2))
        cohens_d = (mean1 - mean2) / pooled_sd if pooled_sd > 0 else 0
        
        # Hedges' g (偏差校正的Cohen's d)
        correction_factor = 1 - (3 / (4 * (n1 + n2) - 9))
        hedges_g = cohens_d * correction_factor
        
        # Glass's delta (使用控制组的标准差)
        glass_delta = (mean1 - mean2) / sd2 if sd2 > 0 else 0
        
        return {
            'cohens_d': round(cohens_d, 6),
            'hedges_g': round(hedges_g, 6),
            'glass_delta': round(glass_delta, 6),
            'pooled_sd': round(pooled_sd, 6),
            'effect_size_interpretation': self._interpret_effect_size(abs(cohens_d))
        }
    
    def _interpret_effect_size(self, effect_size: float) -> str:
        """解释效应量大小"""
        if effect_size < 0.2:
            return "微小效应"
        elif effect_size < 0.5:
            return "小效应"
        elif effect_size < 0.8:
            return "中等效应"
        else:
            return "大效应"
    
    def validate_conversion_result(self, result: Dict) -> Dict:
        """验证转换结果的合理性"""
        validation = {
            'is_valid': True,
            'warnings': [],
            'quality_assessment': 'good'
        }
        
        mean = result.get('mean', 0)
        sd = result.get('sd', 0)
        se = result.get('se', 0)
        sample_size = result.get('sample_size', 0)
        
        # 检查基本数值合理性
        if sd <= 0:
            validation['is_valid'] = False
            validation['warnings'].append("标准差必须大于0")
        
        if se <= 0:
            validation['is_valid'] = False
            validation['warnings'].append("标准误差必须大于0")
        
        # 检查SE和SD的关系
        expected_se = sd / math.sqrt(sample_size) if sample_size > 0 else 0
        if abs(se - expected_se) > 0.001:
            validation['warnings'].append("SE和SD的关系可能不一致")
        
        # 检查变异系数
        if mean != 0:
            cv = abs(sd / mean)
            if cv > 2.0:
                validation['warnings'].append("变异系数过大，可能存在异常值")
                validation['quality_assessment'] = 'poor'
            elif cv > 1.0:
                validation['warnings'].append("变异系数较大，数据变异性高")
                validation['quality_assessment'] = 'fair'
        
        # 检查样本量
        if sample_size < 10:
            validation['warnings'].append("样本量较小，结果可靠性有限")
            if validation['quality_assessment'] == 'good':
                validation['quality_assessment'] = 'fair'
        
        return validation
    
    def batch_convert(self, data_list: list) -> Dict:
        """批量转换数据"""
        results = []
        summary = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'conversion_types': {},
            'quality_distribution': {'good': 0, 'fair': 0, 'poor': 0}
        }
        
        for i, data in enumerate(data_list):
            try:
                result = self.convert_to_mean_sd(
                    data['mean'],
                    data['error_bar'],
                    data['error_type'],
                    data['sample_size']
                )
                
                # 验证结果
                validation = self.validate_conversion_result(result)
                result['validation'] = validation
                
                results.append(result)
                summary['successful_conversions'] += 1
                
                # 统计转换类型
                error_type = data['error_type']
                summary['conversion_types'][error_type] = summary['conversion_types'].get(error_type, 0) + 1
                
                # 统计质量分布
                quality = validation['quality_assessment']
                summary['quality_distribution'][quality] += 1
                
            except Exception as e:
                results.append({
                    'error': str(e),
                    'input_data': data,
                    'conversion_failed': True
                })
                summary['failed_conversions'] += 1
            
            summary['total_conversions'] += 1
        
        return {
            'results': results,
            'summary': summary
        }
    
    def get_conversion_info(self, error_type: str) -> Dict:
        """获取转换方法信息"""
        info = {
            'SD': {
                'name': '标准差',
                'formula': 'SD = SD (直接使用)',
                'description': '标准差是衡量数据分散程度的指标，直接使用无需转换',
                'quality': 'highest',
                'common_use': '最常用的变异性指标'
            },
            'SE': {
                'name': '标准误差',
                'formula': 'SD = SE × √n',
                'description': '标准误差是样本均值的标准差，需要乘以√n得到总体标准差',
                'quality': 'high',
                'common_use': '常用于表示均值的精确度'
            },
            'CI95': {
                'name': '95%置信区间',
                'formula': 'SE = CI95/1.96, SD = SE × √n',
                'description': '95%置信区间表示真实均值有95%概率落在此区间内',
                'quality': 'good',
                'common_use': '常用于医学和社会科学研究'
            },
            'CI99': {
                'name': '99%置信区间',
                'formula': 'SE = CI99/2.576, SD = SE × √n',
                'description': '99%置信区间表示真实均值有99%概率落在此区间内',
                'quality': 'good',
                'common_use': '要求更高置信度的研究'
            },
            '2SE': {
                'name': '2倍标准误差',
                'formula': 'SE = 2SE/2, SD = SE × √n',
                'description': '2倍标准误差约等于95%置信区间',
                'quality': 'high',
                'common_use': '一些图表软件的默认误差线'
            }
        }
        
        return info.get(error_type, {
            'name': '未知类型',
            'formula': '无法转换',
            'description': '不支持的误差线类型',
            'quality': 'unknown',
            'common_use': '请检查数据类型'
        })
