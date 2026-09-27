# sci-fakedata

> 修真不修假迟早走火入魔。

考虑到某些可疑数据的制作水平极差（小数点后忘了改，整列统一加个常数，末位数字对 `5` 情有独钟），令人失望，随之而来的撤稿也浪费了大量版面费（虽然版面费也不是什么好东西，fuck publisher）。

根据知社对徐少雄、胡光伟发表于 *Learned Publishing* 的研究的中文介绍，研究者以部分撤稿论文的平均文章处理费（APC）为依据，估算了更大范围的撤稿论文发表费用：[中文报道][report] · [原论文 DOI][paper]。

本项目致力于提供专业的科研虚假数据生成工具，红噪声一定要红，白噪声一定要白。同时也提供科研虚假数据分析工具，让“这两行数据的小数点后部分一模一样”之类的低端错误不再出现。

**让科研告别实验。**

## 名字与安装

| 用途 | 名称 |
| --- | --- |
| 项目名称 | `sci-fakedata` |
| Python 导入包名 | `sci_fakedata` |
| 示例中的简称 | `sfd` |

安装方式：

```bash
python -m pip install sci-fakedata
sfd demo
```

example：

```python
import sci_fakedata as sfd
```

## `sfd.gen`： Red noise must be red, white noise must be white.

输出伪造的实验数据，让科研工作不再需要实验。

- 常见分布的随机样本，以及可配置的样本量、参数和随机种子。
- 想要什么置信度，就有什么置信度。

```python
import sci_fakedata as sfd

# 生成明确标记为 synthetic 的示例数据。
data = sfd.gen.normal(n=1000, mean=0.0, std=1.0, seed=42)
errors = sfd.gen.error(n=1000, systematic=0.2)
```

## `sfd.analyze`： Am I safe if student Geng see my paper?

计划分析下列模式，并报告命中的位置、统计量、适用条件和解释：

| 分析项 | 示例 |
| --- | --- |
| 末位数字分布 | 为什么这一列的最后一位几乎都是 `5`？ |
| 小数位数与精度 | 声称的测量分辨率能支持这些小数位吗？ |
| 重复值与重复片段 | 不同组为什么出现完全相同的长片段？ |
| 固定偏移 | 是否存在 `B = A + 0.3` 这样的逐行关系？ |
| 仿射关系 | 两列是否几乎精确满足 `B = aA + b`？ |
| 重复小数尾部 | 整数部分不同，小数后几位却逐行一致？ |
| 机械序列 | 是否出现异常整齐的等差变化或循环模式？ |

```python
import sci_fakedata as sfd

# 分析数据，给出需要复核的线索。
report = sfd.analyze.scan(data)
print(report.summary())
```

## 自相矛盾

```python
import sci_fakedata as sfd

# 分析数据，给出需要复核的线索。
report = sfd.analyze.scan(sfd.gen.normal())
print(report.summary())
```

> 楚人有鬻data generator与 data analyzer者，誉之曰：“吾data之random，paper莫能拒也。”又誉其矛曰：“吾analyzer之sharp，于data无不陷也。”或曰：“以子之analyzer，陷子之data，何如？”其人弗能应也。

## 我愿意参加假数据排行榜

**排行榜为规划功能，服务器尚未准备好，目前无法报名或上传。**

排行榜将统计参加者生成的fake data数据量。不排除学习Claude先进经验，通过用户IP分析其所在单位，并隐写入data中。

### 必须手动开启

**默认关闭。只有用户主动打开“我愿意参加假数据排行榜”开关并确认数据说明后，才允许发送排行榜统计。** 安装、导入、生成或分析数据，都不构成报名或同意。

## 开发计划

- [ ] 实现基础合成数据生成器与随机种子支持。
- [ ] 实现末位数字、重复数据、固定偏移及小数尾部分析。
- [ ] 建立带已知标签的异常样本与正常对照样本。
- [ ] 提供可解释的报告，记录检测假设与局限。
- [ ] 发布首个可安装版本，并验证文档示例。
- [ ] 在服务器、数据说明及退出机制就绪后，提供自愿排行榜。

## 致谢

数据检测算法灵感来源于 耿同学 学术打假视频。

## 参考

1. 徐少雄、胡光伟，*Learned Publishing*，2026。中文报道将论文题名译为《中国撤稿的代价：浪费的科研经费及其他》。[DOI: 10.1002/leap.2102][paper]。
2. 知社：《撤稿论文造成的中国经费损失研究：两千多篇撤稿，仅版面费就浪费国自然4780万》。[中文报道][report]。本文费用数字据该报道整理。

[report]: https://mp.weixin.qq.com/s/qSjMsKxQa7-fqlbc05KiIg
[paper]: https://doi.org/10.1002/leap.2102
[packaging]: https://packaging.python.org/en/latest/discussions/distribution-package-vs-import-package/
[pypi-names]: https://pypi.org/help/#project-name
