#!/usr/bin/env python3
"""
MiMo 成本优化工具 - 完整测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from hermes_integration import SmartConversationManager, TopicDetector, ConversationEfficiencyAnalyzer
from prompt_loader import PromptLoader

def test_topic_detector():
    print("=" * 60)
    print("🧪 测试话题检测器")
    print("=" * 60)
    detector = TopicDetector()
    test_cases = [
        ("帮我写一个Python脚本", "development"),
        ("今天天气怎么样", "daily"),
        ("我想减脂，帮我规划饮食", "health"),
        ("MiMo的额度还剩多少", "mimo"),
        ("帮我分析竞品", "business"),
        ("调研一下市场趋势", "research"),
    ]
    passed = 0
    for message, expected in test_cases:
        topic, confidence = detector.detect_topic(message)
        status = "✅" if topic == expected else "❌"
        print(f"{status} '{message[:20]}...' -> {topic} (confidence: {confidence:.2f})")
        if topic == expected:
            passed += 1
    print(f"\n通过率: {passed}/{len(test_cases)} ({passed/len(test_cases)*100:.0f}%)")
    return passed == len(test_cases)

def test_efficiency_analyzer():
    print("\n" + "=" * 60)
    print("🧪 测试效率分析器")
    print("=" * 60)
    analyzer = ConversationEfficiencyAnalyzer()
    short_messages = [{'content': 'hello'} for _ in range(3)]
    efficiency = analyzer.analyze_efficiency(short_messages)
    print(f"短对话效率: {efficiency:.2f} (期望: 1.0)")
    long_messages = [{'content': f'message {i}'} for i in range(20)]
    efficiency = analyzer.analyze_efficiency(long_messages)
    print(f"长对话效率: {efficiency:.2f}")
    repeat_messages = [{'content': 'same message'} for _ in range(20)]
    efficiency = analyzer.analyze_efficiency(repeat_messages)
    print(f"重复对话效率: {efficiency:.2f}")
    print("✅ 效率分析器测试完成")
    return True

def test_conversation_manager():
    print("\n" + "=" * 60)
    print("🧪 测试智能对话管理器")
    print("=" * 60)
    manager = SmartConversationManager()
    result = manager.process_message('user', '帮我写一个Python脚本', 100)
    assert result['action'] == 'add', f"期望add，得到{result['action']}"
    print("✅ 基本消息添加")
    manager.process_message('assistant', '好的，我来写', 50)
    result = manager.process_message('user', '今天天气怎么样', 20)
    assert result['action'] == 'new_session', f"期望new_session，得到{result['action']}"
    print("✅ 话题转换检测")
    manager.process_message('assistant', '让我查一下', 30)
    result = manager.process_message('user', '/new', 0)
    assert result['action'] == 'manual_new', f"期望manual_new，得到{result['action']}"
    print("✅ 手动新起")
    stats = manager.get_session_stats()
    assert 'session_id' in stats
    print("✅ 会话统计")
    report = manager.get_session_report()
    assert 'MiMo成本优化会话报告' in report
    print("✅ 会话报告")
    print("\n✅ 智能对话管理器测试全部通过")
    return True

def test_prompt_loader():
    print("\n" + "=" * 60)
    print("🧪 测试Prompt加载器")
    print("=" * 60)
    loader = PromptLoader()
    prompt = loader.load_prompt('帮我写Python代码')
    assert '代码优先' in prompt
    print("✅ 开发话题加载")
    prompt = loader.load_prompt('我想减脂')
    assert '精确克数' in prompt
    print("✅ 健康话题加载")
    prompt = loader.load_prompt('MiMo额度还剩多少')
    assert '真实数据优先' in prompt
    print("✅ MiMo话题加载")
    stats = loader.get_stats()
    assert 'loaded_domains' in stats
    print("✅ 加载统计")
    print("\n✅ Prompt加载器测试全部通过")
    return True

def run_all_tests():
    print("\n" + "=" * 60)
    print("🚀 MiMo 成本优化工具 - 完整测试")
    print("=" * 60)
    tests = [
        ("话题检测器", test_topic_detector),
        ("效率分析器", test_efficiency_analyzer),
        ("智能对话管理器", test_conversation_manager),
        ("Prompt加载器", test_prompt_loader),
    ]
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"❌ {name} 测试失败: {e}")
            results.append((name, False))
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败，请检查")
    print("=" * 60)
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)