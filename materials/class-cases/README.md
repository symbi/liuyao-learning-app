# 课堂案例

本目录保存从课程中拆分出来的单个课堂案例。理论课和案例课都可以有独立案例；每一课使用自己的子目录：

```text
materials/class-cases/
├── README.md
├── lesson-05/
│   ├── case-001.json
│   └── case-002.json
├── lesson-18/
│   ├── case-001.json
│   └── case-002.json
└── ...
```

每条案例记录只需要：

- `recordType`: 程序识别，固定为 `class-case`
- `id`: 程序生成的案例 ID
- `category`: 在 HTML 里选择的 Category
- `tagOrRealQuestion`: 可选文字，写 tag 或当事人真正的问题
- `casting`: 可选卦盘快照，有可靠资料才保存
- `teacherAnalysis`: 老师对案例的原始讲解和结论

课次由所在文件夹 `lesson-XX` 确定，不需要再让用户重复填写。Category 不作为目录名，不需要建立分类子文件夹。

## 和课程笔记、ASR 转录的对应

同一课的三份资料使用相同课次编号：

- Private raw 原始 ASR：`liuyao-learning-raw/lessons/lesson-XX/transcript-asr-raw.txt`
- Public Learning 该课总结：`docs/lessons/lesson-XX-notes-*.md`
- Public Learning 单独案例：本目录下的 `lesson-XX/case-*.json`

整理某一课时，应自动按课次编号读取这三处资料，把案例对应到该课总结中，并添加案例链接。ASR 只是可能有误的参考，不得将听写错误直接当作老师定论；不确定的地方标注待核对。

课程笔记提到但没有足够资料独立复原的内容，可以继续作为该课的「案例线索」，不必强行建立完整案例文件。
