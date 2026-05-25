# 手术室资源冲突预测系统

基于历史手术数据预测手术时长波动，提前发现器械/麻醉/主刀冲突，输出给科室协调的排程建议。

## 功能特性

- **时长预测**：基于历史数据预测手术时长，支持置信区间
- **冲突检测**：器械冲突、麻醉设备冲突、主刀时间冲突
- **排程优化**：基于冲突检测结果生成排程优化建议
- **多格式报告**：支持文本、CSV、HTML格式输出
- **可视化**：ASCII日程表，冲突高亮显示

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

### 预测手术时长

```bash
python -m src predict --surgery-type "腹腔镜胆囊切除术" --department "普外科" --surgeon "张主任"
```

### 检测冲突

```bash
python -m src detect-conflicts --date 2024-01-15
```

### 生成报告

```bash
python -m src generate-report --format html --output report.html
```

## 项目结构

```
or-resource-conflict-predictor/
├── src/              # 源代码
├── data/             # 数据目录
├── templates/        # 报告模板
├── models/           # 保存的模型
├── README.md
├── requirements.txt
└── .gitignore
```

## 许可证

MIT License

---

## 支持作者

如果您觉得这个项目对您有帮助，欢迎打赏支持！
Wechat:gdgdmp
![Buy Me a Coffee](buymeacoffee.png)

**Buy me a coffee (crypto)**

| 币种 | 地址 |
|------|------|
| BTC | `bc1qc0f5tv577z7yt59tw8sqaq3tey98xehy32frzd` |
| ETH / USDT | `0x3b7b6c47491e4778157f0756102f134d05070704` |
| SOL | `6Xuk373zc6x6XWcAAuqvbWW92zabJdCmN3CSwpsVM6sd` |