# R_geo/Z_geo 轨迹控制新路线：架构提案与研究边界

> **Exact observation and A4 support amendment (2026-08-14):** from the fixed
> 1100 ms takeover onward, the controller observes the current true, noiseless
> same-step paired-boundary `R_geo/Z_geo` and same-step `Ip` before every 1 ms
> action issue. Missing/invalid boundary data fails closed. All causal
> observations and controller-owned issued/quantized/applied/readback/queue
> history accumulated since takeover are available, although the model may
> compress them. This does not assert pre-1100 ms history, and the next/future
> state remains unknown before issue. The observer/belief is therefore for
> latent memory and future-response/model uncertainty, not current or past RZI
> measurement.
>
> The separate zero-TSC A4 support audit returned
> `ONE_MS_NR2R2C2AA4_LATE_STATE_CAUSAL_SUPPORT_FAIL_NO_TSC`: 16/32 transitions
> have direct support and the first gap is issue16 -> effect17, level2
> effect-age 15. A4 remains unimplemented/unrun. Exact state16 knowledge,
> margins and empirical stop thresholds are not a pre-action bound on state17.
> Before new TSC, the route must separately freeze either an independent
> transition tube or a simulator-only empirical exploration contract. This
> result authorizes neither TSC nor controller/model work.

> **Post-C2aA3 route amendment (2026-08-14):** the final objective remains
> finite-domain two-axis relative/path/waypoint tracking; source hold is only
> a bootstrap step toward a qualified terminal/recoverable set. A2/A3 show
> that p03 is aligned with the
> source-drift correction and that cumulative `0.3 A/step` authority matters,
> but the qualified level2 R/Z response norm is only `5.07%` of q0's source-
> drift norm at state16.
> Scalar `delta R-delta Z` is henceforth only a source-drift diagnostic, not a
> two-axis authority claim. The already frozen A4 campaign is retained once,
> unchanged, as a late-tail plus hold discriminator, conditional on a separate
> zero-plant late-state support/margin gate. A safe scientific FAIL ends the
> single-p03 static dwell/level ladder; PASS still requires fresh Nominal-H1. In
> parallel, matched-prefix signed/cumulative vector authority and local
> recourse must qualify before transport, atlas or controller work. The
> structured causal-model, recovery-backed constrained-MPC and later shadow-
> adaptation architecture is unchanged. See
> `docs/codex/reports/RGEO_ZGEO_1MS_POST_C2AA3_DEEP_ROUTE_REVIEW.md`.

> **NR2R2C2aA4 prospective amendment (2026-08-14):** inside the finite
> q0/level1/level2 domain qualified by A3, the next discriminator holds the
> maximum p03 level continuously through 32 ms and applies the unchanged
> source short-hold gates. This is a direct authority bound for one persistent
> schedule, not a general proof over switching laws and not a controller.

> **NR2R2C2aA3 evidence amendment (2026-08-14):** two exact p03 level2
> replays passed the adjacent cumulative-domain gates. Total opposition
> averaged `0.74192 mm`; incremental level2-over-level1 opposition averaged
> `0.38599 mm`, with both signs positive at all 14 states. This supports one
> finite time-varying q0/level1/level2 C2a design. It does not establish hold,
> linear scaling, arbitrary cumulative range, recovery or a model/controller.

> **NR2R2C2aA3 prospective amendment (2026-08-14):** the user's cumulative
> `0.3 A/step` authority is now tested explicitly rather than keeping every
> target within q0+/-0.3 A. The first expansion is only one additional exact
> p03-minus level, repeated twice with a pre-result successor bound and
> incremental comparison against the frozen level1 path. This adjacent-level
> sentinel does not assume linear scaling or authorize a general cumulative
> action domain.

> **NR2R2C2aA2 evidence amendment (2026-08-14):** all three minus-sign
> directions completed safely and were positive at all 14 authority states,
> but none passed every frozen gate. P03-minus had the strongest persistent
> response (`0.35593 mm` mean, `0.52328 mm` maximum) and failed only the
> unchanged maximum gate. C2aA2 remains FAIL. The architecture therefore
> advances only to a separately frozen repeated cumulative-level safety and
> incremental-gain discriminator along p03-minus; this is not permission to
> lower C2aA2 gates or begin model/MPC work.

