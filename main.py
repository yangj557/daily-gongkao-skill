"""每日公考刷题技能主入口

这个技能提供：
- 每日定时推送行测题目
- 智能批改与个性化反馈
- 错题本管理
"""

from openclaw.skill import Skill
from openclaw.memory import Memory
from openclaw.llm import LLM
from openclaw.cron import Cron

from prompt_templates import build_feedback_prompt
from memory_manager import MemoryManager
from utils.question_parser import QuestionParser


class GongKaoDailySkill(Skill):
    """每日公考刷题技能"""

    def __init__(self):
        super().__init__()
        self.parser = QuestionParser()
        self.memory = MemoryManager()
        self.daily_count = int(self.get_setting('daily_question_count', 5))
        self.push_time = self.get_setting('daily_push_time', '08:00')

    def start(self):
        """技能启动时注册定时任务"""
        # 注册每日定时推送任务
        Cron.schedule(self.push_time, self._send_daily_questions)
        self.log(f"公考刷题技能已启动，每日 {self.push_time} 推送题目")

    def _send_daily_questions(self, user_id: str):
        """发送每日题目"""
        # 获取用户 ID
        user_id = user_id or self.get_current_user_id()

        # 抽取今天的题目（避开做过的和做错的）
        questions = self._get_daily_questions(user_id, count=self.daily_count)

        if not questions:
            message = "📚 今天的题库已经刷完啦！休息一天，明天继续卷！"
            self.send_message(user_id, message)
            return

        # 组装题目消息
        msg_text = self._build_questions_text(questions)

        # 缓存今天的题目和答案到 session
        self.memory.cache_today_questions(user_id, questions)

        # 发送题目
        self.send_message(user_id, msg_text)

        # 记录发送时间
        self.memory.record_daily_sent(user_id)

    def _get_daily_questions(self, user_id: str, count: int = 5):
        """获取每日题目，避开错题和已做题"""
        # 获取错题本
        wrong_book = self.memory.get_wrong_book(user_id)
        wrong_ids = {item['id'] for item in wrong_book} if wrong_book else set()

        # 获取今天已做题
        history = self.memory.get_history(user_id)
        history_ids = {item['id'] for item in history} if history else set()

        # 加载题库
        questions = self.parser.load_all_questions()

        # 过滤：排除错题和已做过的题
        available = [
            q for q in questions
            if q['id'] not in wrong_ids and q['id'] not in history_ids
        ]

        # 如果可用的题不够，就包括错题
        if len(available) < count:
            available = [
                q for q in questions
                if q['id'] not in history_ids
            ]

        # 随机抽取
        import random
        return random.sample(available, min(count, len(available)))

    def _build_questions_text(self, questions: list) -> str:
        """组装题目文本"""
        lines = [
            "🌅 早上好，考公狗！",
            "今天又是卷死对手的一天！",
            f"这是今天的 {len(questions)} 道行测真题，",
            "直接回复『1A 2B 3C...』交卷：\n",
            "=" * 40
        ]

        for idx, q in enumerate(questions):
            lines.append(f"\n{idx+1}. {q['title']}")
            for opt in q['options']:
                lines.append(f"   {opt['key']}. {opt['value']}")

        lines.append("\n" + "=" * 40)
        lines.append("\n💡 提示：直接回复『1A 2B 3C...』交卷")

        return "\n".join(lines)

    def handle_user_message(self, message: str, user_id: str = None):
        """处理用户消息"""
        user_id = user_id or self.get_current_user_id()

        # 检查是否是交卷格式
        if self._is_answers_format(message):
            return self._grade_answers(user_id, message)

        # 检查是否是领题指令
        if '领题' in message or '题目' in message:
            self._send_daily_questions(user_id)
            return

        # 检查是否是错题本指令
        if '错题' in message or '错题本' in message:
            return self._show_wrong_book(user_id)

        return "🤔 我不太懂你的意思~ 回复『领题』开始刷题，回复『错题本』查看错题"

    def _is_answers_format(self, message: str) -> bool:
        """检查消息是否符合交卷格式"""
        import re
        # 匹配格式：1A 2B 3C 4D 5A
        pattern = r'^(\d+[A-D]\s*)+$'
        return bool(re.match(pattern, message.strip()))

    def _grade_answers(self, user_id: str, user_answers: str):
        """批改答案"""
        # 获取今天缓存的题目
        today_questions = self.memory.get_today_questions(user_id)
        if not today_questions:
            return "你今天还没领题哦，回复『领题』开始刷题！"

        # 解析用户答案
        user_answers_parsed = self.parser.parse_answers(user_answers)

        # 计算得分
        score, wrong_details = self._calculate_score(user_answers_parsed, today_questions)

        # 记录答题历史
        self.memory.record_answer(user_id, today_questions, user_answers_parsed, score)

        # 记录错题到错题本
        self.memory.add_to_wrong_book(user_id, wrong_details)

        # 生成 AI 反馈
        ai_feedback = self._generate_feedback(score, wrong_details, today_questions, user_id)

        # 清理 session
        self.memory.clear_today_questions(user_id)

        return ai_feedback

    def _calculate_score(self, user_answers: dict, questions: list):
        """计算得分"""
        correct_count = 0
        wrong_details = []

        for idx, q in enumerate(questions):
            q_num = idx + 1
            user_answer = user_answers.get(q_num)
            correct_answer = q['answer']

            if user_answer == correct_answer:
                correct_count += 1
            else:
                wrong_details.append({
                    'question': q,
                    'user_answer': user_answer,
                    'correct_answer': correct_answer
                })

        score = correct_count
        return score, wrong_details

    def _generate_feedback(self, score: int, wrong_details: list, questions: list, user_id: str):
        """生成 AI 反馈"""
        # 获取长期记忆
        wrong_book = self.memory.get_wrong_book(user_id)

        # 构建 Prompt
        prompt = build_feedback_prompt(score, wrong_details, questions, wrong_book)

        # 调用 LLM
        model = self.get_setting('llm_model', 'auto')
        feedback = LLM.generate(
            model=model,
            system_prompt="你是一位顶尖的公考培训名师，专业、犀利、会用网络热梗",
            user_prompt=prompt
        )

        return feedback

    def _show_wrong_book(self, user_id: str):
        """显示错题本"""
        wrong_book = self.memory.get_wrong_book(user_id)

        if not wrong_book:
            return "📖 你的错题本还是空的，快去刷题吧！"

        lines = ["📖 你的错题本：", "=" * 40]

        for item in wrong_book[-10:]:  # 只显示最近 10 条
            lines.append(f"\n【{item['question']['title'][:20]}...】")
            lines.append(f"  你选了：{item['user_answer']} | 正确答案：{item['correct_answer']}")

        lines.append(f"\n共 {len(wrong_book)} 道错题")

        return "\n".join(lines)
