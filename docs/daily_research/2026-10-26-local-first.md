# 2026-10-26：先扩大本地样例，再筛算子

[文档导航](../README.md) · [当日正式实验](2026-10-26.md) · [新研究队列](../../data/experiments/local_valley_20261026/research_queue.json)

## 本次结论

用户指出线上消耗过快、相邻版本成绩接近后，策略改为本地优先。自动研究每天最多使用3次团队提交额度，可以为0；不再以用完平台30次为目标。每小时唤醒、午夜刷新、账户用量恢复、旧作品恢复及榜单第一页两小时缓存保留。

当前生成器提供22族曲线；初版肩峰与窄凸起共用模板的问题已修复并追加验证。完成四个新样例块各1415例、合计16980次真实子进程交互，线上上传0次、榜单请求0次。五个候选均未通过稳定收益门槛。main.cpp保留最高正式203239源码，未用离线候选替换。

## 样例怎样隔离

[生成器](../../dev/tools/scenario_factory.py)覆盖：普通幂指数峰、非对称峰、尖顶、超高斯、肩峰、近等高双峰、远双峰、宽峰上窄凸起、AR(1)相关噪声、异方差噪声、周期纹波、变频纹波、量化顶、饱和顶、平台边缘凸起、趋势叠峰、迟发峰、边界峰、阶梯、平坦并列、无结构随机和单点尖峰。

每轮1188条独立母曲线，含1080条结构化母曲线和108条信息受限母曲线；另有198条镜像/加常数/正缩放变体，以及29条烟测和冻结反例。变体共享母曲线身份，不作为独立统计证据。两轮2376条母曲线，回归样例会重复，不能把2830条评测条目称作完全独立样例。

开发、选择、分布偏移留出各396条母曲线。留出改变长度边界、幂指数、噪声相关性和纹波周期。第一轮使用每族索引0–17，第二轮18–35，每例随机种子独立；第二轮新算子冻结后才读取新块得分。现在两轮留出都已消耗，后续修改需要新的留出块。

无结构随机及孤立尖峰单独报告信息限制，不能用稀疏查询保证命中。单个平坦并列族也可能在低幅整数化后完全变平。所有变换重新按原始值与官方并列规则求目标；不假设镜像后移动成本或分数不变。

## 配对结果

下表为每条结构化母曲线的族均衡平均分差，相对同批203239版本。不是官方总分差。

| 批次/算子 | 开发 | 选择 | 偏移留出 | 新结构化零分 | 决定 |
| --- | ---: | ---: | ---: | ---: | --- |
| 第一轮：有门控的小窗口拟合 | -0.99 | -1.31 | -0.10 | 0 | 无稳定收益，淘汰 |
| 第一轮：拟合尺度分歧后继续精修 | -0.18 | -5.28 | +5.43 | 0 | 修复个别零分，正常曲线额外成本过高 |
| 第一轮：低噪声反尺度偏移补2点 | -0.05 | +0.60 | +1.99 | 0 | 留出置信区间含0，继续离线 |
| 第二轮：仅尺度分歧，作为对照 | -4.37 | -0.59 | +3.58 | 0 | 正常曲线损失再次出现 |
| 第二轮：局部波谷且尺度分歧才继续 | -0.65 | -1.84 | -0.03 | 0 | 降低误触发成本，但遗漏潜在修复，淘汰 |

[第一轮详细分组](../../data/experiments/local_screen_20261026/summary.json) · [第二轮详细分组](../../data/experiments/local_valley_20261026/summary.json) · [运行完成与次数统计](../../data/experiments/local_valley_20261026/research_summary.json)

第二轮[局部波谷算子](../../data/experiments/local_valley_20261026/probe_valley_gate.cpp)在原验证区间已经查询完毕后检查“下降再上升”的原始值证据；只有同时存在半径32与24拟合分歧才放弃早停。它复用共享预算、停车与证书分支，不额外凭空查询。新反例说明：未采样的次峰可以在验证区间外，区间内部单峰不能证明整个竞争区安全。

上一批B曾在84例留出上看到明显正收益，扩大分布后不稳定，正是不能立即上线的例子。B的缺失宽拟合分支与有限顶点分歧分支在281例中可区分：完整门控与有限分歧门控查询轨迹完全相同，单独要求宽拟合存在则与基线相同。这只是观测等价，未宣称所有数组等价。见[B收尾记录](../../data/experiments/2026-10-26-B/final_review.json)。

## 硬约束与剩余风险

9905次交互均检查协议、Q≤199、O≤6和最终停在最佳已观测原始值点。未出现协议/查询/振荡/停车违规；真实目标可能仍未找到。

真实冗余R仍存在零分。第一轮结构化母曲线中19例触发R≥200，114例距离>3；第二轮分别24和111，原因可重叠，不能相加当零分数。最大冗余甚至超过800，现有默认模型绝无通用冗余保证。所有这类失败保留在原报告，未删除来改善平均分。[第一轮失败审计](../../data/experiments/local_screen_20261026/baseline_failure_audit.json) · [第二轮失败审计](../../data/experiments/local_valley_20261026/baseline_failure_audit.json)

