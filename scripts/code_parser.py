import ast
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any


class CodeParser:
    """解析代码库并提取结构化信息"""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.parsed_data = {
            "repo_name": self.repo_path.name,
            "files": [],
            "api_endpoints": [],
            "key_functions": [],
            "key_classes": [],
            "code_snippets": []
        }
        self.exclude_dirs = ['.git', '__pycache__', 'venv', '.idea', 'node_modules']
        self.key_function_names = ["get_db_session", "create_db_and_tables", "drop_all"]
        self.key_class_names = ["Restaurant", "Review", "MyUvicornWorker"]
        self.allowed_extensions = ['.py', '.html', '.htm', '.jinja', '.jinja2', '.txt', '.md', '.json', '.yaml', '.yml', '.xml', '.css', '.js']

    def parse_repository(self):
        """解析整个代码库"""
        print(f"开始解析代码库: {self.repo_path}")

        for file_path in self.repo_path.rglob('*'):
            # 排除不需要的目录
            if any(excluded in str(file_path) for excluded in self.exclude_dirs):
                continue

            if file_path.is_file():
                self.parse_file(file_path)

        # 提取关键函数和关键类
        self.extract_key_elements()

        print(f"解析完成，共处理 {len(self.parsed_data['files'])} 个文件")

    def parse_file(self, file_path: Path):
        """解析单个文件 - 只处理文本文件"""
        relative_path = file_path.relative_to(self.repo_path)

        # 检查文件扩展名，只处理允许的文件类型
        if file_path.suffix.lower() not in self.allowed_extensions:
            # print(f"跳过非文本文件: {relative_path}")
            return

        # 根据文件扩展名确定文件类型
        if file_path.suffix == '.py':
            file_info = self.parse_python_file(file_path, relative_path)
        elif file_path.suffix in ['.html', '.htm', '.jinja', '.jinja2']:
            file_info = self.parse_html_file(file_path, relative_path)
        elif file_path.suffix in ['.txt', '.md', '.json', '.yaml', '.yml', '.xml', '.css', '.js']:
            file_info = self.parse_text_file(file_path, relative_path)
        else:
            file_info = self.parse_generic_file(file_path, relative_path)

        if file_info:  # 只添加成功解析的文件
            self.parsed_data["files"].append(file_info)

    def parse_python_file(self, file_path: Path, relative_path: Path) -> Dict[str, Any]:
        """解析Python文件"""
        file_info = {
            "file_path": str(relative_path),
            "file_name": file_path.name,
            "file_type": "python",
            "lines": 0,
            "functions": [],
            "classes": [],
            "imports": [],
            "code_snippets": []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.splitlines()
            file_info["lines"] = len(lines)

            # 解析Python语法树
            tree = ast.parse(content)

            # 提取导入语句
            imports = self.extract_imports(tree)
            file_info["imports"] = imports

            # 重新处理代码，找到API端点装饰器位置
            self.find_api_endpoints_in_content(content, lines, str(relative_path))

            # 提取函数和类（修复装饰器问题）
            functions, api_endpoints_from_functions = self.extract_functions_with_decorators(tree, lines, str(relative_path))
            classes = self.extract_classes(tree, lines)

            file_info["functions"] = functions
            file_info["classes"] = classes

            # 提取代码片段
            code_snippets = self.extract_code_snippets(content)
            file_info["code_snippets"] = code_snippets

        except SyntaxError as e:
            print(f"警告: {file_path} 语法错误: {e}")
        except Exception as e:
            print(f"警告: 解析 {file_path} 时出错: {e}")

        return file_info

    def find_api_endpoints_in_content(self, content: str, lines: List[str], file_path: str):
        """在代码内容中查找API端点，直接扫描代码"""
        # 查找所有@app.get, @app.post等装饰器
        patterns = [
            r'@app\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\']',
            r'@.*?\.(get|post|put|delete|patch|head|options)\(["\']([^"\']+)["\']',
        ]

        for i, line in enumerate(lines):
            for pattern in patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                for match in matches:
                    if match and len(match) >= 2:
                        method = match[0].upper()
                        route = match[1]

                        # 尝试找到函数名
                        func_name = self.find_function_name_after_line(lines, i)

                        endpoint_info = {
                            "name": func_name or f"endpoint_{i}",
                            "method": method,
                            "route": route,
                            "file": file_path,
                            "function_name": func_name,
                            "is_async": self.is_line_async(lines, i)
                        }

                        # 避免重复添加
                        if not any(ep["route"] == route and ep["method"] == method and ep["file"] == file_path for ep in self.parsed_data["api_endpoints"]):
                            self.parsed_data["api_endpoints"].append(endpoint_info)

    def find_function_name_after_line(self, lines: List[str], decorator_line: int) -> str:
        """在装饰器行之后查找函数名"""
        # 从装饰器行开始向下查找函数定义
        for i in range(decorator_line + 1, min(decorator_line + 10, len(lines))):
            line = lines[i].strip()
            # 查找函数定义
            func_match = re.match(r'^(async\s+)?def\s+(\w+)', line)
            if func_match:
                return func_match.group(2)
        return ""

    def is_line_async(self, lines: List[str], decorator_line: int) -> bool:
        """检查装饰器后的函数是否是异步的"""
        for i in range(decorator_line + 1, min(decorator_line + 10, len(lines))):
            line = lines[i].strip()
            if line.startswith("async def"):
                return True
            elif line.startswith("def"):
                return False
        return False

    def extract_functions_with_decorators(self, tree: ast.AST, lines: List[str], file_path: str) -> tuple:
        """提取函数信息，包括异步函数，修复装饰器提取"""
        functions = []
        api_endpoints = []  # 这个现在主要从find_api_endpoints_in_content获取

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self.extract_function_info_with_fixed_decorators(node, lines)
                functions.append(func_info)

        return functions, api_endpoints

    def extract_function_info_with_fixed_decorators(self, node: ast.AST, lines: List[str]) -> Dict[str, Any]:
        """提取单个函数的详细信息，修复装饰器提取"""
        # 判断是否是异步函数
        is_async = isinstance(node, ast.AsyncFunctionDef)

        # 提取装饰器 - 直接从源代码中获取
        decorators = []

        # 获取函数定义之前的行，查找装饰器
        start_line = node.lineno - 2  # 从函数定义前一行开始
        while start_line >= 0 and lines[start_line].strip().startswith('@'):
            decorators.insert(0, lines[start_line].strip())
            start_line -= 1

        # 从AST中提取装饰器作为备选
        if not decorators and hasattr(node, 'decorator_list'):
            for decorator in node.decorator_list:
                try:
                    # 获取装饰器的源代码行
                    if hasattr(decorator, 'lineno'):
                        decorator_line = lines[decorator.lineno - 1].strip()
                        if decorator_line.startswith('@'):
                            decorators.append(decorator_line)
                except:
                    pass

        # 提取参数
        args = []
        if node.args.args:
            args = [arg.arg for arg in node.args.args]

        # 提取代码片段
        code_snippet_lines = lines[max(0, start_line+1):node.end_lineno]
        code_snippet = '\n'.join(code_snippet_lines)

        return {
            "name": node.name,
            "args": args,
            "decorators": decorators,
            "is_async": is_async,
            "line_start": node.lineno,
            "line_end": node.end_lineno,
            "code_snippet": code_snippet,
            "docstring": ast.get_docstring(node)
        }

    def extract_imports(self, tree: ast.AST) -> List[str]:
        """提取导入语句"""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"from {module} import {alias.name}")

        return list(set(imports))  # 去重

    def extract_classes(self, tree: ast.AST, lines: List[str]) -> List[Dict[str, Any]]:
        """提取类信息"""
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self.extract_class_info(node, lines)
                classes.append(class_info)

        return classes

    def extract_class_info(self, node: ast.ClassDef, lines: List[str]) -> Dict[str, Any]:
        """提取单个类的详细信息"""
        methods = []

        # 提取类的方法
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)

        # 提取基类
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                # 处理类似 xxx.yyy 的基类
                try:
                    # 尝试使用ast.unparse
                    bases.append(ast.unparse(base))
                except:
                    # 备选方案
                    bases.append(self.ast_to_str(base))

        # 提取代码片段
        code_snippet_lines = lines[node.lineno-1:node.end_lineno]
        code_snippet = '\n'.join(code_snippet_lines)

        return {
            "name": node.name,
            "bases": bases,
            "methods": methods,
            "line_start": node.lineno,
            "line_end": node.end_lineno,
            "code_snippet": code_snippet,
            "docstring": ast.get_docstring(node)
        }

    def ast_to_str(self, node: ast.AST) -> str:
        """将AST节点转换为字符串"""
        try:
            # Python 3.9+
            return ast.unparse(node)
        except AttributeError:
            # 备用实现
            if isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.Attribute):
                return f"{self.ast_to_str(node.value)}.{node.attr}"
            elif isinstance(node, ast.Call):
                func_str = self.ast_to_str(node.func)
                args_str = ', '.join([self.ast_to_str(arg) for arg in node.args])
                return f"{func_str}({args_str})"
            else:
                return str(node)

    def extract_code_snippets(self, content: str) -> List[Dict[str, Any]]:
        """从代码中提取关键代码片段"""
        snippets = []
        lines = content.splitlines()

        # 查找API端点定义
        for i, line in enumerate(lines):
            if '@app.get' in line.lower() or '@app.post' in line.lower():
                # 获取接下来的几行代码
                snippet_lines = []
                # 包括当前行
                snippet_lines.append(lines[i])

                # 添加后续行，直到遇到空行或另一个装饰器或函数定义
                for j in range(i+1, min(i+10, len(lines))):
                    next_line = lines[j]
                    if next_line.strip() == '' or next_line.strip().startswith('@') or next_line.strip().startswith('def ') or next_line.strip().startswith('async def '):
                        break
                    snippet_lines.append(next_line)

                snippet = "\n".join(snippet_lines)
                snippets.append({
                    "line": i + 1,  # 行号从1开始
                    "description": "API端点定义",
                    "code": snippet
                })

        return snippets

    def parse_html_file(self, file_path: Path, relative_path: Path) -> Dict[str, Any]:
        """解析HTML/模板文件"""
        file_info = {
            "file_path": str(relative_path),
            "file_name": file_path.name,
            "file_type": "html",
            "lines": 0,
            "template_variables": [],
            "template_tags": [],
            "text_preview": ""
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.splitlines()
            file_info["lines"] = len(lines)

            # 提取模板变量 {{ variable }}
            template_variables = re.findall(r'\{\{[^}]*\}\}', content)
            file_info["template_variables"] = list(set(template_variables))  # 去重

            # 提取模板标签 {% tag %}
            template_tags = re.findall(r'\{%[^%]*%\}', content)
            file_info["template_tags"] = list(set(template_tags))  # 去重

            # 生成文本预览（移除HTML标签和模板语法）
            text_content = re.sub(r'<[^>]*>', '', content)
            text_content = re.sub(r'\{\{[^}]*\}\}', '', text_content)
            text_content = re.sub(r'\{%[^%]*%\}', '', text_content)
            text_content = ' '.join(text_content.split())[:200]  # 取前200个字符
            file_info["text_preview"] = text_content

        except Exception as e:
            print(f"警告: 解析 {file_path} 时出错: {e}")

        return file_info

    def parse_text_file(self, file_path: Path, relative_path: Path) -> Dict[str, Any]:
        """解析通用文本文件"""
        file_info = {
            "file_path": str(relative_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix[1:] if file_path.suffix else 'text',
            "lines": 0
        }

        try:
            # 尝试用utf-8编码读取
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                file_info["lines"] = len(content.splitlines())
        except UnicodeDecodeError:
            try:
                # 尝试用gbk编码读取（常见中文编码）
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
                    file_info["lines"] = len(content.splitlines())
            except Exception as e:
                print(f"警告: 无法读取文件 {file_path}: {e}")
                return None  # 返回None表示解析失败
        except Exception as e:
            print(f"警告: 读取 {file_path} 时出错: {e}")
            return None

        return file_info

    def parse_generic_file(self, file_path: Path, relative_path: Path) -> Dict[str, Any]:
        """解析其他类型的文件（基本不解析内容）"""
        file_info = {
            "file_path": str(relative_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix[1:] if file_path.suffix else 'unknown',
            "lines": 0
        }

        try:
            # 只获取文件大小，不读取内容
            file_size = file_path.stat().st_size
            file_info["size"] = file_size
            print(f"跳过二进制/非文本文件: {relative_path} ({file_size} bytes)")
        except Exception as e:
            print(f"警告: 获取文件信息 {file_path} 时出错: {e}")

        return file_info

    def extract_key_elements(self):
        """提取关键函数和关键类"""
        for file_info in self.parsed_data["files"]:
            # 提取关键函数
            for func in file_info.get("functions", []):
                if func["name"] in self.key_function_names:
                    self.parsed_data["key_functions"].append({
                        "name": func["name"],
                        "file": file_info["file_path"],
                        "code_snippet": func["code_snippet"]
                    })

            # 提取关键类
            for cls in file_info.get("classes", []):
                if cls["name"] in self.key_class_names:
                    self.parsed_data["key_classes"].append({
                        "name": cls["name"],
                        "file": file_info["file_path"],
                        "code_snippet": cls["code_snippet"]
                    })

    def save_to_json(self, output_path: str):
        """将解析结果保存为JSON文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.parsed_data, f, indent=2, ensure_ascii=False)

        print(f"解析结果已保存到: {output_path}")

    def print_statistics(self):
        """打印解析统计信息"""
        total_files = len(self.parsed_data["files"])
        api_endpoints = len(self.parsed_data["api_endpoints"])
        key_functions = len(self.parsed_data["key_functions"])
        key_classes = len(self.parsed_data["key_classes"])

        print("\n解析统计:")
        print(f"  总文件数: {total_files}")
        print(f"  API端点: {api_endpoints}")
        print(f"  关键函数: {key_functions}")
        print(f"  关键类: {key_classes}")

        # 显示发现的API端点
        if api_endpoints > 0:
            print("\nAPI端点列表:")
            for endpoint in self.parsed_data["api_endpoints"]:
                print(f"  {endpoint['method']} {endpoint['route']} - {endpoint['name']} ({endpoint['file']})")


def main():
    """主函数"""
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="解析代码仓")
    parser.add_argument("--repo", type=str, default="../test_repo",
                       help="代码仓位置，默认为 ../test_repo")
    parser.add_argument("--output", type=str, default="../data/parsed_code.json",
                       help="输出文件路径，默认为 ../data/parsed_code.json")

    args = parser.parse_args()

    # 创建解析器
    parser = CodeParser(args.repo)

    # 解析代码库
    parser.parse_repository()

    # 打印统计信息
    parser.print_statistics()

    # 保存结果到 ../data/parsed_code.json

    output_file = args.output

    # 确保输出目录存在

    os.makedirs(Path(output_file).parent, exist_ok=True)

    parser.save_to_json(output_file)

    # 显示关键函数和类
    if parser.parsed_data["key_functions"]:
        print("\n关键函数:")
        for func in parser.parsed_data["key_functions"]:
            print(f"  {func['name']} ({func['file']})")

    if parser.parsed_data["key_classes"]:
        print("\n关键类:")
        for cls in parser.parsed_data["key_classes"]:
            print(f"  {cls['name']} ({cls['file']})")


if __name__ == "__main__":
    main()
