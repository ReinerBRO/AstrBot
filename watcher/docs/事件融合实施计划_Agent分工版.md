# 点击/窗口事件融合实施计划 - Agent 分工版

**项目目标**: 引入鼠标点击和窗口信息作为第二信息源，提升活动分类准确率

**更新日期**: 2026-02-10

---

## Agent 分工概览

| Agent | 负责模块 | 主要任务 | 依赖 |
|-------|---------|---------|------|
| Agent A | 事件采集 | 实现点击和窗口事件采集 | 无 |
| Agent B | 事件存储 | 实现事件缓冲和聚合 | Agent A |
| Agent C | 融合算法 | 实现 VL 和事件信号融合 | Agent B |
| Agent D | 系统集成 | 集成到主流程和 API | Agent C |

---

## Agent A: 事件采集模块

### 职责
实现鼠标点击和窗口信息的实时采集功能。

### 交付物

#### 1. 点击事件监听器
**文件**: `watcher/event_source/click_listener.py`

**功能要求**:
- 使用 pynput 监听全局鼠标点击事件
- 采集数据：时间戳、坐标 (x, y)、按钮类型 (left/right/middle)
- 权限失败时优雅降级（记录错误但不中断程序）
- 支持启动/停止控制

**接口定义**:
```python
class ClickListener:
    def __init__(self, callback: Callable[[ClickEvent], None]):
        """初始化监听器，传入回调函数"""
        pass

    def start(self) -> bool:
        """启动监听，返回是否成功"""
        pass

    def stop(self) -> None:
        """停止监听"""
        pass

    def is_running(self) -> bool:
        """检查是否正在运行"""
        pass
```

**数据模型**:
```python
@dataclass
class ClickEvent:
    ts: float  # Unix 时间戳
    x: int
    y: int
    button: str  # "left" | "right" | "middle"
```

#### 2. 窗口信息解析器
**文件**: `watcher/event_source/window_resolver.py`

**功能要求**:
- 获取当前前台应用名称
- 获取当前窗口标题
- 获取应用 Bundle ID (macOS)
- 跨平台兼容（优先 macOS，可选 Windows/Linux）

**接口定义**:
```python
class WindowResolver:
    @staticmethod
    def get_active_window() -> WindowInfo:
        """获取当前活动窗口信息"""
        pass
```

**数据模型**:
```python
@dataclass
class WindowInfo:
    app_name: str
    window_title: str
    bundle_id: str | None
    timestamp: float
```

### 验收标准
- ✅ 点击监听器可以正常启动和停止
- ✅ 每次点击都能准确采集时间、坐标、按钮类型
- ✅ 窗口解析器能获取应用名称和窗口标题
- ✅ macOS 权限不足时不会崩溃，能记录错误日志
- ✅ 单元测试覆盖率 ≥ 80%

### 配置项
```python
# 在 config.py 中添加
ENABLE_EVENT_SOURCE: bool = True  # 是否启用事件源
EVENT_PRIVACY_MASK: bool = False  # 是否脱敏窗口标题
```

---

## Agent B: 事件存储模块

### 职责
实现事件的缓冲、聚合和持久化功能。

### 依赖
- Agent A 的 `ClickEvent` 和 `WindowInfo` 数据模型

### 交付物

#### 1. 事件缓冲器
**文件**: `watcher/event_source/event_buffer.py`

**功能要求**:
- 内存环形缓冲区，存储最近 N 分钟的事件
- 按时间窗口聚合事件（默认 5 分钟）
- 计算聚合特征：点击次数、应用切换次数、活跃时长
- 提取窗口关键词（去除常见词，保留有意义的词）

**接口定义**:
```python
class EventBuffer:
    def __init__(self, window_seconds: int = 300):
        """初始化缓冲器，指定时间窗口"""
        pass

    def add_click(self, event: ClickEvent, window: WindowInfo) -> None:
        """添加点击事件"""
        pass

    def get_aggregated_features(self,
                                start_time: float,
                                end_time: float) -> AggregatedFeatures:
        """获取指定时间范围的聚合特征"""
        pass

    def clear_old_events(self, before_time: float) -> None:
        """清理指定时间之前的事件"""
        pass
```

**数据模型**:
```python
@dataclass
class AggregatedFeatures:
    start_time: float
    end_time: float
    click_count: int
    app_switch_count: int
    active_seconds: float
    top_app: str  # 最常用的应用
    top_window_keywords: list[str]  # 窗口标题关键词（频率排序）
    app_distribution: dict[str, int]  # 应用使用分布
```

#### 2. 事件持久化
**文件**: `watcher/event_source/event_logger.py`

**功能要求**:
- 将原始事件写入 JSONL 文件
- 文件路径：`logs/click-events-YYYY-MM-DD.jsonl`
- 每天自动创建新文件
- 支持异步写入（避免阻塞主线程）

**接口定义**:
```python
class EventLogger:
    def __init__(self, log_dir: Path):
        """初始化日志器"""
        pass

    def log_event(self, event: ClickEvent, window: WindowInfo) -> None:
        """记录事件到文件"""
        pass

    def flush(self) -> None:
        """强制刷新缓冲区"""
        pass
```

