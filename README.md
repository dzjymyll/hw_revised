# 本地代码仓训练数据生成与处理框架

## 项目简介

本项目是一个**面向本地代码仓的数据生成与处理框架**，目标是通过自动化分析真实代码仓，
构建**高质量、可追溯的训练数据集**，用于**大语言模型（LLM）的微调（Fine-tuning）**。

系统通过对代码结构与业务规则的解析，生成两类核心数据集，对应两个不同的应用场景（Scenario）：
- **场景一：代码理解型问答数据集（Q&A）**
- **场景二：需求驱动的架构设计与推理数据集**

---

## 示例代码仓说明（test_repo）

本项目以以下开源仓库作为示例代码仓进行数据生成与验证：

**Azure FastAPI + PostgreSQL 示例项目**  
https://github.com/Azure-Samples/msdocs-fastapi-postgresql-sample-app/tree/main

使用方式：
1. 将上述仓库克隆或下载到本地
2. 将其重命名或存放为 `test_repo`
3. 使用本项目对 `test_repo` 进行分析和数据生成
```bash
# 克隆示例代码仓（Azure FastAPI + PostgreSQL 示例项目）
git clone https://github.com/Azure-Samples/msdocs-fastapi-postgresql-sample-app.git test_repo
```
---

## 环境准备

### 安装依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
```

---

## 整体流程概览

```
test_repo（本地代码仓）
   │
   ├─ Step 1: 代码解析与规则抽取
   ├─ Step 2: 场景一问答数据生成
   └─ Step 3: 场景二设计方案数据生成
```

---

## 大语言模型配置（可选）

当前支持模型：
- **智谱 AI GLM-4**

配置方式：

在 `./code/.env` 文件中添加：

```env
ZHIPU_API_KEY=your_api_key_here
```

---

## 设计文档说明

针对两个场景，本项目在 `./doc/` 目录下提供了详细设计文档，包括：
- 输入 / 输出数据结构说明
- 数据存储方案
- 设计思路与实现构想

---

## Step 1：代码提取与规则分析

### 1.1 代码解析
在根目录执行代码解析：

```text
python .\scripts\code_parser.py --repo 'test_repo' --output 'data/parsed_code.json'

```

功能：
- 分析本地代码仓中的 Python 与 HTML 文件
- 提取代码结构、函数、类、端点与模板信息

输出：
```text
data/parsed_code.json
```

---

### 1.2 业务规则抽取

根据代码生成业务规则,在根目录执行：
```text
python .\scripts\parsed_rule_extractor.py --input 'data/parsed_code.json' --output 'data/business_rule.json'
```

功能：
- 基于 `parsed_code.json` 抽象业务规则
- 规则作为后续数据生成的统一语义入口

输出：
```text
data/business_rule.json
```

---

## Step 2：场景一 —— 问答对数据集生成
根据业务规则生成多种不同难度等级问答对，在没有大语言模型支持情况下生成中文问答对，存储在data/qa_pairs/base_qa_pairs.json，在有大模型API KEY情况下可以选择生成中英文问答对，存储在data/qa_pairs/enhanced_qa_pairs*
脚本：
```text
./code/qa_generator.py
```

示例命令(在根目录执行代码解析：)：

```bash
#（生成中文问答40个）
python code/qa_generator.py   --num 40   --rules data/business_rule.json   --output data/qa_pairs/enhanced_qa_pairs_zh.json   --lang zh
#（生成英文问答40个）
python code/qa_generator.py   --num 40   --rules data/business_rule.json   --output data/qa_pairs/enhanced_qa_pairs_zh.json   --lang en
#（生成中英文问答40个）
python code/qa_generator.py   --num 40   --rules data/business_rule.json   --output data/qa_pairs/enhanced_qa_pairs_zh.json


```

说明：
-`--num` 控制生成数据数量
- `--lang` 支持 `zh` / `en`，不指定语言时可生成中英文混合数据集（需大模型支持），没有大模型时只生成中文结果，储存在 data/qa_pairs/base_qa_pairs.json

---

## Step 3：场景二 —— 需求与架构设计数据集生成

该阶段生成 **需求 → 设计方案 → 推理过程** 的结构化数据，
用于训练模型的架构设计与推理能力。

在有大语言模型辅助的情况下：
- 支持中文或英文生成
- 输出更完整的设计方案与推理 trace

示例命令(在根目录执行代码解析：)：

```bash
#（生成中文设计方案10个）
python code/design_plan.py --num 10 --rules 'data/business_rule.json' --output 'data/design_solution/enhanced_designs_zh.json' --lang 'zh'

#（生成英文设计方案10个）
python code/design_plan.py --num 10 --rules 'data/business_rule.json' --output 'data/design_solution/enhanced_designs_en.json' --lang en
#（生成中英文设计方案10个）
python code/design_plan.py --num 10 --rules 'data/business_rule.json' --output 'data/design_solution/enhanced_designs.json'


```

说明：
-`--num` 控制生成数据数量
- `--lang` 支持 `zh` / `en`，不指定语言时可生成中英文混合数据集（需大模型支持），没有大模型时只生成中文结果，储存在 data/qa_pairs/base_qa_pairs.json

---

## 项目定位

本项目是一个**规则驱动、结构可追溯**的训练数据生成框架，
专注于基于真实代码仓构建可用于 LLM 微调的数据集。
