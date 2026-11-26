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

## 配套 Markdown 文字资料

每条卦例另有独立的 Markdown 文件，路径为：

    YYYY/MM/markdown/YYYY-MM-DD--<record-id>.md

这些 MD 文件由 HTML 页面中的 JavaScript 从对应 JSON 生成，包含易读的卦盘基本事实、逐爻状态、适用的 Memo / 结论，以及原始 JSON 代码块。生成过程不调用 AI 模型。JSON 是权威数据；MD 是供用户复制、交给其他 AI 阅读的衍生资料。

新卦保存后会自动保存 MD；修改和删除卦例时也会同步更新或清理 MD。较早的历史记录会在用户点击「复制 MD」时按需补建。

**Markdown 文件同样存放在 Public 仓库，对外可见。**
