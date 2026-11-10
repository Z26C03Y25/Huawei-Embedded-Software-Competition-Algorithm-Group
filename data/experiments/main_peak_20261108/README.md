# 2026-11-08 纯波形线上优化

[返回实验目录](../README.md) · [当日采用源码](best.cpp) · [逐次记录](state.json) · [授权](authorization.json)

用户授权30次，方案只根据线上正式总分选择。历史峰位可用于形成假设，提交代码不包含已知坐标、特定N到峰位分派或回复指纹。通用步长、窗口与容错规则仍属于待验证的启发式参数。

当前采用正式 **217614** 分，SHA256 `a87714acc894b2921c10a1ab65a2583916d29783c951502460d79620eff89bee`。历史含样例适配的224148仅作突破目标。

| 方案 | 正式分数 | 相对提交前最佳 | 状态 |
| --- | ---: | ---: | --- |
| trial01_competitor_contour | None | None | failed |
| wave01_evidencescout | None | None | failed |
| probe03_cellbudget | 138801 | -75982 | completed |
| wave81_flatreach | 214783 | 0 | completed |
| wave82_tailprobe | 209116 | -5667 | completed |
| wave83_intervalfine | 214596 | -187 | completed |
| wave84_shapescout | 207996 | -6787 | completed |
| wave85_modeltight | 214671 | -112 | completed |
| wave86_modelguard | 214774 | -9 | completed |
| wave87_startdense | 191694 | -23089 | completed |
| wave88_paired | — | — | failed |
| wave89_wideaudit | 214210 | -573 | completed |
| wave90_maincover | — | — | preflight_failed |
| wave91_mainverify | — | — | preflight_failed |
| wave92_relativetolerance | 212450 | -2333 | completed |
| wave93_statisticalsignal | 177260 | -37523 | completed |
| wave94_quantilefloor | 216531 | 1748 | completed |
| wave95_noiselocal | 197498 | -19033 | completed |
| wave96_maincover | 214783 | -1748 | completed |
| wave97_mainverify | 212923 | -3608 | completed |
| wave98_maincoherent | 213406 | -3125 | completed |
| wave99_basinunion | 216532 | 1 | completed |
| wave100_winnerfrontier | 216532 | 0 | completed |
| wave101_mainall | 184026 | -32506 | completed |
| wave102_sweepcover | 173232 | -43300 | completed |
| wave103_staggered | 204586 | -11946 | completed |
| wave104_tailvalley | 216475 | -57 | completed |
| wave105_multiguard | 215888 | -644 | completed |
| wave106_nocentercap | 213682 | -2850 | completed |
| wave107_fitstop | 217614 | 1082 | completed |
| wave108_burstsupport | 201690 | -15924 | completed |
| wave109_zerosalvage | 217614 | 0 | completed |

本地只检查编译、交互、Q≤199、O≤6和实际停在已查询原始最大值。合成曲线仅验证分支确实改变查询，零分与失败完整保留；不以其分数筛选线上方案。聚合线上分数不能指出具体哪个隐藏样例为零，也不能证明任意数组均找对主峰。

部分本机启动被Windows应用控制4551阻止：仅当所有实际运行项通过原协议断言、未运行项均为查询前启动拒绝时，另行核对源码来源与查询/振荡/停车内核。未运行项不冒充26项通过；逐项结果和源码审计证书保留在rounds目录。

未知或待判任务只恢复原任务；不会重传。所有正式源码按原字节归档。日志和策略沿袭见本目录JSON文件。

2026-11-09补记：此前wave88_paired原作品已连续确认internal_error，没有正式数值分，已按原任务回填状态，未重传。