> **NR2R2C2aA2 prospective amendment (2026-08-14):** after p07-plus level2
> failed persistent authority, the next finite discriminator is frozen to
> three development-selected minus-sign directions inside componentwise
> `q0+/-0.3 A`. It retains the same persistent opposition and hard interface
> gates; it does not lower thresholds, fit a response model, move the command
> center beyond the independently supported cube, or authorize Nominal-H1.
> Any passing candidate still requires a separate fresh repeated validation.

> **NR2R2C2aA1 evidence amendment (2026-08-14):** a componentwise q0+/-0.3 A
> p07-plus level safely completed 64/64 authentic 1 ms advances and exact
> paired replay, but failed persistent authority. Mean q0-drift opposition was
> `0.00708 mm`, only 2/14 states were positive, and level2 was worse than
> level1 at all 14 measured states. This rejects that static direction, not
> cumulative-slew control or global reachability. The next discriminator must
> first compare a small prospectively frozen sign/direction family inside the
> already supported cube; it may not unlock hold/recovery/model/MPC stages.

> **NR2R2C1a evidence amendment (2026-08-14):** canonical-source full-prefix
> replay mechanics passed its finite 12-reset/136-advance envelope, while the
> 56.54 s worst complete branch rejects 1 ms online-Oracle use. Generated
> `sprsina` remained non-hash-identical, so snapshot restart is still a
> separate claim. C1a permits prospective C2a nominal active-hold design only;
> it supplies neither novel-action successor safety nor hold/recourse/model/
> controller evidence. See the tracked C1a result report.
>
> **Post-NR2R2B0 route amendment (2026-08-13):** the architecture below is
> retained. The immediate dependency chain is canonical-source full-prefix
> replay -> finite nominal active hold -> bounded-tube contingency -> minimal
> tail/response evidence -> recovery-backed context atlas. In parallel,
> independent `sprsina` semantics and finite snapshot/common-suffix behavior
> claims jointly bound only the faster snapshot-based moving-prefix route. B0's
> frozen `sprsina` byte-hash FAIL and q0 short-hold FAIL both remain; neither
> is a hidden-state theorem or proof that active hold is impossible. A tiny
> TSC-only discriminator may bootstrap only when each issued primitive has an
> independent one-step worst-case successor bound inside the frozen outer
> envelope; an outer envelope and immediate stop alone are insufficient.
> Transport/atlas/controller execution still requires bounded-tube active
> recourse. Before any controller, the legacy runner's generic
> `magaxis/rc/zc` R/Z path must be excluded; the control path must also refuse
> excess current/delta requests before the runner without relying on or
> triggering its silent clipping. Exact reasoning and authorization boundaries
> are recorded in
> `docs/codex/reports/RGEO_ZGEO_1MS_POST_NR2R2B0_DEEP_ROUTE_REVIEW.md`.

> **Post-NR2R1 implementation-order amendment (2026-08-13):** the main
> architecture below is retained, but NR2R1 showed that its execution order
> was too aggressive.  A single-start, 16 ms model bake-off did not implement
> the required operating-point/history coverage or explicit low-order memory.
> Before another model comparison, the route now requires contextual
> identifiability, independent drift/recovery baselines, repeated actions over
> position and arrival-history anchors, and a separate growing-prefix branch-
> replay qualification.  Within-run adaptation begins only in shadow mode and
> may update bounded low-dimensional belief/context/gain parameters, not deep
> weights.  The evidence and revised order are recorded in
> `docs/codex/reports/RGEO_ZGEO_1MS_POST_NR2R1_ARCHITECTURE_REASSESSMENT.md`.
> NR3 remains blocked.

> **Confirmed timing/action amendment (2026-08-13):** development restarts
> from NR0 with a 1 ms control period. For each of the 14 coils in TSC order,
> the hard per-step limit is the single-turn-current condition
> `|I_i[k+1] - I_i[k]| <= 0.3 A`. Equality is allowed; the architecture must
> not invent an undisclosed headroom reservation. TSC Card15 remains in
> kA-turn and must be converted using the explicit per-coil turn count. The
> old 10 ms / 3 A NR0--NR2 route remains historical and cannot qualify the
> new identity. No coordinate, Ip, queue/effect, Card15, safety, or evidence
> rule below is weakened by this amendment.

