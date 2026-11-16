# 每日卦例 GitHub 保存与 AI 分析方案

## 1. 两类数据仍然分开

### 课堂学习资料

老师的理论课和案例课都属于 Learning 项目，继续使用现有两个仓库：

- Private `liuyao-learning-raw`：课堂录音、原始 ASR 转录和未经整理的来源资料。
- Public `liuyao-learning-app`：每课整理总结、单独课堂案例、规则、参考项目和应用代码。

课堂案例仍按课次关联：原始 ASR、每课总结、独立案例使用相同的 `lesson-XX` 编号。ASR 仅作为可能不准确的参考；老师结论和整理者推断要区分。

### 每日个人卦例

每日卦例是个人数据，保存到现有 Private `liuyao-learning-raw` 仓库的独立目录 `daily-records/`。不放入 Public Learning 仓库，不新建数据仓库。当前阶段以 GitHub 作为持久化位置，不急着迁移 Supabase。

## 2. 每日记录的使用方式

HTML 默认打开当天的「今日运势（每日卦）」：

- Category 默认是「今日运势（每日卦）」。
- 问题栏留空，不要求写具体问题。
- 同一天只允许有一条默认运势卦。
- 点击保存时，按日本当地日期 `Asia/Tokyo` 写入当天文件。
- 如果当天记录已经存在，打开时读取原记录；再次保存则更新同一条记录，不创建重复记录。
- 当天的自由 Memo 与每日运势记录一起保存；以后重新打开仍能恢复。

若当天还有额外问题（例如求工作、求财、某个项目），则在同一天文件的 `additionalQuestions` 中新增独立记录。额外问题有自己的 Category、问题文字和卦盘，不覆盖当天默认运势卦。

## 3. GitHub 文件路径：一天一个文件

建议结构：

```text
liuyao-learning-raw/              # Private
├── lessons/                      # 课堂原始录音与 ASR
│   └── lesson-XX/
│       └── transcript-asr-raw.txt
└── daily-records/                 # 个人每日卦例
    └── 2026/
        └── 11/
            └── 2026-11-16.json
```

一天一个文件，文件内同时保存当天唯一的每日运势卦、额外问题列表和每日 Memo。这样按日期即可直接定位完整记录，也方便 ChatGPT 一次读取。

## 4. 每日 JSON 结构示例

```json
{
  "schemaVersion": 1,
  "recordDate": "2026-11-16",
  "timezone": "Asia/Tokyo",
  "dailyFortune": {
    "id": "daily-2026-11-16",
    "category": "今日运势（每日卦）",
    "question": "",
    "casting": {
      "castDate": "2026-11-16",
      "calendar": {},
      "originalHexagram": {},
      "changedHexagram": null,
      "lines": [],
      "ruleSnapshot": null
    },
    "dailyMemo": ""
  },
  "additionalQuestions": [
    {
      "id": "question-unique-id",
      "category": "求工作",
      "question": "这份工作是否适合我？",
      "casting": {
        "castDate": "2026-11-16",
        "calendar": {},
        "originalHexagram": {},
        "changedHexagram": null,
        "lines": [],
        "ruleSnapshot": null
      }
    }
  ],
  "createdAt": "2026-11-16T09:00:00+09:00",
  "updatedAt": "2026-11-16T09:00:00+09:00"
}
```

示例中的空对象和空数组只是结构占位。真实保存时使用 V80 已经计算出的卦盘快照；没有可靠值的字段不补造。

## 5. HTML 保存和读取流程

### 页面打开/切换日期

1. 以 `Asia/Tokyo` 取得当天日期。
2. 通过安全的 GitHub 数据接口读取对应日期文件。
3. 文件存在：恢复每日运势卦、Memo 和额外问题。
4. 文件不存在：显示当天新的空白每日运势起卦表。
5. 切换历史日期时，先读取该日期的 GitHub 文件；不能把当前未保存编辑静默丢弃。

### 保存每日运势卦

