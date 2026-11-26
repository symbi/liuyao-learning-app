# M4c 试点导入操作与故障处理手册

> 本手册属于 M4c（真实 AuraDB 试点导入与验证）。**M4c-A 离线准备**已于 2026-11-26 完成（本手册、试点配置、验证查询集与演练测试即为其交付物）；**M4c-B（真实 Schema 执行与试点数据写入）与 M4c-C（GCP 云端部署）均未获授权**。本手册中的 B 层步骤只是预先写明的操作程序，执行任何一步真实操作前都必须先取得用户对该步所属授权关口的单独授权。

## 1. 试点范围（固定集合）

来源配置：`tools/liuyao-kb/sources.pilot.yaml`（使用时复制为 `sources.yaml` 并把三处 `root` 改为实际检出路径，或以 `--sources` 显式传入改好 root 的副本）。仓库 slug 固定为 `symbi/liuyao-learning-app`。

| # | source_uri（repo://symbi/liuyao-learning-app/ 前缀省略） | 类型 | Chunk |
|---|---|---|---:|
| 1 | docs/lessons/lesson-19-notes-v0.1.md | 课程笔记（分块） | 30 |
| 2 | materials/class-cases/lesson-19/case-002.json | 案例 JSON（不分块） | 0 |
| 3 | materials/class-cases/lesson-19/case-002-analysis.md | 案例 MD（分块） | 19 |
| 4 | materials/class-cases/lesson-19/case-003.json | 案例 JSON（不分块） | 0 |
| 5 | materials/class-cases/lesson-19/case-003-analysis.md | 案例 MD（分块） | 20 |
| 6 | daily-records/2026/11/markdown/2026-11-22--13e9c29a-cdbc-41e0-912d-5e02fa7c54d3.md | 每日生成 MD（不分块，RENDERS） | 0 |
| 7 | daily-records/2026/11/markdown/2026-11-24--518d525a-838e-479d-8d2c-815296358b5e.md | 每日生成 MD（不分块，RENDERS） | 0 |

另含：Lesson `lesson-19`；ClassCase `L19-C02-shop-operation-transfer`、`L19-C03-female-marriage-multiple-guangui`；CastRecord 两条（allowlist 固定为容器 `daily-records/2026/11/2026-11-22.json` 的 `13e9c29a-cdbc-41e0-912d-5e02fa7c54d3` 与容器 `daily-records/2026/11/2026-11-24.json` 的 `518d525a-838e-479d-8d2c-815296358b5e`，两条 ID 均已于 M4c-A 对照案例 JSON 的 dailyRecord 链接与容器本体查证）；REFERENCES 9 条（case-003 primary 4；case-002 primary 2 + secondary 3，由配置 `case_references` 显式给出，fail-closed 校验）。

**明确排除**：case-001 及其每日记录、2026-11-22 的待核对子记录 `d4f2ced4-…`、其他任何每日记录、全部 raw ASR、PDF、外部 Reference Package、embedding/向量/生成模型调用（M5 范围）。

## 2. 预期数量（M4c-A 已在 FakeSession 上以真实试点计划演练固定）

节点：SourceDocument 7、DocumentRevision 7、Chunk 69、Lesson 1、ClassCase 2、CastRecord 2，**合计 88**。
关系：CONTAINS 69、HAS_REVISION 7、HAS_REPRESENTATION 4、TAUGHT_IN 2、BASED_ON_RECORD 2、RENDERS 2、REFERENCES 9，**合计 95**。

CLI dry-run 的预期输出行（路径部分除外须逐字一致）：
`7 documents, 69 chunks, 1 lessons, 2 cases, 2 records, 2 record links, 2 renders links, 9 references`

任一数字与预期不符时，先查明原因，**不得为了匹配预期而修改数据或放宽校验**。

## 3. A 层已完成的离线验证（证据）

- 真实试点计划经 `collect_plan` 构建：7 文档 / 69 Chunk / 1 Lesson / 2 Case / 2 Record / 2 + 2 链接 / 9 REFERENCES，skipped 为空。
- FakeSession 两次完整运行：首跑报告 ok 且图计数恰为 88 / 95；复跑 7 文档与 2 记录全部 unchanged、计数不变。
- 单文档事务失败演练：伪造一条与既有 Chunk 冲突的新 revision，导入按预期以 ChunkConflictError 整事务回滚、失败进入报告、图计数与 current_revision_id 不变。
- 以上三项由 `tools/liuyao-kb/tests/test_m4c_rehearsal.py` 固定（4 个测试）；导入器/管线层面的回滚、冲突、fail-closed 等行为另有 `tests/test_importer.py`、`tests/test_ingest_pipeline.py` 覆盖。
- 全部结果均为 Cooper 的 Linux venv 本地运行，**不是 GitHub CI**（本仓库无 Actions 运行记录）。

