#!/usr/bin/env python3
"""
Hermes 智能对话管理集成
- 话题转移检测（主要条件）
- Token超限保护（保护机制）
- 轮次过长检查（检查信号）
- 手动新起命令（用户控制）
- 按需Prompt加载
"""
import os
import json
import yaml
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import Counter

# 加载配置
CONFIG_PATH = os.path.expanduser("~/.hermes/config/mimo_optimization.yaml")

def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return get_default_config()

def get_default_config():
    """获取默认配置"""
    return {
        'conversation': {
            'topic_detection': {
                'enabled': True,
                'recent_messages': 3,
                'threshold': 2
            },
            'compression_triggers': {
                'max_tokens': 4000,
                'warning_threshold': 0.8
            },
            'long_conversation': {
                'enabled': True,
                'threshold': 20,
                'check_interval': 5,
                'efficiency_threshold': 0.6
            },
            'manual_new': {
                'enabled': True,
                'command': '/new'
            }
        }
    }

class TopicDetector:
    """话题检测器"""
    
    TOPIC_KEYWORDS = {
        'development': {
            'keywords': ['代码', '编程', '开发', 'bug', '部署', 'git', 'python', 'javascript', 'api', '数据库', '服务器', 'docker', 'nginx', '脚本', '函数', '调试', '测试'],
            'weight': 1.0
        },
        'business': {
            'keywords': ['产品', '需求', '用户', '市场', '竞品', '功能', '设计', 'UI', 'UX', '运营', '方案', '规划', '策略'],
            'weight': 1.0
        },
        'health': {
            'keywords': ['健身', '减肥', '饮食', '运动', '体重', '卡路里', '蛋白质', '减脂', '增肌', '营养'],
            'weight': 1.0
        },
        'research': {
            'keywords': ['调研', '分析', '报告', '数据', '趋势', '对比', '评估', '研究', '探索'],
            'weight': 0.8
        },
        'mimo': {
            'keywords': ['额度', 'token', '消耗', '套餐', '用量', '成本', '监控', '优化', '压缩'],
            'weight': 1.2
        },
        'daily': {
            'keywords': ['天气', '新闻', '提醒', '日程', '聊天', '闲聊', '问候', '谢谢', '好的'],
            'weight': 0.5
        }
    }
    
    def detect_topic(self, message: str) -> Tuple[str, float]:
        message_lower = message.lower()
        scores = {}
        for topic, config in self.TOPIC_KEYWORDS.items():
            keywords = config['keywords']
            weight = config['weight']
            match_count = sum(1 for kw in keywords if kw in message_lower)
            if match_count > 0:
                scores[topic] = match_count * weight
        if not scores:
            return 'general', 0.0
        best_topic = max(scores, key=scores.get)
        max_score = scores[best_topic]
        total_score = sum(scores.values())
        confidence = max_score / total_score if total_score > 0 else 0
        return best_topic, confidence
    
    def is_topic_changed(self, prev_messages, current_message, threshold=0.6):
        if not prev_messages:
            return False, 'none', self.detect_topic(current_message)[0]
        recent_topics = [self.detect_topic(msg)[0] for msg in prev_messages[-3:]]
        current_topic, current_confidence = self.detect_topic(current_message)
        if current_confidence < threshold:
            return False, recent_topics[-1], current_topic
        if current_topic != recent_topics[-1]:
            if len(set(recent_topics)) == 1 and current_topic != recent_topics[0]:
                return True, recent_topics[0], current_topic
        return False, recent_topics[-1], current_topic

class ConversationEfficiencyAnalyzer:
    def analyze_efficiency(self, messages):
        if len(messages) < 5:
            return 1.0
        efficiency_score = 1.0
        recent_contents = [m['content'] for m in messages[-10:]]
        unique_ratio = len(set(recent_contents)) / len(recent_contents)
        if unique_ratio < 0.7:
            efficiency_score *= 0.7
        lengths = [len(m['content']) for m in messages[-10:]]
        if lengths:
            avg_length = sum(lengths) / len(lengths)
            if avg_length < 20:
                efficiency_score *= 0.8
        topics = [TopicDetector().detect_topic(m['content'])[0] for m in messages[-10:]]
        topic_consistency = len(set(topics)) / len(topics) if topics else 1
        if topic_consistency > 0.8:
            efficiency_score *= 0.9
        return min(1.0, efficiency_score)

