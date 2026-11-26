// ============================================================================
// M4c 试点导入后只读验证查询集（pilot-verification.cypher）
//
// 用途：M4c-B 真实试点导入完成后（以及幂等复跑后），对 AuraDB 执行本
// 文件中的查询，逐项与预期结果比对。全部查询均为只读（MATCH/RETURN），
// 不含任何 CREATE / MERGE / SET / DELETE。
//
// 本文件在 M4c-A（离线准备）阶段编写，A 层未连接任何数据库执行。
// 执行时机、授权关口与失败处置见 docs/m4c-pilot-runbook.md。
//
// 约束：只使用冻结的 M3 Schema 标签、属性与关系类型；不为验证便利
// 新增任何 Schema 元素。计数预期来自 M4c-A 在 FakeSession 上的真实
// 试点计划演练（tests/test_m4c_rehearsal.py 固定同一组数字）。
// ============================================================================

// ---------------------------------------------------------------------------
// Q1 节点标签计数
// 预期（恰好 6 行，数值全等）：
//   SourceDocument 7 | DocumentRevision 7 | Chunk 69
//   Lesson 1 | ClassCase 2 | CastRecord 2        （合计 88）
// 失败判据：任一数值不符，或出现预期之外的标签行。
// ---------------------------------------------------------------------------
MATCH (n)
RETURN labels(n)[0] AS label, count(n) AS nodes
ORDER BY label;

// ---------------------------------------------------------------------------
// Q2 关系类型计数
// 预期（恰好 7 行，数值全等）：
//   CONTAINS 69 | HAS_REVISION 7 | HAS_REPRESENTATION 4 | TAUGHT_IN 2
//   BASED_ON_RECORD 2 | RENDERS 2 | REFERENCES 9      （合计 95）
// 失败判据：任一数值不符，或出现预期之外的关系类型行。
// ---------------------------------------------------------------------------
MATCH ()-[r]->()
RETURN type(r) AS rel_type, count(r) AS rels
ORDER BY rel_type;

// ---------------------------------------------------------------------------
// Q3 SourceDocument 与其 Revision 的关联完整性
// 预期：0 行（每份文档的 current_revision_id 都必须指向它自己的一条
// HAS_REVISION revision，且 status 为 imported）。
// 失败判据：返回任何一行 —— 记下 document_id，停止后续验证。
// ---------------------------------------------------------------------------
MATCH (d:SourceDocument)-[:HAS_REVISION]->(rev:DocumentRevision)
WITH d, collect(rev) AS revisions
WHERE NOT any(r IN revisions WHERE r.revision_id = d.current_revision_id)
   OR any(r IN revisions WHERE r.status <> 'imported')
RETURN d.document_id AS document_id, d.current_revision_id AS current_revision_id;

// ---------------------------------------------------------------------------
// Q4 每份 Revision 的 Chunk 数（经 CONTAINS）
// 预期：恰好 7 行。其中带 Chunk 的三份：
//   lesson-19-notes-v0.1.md 的 revision -> 30
//   case-002-analysis.md 的 revision    -> 19
//   case-003-analysis.md 的 revision    -> 20
// 其余 4 份（2 份案例 JSON、2 份每日生成 MD，均为未分块文档）-> 0。
// 失败判据：行数不为 7，或任一数值与上表不符。
// ---------------------------------------------------------------------------
MATCH (d:SourceDocument)-[:HAS_REVISION]->(rev:DocumentRevision)
OPTIONAL MATCH (rev)-[c:CONTAINS]->(:Chunk)
RETURN d.source_uri AS source_uri, rev.revision_id AS revision_id,
       count(c) AS chunks
ORDER BY source_uri;

// ---------------------------------------------------------------------------
// Q5 Chunk 身份完整性
// 预期：单行 chunks = 69 且 distinct_chunk_ids = 69。
// 失败判据：两数不等（存在重复 chunk_id 或缺失），或 chunks 不为 69。
// ---------------------------------------------------------------------------
MATCH (c:Chunk)
RETURN count(c) AS chunks, count(DISTINCT c.chunk_id) AS distinct_chunk_ids;

// Q5b Chunk 必备属性缺失检查
// 预期：0（text 与 text_hash 均不得为 null）。
// 失败判据：返回值大于 0。
MATCH (c:Chunk)
WHERE c.text IS NULL OR c.text_hash IS NULL
RETURN count(c) AS chunks_missing_identity_fields;

// ---------------------------------------------------------------------------
// Q6 ClassCase 与 Lesson 的关系（TAUGHT_IN）
// 预期：恰好 2 行，两个 case_id 各一行，lesson_id 均为 lesson-19。
// 失败判据：行数不为 2，或任一案例缺少 TAUGHT_IN（另见 Q6b）。
// ---------------------------------------------------------------------------
MATCH (k:ClassCase)-[:TAUGHT_IN]->(l:Lesson)
RETURN k.case_id AS case_id, l.lesson_id AS lesson_id
ORDER BY case_id;