状态：**v1 已获用户确认；1 ms NR0 已通过，1 ms NR1 已前瞻冻结并获授权**

日期：2026-08-12

本轮权限：NR0 仓库接口与 synthetic 测试；没有改现有控制语义、部署、运行新
TSC、训练模型、测试 Oracle 或实现 MPC/RL。

2026-08-13 的 NR0 实现把本文件第 3/6/9 节落实为独立纯合同模块：显式成对
边界、限制器中面、Ip、命令、动作各阶段、queue、实际电流、缺测标记和证据
用途均 fail closed。该模块尚未接入环境或控制器；它不是 NR1 或真实闭环资格。

## 1. 路线切换的含义

用户已决定不再把旧 Stage4.2/R8 系列的“固定局部响应模型逐级修补直至
MPC 专家”作为当前主路线。旧路线在切换前的本地保存检查点是
`cbdf874`。这是一项**前瞻性的路线作废决定**，并不改写任何既有原始
结果：过去的 PASS/FAIL 仍只在各自冻结的有限合同内有效。

新路线允许从模型和控制架构层面重新开始，但应复用已经证明有价值的
基础设施：真实 TSC 执行、1100 ms restart、因果前缀审计、Card15 实际
动作边界、逐步 raw/snapshot/hash 证据和 Windows/server 验证流程。

旧 probe、sentinel 和审计轨迹不得因路线切换而追溯改名为专家数据或
学习数据。若以后训练，新数据必须在生成前获得独立的 learning/ID 身份。

## 2. 唯一最终目标

从固定 `1100 ms` 接管，在合理、有限的工作域内，使限制器位形等离子体的
几何中心安全、因果地大体跟随用户给出的 `R_geo/Z_geo` 指令。指令可为：

1. 相对当前位置的 `ΔR/ΔZ`；或
2. 分段光滑的 `R_geo_ref(t), Z_geo_ref(t)` 路径/waypoint 序列。

不要求零误差、全局最优、最快移动或无限工况下完美控制。移动时间可以
协商；旧路线的 250/270 ms 到达门不再约束新路线。未来一次命令若被接受，
应在执行前冻结可接受的时标，不能看结果后无限延长。

若用户只给终点，规划器可以选择安全几何路径和时间；若用户给了完整路径，
规划器只能按事先约定重定时，不能擅自改几何路径或 waypoint 顺序。

## 3. 输出量与 LFS/HFS 的确定定义

### 3.1 R_geo/Z_geo

我建议本项目把 `R_geo/Z_geo` 明确定义为同一条、同一时间步有效等离子体
边界的包围盒几何中心：

```text
R_geo = (min(R_boundary) + max(R_boundary)) / 2
Z_geo = (min(Z_boundary) + max(Z_boundary)) / 2
```

这是对用户所说“简单直接的几何中心”的独立工程建议，并非当前 TSC 已有的
一对唯一原生字段。用户发送配套的新对话开场词即表示接受这一定义；若用户
想要另一种几何中心公式，应在 NR0 开始前明确替换，而不能边实现边改变。

它不是磁轴 `xmag/zmag`，不是电流质心，也不是现有 `gfile.py` 中可回退到
磁轴的 pressure-weighted `rc/zc`。R、Z 必须来自同一边界和同一时间步；
边界缺失、非有限或无效时应 fail closed，不得分别拼接或静默回退。径向
原生 `RGEO` 可作为诊断量，但不得与另一种定义的 Z 混成受控坐标。

### 3.2 LFS/HFS

LFS/HFS 不是用户输入，不是要由 LSTM 推断的隐藏模式，也不是两个互不连通
的控制任务。按用户给定的确定几何规则：

```text
R_mid = (R_inner_limiter_midplane + R_outer_limiter_midplane) / 2
R_geo <  R_mid  -> HFS / 内侧区域
R_geo >= R_mid  -> LFS / 外侧区域
```

