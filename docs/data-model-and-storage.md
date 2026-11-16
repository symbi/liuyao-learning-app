# 数据模型与存储方案（V1）

本文定义两个业务边界：**课堂学习资料（包含老师案例）**与**每日卦例（个人日常数据）**。老师案例属于 Learning 项目本身，存放在现有 `liuyao-learning-app` 仓库；每日卦例目前继续由 HTML 本地保存并支持 JSON 导入/导出，未来再评估 Supabase 等独立数据库。当前阶段不新建数据仓库。

## 1. 核心原则

- 课堂案例是 Learning 学习资料的一部分，和课程笔记、规则、术语表一起维护在现有 Learning 仓库中。
- 每日卦例是个人日常数据，与课堂案例分开管理；现阶段保存在浏览器本地，支持 JSON 导入/导出。
- 导入时必须明确数据类型；不根据文件名猜测类型。
- 课堂案例中的老师原文分析必须原样保留，不由应用自动改写或覆盖。
- 课堂案例必须支持用户自行选择的分类（例如「求学」「求工作」），并可按分类筛选、搜索和浏览；分类不能替代课程编号、主题或标签。
- 每日卦例保存用户自己的每日记录；`dailyMemo` 属于每日卦例，不属于课堂案例。
- 卦象与排盘结果以导入时的快照为准。以后规则引擎升级，不静默重算或覆盖历史记录。
- JSON 使用 UTF-8；日期采用 `YYYY-MM-DD`；时间戳采用 ISO 8601。
- V1 先支持 JSON 导入/导出；GitHub 同步作为下一阶段，不在静态网页中保存 Token。

## 2. 目录规划

课堂案例放在现有 `symbi/liuyao-learning-app` 仓库中，与课程笔记和规则文档共同版本管理。建议目录：

```text
liuyao-learning-app/
├── materials/
│   ├── lessons/
│   └── class-cases/
│       ├── README.md
│       ├── 求学/
│       ├── 求工作/
│       ├── 感情/
│       └── 其他/
├── docs/
│   └── data-model-and-storage.md
└── ...
```

以上分类目录只是示例。最终分类名称以 HTML 中用户实际维护的分类清单为准；不要因为示例而预先锁定分类集合。原始录音、未整理转录稿等原始资料仍按现有 raw 资料归档流程管理；整理后的课堂案例和老师讲解归入 Learning 仓库。

每日卦例当前不要求建立 GitHub 目录或新仓库。V80 继续使用本地存储与 JSON 备份。未来如迁移到 Supabase，数据库表和访问权限再单独设计。

## 3. 共用卦象快照

两个数据类型都可以包含以下 `casting` 对象：

| 字段 | 类型 | 说明 |
|---|---|---|
| `castDate` | string | 起卦日期，YYYY-MM-DD |
| `castTime` | string/null | 有记录时保存当地时间 HH:mm |
| `timezone` | string | 例如 Asia/Tokyo |
| `calendar` | object | 年月日干支、月建、日建等起卦时快照 |
| `questionCategory` | string/null | 起卦问题分类 |
| `question` | string/null | 具体问题，可留空 |
| `originalHexagram` | object | 本卦名称、宫位等快照 |
| `changedHexagram` | object/null | 变卦快照；无变卦时为 null |
| `lines` | array | 六爻数组，固定按初爻到上爻排序 |
| `ruleSnapshot` | object/null | 规则/算法版本与必要计算快照 |

`lines` 每项建议包含 `position`（1–6）、`coinResult`、`yinYang`、`moving`、`sixRelative`、`earthlyBranch`、`sixGod`、`shiYing`。字段缺失时允许为 null；不得为了填满字段而猜测。

## 4. 课堂案例格式

单个文件代表一个课堂案例。老师的分析单独存放在 `teacherAnalysis`，作为来源内容保留；用户自己的学习笔记若以后需要添加，应放在独立字段，不能混入老师原文。

```json
{
  "schemaVersion": 1,
  "datasetType": "class-case",
  "id": "class-case-lesson-01-001",
  "title": "案例标题",
  "category": "求学",
  "lesson": {
    "number": 1,
    "date": null,
    "topic": "课程主题"
  },
  "source": {
    "type": "teacher-material",
    "fileName": "原始资料文件名",
    "reference": null
  },
  "casting": {
    "castDate": null,
    "castTime": null,
    "timezone": "Asia/Tokyo",
    "calendar": {},
    "questionCategory": null,
    "question": null,
    "originalHexagram": {},
    "changedHexagram": null,
    "lines": [],
    "ruleSnapshot": null
  },
  "teacherAnalysis": {
    "text": "老师原始分析全文",
    "format": "plain-text"
  },
  "learnerNotes": "",
  "tags": [],
  "createdAt": null,
  "updatedAt": null
}
```

