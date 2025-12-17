# 场景二设计文档：基于本地代码仓的需求驱动设计方案生成

## 1. 场景说明

场景二的目标是：**针对给定的业务需求，自动生成一个基于本地代码仓架构的系统设计方案**，并同时给出清晰、可追溯的**推理 trace（reasoning trace）**，用于支持大语言模型在“设计能力 + 推理能力”上的微调。

与场景一侧重于“事实性与功能性问答”不同，场景二聚焦于：

* 架构理解
* 方案设计
* 扩展性与工程权衡
* 设计决策背后的推理过程

本设计文档仅覆盖**当前已实现的数据生成能力**。

---

## 2. 系统输入与整体流程

场景二复用场景一生成的业务规则数据，并在此基础上引入“需求描述”，形成设计任务。

整体流程如下：

```
Local Repo
   ↓
code_parser.py
   ↓
parsed_code.json
   ↓
parsed_rule_extractor.py
   ↓
business_rule.json
   ↓
design_plan.py + Requirement
   ↓
Design Solutions + Reasoning Traces
```

---

## 3. 输入数据定义

### 3.1 业务规则输入

* 输入文件：`./data/business_rule.json`
* 来源：由代码解析与规则抽取自动生成
* 作用：

  * 约束设计方案必须基于真实代码结构
  * 为设计推理提供代码级上下文依据

---

### 3.2 需求描述（Requirement）结构

每条设计任务包含一个结构化需求描述，主要字段包括：

* `requirement_id`：需求唯一标识
* `requirement_category`：需求类型（如功能扩展、性能优化、架构改进等）
* `requirement_description`：自然语言需求描述
* `requirement_complexity`：需求复杂度
* `language`：需求语言（zh / en）
* `relevant_code_references`：与需求最相关的代码组件引用
* `relevant_files`：涉及的主要文件列表

这些信息共同构成设计方案生成的**上下文输入**。

---

## 4. 场景二训练数据结构定义

### 4.1 设计方案对象形式

每条设计数据由三部分组成：

1. **Input（设计输入）**
2. **Output（设计方案）**
3. **Metadata（生成信息）**

---

### 4.2 设计输出内容

#### 4.2.1 设计方案（design_solution）

设计方案以结构化自然语言形式给出，通常包含：

* 需求分析
* 技术方案选择
* 主要实现思路
* 需要修改或新增的模块
* 架构完整性与可扩展性说明

设计内容严格基于现有代码架构与技术栈，避免脱离实际代码仓。

---

#### 4.2.2 推理 Trace（reasoning_trace）

推理 trace 明确记录设计决策的来源与逻辑，包括：

* 基于哪些现有代码模式做出设计选择
* 如何复用或扩展当前系统架构
* 设计过程中考虑的约束条件与最佳实践

该字段用于：

* 支持可解释的模型训练
* 为推理能力微调提供显式监督信号

---

### 4.3 语言支持

* 中文设计方案生成（无或有 LLM）
* 英文设计方案生成（需 LLM 支持）
* 中英文混合数据集生成 （需 LLM 支持）

语言类型由脚本参数控制。

---

## 5. 数据合规性与质量保障机制

### 5.1 架构一致性约束

* 所有设计方案必须引用真实存在的代码组件
* 不引入与代码仓无关的外部架构假设

### 5.2 推理 Trace 合规性

* 推理过程以自然语言显式表达
* 每一步推理均可追溯到代码结构或工程实践
* 避免黑盒式结论输出

### 5.3 示例清晰度

* 设计方案与推理 trace 分离表达
* 输入 / 输出结构固定，便于模型学习

---

## 6. 使用方法

```bash
# 生成中文设计方案 10 条
python ./code/design_plan.py \
  --num 10 \
  --rules data/business_rule.json \
  --output data/design_solution/enhanced_designs_zh.json \
  --lang zh

# 生成英文设计方案 10 条（需 LLM）
python ./code/design_plan.py \
  --num 10 \
  --rules data/business_rule.json \
  --output data/design_solution/enhanced_designs_en.json \
  --lang en

# 生成中英文混合设计方案 10 条
python ./code/design_plan.py \
  --num 10 \
  --rules data/business_rule.json \
  --output data/design_solution/enhanced_designs.json
```
输出文件位置：
```text
data/design_solution/based_designs.json (For No LLM)
data/design_solution/enhanced_designs.json (For LLM No Language Requirement)
data/design_solution/enhanced_designs_en.json (For LLM with English)
data/design_solution/enhanced_designs_zh.json (For LLM with Chinese)
```
---

## 7. Future Work：基于设计数据的模型微调方向

基于场景二生成的数据集，可以支持以下模型微调方向：

* **架构级设计能力微调**：让模型学会在给定代码仓约束下进行系统设计
* **推理可解释性微调**：通过 reasoning trace 强化模型的显式推理能力
* **需求到方案映射能力**：提升模型从自然语言需求到工程方案的转换能力
* **多语言工程设计能力**：支持中英文技术设计任务

该数据集可与场景一问答数据联合使用，构建从“代码理解 → 设计推理”的完整能力训练闭环。