这是用户给定的几何标签规则，不另行推断接触状态。允许一条轨迹多次发生
LFS→HFS、HFS→LFS 和往返。控制模型可将
`R_geo - R_mid` 作为连续调度特征，并在中点附近使用预先冻结的平滑混合，
但这不创造第三种物理位形，历史状态也不能在跨越时重置。

### 3.3 Ip

`Ip` 不是用户命令维度，但也不能假定“加热会自动精确保持”而从模型中删除。
它应作为耦合观测/预测状态：跟随既有场景参考或允许带是软目标，独立硬安全
带不可交易。只有以后从真实 TSC 接口证明存在并足以解耦的独立 Ip 环，才可
进一步简化控制分配。

## 4. 对“每一步尝试后再决定”的专业定性

`t0` 执行一步、`t1` 读取新状态、再决定下一步，本身是闭环反馈或滚动时域
控制，并不自动等于 RL：

- 只重新计算动作而不更新模型/策略：反馈控制或 receding-horizon MPC；
- 用新转移更新局部动力学再规划：在线系统辨识 + adaptive MPC；
- 动作还显式权衡信息增益与跟踪收益：dual control/dual MPC；
- 从转移更新 policy/value 并优化多步累计奖励：online/model-based RL。

因此“当场训练一个局部专家”不是合适的工程名称。更准确的表述是：
**历史条件化的局部状态估计与在线系统辨识，再由约束规划器逐步决策**。

## 5. 推荐的总体架构

推荐的主干名称：

> **历史条件化、带不确定度的约束滚动控制**
>
> History-Conditioned Uncertainty-Aware Constrained Receding-Horizon Control

```text
用户终点/路径
      |
轨迹合同与 reference governor（路径保持、可行时标）
      |
因果 history observer / belief state
      |
+--------------------------------------+
| 主干：结构化概率模型 ensemble       |
| 可选：TSC 分支 Oracle/教师候选       |
+--------------------------------------+
      |
约束滚动规划：只选下一步实际可表示动作
      |
独立硬接口：Card15/电流/slew/queue/Ip/hold-abort
      |
TSC 执行一步 -> 新观测 -> 更新 belief -> 重复
```

主干是结构化历史模型和约束滚动控制。TSC Oracle 是很有价值、但必须先
资格化的可选工具：若成立，它可减少模型臆测并产生高质量教师决策；若不
成立，主干仍可独立发展。当前仓库没有 head-to-head 证据证明该主干必然
优于 outer RL；优先顺序来自本任务“参考已知、时间宽松、约束强、要求可
审计”的工程判断，不是文献已经给出的本项目结论。

### 5.1 可选工具：TSC 分支 Oracle / rolling shooting

本项目的目标 plant 当前就是 TSC，用户也不要求很短的壁钟时间。因此第一
候选不是让主轨迹承担随机探索，而是在同一因果前缀的克隆分支中评估多条
有限候选动作序列，再只在主干执行最佳序列的第一步。

如果将来不能直接保存任意时刻的完整 moving-state snapshot，可从认证的
1100 ms snapshot 重启，精确重放截至当前的 issued/quantized/applied 动作
前缀；只有重放前缀与主干一致的分支才可作为未来预测。这是未来资格条件，
不是本文件声称已经具备的能力。

Oracle 搜索应作用在**实际 Card15 后动作**或重新辨识的有限安全 primitive
上，而不是默认继承旧 3-SVD、4D basis 或连续 14 维高斯动作。候选算法可
比较 beam search、CEM、MPPI 或短时域直接 shooting；算法名称不是先验结论。

Oracle 的优势只属于同一 TSC 数字孪生。它不能被表述为真实装置的可部署性
或 sim-to-real 安全证明。

### 5.2 主干：历史条件化的结构化概率模型 + 约束 NMPC 候选

可扩展主控制器不再采用“当前 R/Z 对应一个固定局部 Jacobian”的假设，而是
维护一个由完整因果历史更新的 belief state，并输出多步预测分布。推荐起点：

1. 显式保留可知状态和执行器语义；
2. 用稳定的低阶状态空间记忆表示被动导体/涡流等慢动态；
3. 用小型 GRU 只学习剩余的非线性 observer/dynamics residual；
4. 用 bootstrap/probabilistic ensemble 表示模型分歧；
5. 由带不确定度的约束 NMPC 在模型分布上滚动规划，而不是让 RNN 直接发
   14 路线圈动作。

