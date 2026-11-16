# 数据模型与导入格式（V1）

本文定义两类彼此隔离的数据集：**课堂案例**与**每日卦例**。两者可以共享卦象快照字段，但不共用记录列表、导入入口或业务用途。

## 1. 核心原则

- `class-cases` 与 `daily-records` 是两个独立数据集。
- 导入时必须明确数据集类型；不根据文件名猜测类型。
- 课堂案例中的老师原文分析必须原样保留，不由应用自动改写或覆盖。
- 每日卦例保存用户自己的每日记录；Memo 属于每日卦例，不属于课堂案例。
- 卦象与排盘结果以导入时的快照为准。以后规则引擎升级，不静默重算或覆盖历史记录。
- JSON 使用 UTF-8；日期采用 `YYYY-MM-DD`；时间戳采用 ISO 8601。
- V1 先支持 JSON 导入/导出；GitHub 同步作为下一阶段，不在静态网页中保存 Token。

## 2. 目录规划

私有数据仓库建议命名为 `symbi/liuyao-learning-data`：

```text
liuyao-learning-data/                 # Private
├── README.md
├── schemas/
│   ├── class-case.schema.json
│   └── daily-record.schema.json
├── class-cases/
│   ├── lesson-01/
│   │   └── case-001.json
│   ├── lesson-02/
│   └── lesson-03/
├── daily-records/
│   └── 2026/
│       └── 2026-11/
│           └── 2026-11-16.json
└── backups/
    ├── class-cases/
    └── daily-records/
```

课堂案例按课程组织；每日卦例按起卦日期组织。备份目录只存定期导出的备份，不作为应用日常读取的主目录。

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

## 8. 同步与安全边界

- `liuyao-learning-app`（Public）：网页代码、公开文档、JSON 格式说明和不含个人内容的示例。
- `liuyao-learning-data`（Private）：课堂案例原始内容、每日卦例、Memo 和备份。
- GitHub Token、OAuth 凭据或其他密钥不得写入 HTML、JavaScript、JSON 数据文件或 Public 仓库。
- 在安全授权方案完成前，应用只做本地保存和 JSON 导入/导出；用户可手动备份到 Private 仓库。
- 后续 GitHub 同步必须区分两个数据集的读写路径，并提供冲突检测与恢复机制。

## 9. V1 实施顺序

1. 建立两个独立 JSON Schema，并用真实 V80 导出样本核对映射。
2. 建立 Private 数据仓库及目录骨架。
3. 实现课堂案例独立导入、列表、搜索和详情查看。
4. 实现每日卦例独立导入、日期列表、打开编辑和 Memo 保存。
5. 增加批量导出、备份与重复记录冲突提示。
6. 最后再设计 GitHub 安全授权和同步。
