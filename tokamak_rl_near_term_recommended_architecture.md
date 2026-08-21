# tokamak RL 近期推荐控制架构方案

> **2026-08-21 ID2Z35 route amendment:** the two-phase componentwise min--max
> sparse-event box failed fresh calibration even though non-event prediction
> remained accurate. Calibration rows stay zero fit weight and blind stayed
> unopened. Permit one new robust-event candidate with event-width floors fixed
> from pre-existing engineering caps, followed by entirely fresh calibration
> and blind validation. Do not search widths or add a third model. A PASS would
> still be only a finite response-set qualification; Authority-L0 and
> Recourse-L1 remain independent axes before any in-loop controller.

> **2026-08-20 active route amendment:** before another learned predictor or
> rolling controller, qualify finite sustained `Authority-L0` with exact
> per-millisecond R_geo/Z_geo/Ip feedback under the signed rank-four Card15
> action grammar. Keep three claims separate: Authority-L0, a repeated
> six-state nominal capture seed, and bounded-tube Recourse-L1. Authority
> PASS may open event/candidate-value model development; capture may open
> Recourse-L1 in parallel. A real controller requires fresh model
> calibration/blind holdout, Recourse-L1 and the independent hard interface
> to pass together. Exact return, hold, replay or simulator safe-stop is not
> recovery. This amendment supersedes older near-term sequencing below but
> retains the final two-axis waypoint/path and repeated R_mid-crossing goal.

## 1. 方案名称

**增广信息状态驱动的安全鲁棒自适应 MPC**

英文可记为：

**Safety-Constrained Robust Adaptive MPC with Augmented Information State**

近期主线不训练新的在线 actor，不让 RL 直接控制 14 个线圈。控制器以现有物理模型、低维 SVD 控制空间和冻结专家基线为基础，在每个控制周期利用新测量更新局部模型与不确定度，再由受约束 MPC 重新求解下一步动作。

---

## 2. 近期目标

构建一个能够在单次放电过程中完成以下闭环循环的控制器：

1. 读取当前 R、Z、Ip、线圈电流和动作队列；
2. 估计速度、隐藏动态及模型参数；
3. 利用最新真实转移更新局部动力学模型；
4. 根据剩余到达时间、目标和安全约束重新求解 MPC；
5. 只执行当前一步动作；
6. 获得下一时刻测量后继续更新与决策；
7. 模型置信度不足或优化不可行时，自动回退到冻结安全基线。

近期重点是：

- 在线状态与参数适应；
- 显式 delay queue；
- 不确定度感知；
- 被动学习；
- 鲁棒 MPC；
- 安全回退；
- 原正式到达时间不变。

---

## 3. 正式控制合同

除非用户明确修改，正式验收时间固定为：

```text
slew = 1.0 / 1.1：
  最晚 250 ms 到达
  保持并评价到 350 ms

slew = 0.9：
  最晚 270 ms 到达
  保持并评价到 370 ms
```

其余门槛保持冻结版本：

```text
R / Z 容差：30 mm
速度门槛：0.1 m/s
Ip 门槛：保持冻结基线定义
arrival streak：保持冻结基线定义
```

任何更长时域只能作为到达后的独立保持测试，不能替代或延后正式到达截止时间。

---

## 4. 总体架构

```text
测量与已知信息
R / Z / Ip
14 线圈电流
已发动作
pending delay queue
目标与剩余时间
        │
        ▼
┌──────────────────────────────┐
│ 增广状态与隐藏动态估计器       │
│ 速度、vessel/eddy latent      │
│ 状态协方差与异常检测           │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ 在线参数与局部残差辨识器       │
│ delay / gain / slew           │
│ 局部响应修正                   │
│ 参数协方差与可信集合           │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ 鲁棒自适应 MPC                │
│ 显式 delay pipeline           │
│ 到达、减速、保持约束           │
│ 状态与动作不确定度传播         │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ 独立安全核与 fallback          │
│ 电流 / slew / queue 守卫       │
│ 可行性检查与动作投影           │
│ 冻结专家回退                   │
└──────────────┬───────────────┘
               │
               ▼
         3 个 SVD 控制模态
               │
               ▼
             14 线圈
```

