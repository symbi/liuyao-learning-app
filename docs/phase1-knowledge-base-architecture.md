# Phase 1：知识库与课堂案例架构规划

> 本文记录知识库的概念模型。2026-11-18 起，关于实际部署位置、Importer 增量策略、Gemini 的两种模型职责、Graph Builder 是否必须、谁负责最终分析及是否需要 Supabase，以 [Phase 1 实际运行架构与工作流](phase1-operating-model.md) 为最新执行决策。

## 1. 目标与边界

Phase 1 在验证现有 HTML 排卦、每日记录和 GitHub 保存流程的同时，逐步建立可追溯的六爻学习知识库。

本阶段建议采用：

- **GitHub**：继续保存应用代码、整理后的课程资料、案例 JSON、规则文档和项目规划。
- **Private raw 仓库**：保存原始录音、未经校对的 ASR 转写稿、原始 PDF 等来源材料。
- **Neo4j AuraDB Free**：作为逐步建设的知识图谱数据库，保存课程、知识片段、概念、规则、案例及它们之间的关系；在确认当前免费实例支持范围后使用 Neo4j 原生向量索引。
- **Gemini API**：可用于候选知识抽取和 Embedding。API Key 只能放在服务端/受保护的导入环境，不得放入 HTML、浏览器代码或 Public GitHub。
- **来源追溯与质量标注**：用户不需要逐条审核 AI 抽取的节点和关系。Importer 自动保留来源文档、Chunk、课次、抽取方式和不确定性；分析时必须引用来源并区分老师课堂内容、ASR 线索、个人 Memo、外部资料和 AI 推断。对来源冲突或低置信内容明确提示，不自动将 AI 抽取提升为已确认课程规则。

Phase 1 先不要求把 Neo4j 直接接入当前 HTML，也不要求立即部署自建 VPS、Supabase 或完整后端。先验证数据模型、导入、来源追溯和检索。当前 Cloudflare Pages + GitHub 的每日记录流程保持独立，不因知识库试验而被破坏。

## 2. Phase 1 总体数据流

```text
课程资料入口
  ├─ 原始录音 / 原始 ASR / 原始 PDF
  │    └─ Private: liuyao-learning-raw
  ├─ ChatGPT 整理校对后的课程笔记
  │    └─ Public: liuyao-learning-app/docs/lessons/
  └─ HTML 中录入的卦例 + 用户 memo
       └─ Public: liuyao-learning-app/materials/class-cases/
            或个人练习案例目录（按后续统一的数据模型保存）

                    ↓ 增量导入（只处理新增/变更内容）

        导入与预处理
        - 文件哈希 / 文档 ID / chunk ID 去重
        - 保留课程编号、文件路径、页码或时间戳
        - 区分原文、人工整理、AI 摘要和用户 memo
                    ↓
        Gemini API（可选）
        - 候选概念、关系、规则、案例摘要抽取
        - Embedding 向量生成
                    ↓
        Neo4j AuraDB
        - 课程、来源文档、文本片段
        - 六爻概念、规则、案例
        - 节点之间的关系
        - 向量索引 / 相似内容检索
                    ↓
        人工审核与确认
        - 核对老师讲解和来源
        - 标记确认、待核对、存在分歧或已废止
```

说明：Embedding 是文本的向量表示，用于相似内容检索；它本身不负责判断规则是否正确，也不会替代原文。检索到的原文/笔记再交给 LLM 辅助回答。

## 3. HTML 卦例必须区分的两种类型

HTML 的卦例录入界面应提供明确的「案例类型」选择，不能只靠 memo 内容或文件夹位置猜测。

### A. 课堂正式案例（Classroom Reference Case）

这是老师在课堂上实际讲解、分析过的案例，可作为课程学习和后续分析的参考依据。

录入时建议包含：