class ConversationSession:
    def __init__(self, session_id=None):
        self.session_id = session_id or datetime.now().strftime('%Y%m%d_%H%M%S')
        self.messages = []
        self.topics = []
        self.start_time = datetime.now()
        self.last_activity = datetime.now()
        self.total_tokens = 0
        self.message_count = 0
    
    def add_message(self, role, content, tokens=0):
        self.messages.append({'role': role, 'content': content, 'timestamp': datetime.now().isoformat(), 'tokens': tokens})
        detector = TopicDetector()
        topic, confidence = detector.detect_topic(content)
        self.topics.append({'topic': topic, 'confidence': confidence, 'timestamp': datetime.now().isoformat()})
        self.last_activity = datetime.now()
        self.total_tokens += tokens
        self.message_count += 1
    
    def get_duration_days(self):
        return (datetime.now() - self.start_time).total_seconds() / 86400
    
    def get_dominant_topic(self):
        if not self.topics:
            return 'general'
        topic_counts = Counter(t['topic'] for t in self.topics)
        return topic_counts.most_common(1)[0][0]
    
    def should_compress(self, max_tokens=4000):
        if self.total_tokens > max_tokens:
            return True, f'Token超限: {self.total_tokens}/{max_tokens}'
        if self.get_duration_days() > 2:
            return True, f'跨天对话: {self.get_duration_days():.1f}天'
        return False, '正常'

