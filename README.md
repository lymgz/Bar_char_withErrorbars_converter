# Bar_char_withErrorbars_converter
A toole convert the figure of Bar char with error bars, namely  Bar char converter
---
## 带误差线柱状图数据转换工具

## 简介

这是一个强大的数据转换工具，专门用于将带误差线的柱状图数据转换为Meta分析标准格式。支持多种误差线类型，包括非对称误差线，并提供完整的统计分析和组间比较功能。

## 功能特性

### 📊 核心功能
- **多种误差线类型支持**: SE, SD, CI95, CI99, 2SE, ASYMMETRIC
- **非对称误差线处理**: 支持 "upper/lower" 格式
- **自动误差线类型检测**: 智能识别和验证误差线类型
- **统计转换**: 将各种误差线类型统一转换为Mean±SD格式
- **组间比较分析**: 自动执行t检验和效应量计算
- **多语言支持**: 中英文标签自动识别

### 📈 输出格式
- **Excel格式**: 完整分析结果，包含多个工作表
- **CSV格式**: 简化摘要，便于导入其他软件
- **Meta分析标准格式**:
  - 通用格式 (Universal)
  - RevMan格式
  - R Meta包格式

### 🛠️ 技术特性
- **智能数据验证**: 自动检测数据完整性和质量
- **置信度评估**: 为每种转换提供置信度评分
- **文件冲突处理**: 自动处理文件占用和重命名
- **详细日志输出**: 完整的分析过程和结果说明

## 安装要求

```bash
pip install pandas openpyxl
```

## 使用方法

### 1. 生成模板
```bash
python bar_converter.py --generate-template --indicators 6
```

### 2. 填写数据
编辑生成的 `template.csv` 文件，填写实验数据后保存为 `data.csv`

### 3. 转换数据
```bash
# 基本转换
python bar_converter.py --convert data.csv

# 详细输出
python bar_converter.py --convert data.csv --verbose

# 包含组间比较
python bar_converter.py --convert data.csv --compare-groups

# 生成Meta分析格式
python bar_converter.py --convert data.csv --meta-analysis-format

# 完整分析
python bar_converter.py --convert data.csv --compare-groups --meta-analysis-format --verbose
```

## CSV数据格式

### 支持的标签
- **组标签**: Baseline/Intervention 或 基线组/干预组
- **数据标签**: Mean/Error_Bar/Error_Type/Sample_Size 或 均值/误差线/误差类型/样本量

### 误差线类型说明
| 类型 | 说明 | 转换方法 |
|------|------|----------|
| SE | 标准误差 | SE × √N = SD |
| SD | 标准差 | 直接使用 |
| CI95 | 95%置信区间 | CI95 ÷ (1.96 × √N) = SD |
| CI99 | 99%置信区间 | CI99 ÷ (2.576 × √N) = SD |
| 2SE | 2倍标准误差 | 2SE ÷ 2 × √N = SD |
| ASYMMETRIC | 非对称误差线 | 使用平均值，保存原始值 |

### 非对称误差线格式
```
Error_Bar: 1.5/0.8  # 上误差线/下误差线
Error_Type: ASYMMETRIC
```

## 输出文件说明

### Excel文件 (详细结果)
包含4个工作表：
1. **转换结果**: 基本转换结果
2. **组间比较结果**: t检验和效应量分析
3. **数据质量分析**: 数据完整性和质量评估
4. **摘要信息**: 统计摘要和改进建议

### CSV文件 (摘要结果)
简化格式，便于快速导入其他统计软件。

### Meta分析格式文件
- `meta_universal.csv`: 通用Meta分析格式
- `meta_revman.csv`: RevMan兼容格式
- `meta_r.csv`: R Meta包格式

## 命令行参数

```bash
usage: bar_converter.py [-h] [--generate-template] [--indicators INDICATORS]
                        [--convert CONVERT] [--verbose] [--json]
                        [--output-dir OUTPUT_DIR]
                        [--output-name OUTPUT_NAME] [--no-csv]
                        [--compare-groups]
                        [--comparison-type {all,intervention-baseline}]
                        [--confidence-level CONFIDENCE_LEVEL]
                        [--meta-analysis-format]

带误差线柱状图数据转换工具

optional arguments:
  -h, --help            show this help message and exit
  --generate-template   生成CSV模板
  --indicators INDICATORS
                        模板中的指标数量 (默认: 4)
  --convert CONVERT     转换CSV文件
  --verbose             详细输出
  --json                JSON格式输出
  --output-dir OUTPUT_DIR
                        输出目录 (默认: results)
  --output-name OUTPUT_NAME
                        输出文件基础名称 (默认: bar_results)
  --no-csv              不生成CSV摘要文件
  --compare-groups      启用组间比较功能
  --comparison-type {all,intervention-baseline}
                        比较类型 (默认: intervention-baseline)
  --confidence-level CONFIDENCE_LEVEL
                        置信水平 (默认: 0.95)
  --meta-analysis-format
                        生成Meta分析标准格式文件
```

## 使用示例

### 基本使用
```bash
# 生成6指标模板
python bar_converter.py --generate-template --indicators 6

# 转换数据并生成详细报告
python bar_converter.py --convert data.csv --verbose
```

### 高级分析
```bash
# 完整分析流程
python bar_converter.py --convert data.csv \
    --compare-groups \
    --meta-analysis-format \
    --verbose \
    --output-name "my_analysis"
```

## 开发和测试

### 运行测试
```bash
python test_converter.py
```

### 测试内容
1. 基本功能测试
2. 非对称误差线处理
3. 组间比较分析
4. Meta分析格式生成
5. 中文支持
6. 文件操作功能

## 常见问题

### Q: 如何处理非对称误差线？
A: 在CSV中使用 "upper/lower" 格式，如 "2.1/1.8"，并在Error_Type中指定 "ASYMMETRIC"

### Q: 转换结果中的置信度是什么？
A: 置信度表示误差线类型识别的准确性，范围0-1，越高越可靠

### Q: 如何处理混合误差线类型？
A: 工具支持同一数据集中使用不同误差线类型，会自动识别和转换

### Q: 输出文件被占用怎么办？
A: 工具会自动检测文件占用并生成带序号的新文件名

## 贡献

欢迎提交问题和改进建议！

## 许可证

MIT License