只有将来取得校准的多步误差边界、合适的约束收紧、terminal/recovery set
和递归可行性证据后，才可把它称为 robust/adaptive NMPC；ensemble 分歧
本身不构成鲁棒性或安全保证。

推荐的模型骨架是“精确 queue + 受稳定性约束的低阶显式记忆 + neural
residual”。一个 shared belief 贯穿整条轨迹；已知的 `R_geo-R_mid` gate 可
调度 H/L 局部 dynamics head，在窄过渡带连续混合并允许一个 interaction
residual。未来多步预测应按预测出的 `R_geo` 递推 gate，而非锁死当前标签。
该平滑只服务数值建模，不产生第三种位形。

推荐 GRU 只是合理首选，不是冻结答案。必须在相同的 whole-trajectory、
whole-history 隔离数据上，与显式有限窗/ARX/LPV/classical state-space、
causal TCN、LSTM 或小型 RSSM 公平比较，选择达到门槛的最简单模型。LSTM
的“记住历史”直觉是正确方向，但更多参数和 gate 并不自动得到正确物理
记忆。IMM 不作为核心，因为位形标签已知；S4/Mamba 等长序列模型也不作为
第一版，除非消融证明确有超长记忆且简单候选不能满足。

## 6. 历史如何进入模型

历史不是仅把若干帧 `R/Z` 塞入网络。自 1100 ms 接管后，完整因果历史由接口
保留；模型选择有限窗或压缩 belief 是表示选择，不表示其余历史不可见。每个
动作签发前，当前 `R_geo/Z_geo/Ip` 是无噪声真值输入，其测量协方差为零并保留
直接通路，不由 observer 重构。observer 只表征未观测慢记忆及未来动力学不确定
度；动作后的下一状态仍须等 TSC advance 后才能观测。每步的因果输入至少包括：

- `R_geo/Z_geo/Ip` 及有效性、时间戳和必要的差分量；
- 14 路实际线圈电流，以及部署时确实可取得的被动/结构电流；
- issued、serialized/量化后、applied/readback 动作，精确 delay FIFO 和
  action age；
- `dt`、自 1100 ms 起的时间、异常/缺测 mask；
- `R_geo-R_mid` 及由它确定的 HFS/LFS 调度特征。

未来参考只进入 planner，不进入 plant dynamics model，避免模型利用目标标签
伪造因果预测。future action/outcome、source/history ID、restart hash 和部署
时不可见的 TSC 隐状态也不得作为模型输入。wire/passive current 只有部署时
真实可得才可输入，否则最多作为离线 auxiliary label。模型的 recurrent
state 在跨越 `R_mid` 时连续保持。

1100 ms 也是记忆初始化问题：若未来接口可提供部署时真实可得的 1100 ms
以前因果窗口，就用它 burn-in；否则使用独立的 1100 ms 状态初始化器/集合
先验并保留较大初始不确定度，不能简单把 hidden state 清零后称作真实历史。

推荐的三种更新时间尺度：

- 每个控制步：更新可观测状态、queue 和 hidden belief；
- 单次运行内：首版只更新 hidden belief、精确 queue 和审计过的 ensemble/
  Bayesian weight，深网权重冻结；以后只有 effect window 已完成、innovation
  仍在校准域且辨识条件合格时，才可能开放投影约束下的低维 context/bias/
  gain；中点过渡带先禁止参数更新，在线 uncertainty floor 不得缩小；
- 运行之间：用合规数据离线重训、校准和版本化完整 world model。

因此新路线会“不断累积经验”，但不会在一条轨迹中从零反向传播出一个未经
验证的深度专家。

未来 world model 的验收不能只看 one-step teacher-forced MAE。输出至少应
包括 belief posterior、多个时域的 `ΔR_geo/ΔZ_geo/ΔIp` 分布、约束相关电流
辅助量和 disagreement/OOD 指标；训练与选择应看 action-conditioned free
rollout 及不确定度校准。数据按完整 1100 ms source/history/snapshot family
分组，所有 sibling branches 必须进入同一个 split，并把训练、校准和一次性
blind holdout 分开，禁止按 step 随机拆分造成历史泄漏。