**文件格式**:
```jsonl
{"ts": 1707552000.123, "x": 100, "y": 200, "button": "left", "app_name": "VSCode", "window_title": "main.py", "bundle_id": "com.microsoft.VSCode"}
```

### 验收标准
- ✅ 环形缓冲区能正确存储和清理事件
- ✅ 聚合特征计算准确（点击数、应用切换数等）
- ✅ 窗口关键词提取合理（去除 "Untitled", "New Tab" 等无意义词）
- ✅ JSONL 文件格式正确，每天自动创建新文件
- ✅ 单元测试覆盖率 ≥ 80%

### 配置项
```python
EVENT_BUFFER_WINDOW_S: int = 300  # 缓冲窗口大小（秒）
EVENT_LOG_DIR: Path = Path("logs")  # 日志目录
```

---

## Agent C: 融合算法模块

### 职责
实现 VL 分类结果和事件信号的融合算法。

### 依赖
- Agent B 的 `AggregatedFeatures` 数据模型
- 现有的 VL 分类结果

### 交付物

#### 1. 事件分类器
**文件**: `watcher/signal_fusion/event_classifier.py`

**功能要求**:
- 基于窗口关键词和应用名称进行规则分类
- 支持关键词规则配置（IDE、论文、视频、聊天工具等）
- 输出分类结果和置信度

**接口定义**:
```python
class EventClassifier:
    def __init__(self, rules: dict[str, list[str]]):
        """初始化分类器，传入关键词规则"""
        pass

    def classify(self, features: AggregatedFeatures) -> ClassificationResult:
        """基于聚合特征进行分类"""
        pass
```

**数据模型**:
```python
@dataclass
class ClassificationResult:
    category: str  # "写代码" | "研究" | "娱乐" | "其他"
    confidence: float  # 0.0 - 1.0
    reason: str  # 分类理由
```

**关键词规则示例**:
```python
KEYWORD_RULES = {
    "写代码": ["vscode", "pycharm", "intellij", "terminal", "git", "github"],
    "研究": ["arxiv", "paper", "pdf", "scholar", "documentation"],
    "娱乐": ["youtube", "bilibili", "netflix", "spotify", "游戏"],
    "聊天": ["wechat", "slack", "discord", "telegram", "zoom"]
}
```

#### 2. 融合决策器
**文件**: `watcher/signal_fusion/fusion_engine.py`

**功能要求**:
- 接收 VL 分类结果和事件分类结果
- 基于置信度加权融合
- 处理冲突情况（高置信度覆盖低置信度）
- 输出最终分类和融合理由

**接口定义**:
```python
class FusionEngine:
    def fuse(self,
             vl_result: ClassificationResult,
             event_result: ClassificationResult) -> FusionResult:
        """融合两个分类结果"""
        pass
```

**数据模型**:
```python
@dataclass
class FusionResult:
    category: str
    confidence: float
    source: str  # "vl" | "event" | "fusion"
    reason: str  # 融合理由
    vl_category: str | None  # 原始 VL 分类
    event_category: str | None  # 原始事件分类
```

**融合规则**:
1. 若 VL 置信度 > 0.8，直接采用 VL 结果
2. 若事件置信度 > 0.8 且 VL 置信度 < 0.5，采用事件结果
3. 若两者置信度接近（差值 < 0.2），加权平均
4. 若两者冲突且置信度都不高，保守采用"研究"或沿用上一次分类

### 验收标准
- ✅ 事件分类器能基于关键词正确分类
- ✅ 融合引擎能处理各种冲突情况
- ✅ 融合理由清晰可读
- ✅ 单元测试覆盖率 ≥ 80%
- ✅ 集成测试验证融合逻辑正确性

### 配置项
```python
FUSION_VL_WEIGHT: float = 0.7  # VL 权重
FUSION_EVENT_WEIGHT: float = 0.3  # 事件权重
FUSION_CONFIDENCE_THRESHOLD: float = 0.5  # 置信度阈值
```

---

## Agent D: 系统集成模块

### 职责
将事件融合功能集成到主流程和 API。

### 依赖
- Agent A、B、C 的所有模块

### 交付物

#### 1. Runner 集成
**文件**: `watcher/runner.py`（修改）

**功能要求**:
- 在主循环中启动事件监听器
- 每轮处理时读取聚合特征
- 调用融合引擎获取最终分类
- 处理事件触发逻辑（应用切换、点击密度突增）

**修改点**:
```python
class WatcherRunner:
    def __init__(self):
        # 新增：初始化事件采集组件
        self.click_listener = ClickListener(self._on_click)
        self.event_buffer = EventBuffer()
        self.event_classifier = EventClassifier(KEYWORD_RULES)
        self.fusion_engine = FusionEngine()

    def start(self):
        # 新增：启动事件监听
        if config.ENABLE_EVENT_SOURCE:
            self.click_listener.start()

    def _process_snapshot(self, snapshot):
        # 修改：融合事件信号
        vl_result = self._classify_with_vl(snapshot)

        if config.ENABLE_EVENT_SOURCE:
            features = self.event_buffer.get_aggregated_features(
                snapshot.timestamp - 300,
                snapshot.timestamp
            )
            event_result = self.event_classifier.classify(features)
            final_result = self.fusion_engine.fuse(vl_result, event_result)
        else:
            final_result = vl_result

        return final_result
```

