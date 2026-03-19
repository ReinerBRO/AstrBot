# V2 Connected Workspace

## 启动入口

```bash
pnpm dev:v2
```

## 本版更新

- 进度定位：累计约 43.75%
- 在 V1 基础上开放机器人接入
- 开放 Knowledge Base 和 Persona
- 系统开始从“能聊天”升级到“能接入用户并理解用户”

## Demo 上能直接看见的变化

- 左侧多出 `Platforms`
- 左侧多出 `Knowledge Base`
- 左侧多出 `Persona`
- 欢迎页顶部显示 `V2 Connected Workspace`

## 六人具体工作

1. Yi Ding（Cognitive Engine）：让认知引擎开始消费外部上下文，不再只是对话响应，而是能结合平台接入状态、Persona 和知识内容来理解“这个用户是谁、现在在什么工作场景里”。
2. Jinchang Zhu（Agent Memory System）：把 Knowledge Base 和 Persona 作为记忆系统的第一批显式输入面，形成从聊天历史走向 Episodic/Semantic/Profile 三类信息的过渡。
3. Chenghao Wu（Semantic Recommendation）：在 V2 先把 user interest profile 的数据入口铺出来，让后续 Graph-Enhanced Reranking 不再是空转，而是有 Persona 和 KB 作为推荐依据。
4. Xiaojian Nie（Visual Workflow）：开放 Platforms 这一层，先把用户软件环境接进来，为后面的视觉示教、事件解析和执行脚本学习建立入口，而不是直接跳到自动化。
5. Ying Liu（Behavior Alignment）：围绕“接入用户数据”补第一层行为边界，确保平台接入、知识导入、画像配置这些操作还处在人工可控阶段，不让系统过早进入主动执行。
6. Yaxin Li（Security and Privacy Framework）：把这一版的安全重点放在平台凭证和知识导入边界上，允许系统开始接入用户环境，但仍然不开放插件和外部工具生态。

## 组会直接可说

- 整组：`V2 相比 V1，核心升级是接入能力和用户理解能力开始真正出现在界面里。`
- Yi Ding：`我这一版让认知引擎开始结合平台接入、Persona 和知识内容理解用户，而不是只做纯聊天。`
- Jinchang Zhu：`我这一版把记忆系统的输入面打开了，Knowledge Base 和 Persona 可以开始为长期记忆提供材料。`
- Chenghao Wu：`我这一版重点是把推荐系统需要的兴趣画像入口先铺出来，为后续主动推荐做准备。`
- Xiaojian Nie：`我这一版先把平台接入层接进来，为后面视觉工作流学习真实软件环境。`
- Ying Liu：`我这一版的重点是接入阶段的行为边界，保证系统先学会理解用户，再考虑主动执行。`
- Yaxin Li：`我这一版主要盯平台凭证和知识导入边界，让系统开始接入用户环境但不扩大攻击面。`
