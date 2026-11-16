# 每日卦例（Phase 1）

此目录位于 Public `symbi/liuyao-learning-app`，用于第一阶段验证每日排卦、Memo、保存和 AI 分析流程。

**公开提示：** 本目录中的卦例和 Memo 对所有人可见，也可能被复制或 Fork。不要写入密码、访问令牌、公司机密或不希望公开的个人信息。

## 路径规则

一天一个 JSON 文件：`YYYY/MM/YYYY-MM-DD.json`。例如 `2026/11/2026-11-16.json`。

文件包含：
- `dailyFortune`：当天唯一的「今日运势（每日卦）」；同一天再次保存时更新此对象。
- `additionalQuestions`：当天额外问事的独立记录列表。
- `dailyMemo`：当天自由记录的 Memo，与额外问事分开。
- `timezone`：固定使用 `Asia/Tokyo`。

由应用页面和 Pages Function 创建、读取、更新。不要手工把 Token 或 Secret 写入 JSON。