#!/usr/bin/env python3
"""
Hermes 按需Prompt加载器
根据对话话题动态加载系统提示
"""
import os
import json
from typing import Dict, List, Optional

# 核心提示（必读）
CORE_PROMPT = """你是一个智能助手，名叫Hermes。你的特点：
- 诚实务实，先做再说
- 直接高效，不堆术语
- 中文交流，简洁清晰
- 执行力强，一口气做完

你的记忆：
- 用户是中国开发者，用小米MiMo模型
- 偏好MCP集成，开箱即用
- 有女朋友在减肥，目标120→110斤
- 有健身教练Agent"小美"
- 偏好"先做再说"，不纠结前期调研"""

# 领域提示（按需加载）
DOMAIN_PROMPTS = {
    'development': """开发相关规则：
- 代码优先，先跑通再优化
- 使用Python/Node.js，优先MCP集成
- 部署用Docker，配置用YAML
- 测试要覆盖核心路径""",
    'business': """业务相关规则：
- 用户需求优先，快速验证
- MVP思维，先做核心功能
- 数据驱动，关注转化率
- 竞品分析要找差异化""",
    'health': """健康相关规则：
- 精确克数，表格展示
- 科学减脂，热量缺口
- 营养均衡，蛋白质优先
- 减肥截止6/15，目标110斤""",
    'research': """研究相关规则：
- 信息收集要全面
- 数据要验证来源
- 分析要客观中立
- 结论要可执行""",
    'mimo': """MiMo相关规则：
- 真实数据优先，避免估算
- 缓存命中率分析
- 成本优化建议
- 套餐进度监控""",
    'daily': """日常交流规则：
- 保持友好亲切
- 回答简洁实用
- 适当使用emoji
- 记住用户习惯"""
}

# 话题关键词映射
TOPIC_KEYWORDS = {
    'development': ['代码', '编程', '开发', 'bug', '部署', 'git', 'python', 'javascript', 'api', '数据库', '服务器', 'docker', 'nginx'],
    'business': ['产品', '需求', '用户', '市场', '竞品', '功能', '设计', 'UI', 'UX', '运营'],
    'health': ['健身', '减肥', '饮食', '运动', '体重', '卡路里', '蛋白质', '减脂', '增肌'],
    'research': ['调研', '分析', '报告', '数据', '趋势', '对比', '评估'],
    'mimo': ['额度', 'token', '消耗', '套餐', '用量', '成本', '监控', '优化', '压缩'],
    'daily': ['天气', '新闻', '提醒', '日程', '聊天', '闲聊', '问候']
}

class PromptLoader:
    """按需Prompt加载器"""
    
    def __init__(self):
        self.loaded_domains = set()
        self.current_topic = None
    
    def detect_topic(self, message: str) -> str:
        message_lower = message.lower()
        scores = {}
        for topic, keywords in TOPIC_KEYWORDS.items():
            match_count = sum(1 for kw in keywords if kw in message_lower)
            if match_count > 0:
                scores[topic] = match_count
        if not scores:
            return 'general'
        return max(scores, key=scores.get)
    
    def load_prompt(self, message: str, context: List[Dict] = None) -> str:
        topic = self.detect_topic(message)
        if topic != 'general':
            self.current_topic = topic
            self.loaded_domains.add(topic)
        prompt_parts = [CORE_PROMPT]
        if topic in DOMAIN_PROMPTS:
            prompt_parts.append(DOMAIN_PROMPTS[topic])
        if context:
            context_topics = set()
            for msg in context[-5:]:
                if isinstance(msg, dict) and 'content' in msg:
                    ctx_topic = self.detect_topic(msg['content'])
                    if ctx_topic != 'general':
                        context_topics.add(ctx_topic)
            for ctx_topic in context_topics:
                if ctx_topic != topic and ctx_topic in DOMAIN_PROMPTS:
                    prompt_parts.append(DOMAIN_PROMPTS[ctx_topic])
        return '\n\n'.join(prompt_parts)
    
    def get_stats(self) -> Dict:
        return {
            'loaded_domains': list(self.loaded_domains),
            'current_topic': self.current_topic,
            'total_loaded': len(self.loaded_domains)
        }

if __name__ == "__main__":
    loader = PromptLoader()
    prompt = loader.load_prompt('帮我写Python代码')
    print(f'Prompt loaded: {len(prompt)} chars')