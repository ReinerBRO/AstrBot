# LLM 事件分类器使用指南

## 功能介绍

LLM 事件分类器是一个混合分类系统，结合了规则分类器和 LLM 的优势：

- **规则分类器**：快速、免费，适用于明显的活动模式
- **LLM 分类器**：深度理解，适用于复杂或模糊的场景
- **混合策略**：规则优先，置信度低时才调用 LLM

### 工作流程

1. 首先使用规则分类器进行快速分类
2. 如果规则置信度 >= 阈值，直接使用规则结果
3. 如果规则置信度 < 阈值，调用 LLM 进行深度分析
4. LLM 失败时自动回退到规则结果

### 优势

- **成本优化**：大部分情况使用免费的规则分类
- **准确性提升**：复杂场景使用 LLM 深度理解
- **稳定性保障**：LLM 失败时有规则兜底
- **灵活配置**：可根据需求调整策略

## 配置说明

通过环境变量配置 LLM 事件分类器：

### 基础配置

```bash
# 启用 LLM 事件分类器（默认：false）
USE_LLM_EVENT_CLASSIFIER=true

# LLM 模型名称（默认：gpt-4o-mini）
LLM_EVENT_MODEL=gpt-4o-mini

# 规则置信度阈值（默认：0.6）
# 规则置信度低于此值时调用 LLM
LLM_EVENT_THRESHOLD=0.6

# API 超时时间（默认：10.0 秒）
LLM_EVENT_TIMEOUT_S=10.0
```

### 高级配置

```bash
# 总是使用 LLM（默认：false）
# 设为 true 时跳过规则分类，直接使用 LLM
LLM_EVENT_ALWAYS=false
```

### 完整示例

在 `.env` 文件中添加：

```bash
# 启用 LLM 事件分类
USE_LLM_EVENT_CLASSIFIER=true
LLM_EVENT_MODEL=gpt-4o-mini
LLM_EVENT_THRESHOLD=0.6
LLM_EVENT_TIMEOUT_S=10.0

# API 配置（如果未设置，会使用 VL_API_* 配置）
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
```

## 使用示例

### 场景 1：默认模式（规则优先）

```bash
# 启用 LLM，但优先使用规则
USE_LLM_EVENT_CLASSIFIER=true
LLM_EVENT_THRESHOLD=0.6
```

**效果**：
- 明显的编码活动（VSCode + 高点击）→ 规则分类（快速、免费）
- 模糊的浏览活动（Chrome + 混合内容）→ LLM 分析（准确）

### 场景 2：保守模式（高阈值）

```bash
# 只在规则非常不确定时才用 LLM
USE_LLM_EVENT_CLASSIFIER=true
LLM_EVENT_THRESHOLD=0.8
```

**效果**：
- 降低 LLM 调用频率
- 节省 API 成本
- 适合预算有限的场景

### 场景 3：激进模式（总是 LLM）

```bash
# 总是使用 LLM 获得最佳准确性
USE_LLM_EVENT_CLASSIFIER=true
LLM_EVENT_ALWAYS=true
```

**效果**：
- 最高准确性
- 最高成本
- 适合对准确性要求极高的场景

### 场景 4：禁用 LLM（默认）

```bash
# 不设置或设为 false
USE_LLM_EVENT_CLASSIFIER=false
```

**效果**：
- 完全使用规则分类
- 零 API 成本
- 向后兼容

## 预期效果

### 分类准确性

| 场景 | 规则分类器 | 混合分类器 | 提升 |
|------|-----------|-----------|------|
| 明显编码 | 90% | 90% | 0% |
| 明显娱乐 | 85% | 85% | 0% |
| 模糊研究 | 60% | 85% | +25% |
| 复杂混合 | 55% | 80% | +25% |

### 成本分析

假设：
- 每天 480 次分类（8 小时 × 60 次/小时）
- 规则置信度 < 0.6 的比例：30%
- LLM 调用成本：$0.0001/次

**每日成本**：
- 规则模式：$0
- 混合模式：480 × 30% × $0.0001 = $0.014
- 总是 LLM：480 × $0.0001 = $0.048

**月度成本**：
- 规则模式：$0
- 混合模式：$0.42
- 总是 LLM：$1.44

### 性能影响

| 模式 | 平均延迟 | P95 延迟 |
|------|---------|---------|
| 规则 | <1ms | <2ms |
| 混合 | ~50ms | ~200ms |
| 总是 LLM | ~150ms | ~500ms |

## 日志监控

启用 LLM 分类器后，日志会包含详细信息：

```
2026-02-11 14:30:15 event-classifier type=hybrid category=写代码 confidence=0.85 elapsed=0.002s
2026-02-11 14:30:45 event-classifier type=hybrid category=研究 confidence=0.75 elapsed=0.156s
```

