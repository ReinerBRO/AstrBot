# LLM 事件分类实施 - Agent 分工方案

## 总体目标

实现混合事件分类器（规则 + LLM），提升事件分类准确度和可解释性。

## 架构概览

```
EventBuffer → AggregatedFeatures
                    ↓
            HybridEventClassifier
                    ↓
         规则分类器（快速路径）
                    ↓
         置信度 < 0.6？
            ↙         ↘
          是           否
          ↓            ↓
    LLM分类器      使用规则结果
          ↓            ↓
        融合引擎 ← ← ← ←
```

## Agent 分工

### Agent 1: LLM 集成专家

**职责**：实现 LLM 事件分类的核心逻辑

#### 任务清单

**Task 1.1: 实现 LLM API 调用**
- 文件：`watcher/signal_fusion/llm_event_classifier.py`
- 功能：
  - [ ] 创建或复用 API 客户端（基于 VLClient 或新建）
  - [ ] 实现 `classify()` 方法的 LLM 调用逻辑
  - [ ] 处理 API 超时和错误
  - [ ] 添加重试机制（最多 2 次）
- 接口：
  ```python
  def classify(self, features: AggregatedFeatures) -> EnhancedClassificationResult:
      # 1. 构建 prompt
      # 2. 调用 LLM API
      # 3. 解析响应
      # 4. 返回结果
  ```

**Task 1.2: Prompt 工程**
- 文件：`watcher/signal_fusion/llm_event_classifier.py`
- 功能：
  - [ ] 优化 `_build_prompt()` 方法
  - [ ] 添加 few-shot 示例（3-5 个典型案例）
  - [ ] 设计 JSON 输出格式约束
  - [ ] 处理中文和英文混合场景
- 示例 prompt 结构：
  ```
  系统角色 + 任务描述
  + 输入数据格式
  + Few-shot 示例
  + 输出格式要求
  + 注意事项
  ```

**Task 1.3: 响应解析和错误处理**
- 文件：`watcher/signal_fusion/llm_event_classifier.py`
- 功能：
  - [ ] 实现 `_parse_response()` 方法
  - [ ] 处理 JSON 解析失败
  - [ ] 处理 LLM 返回无效分类
  - [ ] 处理 LLM 返回格式错误
  - [ ] 添加 fallback 逻辑（降级到规则分类）
- 错误处理策略：
  ```python
  try:
      result = parse_llm_response(response)
  except JSONDecodeError:
      # 尝试提取关键信息
      result = extract_from_text(response)
  except Exception:
      # 降级到规则分类
      result = rule_classifier.classify(features)
  ```

**Task 1.4: 单元测试**
- 文件：`tests/signal_fusion/test_llm_event_classifier.py`
- 功能：
  - [ ] 测试正常分类流程
  - [ ] 测试 API 失败场景
  - [ ] 测试响应解析（正常 + 异常）
  - [ ] 测试 fallback 逻辑
  - [ ] Mock LLM API 调用
- 覆盖率目标：> 80%

**交付物**：
- ✅ `llm_event_classifier.py` 完整实现
- ✅ `test_llm_event_classifier.py` 测试文件
- ✅ Prompt 设计文档（在代码注释中）

---

### Agent 2: 系统集成专家

**职责**：将混合分类器集成到现有系统

#### 任务清单

**Task 2.1: 配置管理**
- 文件：`watcher/config.py`
- 功能：
  - [ ] 添加 LLM 分类器配置项
  - [ ] 添加环境变量解析
  - [ ] 设置合理的默认值
- 新增配置：
  ```python
  @dataclass
  class Config:
      # ... 现有配置 ...

      # LLM 事件分类器配置
      use_llm_event_classifier: bool  # 是否启用
      llm_event_model: str  # 模型名称
      llm_event_threshold: float  # 规则置信度阈值
      llm_event_always: bool  # 总是使用 LLM
      llm_event_timeout_s: float  # API 超时
  ```
- 环境变量：
  ```bash
  USE_LLM_EVENT_CLASSIFIER=true
  LLM_EVENT_MODEL=gpt-4o-mini
  LLM_EVENT_THRESHOLD=0.6
  LLM_EVENT_ALWAYS=false
  LLM_EVENT_TIMEOUT_S=10.0
  ```

**Task 2.2: 集成混合分类器**
- 文件：`watcher/runner.py`
- 功能：
  - [ ] 在 `__init__` 中初始化混合分类器
  - [ ] 根据配置选择使用规则或混合分类器
  - [ ] 传递正确的参数（API 客户端、配置等）
  - [ ] 保持向后兼容（默认使用规则分类器）
- 实现：
  ```python
  # 在 Watcher.__init__ 中
  if self.config.use_llm_event_classifier:
      llm_classifier = LLMEventClassifier(
          api_client=self.client,
          model=self.config.llm_event_model,
          categories=self.config.task_categories,
      )
      self.event_classifier = HybridEventClassifier(
          rule_classifier=EventClassifier(),
          llm_classifier=llm_classifier,
          llm_threshold=self.config.llm_event_threshold,
          always_use_llm=self.config.llm_event_always,
      )
  else:
      self.event_classifier = EventClassifier()
  ```

