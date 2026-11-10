# 2026-11-10主峰确认实验

[实验目录](../README.md) · [当前代码](../../../main.cpp) · [逐次状态](state.json)

当前无打表采用 **218796**，当日起点218796。默认从冻结218796出发，后续受控组的父版见qualifications；按线上总分判断收益；不由合成分数挑选，不含指定样例长度、峰位或回复指纹。

|方案|正式分|对比提交前最高|状态|
|---|---:|---:|---|
|valley_separated_rivals|218796|0|completed|
|basin_rearm|218775|-21|completed|
|tail_order_veto|218024|-772|completed|
|fractional_cells|218796|0|completed|
|envelope_finish|218796|0|completed|
|fresh_fit_support|218036|-760|completed|

[研究过程](WORKLOG.md)记录机制假设与线上消融。

本地只验证编译与交互/查询/振荡/真实停车。主机若在查询前被Windows4551拒绝启动，保留原记录，仅以源码内核等价审计补充缺项，未运行项不冒充通过；真实协议或预算错误仍拒绝。总分不能确认每个零分样例已恢复。未知上传只恢复原任务；旧任务保留原作品编号，无重传。