#### 2. Reporter 集成
**文件**: `watcher/reporter.py`（修改）

**功能要求**:
- 在日志中记录融合来源（`source=vl|event|fusion`）
- 记录融合理由
- 支持查看事件分类历史

**修改点**:
```python
def write_entry(self, result: FusionResult):
    # 新增：记录融合信息
    entry = f"{result.timestamp} [{result.category}] {result.summary}"
    if result.source != "vl":
        entry += f" (source={result.source}, reason={result.reason})"

    self.log_file.write(entry + "\n")
```

#### 3. API 集成
**文件**: `app/service.py`（修改）

**功能要求**:
- 暴露事件源状态（是否启用、权限是否可用）
- 返回最近窗口摘要
- 支持前端展示融合来源标签

**新增 API**:
```python
@app.get("/api/event-source/status")
def event_source_status():
    return {
        "enabled": config.ENABLE_EVENT_SOURCE,
        "listener_running": click_listener.is_running(),
        "permission_granted": check_accessibility_permission(),
        "recent_apps": event_buffer.get_recent_apps(limit=5)
    }

@app.get("/api/event-source/summary")
def event_source_summary():
    features = event_buffer.get_aggregated_features(
        time.time() - 300,
        time.time()
    )
    return {
        "click_count": features.click_count,
        "app_switch_count": features.app_switch_count,
        "top_app": features.top_app,
        "top_keywords": features.top_window_keywords[:5]
    }
```

#### 4. 触发逻辑
**文件**: `watcher/trigger.py`（新增）

**功能要求**:
- 检测应用切换事件
- 检测点击密度突增
- 触发补充分析（受 `MIN_SEND_INTERVAL_S` 约束）

**接口定义**:
```python
class TriggerDetector:
    def should_trigger(self, features: AggregatedFeatures) -> bool:
        """判断是否应该触发补充分析"""
        pass
```

### 验收标准
- ✅ 事件监听器随主程序启动/停止
- ✅ 融合结果正确记录到日志
- ✅ API 能返回事件源状态和摘要
- ✅ 触发逻辑不会导致 API 调用暴涨（≤ 1.3 倍）
- ✅ 关闭事件源后系统完全退回原有行为
- ✅ 集成测试验证端到端流程

### 配置项
```python
EVENT_TRIGGER_MIN_CLICKS: int = 6  # 触发阈值
EVENT_SWITCH_TRIGGER: bool = True  # 是否启用应用切换触发
MIN_SEND_INTERVAL_S: int = 60  # 最小发送间隔
```

---

## 里程碑和时间线

| 里程碑 | 负责 Agent | 交付内容 | 预计时间 |
|--------|-----------|---------|----------|
| M1: 采集可用 | Agent A | 点击监听器 + 窗口解析器 | 3 天 |
| M2: 存储可用 | Agent B | 事件缓冲器 + 持久化 | 2 天 |
| M3: 融合算法 | Agent C | 事件分类器 + 融合引擎 | 3 天 |
| M4: 系统集成 | Agent D | Runner/Reporter/API 集成 | 3 天 |
| M5: 测试调优 | 全体 | 端到端测试 + 性能调优 | 2 天 |

**总计**: 约 13 天（可并行开发，实际约 7-10 天）

---

## 验收标准（整体）

### 功能验收
- ✅ 连续运行 1 天，日志无异常中断
- ✅ 聊天/讨论场景分类准确率有可见提升（≥ 10%）
- ✅ API 调用次数增长可控（≤ 1.3 倍）
- ✅ 关闭事件源后，系统完全退回原有行为

### 性能验收
- ✅ 事件采集不影响主程序性能（CPU < 5%）
- ✅ 内存占用增长可控（< 50MB）
- ✅ 事件缓冲区不会无限增长

### 代码质量
- ✅ 单元测试覆盖率 ≥ 80%
- ✅ 集成测试覆盖主要流程
- ✅ 代码符合 PEP 8 规范
- ✅ 类型注解完整

---

## 风险和缓解措施

| 风险 | 影响 | 缓解措施 | 负责人 |
|------|------|---------|--------|
| macOS 权限问题 | 无法采集事件 | 优雅降级 + 权限检查 | Agent A |
| 事件缓冲区内存泄漏 | 程序崩溃 | 定期清理 + 大小限制 | Agent B |
| 融合算法误判 | 分类准确率下降 | 可配置权重 + A/B 测试 | Agent C |
| API 调用暴涨 | 成本失控 | 触发阈值 + 频率限制 | Agent D |

---

## 协作流程

1. **每日站会**: 同步进度，解决阻塞问题
2. **代码审查**: 每个 PR 需要至少 1 人审查
3. **集成测试**: Agent D 负责协调集成测试
4. **文档更新**: 每个 Agent 更新自己模块的文档

---

**项目负责人**: [待指定]
**开始日期**: 2026-02-10
**预计完成**: 2026-02-20
