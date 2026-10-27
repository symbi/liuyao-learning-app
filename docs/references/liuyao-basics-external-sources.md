# 六爻基础知识：外部参考登记

> 外部资料用于帮助整理者理解基础术语与计算规则，不是课程原文，也不自动成为本项目最终规则。若课程与外部资料不一致，保留差异并登记来源。

## 六亲五行映射

常见规则以本卦所属卦宫五行为“我”，比较各爻地支五行：生我为父母、同我为兄弟、我生为子孙、我克为妻财、克我为官鬼。

参考：
- [woaichiji/liuyao：装六亲](https://github.com/woaichiji/liuyao/blob/main/2-04-%E8%A3%85六亲.md)
- [ShousenZHANG/chinese-fortune：04-liuyao.md](https://github.com/ShousenZHANG/chinese-fortune/blob/main/references/04-liuyao.md)
- [laowangqi/liuyao](https://github.com/laowangqi/liuyao)

## 世应位置

六爻自下而上编号为初、二、三、四、五、上。先确定世爻，再将应爻定位在相隔两个爻位的位置：初—四、二—五、三—上。

参考：
- [世应位置与含义](https://www.tianeon.com/zh-CN/learn/shi-and-ying-lines)
- [FateMaster：世应定位指南](https://www.fatemaster.ai/guides/liuyao-shiying)

## 变爻六亲的基准

部分开源六爻项目明确采用本卦所属卦宫五行作为六亲基准，并将此基准用于变爻，而不是在变卦中重新按变卦自身的卦宫五行装六亲。该点可作为基础算法候选，但实现前仍需与课程后续装卦规则对齐。

## 使用规则

1. 区分“课程明确说过”“外部资料常见做法”“当前推断”。
2. 不把外部网站的解释自动升级为课程已确认规则。
3. 对排盘计算规则优先找有代码、测试样例和明确约定的开源项目；对断卦含义还需核对其引用古籍/原文。
4. 公共仓库只放自写摘要、规则记录和必要链接；课程完整转录保存在私有仓库。
