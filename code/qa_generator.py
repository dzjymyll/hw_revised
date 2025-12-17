"""
增强问答对生成器 - 使用智谱AI API生成丰富的问答对
支持按比例生成不同技术层级的问答对：level1: 50%, level2: 40%, level3: 10%
改进版：修复占位符问题，增强格式解析
"""
import json
import asyncio
import re
# import aiohttp
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import datetime
import random
import os
from dotenv import load_dotenv
from openai import OpenAI


class EnhancedQAGenerator:
    """增强问答对生成器（使用智谱AI API）"""

    def __init__(self, rules_file: str = "../data/business_rule.json",
                 output_file: str = "../data/qa_pairs/qa_pairs.json",
                 num_pairs: int = 100,
                 language: str = None,
                 level_ratio: Dict[str, float] = None):
        """
        初始化问答对生成器

        Args:
            rules_file: 业务规则文件路径
            output_file: 输出文件路径
            num_pairs: 要生成的问答对数量，默认100
            language: 指定生成的语言，'zh'=中文, 'en'=英文, None=中英文皆有
            level_ratio: 各层级问答对的比例，默认{"level_1": 0.5, "level_2": 0.4, "level_3": 0.1}
        """
        self.rules_file = Path(rules_file)
        self.output_file = Path(output_file)
        self.num_pairs = num_pairs
        self.language = language

        # 设置层级比例
        if level_ratio is None:
            self.level_ratio = {"level_1": 0.5, "level_2": 0.4, "level_3": 0.1}
        else:
            self.level_ratio = level_ratio

        self.logger = logging.getLogger(__name__)

        # 确保输出目录存在
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        # 初始化智谱AI客户端
        self.api_key = os.getenv("ZHIPU_API_KEY")
        self.base_url = os.getenv("ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4/")

        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            self.has_llm = True
            self.logger.info("智谱AI API已配置，将生成增强的问答对")
        else:
            self.client = None
            self.has_llm = False
            self.logger.warning("未配置智谱AI API，将使用基础生成器")

        # 加载规则
        self.rules_data = None
        if self.rules_file.exists():
            self.load_rules()
        else:
            self.logger.error(f"规则文件不存在: {self.rules_file}")

    def load_rules(self) -> None:
        """加载业务规则"""
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                self.rules_data = json.load(f)
            self.logger.info(f"已加载规则数据，包含 {len(self.rules_data.get('rules', []))} 条规则")
        except Exception as e:
            self.logger.error(f"加载规则数据时出错: {e}")
            raise

    def select_rules_by_level(self) -> Dict[str, List[Dict[str, Any]]]:
        """根据层级要求选择合适的规则"""
        if not self.rules_data:
            return {}

        rules = self.rules_data.get("rules", [])
        selected_rules = {"level_1": [], "level_2": [], "level_3": []}

        # 计算每个层级需要的规则数量
        if not self.has_llm:
            # 无LLM时每个规则只生成一个中文问答对
            level_1_needed = max(1, int(self.num_pairs * self.level_ratio["level_1"]))
            level_2_needed = max(1, int(self.num_pairs * self.level_ratio["level_2"]))
            level_3_needed = max(0, int(self.num_pairs * self.level_ratio["level_3"]))
        elif self.language:
            # 指定语言时每个规则生成一个问答对
            level_1_needed = max(1, int(self.num_pairs * self.level_ratio["level_1"]))
            level_2_needed = max(1, int(self.num_pairs * self.level_ratio["level_2"]))
            level_3_needed = max(1, int(self.num_pairs * self.level_ratio["level_3"]))
        else:
            # 中英文皆有，每个规则生成2个问答对
            level_1_needed = max(1, int(self.num_pairs * self.level_ratio["level_1"] / 2))
            level_2_needed = max(1, int(self.num_pairs * self.level_ratio["level_2"] / 2))
            level_3_needed = max(1, int(self.num_pairs * self.level_ratio["level_3"] / 2))

        # 根据规则类型分配到不同层级
        for rule in rules:
            rule_type = rule.get("type", "")

            # Level 1: 基础类型 - 适合生成事实性问题
            if rule_type in ["import", "config", "template", "file_structure"]:
                selected_rules["level_1"].append(rule)

            # Level 2: 中等类型 - 适合生成理解性问题
            elif rule_type in ["function", "model", "class"]:
                selected_rules["level_2"].append(rule)

            # Level 3: 高级类型 - 适合生成架构分析问题
            elif rule_type in ["endpoint"]:
                selected_rules["level_3"].append(rule)

        # 随机选择每个层级需要的规则数量
        final_selected = {"level_1": [], "level_2": [], "level_3": []}

        for level, rules_list in selected_rules.items():
            needed = {
                "level_1": level_1_needed,
                "level_2": level_2_needed,
                "level_3": level_3_needed
            }[level]

            if rules_list:
                if needed > len(rules_list):
                    # 重复选择
                    repeat_times = needed // len(rules_list) + 1
                    repeated_rules = rules_list * repeat_times
                    random.shuffle(repeated_rules)
                    final_selected[level] = repeated_rules[:needed]
                else:
                    final_selected[level] = random.sample(rules_list, needed)

        # 打印选择统计
        total_selected = sum(len(rules) for rules in final_selected.values())
        self.logger.info(f"按层级选择规则: Level1={len(final_selected['level_1'])}, "
                        f"Level2={len(final_selected['level_2'])}, "
                        f"Level3={len(final_selected['level_3'])}, 总计={total_selected}")

        return final_selected

    def prepare_prompt_by_level(self, rule: Dict[str, Any], language: str, level: str) -> str:
        """根据层级准备不同的提示词，避免占位符"""
        rule_type = rule.get("type", "")
        rule_name = rule.get("name", "")
        file_path = rule.get("file", "")
        code_snippet = rule.get("code_snippet", "")
        metadata = rule.get("metadata", {})

        # 对于import类型，如果没有name字段，使用match字段作为名称
        if rule_type == "import" and not rule_name:
            rule_name = rule.get("match", "import语句")

        # 根据规则类型选择问题类型
        if rule_type == "endpoint":
            question_type = "API端点"
            details = f"HTTP方法: {metadata.get('http_method', '')}, 路由路径: {metadata.get('route_path', '')}"
        elif rule_type == "function":
            question_type = "函数"
            details = f"参数: {metadata.get('args', [])}, 异步: {metadata.get('is_async', False)}"
        elif rule_type == "model":
            question_type = "数据模型"
            details = f"字段: {metadata.get('fields', [])[:3] if metadata.get('fields') else '无'}"
        elif rule_type == "file_structure":
            question_type = "项目结构"
            details = f"文件类型分布: {metadata.get('file_types', {})}"
        elif rule_type == "import":
            question_type = "导入语句"
            imports = metadata.get("imports", [])
            total_imports = metadata.get("total_imports", 0)
            details = f"总导入数: {total_imports}, 主要导入: {', '.join(imports[:3]) if imports else '无'}"
            if not code_snippet and imports:
                code_snippet = "\n".join(imports[:10])
        elif rule_type == "config":
            question_type = "配置文件"
            details = f"文件类型: {metadata.get('file_type', '')}, 行数: {metadata.get('lines', 0)}"
        elif rule_type == "template":
            question_type = "模板文件"
            details = f"行数: {metadata.get('lines', 0)}, 模板变量: {len(metadata.get('template_variables', []))}个"
        elif rule_type == "class":
            question_type = "类定义"
            bases = metadata.get("bases", [])
            details = f"基类: {', '.join(bases) if bases else '无'}, 方法数: {len(metadata.get('methods', []))}"
        else:
            question_type = "代码组件"
            details = ""

        if language == "zh":
            if level == "level_1":
                # Level 1: 基础事实性问题 - 强调不要使用占位符
                prompt = f"""请基于以下代码信息生成一个基础问答对：

{question_type}名称: {rule_name}
文件路径: {file_path}
详细说明: {details}
代码片段:
{code_snippet[:500]}

请生成：
1. 一个基础事实性问题（如：这个组件是什么？包含什么？在哪里？）
2. 一个简洁明确的答案，直接回答上述问题

重要要求：
- 不要使用任何方括号[]、尖括号<>或占位符
- 直接生成具体的问题和答案
- 问题和答案都应该是完整的句子
- 问题不要以"问题："开头，直接写问题内容
- 答案不要以"答案："开头，直接写答案内容

格式要求（不要复制这个示例，生成你自己的内容）：
问题内容
答案内容"""
            elif level == "level_2":
                # Level 2: 功能理解性问题
                prompt = f"""请基于以下代码信息生成一个功能理解性问答对：

{question_type}名称: {rule_name}
文件路径: {file_path}
详细说明: {details}
代码片段:
{code_snippet[:500]}

请生成：
1. 一个功能理解性问题（如：这个组件如何工作？为什么这样设计？有什么作用？）
2. 一个详细的答案，包含代码功能、工作流程和关键代码解释

重要要求：
- 不要使用任何占位符（如[功能理解性问题]、[详细解释答案]等）
- 直接生成具体的问题和答案
- 问题不要以"问题："开头，直接写问题内容
- 答案不要以"答案："开头，直接写答案内容

格式要求：
问题内容
答案内容"""
            else:  # level == "level_3"
                # Level 3: 架构分析性问题
                prompt = f"""请基于以下代码信息生成一个架构分析性问答对：

{question_type}名称: {rule_name}
文件路径: {file_path}
详细说明: {details}
代码片段:
{code_snippet[:500]}

请生成：
1. 一个架构或设计层面的深入问题（如：架构设计考虑？性能优化？安全机制？扩展性？）
2. 一个深入的技术分析答案，包含架构设计原理、性能优化、安全机制等考虑

重要要求：
- 不要使用任何占位符（如[架构/设计问题]、[深入技术分析]等）
- 直接生成具体的问题和答案
- 问题不要以"问题："开头，直接写问题内容
- 答案不要以"答案："开头，直接写答案内容

格式要求：
问题内容
答案内容"""
        else:  # English
            if level == "level_1":
                # Level 1: Basic factual questions
                prompt = f"""Please generate a basic Q&A pair based on the following code information:

{question_type} Name: {rule_name}
File Path: {file_path}
Details: {details}
Code Snippet:
{code_snippet[:500]}

Please generate:
1. A basic factual question (e.g., What is this component? What does it contain? Where is it?)
2. A concise and direct answer to the above question

Important requirements:
- Do not use any placeholders like [Basic question], [Direct answer], etc.
- Generate specific questions and answers directly
- Do not start the question with "Question:" or "问题："
- Do not start the answer with "Answer:" or "答案："

Format requirements:
Question content
Answer content"""
            elif level == "level_2":
                # Level 2: Functional understanding questions
                prompt = f"""Please generate a functional Q&A pair based on the following code information:

{question_type} Name: {rule_name}
File Path: {file_path}
Details: {details}
Code Snippet:
{code_snippet[:500]}

Please generate:
1. A functional understanding question (e.g., How does this component work? Why is it designed this way? What is its purpose?)
2. A detailed answer that includes the code function, workflow and key code explanation

Important requirements:
- Do not use any placeholders like [Functional question], [Detailed explanation], etc.
- Generate specific questions and answers directly
- Do not start the question with "Question:" or "问题："
- Do not start the answer with "Answer:" or "答案："

Format requirements:
Question content
Answer content"""
            else:  # level == "level_3"
                # Level 3: Architectural analysis questions
                prompt = f"""Please generate an architectural analysis Q&A pair based on the following code information:

{question_type} Name: {rule_name}
File Path: {file_path}
Details: {details}
Code Snippet:
{code_snippet[:500]}

Please generate:
1. An in-depth architectural or design question (e.g., Architectural design considerations? Performance optimization? Security mechanisms? Scalability?)
2. A deep technical analysis answer that includes architectural design principles, performance optimization, security mechanisms, etc.

Important requirements:
- Do not use any placeholders like [Architectural/Design question], [Deep technical analysis], etc.
- Generate specific questions and answers directly
- Do not start the question with "Question:" or "问题："
- Do not start the answer with "Answer:" or "答案："

Format requirements:
Question content
Answer content"""
        return prompt

    def validate_qa_content(self, question: str, answer: str) -> bool:
        """验证问答对内容是否有效"""
        # 检查是否为空
        if not question or not answer:
            return False

        # 检查是否包含常见占位符
        placeholders = [
            # 中文占位符
            '[基础问题]', '[直接答案]', '[功能理解性问题]',
            '[详细解释答案]', '[架构/设计问题]', '[深入技术分析]',
            '【基础问题】', '【直接答案】', '【功能理解性问题】',
            '【详细解释答案】', '【架构/设计问题】', '【深入技术分析】',
            '<基础问题>', '<直接答案>', '<功能理解性问题>',
            '<详细解释答案>', '<架构/设计问题>', '<深入技术分析>',

            # 英文占位符
            '[Basic question]', '[Direct answer]', '[Functional question]',
            '[Detailed explanation]', '[Architectural/Design question]',
            '[Deep technical analysis]',
            '[Basic Question]', '[Direct Answer]', '[Functional Question]',
            '[Detailed Explanation]', '[Architectural/Design Question]',
            '[Deep Technical Analysis]',

            # 简单占位符
            '[问题]', '[答案]', '[question]', '[answer]',
            '【问题】', '【答案】', '【question】', '【answer】',
            '<问题>', '<答案>', '<question>', '<answer>',
        ]

        for placeholder in placeholders:
            if placeholder in question or placeholder in answer:
                self.logger.debug(f"检测到占位符: {placeholder}")
                return False

        # 检查是否包含方括号占位符模式
        if re.search(r'\[.*?\]', question) or re.search(r'\[.*?\]', answer):
            self.logger.debug("检测到方括号占位符模式")
            return False

        # 检查是否包含中文方括号占位符模式
        if re.search(r'【.*?】', question) or re.search(r'【.*?】', answer):
            self.logger.debug("检测到中文方括号占位符模式")
            return False

        # 检查是否包含尖括号占位符模式
        if re.search(r'<.*?>', question) or re.search(r'<.*?>', answer):
            self.logger.debug("检测到尖括号占位符模式")
            return False

        # 检查问题是否过于简单（只是一个标签）
        if len(question.strip()) < 10:
            self.logger.debug(f"问题太短: {question}")
            return False

        # 检查问题是否只是"问题"或"Question"
        if question.strip() in ['问题', 'Question', '问题：', 'Question:']:
            self.logger.debug(f"问题只是标签: {question}")
            return False

        # 检查答案是否只是"答案"或"Answer"
        if answer.strip() in ['答案', 'Answer', '答案：', 'Answer:']:
            self.logger.debug(f"答案只是标签: {answer}")
            return False

        # 检查是否包含"问题："或"答案："前缀（应该已经去除）
        if question.strip().startswith('问题：') or question.strip().startswith('Question:'):
            self.logger.debug(f"问题包含前缀: {question}")
            return False

        if answer.strip().startswith('答案：') or answer.strip().startswith('Answer:'):
            self.logger.debug(f"答案包含前缀: {answer}")
            return False

        return True

    async def call_zhipu_api(self, prompt: str) -> Optional[Tuple[str, str]]:
        """调用智谱AI API，增强格式解析能力"""
        if not self.has_llm or not self.client:
            return None

        try:
            model = "glm-4"

            # 使用更明确的系统提示
            system_content = """你是一个专业的代码分析助手。请严格按照以下要求生成问答对：
1. 直接生成具体的问题和答案，不要使用任何占位符（如[问题]、[答案]等）
2. 问题不要以"问题："或"Question:"开头
3. 答案不要以"答案："或"Answer:"开头
4. 确保问题和答案都是完整的句子
5. 按照用户指定的格式生成内容"""

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            content = response.choices[0].message.content.strip()
            self.logger.debug(f"API响应内容（前200字符）: {content[:200]}...")

            # 增强的解析逻辑，支持多种格式
            patterns = [
                # 格式1: "问题：xxx\n答案：xxx"（带中文冒号）
                (r'问题[：:]\s*(.*?)\s*\n\s*答案[：:]\s*(.*)', re.DOTALL),
                # 格式2: "Question: xxx\nAnswer: xxx"
                (r'Question[：:]\s*(.*?)\s*\n\s*Answer[：:]\s*(.*)', re.DOTALL),
                # 格式3: 以"1."开头的问题和"2."开头的答案
                (r'1[\.、]\s*(.*?)\s*\n\s*2[\.、]\s*(.*)', re.DOTALL),
                # 格式4: 空行分隔的问题和答案
                (r'^(.*?)\s*\n\s*\n\s*(.*)$', re.DOTALL),
                # 格式5: 简单换行分隔
                (r'^(.*?)\s*\n\s*(.*)$', re.DOTALL),
            ]

            for pattern, flags in patterns:
                match = re.search(pattern, content, flags)
                if match:
                    question = match.group(1).strip()
                    answer = match.group(2).strip()

                    # 清理可能的残留前缀
                    question = re.sub(r'^(问题[：:]|Question[：:]\s*)', '', question)
                    answer = re.sub(r'^(答案[：:]|Answer[：:]\s*)', '', answer)

                    # 验证内容
                    if self.validate_qa_content(question, answer):
                        self.logger.debug(f"成功解析问答对: 问题长度={len(question)}, 答案长度={len(answer)}")
                        return question, answer
                    else:
                        self.logger.warning(f"解析的内容包含占位符或无效: 问题='{question[:50]}...', 答案='{answer[:50]}...'")

            # 如果所有格式都匹配失败，尝试智能分割
            lines = [line.strip() for line in content.split('\n') if line.strip()]

            if len(lines) >= 2:
                # 简单假设第一行是问题，其余是答案
                question = lines[0]
                answer = '\n'.join(lines[1:])

                # 清理前缀
                question = re.sub(r'^(问题[：:]|Question[：:]\s*)', '', question)
                answer = re.sub(r'^(答案[：:]|Answer[：:]\s*)', '', answer)

                if self.validate_qa_content(question, answer):
                    return question, answer

            self.logger.warning(f"无法解析API响应格式。内容: {content[:200]}...")
            return None

        except Exception as e:
            self.logger.error(f"调用智谱AI API时出错: {e}")
            return None

    def generate_simple_qa_by_level(self, rule: Dict[str, Any], language: str, level: str) -> Tuple[str, str]:
        """根据层级生成简单的问答对（无LLM时使用）"""
        rule_type = rule.get("type", "")
        rule_name = rule.get("name", "")

        if rule_type == "import" and not rule_name:
            rule_name = rule.get("match", "import语句")

        file_path = rule.get("file", "")
        metadata = rule.get("metadata", {})

        if level == "level_1":
            # 基础事实性问题
            if language == "zh":
                if rule_type == "import":
                    imports = metadata.get("imports", [])
                    question = f"{file_path}文件中导入了哪些模块？"
                    answer = f"导入了{len(imports)}个模块，包括：{', '.join(imports[:5]) if imports else '无'}"
                elif rule_type == "config":
                    question = f"{rule_name}配置文件的作用是什么？"
                    answer = f"{rule_name}是项目的配置文件，包含基本设置参数。"
                else:
                    question = f"{rule_name}是什么？"
                    answer = f"{rule_name}是项目中的一个{rule_type}组件。"
            else:
                if rule_type == "import":
                    imports = metadata.get("imports", [])
                    question = f"What modules are imported in {file_path}?"
                    answer = f"Imported {len(imports)} modules, including: {', '.join(imports[:5]) if imports else 'none'}"
                elif rule_type == "config":
                    question = f"What is the purpose of the {rule_name} configuration file?"
                    answer = f"{rule_name} is a configuration file for the project, containing basic settings."
                else:
                    question = f"What is {rule_name}?"
                    answer = f"{rule_name} is a {rule_type} component in the project."

        elif level == "level_2":
            # 功能理解性问题
            if language == "zh":
                if rule_type == "function":
                    question = f"{rule_name}函数是如何工作的？"
                    answer = f"{rule_name}函数处理相关业务逻辑，接收特定参数并返回处理结果。"
                elif rule_type == "model":
                    question = f"{rule_name}数据模型的主要功能是什么？"
                    answer = f"{rule_name}模型定义了数据结构，用于数据存储和验证。"
                else:
                    question = f"{rule_name}的主要功能是什么？"
                    answer = f"{rule_name}负责处理{rule_type}相关的业务逻辑。"
            else:
                if rule_type == "function":
                    question = f"How does the {rule_name} function work?"
                    answer = f"The {rule_name} function handles related business logic, accepts specific parameters and returns processing results."
                elif rule_type == "model":
                    question = f"What is the main function of the {rule_name} data model?"
                    answer = f"The {rule_name} model defines the data structure for data storage and validation."
                else:
                    question = f"What is the main function of {rule_name}?"
                    answer = f"{rule_name} is responsible for handling {rule_type}-related business logic."

        else:  # level == "level_3"
            # 架构分析性问题
            if language == "zh":
                if rule_type == "endpoint":
                    question = f"{rule_name}端点的架构设计考虑是什么？"
                    answer = f"{rule_name}端点遵循RESTful设计原则，考虑了请求处理、数据验证和错误处理机制。"
                else:
                    question = f"{rule_name}的架构设计有什么考虑？"
                    answer = f"{rule_name}的设计考虑了模块化、可扩展性和性能优化等因素。"
            else:
                if rule_type == "endpoint":
                    question = f"What are the architectural design considerations for the {rule_name} endpoint?"
                    answer = f"The {rule_name} endpoint follows RESTful design principles, considering request handling, data validation, and error handling mechanisms."
                else:
                    question = f"What are the architectural design considerations for {rule_name}?"
                    answer = f"The design of {rule_name} considers factors such as modularity, scalability, and performance optimization."

        return question, answer

    async def generate_qa_pair_for_rule(self, rule: Dict[str, Any], language: str, level: str) -> Optional[Dict[str, Any]]:
        """为单个规则生成指定语言和层级的问答对"""
        try:
            max_retries = 3  # 最大重试次数
            retry_count = 0
            question, answer = "", ""

            while retry_count <= max_retries:
                if self.has_llm:
                    # 使用LLM生成
                    prompt = self.prepare_prompt_by_level(rule, language, level)
                    result = await self.call_zhipu_api(prompt)

                    if result:
                        question, answer = result

                        # 验证生成的内容
                        if self.validate_qa_content(question, answer):
                            self.logger.debug(f"成功生成有效的问答对（尝试{retry_count+1}次）")
                            break  # 内容有效，退出循环
                        else:
                            self.logger.warning(f"生成的内容包含占位符或无效，第{retry_count + 1}次重试")
                            retry_count += 1
                            # 等待一下再重试，避免频率限制
                            await asyncio.sleep(0.5)
                            continue
                    else:
                        # 如果API调用失败，使用简单生成
                        self.logger.warning("API调用失败，使用简单生成")
                        self.has_llm = False
                        break
                else:
                    # 无LLM时使用简单生成
                    break

            # 如果重试后仍然无效或没有LLM，使用简单生成
            if retry_count > max_retries or not self.has_llm or not question or not answer:
                question, answer = self.generate_simple_qa_by_level(rule, language, level)
                self.logger.debug(f"使用简单生成: 问题长度={len(question)}, 答案长度={len(answer)}")

            # 提取数据处理信息
            data_processing_info = self._extract_data_processing_info(rule, answer)

            # 构建问答对
            qa_pair = {
                "question": question,
                "answer": answer,
                "level": level,
                "language": language,
                "code_references": [
                    {
                        "file_path": rule.get("file", ""),
                        "description": f"{rule.get('type', '')}: {rule.get('name', rule.get('match', ''))}",
                        "code_snippet": rule.get("code_snippet", "")[:300] + "..." if rule.get("code_snippet") else ""
                    }
                ],
                "data_processing_info": data_processing_info
            }

            return qa_pair

        except Exception as e:
            self.logger.error(f"为规则生成问答对时出错: {e}")
            return None

    def _extract_data_processing_info(self, rule: Dict[str, Any], answer: str) -> Dict[str, Any]:
        """从答案中提取数据处理信息"""
        answer_lower = answer.lower()

        data_processing_info = {
            "database_operations": [],
            "validation_rules": [],
            "data_transformations": []
        }

        # 检测关键词
        if "数据库" in answer_lower or "database" in answer_lower:
            data_processing_info["database_operations"].append("数据库操作")
        if "验证" in answer_lower or "validation" in answer_lower:
            data_processing_info["validation_rules"].append("数据验证")
        if "转换" in answer_lower or "transform" in answer_lower:
            data_processing_info["data_transformations"].append("数据转换")

        return data_processing_info

    async def generate_qa_pairs_by_level(self, rules_by_level: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """按层级生成问答对"""
        all_qa_pairs = []

        # 确定语言
        if not self.has_llm:
            languages = ["zh"]
        elif self.language:
            languages = [self.language]
        else:
            languages = ["zh", "en"]

        # 计算每个层级的目标数量
        level_targets = {
            "level_1": int(self.num_pairs * self.level_ratio["level_1"]),
            "level_2": int(self.num_pairs * self.level_ratio["level_2"]),
            "level_3": int(self.num_pairs * self.level_ratio["level_3"])
        }

        # 为每个层级和语言生成问答对
        for level in ["level_1", "level_2", "level_3"]:
            rules = rules_by_level.get(level, [])
            target_count = level_targets[level]

            if not rules:
                self.logger.warning(f"没有可用于层级 {level} 的规则")
                continue

            # 计算每个语言需要生成的数量
            for language in languages:
                # 如果只有一种语言，分配全部数量
                # 如果有两种语言，各分配一半
                if len(languages) == 1:
                    language_target = target_count
                else:
                    language_target = target_count // 2
                    if language == "zh":
                        language_target += target_count % 2  # 如果奇数，中文多一个

                self.logger.info(f"为层级 {level} 语言 {language} 生成 {language_target} 个问答对")

                generated = 0
                rule_index = 0

                while generated < language_target and rule_index < len(rules):
                    rule = rules[rule_index]

                    qa_pair = await self.generate_qa_pair_for_rule(rule, language, level)
                    if qa_pair:
                        all_qa_pairs.append(qa_pair)
                        generated += 1

                    rule_index += 1

                    # 避免频繁调用API
                    if self.has_llm:
                        await asyncio.sleep(1)

                self.logger.info(f"层级 {level} 语言 {language} 已生成 {generated} 个问答对")

        return all_qa_pairs

    async def generate_all_qa_pairs(self) -> List[Dict[str, Any]]:
        """生成所有问答对"""
        all_qa_pairs = []

        if not self.rules_data:
            self.logger.error("规则数据未加载")
            return all_qa_pairs

        # 按层级选择规则
        rules_by_level = self.select_rules_by_level()

        if not any(rules_by_level.values()):
            self.logger.error("没有可用的规则")
            return all_qa_pairs

        # 生成问答对
        all_qa_pairs = await self.generate_qa_pairs_by_level(rules_by_level)

        # 如果生成的问答对数量超过目标数量，随机选择
        if len(all_qa_pairs) > self.num_pairs:
            all_qa_pairs = random.sample(all_qa_pairs, self.num_pairs)

        # 统计信息
        level_stats = {}
        language_stats = {}

        for qa in all_qa_pairs:
            level = qa.get("level", "unknown")
            language = qa.get("language", "unknown")

            level_stats[level] = level_stats.get(level, 0) + 1
            language_stats[language] = language_stats.get(language, 0) + 1

        self.logger.info(f"最终生成 {len(all_qa_pairs)} 个问答对")
        self.logger.info(f"层级分布: {level_stats}")
        self.logger.info(f"语言分布: {language_stats}")

        return all_qa_pairs

    def save_qa_pairs(self, qa_pairs: List[Dict[str, Any]]) -> None:
        """保存问答对到文件"""
        try:

            # 根据语言参数确定输出文件名
            if self.has_llm:
                if self.language == 'zh':
                    filename = f"enhanced_qa_pairs_zh.json"
                elif self.language == 'en':
                    filename = f"enhanced_qa_pairs_en.json"
                else:
                    filename = f"enhanced_qa_pairs_two_language.json"
            else:
                filename = "base_qa_pairs.json"

            output_file = self.output_file.parent / filename

            # 准备输出数据
            output_data = {
                "project": self.rules_data.get("project", "unknown") if self.rules_data else "unknown",
                "total_qa_pairs": len(qa_pairs),
                "generated_with_llm": self.has_llm,
                "language": self.language if self.language else "both",
                "level_ratio": self.level_ratio,
                "generation_time": datetime.datetime.now().isoformat(),
                "statistics": {
                    "levels": {},
                    "languages": {}
                },
                "qa_pairs": qa_pairs
            }

            # 统计信息
            for qa in qa_pairs:
                level = qa.get("level", "unknown")
                language = qa.get("language", "unknown")

                if level not in output_data["statistics"]["levels"]:
                    output_data["statistics"]["levels"][level] = 0
                if language not in output_data["statistics"]["languages"]:
                    output_data["statistics"]["languages"][language] = 0

                output_data["statistics"]["levels"][level] += 1
                output_data["statistics"]["languages"][language] += 1

            # 保存到文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"已保存 {len(qa_pairs)} 个问答对到 {output_file}")

            # 打印统计信息
            print(f"\n{'='*60}")
            print(f"✓ 问答对生成完成!")
            print(f"{'='*60}")
            print(f"目标数量: {self.num_pairs}")
            print(f"实际生成: {len(qa_pairs)}")
            print(f"生成语言: {self.language if self.language else '中英文'}")
            print(f"层级比例: Level1={self.level_ratio['level_1']*100}%, "
                  f"Level2={self.level_ratio['level_2']*100}%, "
                  f"Level3={self.level_ratio['level_3']*100}%")
            print(f"层级分布:")
            for level, count in sorted(output_data["statistics"]["levels"].items()):
                percentage = (count / len(qa_pairs)) * 100 if qa_pairs else 0
                print(f"  {level}: {count} ({percentage:.1f}%)")
            print(f"语言分布:")
            for lang, count in output_data["statistics"]["languages"].items():
                percentage = (count / len(qa_pairs)) * 100 if qa_pairs else 0
                print(f"  {lang}: {count} ({percentage:.1f}%)")
            print(f"输出文件: {output_file}")
            print(f"{'='*60}")

            # 显示示例
            if qa_pairs:
                print(f"\n示例问答对:")
                for level in ["level_1", "level_2", "level_3"]:
                    level_pairs = [q for q in qa_pairs if q.get("level") == level]
                    if level_pairs:
                        qa = level_pairs[0]
                        print(f"\n{level.upper()} 示例:")
                        print(f"  问题: {qa.get('question', '')}")
                        answer_preview = qa.get('answer', '')
                        if len(answer_preview) > 100:
                            answer_preview = answer_preview[:100] + "..."
                        print(f"  答案: {answer_preview}")
                        print(f"  语言: {qa.get('language', 'zh')}")

            print(f"{'='*60}\n")

        except Exception as e:
            self.logger.error(f"保存问答对时出错: {e}")
            raise

    async def generate_and_save_async(self) -> Dict[str, Any]:
        """异步生成并保存问答对"""
        self.logger.info("开始生成问答对...")

        if not self.rules_data:
            return {
                "status": "error",
                "message": "规则数据未加载"
            }

        qa_pairs = await self.generate_all_qa_pairs()

        if qa_pairs:
            self.save_qa_pairs(qa_pairs)
            return {
                "status": "success",
                "total_qa_pairs": len(qa_pairs),
                "has_llm": self.has_llm,
                "language": self.language if self.language else "both",
                "level_ratio": self.level_ratio
            }
        else:
            self.logger.warning("未生成任何问答对")
            return {
                "status": "no_qa_pairs_generated",
                "total_qa_pairs": 0,
                "has_llm": self.has_llm,
                "language": self.language if self.language else "both",
                "level_ratio": self.level_ratio
            }

    def generate_and_save(self) -> Dict[str, Any]:
        """同步生成并保存问答对"""
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
    parser = argparse.ArgumentParser(description="问答对生成器 - 按比例生成不同层级的问答对（改进版）")
    parser.add_argument("--rules", type=str, default="../data/business_rule.json",
                       help="业务规则文件路径，默认为 ../data/business_rule.json")
    parser.add_argument("--output", type=str, default="../data/qa_pairs/qa_pairs.json",
                       help="输出文件路径，默认为 ../data/qa_pairs/qa_pairs.json")
    parser.add_argument("--num", type=int, default=40,
                       help="要生成的问答对数量，默认为40")
    parser.add_argument("--lang", type=str, choices=['zh', 'en'], default=None,
                       help="指定生成的语言，zh=中文, en=英文，默认中英文皆有")
    parser.add_argument("--level1", type=float, default=0.5,
                       help="Level1问答对比例，默认为0.5")
    parser.add_argument("--level2", type=float, default=0.4,
                       help="Level2问答对比例，默认为0.4")
    parser.add_argument("--level3", type=float, default=0.1,
                       help="Level3问答对比例，默认为0.1")
    parser.add_argument("--debug", action="store_true",
                       help="启用调试日志")

    args = parser.parse_args()

    # 设置调试日志
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # 验证比例总和为1
    total_ratio = args.level1 + args.level2 + args.level3
    if abs(total_ratio - 1.0) > 0.001:
        print(f"错误: 层级比例总和必须为1，当前总和为 {total_ratio}")
        return {
            "status": "error",
            "message": f"层级比例总和必须为1，当前总和为 {total_ratio}"
        }

    # 加载环境变量
    load_dotenv()

    # 检查API密钥
    api_key = os.getenv("ZHIPU_API_KEY")
    if api_key:
        print(f"使用智谱AI API生成增强问答对（改进版）")
    else:
        print(f"未配置智谱AI API，将生成基础问答对")
        print(f"提示: 创建.env文件并添加 ZHIPU_API_KEY=your_api_key")

    print(f"\n{'='*50}")
    print(f"配置信息:")
    print(f"{'='*50}")
    print(f"规则文件: {args.rules}")
    # print(f"输出目录: {args.output}")
    print(f"生成数量: {args.num}")
    print(f"生成语言: {args.lang if args.lang else '中英文'}")
    print(f"层级比例: Level1={args.level1*100}%, Level2={args.level2*100}%, Level3={args.level3*100}%")
    print(f"调试模式: {'开启' if args.debug else '关闭'}")
    print(f"{'='*50}\n")

    # 创建生成器并运行
    generator = EnhancedQAGenerator(
        rules_file=args.rules,
        output_file=args.output,
        num_pairs=args.num,
        language=args.lang,
        level_ratio={
            "level_1": args.level1,
            "level_2": args.level2,
            "level_3": args.level3
        }
    )

    result = generator.generate_and_save()

    return result


if __name__ == "__main__":
    main()