慢时标外层规划器位于鲁棒自适应 MPC 之上，只生成参考轨迹、阶段、终端集合和权重调度，不直接输出线圈动作。

---

## 5. 增广信息状态

近期不使用“完整 belief state”作为默认表述。控制器使用**增广信息状态**：

\[
\xi_t =
\begin{bmatrix}
\hat{x}_t \\
q_t \\
\hat{\theta}_t \\
P_t \\
\Sigma_{\theta,t} \\
r_t^{\mathrm{target}} \\
T_t^{\mathrm{remain}}
\end{bmatrix}
\]

其中：

### 5.1 已知或直接测量量

```text
R_t
Z_t
Ip_t
14 个线圈当前电流
当前已发动作
pending delay queue
当前目标
剩余到达时间
当前控制阶段
```

### 5.2 在线估计量

```text
vR_t
vZ_t
低阶 vessel / eddy-current 隐状态
局部响应增益
执行器 gain
执行器 slew
动作 delay
模型残差参数
```

### 5.3 不确定度

```text
状态协方差 P_t
参数协方差 Σθ,t
有界扰动集合
模型有效域
当前模型可信度
异常检测标志
```

pending queue 是控制器精确维护的扩展状态，不属于概率估计。

---

## 6. 动力学模型

基础模型保留当前项目已经验证的低维结构：

```text
3 个主要 SVD 控制模态
175 × 105 真实 TSC Jacobian
目标条件化参考轨迹
当前 observer
执行器 delay / gain / slew 模型
```

在线模型写为：

\[
x_{t+1}
=
f_0(x_t, u_{t-d})
+
r_{\theta_t}(\xi_t, u_{t-d})
+
w_t
\]

其中：

- \(f_0\)：冻结的物理基线或 lifted linear model；
- \(r_{\theta_t}\)：在线更新的低维局部残差模型；
- \(d\)：当前估计或可信确认的动作延迟；
- \(w_t\)：有界未建模动态与测量误差。

近期残差模型优先采用：

```text
低维线性残差
递推最小二乘更新
参数投影
遗忘因子
协方差输出
异常样本拒绝
```

不在单次放电内训练新的深度神经策略网络。

---

## 7. 在线参数与残差更新

每个控制周期获得真实转移：

\[
(\xi_t,\; u_t,\; y_{t+1})
\]

计算一步预测误差：

\[
e_{t+1}
=
y_{t+1}
-
\hat{y}_{t+1}
\]

更新局部模型：

\[
\theta_{t+1}
=
\Pi_{\Theta_{\mathrm{safe}}}
\left[
\theta_t
+
K_t e_{t+1}
\right]
\]

其中：

- \(K_t\)：递推更新增益；
- \(\Pi_{\Theta_{\mathrm{safe}}}\)：参数安全集合投影；
- \(\Theta_{\mathrm{safe}}\)：根据历史真实 TSC、辨识结果和执行器物理范围设定。

更新规则必须满足：

```text
参数变化率有界
高残差异常样本可拒绝
协方差不能伪造收敛
模型超出有效域时降权
不可信模型不得接管控制
```

---

## 8. 鲁棒自适应 MPC

MPC 在每个实时周期根据最新增广信息状态重新优化：

\[
\min_{u_{t:t+H-1}}
J_{\mathrm{track}}
+
J_{\mathrm{velocity}}
+
J_{\mathrm{effort}}
+
J_{\mathrm{smooth}}
+
J_{\mathrm{risk}}
\]

### 8.1 代价项

```text
R / Z / Ip 跟踪误差
vR / vZ 减速误差
线圈动作大小
动作变化率
终端状态误差
模型不确定度风险
安全余量消耗
fallback 触发代价
```

### 8.2 显式约束

```text
R / Z 安全区域
Ip 安全区域
14 线圈电流限制
线圈 slew 限制
3 个 SVD 模态限制
显式动作 delay pipeline
正式到达截止时间
终端减速约束
到达后保持约束
```

### 8.3 鲁棒处理

MPC 使用状态和参数不确定度进行约束收紧：

\[
x_k \in \mathcal{X} \ominus \mathcal{E}_k
\]

\[
u_k \in \mathcal{U} \ominus \mathcal{D}_k
\]