**Task 2.3: 日志和监控**
- 文件：`watcher/runner.py`
- 功能：
  - [ ] 记录 LLM 分类器的使用情况
  - [ ] 记录规则 vs LLM 的分类差异
  - [ ] 记录 LLM API 调用时间
  - [ ] 记录错误和 fallback 情况
- 日志示例：
  ```python
  # 在 _process_once 中
  if summary and self.event_source_enabled:
      start = time.time()
      event_result = self.event_classifier.classify(event_features)
      elapsed = time.time() - start

      self.reporter.log_event(
          now,
          f"event-classifier: category={event_result.category} "
          f"confidence={event_result.confidence:.2f} "
          f"elapsed={elapsed:.3f}s"
      )
  ```

**Task 2.4: 集成测试**
- 文件：`tests/test_runner_integration.py`
- 功能：
  - [ ] 测试混合分类器集成
  - [ ] 测试配置加载
  - [ ] 测试规则 → LLM 降级流程
  - [ ] 测试与融合引擎的交互
  - [ ] 端到端测试（模拟真实场景）
- 测试场景：
  ```python
  # 场景 1：规则置信度高，不调用 LLM
  # 场景 2：规则置信度低，调用 LLM
  # 场景 3：LLM 失败，fallback 到规则
  # 场景 4：LLM 和规则冲突，融合引擎处理
  ```

**Task 2.5: 文档和示例**
- 文件：`README.md` 或 `docs/LLM事件分类_使用指南.md`
- 功能：
  - [ ] 编写配置说明
  - [ ] 提供使用示例
  - [ ] 说明预期效果
  - [ ] 添加故障排查指南
- 内容：
  ```markdown
  ## LLM 事件分类器

  ### 启用方式
  在 .env 中添加：
  USE_LLM_EVENT_CLASSIFIER=true

  ### 配置选项
  ...

  ### 预期效果
  - 事件分类准确度提升 10-15%
  - 20% 情况会调用 LLM
  - 平均延迟增加 100-200ms

  ### 故障排查
  ...
  ```

**交付物**：
- ✅ `config.py` 更新
- ✅ `runner.py` 集成完成
- ✅ `test_runner_integration.py` 测试文件
- ✅ 使用文档

---

## 协作接口

### Agent 1 → Agent 2

**接口定义**：
```python
# llm_event_classifier.py
class LLMEventClassifier:
    def __init__(
        self,
        api_client,  # VLClient 或类似接口
        model: str = "gpt-4o-mini",
        categories: list[str] | None = None,
    ):
        ...

    def classify(
        self,
        features: AggregatedFeatures
    ) -> EnhancedClassificationResult:
        ...
```

**依赖**：
- Agent 2 需要 Agent 1 完成 `LLMEventClassifier` 的基本实现
- Agent 2 可以先用 mock 进行集成测试

### Agent 2 → Agent 1

**反馈**：
- Agent 2 在集成过程中发现的接口问题
- 实际使用中的错误日志
- 性能瓶颈（如果有）

---

## 时间规划

### 第 1 天
- **Agent 1**: Task 1.1 + 1.2（LLM API 调用 + Prompt 工程）
- **Agent 2**: Task 2.1（配置管理）

### 第 2 天
- **Agent 1**: Task 1.3（响应解析和错误处理）
- **Agent 2**: Task 2.2（集成混合分类器）

### 第 3 天
- **Agent 1**: Task 1.4（单元测试）
- **Agent 2**: Task 2.3 + 2.4（日志监控 + 集成测试）

### 第 4 天
- **联调**: 端到端测试，修复问题
- **Agent 2**: Task 2.5（文档）

### 第 5 天
- **验证**: 实际运行一天，收集数据
- **优化**: 根据反馈调整 prompt 和配置

---

## 验收标准

### Agent 1
- [ ] LLM API 调用成功率 > 95%
- [ ] 响应解析成功率 > 98%
- [ ] 单元测试覆盖率 > 80%
- [ ] 平均响应时间 < 1 秒
- [ ] Fallback 机制正常工作

### Agent 2
- [ ] 配置正确加载
- [ ] 混合分类器正确集成
- [ ] 日志完整记录关键信息
- [ ] 集成测试全部通过
- [ ] 文档清晰完整

### 整体
- [ ] 端到端测试通过
- [ ] 实际运行无崩溃
- [ ] 事件分类准确度提升可观测
- [ ] 性能影响在可接受范围内

---

## 风险和缓解

| 风险 | 责任方 | 缓解措施 |
|------|--------|----------|
| LLM API 不稳定 | Agent 1 | 添加重试和 fallback |
| Prompt 效果不佳 | Agent 1 | 迭代优化，添加示例 |
| 集成破坏现有功能 | Agent 2 | 保持向后兼容，充分测试 |
| 性能下降明显 | 两者 | 优化 prompt，调整阈值 |
| 配置复杂难用 | Agent 2 | 提供合理默认值，完善文档 |

---

## 沟通机制

- **每日同步**：分享进度和遇到的问题
- **接口变更**：提前通知对方
- **问题升级**：无法解决的问题及时讨论
- **代码审查**：互相 review 关键代码

---

## 下一步

1. **Agent 1** 开始实现 Task 1.1（LLM API 调用）
2. **Agent 2** 开始实现 Task 2.1（配置管理）
3. 每天同步进度，确保接口对齐