## 4. B 层执行前检查（连接真实 AuraDB 之前）

1. **授权确认**：确认已取得 M4c-B 的用户授权，并明确本次执行覆盖哪些关口（见第 5 节的关口 1–3，建议分开授权）。
2. **实例状态**：在 Aura 控制台确认正式实例「六爻」（`97d17d42`）为 Running。AuraDB Free 闲置 72 小时自动暂停；若已暂停，先唤醒并等待其恢复，只做只读连通确认后才进入下一步。
3. **代码基线**：执行代码必须是已合并 main 的确定提交（记录 SHA 到执行报告）；不得使用未合并分支的代码做真实导入。
4. **配置就位**：由 `sources.pilot.yaml` 生成本次运行的 `sources.yaml`，三处 `root` 指向同一份上述基线的检出；运行前用 `sources list` 复核启用项与 allowlist 恰为第 1 节集合。
5. **凭据**：Neo4j 凭据只经既有 `.env` / `LIUYAO_KB_CONFIG_DIR` 机制提供；不打印、不写入日志、不进入任何报告或仓库文件。报告只记录"凭据已配置"的布尔事实（doctor 的既有输出方式）。
6. **最终 dry-run**：先执行 `ingest run --dry-run --repository symbi/liuyao-learning-app`，输出行必须与第 2 节预期逐字一致，否则停止并查明原因，不进入写操作。

## 5. B 层逐步流程与授权关口

> 每一步的实际命令以仓库 CLI 为准（`liuyao-kb schema check`、`liuyao-kb schema init`、`liuyao-kb ingest run …`）。关口之间必须停下汇报，不得连贯越过。

1. **Schema check（只读）**：`schema check`。在 init 之前，预期为非零退出并报告 5 个唯一约束缺失——这是 init 前的预期状态，不是部署失败，原样记录。
2. **授权关口 1（Schema init）**：取得单独授权后执行 `schema init`。只创建 M3 目录中的 5 个唯一约束（SourceDocument.document_id、DocumentRevision.revision_id、Chunk.chunk_id、CastRecord.record_id、ClassCase.case_id），不创建生产向量索引（向量维度是 M5 的决策）。
3. **Init 后重新 check**：`schema check` 必须退出 0；不为 0 则停止，报告差异，不导入数据。
4. **最终 dry-run**：重复第 4 节第 6 步，确认计划未漂移。
5. **授权关口 2（单次真实导入）**：取得单独授权后执行一次 `ingest run --no-dry-run --repository symbi/liuyao-learning-app`。只执行一次；无论结果如何都不自动重跑（复跑是关口 3 的独立步骤）。保存完整运行报告：每份文档的 outcome、每条 CastRecord 的 outcome 与 provenance（容器路径 + JSON Pointer，不含正文）、失败清单（预期为空）。
6. **导入后只读验证**：按 `tools/liuyao-kb/verification/pilot-verification.cypher` 逐条执行 Q1–Q10，与每条查询的预期比对；另将 Q7 的两条 record_id 与第 5 步报告中的 provenance 交叉核对（容器路径与 JSON Pointer 只存在于报告侧，图侧只验证 BASED_ON_RECORD / RENDERS 链）。任一条失败即停止，按第 7 节处理。
7. **授权关口 3（幂等复跑）**：取得授权（可与关口 2 同批，但须明确提及）后，再执行一次同一命令。预期：7 份文档与 2 条记录全部 unchanged、报告 ok；随后重跑 Q1/Q2，结果须与第 6 步逐行全等（cypher 文件 Q11）。
8. **收尾记录**：把执行基线 SHA、各步退出码、导入报告摘要、验证结果写入 `docs/phase1-progress.md` 的 M4c 检查点；M4 至此才可标记为真实导入完成。

## 6. 事务边界（必须先理解再执行）