其中：

- \(\mathcal{E}_k\)：状态预测误差集合；
- \(\mathcal{D}_k\)：执行器与模型误差余量。

当不确定度过高时，控制器必须降低动作激进程度或回退冻结专家。

---

## 9. 独立安全核

安全核独立于在线学习器和外层规划器。

它负责：

```text
线圈电流硬限制
slew 硬限制
delay queue 顺序
动作维度与有限数检查
模型有效域检查
MPC 可行性检查
动作投影
fallback
异常状态停止或降级
```

最终执行动作：

\[
u_t^{\mathrm{exec}}
=
\Pi_{\mathcal{U}_{\mathrm{safe}}}
\left(
u_t^{\mathrm{MPC}}
\right)
\]

### 9.1 回退条件

出现以下任一情况立即回退：

```text
在线模型置信度不足
参数估计跳变
状态估计发散
MPC 不可行
预测轨迹进入安全边界
动作超出有效域
观测异常
delay queue 不一致
计算超时
```

### 9.2 回退对象

近期回退对象必须是：

```text
冻结的有限专家基线
或
最后一个已验证可行控制序列
```

不能回退到未验证的在线策略。

---

## 10. 慢时标外层规划器

近期外层规划器使用优化方法，不直接采用 RL。

外层更新频率低于内层控制周期，可按固定间隔或事件触发运行。

输出内容：

```text
目标条件化参考轨迹
R / Z / Ip 参考曲线控制点
到达—减速—保持阶段
终端状态或终端集合
MPC 权重调度
允许的不确定度预算
允许的探索预算
模型 bank 选择或加权
fallback 模式
```

外层输出必须经过：

```text
reachable-set 检查
reference governor
MPC feasibility 检查
安全核审查
```

外层不得直接输出14线圈电流或3个SVD模态动作。

---

## 11. 主动探索策略

近期第一版只使用**被动在线适应**：

```text
不额外添加探索动作
只利用正常控制动作产生的数据
在线更新状态、参数和局部残差模型
```

当被动适应通过独立验证后，才增加有界主动辨识。

主动辨识动作必须满足：

```text
不破坏正式到达截止时间
robust reachable tube仍在安全集内
动作可在有限步内零净值回收
fallback仍然可行
模型不确定度确实能够下降
信息收益高于安全代价
```

不采用随机动作、epsilon-greedy或真实装置上的无约束试错。

---

## 12. 单周期实时流程

```python
measurement = read_measurements()

augmented_state = estimator.update(
    measurement=measurement,
    coil_currents=current_coils,
    pending_queue=pending_queue,
    previous_action=previous_applied_action,
)

model, uncertainty = identifier.update(
    previous_state=previous_augmented_state,
    applied_action=previous_applied_action,
    current_state=augmented_state,
)

reference = slow_planner.current_reference(
    state=augmented_state,
    target=target,
    remaining_time=remaining_time,
)

candidate_action = adaptive_mpc.solve(
    state=augmented_state,
    model=model,
    uncertainty=uncertainty,
    reference=reference,
    pending_queue=pending_queue,
    formal_deadline=formal_deadline,
)

safe_action = safety_kernel.project_or_fallback(
    candidate_action=candidate_action,
    state=augmented_state,
    uncertainty=uncertainty,
)

apply_one_step(safe_action)
```

每次只执行一步，然后用下一时刻真实测量重新估计、辨识和优化。

---

## 13. 近期实施阶段

## 阶段 A：Shadow 在线辨识

控制动作仍完全由冻结专家生成。

在线模块只输出：

```text
下一步状态预测
vR / vZ 预测
delay / gain / slew 估计
局部残差模型
状态与参数不确定度
有效域判断
```

不允许修改动作。

### 阶段 A 验收

```text
预测误差满足预注册门槛
不确定度覆盖率满足门槛
错误模型能够拒绝
参数变化率合理
隐藏历史变化能够被检测
对正式控制轨迹无扰动
```

---

## 阶段 B：被动鲁棒自适应 MPC

允许在线模型影响 MPC，但：

```text
不主动探索
残差动作严格限幅
不确定度高时回退冻结专家
硬约束由安全核和鲁棒模型保证
```