- 卦盘快照：保存当时的六爻数据，不依赖以后重新计算。
- 课次：例如 `lesson-11`。
- 案例标题或简短主题：可选。
- 老师分析 memo：用户根据课堂讲解记录的重点、判断过程、结论和例外。
- 对应课程笔记：链接到整理后的课堂笔记。
- 来源定位：如果知道，可记录录音时间戳、转写段落、讲义页码等。
- 不确定项：ASR 识别错误、听不清或尚未确认的内容。

课堂案例类型还应有独立的审核状态：

- `draft`：刚录入，尚未整理完成。
- `needs_review`：有内容或来源需要核对。
- `verified`：已对照课程材料核实，可作为已确认的课堂参考案例。
- `disputed`：不同课堂材料或老师说法之间存在需要保留的分歧。

**只有 `verified` 的课堂案例才进入“已核实课堂参考案例”检索集合。** 刚按下“这是课堂案例”按钮，不代表案例内容已经自动核实。

### B. 个人练习案例（Personal Practice Case）

这是用户自己排卦、尝试分析或日常记录的案例。它有学习价值，也可以保存 memo 和后续结果，但不能被系统误认为老师课堂讲授过的案例。

个人练习案例可使用状态：

- `draft`：草稿。
- `completed`：已完成当次记录。
- `reviewed`：后来复盘过。

个人练习案例可以在未来用于个人复盘或观察，但默认不进入“老师课堂参考案例”集合，也不能用来证明某条课程规则。

## 4. 建议的数据字段

建议案例 JSON 至少能表达以下信息（字段名可在实现时调整，但语义应保留）：

```json
{
  "schemaVersion": 1,
  "recordType": "case",
  "id": "case-unique-id",
  "caseType": "classroom_reference",
  "reviewStatus": "needs_review",
  "title": "",
  "lessonId": "lesson-11",
  "category": "",
  "question": "",
  "casting": {},
  "teacherAnalysisMemo": "",
  "personalAnalysisMemo": "",
  "sourceRefs": [
    {
      "kind": "lesson_notes",
      "path": "docs/lessons/lesson-11-notes.md"
    },
    {
      "kind": "raw_transcript",
      "repository": "symbi/liuyao-learning-raw",
      "path": "lessons/lesson-11/transcript-asr-raw.txt",
      "visibility": "private",
      "timestampOrLocation": ""
    }
  ],
  "uncertainties": [],
  "createdAt": "",
  "updatedAt": ""
}
```

注意：

- 上面是结构示意，不代表当前 HTML 已经实现这些字段。
- Public 案例 JSON 不应复制整份原始录音或未经校对的 ASR。只保留必要的来源引用和经过整理的摘要。
- 如果 raw 仓库是 Private，公开案例中的引用只是来源定位，不应让导入程序或网页假设匿名用户可以读取它。
- 如果用户 memo 含私人信息，应先考虑 Public 仓库的公开可见性；Phase 1 的 Public 数据不是私密日记。

## 5. 课程录音、ASR 与课堂案例如何关联

同一课的不同资料通过统一课次 ID 关联，例如 `lesson-11`：

1. 原始录音和未经校对的 ASR 存在 Private raw 仓库。
2. ChatGPT 整理后的课程笔记存在 Public Learning 的 `docs/lessons/`。
3. 从课堂讲解中拆出的每个独立案例，存在 `materials/class-cases/lesson-11/`。
4. 案例 JSON 记录老师分析 memo，并引用对应课程笔记及可用的原始转写位置。
5. ASR 仅是回查线索；遇到术语、数字、爻位或判断不确定时必须标注待核对，不能直接当作老师定论。

课堂讲过的案例和课程理论笔记是两种不同资料：笔记表达一课的知识整理，案例表达一件具体事情、一个具体卦盘和老师对它的分析。两者应互相链接，而不是把案例全部塞进一篇课程笔记。

## 6. Neo4j 知识图谱建议实体

初期不必设计得过度复杂，可从以下节点开始：