1. 读取当前日期文件（若存在）。
2. 将 `dailyFortune` 更新为当前排盘；Category 仍为「今日运势（每日卦）」，问题保持空白。
3. 保留文件内原有的 `additionalQuestions`。
4. 写回当天同一个 JSON 文件。
5. 只有 GitHub 返回成功后才显示「已保存到 GitHub」；若网络失败，只能显示「本地暂存／尚未同步」，并允许重试。

### 保存额外问题

1. 新增一个独立 ID 的问题记录。
2. 写入自己的 Category、真实问题和卦盘快照。
3. 保存回同一天的文件，但不覆盖 `dailyFortune`。
4. 修改某条额外问题时按 ID 更新该条记录。

同一个日期文件可能在不同设备上被编辑。写回前需使用 GitHub 文件当前的 blob SHA；若 SHA 冲突，先重新读取并合并，再提示用户确认，不能静默覆盖新内容。

## 6. ChatGPT 怎样直接读取

当用户说「分析我今天的卦」或指定某个日期时：

1. 通过已连接并获准访问 Private 仓库的 GitHub 连接器，读取 `daily-records/YYYY/MM/YYYY-MM-DD.json`。
2. 先读取其中的每日运势卦；如用户指定额外问题，则读取对应问题记录。
3. 根据 Category / Real Question 检索 Public Learning 仓库中的相关课程笔记和课堂案例。
4. 检索相关规则状态和外部六爻项目参考。
5. 将「课程明确」「老师课堂案例」「外部参考」「AI 综合推理」分开说明，附上相应来源。
6. 盘面事实以已保存的结构化排盘为依据，不让模型凭记忆重新计算并覆盖排盘。

这意味着用户不必每次下载 JSON 再上传到 ChatGPT。前提是 ChatGPT 的 GitHub 连接仍然有效，并有权读取该 Private 仓库；若连接失效，需要重新连接或授权。

GitHub 保存成功本身不会自动触发 ChatGPT 开始分析。用户发出分析请求时，ChatGPT 再读取对应日期记录。

## 7. GitHub 写入的安全方式

静态 HTML 可以展示页面，但不能把 GitHub Token、App 私钥或 Client Secret 写在 HTML/JavaScript 中。任何能访问页面的人都可能检查前端代码和浏览器存储。

建议使用一个很小的 Serverless 授权中转（例如 Cloudflare Worker）：

- 创建 GitHub App，只安装到 `symbi/liuyao-learning-raw` 这个 Private 仓库。
- App 权限只开 Repository contents：Read and write。
- 使用 GitHub OAuth 授权登录，并验证登录账户确实是仓库所有者。
- OAuth code exchange、Client Secret、Token refresh 等敏感操作在 Worker 服务端完成。
- HTML 只调用 Worker 的读取/保存接口，不接触 App 私钥或 Client Secret。
- Worker 只允许读写 `daily-records/` 路径，不允许网页调用者任意操作整个仓库。
- Token 采用短期授权并安全保存/续期；用户可撤销 App 授权。

GitHub Contents API 支持 GitHub App user access token，并要求仓库 Contents 写入权限；文件更新需要带上原文件 SHA。权限和授权流程必须按 GitHub 当前文档实现。

**不要使用把个人 Access Token 直接粘贴进 HTML 或长期保存在 localStorage 的简化方案。** 这会把整个私有仓库暴露给前端凭据泄漏风险。

## 8. 实施阶段

1. 先保持 V80 的排盘、六爻计算、每日 Memo 和本地备份逻辑不变。
2. 为每日记录增加按日本日期读取的 GitHub JSON 数据模型。
3. 配置 GitHub App 和一个最小 Worker 授权/代理接口。
4. 实现默认每日运势卦的按日唯一保存、读取和更新。
5. 实现额外问题列表的新增、读取和更新。
6. ChatGPT 通过 GitHub 连接器直接读取 Private 每日文件，并关联 Public 课程和案例资料。
7. 验收保存、重复打开、跨日期、额外问题、网络失败、权限撤销和 SHA 冲突情形。

暂时不做 Supabase 数据库、不做复杂 RAG / Embedding，也不把每日记录提交到 Public 仓库。等数据量和使用需求真实增长后再决定是否迁移。