- M4b 导入器以 **每个 DocumentRevision 为一个写事务**：单份文档的节点、CONTAINS 与 `current_revision_id` 指针更新要么全成、要么全回滚，指针永远在该事务的最后一步才移动。
- **整个试点不是一个跨文档原子事务**：7 份文档是 7 个（组）独立事务，中途失败时，先前已提交的文档不会自动回滚。
- `run_plan` 对单项失败的处理是**记录失败并继续处理其余项**，最终报告 `ok=false`、CLI 非零退出。因此"出现失败必须停止"的含义是**程序层面的停止**：看到任何失败即中止整个 B 层流程，不进入验证与复跑环节，先按第 7 节定位原因；不得把"再跑一次直到全绿"当作默认恢复手段——复跑只在原因查明并修复后，作为第 7 节的恢复路径执行。

## 7. 故障处理

| 情形 | 判定 | 处置 |
|---|---|---|
| dry-run 数字与第 2 节预期不符 | 计划漂移（资料或配置已变） | 停止。对比 `sources.pilot.yaml` 与资料现状，查明变化来源；不得改预期数字迁就现状，除非变化本身经用户确认 |
| schema check 在 init 后仍非零 | 约束未建全或 Schema 漂移 | 停止，不导入。报告缺失/多余项，等待用户决定 |
| 单份文档导入失败（如 ChunkConflictError） | 该文档事务已回滚，图内无其残留（演练已证明） | 停止整个流程。保留失败条目原文（item + 错误类型）；查明是资料变化还是既有数据冲突；修复经用户确认后，才以幂等复跑恢复（第 8 节） |
| 案例导入失败（Lesson/表示文档缺失等） | 案例事务已回滚（ClassCase 与其关系不残留） | 同上。特别注意 TAUGHT_IN 只连已存在的 Lesson，不允许为绕过失败而手工补建空 Lesson |
| 导入中途连接中断 / 实例被暂停 | 已提交的文档事务保留，未提交的未生效 | 停止。先只读核对 Q1/Q2 与各文档 current_revision_id，确定实际落点；再按第 8 节以幂等复跑补齐，复跑报告中已导入项应为 unchanged |
| 验证查询任一条失败 | 图状态与预期不一致 | 停止。不复跑、不清理；把失败查询编号、实际返回值与预期一并报告用户，等待决定 |

## 8. 部分导入后的恢复策略

1. **首选恢复路径是幂等复跑**：原因修复后重跑同一导入命令——未变化的文档/记录零写事务跳过，缺失部分补齐，冲突部分会再次明确报错而不是静默覆盖。
2. 复跑前先只读核对（Q1、Q2、Q4），把"已落点"清单与导入报告对齐，再执行复跑。
3. 复跑后必须重做第 5 节第 6 步的完整验证与第 7 步的稳定性确认，才能宣布恢复完成。
4. 若复跑仍失败，停止并报告；不尝试第三次，不改代码现场修补。

## 9. 精确范围清理（最后手段，单独授权）

只有当用户明确决定放弃本次试点数据时才考虑清理，且必须满足全部条件：

- **单独授权**：清理是独立于导入的写操作，须用户单独明确授权，并写明清理范围；
- **范围锁定**：只能按第 1 节的固定清单定点删除——7 份 SourceDocument（按 document_id）及其 HAS_REVISION / DocumentRevision / 该 revision 独占的 CONTAINS 与 Chunk、2 个 ClassCase、2 个 CastRecord、Lesson `lesson-19`（仅当无其他引用时）；Chunk 若被试点外 revision 共享 CONTAINS，不得删除 Chunk 本体；
- **禁止宽范围删除**：不允许无条件或仅按标签的批量 `DETACH DELETE`；每条清理语句必须带明确的 ID 清单；
- **清理后验证**：重跑 Q1/Q2 应回到清理前的基线（首次导入前为空图时即全 0），并把清理语句与结果记入 progress 检查点；
- 约束的删除（DROP CONSTRAINT）属于 Schema 变更，同样须单独授权，不与数据清理混同。

## 10. 交接 M5 的数据契约

M4c 完成后，图内应具备：稳定的 document_id / revision_id / chunk_id（公式不变）、Chunk 节点仅含 chunk_id / text / text_hash（embedding 相关属性由 M5 按其维度决策写入）、CONTAINS 定位信息完整（paragraph_ordinal / subchunk_index / heading_path / start_offset / end_offset，可按 offset 回溯原文）、每份 SourceDocument 的 current_revision_id 指向已导入 revision、DocumentRevision 的 parser_version / chunker_version 齐全。M5 只读消费这批 Chunk，不得依赖任何 M4c 运行期临时状态；生产向量索引的维度与模型在 M5 决定，不由 M4c 预建。
