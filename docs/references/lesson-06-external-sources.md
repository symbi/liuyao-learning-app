# 第六课基础术语：外部参考登记

> 本页是为了帮助整理者核对基本结构而查阅的公开资料。外部资料不是老师的课堂原话，不自动成为项目的最终判断规则；不同流派的断法可能有差异。

## 1. 动爻、静爻、变爻

开源入门资料区分本卦、动爻、变爻：发动的原爻是动爻，变化后对应的爻称变爻；动而必变是分析关系的一部分。具体如何判断变爻是否对其他爻产生作用，需要继续依据课程和规则来源核对。

- [woaichiji/liuyao：动爻、静爻与变爻](https://github.com/woaichiji/liuyao/blob/main/2-06-%E5%8A%A8%E7%88%BB%E3%80%81%E9%9D%99%E7%88%BB%E4%B8%8E%E5%8F%98%E7%88%BB.md)
- [《增删卜易》公开文本：动变章、用神章等](https://github.com/weihus/liuyao/blob/main/%E5%A2%9E%E5%88%A0%E5%8D%9C%E6%98%93.txt)

## 2. 纳甲：艮卦

参考表中，艮卦下卦由初爻向上为辰、午、申；上卦由四爻向上为戌、子、寅。

- [woaichiji/liuyao：纳甲](https://github.com/woaichiji/liuyao/blob/main/2-03-%E7%BA%B3%E7%94%B2.md)
- [ShousenZHANG/chinese-fortune：六爻算法中的纳甲表](https://github.com/ShousenZHANG/chinese-fortune/blob/main/scripts/liuyao_cast.py)

## 3. 用神不现、伏神与飞神

常见基础流程是：本卦中所需六亲不现时，查本卦所属卦宫的本宫卦全图，寻找缺失的六亲并按对应爻位登记为伏神，再考虑其所在位置（飞神）以及两者的生克关系。不同流派或软件可能把本卦明现、变爻与伏神的查找顺序规定得更细，不能不加核对就把一种实现当作唯一标准。

- [woaichiji/liuyao 仓库目录：伏神与飞神、用神等章节](https://github.com/woaichiji/liuyao)
- [《增删卜易》公开文本：飞伏神章](https://github.com/weihus/liuyao/blob/main/%E5%A2%9E%E5%88%A0%E5%8D%9C%E6%98%93.txt)

## 4. 项目使用约定

1. 明确区分课堂原话、外部共通知识和整理者推断。
2. 算法类规则优先寻找公开代码、明确映射表和可复算测试样例。
3. 断卦解释如缺少完整卦盘，不能把口头例子变成程序的固定期望结果。
4. 不因某一爻发动，就自动输出“成功”“失败”“可以投资”等绝对结论。
