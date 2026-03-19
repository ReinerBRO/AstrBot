# LLM 事件分类 - 重新设计方案

## 背景

当前系统使用规则匹配进行事件分类，在不考虑预算和延时的情况下，探索 LLM 增强方案。

## 核心问题

**当前架构的局限**：
1. 规则匹配只能识别关键词，无法理解上下文
2. 丢失时序信息（先做什么，后做什么）
3. 无法识别活动模式（调试、研究、多任务）
4. 对新应用/场景适应性差

**关键洞察**：
- VL 已经有 0.7 权重，看到完整截图
- 事件数据有限（应用名、窗口标题、点击数）
- 事件分类的价值在于：速度、验证、备用

## 设计方案

### 方案 A：混合分类器（推荐）

**架构**：
```
EventBuffer → AggregatedFeatures
                    ↓
            规则分类器（快速）
                    ↓
         置信度 < 0.6？
                ↙     ↘
              是        否
              ↓         ↓
        LLM 分析    使用规则结果
              ↓
        融合引擎
```

**优势**：
- 80% 情况用规则（快速、免费）
- 20% 情况用 LLM（深度理解）
- 向后兼容现有架构

**实现**：
- ✅ 已创建 `hybrid_classifier.py`
- ✅ 已创建 `llm_event_classifier.py`
- ⏳ 需要实现 LLM API 调用
- ⏳ 需要集成到 runner.py

### 方案 B：时序事件分析（更激进）

**核心思想**：不只分类，而是理解活动场景

**数据结构增强**：
```python
# 当前：只有聚合特征
AggregatedFeatures(
    click_count=15,
    top_app="VSCode",
    ...
)

# 增强：保留事件序列
EventSequence(
    events=[
        Event(ts=0, app="VSCode", window="main.py", action="click"),
        Event(ts=30, app="Chrome", window="Stack Overflow", action="switch"),
        Event(ts=45, app="VSCode", window="main.py", action="switch"),
        ...
    ],
    aggregated=AggregatedFeatures(...)
)
```

**LLM 输入示例**：
```json
{
  "time_window": "5 minutes",
  "summary": {
    "clicks": 15,
    "switches": 4,
    "top_apps": ["VSCode", "Chrome", "Terminal"]
  },
  "sequence": [
    "0:00 - VSCode: main.py (click)",
    "0:30 - Chrome: Python asyncio - Stack Overflow (switch)",
    "0:45 - VSCode: main.py (switch)",
    "1:00 - Terminal: pytest (switch)"
  ]
}
```

**LLM 输出示例**：
```json
{
  "category": "写代码",
  "confidence": 0.92,
  "reasoning": "用户在调试 Python 异步代码：编辑代码 → 查询文档 → 修改代码 → 运行测试",
  "activity_pattern": "debugging",
  "focus_level": "high",
  "sub_activities": [
    {"type": "coding", "duration": 120},
    {"type": "researching", "duration": 60},
    {"type": "testing", "duration": 60}
  ]
}
```

**优势**：
- 理解完整活动场景
- 识别行为模式
- 提供可解释的推理
- 可以生成更丰富的报告

**挑战**：
- 需要修改 EventBuffer 保留事件序列
- Token 消耗更多（但你说不考虑预算）
- 需要更复杂的 prompt 工程

### 方案 C：双模型协同

**架构**：
```
截图 → VL 模型 → 视觉理解
                    ↓
事件 → LLM 模型 → 行为理解
                    ↓
            协同融合引擎
                    ↓
            增强分类结果
```

**协同融合示例**：
```python
# VL 看到：
"用户在看一个代码编辑器，屏幕上有 Python 代码"

# LLM 看到：
"用户在 VSCode 和 Chrome 之间快速切换，查询 Stack Overflow"

# 融合结论：
"用户在调试 Python 代码，遇到问题后查询解决方案"
category = "写代码"
confidence = 0.95  # 两个信号一致，置信度高
activity_pattern = "debugging"
```