// Q6b 无 TAUGHT_IN 的 ClassCase
// 预期：0 行。
MATCH (k:ClassCase)
WHERE NOT (k)-[:TAUGHT_IN]->(:Lesson)
RETURN k.case_id AS case_without_lesson;

// ---------------------------------------------------------------------------
// Q7 CastRecord 的图内来源链（provenance 的图侧部分）
// 预期：恰好 2 行，record_id 分别为
//   13e9c29a-cdbc-41e0-912d-5e02fa7c54d3（case-002 的每日记录）
//   518d525a-838e-479d-8d2c-815296358b5e（case-003 的每日记录）
// 每行 based_on_record = 1 且 renders = 1。
// 说明：容器路径与 JSON Pointer 不存于图内（冻结 Schema 无此属性），
// 须与导入运行报告 IngestReport.records 中的 provenance 交叉核对，
// 见手册第 5 节。图侧只验证 BASED_ON_RECORD / RENDERS 链完整。
// 失败判据：行数不为 2、record_id 不符、任一计数不为 1。
// ---------------------------------------------------------------------------
MATCH (rec:CastRecord)
OPTIONAL MATCH (k:ClassCase)-[b:BASED_ON_RECORD]->(rec)
OPTIONAL MATCH (rec)-[r:RENDERS]->(d:SourceDocument)
RETURN rec.record_id AS record_id, rec.record_type AS record_type,
       rec.date AS date, count(DISTINCT b) AS based_on_record,
       count(DISTINCT r) AS renders
ORDER BY record_id;

// ---------------------------------------------------------------------------
// Q8 REFERENCES 端点与角色分布
// 预期：恰好 3 行：
//   L19-C03-female-marriage-multiple-guangui | primary   | 4
//   L19-C02-shop-operation-transfer          | primary   | 2
//   L19-C02-shop-operation-transfer          | secondary | 3
// 失败判据：行数或任一数值不符。
// ---------------------------------------------------------------------------
MATCH (k:ClassCase)-[r:REFERENCES]->(:Chunk)
RETURN k.case_id AS case_id, r.role AS role, count(r) AS refs
ORDER BY case_id, role;

// Q8b REFERENCES 目标 Chunk 必须属于第十九课笔记的 revision
// 预期：0 行（所有被引用的 Chunk 都应被笔记文档的某个 revision 以
// CONTAINS 收录；引用到其他文档 Chunk 即为配置或导入错误）。
// 失败判据：返回任何一行。
MATCH (k:ClassCase)-[:REFERENCES]->(c:Chunk)
WHERE NOT EXISTS {
  MATCH (d:SourceDocument)-[:HAS_REVISION]->(:DocumentRevision)-[:CONTAINS]->(c)
  WHERE d.source_uri ENDS WITH 'docs/lessons/lesson-19-notes-v0.1.md'
}
RETURN k.case_id AS case_id, c.chunk_id AS chunk_id;

// ---------------------------------------------------------------------------
// Q9 孤儿检查
// 预期：三个数值全为 0。
// 失败判据：任一数值大于 0。
// ---------------------------------------------------------------------------
MATCH (c:Chunk) WHERE NOT (:DocumentRevision)-[:CONTAINS]->(c)
RETURN count(c) AS chunks_without_contains;
MATCH (rev:DocumentRevision) WHERE NOT (:SourceDocument)-[:HAS_REVISION]->(rev)
RETURN count(rev) AS revisions_without_document;
MATCH (d:SourceDocument) WHERE NOT (d)-[:HAS_REVISION]->(:DocumentRevision)
RETURN count(d) AS documents_without_revision;

// ---------------------------------------------------------------------------
// Q10 case-002 的 matchStatus 规范化抽查
// 预期：单行 match_status = 'verified'（原始 'matched' 已在读取期
// 规范化），且其 JSON 表示关系上的 match_status_raw = 'matched'。
// 失败判据：行数不为 1 或任一值不符。
// ---------------------------------------------------------------------------
MATCH (k:ClassCase {case_id: 'L19-C02-shop-operation-transfer'})
      -[rep:HAS_REPRESENTATION {format: 'json'}]->(:SourceDocument)
RETURN k.match_status AS match_status, rep.match_status_raw AS match_status_raw;

// ---------------------------------------------------------------------------
// Q11 幂等复跑稳定性（程序性检查，无独立查询）
// 步骤：真实导入后记录 Q1/Q2 结果 -> 执行一次幂等复跑（导入报告中
// 7 份文档应全部为 unchanged、2 条记录全部为 unchanged）-> 再次执行
// Q1/Q2。预期：两次 Q1/Q2 结果逐行全等（88 节点 / 95 关系）。
// 失败判据：任一数值变化，或复跑报告出现 created/updated/失败项。
// ---------------------------------------------------------------------------