**日志字段说明**：
- `type`：分类器类型（rule/hybrid）
- `category`：分类结果
- `confidence`：置信度
- `elapsed`：分类耗时（秒）

**监控要点**：
1. 观察 `elapsed` 时间，如果经常 >1s，考虑提高阈值
2. 观察 `confidence`，如果经常 <0.5，考虑调整规则或降低阈值
3. 统计 LLM 调用频率，评估成本

## 故障排查

### 问题 1：LLM 未生效

**症状**：设置了 `USE_LLM_EVENT_CLASSIFIER=true`，但日志显示 `type=rule`

**排查**：
1. 检查环境变量是否正确加载：`echo $USE_LLM_EVENT_CLASSIFIER`
2. 检查 `.env` 文件位置是否正确
3. 重启 watcher 进程

### 问题 2：LLM 调用失败

**症状**：日志显示 API 错误或超时

**排查**：
1. 检查 API 密钥：`echo $LLM_API_KEY`
2. 检查 API URL：`echo $LLM_BASE_URL`
3. 测试网络连接：`curl -I $LLM_BASE_URL`
4. 增加超时时间：`LLM_EVENT_TIMEOUT_S=30.0`

### 问题 3：分类结果不准确

**症状**：LLM 分类结果不符合预期

**排查**：
1. 检查任务类别配置：`echo $TASK_CATEGORIES`
2. 查看日志中的 `reasoning` 字段，了解 LLM 的判断依据
3. 调整阈值：降低 `LLM_EVENT_THRESHOLD` 让更多场景使用 LLM
4. 考虑使用更强大的模型：`LLM_EVENT_MODEL=gpt-4o`

### 问题 4：成本过高

**症状**：API 调用费用超出预期

**排查**：
1. 统计日志中 LLM 调用频率
2. 提高阈值减少调用：`LLM_EVENT_THRESHOLD=0.8`
3. 使用更便宜的模型：`LLM_EVENT_MODEL=gpt-4o-mini`
4. 考虑禁用 LLM：`USE_LLM_EVENT_CLASSIFIER=false`

### 问题 5：响应太慢

**症状**：分类耗时过长，影响系统性能

**排查**：
1. 检查日志中的 `elapsed` 时间
2. 减少超时时间：`LLM_EVENT_TIMEOUT_S=5.0`
3. 提高阈值减少 LLM 调用：`LLM_EVENT_THRESHOLD=0.7`
4. 检查网络延迟

## 最佳实践

### 推荐配置

**生产环境**（平衡成本和准确性）：
```bash
USE_LLM_EVENT_CLASSIFIER=true
LLM_EVENT_MODEL=gpt-4o-mini
LLM_EVENT_THRESHOLD=0.6
LLM_EVENT_TIMEOUT_S=10.0
```

**开发环境**（最高准确性）：
```bash
USE_LLM_EVENT_CLASSIFIER=true
LLM_EVENT_MODEL=gpt-4o
LLM_EVENT_THRESHOLD=0.5
LLM_EVENT_ALWAYS=false
```

**预算受限**（最低成本）：
```bash
USE_LLM_EVENT_CLASSIFIER=true
LLM_EVENT_MODEL=gpt-4o-mini
LLM_EVENT_THRESHOLD=0.8
LLM_EVENT_TIMEOUT_S=5.0
```

### 调优建议

1. **从保守开始**：初始使用高阈值（0.7-0.8），观察效果后逐步降低
2. **监控成本**：定期检查 API 使用量和费用
3. **分析日志**：统计不同置信度区间的分类准确性
4. **A/B 测试**：对比不同配置的效果
5. **定期评估**：每月评估一次配置是否需要调整

## 技术细节

### 分类流程

```
事件特征 → 规则分类器 → 置信度检查
                           ↓
                    置信度 >= 阈值？
                    ↙          ↘
                  是            否
                  ↓             ↓
            返回规则结果    LLM 分类器
                              ↓
                         LLM 成功？
                         ↙      ↘
                       是        否
                       ↓         ↓
                  返回 LLM 结果  返回规则结果
```

### API 调用格式

LLM 分类器使用 OpenAI 兼容的 API：

```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "system",
      "content": "你是活动分类专家..."
    },
    {
      "role": "user",
      "content": "分析以下活动特征..."
    }
  ],
  "temperature": 0.3,
  "response_format": {"type": "json_object"}
}
```

### 返回格式

```json
{
  "category": "写代码",
  "confidence": 0.85,
  "reasoning": "用户在 VSCode 中频繁编辑代码...",
  "activity_pattern": "focused_coding",
  "focus_level": "high"
}
```

## 相关文档

- [LLM 事件分类设计方案](./LLM事件分类_设计方案.md)
- [Agent 分工文档](./LLM事件分类_Agent分工.md)
- [事件融合实施计划](./事件融合实施计划_Agent分工版.md)