## 7. RL、ILC 和直接 recurrent policy 的位置

“外层 RL 规划、内层自适应控制”可以借鉴，但不应成为第一版：

- 用户给完整路径时，高层可做的主要是调时标，确定性优化器通常更透明；
- 用户只给终点且路径选择复杂时，outer RL 才可能有额外价值；
- 内层 adaptive controller 和独立安全层仍是必需的，RL 不是安全来源。

未来最合理的 RL 用法，是把已合格 Oracle/MPC 的昂贵搜索摊销成冻结策略，
或只输出 waypoint、pace、有限 primitive/残差。reward-trained policy 本身
不构成安全证明；在本项目中仍须经过同一独立安全层。它必须在相同命令、
TSC 预算和同一安全层下证明可测收益；若 MPC 已能满足粗略跟踪，最终不使用
RL 是完全合格的结果。

鉴于本项目当前证据和审计要求，直接 recurrent policy 更适合作为 Oracle/
MPC 蒸馏后的快速 student，而不作为首个安全基线。经典 ILC 最适合高度重复
的初态和任务；虽有变参考等扩展，但本项目没有证据让它承担任意新轨迹，
因此只把它作为重复命令的 feedforward 增强器。

主动 online model-based RL/dual exploration 放在最后。若 Oracle 分支可以
在不污染主干的克隆中探索，就没有理由让主轨迹承担同样的辨识风险。

## 8. 路线优先级

| 优先级 | 候选 | 推荐角色 | 主要诚实边界 |
|---:|---|---|---|
| 1 | history-conditioned uncertainty-aware constrained NMPC | 可扩展主控制器 | 尚未取得 robust/recursive-feasibility 资格 |
| 2 | TSC branch Oracle + shooting/CEM/MPPI | 待资格化的可达性工具、教师，可能是慢速控制器 | 任意时刻分支、完整前缀和成本尚未资格化 |
| 3 | outer RL + inner adaptive controller | 有明确增益后才加入 | 可能不优于确定性规划，还增加验证负担 |
| 4 | recurrent student / ILC | 蒸馏加速或重复轨迹增强 | 不能独立承担 OOD 和硬安全 |
| 5 | online MBRL / dual control | 后期小幅信息动作 | 延迟、量化、错归因和主轨迹探索风险最高 |

当前最有希望的组合不是押注单个算法，而是：**以结构化历史模型和约束
NMPC 为主干；若 Oracle 资格通过，就用它直接询问 TSC、提供教师与审计；
RL 只竞争剩余的可测收益。**

## 9. 独立安全与成功定义

点动作投影只能限制瞬时动作，不能证明后续状态安全。未来安全层至少要独立
处理实际 Card15 可表示性、线圈绝对电流和 slew、动作 queue、Ip 硬带、有限
R_geo/Z_geo 工作域，以及 hold/减速/abort。接受一个动作还应保留一条已资格
化的 recovery continuation；预测分歧、OOD、无进展或求解超时应触发减速、
hold 或退到安全 waypoint。任何安全 stop 可算安全机制工作，但对应跟踪 case
仍是 FAIL，不能把“一直拒绝”算作成功。中点 corridor 任一侧若没有合格的
hold/recovery，就不得执行 crossing。

新路线成功只在前瞻冻结的有限工作域和轨迹类内声明，至少覆盖水平、垂直、
斜向、弯曲路径、hold、多 waypoint、两个方向跨 `R_mid` 和往返；分阶段从小
域扩展是工程顺序，不得把最终目标偷换成两个单侧控制器。

## 10. 后续阶段（本轮不执行）

下一对话建议一次只授权一个阶段：

1. **NR0 — 接口与实现合同**：把上述坐标、命令、因果历史、动作、Ip 和证据
   身份落实为代码级规格与测试；只做仓库工作，不运行新 TSC。
2. **NR1 — 安全基础与可选 Oracle 资格**：在用户另行授权后，先建立 hold/
   abort/recovery 和合规数据采集边界；再检查分支/前缀重放能否作为因果预测
   工具并测量成本，失败时不强行包装为 Oracle。
