#!/usr/bin/env python3
"""
带误差线柱状图转换器测试脚本
"""

import os
import sys
import pandas as pd
from bar_converter import BarChartConverter

def test_basic_functionality():
    """测试基本功能"""
    print("=== 测试基本功能 ===")
    
    converter = BarChartConverter()
    
    # 测试模板生成
    print("1. 测试模板生成...")
    template_file = converter.generate_template(6)
    assert os.path.exists(template_file), "模板文件未生成"
    print(f"   ✓ 模板文件已生成: {template_file}")
    
    # 测试数据读取
    print("2. 测试数据读取...")
    try:
        groups = converter.read_csv_data("data.csv")
        assert len(groups) >= 2, "数据组数不足"
        print(f"   ✓ 成功读取 {len(groups)} 个数据组")
    except Exception as e:
        print(f"   ✗ 数据读取失败: {e}")
        return False
    
    # 测试数据分析
    print("3. 测试数据分析...")
    try:
        analysis = converter.analyze_error_types(groups)
        assert len(analysis) >= 2, "分析结果组数不足"
        print(f"   ✓ 成功分析 {len(analysis)} 个数据组")
    except Exception as e:
        print(f"   ✗ 数据分析失败: {e}")
        return False
    
    # 测试数据转换
    print("4. 测试数据转换...")
    try:
        result = converter.convert_bar_data("data.csv")
        assert 'results' in result, "转换结果格式错误"
        print(f"   ✓ 成功转换数据，共 {result['summary']['total_indicators']} 个指标")
    except Exception as e:
        print(f"   ✗ 数据转换失败: {e}")
        return False
    
    return True

def test_asymmetric_error_bars():
    """测试非对称误差线功能"""
    print("\n=== 测试非对称误差线功能 ===")
    
    converter = BarChartConverter()
    
    # 测试非对称误差线解析
    print("1. 测试非对称误差线解析...")
    try:
        groups = converter.read_csv_data("data.csv")
        baseline_data = groups.get('Baseline', groups.get('基线组'))
        if baseline_data:
            indicators = baseline_data.get('indicators', [])
            data = baseline_data.get('data', {})
            
            # 检查是否包含非对称误差线
            error_types = data.get('Error_Type', [])
            asymmetric_found = any(et == 'ASYMMETRIC' for et in error_types)
            
            if asymmetric_found:
                print("   ✓ 成功检测到非对称误差线")
            else:
                print("   ○ 未找到非对称误差线数据")
        else:
            print("   ✗ 未找到基线组数据")
    except Exception as e:
        print(f"   ✗ 非对称误差线测试失败: {e}")
        return False
    
    return True

def test_group_comparisons():
    """测试组间比较功能"""
    print("\n=== 测试组间比较功能 ===")
    
    converter = BarChartConverter()
    
    # 测试组间比较
    print("1. 测试组间比较...")
    try:
        result = converter.convert_bar_data("data.csv")
        comparison_data = converter.perform_group_comparisons(result)
        
        if comparison_data and comparison_data['comparisons']:
            print(f"   ✓ 成功执行组间比较，共 {len(comparison_data['comparisons'])} 个比较")
            print(f"   ✓ 其中 {comparison_data['significant_comparisons']} 个比较具有显著性")
        else:
            print("   ○ 未生成比较结果")
    except Exception as e:
        print(f"   ✗ 组间比较测试失败: {e}")
        return False
    
    return True

def test_meta_analysis_formats():
    """测试Meta分析格式生成功能"""
    print("\n=== 测试Meta分析格式生成功能 ===")
    
    converter = BarChartConverter()
    
    # 测试Meta分析格式生成
    print("1. 测试Meta分析格式生成...")
    try:
        result = converter.convert_bar_data("data.csv")
        comparison_data = converter.perform_group_comparisons(result)
        
        # 生成Meta分析格式
        meta_files = converter.generate_meta_analysis_formats(result, comparison_data)
        
        if meta_files:
            print(f"   ✓ 成功生成 {len(meta_files)} 种Meta分析格式:")
            for format_name, file_path in meta_files.items():
                if os.path.exists(file_path):
                    print(f"     - {format_name}: {file_path}")
                else:
                    print(f"     - {format_name}: 文件未生成")
        else:
            print("   ○ 未生成Meta分析格式文件")
    except Exception as e:
        print(f"   ✗ Meta分析格式测试失败: {e}")
        return False
    
    return True

def test_chinese_support():
    """测试中文支持"""
    print("\n=== 测试中文支持 ===")
    
    converter = BarChartConverter()
    
    # 测试中文数据读取
    print("1. 测试中文数据读取...")
    try:
        groups = converter.read_csv_data("test_chinese_data.csv")
        chinese_groups = [name for name in groups.keys() if any(char in name for char in ['基线', '干预'])]
        
        if chinese_groups:
            print(f"   ✓ 成功读取中文组名: {', '.join(chinese_groups)}")
        else:
            print("   ○ 未检测到中文组名")
    except Exception as e:
        print(f"   ✗ 中文支持测试失败: {e}")
        return False
    
    return True

def test_file_operations():
    """测试文件操作功能"""
    print("\n=== 测试文件操作功能 ===")
    
    converter = BarChartConverter()
    
    # 测试Excel保存
    print("1. 测试Excel保存...")
    try:
        result = converter.convert_bar_data("data.csv")
        excel_path = converter.save_to_excel(result, output_dir="test_results")
        
        if os.path.exists(excel_path):
            print(f"   ✓ Excel文件保存成功: {excel_path}")
        else:
            print("   ✗ Excel文件未生成")
    except Exception as e:
        print(f"   ✗ Excel保存测试失败: {e}")
        return False
    
    # 测试CSV保存
    print("2. 测试CSV保存...")
    try:
        csv_path = converter.save_to_csv(result, output_dir="test_results")
        
        if os.path.exists(csv_path):
            print(f"   ✓ CSV文件保存成功: {csv_path}")
        else:
            print("   ✗ CSV文件未生成")
    except Exception as e:
        print(f"   ✗ CSV保存测试失败: {e}")
        return False
    
    return True

def main():
    """主测试函数"""
    print("带误差线柱状图转换器测试套件")
    print("=" * 50)
    
    tests = [
        test_basic_functionality,
        test_asymmetric_error_bars,
        test_group_comparisons,
        test_meta_analysis_formats,
        test_chinese_support,
        test_file_operations
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"测试 {test_func.__name__} 发生异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