**优势**：
- VL 和 LLM 互补
- 更高的准确度
- 更丰富的上下文

**挑战**：
- 需要重新设计融合引擎
- 两次 API 调用（VL + LLM）
- 更复杂的 prompt 设计

## 实施建议

### 阶段 1：快速验证（1-2 天）

1. **实现 LLM API 调用**
   - 在 `llm_event_classifier.py` 中实现 `classify()` 方法
   - 使用现有的 `VLClient` 或创建新的 LLM 客户端
   - 测试基本分类功能

2. **集成混合分类器**
   - 在 `runner.py` 中添加配置选项：
     ```python
     use_llm_classifier = os.getenv("USE_LLM_EVENT_CLASSIFIER", "false").lower() == "true"
     llm_threshold = float(os.getenv("LLM_CLASSIFIER_THRESHOLD", "0.6"))
     ```
   - 替换 `EventClassifier` 为 `HybridEventClassifier`

3. **对比测试**
   - 运行一天，记录规则 vs LLM 的分类差异
   - 分析哪些场景 LLM 更准确
   - 评估实际收益

### 阶段 2：增强功能（3-5 天）

4. **保留事件序列**
   - 修改 `EventBuffer` 保留最近 20-30 个事件
   - 添加 `get_event_sequence()` 方法
   - 限制序列长度避免 token 爆炸

5. **时序分析 Prompt**
   - 设计更好的 prompt 利用时序信息
   - 添加活动模式识别
   - 添加专注度分析

6. **增强融合引擎**
   - 利用 LLM 的 reasoning 改进融合决策
   - 当 VL 和 LLM 冲突时，分析 reasoning 选择更合理的

### 阶段 3：优化迭代（持续）

7. **Prompt 优化**
   - 收集错误案例
   - 迭代改进 prompt
   - 添加 few-shot 示例

8. **成本优化**（如果后续需要）
   - 使用更小的模型（gpt-4o-mini）
   - 缓存常见模式
   - 批量处理

9. **可解释性增强**
   - 在 Web UI 显示 LLM 的 reasoning
   - 帮助用户理解分类依据
   - 收集用户反馈改进

## 配置参数

```bash
# .env 配置
USE_LLM_EVENT_CLASSIFIER=true          # 启用 LLM 分类器
LLM_CLASSIFIER_THRESHOLD=0.6           # 规则置信度阈值
LLM_CLASSIFIER_ALWAYS=false            # 总是使用 LLM（忽略阈值）
LLM_EVENT_MODEL=gpt-4o-mini            # LLM 模型
LLM_EVENT_SEQUENCE_ENABLED=false       # 启用时序分析（阶段2）
LLM_EVENT_SEQUENCE_LENGTH=20           # 保留事件数量
```

## 预期收益

### 定量收益
- 事件分类准确度：70% → 85-90%
- 最终分类准确度：+5-10%（考虑 0.3 权重）
- 冲突解决能力：+20%（VL 不确定时）

### 定性收益
- 理解活动场景（不只是分类）
- 识别行为模式（调试、研究、多任务）
- 提供可解释的推理
- 更好的用户体验（看到 reasoning）

### 成本
- API 调用：+20-100%（取决于阈值）
- 延迟：+200-500ms（可接受）
- 开发时间：5-10 天

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 不稳定 | 分类错误 | 保留规则作为 fallback |
| Token 超限 | 成本爆炸 | 限制序列长度，使用摘要 |
| 延迟过高 | 用户体验差 | 异步处理，显示进度 |
| Prompt 不佳 | 准确度低 | 迭代优化，添加示例 |

## 下一步

1. **你决定**：选择方案 A（混合）还是方案 B（时序）？
2. **我实现**：完成 LLM API 调用和集成
3. **你测试**：运行一天，看实际效果
4. **我们迭代**：根据反馈优化

你想先从哪个方案开始？