- `Lesson`：课程课次。
- `SourceDocument`：课程笔记、讲义或其他来源文件。
- `Chunk`：可检索的文本片段，带来源定位。
- `Concept`：六亲、六神、月建、日辰、暗动等概念。
- `Rule`：从课程资料整理出的规则，带状态、版本和出处。
- `Case`：课堂正式案例或个人练习案例，带类型与审核状态。

关系示例：

- `Lesson -[:HAS_DOCUMENT]-> SourceDocument`
- `SourceDocument -[:HAS_CHUNK]-> Chunk`
- `Chunk -[:MENTIONS]-> Concept`
- `Rule -[:SUPPORTED_BY]-> Chunk`
- `Case -[:TAUGHT_IN]-> Lesson`
- `Case -[:ILLUSTRATES]-> Rule`
- `Case -[:REFERENCES]-> Chunk`

AI 自动抽取的节点和关系先标记为候选，不能因为它们已经写入图数据库就视为课程事实。规则需要记录来源、审核状态、版本和适用条件；规则修订时保留旧版本及其历史，不静默覆盖。

## 7. 增量更新原则

每次新增资料只处理新增或变化部分：

- 新增第 12 课：只导入第 12 课及其案例。
- 新增一条课堂案例：只新增该案例，并连接对应课次和笔记。
- 新增个人练习：只新增个人练习案例，不改变课堂案例集合。
- 修正规则：创建新版本并把旧版本标记为被替代，保留来源和修改历史。
- 新增反例：新增案例及关系，不删除或覆盖原有案例。
- 文件未变化：通过文档哈希和 chunk ID 跳过重复导入。

## 8. 分阶段实施

### Phase 1A：先稳定资料结构

- 确认课程、课堂案例、个人练习案例的文件组织与字段。
- 明确课堂案例的类型和审核状态。
- 保留老师 memo、卦盘快照、课程笔记链接和来源定位。
- 不改变当前排盘算法和每日记录功能。

### Phase 1B：建立 Neo4j 原型

- 创建 Neo4j AuraDB Free 实例。
- 先导入少量已整理课程笔记和少量已核实课堂案例。
- 验证节点、关系、来源追溯和增量更新。
- 确认 AuraDB 当前套餐的存储、索引和备份限制；原始资料仍以 GitHub 仓库为准。

### Phase 1C：加入候选抽取与语义检索

- 配置 Gemini API 或其他经确认的模型服务。
- 先对少量资料做概念/关系抽取和 Embedding 试验。
- 人工检查中文六爻术语、ASR 错误和抽取质量。
- 验证向量检索能否找到相关课程段落和案例。
- 只有在数据质量可控后，才扩大批量导入。

### 后续阶段（不属于 Phase 1 的前置条件）

- 用后端 API / GraphRAG 将 Neo4j 检索能力接入 HTML。
- 用确定性代码实现经课程核实的六爻规则引擎；规则计算不需要 LLM API Key。
- 将 Supabase 等数据库用于登录、用户权限、私人 memo 和个人记录隔离。
- 由 GraphRAG 负责检索相关知识，LLM 负责基于检索内容组织解释；二者都不能替代规则引擎和人工审核。

## 9. 不可违反的知识质量原则

1. 老师课堂原始讲解和核实过的课堂笔记是课程规则的主要依据。
2. 原始 ASR 可能错误，不得将未经核实的转写直接标为老师定论。
3. 课堂正式案例与个人练习案例必须分开存储、筛选和展示。
4. “课堂案例”标签说明其来源类别；“已核实”状态才说明它经过核对。
5. 外部流派资料必须单独标注来源，不得混写成老师课程规则。
6. AI 推断、候选抽取、用户 memo 和老师明确讲解必须能够区分。
7. 每条规则和重要案例尽可能保留来源路径、课次、页码/时间戳或原文片段。
8. 不因接入图数据库或向量检索而改变现有 HTML 排盘结果。
