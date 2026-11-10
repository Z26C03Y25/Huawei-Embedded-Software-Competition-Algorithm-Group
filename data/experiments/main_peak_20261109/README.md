# 2026-11-09主峰确认实验

[实验目录](../README.md) · [当前代码](../../../main.cpp) · [逐次状态](state.json)

当前无打表采用 **218796**，当日起点217614。前期方案从冻结217614出发，后续受控组的父版见qualifications与followup_parent.json；按线上总分判断收益；不由合成分数挑选，不含指定样例长度、峰位或回复指纹。

|方案|正式分|对比提交前最高|状态|
|---|---:|---:|---|
|carry_20261108_wave88_paired|None|None|failed|
|short_rebound|216982|-632|completed|
|confirmed_apex|216857|-757|completed|
|rival_veto|217614|0|completed|
|predictive_fit|216195|-1419|completed|
|scale_confirmation|213782|-3832|completed|
|edge_recovery|217614|0|completed|
|persistent_confirmation|218389|775|completed|
|shoulder_recovery|217614|0|completed|
|challenge_marginal|218135|-254|completed|
|weak_companions|210778|-7611|completed|
|persistent_challenge|215951|-2438|completed|
|spatial_background|217714|-675|completed|
|spatial_persistent|218796|407|completed|
|curvature_noise|210082|-8307|completed|
|persistent_curvature_noise|210416|-8380|completed|
|spatial_fit|217457|-1339|completed|
|spatial_all|217557|-1239|completed|
|persistent_spatial_fit|217704|-1092|completed|
|persistent_spatial_all|218111|-685|completed|
|robust_confirmation|217614|-1182|completed|
|robust_persistent|218389|-407|completed|
|sharp_or_fit|217614|-1182|completed|
|hybrid_sharp|218389|-407|completed|
|after_challenge|215931|-2865|completed|
|after_rebound|218196|-600|completed|
|after_edge|218796|0|completed|
|after_width|217870|-926|completed|
|after_plateau|218796|0|completed|
|after_robust|218796|0|completed|
|after_sharp|218796|0|completed|

carry_20261108行是昨日原作品只读恢复，不计入当日上传次数。 [研究过程](WORKLOG.md)记录机制假设与线上消融。

本地只验证编译与交互/查询/振荡/真实停车。主机若在查询前被Windows4551拒绝启动，保留原记录，仅以源码内核等价审计补充缺项，未运行项不冒充通过；真实协议或预算错误仍拒绝。总分不能确认每个零分样例已恢复。未知上传只恢复原任务；旧任务保留原作品编号，无重传。

当日已用30/30，30份均有正式数值成绩。最终构建、原生检查与归档核对见[最终验证](final_validation.json)。
