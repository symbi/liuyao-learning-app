# 六爻起卦与排盘网页：项目主计划 v1

> 本文是项目入口与实施约定。六爻规则以课程资料和 `docs/rules-status.md` 为准；未核实内容不得被模型或程序静默补齐。

## 1. 产品目标

制作一个轻量的六爻学习与排盘工具。核心用途包括：正确生成和保存卦盘；按用户课堂所学检索相关规则和老师案例；在有来源依据的前提下辅助分析每日卦例；通过 Memo 记录实际情况并事后复盘。

## 2. 仓库与资料分工

- Public Learning：`symbi/liuyao-learning-app`，保存网页代码、自写课程笔记、规则状态、整理后的课堂案例和外部项目参考目录。
- Private raw：`symbi/liuyao-learning-raw`，保存课堂原始录音、ASR 转录及个人每日卦例数据。
- 原始 ASR 可能有术语识别错误，只作为回查老师讲解的参考；整理后的课堂总结和独立案例放在 Public Learning。
- 课堂总结、案例、原始 ASR 用相同课次编号 `lesson-XX` 自动关联。
- 每日卦例不进入 Public 仓库；保存与 AI 读取方案见 [每日卦例 GitHub 保存与 AI 分析方案](data-model-and-storage.md)。

## 3. 每日卦例的保存行为

- 默认类型为「今日运势（每日卦）」；默认问题栏留空。
- 每个日本当地日期（`Asia/Tokyo`）只有一条默认每日运势记录。
- 点击保存后，按日期写入 Private raw 仓库的 `daily-records/YYYY/MM/YYYY-MM-DD.json`。
- 同一天再次打开记录或保存 Memo，应读取并更新同一条 `dailyFortune`，不可生成重复条目。
- 同一天的额外问题记录放进该日期文件的 `additionalQuestions` 列表，每条有独立 ID、Category、问题文字和卦盘快照。
- GitHub 是持久化目标；只有后端确认写入成功才能显示 GitHub 保存成功。网络失败可本地暂存，但要清楚标记尚未同步。
- 不把每日卦例写入 Public Learning 仓库。

## 4. GitHub 授权与安全

- HTML 前端不能携带个人 PAT、GitHub App 私钥或 Client Secret。
- 使用最小权限 GitHub App，只安装到 Private raw 仓库，只授予 Repository contents Read and write。
- 用小型 Serverless Worker 处理 OAuth code exchange、用户身份验证、Token refresh 和 GitHub Contents API 读写代理。
- Worker 校验用户身份并限制只允许操作 `daily-records/` 路径。
- 更新已存在 JSON 文件时带上 GitHub 当前 blob SHA；SHA 冲突时重新读取并合并，不静默覆盖。
- 详细设计及当前实现状态见 `docs/data-model-and-storage.md`。在安全授权中转完成前，不向 HTML 加入 Token 输入框作为替代。

## 5. ChatGPT 辅助分析流程

当用户请求分析当天或指定日期的卦时：

1. 使用已连接的 GitHub 连接读取 Private raw 对应日期的 JSON。
2. 核对每日运势或指定额外问题的卦盘事实；不凭模型记忆重算或覆盖盘面。
3. 按 Category / Real Question 检索 Public Learning 中的相关课堂笔记、规则状态和课堂案例。
4. 外部六爻项目仅作交叉参考；如与老师课程不一致，明确指出分歧，不静默取代课程规则。
5. 输出时标明课程明确、课堂案例、外部参考和 AI 综合推理。
6. 用户以后补充 Memo 或实际情况时，再读取同一日期记录进行复盘。

GitHub 文件更新不会自行启动 ChatGPT 分析；用户提出分析请求时再检索。

## 6. 开发顺序

1. 保持 V80 已验证的排盘、日期、Memo 和 JSON 导入/导出逻辑。
2. 确定每日 JSON 结构和按日唯一记录行为。
3. 建立最小权限 GitHub App 和 Serverless Worker。
4. 实现当天文件读取、创建和更新。
5. 实现额外问题列表。
6. 测试 GitHub 不可用、授权撤销、跨设备更新和 SHA 冲突。
7. 接通 ChatGPT GitHub 检索与来源明确的分析流程。
8. 未来再评估是否需要 Supabase 或向量检索；当前不提前增加数据库和 RAG 复杂度。

## 7. 通用工程原则

- 先读现有 README、规则状态、课程笔记、案例与外部参考，再修改项目。
- 排盘计算必须确定性、可测试；AI 分析和排盘事实分层。
- 课程明确、外部参考、推断、有分歧分别标记。
- 不提交未授权原始课程材料、秘密、令牌、个人隐私或公司资料到 Public。
- 所有记录保留原始日期、时区、规则快照和来源信息，以便复核。
