"""
场景二：简化架构设计方案生成器（支持多语言，输入输出语言一致）
基于本地代码仓生成架构设计方案和推理 trace
"""

import json
import asyncio
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import random
from dotenv import load_dotenv
from openai import OpenAI


class SimpleDesignGenerator:
    """简化架构设计方案生成器（支持多语言，输入输出语言一致）"""

    def __init__(self,
                 business_rule_file: str = "../data/business_rule.json",
                 output_file: str = "../data/design_solution/simple_designs.json",
                 num_designs: int = 10,
                 language: str = None):
        """
        初始化设计方案生成器

        Args:
            business_rule_file: 业务规则文件路径
            output_file: 输出文件路径（默认为design_solution目录下）
            num_designs: 生成的设计方案数量
            language: 指定生成的语言，'zh'=中文, 'en'=英文, None=中英文皆有（仅当有LLM时）
        """
        self.business_rule_file = Path(business_rule_file)
        self.output_file = Path(output_file)
        self.num_designs = num_designs
        self.language = language
        self.logger = logging.getLogger(__name__)

        # 确保输出目录存在（design_solution目录）
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        # 初始化LLM客户端
        self.api_key = os.getenv("ZHIPU_API_KEY")
        self.base_url = os.getenv("ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4/")

        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            self.has_llm = True
            self.logger.info("智谱AI API已配置，将生成增强的设计方案")
        else:
            self.client = None
            self.has_llm = False
            self.logger.warning("未配置智谱AI API，将生成基础设计方案")
            # 无LLM时，无论指定什么语言，都只生成中文
            self.language = "zh"

        # 加载数据
        self.business_rules = None
        self.load_data()

        # 预定义的需求模板（包含中英文描述）
        self.requirement_templates = self._create_requirement_templates()

    def load_data(self) -> None:
        """加载解析代码和业务规则数据"""
        try:

            # 加载业务规则
            if self.business_rule_file.exists():
                with open(self.business_rule_file, 'r', encoding='utf-8') as f:
                    self.business_rules = json.load(f)
                self.logger.info(f"已加载业务规则数据，包含 {len(self.business_rules.get('rules', []))} 条规则")
            else:
                self.logger.error(f"业务规则文件不存在: {self.business_rule_file}")

        except Exception as e:
            self.logger.error(f"加载数据时出错: {e}")
            raise

    def _create_requirement_templates(self) -> List[Dict[str, Any]]:
        """创建需求模板（包含中英文描述）"""
        templates = [
            {
                "id": "REQ001",
                "category": "功能扩展",
                "category_en": "Feature Extension",
                "description": "需要为餐厅管理系统添加一个新的功能：用户可以对餐厅进行收藏和取消收藏操作。",
                "description_en": "Add a new feature to the restaurant management system: users can favorite and unfavorite restaurants.",
                "complexity": "中等",
                "complexity_en": "Medium",
                "target_modules": ["model", "endpoint", "function"]
            },
            {
                "id": "REQ002",
                "category": "性能优化",
                "category_en": "Performance Optimization",
                "description": "需要优化餐厅列表页面的加载性能，特别是当餐厅数量较多时，提高查询效率。",
                "description_en": "Optimize the loading performance of the restaurant list page, especially when there are many restaurants, to improve query efficiency.",
                "complexity": "中等",
                "complexity_en": "Medium",
                "target_modules": ["endpoint", "function", "model"]
            },
            {
                "id": "REQ003",
                "category": "功能扩展",
                "category_en": "Feature Extension",
                "description": "需要为餐厅添加一个图片上传功能，每个餐厅最多可以上传5张图片。",
                "description_en": "Add an image upload function for restaurants, with each restaurant allowed to upload up to 5 images.",
                "complexity": "中等",
                "complexity_en": "Medium",
                "target_modules": ["model", "endpoint", "function"]
            },
            {
                "id": "REQ004",
                "category": "架构改进",
                "category_en": "Architecture Improvement",
                "description": "需要将数据库访问逻辑从端点函数中抽离出来，创建专门的数据访问层。",
                "description_en": "Extract database access logic from endpoint functions and create a dedicated data access layer.",
                "complexity": "高",
                "complexity_en": "High",
                "target_modules": ["function", "class", "model"]
            },
            {
                "id": "REQ005",
                "category": "功能扩展",
                "category_en": "Feature Extension",
                "description": "需要添加一个餐厅搜索功能，支持按名称、地址、评分范围进行搜索。",
                "description_en": "Add a restaurant search function that supports searching by name, address, and rating range.",
                "complexity": "中等",
                "complexity_en": "Medium",
                "target_modules": ["endpoint", "function", "model"]
            },
            {
                "id": "REQ006",
                "category": "安全性",
                "category_en": "Security",
                "description": "需要为所有API端点添加身份验证和权限控制，确保只有授权用户才能访问特定功能。",
                "description_en": "Add authentication and permission control to all API endpoints to ensure only authorized users can access specific functions.",
                "complexity": "高",
                "complexity_en": "High",
                "target_modules": ["endpoint", "function", "config"]
            },
            {
                "id": "REQ007",
                "category": "功能扩展",
                "category_en": "Feature Extension",
                "description": "需要添加一个管理员后台界面，用于管理餐厅和用户评论。",
                "description_en": "Add an admin backend interface for managing restaurants and user reviews.",
                "complexity": "高",
                "complexity_en": "High",
                "target_modules": ["endpoint", "template", "function"]
            },
            {
                "id": "REQ008",
                "category": "性能优化",
                "category_en": "Performance Optimization",
                "description": "需要为频繁访问的数据添加缓存机制，减少数据库查询次数。",
                "description_en": "Add a caching mechanism for frequently accessed data to reduce the number of database queries.",
                "complexity": "中等",
                "complexity_en": "Medium",
                "target_modules": ["function", "model", "config"]
            },
            {
                "id": "REQ009",
                "category": "功能扩展",
                "category_en": "Feature Extension",
                "description": "需要添加一个餐厅预订功能，用户可以选择日期和时间预订座位。",
                "description_en": "Add a restaurant reservation function that allows users to select date and time to book seats.",
                "complexity": "高",
                "complexity_en": "High",
                "target_modules": ["model", "endpoint", "function", "template"]
            },
            {
                "id": "REQ010",
                "category": "架构改进",
                "category_en": "Architecture Improvement",
                "description": "需要将应用拆分为微服务架构，将餐厅管理、用户管理、评论管理拆分为独立服务。",
                "description_en": "Split the application into a microservices architecture, separating restaurant management, user management, and review management into independent services.",
                "complexity": "高",
                "complexity_en": "High",
                "target_modules": ["endpoint", "function", "model", "config"]
            }
        ]
        return templates

    def select_requirements(self) -> List[Dict[str, Any]]:
        """选择需求用于生成设计方案"""
        if len(self.requirement_templates) <= self.num_designs:
            return self.requirement_templates
        else:
            return random.sample(self.requirement_templates, self.num_designs)

    def select_relevant_rules(self, requirement: Dict[str, Any]) -> List[Dict[str, Any]]:
        """选择与需求相关的业务规则"""
        if not self.business_rules:
            return []

        target_modules = requirement.get("target_modules", [])
        all_rules = self.business_rules.get("rules", [])

        # 筛选相关规则
        relevant_rules = []
        for rule in all_rules:
            rule_type = rule.get("type", "")
            if rule_type in target_modules:
                relevant_rules.append(rule)

        # 如果没有找到相关规则，返回一些重要的规则
        if not relevant_rules:
            important_types = ["endpoint", "function", "model"]
            relevant_rules = [r for r in all_rules if r.get("type") in important_types]

        # 限制规则数量
        max_rules = min(3, len(relevant_rules))
        return random.sample(relevant_rules, max_rules) if len(relevant_rules) > max_rules else relevant_rules

    def select_relevant_code_files(self) -> List[str]:
        """选择相关的代码文件"""

        # 提取项目结构信息
        project_structure = None
        for rule in self.business_rules.get("rules", []):
            if rule.get("type") == "file_structure":
                project_structure = rule
                break

        if project_structure:
            python_files = project_structure.get("metadata", {}).get("python_files", [])
            # 选择几个重要的文件
            important_files = [
                "src/fastapi_app/app.py",
                "src/fastapi_app/models.py",
                "src/fastapi_app/seed_data.py"
            ]

            # 确保文件路径格式一致
            relevant_files = []
            for file in important_files:
                # 转换路径格式
                converted_file = file.replace("/", "\\")
                if converted_file in python_files:
                    relevant_files.append(converted_file)

            return relevant_files if relevant_files else python_files[:2]

        return []

    def prepare_llm_prompt(self, requirement: Dict[str, Any],
                          relevant_rules: List[Dict[str, Any]],
                          relevant_files: List[str],
                          language: str = "zh") -> str:
        """准备LLM提示词"""
        # 根据语言选择需求描述
        if language == "zh":
            requirement_desc = requirement.get("description", "")
            requirement_cat = requirement.get("category", "")
            requirement_comp = requirement.get("complexity", "")
        else:
            requirement_desc = requirement.get("description_en", requirement.get("description", ""))
            requirement_cat = requirement.get("category_en", requirement.get("category", ""))
            requirement_comp = requirement.get("complexity_en", requirement.get("complexity", ""))

        # 格式化相关规则信息
        rules_info = []
        for i, rule in enumerate(relevant_rules[:3], 1):
            rule_type = rule.get("type", "")
            rule_name = rule.get("name", rule.get("match", ""))
            file_path = rule.get("file", "")
            rules_info.append(f"{i}. {rule_type}: {rule_name} (文件: {file_path})")

        rules_text = "\n".join(rules_info) if rules_info else "无相关规则"

        # 格式化相关文件信息
        files_text = "\n".join(relevant_files[:3]) if relevant_files else "无相关文件"

        if language == "zh":
            prompt = f"""请基于以下需求和相关代码信息，生成一个简洁的架构设计方案：

## 需求描述
{requirement_desc}

需求分类：{requirement_cat}
需求复杂度：{requirement_comp}

## 现有代码上下文
相关代码组件：
{rules_text}

相关代码文件：
{files_text}

## 请生成以下两个部分（请使用中文）：

### 1. 设计方案
[请在这里写完整的设计方案，包括：
- 需求分析
- 技术方案
- 主要实现思路
- 需要修改/新增的模块]

### 2. 推理 trace
[请在这里详细说明设计决策的原因和依据，包括：
- 基于哪些现有代码模式做出的设计决策
- 如何利用现有架构进行扩展
- 考虑了哪些约束条件和最佳实践]

重要提示：
1. 请确保设计方案简洁明了
2. 推理 trace 必须详细说明设计思路和依据
3. 设计方案要与现有代码架构保持一致
4. 请使用中文回答"""
        else:  # English
            prompt = f"""Please generate a concise architectural design solution based on the following requirements and related code information:

## Requirement Description
{requirement_desc}

Requirement Category: {requirement_cat}
Requirement Complexity: {requirement_comp}

## Existing Code Context
Relevant code components:
{rules_text}

Relevant code files:
{files_text}

## Please generate the following two parts (in English):

### 1. Design Solution
[Please write a complete design solution here, including:
- Requirement analysis
- Technical solution
- Main implementation ideas
- Modules to be modified/added]

### 2. Reasoning Trace
[Please explain in detail the reasons and basis for design decisions, including:
- Which existing code patterns the design decisions are based on
- How to extend using the existing architecture
- What constraints and best practices were considered]

Important notes:
1. Ensure the design solution is concise and clear
2. The reasoning trace must explain the design thinking and basis in detail
3. The design solution should be consistent with the existing code architecture
4. Please answer in English"""

        return prompt

    def generate_simple_design(self, requirement: Dict[str, Any],
                              relevant_rules: List[Dict[str, Any]],
                              language: str = "zh") -> Dict[str, str]:
        """生成简单的设计方案（无LLM时使用）"""
        # 根据语言选择需求描述
        if language == "zh":
            category = requirement.get("category", "")
            description = requirement.get("description", "")
        else:
            category = requirement.get("category_en", requirement.get("category", ""))
            description = requirement.get("description_en", requirement.get("description", ""))

        if language == "zh":
            # 生成设计方案（中文）
            design_solution = f"""
基于需求"{description}"，提出以下设计方案：

1. 需求分析：
   - 这是一个{category}需求，需要对现有系统进行扩展
   - 需要确保与现有功能兼容

2. 技术方案：
   - 利用现有FastAPI框架进行扩展
   - 基于现有数据模型进行设计
   - 保持前后端分离的架构模式

3. 主要实现思路：
   - 扩展现有API端点或创建新端点
   - 更新或新增数据模型
   - 修改或新增业务逻辑函数

4. 需要修改/新增的模块：
   - 相关代码文件：{[r.get('file', '') for r in relevant_rules[:2]]}
   - 相关组件：{[r.get('type', '') for r in relevant_rules[:2]]}
            """.strip()

            # 生成推理 trace（中文）
            reasoning_trace = f"""
推理 trace：

1. 基于现有代码分析：
   - 参考了相关规则：{[r.get('type') + ': ' + r.get('name', r.get('match', '')) for r in relevant_rules[:2]]}
   - 分析了现有系统架构和代码模式

2. 设计决策依据：
   - 充分利用现有FastAPI框架特性
   - 保持与现有数据库模型的兼容性
   - 遵循现有项目的编码规范和架构模式

3. 技术考虑：
   - 确保新功能不会破坏现有业务逻辑
   - 考虑系统的可维护性和扩展性
   - 采用前后端分离的设计原则

4. 风险评估：
   - 确保数据迁移和兼容性
   - 制定详细的测试计划
   - 分阶段实施以降低风险
            """.strip()
        else:
            # 生成设计方案（英文）
            design_solution = f"""
Based on the requirement "{description}", propose the following design solution:

1. Requirement Analysis:
   - This is a {category} requirement that requires extension of the existing system
   - Need to ensure compatibility with existing functions

2. Technical Solution:
   - Extend using the existing FastAPI framework
   - Design based on existing data models
   - Maintain the front-end and back-end separation architecture pattern

3. Main Implementation Ideas:
   - Extend existing API endpoints or create new endpoints
   - Update or add data models
   - Modify or add business logic functions

4. Modules to be Modified/Added:
   - Relevant code files: {[r.get('file', '') for r in relevant_rules[:2]]}
   - Relevant components: {[r.get('type', '') for r in relevant_rules[:2]]}
            """.strip()

            # 生成推理 trace（英文）
            reasoning_trace = f"""
Reasoning Trace:

1. Based on existing code analysis:
   - Referred to relevant rules: {[r.get('type') + ': ' + r.get('name', r.get('match', '')) for r in relevant_rules[:2]]}
   - Analyzed the existing system architecture and code patterns

2. Design Decision Basis:
   - Make full use of existing FastAPI framework features
   - Maintain compatibility with existing database models
   - Follow existing project coding standards and architecture patterns

3. Technical Considerations:
   - Ensure new functions do not break existing business logic
   - Consider system maintainability and scalability
   - Adopt front-end and back-end separation design principles

4. Risk Assessment:
   - Ensure data migration and compatibility
   - Develop detailed test plans
   - Implement in phases to reduce risks
            """.strip()

        return {
            "design_solution": design_solution,
            "reasoning_trace": reasoning_trace
        }

    async def call_zhipu_api(self, prompt: str) -> Optional[str]:
        """调用智谱AI API"""
        if not self.has_llm or not self.client:
            return None

        try:
            model = "glm-4"

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的软件架构师，擅长基于现有代码库设计简洁有效的扩展方案。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            content = response.choices[0].message.content
            return content

        except Exception as e:
            self.logger.error(f"调用智谱AI API时出错: {e}")
            return None

    def parse_design_response(self, response: str, language: str = "zh") -> Dict[str, str]:
        """解析LLM返回的设计方案"""
        result = {
            "design_solution": "",
            "reasoning_trace": ""
        }

        # 根据语言设置关键词
        if language == "zh":
            design_keywords = ["设计方案", "设计解决方案", "设计"]
            reasoning_keywords = ["推理 trace", "推理过程", "设计决策", "基于现有"]
        else:
            design_keywords = ["Design Solution", "Design", "Solution"]
            reasoning_keywords = ["Reasoning Trace", "Reasoning Process", "Design Decision", "Based on"]

        # 尝试按部分分割
        lines = response.split('\n')
        in_design = False
        in_reasoning = False
        design_lines = []
        reasoning_lines = []

        for line in lines:
            line_stripped = line.strip()

            # 检测设计方案部分
            for keyword in design_keywords:
                if keyword in line_stripped and not any(rk in line_stripped for rk in reasoning_keywords):
                    in_design = True
                    in_reasoning = False
                    break

            # 检测推理 trace 部分
            for keyword in reasoning_keywords:
                if keyword in line_stripped:
                    in_design = False
                    in_reasoning = True
                    break

            # 收集各行内容
            if in_design and line_stripped and not any(rk in line_stripped for rk in reasoning_keywords):
                design_lines.append(line_stripped)
            elif in_reasoning and line_stripped:
                reasoning_lines.append(line_stripped)

        # 如果没有检测到明确的部分，尝试智能分割
        if not design_lines or not reasoning_lines:
            # 查找可能的分割点
            split_keywords = reasoning_keywords
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                for keyword in split_keywords:
                    if keyword in line_stripped:
                        # 前部分为设计方案，后部分为推理 trace
                        design_lines = [l.strip() for l in lines[:i] if l.strip()]
                        reasoning_lines = [l.strip() for l in lines[i:] if l.strip()]
                        break
                if design_lines and reasoning_lines:
                    break

        # 如果还是没有，使用默认内容
        if not design_lines:
            if language == "zh":
                design_lines = ["基于需求分析，提出扩展方案。"]
            else:
                design_lines = ["Based on requirement analysis, propose an extension solution."]

        if not reasoning_lines:
            if language == "zh":
                reasoning_lines = ["基于现有代码架构、业务规则和最佳实践进行设计决策。"]
            else:
                reasoning_lines = ["Design decisions are made based on existing code architecture, business rules and best practices."]

        result["design_solution"] = '\n'.join(design_lines).strip()
        result["reasoning_trace"] = '\n'.join(reasoning_lines).strip()

        return result

    async def generate_design_for_requirement(self, requirement: Dict[str, Any], language: str = "zh") -> Optional[Dict[str, Any]]:
        """为单个需求生成设计方案"""
        try:
            # 选择相关规则和文件
            relevant_rules = self.select_relevant_rules(requirement)
            relevant_files = self.select_relevant_code_files()

            if self.has_llm:
                # 使用LLM生成
                prompt = self.prepare_llm_prompt(requirement, relevant_rules, relevant_files, language)
                response = await self.call_zhipu_api(prompt)

                if response:
                    design_sections = self.parse_design_response(response, language)
                    # 记录解析结果
                    self.logger.debug(f"生成{language}设计方案，长度: {len(design_sections.get('design_solution', ''))}")
                    self.logger.debug(f"生成{language}推理 trace，长度: {len(design_sections.get('reasoning_trace', ''))}")
                else:
                    # 如果API调用失败，使用简单生成
                    design_sections = self.generate_simple_design(requirement, relevant_rules, language)
            else:
                # 无LLM时使用简单生成
                design_sections = self.generate_simple_design(requirement, relevant_rules, language)

            # 根据语言选择输入描述
            if language == "zh":
                input_desc = requirement.get("description", "")
                input_cat = requirement.get("category", "")
                input_comp = requirement.get("complexity", "")
            else:
                input_desc = requirement.get("description_en", requirement.get("description", ""))
                input_cat = requirement.get("category_en", requirement.get("category", ""))
                input_comp = requirement.get("complexity_en", requirement.get("complexity", ""))

            # 构建设计方案
            design_case = {
                "input": {
                    "requirement_id": requirement.get("id", ""),
                    "requirement_category": input_cat,
                    "requirement_description": input_desc,
                    "requirement_complexity": input_comp,
                    "language": language,
                    "relevant_code_references": [
                        {
                            "file_path": rule.get("file", ""),
                            "rule_type": rule.get("type", ""),
                            "rule_name": rule.get("name", rule.get("match", "")),
                            "description": f"相关{rule.get('type', '')}组件" if language == "zh" else f"Relevant {rule.get('type', '')} component"
                        }
                        for rule in relevant_rules[:3]
                    ],
                    "relevant_files": relevant_files[:3]
                },
                "output": {
                    "design_solution": design_sections.get("design_solution", ""),
                    "reasoning_trace": design_sections.get("reasoning_trace", "")
                },
                "metadata": {
                    "generated_with_llm": self.has_llm,
                    "generation_timestamp": self._get_timestamp(),
                    "language": language
                }
            }

            self.logger.debug(f"为需求 {requirement.get('id')} 生成 {language} 设计方案")

            # 避免频繁调用API
            if self.has_llm:
                await asyncio.sleep(1.5)

            return design_case

        except Exception as e:
            self.logger.error(f"为需求 {requirement.get('id', 'unknown')} 生成设计方案时出错: {e}")
            return None

    async def generate_all_designs(self) -> List[Dict[str, Any]]:
        """生成所有设计方案"""
        all_designs = []

        if not self.business_rules:
            self.logger.error("数据未加载")
            return all_designs

        # 根据语言设置确定需要生成的语言
        if not self.has_llm:
            # 无LLM时只生成中文
            languages = ["zh"]
            # 需要的需求数量
            needed_requirements = self.num_designs
        elif self.language:
            # 指定语言时生成指定语言
            languages = [self.language]
            needed_requirements = self.num_designs
        else:
            # 无语言参数时生成中英文
            languages = ["zh", "en"]
            # 每个需求生成2个设计方案，所以需要的需求数量减半
            needed_requirements = max(1, self.num_designs // 2)

        # 选择需求
        selected_requirements = self.select_requirements()

        # 调整选择的规则数量
        if len(selected_requirements) > needed_requirements:
            selected_requirements = selected_requirements[:needed_requirements]

        self.logger.info(f"选择了 {len(selected_requirements)} 个需求用于生成设计方案，目标生成 {self.num_designs} 个设计方案")

        # 并发生成设计方案
        tasks = []
        for requirement in selected_requirements:
            for language in languages:
                task = self.generate_design_for_requirement(requirement, language)
                tasks.append(task)

        # 执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 收集结果
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"生成设计方案时发生异常: {result}")
            elif result:
                all_designs.append(result)

        # 如果生成的设计方案数量超过目标数量，随机选择
        if len(all_designs) > self.num_designs:
            all_designs = random.sample(all_designs, self.num_designs)

        self.logger.info(f"生成了 {len(all_designs)} 个设计方案")

        # 统计信息
        language_stats = {}
        category_stats = {}

        for design in all_designs:
            language = design.get("metadata", {}).get("language", "unknown")
            category = design.get("input", {}).get("requirement_category", "unknown")

            language_stats[language] = language_stats.get(language, 0) + 1
            category_stats[category] = category_stats.get(category, 0) + 1

        self.logger.info(f"语言分布: {language_stats}")
        self.logger.info(f"需求分类分布: {category_stats}")

        return all_designs

    def save_designs(self, designs: List[Dict[str, Any]]) -> None:
        """保存设计方案到文件"""
        try:
            # 根据语言参数确定输出文件名
            if not self.has_llm:
                # 无LLM时生成基础文件
                output_file = self.output_file.parent / f"base_designs.json"
            elif self.language == 'zh':
                output_file = self.output_file.parent / f"enhanced_designs_zh.json"
            elif self.language == 'en':
                output_file = self.output_file.parent / f"enhanced_designs_en.json"
            else:
                output_file = self.output_file  # 保持原文件名

            # 准备输出数据
            output_data = {
                "project": self.business_rules.get("project", "unknown") if self.business_rules else "unknown",
                "total_designs": len(designs),
                "generated_with_llm": self.has_llm,
                "language": self.language if self.language else "both",
                "generation_timestamp": self._get_timestamp(),
                "designs": designs
            }

            # 保存到文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"已保存 {len(designs)} 个设计方案到 {output_file}")

            # 打印统计信息
            print(f"\n=== 设计方案生成统计 ===")
            print(f"目标数量: {self.num_designs}")
            print(f"实际生成: {len(designs)}")
            print(f"生成语言: {self.language if self.language else '中英文'}")
            print(f"使用LLM: {self.has_llm}")
            print(f"输出文件: {output_file}")

            # 显示示例
            if designs:
                print(f"\n示例设计方案结构:")
                sample = designs[0]
                print(f"1. 输入 (input):")
                print(f"   需求ID: {sample['input']['requirement_id']}")
                print(f"   语言: {sample['input']['language']}")
                desc = sample['input']['requirement_description']
                if len(desc) > 80:
                    desc = desc[:80] + "..."
                print(f"   需求描述: {desc}")
                print(f"   相关代码引用: {len(sample['input']['relevant_code_references'])} 个")

                print(f"\n2. 输出 (output):")
                design_solution = sample['output']['design_solution']
                if len(design_solution) > 100:
                    design_solution = design_solution[:100] + "..."
                print(f"   设计方案: {design_solution}")

                reasoning_trace = sample['output']['reasoning_trace']
                if len(reasoning_trace) > 100:
                    reasoning_trace = reasoning_trace[:100] + "..."
                print(f"   推理 trace: {reasoning_trace}")

        except Exception as e:
            self.logger.error(f"保存设计方案时出错: {e}")
            raise

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async def generate_and_save_async(self) -> Dict[str, Any]:
        """异步生成并保存设计方案"""
        self.logger.info("开始生成设计方案...")

        if not self.business_rules:
            return {
                "status": "error",
                "message": "数据未加载"
            }

        designs = await self.generate_all_designs()

        if designs:
            self.save_designs(designs)
            # 确定实际输出文件名
            if not self.has_llm:
                output_file = self.output_file.parent / f"base_designs.json"
            elif self.language == 'zh':
                output_file = self.output_file.parent / f"enhanced_designs_zh.json"
            elif self.language == 'en':
                output_file = self.output_file.parent / f"enhanced_designs_en.json"
            else:
                output_file = self.output_file

            return {
                "status": "success",
                "total_designs": len(designs),
                "has_llm": self.has_llm,
                "language": self.language if self.language else "both",
                "output_file": str(output_file)
            }
        else:
            self.logger.warning("未生成任何设计方案")
            return {
                "status": "no_designs_generated",
                "total_designs": 0,
                "has_llm": self.has_llm,
                "language": self.language if self.language else "both",
                "output_file": str(self.output_file)
            }

    def generate_and_save(self) -> Dict[str, Any]:
        """同步生成并保存设计方案"""
        return asyncio.run(self.generate_and_save_async())