### 阶段 B 验收

```text
正式250/350和270/370 ms合同不变
不低于冻结专家成功率
最小安全余量不恶化
fallback行为可审计
无错误模型接管
无queue语义错误
不同隐藏历史下性能改善或保持
```

---

## 阶段 C：优化式外层规划

使用：

```text
CEM
trajectory optimization
goal-conditioned receding-horizon planning
```

生成参考轨迹与阶段切换。

### 阶段 C 验收

```text
内层MPC可行率
参考轨迹可达性
到达速度与末端减速
不同目标泛化
扰动后重新规划能力
安全投影和fallback频率
```

---

## 阶段 D：有界双重自适应 MPC

在被动适应稳定后，加入有界信息动作。

MPC目标增加：

\[
J_{\mathrm{info}}
=
\lambda_{\mathrm{info}}
\operatorname{Tr}
\left(
\Sigma_{\theta,t+H}
\right)
\]

只允许在正式约束和fallback可行性均满足时执行。

### 阶段 D 验收

```text
信息动作确实降低关键不确定度
正式跟踪性能不下降
安全余量不下降
probe可零净值回收
不出现持续探索
模型错误时自动禁止探索
```

---

## 14. 数据与日志要求

每个控制周期必须保存：

```text
时间戳
R / Z / Ip
vR / vZ估计
14线圈电流
3个SVD模态动作
issued action
applied action
pending queue
delay / gain / slew估计
局部模型参数
状态协方差
参数协方差
预测下一状态
真实下一状态
预测误差
MPC目标值
约束余量
模型有效域
安全投影
fallback标志与原因
外层参考与阶段
```

必须能够逐点重放：

```text
测量
→ 状态估计
→ 参数更新
→ MPC输入
→ 候选动作
→ 安全投影
→ 实际动作
```

---

## 15. 近期验收矩阵

至少覆盖：

```text
不同初始状态
不同R / Z / Ip目标
不同隐藏vessel / eddy历史
delay变化
gain变化
slew变化
plant / Jacobian误差
测量噪声
外部扰动
```

每类实验分别报告：

```text
运行错误
数据完整性
状态估计误差
模型预测误差
不确定度覆盖率
正式到达成功率
最小signed margin
动作与线圈利用率
fallback次数
扰动恢复时间
保持稳定性
```

不能用一个总verdict替代分项证据。

---

## 16. 明确禁止事项

```text
禁止单次放电内从零训练神经actor
禁止RL直接输出14线圈电流
禁止RL直接输出3个SVD模态动作
禁止随机真实装置探索
禁止在线修改硬安全门槛
禁止在线修改正式到达deadline
禁止用更长时域掩盖晚到达
禁止不可信模型接管控制
禁止将summary success解释成控制通过
禁止将未运行阶段解释成失败或成功
禁止在MPC专家未完成前进入BC、DAgger或bounded residual RL
```

---

## 17. 中期扩展

近期方案完成后，再加入：

```text
完整controller-state restart
matched-visible / different-hidden-history测试
连续delay / gain / slew变化
新预冻结目标
plant / Jacobian误差
测量噪声与observer
扰动恢复
独立长时保持
```

外层学习策略的顺序：

```text
优化式外层规划器
→ 规划器数据集
→ Behavior Cloning
→ DAgger
→ 必要时外层RL
```

RL只作用于高层参考、阶段、风险预算、探索预算或bounded residual，不接管安全核和14线圈直接控制。

---

## 18. 最终任务

最终控制器必须面对：

```text
不同初始状态
隐藏vessel / eddy-current历史
不同R / Z / Ip目标
连续执行器delay / gain / slew变化
plant与Jacobian误差
测量噪声
外部扰动
```

仍能：

```text
因果决策
安全约束
按正式时间到达
提前减速
扰动恢复
长期稳定保持
```

近期主线为：

```text
增广信息状态估计
→ Shadow在线辨识
→ 被动鲁棒自适应MPC
→ 优化式外层规划
→ 有界双重自适应MPC
```

只有形成可靠MPC专家后，才进入：

```text
MPC专家数据集
→ Behavior Cloning
→ DAgger
→ bounded residual RL
```
