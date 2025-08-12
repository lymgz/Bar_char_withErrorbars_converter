#!/usr/bin/env python3
"""
带误差线柱状图数据转换工具
支持多种误差线类型转换为Meta分析标准格式
"""

import csv
import os
import sys
import json
import pandas as pd
import math
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from error_detector import ErrorBarDetector
from statistical_engine import StatisticalEngine

class BarChartConverter:
    def __init__(self):
        self.detector = ErrorBarDetector()
        self.engine = StatisticalEngine()
        self.template_filename = "template.csv"
        self.data_filename = "data.csv"
        
    def generate_template(self, indicators_count: int = 4) -> str:
        """生成CSV模板文件"""
        template_content = []
        
        # 表头说明
        template_content.append(["# 带误差线柱状图数据输入模板"])
        template_content.append(["# 误差线类型: SE(标准误差), SD(标准差), CI95(95%置信区间), CI99(99%置信区间), 2SE(2倍标准误差), ASYMMETRIC(非对称误差线)"])
        template_content.append(["# 非对称误差线格式: Error_Bar_Upper/Error_Bar_Lower (例如: 1.5/0.8)"])
        template_content.append(["# 请在Error_Type行中明确标注误差线类型"])
        template_content.append([""])
        
        # 基线组
        header = ["Baseline"] + [f"Indicator{i+1}" for i in range(indicators_count)]
        template_content.append(header)
        
        data_items = ["Mean", "Error_Bar", "Error_Type", "Sample_Size"]
        for item in data_items:
            row = [item] + [""] * indicators_count
            template_content.append(row)
        
        # 空行分隔
        template_content.append([""] * (indicators_count + 1))
        
        # 干预组
        header = ["Intervention"] + [f"Indicator{i+1}" for i in range(indicators_count)]
        template_content.append(header)
        
        for item in data_items:
            row = [item] + [""] * indicators_count
            template_content.append(row)
        
        # 写入文件
        with open(self.template_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(template_content)
        
        return self.template_filename
    
    def read_csv_data(self, filename: str) -> Dict:
        """读取CSV数据并解析"""
        if not os.path.exists(filename):
            raise FileNotFoundError(f"找不到文件: {filename}")
        
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        return self._parse_csv_structure(rows)
    
    def _parse_csv_structure(self, rows: List[List[str]]) -> Dict:
        """解析CSV结构，支持动态列数"""
        groups = {}
        current_group = None
        current_data = {}
        
        for row in rows:
            if not row or all(cell.strip() == "" for cell in row):
                # 空行，结束当前组
                if current_group and current_data:
                    groups[current_group] = current_data
                    current_data = {}
                continue
            
            # 跳过注释行
            if row[0].startswith('#'):
                continue
            
            first_cell = row[0].strip()
            
            # 检查是否是组标题
            if first_cell in ["基线组", "干预组", "Baseline", "Intervention"] or first_cell.endswith("组"):
                if current_group and current_data:
                    groups[current_group] = current_data
                
                current_group = first_cell
                current_data = {}
                
                # 检测指标数量
                indicators = [cell.strip() for cell in row[1:] if cell.strip()]
                current_data['indicators'] = indicators
                current_data['indicator_count'] = len(indicators)
                current_data['data'] = {}
                continue
            
            # 数据行
            data_labels = ["Mean", "Error_Bar", "Error_Type", "Sample_Size", "均值", "误差线", "误差类型", "样本量"]
            
            if current_group and first_cell in data_labels:
                # 标准化标签为英文
                label_mapping = {
                    "均值": "Mean",
                    "误差线": "Error_Bar", 
                    "误差类型": "Error_Type",
                    "样本量": "Sample_Size"
                }
                normalized_label = label_mapping.get(first_cell, first_cell)
                
                values = []
                for cell in row[1:]:
                    cell_value = cell.strip()
                    if cell_value:
                        if normalized_label in ["Mean", "Sample_Size"]:
                            try:
                                values.append(float(cell_value))
                            except ValueError:
                                values.append(None)
                        elif normalized_label == "Error_Bar":
                            # 支持非对称误差线格式 "upper/lower"
                            if '/' in cell_value:
                                values.append(cell_value)  # 保持字符串格式
                            else:
                                try:
                                    values.append(float(cell_value))
                                except ValueError:
                                    values.append(None)
                        else:  # Error_Type
                            values.append(cell_value.upper())
                    else:
                        values.append(None)
                
                current_data['data'][normalized_label] = values
        
        # 处理最后一组
        if current_group and current_data:
            groups[current_group] = current_data
        
        return groups
    
    def analyze_error_types(self, groups: Dict) -> Dict:
        """分析误差线类型和数据质量"""
        analysis = {}
        
        for group_name, group_data in groups.items():
            indicators_analysis = []
            indicator_count = group_data.get('indicator_count', 0)
            
            for i in range(indicator_count):
                indicator_data = self._extract_indicator_data(group_data, i)
                error_type = indicator_data.get('Error_Type', 'UNKNOWN')
                
                # 检测和验证误差线类型
                detected_type, confidence = self.detector.detect_error_type(
                    indicator_data.get('Mean'),
                    indicator_data.get('Error_Bar'),
                    error_type,
                    indicator_data.get('Sample_Size')
                )
                
                indicators_analysis.append({
                    'indicator_index': i + 1,
                    'indicator_name': group_data['indicators'][i] if i < len(group_data['indicators']) else f"指标{i+1}",
                    'declared_type': error_type,
                    'detected_type': detected_type,
                    'confidence': confidence,
                    'data_complete': self._check_data_completeness(indicator_data),
                    'data': indicator_data
                })
            
            analysis[group_name] = {
                'indicators': indicators_analysis,
                'indicator_count': indicator_count,
                'overall_quality': self._assess_group_quality(indicators_analysis)
            }
        
        return analysis
    
    def _extract_indicator_data(self, group_data: Dict, indicator_index: int) -> Dict:
        """提取特定指标的数据"""
        indicator_data = {}
        
        for data_type, values in group_data['data'].items():
            if indicator_index < len(values) and values[indicator_index] is not None:
                indicator_data[data_type] = values[indicator_index]
        
        # 处理非对称误差线格式
        if 'Error_Type' in indicator_data and indicator_data['Error_Type'] == 'ASYMMETRIC':
            if 'Error_Bar' in indicator_data:
                error_bar_value = indicator_data['Error_Bar']
                # 如果是字符串格式 "upper/lower"，转换为平均值
                if isinstance(error_bar_value, str):
                    try:
                        parts = error_bar_value.split('/')
                        if len(parts) == 2:
                            upper = float(parts[0])
                            lower = float(parts[1])
                            # 使用平均值作为误差线值
                            indicator_data['Error_Bar'] = (upper + lower) / 2
                            # 保存原始非对称值用于参考
                            indicator_data['Asymmetric_Error_Upper'] = upper
                            indicator_data['Asymmetric_Error_Lower'] = lower
                    except (ValueError, AttributeError):
                        pass
        
        return indicator_data
    
    def _check_data_completeness(self, indicator_data: Dict) -> bool:
        """检查数据完整性"""
        required_fields = ['Mean', 'Error_Bar', 'Error_Type', 'Sample_Size']
        return all(field in indicator_data and indicator_data[field] is not None for field in required_fields)
    
    def _assess_group_quality(self, indicators_analysis: List[Dict]) -> str:
        """评估组数据质量"""
        if not indicators_analysis:
            return "无数据"
        
        complete_count = sum(1 for ind in indicators_analysis if ind['data_complete'])
        total_count = len(indicators_analysis)
        
        if complete_count == total_count:
            return "完整"
        elif complete_count >= total_count * 0.8:
            return "良好"
        elif complete_count >= total_count * 0.5:
            return "一般"
        else:
            return "不完整"
    
    def convert_bar_data(self, filename: str, verbose: bool = False) -> Dict:
        """转换柱状图数据"""
        # 读取数据
        groups = self.read_csv_data(filename)
        
        # 分析误差线类型
        analysis = self.analyze_error_types(groups)
        
        # 执行转换
        results = {}
        
        for group_name, group_analysis in analysis.items():
            group_results = []
            
            if verbose:
                print(f"\n=== {group_name} 分析 ===")
                print(f"检测到 {group_analysis['indicator_count']} 个指标")
                print(f"数据质量: {group_analysis['overall_quality']}")
            
            for indicator in group_analysis['indicators']:
                if not indicator['data_complete']:
                    if verbose:
                        print(f"跳过 {indicator['indicator_name']}: 数据不完整")
                    continue
                
                indicator_data = indicator['data']
                
                # 执行统计转换
                try:
                    result = self.engine.convert_to_mean_sd(
                        mean=indicator_data['Mean'],
                        error_bar=indicator_data['Error_Bar'],
                        error_type=indicator['detected_type'],
                        sample_size=int(indicator_data['Sample_Size'])
                    )
                    
                    result.update({
                        'indicator_name': indicator['indicator_name'],
                        'declared_type': indicator['declared_type'],
                        'detected_type': indicator['detected_type'],
                        'confidence': indicator['confidence'],
                        'conversion_method': result.get('method_used', 'unknown')
                    })
                    
                    group_results.append(result)
                    
                    if verbose:
                        print(f"{indicator['indicator_name']}: Mean={result['mean']:.3f}, SD={result['sd']:.3f} "
                              f"(类型: {indicator['detected_type']}, 置信度: {indicator['confidence']:.2f})")
                
                except Exception as e:
                    if verbose:
                        print(f"转换失败 {indicator['indicator_name']}: {e}")
            
            results[group_name] = group_results
        
        return {
            'results': results,
            'analysis': analysis,
            'summary': self._generate_summary(analysis, results)
        }
    
    def _generate_summary(self, analysis: Dict, results: Dict) -> Dict:
        """生成分析摘要"""
        total_indicators = sum(group['indicator_count'] for group in analysis.values())
        successful_conversions = sum(len(group_results) for group_results in results.values())
        
        # 统计误差线类型分布
        type_distribution = {}
        for group_analysis in analysis.values():
            for indicator in group_analysis['indicators']:
                detected_type = indicator['detected_type']
                type_distribution[detected_type] = type_distribution.get(detected_type, 0) + 1
        
        return {
            'total_groups': len(analysis),
            'total_indicators': total_indicators,
            'successful_conversions': successful_conversions,
            'conversion_rate': successful_conversions / total_indicators if total_indicators > 0 else 0,
            'error_type_distribution': type_distribution,
            'recommendations': self._generate_recommendations(analysis)
        }
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        for group_name, group_analysis in analysis.items():
            incomplete_indicators = [
                ind['indicator_name'] for ind in group_analysis['indicators'] 
                if not ind['data_complete']
            ]
            
            if incomplete_indicators:
                recommendations.append(
                    f"{group_name}: 补充{', '.join(incomplete_indicators)}的完整数据"
                )
            
            # 检查误差线类型一致性
            declared_types = set(ind['declared_type'] for ind in group_analysis['indicators'] 
                                if ind['declared_type'] != 'UNKNOWN')
            if len(declared_types) > 1:
                recommendations.append(
                    f"{group_name}: 建议统一误差线类型，当前混合使用了{', '.join(declared_types)}"
                )
        
        return recommendations
    
    def perform_group_comparisons(self, result_data: Dict, comparison_type: str = "intervention-baseline", 
                                confidence_level: float = 0.95) -> Dict:
        """执行组间比较分析"""
        results = result_data['results']
        comparisons = []
        
        if comparison_type in ["all", "intervention-baseline"]:
            # 干预组 vs 基线组比较
            baseline_results = results.get('Baseline', results.get('基线组', []))
            intervention_results = results.get('Intervention', results.get('干预组', []))
            
            # 按指标配对比较
            for i, baseline in enumerate(baseline_results):
                if i < len(intervention_results):
                    intervention = intervention_results[i]
                    comparison = self._calculate_group_comparison(
                        intervention, baseline, confidence_level
                    )
                    comparison.update({
                        'comparison_id': f"Intervention_vs_Baseline_{baseline['indicator_name']}",
                        'group1_name': 'Intervention',
                        'group2_name': 'Baseline',
                        'indicator_name': baseline['indicator_name'],
                        'group1_data': intervention,
                        'group2_data': baseline
                    })
                    comparisons.append(comparison)
        
        return {
            'comparisons': comparisons,
            'comparison_type': comparison_type,
            'confidence_level': confidence_level,
            'total_comparisons': len(comparisons),
            'significant_comparisons': sum(1 for c in comparisons if c['significant'])
        }
    
    def _calculate_group_comparison(self, group1_data: Dict, group2_data: Dict, 
                                  confidence_level: float = 0.95) -> Dict:
        """计算两组间的差异分析"""
        delta_mean = group1_data['mean'] - group2_data['mean']
        
        # 计算差异的标准差
        sd_diff = math.sqrt(
            (group1_data['sd']**2 / group1_data['sample_size']) + 
            (group2_data['sd']**2 / group2_data['sample_size'])
        )
        
        # 计算置信区间
        z_score = self._get_z_score(confidence_level)
        ci_lower = delta_mean - z_score * sd_diff
        ci_upper = delta_mean + z_score * sd_diff
        
        # 计算效应量 (Cohen's d)
        pooled_sd = math.sqrt(
            ((group1_data['sample_size'] - 1) * group1_data['sd']**2 + 
             (group2_data['sample_size'] - 1) * group2_data['sd']**2) / 
            (group1_data['sample_size'] + group2_data['sample_size'] - 2)
        )
        cohens_d = delta_mean / pooled_sd if pooled_sd > 0 else 0
        
        # Hedges' g (偏差校正的Cohen's d)
        correction_factor = 1 - (3 / (4 * (group1_data['sample_size'] + group2_data['sample_size']) - 9))
        hedges_g = cohens_d * correction_factor
        
        # 计算p值 (双尾t检验)
        df = group1_data['sample_size'] + group2_data['sample_size'] - 2
        t_stat = delta_mean / sd_diff if sd_diff > 0 else 0
        p_value = self._calculate_p_value(abs(t_stat), df)
        
        # 判断显著性
        alpha = 1 - confidence_level
        significant = p_value < alpha
        
        return {
            'delta_mean': round(delta_mean, 4),
            'sd_diff': round(sd_diff, 4),
            'ci_lower': round(ci_lower, 4),
            'ci_upper': round(ci_upper, 4),
            'confidence_level': confidence_level,
            'cohens_d': round(cohens_d, 4),
            'hedges_g': round(hedges_g, 4),
            'p_value': round(p_value, 4),
            'significant': significant,
            't_statistic': round(t_stat, 4),
            'degrees_of_freedom': df,
            'interpretation': self._interpret_comparison(delta_mean, ci_lower, ci_upper, significant)
        }
    
    def _get_z_score(self, confidence_level: float) -> float:
        """获取对应置信水平的z分数"""
        z_scores = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576
        }
        return z_scores.get(confidence_level, 1.96)
    
    def _calculate_p_value(self, t_stat: float, df: int) -> float:
        """简化的p值计算（双尾检验）"""
        if df <= 0:
            return 1.0
        
        # 使用近似公式
        if t_stat == 0:
            return 1.0
        elif t_stat > 4:
            return 0.0001
        elif t_stat > 3:
            return 0.01
        elif t_stat > 2:
            return 0.05
        elif t_stat > 1.5:
            return 0.1
        else:
            return 0.2
    
    def _interpret_comparison(self, delta_mean: float, ci_lower: float, 
                            ci_upper: float, significant: bool) -> str:
        """解释比较结果"""
        if significant:
            if ci_lower > 0:
                return "显著差异：组1显著高于组2"
            elif ci_upper < 0:
                return "显著差异：组1显著低于组2"
            else:
                return "显著差异：但置信区间包含0"
        else:
            return "无显著差异"
    
    def generate_meta_analysis_formats(self, result_data: Dict, comparison_data: Dict = None, 
                                     output_dir: str = "results") -> Dict[str, str]:
        """生成多种Meta分析标准格式"""
        self.ensure_results_dir(output_dir)
        saved_files = {}
        
        # 通用Meta分析格式
        universal_data = self._create_universal_meta_format(result_data, comparison_data)
        universal_path = os.path.join(output_dir, "meta_universal.csv")
        universal_path = self.get_available_filename(universal_path)
        
        df_universal = pd.DataFrame(universal_data)
        df_universal.to_csv(universal_path, index=False, encoding='utf-8')
        saved_files['universal'] = universal_path
        
        # RevMan格式
        revman_data = self._create_revman_format(result_data)
        revman_path = os.path.join(output_dir, "meta_revman.csv")
        revman_path = self.get_available_filename(revman_path)
        
        df_revman = pd.DataFrame(revman_data)
        df_revman.to_csv(revman_path, index=False, encoding='utf-8')
        saved_files['revman'] = revman_path
        
        # R Meta包格式
        if comparison_data:
            r_meta_data = self._create_r_meta_format(comparison_data)
            r_path = os.path.join(output_dir, "meta_r.csv")
            r_path = self.get_available_filename(r_path)
            
            df_r = pd.DataFrame(r_meta_data)
            df_r.to_csv(r_path, index=False, encoding='utf-8')
            saved_files['r_meta'] = r_path
        
        return saved_files
    
    def _create_universal_meta_format(self, result_data: Dict, comparison_data: Dict = None) -> List[Dict]:
        """创建通用Meta分析格式"""
        universal_data = []
        
        if comparison_data and comparison_data['comparisons']:
            for comparison in comparison_data['comparisons']:
                if 'Intervention_vs_Baseline' in comparison['comparison_id']:
                    universal_data.append({
                        'Study_ID': comparison['indicator_name'],
                        'Comparison_Type': 'Intervention-Baseline',
                        'Intervention_Mean': comparison['group1_data']['mean'],
                        'Intervention_SD': comparison['group1_data']['sd'],
                        'Intervention_N': comparison['group1_data']['sample_size'],
                        'Control_Mean': comparison['group2_data']['mean'],
                        'Control_SD': comparison['group2_data']['sd'],
                        'Control_N': comparison['group2_data']['sample_size'],
                        'Mean_Difference': comparison['delta_mean'],
                        'SD_Difference': comparison['sd_diff'],
                        'Effect_Size_Cohens_d': comparison['cohens_d'],
                        'Effect_Size_Hedges_g': comparison['hedges_g'],
                        'SE_Mean_Diff': comparison['sd_diff'],
                        '95_CI_Lower': comparison['ci_lower'],
                        '95_CI_Upper': comparison['ci_upper'],
                        'P_Value': comparison['p_value'],
                        'Significant': 'Yes' if comparison['significant'] else 'No',
                        'Error_Bar_Type': comparison['group1_data']['detected_type'],
                        'Conversion_Method': comparison['group1_data']['conversion_method'],
                        'Notes': comparison['interpretation']
                    })
        else:
            # 如果没有比较数据，只输出基础转换结果
            for group_name, group_results in result_data['results'].items():
                for result in group_results:
                    universal_data.append({
                        'Study_ID': result['indicator_name'],
                        'Group': group_name,
                        'Mean': result['mean'],
                        'SD': result['sd'],
                        'Sample_Size': result['sample_size'],
                        'Error_Bar_Type': result['detected_type'],
                        'Conversion_Method': result['conversion_method'],
                        'Confidence': result['confidence']
                    })
        
        return universal_data
    
    def _create_revman_format(self, result_data: Dict) -> List[Dict]:
        """创建RevMan格式"""
        revman_data = []
        results = result_data['results']
        
        baseline_results = results.get('Baseline', results.get('基线组', []))
        intervention_results = results.get('Intervention', results.get('干预组', []))
        
        for i, baseline in enumerate(baseline_results):
            if i < len(intervention_results):
                intervention = intervention_results[i]
                revman_data.append({
                    'Study_ID': baseline['indicator_name'],
                    'Intervention_Mean': intervention['mean'],
                    'Intervention_SD': intervention['sd'],
                    'Intervention_N': intervention['sample_size'],
                    'Control_Mean': baseline['mean'],
                    'Control_SD': baseline['sd'],
                    'Control_N': baseline['sample_size']
                })
        
        return revman_data
    
    def _create_r_meta_format(self, comparison_data: Dict) -> List[Dict]:
        """创建R Meta包格式"""
        r_data = []
        
        for comparison in comparison_data['comparisons']:
            if 'Intervention_vs_Baseline' in comparison['comparison_id']:
                r_data.append({
                    'Study': comparison['indicator_name'],
                    'TE': comparison['delta_mean'],
                    'seTE': comparison['sd_diff'],
                    'n.e': comparison['group1_data']['sample_size'],
                    'n.c': comparison['group2_data']['sample_size'],
                    'mean.e': comparison['group1_data']['mean'],
                    'sd.e': comparison['group1_data']['sd'],
                    'mean.c': comparison['group2_data']['mean'],
                    'sd.c': comparison['group2_data']['sd']
                })
        
        return r_data
    
    def is_file_locked(self, filepath: str) -> bool:
        """检测文件是否被占用"""
        if not os.path.exists(filepath):
            return False
        
        try:
            with open(filepath, 'a'):
                return False
        except (IOError, OSError):
            return True
    
    def get_available_filename(self, base_filename: str) -> str:
        """获取可用的文件名，处理文件占用情况"""
        name, ext = os.path.splitext(base_filename)
        
        if not self.is_file_locked(base_filename):
            return base_filename
        
        for i in range(1, 100):
            suffix = f"_{i:02d}"
            new_filename = f"{name}{suffix}{ext}"
            if not self.is_file_locked(new_filename):
                return new_filename
        
        return f"{name}_01{ext}"
    
    def ensure_results_dir(self, output_dir: str = "results") -> str:
        """确保结果目录存在"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir
    
    def save_to_excel(self, result_data: Dict, comparison_data: Dict = None, 
                     output_dir: str = "results", base_filename: str = "bar_results.xlsx") -> str:
        """保存结果到Excel文件"""
        self.ensure_results_dir(output_dir)
        filepath = os.path.join(output_dir, base_filename)
        final_filepath = self.get_available_filename(filepath)
        
        with pd.ExcelWriter(final_filepath, engine='openpyxl') as writer:
            # Sheet1: 转换结果
            results_data = []
            for group_name, group_results in result_data['results'].items():
                for result in group_results:
                    results_data.append({
                        'Group': group_name,
                        'Indicator': result['indicator_name'],
                        'Mean': round(result['mean'], 4),
                        'SD': round(result['sd'], 4),
                        'Sample_Size': result['sample_size'],
                        'Error_Bar_Type': result['detected_type'],
                        'Declared_Type': result['declared_type'],
                        'Confidence': round(result['confidence'], 3),
                        'Conversion_Method': result['conversion_method']
                    })
            
            if results_data:
                df_results = pd.DataFrame(results_data)
                df_results.to_excel(writer, sheet_name='转换结果', index=False)
            
            # Sheet2: 组间比较结果 (如果有比较数据)
            if comparison_data and comparison_data['comparisons']:
                comparison_results = []
                for comp in comparison_data['comparisons']:
                    comparison_results.append({
                        'Comparison': f"{comp['group1_name']} vs {comp['group2_name']}",
                        'Indicator': comp['indicator_name'],
                        'ΔMean': comp['delta_mean'],
                        'SD_diff': comp['sd_diff'],
                        '95%_CI_Lower': comp['ci_lower'],
                        '95%_CI_Upper': comp['ci_upper'],
                        'Cohens_d': comp['cohens_d'],
                        'Hedges_g': comp['hedges_g'],
                        'P_Value': comp['p_value'],
                        'Significant': 'Yes' if comp['significant'] else 'No',
                        'Interpretation': comp['interpretation']
                    })
                
                df_comparisons = pd.DataFrame(comparison_results)
                df_comparisons.to_excel(writer, sheet_name='组间比较结果', index=False)
            
            # Sheet3: 数据质量分析
            quality_data = []
            for group_name, group_analysis in result_data['analysis'].items():
                quality_data.append({
                    'Group': group_name,
                    'Total_Indicators': group_analysis['indicator_count'],
                    'Overall_Quality': group_analysis['overall_quality']
                })
            
            if quality_data:
                df_quality = pd.DataFrame(quality_data)
                df_quality.to_excel(writer, sheet_name='数据质量分析', index=False)
            
            # Sheet4: 摘要信息
            summary = result_data['summary']
            summary_data = [
                {'项目': '总组数', '值': summary['total_groups']},
                {'项目': '总指标数', '值': summary['total_indicators']},
                {'项目': '成功转换数', '值': summary['successful_conversions']},
                {'项目': '转换成功率', '值': f"{summary['conversion_rate']*100:.1f}%"},
                {'项目': '处理时间', '值': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            ]
            
            # 添加误差线类型分布
            for error_type, count in summary['error_type_distribution'].items():
                summary_data.append({'项目': f'误差线类型_{error_type}', '值': count})
            
            # 如果有比较数据，添加比较摘要
            if comparison_data:
                summary_data.extend([
                    {'项目': '总比较数', '值': comparison_data['total_comparisons']},
                    {'项目': '显著比较数', '值': comparison_data['significant_comparisons']},
                    {'项目': '比较类型', '值': comparison_data['comparison_type']},
                    {'项目': '置信水平', '值': f"{comparison_data['confidence_level']*100}%"}
                ])
            
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='摘要信息', index=False)
            
            # 如果有建议，添加到改进建议工作表
            if result_data['summary']['recommendations']:
                rec_data = [{'建议': rec} for rec in result_data['summary']['recommendations']]
                df_rec = pd.DataFrame(rec_data)
                df_rec.to_excel(writer, sheet_name='改进建议', index=False)
        
        return final_filepath
    
    def save_to_csv(self, result_data: Dict, output_dir: str = "results", 
                   base_filename: str = "bar_results_summary.csv") -> str:
        """保存摘要结果到CSV文件"""
        self.ensure_results_dir(output_dir)
        filepath = os.path.join(output_dir, base_filename)
        final_filepath = self.get_available_filename(filepath)
        
        # 准备CSV数据
        csv_data = []
        for group_name, group_results in result_data['results'].items():
            for result in group_results:
                csv_data.append({
                    'Group': group_name,
                    'Indicator': result['indicator_name'],
                    'Mean': round(result['mean'], 4),
                    'SD': round(result['sd'], 4),
                    'Sample_Size': result['sample_size'],
                    'Error_Bar_Type': result['detected_type'],
                    'Conversion_Method': result['conversion_method'],
                    'Confidence': round(result['confidence'], 3)
                })
        
        # 写入CSV
        if csv_data:
            df = pd.DataFrame(csv_data)
            df.to_csv(final_filepath, index=False, encoding='utf-8')
        
        return final_filepath


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='带误差线柱状图数据转换工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用步骤:
  1. 生成模板: python bar_converter.py --generate-template
  2. 填写数据: 编辑 template.csv，保存为 data.csv
  3. 转换数据: python bar_converter.py --convert data.csv
  
误差线类型支持:
  SE    - 标准误差
  SD    - 标准差
  CI95  - 95%置信区间
  CI99  - 99%置信区间
  2SE   - 2倍标准误差
  
示例:
  python bar_converter.py --generate-template --indicators 6
  python bar_converter.py --convert data.csv --verbose
  python bar_converter.py --convert data.csv --compare-groups --meta-analysis-format
        """
    )
    
    parser.add_argument('--generate-template', action='store_true', help='生成CSV模板')
    parser.add_argument('--indicators', type=int, default=4, help='模板中的指标数量 (默认: 4)')
    parser.add_argument('--convert', help='转换CSV文件')
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    parser.add_argument('--json', action='store_true', help='JSON格式输出')
    parser.add_argument('--output-dir', default='results', help='输出目录 (默认: results)')
    parser.add_argument('--output-name', default='bar_results', help='输出文件基础名称 (默认: bar_results)')
    parser.add_argument('--no-csv', action='store_true', help='不生成CSV摘要文件')
    
    # 组间比较功能
    parser.add_argument('--compare-groups', action='store_true', help='启用组间比较功能')
    parser.add_argument('--comparison-type', choices=['all', 'intervention-baseline'], 
                       default='intervention-baseline', help='比较类型 (默认: intervention-baseline)')
    parser.add_argument('--confidence-level', type=float, default=0.95, 
                       help='置信水平 (默认: 0.95)')
    parser.add_argument('--meta-analysis-format', action='store_true', 
                       help='生成Meta分析标准格式文件')
    
    args = parser.parse_args()
    
    converter = BarChartConverter()
    
    try:
        if args.generate_template:
            filename = converter.generate_template(args.indicators)
            print(f"✓ 已生成模板文件: {filename}")
            print(f"  支持 {args.indicators} 个指标")
            print(f"  请填写数据后保存为 data.csv")
            print(f"  支持的误差线类型: SE, SD, CI95, CI99, 2SE")
            return
        
        if args.convert:
            print("=== 带误差线柱状图数据转换工具 ===\n")
            print(f"处理文件: {args.convert}")
            
            result = converter.convert_bar_data(args.convert, args.verbose)
            
            # 执行组间比较（如果启用）
            comparison_data = None
            if args.compare_groups:
                print(f"\n正在执行组间比较分析...")
                comparison_data = converter.perform_group_comparisons(
                    result, 
                    args.comparison_type, 
                    args.confidence_level
                )
                
                if not args.json:
                    print_comparison_results(comparison_data, args.verbose)
            
            if args.json:
                output_data = result.copy()
                if comparison_data:
                    output_data['comparisons'] = comparison_data
                print(json.dumps(output_data, indent=2, ensure_ascii=False))
            else:
                print_results(result, args.verbose)
            
            # 强制保存结果
            print(f"\n正在保存结果...")
            try:
                # 保存基础结果（包含比较数据）
                excel_filename = f"{args.output_name}.xlsx"
                excel_path = converter.save_to_excel(
                    result, 
                    comparison_data, 
                    args.output_dir, 
                    excel_filename
                )
                
                saved_files = {'excel': excel_path}
                
                # 保存CSV摘要文件
                if not args.no_csv:
                    csv_filename = f"{args.output_name}_summary.csv"
                    csv_path = converter.save_to_csv(result, args.output_dir, csv_filename)
                    saved_files['csv'] = csv_path
                
                # 生成Meta分析格式文件（如果启用）
                if args.meta_analysis_format:
                    meta_files = converter.generate_meta_analysis_formats(
                        result, comparison_data, args.output_dir
                    )
                    saved_files.update(meta_files)
                
                print(f"\n✓ 结果已保存:")
                print(f"  📊 详细结果: {saved_files['excel']}")
                if 'csv' in saved_files:
                    print(f"  📋 摘要结果: {saved_files['csv']}")
                
                if args.meta_analysis_format:
                    print(f"  📈 Meta分析格式:")
                    for format_name, file_path in meta_files.items():
                        print(f"    - {format_name}: {file_path}")
                
                print(f"\n文件说明:")
                print(f"- Excel文件包含完整分析和多个工作表")
                if comparison_data:
                    print(f"- 包含组间比较结果和置信区间分析")
                if 'csv' in saved_files:
                    print(f"- CSV文件为简化摘要，便于导入其他软件")
                if args.meta_analysis_format:
                    print(f"- Meta分析格式文件可直接导入RevMan、R等软件")
                
            except Exception as save_error:
                print(f"⚠️  保存文件时出现问题: {save_error}")
                print(f"结果已在屏幕上显示，请手动保存")
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def print_results(result: Dict, verbose: bool = False):
    """打印结果"""
    analysis = result['analysis']
    results = result['results']
    summary = result['summary']
    
    print("=" * 60)
    print("误差线类型分析")
    print("=" * 60)
    
    for group_name, group_analysis in analysis.items():
        print(f"\n{group_name}:")
        for indicator in group_analysis['indicators']:
            status = "✓ 完整" if indicator['data_complete'] else "❌ 不完整"
            print(f"  {indicator['indicator_name']}: {status}")
            print(f"    声明类型: {indicator['declared_type']}")
            print(f"    检测类型: {indicator['detected_type']} (置信度: {indicator['confidence']:.2f})")
        
        print(f"  整体质量: {group_analysis['overall_quality']}")
    
    print(f"\n误差线类型分布:")
    for error_type, count in summary['error_type_distribution'].items():
        print(f"  {error_type}: {count}个")
    
    print(f"\n转换成功率: {summary['conversion_rate']*100:.1f}% ({summary['successful_conversions']}/{summary['total_indicators']})")
    
    if summary['recommendations']:
        print(f"\n改进建议:")
        for rec in summary['recommendations']:
            print(f"  • {rec}")
    
    print("\n" + "=" * 60)
    print("转换结果")
    print("=" * 60)
    
    for group_name, group_results in results.items():
        print(f"\n{group_name}:")
        for result in group_results:
            print(f"  {result['indicator_name']}: Mean={result['mean']:.3f}, "
                  f"SD={result['sd']:.3f}")
            if verbose:
                print(f"    方法: {result['conversion_method']}, "
                      f"类型: {result['detected_type']}, 置信度: {result['confidence']:.2f}")