class SmartConversationManager:
    def __init__(self, config=None):
        self.config = config or self._get_default_config()
        self.sessions = []
        self.current_session = None
        self.topic_detector = TopicDetector()
        self.efficiency_analyzer = ConversationEfficiencyAnalyzer()
        self.session_stats = {'total_tokens_saved': 0, 'compressed_count': 0, 'topic_changes': 0}
    
    def _get_default_config(self):
        return get_default_config()['conversation']
    
    def start_new_session(self):
        session = ConversationSession()
        self.sessions.append(session)
        self.current_session = session
        return session
    
    def process_message(self, role, content, tokens=0):
        if content.strip() == self.config['manual_new']['command']:
            if self.current_session:
                summary = self._generate_session_summary(self.current_session)
                new_session = self.start_new_session()
                new_session.add_message('system', f'上一话题摘要: {summary}', 50)
                return {'action': 'manual_new', 'reason': '用户手动新起', 'summary': summary, 'session_id': new_session.session_id}
        if not self.current_session:
            self.start_new_session()
        should_new, reason = self._check_should_new_session(content)
        if should_new:
            summary = self._generate_session_summary(self.current_session)
            new_session = self.start_new_session()
            new_session.add_message('system', f'上一话题摘要: {summary}', 50)
            self.session_stats['topic_changes'] += 1
            return {'action': 'new_session', 'reason': reason, 'summary': summary, 'session_id': new_session.session_id}
        should_compress, compress_reason = self.current_session.should_compress(self.config['compression_triggers']['max_tokens'])
        if should_compress:
            compressed_history = self._compress_history(self.current_session)
            self.current_session.messages = compressed_history
            self.session_stats['compressed_count'] += 1
            saved_tokens = len(compressed_history) * 500
            self.session_stats['total_tokens_saved'] += saved_tokens
            return {'action': 'compress', 'reason': compress_reason, 'compressed_count': len(self.current_session.messages), 'saved_tokens': saved_tokens}
        long_conv_config = self.config['long_conversation']
        if (long_conv_config['enabled'] and self.current_session.message_count >= long_conv_config['threshold'] and self.current_session.message_count % long_conv_config['check_interval'] == 0):
            efficiency = self.efficiency_analyzer.analyze_efficiency(self.current_session.messages)
            if efficiency < long_conv_config['efficiency_threshold']:
                compressed_history = self._compress_history(self.current_session)
                self.current_session.messages = compressed_history
                self.session_stats['compressed_count'] += 1
                saved_tokens = len(compressed_history) * 500
                self.session_stats['total_tokens_saved'] += saved_tokens
                return {'action': 'compress', 'reason': f'轮次过长且效率低: {efficiency:.2f}', 'efficiency': efficiency, 'compressed_count': len(self.current_session.messages), 'saved_tokens': saved_tokens}
        self.current_session.add_message(role, content, tokens)
        return {'action': 'add', 'session_id': self.current_session.session_id, 'total_tokens': self.current_session.total_tokens, 'topic': self.current_session.get_dominant_topic(), 'message_count': self.current_session.message_count}
    
    def _check_should_new_session(self, content):
        if not self.current_session or not self.current_session.messages:
            return False, ''
        recent_messages = [m['content'] for m in self.current_session.messages[-3:]]
        is_changed, old_topic, new_topic = self.topic_detector.is_topic_changed(recent_messages, content)
        if is_changed:
            return True, f'话题转换: {old_topic} → {new_topic}'
        return False, ''
    
    def _generate_session_summary(self, session):
        if not session.messages:
            return '无内容'
        dominant_topic = session.get_dominant_topic()
        key_points = [msg['content'][:30] + '...' for msg in session.messages if len(msg['content']) > 30]
        duration = session.get_duration_days()
        summary_parts = [f'话题: {dominant_topic}', f'持续: {duration:.1f}天', f'消息数: {len(session.messages)}', f'Token: {session.total_tokens:,}']
        if key_points:
            summary_parts.append(f'要点: {", ".join(key_points[:3])}')
        return ' | '.join(summary_parts)
    
    def _compress_history(self, session):
        messages = session.messages
        if len(messages) <= 10:
            return messages
        recent = messages[-5:]
        early = messages[:-5]
        summary = self._generate_session_summary_from_messages(early)
        summary_msg = {'role': 'system', 'content': f'对话摘要: {summary}', 'timestamp': datetime.now().isoformat(), 'tokens': len(summary) // 4}
        return [summary_msg] + recent
    
    def _generate_session_summary_from_messages(self, messages):
        topics = set()
        key_points = []
        for msg in messages:
            content = msg['content']
            topic, _ = self.topic_detector.detect_topic(content)
            topics.add(topic)
            if len(content) > 30:
                key_points.append(content[:30] + '...')
        return f'讨论了{", ".join(topics)}等话题，涉及{len(key_points)}个要点'
    
    def get_session_stats(self):
        if not self.current_session:
            return {}
        session = self.current_session
        return {'session_id': session.session_id, 'duration_days': session.get_duration_days(), 'message_count': len(session.messages), 'total_tokens': session.total_tokens, 'dominant_topic': session.get_dominant_topic(), 'topic_changes': len(set(t['topic'] for t in session.topics)), 'session_stats': self.session_stats}
    
    def get_session_report(self):
        report = []
        report.append('=' * 60)
        report.append('📊 MiMo成本优化会话报告')
        report.append('=' * 60)
        report.append(f'📅 时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        report.append(f'\n📈 统计信息:')
        report.append(f'  消息数: {len(self.current_session.messages) if self.current_session else 0}')
        report.append(f'  总Token: {self.current_session.total_tokens if self.current_session else 0:,}')
        report.append(f'  压缩次数: {self.session_stats["compressed_count"]}')
        report.append(f'  话题转换: {self.session_stats["topic_changes"]}')
        report.append(f'\n💡 优化效果:')
        report.append(f'  预估节省: {self.session_stats["total_tokens_saved"]:,} tokens')
        report.append('=' * 60)
        return '\n'.join(report)

if __name__ == "__main__":
    manager = SmartConversationManager()
    print('智能对话管理器已加载')