3. **NR2 — 有权限的数据与历史模型比较**：生成前冻结用途，按完整 history/
   trajectory 分组；比较简单模型、GRU、LSTM/TCN 等的多步预测和不确定度。
4. **NR3 — 约束滚动控制**：先慢速、小工作域、同侧和二维，再扩大到跨中点。
5. **NR4 — 连通工作域资格**：双向 crossing、往返、多 waypoint、不同历史；
   只声明实际通过的有限域。
6. **NR5 — 可选学习收益门**：比较 outer RL、蒸馏或有界在线适应；无实用
   收益就结束在非 RL 控制器。

任何阶段失败都必须区分接口/部署/数据/模型/规划器/真实闭环结果；不得用
学习算法掩盖不存在的物理 authority，也不得从同一 TSC Oracle 的成功外推
到真实装置。

为避免重新进入无限微阶段修补，出现以下任一情形应停止当前模型路线并重新
判断，而不是只扩大网络或继续加 probe：坐标/实际动作/effect timing 语义不
唯一；同等因果历史与动作仍有不可覆盖的响应冲突；whole-history blind
holdout 的多步区间系统性欠覆盖；安全 hold/recovery 不成立；在宽松时标下
高保真规划仍找不到合理小位移；复杂 recurrent 模型不显著优于简单因果基线。

## 11. 关键文献与独立判断依据

- Degrave et al., TCV 深度 RL 磁控制：训练在模拟器中完成，硬件部署为冻结
  策略，不是实机在线盲试。<https://www.nature.com/articles/s41586-021-04301-9>
- HL-3 先用历史日志离线训练 LSTM 动力学模型，再在该模型内训练 PPO；这
  支持历史建模，但不证明 LSTM 或 online RL 必然最优。
  <https://www.nature.com/articles/s42005-025-02302-y>
- TCV 实验 MPC 使用上层 MPC 优化内层磁控制参考，支持约束层级架构。
  <https://arxiv.org/abs/2506.20096>
- Learning-based MPC 综述。<https://doi.org/10.1146/annurev-control-090419-075625>
- Dual control 与 Bayesian RL 的探索—控制关系。
  <https://www.jmlr.org/papers/v17/15-162.html>
- DIII-D 展示了先从历史日志建模、再训练 model-based RL 的具体实例；这不
  是所有昂贵装置的普遍最优性证明。
  <https://proceedings.mlr.press/v211/char23a.html>
- PETS 在通用 benchmark 上给出 probabilistic ensemble + MPC 的样本效率
  证据，不是 tokamak 安全性证明。
  <https://proceedings.neurips.cc/paper/2018/hash/3de568f8597b94bda53149c7d7f5958c-Abstract.html>
- Predictive safety filter 的保证依赖明确的概率误差、约束与 terminal/
  recovery 假设，不是简单动作裁剪。
  <https://doi.org/10.1016/j.automatica.2021.109597>
- Tokamak 部分可观测性模拟研究显示具有差分/积分归纳偏置的简单历史模型
  可能比通用 recurrent/Transformer 更稳健；这不是本项目实证。
  <https://arxiv.org/abs/2307.05891>
- Robust adaptive MPC 理论可参考 Lu、Cannon 与 Koksal-Rivet；其有界参数
  等假设不能直接搬到 TSC 黑箱。<https://arxiv.org/abs/1911.00865>

## 12. 提案结论

1. 新问题不是“换一个更大的神经网络”，而是重新建立历史条件、实际动作
   语义明确、带不确定度和独立约束的滚动控制系统。
2. 用户关于历史很重要的直觉是正确的；专业实现应是 structured belief
   observer，GRU/LSTM 只是候选组件。
3. TSC 分支 Oracle 是值得尽早问清的可选工具，但本文件不声称它已通过，
   它失败也不阻断结构化历史模型主干。
4. 主控制器优先研究结构化概率模型 + 带不确定度的约束 NMPC；在满足额外
   理论和证据条件前不称其为 robust。
5. 外层 RL 可以借鉴，但必须后置并通过增益门；不做 RL 仍可完成最终任务。
6. 本文件提出方案并等待用户通过发送配套开场词确认；没有开始实现或实验。
