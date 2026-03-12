"""记忆管理器

封装 Memory API 操作：
- 错题本管理
- 当日状态缓存
- 答题历史记录
"""

from openclaw.memory import Memory
from typing import List, Dict, Any, Optional
import json
from datetime import datetime


class MemoryManager:
    """记忆管理器"""

    # Memory key 常量
    KEY_WRONG_BOOK = "wrong_book"
    KEY_TODAY_QUESTIONS = "today_questions"
    KEY_HISTORY = "history"
    KEY_LAST_PUSH_DATE = "last_push_date"

    def __init__(self):
        pass

    # ==================== 错题本管理 ====================

    def get_wrong_book(self, user_id: str) -> List[Dict[str, Any]]:
        """获取错题本"""
        data = Memory.get(user_id, self.KEY_WRONG_BOOK)
        return json.loads(data) if data else []

    def add_to_wrong_book(self, user_id: str, wrong_details: List[Dict[str, Any]]):
        """添加错题到错题本"""
        wrong_book = self.get_wrong_book(user_id)

        for detail in wrong_details:
            wrong_book.append({
                "id": detail['question'].get('id'),
                "question": detail['question'],
                "user_answer": detail['user_answer'],
                "correct_answer": detail['correct_answer'],
                "category": detail['question'].get('category', '未知'),
                "timestamp": datetime.now().isoformat()
            })

        # 限制错题本大小，只保留最近 100 条
        if len(wrong_book) > 100:
            wrong_book = wrong_book[-100:]

        Memory.set(user_id, self.KEY_WRONG_BOOK, json.dumps(wrong_book))

    def clear_wrong_book(self, user_id: str):
        """清空错题本"""
        Memory.delete(user_id, self.KEY_WRONG_BOOK)

    # ==================== 当日状态缓存 ====================

    def cache_today_questions(self, user_id: str, questions: List[Dict[str, Any]]):
        """缓存今天的题目到 session"""
        Memory.set_session(user_id, self.KEY_TODAY_QUESTIONS, questions)

    def get_today_questions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取今天缓存的题目"""
        return Memory.get_session(user_id, self.KEY_TODAY_QUESTIONS) or []

    def clear_today_questions(self, user_id: str):
        """清理今天缓存的题目"""
        Memory.delete_session(user_id, self.KEY_TODAY_QUESTIONS)

    # ==================== 答题历史 ====================

    def get_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取答题历史"""
        data = Memory.get(user_id, self.KEY_HISTORY)
        history = json.loads(data) if data else []
        return history[-limit:]  # 只返回最近的

    def record_answer(self, user_id: str, questions: List[Dict[str, Any]],
                      user_answers: Dict[int, str], score: int):
        """记录一次答题历史"""
        history = self.get_history(user_id)

        record = {
            "date": datetime.now().isoformat(),
            "questions_count": len(questions),
            "score": score,
            "total": len(questions),
            "accuracy": score / len(questions) if questions else 0
        }

        history.append(record)

        # 只保留最近 100 条历史
        if len(history) > 100:
            history = history[-100:]

        Memory.set(user_id, self.KEY_HISTORY, json.dumps(history))

    # ==================== 推送状态 ====================

    def record_daily_sent(self, user_id: str):
        """记录今日推送时间"""
        Memory.set(user_id, self.KEY_LAST_PUSH_DATE, datetime.now().isoformat())

    def get_last_push_date(self, user_id: str) -> Optional[datetime]:
        """获取上次推送日期"""
        data = Memory.get(user_id, self.KEY_LAST_PUSH_DATE)
        if data:
            try:
                return datetime.fromisoformat(data)
            except:
                pass
        return None

    def is_today_pushed(self, user_id: str) -> bool:
        """判断今天是否已推送"""
        last_date = self.get_last_push_date(user_id)
        if not last_date:
            return False
        return last_date.date() == datetime.now().date()
