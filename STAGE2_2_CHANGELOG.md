# Stage2.2 Changelog

## 从Stage2.1到Stage2.2

### 数据基础

- 同时读取完整Stage2和Stage2.1原始TSC结果；
- 对3072条轨迹逐条重新计算Gate和最后3步矩形盒误差；
- 15维向量按1e-10精度去重；
- 源catalog对CSV、配置和全部原始gzip结果做内容指纹；
- 标记成功却缺失/损坏的源结果现在直接终止，不再静默跳过。

### 成功判据

- 30 mm、最后3步、终端速度、late速度RMS和Ip hard gate完全不变；
- Stage2.2额外在运行时独立重算hard gate，并与Stage2基础实现交叉核对；
- 代理模型仍无权宣布Gate成功。

### 目标函数

- 废弃非strict候选由旧Gate tier主导的排序；
- 优先最小化最大归一化严格约束违反量；
- 再比较总违反量、L2违反量和连续质量项；
- 任意真实strict候选优先于全部非strict候选。

### Archive

- 新增 `corner` 和 `strict` archive；
- `damped`严格使用0.10 m/s两项速度阈值，不含1.05 margin；
- `precise`重新偏向位置接近且已接近阻尼的过渡候选；
- 所有archive执行向量去重和最小距离多样性控制。

### 搜索

- 96候选/代，最多6代；
- 3个不同中心、24个Hadamard正负探针；
- 重点搜索node steps 2/4/6/9；
- node step 0不独立扰动，新proposal继承已真实验证父代的node 0；
- 新增corner local、boundary bridge、trust mix和random local家族；
- trust region随改进/无改进自适应收缩。

### 代理模型

- 从两个历史阶段联合训练：
  - final-three box max；
  - terminal velocity；
  - late velocity RMS；
- leave-one-generation-out验证不达标自动禁用；
- 所有缺失预测写为JSON `null`，不写NaN。

### 确认与分析

- 分类选择strict、corner、speed-safe、position-front和legacy gate候选；
- 最多8个唯一向量，每个3次确认；
- 散点图改用最后3步最大矩形盒误差作为横轴；
- 新增按类别拆分的Hall of Fame和严格违反量进展图。

### 运行安全

- 继承Stage2.1 JSON-safe基础代码；
- TSC启动前检查spec严格JSON合法性和ID唯一性；
- 单条异常结果被隔离为失败，不中止整代；
- 原子写入失败清理临时文件；
- 完整源码树，无Git/网络/外部代码树依赖。
