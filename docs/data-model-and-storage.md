# 学习案例与每日卦例：课次关联方案

## 1. 两条独立的数据线

### 课堂学习资料

老师的课堂内容（包括理论课和后续案例课）都属于 Learning 项目，继续使用现有两个仓库：

- Private `liuyao-learning-raw`：录音、原始 ASR 转录和未经整理的来源资料。
- Public `liuyao-learning-app`：每课整理总结、独立案例记录、规则和学习 App。

### 每日卦例

每日卦例是个人日常数据，与课堂资料分开。当前继续使用 V80 浏览器本地保存和 JSON 导入/导出；未来再评估 Supabase 等数据库。本阶段不把每日卦例提交到 Public Learning 仓库。

## 2. 一堂案例课的三份资料

同一堂课的资料使用相同课次编号 `lesson-XX`：

| 内容 | 仓库与路径 | 说明 |
|---|---|---|
| 录音转文字（ASR） | Private raw：`lessons/lesson-XX/transcript-asr-raw.txt` | 原始参考，可能存在错字、漏字和术语识别错误 |
| 每课整理总结 | Public Learning：`docs/lessons/lesson-XX-notes-v0.1.md` | 用户提供或确认的该课总结，保留课程主题、讲解脉络和待核对内容 |
| 单独案例 | Public Learning：`materials/class-cases/lesson-XX/case-001.json` | 一课可以有多个案例，按 case-001、case-002 递增 |

原始 ASR 文件沿用 Private raw 仓库现有的 `lessons/lesson-XX/` 目录约定，不另建仓库，也不把原始转录复制进 Public 仓库。

## 3. HTML 中的案例标记

在 HTML 里录入或整理一个案例时，只需要这些业务信息：

1. **类型**：标记为「课堂案例」。
2. **Category**：选择案例分类，例如「求学」「求工作」「求财」。
3. **Tag / Real Question**：一个可选文字栏，填写简短 tag，或当事人真正提出的问题。
4. **案例内容**：老师的案例解说；有可靠资料时附卦盘，没有的部分不补造。

课次编号由当前整理的课程/目标文件夹确定，不要求用户另外维护一套课程分类。Category 不由课次自动推断；同一课可以有不同 Category。

## 4. 单个案例的数据格式

案例文件放入对应课次文件夹。目录本身已经说明来源课次，所以不必再要求额外填写一套重复的课次元数据。

```json
{
  "schemaVersion": 1,
  "recordType": "class-case",
  "id": "case-001",
  "category": "求工作",
  "tagOrRealQuestion": "去这家公司工作怎么样？",
  "casting": null,
  "teacherAnalysis": "根据课堂资料整理的老师分析摘要和结论"
}
```

- `recordType` 和 `id` 是程序识别与去重所需字段，可以自动生成。
- `category` 和 `tagOrRealQuestion` 是 HTML 中需要你选择/填写的两个简洁字段。
- `casting` 是可选卦盘快照，只记录资料中实际有的内容。
- `teacherAnalysis` 保存根据课堂资料整理的老师分析摘要和结论；原始 ASR 全文保留在 Private raw。老师的结论、整理者归纳和不确定之处要能区分。

不增加必填的多个 tags、独立标题、学习者笔记或复杂来源分类。案例列表按 Category 筛选，并可搜索 Tag / Real Question。

## 5. 自动按课次关联

这是本项目后续整理案例课时要遵循的固定流程：

1. 读取待整理的课次编号，例如 `lesson-18`。
2. 到 Private raw 的 `lessons/lesson-18/` 查找对应 ASR 转录（若已归档）。
3. 到 Public Learning 的 `materials/class-cases/lesson-18/` 读取该课所有案例文件。
4. 读取 `docs/lessons/lesson-18-notes-*.md` 的该课总结。
5. 按照同一课次把总结、案例记录和 ASR 参考对应起来，生成/更新该课的学习总结，并在总结中列出该课案例的链接及简要内容。

因此，第十八课的总结只需要按编号查找第十八课的案例文件夹；不需要你在每份总结里手动重新录入每个案例。某课的案例文件夹没有内容时，明确显示「尚无独立案例记录」，不能虚构案例。

### 整理时的证据顺序

- 用户已确认的课程总结和单独案例记录，是整理后的主要依据。
- ASR 转录是辅助参考，可能不准确；遇到听写疑点、术语不清或来源之间不一致时，保留疑点并标记「待核对」。
- 不可以为了让总结看起来完整而自行修正老师原意、补齐缺失卦盘，或把模型推断写成老师的结论。
- 案例笔记有比 ASR 更具体的卦盘或老师结论时，可以在总结中引用案例笔记；如两者冲突，指出冲突，不静默覆盖。

### 当前自动化状态

目前 GitHub 目录和课次命名约定已经明确；自动扫描、汇总和反向链接功能尚未写入 HTML 或 GitHub Actions。后续实现时，应按以上规则用课次编号自动发现对应文件，而不是要求用户手动维护重复链接。

## 6. 与现有理论课笔记的关系

现有 `docs/lessons/` 中的第五至第十七课笔记继续保留。未来的案例课可以继续使用同样的课次编号规则：

- 每课总结仍放在 `docs/lessons/`。
- 每课独立案例放在 `materials/class-cases/lesson-XX/`。
- 每课原始 ASR 仍放在 Private raw 的 `lessons/lesson-XX/`。
- 课程笔记保留整堂课的知识脉络；案例文件保存单个案例，避免两份文件重复粘贴全部内容。

## 7. 每日卦例：暂时维持现状

- V80 的每日记录继续使用浏览器本地存储。
- 每条记录保留起卦日期、卦盘快照和一个 `dailyMemo` 自由记录栏。
- JSON 导入/导出用于备份和迁移。
- 每日卦例不进入 Public Learning 仓库，也不与老师课堂案例混在同一个列表。
- 未来若迁移 Supabase，再另行设计数据库表、身份验证和访问权限；现在不提前增加后端。

## 8. 当前实施顺序

1. 沿用现有 raw 仓库的 `lessons/lesson-XX/` 归档原始 ASR 转录。
2. 在 Learning 仓库按课次建立 `materials/class-cases/lesson-XX/`，存放这堂课的独立案例。
3. 每课总结继续放在 `docs/lessons/`。
4. 后续实现按课次自动查找、匹配案例，并在课程总结中生成链接和案例摘要。
5. 每日卦例保持 V80 本地保存与 JSON 备份，不在本阶段接数据库。
