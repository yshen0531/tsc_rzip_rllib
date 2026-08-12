# 新对话建议开场词：R_geo/Z_geo 新控制路线

下面代码块可在本仓库的新 Codex 对话中直接发送。它只授权新路线的
`NR0` 阶段；完成后应暂停，避免新对话未经确认直接运行大规模 TSC。

```text
请先完整读取仓库根目录 AGENTS.md，然后依次完整读取：

- docs/codex/TOKAMAK_RL_PROJECT_CONTEXT.md
- docs/codex/SERVER_WORKFLOW.md
- docs/codex/CURRENT_TASK.md
- docs/codex/CURRENT_STATUS.md
- docs/codex/RGEO_ZGEO_NEW_CONTROL_ARCHITECTURE.md

不要依赖聊天摘要。以上述本地文件、真实代码和已有原始证据为准。

首先检查仓库根目录、当前分支、git status、最近提交、远程跟踪状态和所有
未提交差异。保留全部用户文件与既有修改，不 reset、clean、stash、覆盖或
删除任何未知文件。旧路线切换前的保存检查点是 cbdf874；新路线文档提交
以当前实际 git HEAD 为准。

这是一个新的控制架构任务。最终目标是：每次从固定 1100 ms 起手，在前瞻
声明的合理有限工作域内，使限制器位形等离子体的边界包围盒几何中心
R_geo/Z_geo 安全、因果地大体跟随用户给出的相对位移、路径或 waypoint
指令。时间可以协商，不沿用旧 250/270 ms 到达门；不要求零误差、全局最优
或无限工况完美控制。

发送本提示即表示我接受方案文档建议的精确定义。坐标必须使用同一条、同一
时间步有效等离子体边界：

R_geo = (R_boundary_min + R_boundary_max) / 2
Z_geo = (Z_boundary_min + Z_boundary_max) / 2

边界缺失/无效时 fail closed。不得分别拼接 R/Z，也不得把 xmag/zmag、
pressure-weighted rc/zc 或任意 silent fallback 当作 R_geo/Z_geo。LFS/HFS
不是用户输入或隐藏模式：

R_mid = (R_inner_limiter_midplane + R_outer_limiter_midplane) / 2
R_geo < R_mid 为 HFS；否则为 LFS。

轨迹允许从 LFS 移到 HFS、从 HFS 移到 LFS并多次往返；历史/belief 在跨越
R_mid 时不得重置。Ip 不由用户命令，但必须作为耦合观测和软保持/硬安全量，
不能未经证据假设加热会自动精确保持。

候选架构不是“从零在线训练 LSTM/RL 专家”，而是：

1. history-conditioned、带不确定度的约束滚动控制作为主干；
2. TSC branch/prefix-replay rolling Oracle 作为尚待资格化的可选教师；
3. 显式执行器/queue + 低阶记忆 + GRU/LSTM/TCN 等 residual 候选在 NR2
   公平比较，不在 NR0 预选模型；
4. reference governor + uncertainty-aware constrained NMPC candidate；
5. 独立 Card15/电流/slew/queue/Ip/hold-abort 硬接口；
6. outer RL、direct recurrent student 或 ILC 只在后续证明有实际增益时加入。

本次只授权 CURRENT_TASK.md 定义的 NR0：接口与实现合同。请完成真实代码
审计，并只以纯接口、schema/dataclass、解析/验证器以及 synthetic/仓库 fixture
tests 的形式，实现最小且可审查的 R_geo/Z_geo 信号与因果历史/动作数据
合同。不得改变现有 controller、reward、termination、Card15 量化、queue
生效时刻或 TSC state semantics；发现真实字段缺失就记录 BLOCKER 并暂停，
不得伪造 fallback。NR0 不得运行新 TSC、部署或写服务器、读取服务器 raw
作为 fixture、训练/拟合模型、进行 Oracle 分支实验、实现 MPC/RL 或生成任何
数据。服务器默认不访问；只有为避免臆测真实接口而绝对必要时，才先说明
目的并按 SERVER_WORKFLOW 做最小只读核验，且不得下载训练/fixture 数据。

开始 NR0 前，确认当前已同步文档检查点（见本提示下方记录）存在且 tracked
工作树没有未知改动，再从该检查点新建一个聚焦分支，例如
codex/rgeo-zgeo-history-control。这个新对话文本明确授权该次新建和切换；
若同名分支已存在或工作树有冲突，停止并报告，不覆盖任何内容。

本地只在当前 VS Code 仓库内工作，只使用项目虚拟环境；不得本地压缩或
解压。服务器若以后获准执行，只能使用既有服务器虚拟环境。旧 probe、
sentinel 和审计轨迹继续禁止追溯改成专家/学习数据。始终区分接口错误、
部署错误、统计错误、模型失败、规划器失败和真实闭环结论。

只可精确 stage 本次 NR0 自己修改的文件；禁止 `git add -A`，不得提交或清理
现有 untracked evidence、缓存或用户文件。请自主完成 NR0，验证、建立小而
清晰的提交并推送远程代码库，然后暂停，
向我汇报：采用的精确定义、修改文件、测试证据、仍未决问题，以及 NR1
是否值得授权。NR0 PASS 仍不授权 NR1 设计/实现、server package/deploy、
snapshot/branch/prefix-replay、任何 TSC、训练或数据生成。未经我确认，不
越过 NR0。
```

当前已同步文档检查点标签：`rgeo-zgeo-route-proposal-v1`。开始前请确认该标签
存在并指向包含本提示与新架构文档的提交；若不存在或不一致，停止并报告。

若希望新对话仍停留在设计审查、不写代码，只需把倒数第二段改为：

```text
本次只做 NR0 的只读代码审计和实施计划，不修改任何文件；完成后暂停。
```