def print_comparison_results(comparison_data: Dict, verbose: bool = False):
    """打印组间比较结果"""
    print("\n" + "=" * 60)
    print("组间比较分析")
    print("=" * 60)
    
    print(f"\n比较类型: {comparison_data['comparison_type']}")
    print(f"置信水平: {comparison_data['confidence_level']*100}%")
    print(f"总比较数: {comparison_data['total_comparisons']}")
    print(f"显著比较数: {comparison_data['significant_comparisons']}")
    
    if comparison_data['comparisons']:
        print(f"\n详细比较结果:")
        print("-" * 80)
        
        for comp in comparison_data['comparisons']:
            print(f"\n📊 {comp['group1_name']} vs {comp['group2_name']} ({comp['indicator_name']})")
            print(f"   ΔMean = {comp['delta_mean']:.4f}")
            print(f"   SD_diff = {comp['sd_diff']:.4f}")
            print(f"   95% CI: [{comp['ci_lower']:.4f}, {comp['ci_upper']:.4f}]")
            print(f"   Cohen's d = {comp['cohens_d']:.4f}")
            print(f"   P值 = {comp['p_value']:.4f}")
            
            # 显著性标记
            if comp['significant']:
                print(f"   ✓ {comp['interpretation']}")
            else:
                print(f"   ○ {comp['interpretation']}")
            
            if verbose:
                print(f"   详细信息:")
                print(f"     - Hedges' g = {comp['hedges_g']:.4f}")
                print(f"     - t统计量 = {comp['t_statistic']:.4f}")
                print(f"     - 自由度 = {comp['degrees_of_freedom']}")
    
    print("\n" + "=" * 60)
    print("比较结果摘要")
    print("=" * 60)
    
    # 按显著性分组显示
    significant_comps = [c for c in comparison_data['comparisons'] if c['significant']]
    non_significant_comps = [c for c in comparison_data['comparisons'] if not c['significant']]
    
    if significant_comps:
        print(f"\n✓ 显著差异 ({len(significant_comps)}个):")
        for comp in significant_comps:
            direction = "↑" if comp['delta_mean'] > 0 else "↓"
            print(f"  {direction} {comp['indicator_name']}: ΔMean={comp['delta_mean']:.3f} (p={comp['p_value']:.3f})")
    
    if non_significant_comps:
        print(f"\n○ 无显著差异 ({len(non_significant_comps)}个):")
        for comp in non_significant_comps:
            print(f"    {comp['indicator_name']}: ΔMean={comp['delta_mean']:.3f} (p={comp['p_value']:.3f})")


if __name__ == "__main__":
    main()