`category` 是用户在 HTML 页面中为该案例选择的主分类，例如「求学」「求工作」。它应来自可维护的分类清单，而不是写死在代码里的固定枚举；列表页要能按该字段筛选。可额外使用 `tags` 做更细的关键词标记。`category` 与 `casting.questionCategory` 含义不同：前者是案例库整理分类，后者是起卦时的问题分类。

注意：示例中的空对象/空数组是结构占位，不代表真实案例数据。导入真实案例时，保留原始材料中确实存在的内容；没有提供的信息保持 null 或省略。

## 5. 每日卦例格式

每日卦例以起卦日期为主要索引。`dailyMemo` 是唯一的自由记录区，用来写当天发生的事情、观察和复盘；不再拆成早间/晚间字段。

```json
{
  "schemaVersion": 1,
  "datasetType": "daily-record",
  "id": "daily-2026-11-16",
  "castDate": "2026-11-16",
  "casting": {
    "castDate": "2026-11-16",
    "castTime": null,
    "timezone": "Asia/Tokyo",
    "calendar": {},
    "questionCategory": "今日运势（每日卦）",
    "question": null,
    "originalHexagram": {},
    "changedHexagram": null,
    "lines": [],
    "ruleSnapshot": null
  },
  "dailyMemo": "",
  "tags": [],
  "createdAt": null,
  "updatedAt": null
}
```

同一天的记录应更新同一条记录，不因补写 Memo 而创建重复记录。若用户明确需要同一天多次起卦，后续再扩展为同日多条记录，并为每条记录使用独立 ID。

## 6. 批量导入/导出包

单条记录文件可直接导入。批量导入/导出使用以下外层结构：

```json
{
  "schemaVersion": 1,
  "datasetType": "class-cases",
  "exportedAt": "2026-11-16T15:00:00+09:00",
  "records": []
}
```

每日卦例批次的 `datasetType` 必须是 `daily-records`。一次导入只能对应一个数据集；课堂案例包不能导入每日卦例入口，反之亦然。导入前先校验类型、版本、必需字段和重复 ID，并提供预览；默认不静默覆盖已有记录。

## 7. V80 兼容与迁移

当前 V80 本地记录使用既有应用快照结构，包含 `dailyMemo`，JSON 导出版本为 schemaVersion 10。V1 数据仓库格式是独立的持久化格式，不应直接把 V80 导出文件当作 V1 单条记录。

迁移时需要一个显式转换步骤：
1. 识别 V80 导出包及其 schemaVersion。
2. 将 V80 每条每日记录转换为 `datasetType: daily-record`。
3. 保留原始卦象、六爻、日历、规则快照及 `dailyMemo`。
4. 生成稳定 ID；同日期已有记录时先提示冲突，不自动覆盖。
5. 转换完成后做记录数量、日期、六爻数量和 Memo 内容核对。

课堂案例导入使用独立转换器，不能将每日记录转换器套用到课堂案例。

## 8. 仓库与未来数据库边界

- `liuyao-learning-app`（现有 Learning 仓库）：网页代码、课程笔记、整理后的老师课堂案例、规则、术语表、数据格式说明和可公开的学习资料。
- 现有 raw 资料仓库继续用于原始录音、未经整理的转录稿和来源文件；整理后的课堂案例归入 Learning 仓库。
- 每日卦例：当前留在 V80 浏览器本地存储，使用 JSON 导入/导出做备份；不提交到 Public Learning 仓库。
- 未来可评估 Supabase 等数据库保存每日卦例。届时再设计用户身份验证、表结构、访问控制、备份与迁移方案。
- GitHub Token、Supabase service-role key 或其他密钥不得写入 HTML、JavaScript、JSON 数据文件或 Public 仓库。
- 现阶段不实现 GitHub 数据同步，也不创建 `liuyao-learning-data` 新仓库。

## 9. V1 实施顺序

1. 定义课堂案例 JSON 格式，增加可配置的 `category` 字段。
2. 在现有 Learning 仓库建立课堂案例目录与分类说明。
3. 实现 HTML 中课堂案例分类选择、导入、列表筛选、搜索和详情查看。
4. 保持每日卦例现有本地存储、日期列表、Memo 编辑和 JSON 导入/导出。
5. 增加批量导出、备份与重复记录冲突提示。
6. 等每日数据积累和使用需求明确后，再评估 Supabase 等数据库；不提前引入后端复杂度。