def main():
    """主函数"""
    import sys
    import argparse

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="简化架构设计方案生成器（支持多语言，输入输出语言一致）")

    parser.add_argument("--rules", type=str, default="../data/business_rule.json",
                       help="业务规则文件路径，默认为 ../data/business_rule.json")
    parser.add_argument("--output", type=str, default="../data/design_solution/enhanced_designs.json",
                       help="输出文件路径，默认为 ../data/design_solution/enhanced_designs.json")
    parser.add_argument("--num", type=int, default=10,
                       help="要生成的设计方案数量，默认为10")
    parser.add_argument("--lang", type=str, choices=['zh', 'en'], default=None,
                       help="指定生成的语言，zh=中文, en=英文，默认中英文皆有（仅当有LLM时）")

    args = parser.parse_args()

    # 加载环境变量
    load_dotenv()

    # 检查API密钥
    api_key = os.getenv("ZHIPU_API_KEY")
    if api_key:
        print(f"使用智谱AI API生成增强设计方案")
    else:
        print(f"未配置智谱AI API，将生成基础设计方案")
        print(f"提示: 创建.env文件并添加 ZHIPU_API_KEY=your_api_key")

    print(f"业务规则文件: {args.rules}")
    print(f"输出文件: {args.output}")
    print(f"生成数量: {args.num}")
    print(f"生成语言: {args.lang if args.lang else '中英文（仅当有LLM时）'}")

    # 创建生成器并运行
    generator = SimpleDesignGenerator(
        business_rule_file=args.rules,
        output_file=args.output,
        num_designs=args.num,
        language=args.lang
    )

    result = generator.generate_and_save()

    # 打印结果
    print(f"\n{'='*50}")
    if result.get("status") == "success":
        print(f"✓ 生成成功!")
        print(f"   生成数量: {result.get('total_designs')}")
        print(f"   生成语言: {result.get('language')}")
        print(f"   输出文件: {result.get('output_file')}")
    else:
        print(f"✗ 生成失败!")
        print(f"   错误信息: {result.get('message', '未知错误')}")

    return result


if __name__ == "__main__":
    main()