新样例主要暴露迟发峰、平台细节、肩峰/凸起及趋势风险，属于合成分布发现，不是官方逐例归因。已将开发集代表性失败完整冻结在各批counterexamples目录；完整数组和查询轨迹在本机忽略目录dev/build/research，公开生成器与种子可重建。

## 如何复现与选择

需要Python3.10+和GCC C++17，在仓库目录运行；命令不联网：

```bash
python dev/tools/screen_operators.py --generator-version 1 --out data/experiments/local_screen_20261026 --program formal203239=main.cpp --program guarded16=data/experiments/2026-10-26-B/guarded_fit16_v2.cpp --program drift_gate=data/experiments/2026-10-26-B/post_probe_drift_only.cpp --program inverse_audit=data/experiments/2026-10-26-B/low_noise_inverse_scale_drift.cpp
python dev/tools/screen_operators.py --generator-version 1 --out data/experiments/local_valley_20261026 --case-offset 18 --program formal203239=main.cpp --program drift_gate=data/experiments/2026-10-26-B/post_probe_drift_only.cpp --program valley_gate=data/experiments/local_valley_20261026/probe_valley_gate.cpp
```

运行前冻结完整数组摘要、生成器摘要和所有源码SHA256；中断后在同一输出目录续跑，输入或源码身份变化则拒绝复用。若main.cpp已升级，使用203239归档作为基线，并换新输出目录。退出0表示研究跑完，候选是否通过以summary.qualification为准。

局部筛选至少1000条独立母曲线、12个结构化族，新增结构化零分及硬约束失败否决；开发/选择/留出族均衡收益要稳定，最差族均值退化不超过25分，留出按族分层的母曲线bootstrap下界要大于0。这是保守的研究筛选规则，不是对官方分布的统计保证。变体只参与稳健性与新零分检查，未重复计入置信区间。

[研究策略](../../automation/research_policy.json)已接入自动控制器上传前检查，[合格清单](../../data/experiments/qualified_candidates.json)当前为空。已投递或不确定的作品先恢复，不能让新上传门槛阻断取分。手工单次judge.py命令保持独立，不会把自动研究规则强加给他人的手工使用。

后续先研究分歧触发后的补查成本上界、平台/阶梯的不可逆超越，以及迟发峰覆盖与冗余权衡。旧tau6/tau12队列降为离线假设，不再次日自动上传。无证据就继续研究，可以一次都不提交。

## 生成器复核与最终追加验证

复核发现初版“肩峰”和“宽峰上窄凸起”共用同一生成公式，虽然随机样例独立，但不能声称是两个独立结构类型。第一次V2替换因Windows换行未匹配而没有生效，新加的组件宽度测试明确报错；失败报告和V2源码原样保留。V3采用明确区分的0.85×宽肩与0.06×窄凸起，并用精确替换计数和双Python版本测试确认。自动上传证据门槛现在只接受V3及以后版本，旧批次不能重新贴标签通过门槛。

[V1源码快照](../../data/experiments/local_screen_20261026/scenario_factory_v1.py)可逐例重建其1386条生成输入，已核对完全一致。[V2失败说明](../../data/experiments/local_widevalley_20261026/generator_review.json)保留了未生效改动和报告，不将其作为修正后分类的证据。

第三块索引36–53测试“宽域已观测波谷”算子及原分歧算子，两者仍不合格；第四块54–71使用真正修正的V3生成器，分别跑203239基线和宽域算子2830次交互。

| V3宽域波谷算子 | 开发 | 选择 | 偏移留出 |
| --- | ---: | ---: | ---: |
| 结构化母曲线族均衡平均分差 | +16.19 | -2.96 | +9.55 |
| 修复零分条目（含同母变体） | 5 | 0 | 2 |
| 新增结构化零分 | 0 | 0 | 0 |

实际修复的是5条独立母曲线（开发3、偏移留出2），另有同一开发母曲线的加常数/缩放变体2条，以及旧冻结反例1条；不能说独立修复了8条。选择集近等高竞争峰族平均下降37.44分，纹波族也有损失，故继续留在本地。偏移留出bootstrap下界仍小于0，未据单批正均值安排上传。

[最终分组报告](../../data/experiments/local_factory_v3_20261026/summary.json) · [修复曲线原始值与配对轨迹](../../data/experiments/local_factory_v3_20261026/counterexamples/repaired_cases.json) · [全批次运行账本](../../data/experiments/local_factory_v3_20261026/research_summary.json) · [最新研究队列](../../data/experiments/local_factory_v3_20261026/research_queue.json)

复现最终V3批次：

```bash
python dev/tools/screen_operators.py --out data/experiments/local_factory_v3_20261026 --case-offset 54 --program formal203239=main.cpp --program wide_valley=data/experiments/local_widevalley_20261026/wide_observed_valley_gate.cpp
```

全程新增线上提交0次、榜单请求0次；所有16980次交互的协议/Q/O/已观测冠军停车检查通过，真实冗余零分仍保留。完整策略诊断另跑15个方法，9个失败断言仍可见。当前已消耗的0–71号样例块不能再当新留出，下一轮从未使用的72号以后或新冻结种子开始。
