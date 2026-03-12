"""题目解析工具

负责：
- 加载题库文件
- 解析用户交卷答案
- 题目抽取逻辑
"""

import json
import os
import re
from typing import List, Dict, Any, Optional


class QuestionParser:
    """题目解析器"""

    def __init__(self, base_path: str = "data/ocr_question_bank"):
        self.base_path = base_path

    def load_all_questions(self) -> List[Dict[str, Any]]:
        """
        加载所有题库文件

        Returns:
            所有题目的列表
        """
        questions = []

        if not os.path.exists(self.base_path):
            return questions

        for filename in os.listdir(self.base_path):
            if filename.endswith('.json'):
                filepath = os.path.join(self.base_path, filename)
                file_questions = self._load_json_file(filepath)
                questions.extend(file_questions)

        return questions

    def _load_json_file(self, filepath: str) -> List[Dict[str, Any]]:
        """
        加载单个 JSON 题库文件

        Args:
            filepath: 文件路径

        Returns:
            题目列表
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 支持三种格式：直接列表 / 包含 questions / 按题型归类
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and 'questions' in data:
                return data['questions']
            if isinstance(data, dict):
                categories = None
                if isinstance(data.get('categories'), dict):
                    categories = data['categories']
                elif all(isinstance(v, list) for v in data.values()):
                    categories = data
                if categories:
                    flat = []
                    for category, items in categories.items():
                        if not isinstance(items, list):
                            continue
                        for q in items:
                            if not isinstance(q, dict):
                                continue
                            row = dict(q)
                            row.setdefault('category', category)
                            flat.append(row)
                    return flat
            return []
        except Exception as e:
            print(f"加载题库文件失败 {filepath}: {e}")
            return []

    def parse_answers(self, answer_str: str) -> Dict[int, str]:
        """
        解析用户交卷的答案

        支持格式：
        - "1A 2B 3C 4D 5A"
        - "1A\n2B\n3C"
        - "1A 2B\n3C 4D 5A"

        Args:
            answer_str: 用户回复的字符串

        Returns:
            {题号：答案} 的字典，如 {1: 'A', 2: 'B', ...}
        """
        answers = {}

        # 标准化：去掉多余空格，转大写
        answer_str = answer_str.strip().upper()

        # 匹配所有题号和答案
        # 匹配模式：数字 + A/B/C/D
        pattern = r'(\d+)[A-D]'
        matches = re.findall(pattern, answer_str)

        # 提取题号和对应答案
        answer_pattern = r'(\d+)([A-D])'
        answer_matches = re.findall(answer_pattern, answer_str)

        for num, ans in answer_matches:
            try:
                question_num = int(num)
                answers[question_num] = ans
            except ValueError:
                continue

        return answers

    def get_question_by_id(self, question_id: str, questions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取题目

        Args:
            question_id: 题目 ID
            questions: 题目列表

        Returns:
            题目详情 or None
        """
        for q in questions:
            if q.get('id') == question_id:
                return q
        return None

    def filter_questions_by_category(self, questions: List[Dict[str, Any]], category: str) -> List[Dict[str, Any]]:
        """
        按题型筛选题目

        Args:
            questions: 题目列表
            category: 题型分类

        Returns:
            筛选后的题目列表
        """
        return [q for q in questions if q.get('category') == category]
