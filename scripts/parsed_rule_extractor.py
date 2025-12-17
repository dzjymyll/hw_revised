"""
从已解析的代码结构中提取业务规则的模块
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import datetime


class ParsedCodeRuleExtractor:
    """从已解析的代码结构中提取业务规则"""

    def __init__(self, parsed_file: str = "parsed_code.json",
                 output_file: str = "../data/business_rule.json"):
        """
        初始化规则提取器

        Args:
            parsed_file: 已解析的代码结构文件路径
            output_file: 输出规则文件的路径
        """
        self.parsed_file = Path(parsed_file)
        self.output_file = Path(output_file)
        self.logger = logging.getLogger(__name__)

        # 确保输出目录存在
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        # 问题类型映射
        self.question_type_mapping = {
            "endpoint": ["route_basic", "api_endpoints", "endpoint_processing"],
            "function": ["function_purpose", "function_location", "database_connection",
                        "async_processing", "function_behavior", "dependency_injection"],
            "model": ["model_relationship", "data_structure", "database_schema", "model_fields"],
            "class": ["class_structure", "inheritance", "class_methods"],
            "template": ["template_rendering", "ui_components", "template_variables"],
            "import": ["dependencies", "external_libraries", "framework_imports"],
            "config": ["project_setup", "configuration", "deployment"],
            "file_structure": ["project_structure", "file_organization"]
        }

        # 加载已解析的数据
        self.parsed_data = None
        if self.parsed_file.exists():
            self.load_parsed_data()
        else:
            self.logger.error(f"解析文件不存在: {self.parsed_file}")

    def load_parsed_data(self) -> None:
        """加载已解析的代码数据"""
        try:
            with open(self.parsed_file, 'r', encoding='utf-8') as f:
                self.parsed_data = json.load(f)
            self.logger.info(f"已加载解析数据，包含 {len(self.parsed_data.get('files', []))} 个文件")
        except Exception as e:
            self.logger.error(f"加载解析数据时出错: {e}")
            raise

    def extract_endpoint_rules(self) -> List[Dict[str, Any]]:
        """从API端点提取规则"""
        rules = []

        if not self.parsed_data:
            return rules

        # 从全局api_endpoints提取
        for endpoint in self.parsed_data.get("api_endpoints", []):
            rule = {
                "type": "endpoint",
                "name": endpoint.get("name", ""),
                "match": f"{endpoint.get('method', '')} {endpoint.get('route', '')}",
                "file": endpoint.get("file", ""),
                "function_name": endpoint.get("function_name", ""),
                "is_async": endpoint.get("is_async", False),
                "question_types": self.question_type_mapping.get("endpoint", []),
                "metadata": {
                    "http_method": endpoint.get("method", ""),
                    "route_path": endpoint.get("route", "")
                }
            }

            # 从文件中找到对应的函数代码片段
            for file_info in self.parsed_data.get("files", []):
                if file_info.get("file_path") == endpoint.get("file"):
                    for func in file_info.get("functions", []):
                        if func.get("name") == endpoint.get("function_name"):
                            rule["code_snippet"] = func.get("code_snippet", "")
                            rule["metadata"]["line_start"] = func.get("line_start")
                            rule["metadata"]["line_end"] = func.get("line_end")
                            rule["metadata"]["decorators"] = func.get("decorators", [])
                            break
                    break

            rules.append(rule)

        return rules

    def extract_function_rules(self) -> List[Dict[str, Any]]:
        """从函数定义中提取规则"""
        rules = []

        if not self.parsed_data:
            return rules

        # 从全局key_functions提取
        for func in self.parsed_data.get("key_functions", []):
            rule = {
                "type": "function",
                "name": func.get("name", ""),
                "match": func.get("name", ""),
                "file": func.get("file", ""),
                "code_snippet": func.get("code_snippet", ""),
                "question_types": self.question_type_mapping.get("function", []),
                "metadata": {
                    "is_key_function": True
                }
            }

            # 从文件中找到更详细的信息
            for file_info in self.parsed_data.get("files", []):
                if file_info.get("file_path") == func.get("file"):
                    for file_func in file_info.get("functions", []):
                        if file_func.get("name") == func.get("name"):
                            rule["metadata"]["is_async"] = file_func.get("is_async", False)
                            rule["metadata"]["args"] = file_func.get("args", [])
                            rule["metadata"]["decorators"] = file_func.get("decorators", [])
                            rule["metadata"]["line_start"] = file_func.get("line_start")
                            rule["metadata"]["line_end"] = file_func.get("line_end")
                            break
                    break

            rules.append(rule)

        # 从所有文件的functions中提取
        for file_info in self.parsed_data.get("files", []):
            if file_info.get("file_type") == "python":
                for func in file_info.get("functions", []):
                    # 跳过已经在key_functions中的函数
                    func_name = func.get("name", "")
                    if any(r.get("name") == func_name for r in rules):
                        continue

                    rule = {
                        "type": "function",
                        "name": func_name,
                        "match": func_name,
                        "file": file_info.get("file_path", ""),
                        "code_snippet": func.get("code_snippet", ""),
                        "question_types": self.question_type_mapping.get("function", []),
                        "metadata": {
                            "is_async": func.get("is_async", False),
                            "args": func.get("args", []),
                            "decorators": func.get("decorators", []),
                            "line_start": func.get("line_start"),
                            "line_end": func.get("line_end"),
                            "is_key_function": False
                        }
                    }

                    rules.append(rule)

        return rules

    def extract_model_rules(self) -> List[Dict[str, Any]]:
        """从数据模型中提取规则"""
        rules = []

        if not self.parsed_data:
            return rules

        # 从全局key_classes中提取模型（Restaurant, Review）
        for cls in self.parsed_data.get("key_classes", []):
            cls_name = cls.get("name", "")
            if cls_name in ["Restaurant", "Review"]:
                rule = {
                    "type": "model",
                    "name": cls_name,
                    "match": cls_name,
                    "file": cls.get("file", ""),
                    "code_snippet": cls.get("code_snippet", ""),
                    "question_types": self.question_type_mapping.get("model", []),
                    "metadata": {
                        "is_data_model": True,
                        "model_type": cls_name
                    }
                }

                # 从文件中找到更详细的信息
                for file_info in self.parsed_data.get("files", []):
                    if file_info.get("file_path") == cls.get("file"):
                        for file_cls in file_info.get("classes", []):
                            if file_cls.get("name") == cls_name:
                                rule["metadata"]["bases"] = file_cls.get("bases", [])
                                rule["metadata"]["methods"] = file_cls.get("methods", [])
                                rule["metadata"]["line_start"] = file_cls.get("line_start")
                                rule["metadata"]["line_end"] = file_cls.get("line_end")

                                # 提取字段信息
                                code_snippet = file_cls.get("code_snippet", "")
                                field_patterns = [
                                    r'id:\s*[^=]*=\s*Field\([^)]*primary_key=True[^)]*\)',
                                    r'name:\s*\w+\s*=\s*Field\([^)]*\)',
                                    r'street_address:\s*\w+\s*=\s*Field\([^)]*\)',
                                    r'description:\s*\w+\s*=\s*Field\([^)]*\)',
                                    r'restaurant:\s*\w+\s*=\s*Field\([^)]*\)',
                                    r'user_name:\s*\w+\s*=\s*Field\([^)]*\)',
                                    r'rating:\s*[^=]*',
                                    r'review_text:\s*\w+\s*=\s*Field\([^)]*\)',
                                    r'review_date:\s*\w+'
                                ]

                                fields = []
                                import re
                                for pattern in field_patterns:
                                    matches = re.findall(pattern, code_snippet)
                                    fields.extend(matches)

                                rule["metadata"]["fields"] = fields
                                break
                        break

                rules.append(rule)

        return rules

    def extract_class_rules(self) -> List[Dict[str, Any]]:
        """从类定义中提取规则"""
        rules = []

        if not self.parsed_data:
            return rules

        for file_info in self.parsed_data.get("files", []):
            if file_info.get("file_type") == "python":
                for cls in file_info.get("classes", []):
                    cls_name = cls.get("name", "")

                    # 跳过已经是模型的类
                    if cls_name in ["Restaurant", "Review"]:
                        continue

                    rule = {
                        "type": "class",
                        "name": cls_name,
                        "match": cls_name,
                        "file": file_info.get("file_path", ""),
                        "code_snippet": cls.get("code_snippet", ""),
                        "question_types": self.question_type_mapping.get("class", []),
                        "metadata": {
                            "bases": cls.get("bases", []),
                            "methods": cls.get("methods", []),
                            "line_start": cls.get("line_start"),
                            "line_end": cls.get("line_end"),
                            "docstring": cls.get("docstring")
                        }
                    }

                    rules.append(rule)

        return rules

    def extract_template_rules(self) -> List[Dict[str, Any]]:
        """从模板文件中提取规则"""
        rules = []

        if not self.parsed_data:
            return rules

        for file_info in self.parsed_data.get("files", []):
            if file_info.get("file_type") == "html":
                rule = {
                    "type": "template",
                    "name": file_info.get("file_name", ""),
                    "match": file_info.get("file_name", ""),
                    "file": file_info.get("file_path", ""),
                    "question_types": self.question_type_mapping.get("template", []),
                    "metadata": {
                        "lines": file_info.get("lines", 0),
                        "template_variables": file_info.get("template_variables", []),
                        "template_tags": file_info.get("template_tags", []),
                        "text_preview": file_info.get("text_preview", "")
                    }
                }

                rules.append(rule)

        return rules

    def extract_import_rules(self) -> List[Dict[str, Any]]:
        """从导入语句中提取规则"""
        rules = []

        if not self.parsed_data:
            return rules

        for file_info in self.parsed_data.get("files", []):
            if file_info.get("file_type") == "python":
                imports = file_info.get("imports", [])
                if imports:
                    rule = {
                        "type": "import",
                        "match": f"{len(imports)} imports in {file_info.get('file_name')}",
                        "file": file_info.get("file_path", ""),
                        "question_types": self.question_type_mapping.get("import", []),
                        "metadata": {
                            "imports": imports,
                            "total_imports": len(imports)
                        }
                    }

                    rules.append(rule)

        return rules

    def extract_file_structure_rules(self) -> List[Dict[str, Any]]:
        """从文件结构中提取规则"""
        rules = []

        if not self.parsed_data:
            return rules

        # 按文件类型统计
        file_types = {}
        python_files = []

        for file_info in self.parsed_data.get("files", []):
            file_type = file_info.get("file_type", "unknown")
            file_types[file_type] = file_types.get(file_type, 0) + 1

            if file_type == "python":
                python_files.append(file_info.get("file_path", ""))

        # 项目结构规则
        rule = {
            "type": "file_structure",
            "name": "project_structure",
            "match": f"Project: {self.parsed_data.get('repo_name', 'Unknown')}",
            "file": "all",
            "question_types": self.question_type_mapping.get("file_structure", []),
            "metadata": {
                "repo_name": self.parsed_data.get("repo_name", ""),
                "total_files": len(self.parsed_data.get("files", [])),
                "file_types": file_types,
                "python_files": python_files,
                "total_python_files": len(python_files)
            }
        }

        rules.append(rule)

        # 关键文件规则
        for file_info in self.parsed_data.get("files", []):
            file_name = file_info.get("file_name", "")
            if file_name in ["app.py", "models.py", "__init__.py", "requirements.txt"]:
                rule = {
                    "type": "config",
                    "name": f"config_{file_name}",
                    "match": file_name,
                    "file": file_info.get("file_path", ""),
                    "question_types": self.question_type_mapping.get("config", []),
                    "metadata": {
                        "lines": file_info.get("lines", 0),
                        "file_type": file_info.get("file_type", ""),
                        "is_key_file": True
                    }
                }

                # 对于Python文件，添加更多信息
                if file_info.get("file_type") == "python":
                    rule["metadata"]["functions"] = file_info.get("functions", [])
                    rule["metadata"]["classes"] = file_info.get("classes", [])
                    rule["metadata"]["imports"] = file_info.get("imports", [])

                rules.append(rule)

        return rules

    def analyze_rules(self, all_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析规则，生成统计信息"""
        type_stats = {}
        file_stats = {}

        for rule in all_rules:
            # 按规则类型统计
            rule_type = rule.get("type", "unknown")
            type_stats[rule_type] = type_stats.get(rule_type, 0) + 1

            # 按文件统计
            file_name = rule.get("file", "unknown")
            if file_name not in file_stats:
                file_stats[file_name] = 0
            file_stats[file_name] += 1

        return {
            "total_rules": len(all_rules),
            "rules_by_type": type_stats,
            "rules_by_file": file_stats,
            "most_common_type": max(type_stats, key=type_stats.get) if type_stats else None,
            "most_common_file": max(file_stats, key=file_stats.get) if file_stats else None
        }

    def extract_all_rules(self) -> List[Dict[str, Any]]:
        """提取所有类型的规则"""
        all_rules = []

        if not self.parsed_data:
            self.logger.error("没有解析数据可用")
            return all_rules

        # 提取各种类型的规则
        extractors = [
            ("端点规则", self.extract_endpoint_rules),
            ("函数规则", self.extract_function_rules),
            ("模型规则", self.extract_model_rules),
            ("类规则", self.extract_class_rules),
            ("模板规则", self.extract_template_rules),
            ("导入规则", self.extract_import_rules),
            ("文件结构规则", self.extract_file_structure_rules)
        ]

        for name, extractor in extractors:
            try:
                rules = extractor()
                all_rules.extend(rules)
                self.logger.info(f"提取了 {len(rules)} 条{name}")
            except Exception as e:
                self.logger.error(f"提取{name}时出错: {e}")

        return all_rules

    def save_rules(self, rules: List[Dict[str, Any]]) -> None:
        """保存提取的规则到文件"""
        try:
            # 分析规则
            analysis = self.analyze_rules(rules)

            # 准备要保存的数据
            output_data = {
                "project": self.parsed_data.get("repo_name", "unknown") if self.parsed_data else "unknown",
                "source_parsed_file": str(self.parsed_file),
                "total_rules": len(rules),
                "extraction_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "analysis": analysis,
                "question_type_mapping": self.question_type_mapping,
                "rules": rules
            }

            # 保存到文件
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"已保存 {len(rules)} 条规则到 {self.output_file}")

            # 打印统计信息
            print(f"\n=== 规则提取统计 ===")
            print(f"总规则数: {len(rules)}")
            print(f"项目名称: {output_data['project']}")
            print(f"规则类型分布:")
            for rule_type, count in analysis.get("rules_by_type", {}).items():
                print(f"  - {rule_type}: {count}")

            print(f"\n最常用的规则类型: {analysis.get('most_common_type')}")
            print(f"输出文件: {self.output_file}")

        except Exception as e:
            self.logger.error(f"保存规则时出错: {e}")
            raise

    def extract_and_save(self) -> Dict[str, Any]:
        """提取并保存规则的主方法"""
        self.logger.info(f"开始从 {self.parsed_file} 提取规则...")
        self.logger.info(f"输出文件: {self.output_file}")

        if not self.parsed_data:
            self.logger.error("解析数据未加载")
            return {
                "status": "error",
                "message": "解析数据未加载"
            }

        rules = self.extract_all_rules()

        if rules:
            self.save_rules(rules)
            return {
                "status": "success",
                "total_rules": len(rules),
                "output_file": str(self.output_file),
                "analysis": self.analyze_rules(rules)
            }
        else:
            self.logger.warning("未提取到任何规则")
            return {
                "status": "no_rules_found",
                "total_rules": 0,
                "output_file": str(self.output_file)
            }


def main():
    """主函数"""
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="获取规则")
    parser.add_argument("--input", type=str, default="../data/parsed_code.json",
                       help="代码仓位置，默认为 ../data/parsed_code.json")
    parser.add_argument("--output", type=str, default="../data/business_rule.json",
                       help="输出文件路径，默认为 ../data/business_rule.json")

    args = parser.parse_args()
    # 获取命令行参数或使用默认值
    parsed_file = args.input
    output_file = args.output

    # 显示配置信息
    print(f"解析文件: {parsed_file}")
    print(f"输出文件: {output_file}")

    extractor = ParsedCodeRuleExtractor(parsed_file=parsed_file, output_file=output_file)
    result = extractor.extract_and_save()

    return result


if __name__ == "__main__":
    main()
