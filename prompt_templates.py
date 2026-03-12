"""大模型 Prompt 模板

包含：
1. System Prompt - 定义公考名师的人设
2. 反馈 Prompt 构建器 - 组装用户答题数据
"""

SYSTEM_PROMPT = """
你是一位顶尖的公考培训名师，你的特点是：

【人设】
- 专业：对行测各科目的解题方法了如指掌
- 犀利：说话一针见血，不绕弯子
- 幽默：会用网络热梗，让枯燥的刷题变得有趣
- 恨铁不成钢：对学生既严厉又关心

【回答原则】
1. 先看分数，用一句话点评（满分猛夸，低分阴阳怪气地鞭策）
2. 针对错题，直接指出思维误区，不要给标准解析（用户要看的是你的点评，不是百度能查到的解析）
3. 结合历史错题，给出针对性建议
4. 结尾要鼓励，但不要鸡汤

【语气参考】
- "就这？5 道错 4 道，你是来公考界当混子的吧？"
- "不错不错，终于不是零分了，虽然离上岸还差十万八千里"
- "言语理解错成这样，你平时是语文课都在睡觉吗？"
- "逻辑判断全对？转性了？不过别飘，下次继续测你"

【格式要求】
- 多用 emoji，增加可读性
- 重点词汇可以用 ** 标粗（如果平台支持）
- 分段清晰，每段不要超过 3 行
"""


def build_feedback_prompt(score: int, wrong_details: list, questions: list, wrong_book: list = None) -> str:
    """
    构建给 LLM 的反馈 Prompt

    Args:
        score: 本次得分（每题 1 分）
        wrong_details: 错题详情列表
        questions: 今天的题目列表
        wrong_book: 长期错题本

    Returns:
        完整的 user_prompt 字符串
    """
    total = len(questions)
    percentage = (score / total * 100) if total > 0 else 0

    # 构建本次答题情况
    prompt_lines = [
        f"📊 本次答题情况：{score}/{total} ({percentage:.0f}分)",
        ""
    ]

    # 错题详情
    if wrong_details:
        prompt_lines.append("❌ 错题详情：")
        for i, detail in enumerate(wrong_details, 1):
            q = detail['question']
            prompt_lines.append(f"
{i} {q['title']}")
            prompt_lines.append(f"   你的选择：{detail['user_answer'] or '未答'}")
            prompt_lines.append(f"   正确答案：{detail['correct_answer']}")
            # 如果题目有解析，加上解析
            if q.get('explanation'):
                # 让 LLM 参考解析来点评，而不是直接给解析
                prompt_lines.append(f"   题目解析：{q['explanation'][:100]}...")
            prompt_lines.append("")
    else:
        prompt_lines.append("🎉 全对！太强了！")

    # 历史错题分析
    if wrong_book and len(wrong_book) > 0:
        # 统计各题型错误次数
        category_stats = {}
        for item in wrong_book:
            cat = item.get('question', {}).get('category', '未知')
            category_stats[cat] = category_stats.get(cat, 0) + 1

        prompt_lines.append("")
        prompt_lines.append("📚 历史错题统计（最近 20 条）：")
        for cat, count in sorted(category_stats.items(), key=lambda x: -x[1])[:5]:
            prompt_lines.append(f"   {cat}: {count}次")

        # 找出最弱的题型
        weakest = max(category_stats.items(), key=lambda x: x[1]) if category_stats else None
        if weakest and weakest[1] >= 3:
            prompt_lines.append(f"")
            prompt_lines.append(f"⚠️ 警告：{weakened[0]} 是你的薄弱项，错了 {weakened[1]} 次！")

    # 要求 LLM 回复的结构
    prompt_lines.append("")
    prompt_lines.append("=" * 40)
    prompt_lines.append("")
    prompt_lines.append("请按以下结构回复：")
    prompt_lines.append("1. 一句话点评（根据分数，犀利或鼓励）")
    prompt_lines.append("2. 错题思维误区分析（每道题一针见血指出问题）")
    prompt_lines.append("3. 明天/下次刷题的针对性建议")

    return "\n".join(prompt_lines)


def build_explanation_prompt(question: dict, user_answer: str, correct_answer: str) -> str:
    """
    构建单题解析 Prompt（用于用户追问某题）

    Args:
        question: 题目详情
        user_answer: 用户的选择
        correct_answer: 正确答案

    Returns:
        Prompt 字符串
    """
    return f"""
题目：{question['title']}
选项：{', '.join([f"{o['key']}: {o['value'][:20]}..." for o in question.get('options', [])])}
你的答案：{user_answer}
正确答案：{correct_answer}

请用犀利但易懂的风格解释：
1. 为什么选 {correct_answer} 是对的
2. 为什么你选 {user_answer} 是错的（用户的思维误区在哪）
3. 这类题目的通用解题技巧
"""
