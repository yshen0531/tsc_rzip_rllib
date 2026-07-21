# Stage2.2：三模态严格角点可行性搜索

## 1. 这一版解决什么问题

Stage2.2不是重新做一轮大范围CEM，也不是放宽Stage2的成功标准。它专门利用已经完成的Stage2和Stage2.1真实TSC数据，搜索下面四个严格约束的狭窄交集：

1. 最后3个采样点同时满足 `|R error| <= 30 mm` 和 `|Z error| <= 30 mm`；
2. 终端R/Z速度 `<= 0.10 m/s`；
3. late-window速度RMS `<= 0.10 m/s`；
4. 终端Ip误差位于原有安全容差内。

三SVD模态、5个时间节点、100 ms时域、线圈电流限制、`3 A / 10 ms` slew约束和真实TSC判据全部保持不变。

Stage2.2的源数据是：

- Stage2：1536条成功的真实TSC轨迹；
- Stage2.1：1536条成功的真实TSC轨迹；
- 合并前3072条，按15维参数向量去重后2965条。

程序启动时会重新读取每条原始压缩轨迹并计算最后3步矩形盒误差，不相信旧CSV里可能缺失或版本不同的派生指标。

## 2. 核心算法

### 2.1 直接优化严格约束违反量

对每个真实TSC候选计算：

```text
position_violation = max(final3_box_max / 0.030 - 1, 0)
terminal_speed_violation = max(terminal_speed / 0.10 - 1, 0)
late_speed_violation = max(late_speed_rms / 0.10 - 1, 0)
ip_violation = max(abs(terminal_Ip_error) / Ip_limit - 1, 0)
```

非strict候选首先最小化四项中的最大值，然后比较总违反量、L2违反量和连续质量项。任意真实strict候选始终排在所有非strict候选之前。

### 2.2 四类独立Archive

- `strict`：真实TSC已经通过完整30 mm hard gate；
- `corner`：最大归一化严格约束违反量最小；
- `damped`：严格使用原始 `0.10 m/s` 两项速度阈值，不再使用Stage2.1旧版的1.05 margin；
- `precise`：位置接近30 mm、同时已接近阻尼的过渡前沿，避免只保留高速穿过30 mm管的候选。

### 2.3 96候选/代、最多6代

每一代固定组成：

```text
anchors                 12
multi_center_probes      24
corner_local             24
boundary_bridge          18
trust_mix                12
random_local              6
---------------------------
total                    96
```

主要搜索node steps `2, 4, 6, 9`对应的12个变量。node step 0不做独立连续扰动；新候选的node 0来自已经真实验证过的父代。

24个探针来自3个不同中心：

- 当前最小违反量corner中心；
- 严格速度安全damped中心；
- 位置/速度过渡precise中心。

每个中心使用4个Hadamard方向的正负成对扰动，共 `3 x 4 x 2 = 24` 条真实TSC探针。不同代轮换方向。

### 2.4 三输出代理模型只做排序

用Stage2和Stage2.1全部历史轨迹训练三个纯NumPy ridge模型：

- 最后三步最大矩形盒误差；
- 终端速度；
- late速度RMS。

必须先通过leave-one-generation-out交叉验证才会启用。代理模型只对候选池排序，永远不能判定hard gate。

### 2.5 分类确认，不再只确认40 mm Hall of Fame

最终确认会从以下类别去重选取最多8个候选，每个真实TSC回放3次：

- strict；
- 最小严格违反量corner；
- 严格速度安全边界；
- 30 mm位置前沿；
- 旧Gate Hall of Fame。

只有至少一个候选3次全部通过strict gate，最终才报告：

```text
PASS_PRECISE_HOLD_30MM_CONFIRMED
```

## 3. 完整包内容

本ZIP物理包含：

```text
configs/
scripts/
tests/
tsc_rzip_rllib/
```

以及Stage2、Stage2.1和Stage2.2全部根目录脚本。它不依赖：

```text
.git
GitHub
STAGE2_2_BASE_TREE
在线下载
旧的configs/scripts/tests/tsc_rzip_rllib目录
```

Stage2.2仍然需要你已经保留的结果目录：

```text
stage1_1_runs/<完整Stage1.1运行>/
stage2_runs/<完整Stage2运行>/
stage2_1_runs/<完整Stage2.1运行>/
```

这三个目录是训练数据，不属于代码包，安装时不要删除。

## 4. 安装

进入项目：

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
```

停止旧程序：

```bash
./run_stop_stage2_2_now.sh 2>/dev/null || true
./run_stop_stage2_1_now.sh 2>/dev/null || true
ray stop --force 2>/dev/null || true
```

按照你的覆盖方式删除旧代码目录：

```bash
rm -rf configs scripts tests tsc_rzip_rllib
```

不要删除：

```text
stage1_1_runs/
stage2_runs/
stage2_1_runs/
```

解压完整包：

```bash
unzip -o /path/to/stage2_2_complete_standalone.zip \
  -d /home/yangshen0711/tsc_all/tsc_rzip_rllib
```

设置权限：

```bash
chmod +x \
  run_stage2_2_svd3_corner_native.sh \
  run_stage2_2_svd3_corner_nohup.sh \
  run_stage2_2_one_generation_native.sh \
  run_stage2_2_prepare_only.sh \
  run_stage2_2_confirm_only.sh \
  run_stage2_2_analyze_only.sh \
  run_stage2_2_self_test.sh \
  run_stage2_2_verify_package.sh \
  run_stop_stage2_2_now.sh
```

## 5. 运行前验证

```bash
./run_stage2_2_verify_package.sh
```

该命令不调用gotsc。它检查：

- 包内逐文件SHA256；
- Stage2、Stage2.1和Stage2.2完整导入；
- Python编译；
- 配置JSON；
- 全部Shell语法；
- Stage2、Stage2.1、Stage2.2自检；
- 全部单元测试；
- 不存在Git、网络或外部代码树依赖。

## 6. 指定源结果

推荐明确指定：

```bash
export SOURCE_STAGE1_1_RUN=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage1_1_runs/stage1_1_svd234_strict_validation_100ms_20260718_025916

export SOURCE_STAGE2_RUN=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage2_runs/stage2_svd3_real_tsc_cem_100ms_20260720_114614

export SOURCE_STAGE2_1_RUN=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage2_1_runs/stage2_1_svd3_dual_archive_tail_cem_100ms_20260720_151221
```

不设置时，脚本会优先读取：

```text
stage2_1_runs/latest_stage2_1_run.txt
```

并从Stage2.1 manifest恢复Stage2和Stage1.1路径；旧绝对路径失效时会按结果目录basename在当前项目中回退查找。

## 7. 推荐正式运行方式

```bash
./run_stage2_2_svd3_corner_nohup.sh
```

输出会显示：

```text
[Stage2.2] pid=...
[Stage2.2] run_dir=...
[Stage2.2] log=...
```

查看日志：

```bash
tail -f "$(cat logs/nohup/latest_stage2_2_svd3_corner.log)"
```

查看本次结果目录：

```bash
cat stage2_2_runs/latest_stage2_2_run.txt
```

默认使用96个Ray workers：

```bash
export STAGE2_2_WORKERS=96
```

可在启动前调整，但候选数量仍固定为每代96。

## 8. 分步运行

### 8.1 只整理3072条源轨迹，不调用TSC

```bash
./run_stage2_2_prepare_only.sh
```

重点检查：

```text
source_candidate_catalog_summary.json
```

完整源结果应报告：

```text
Stage2 catalog_records       = 1536
Stage2.1 catalog_records     = 1536
before deduplication         = 3072
unique vectors               = 2965
skipped successful rows      = 0
strict source candidates     = 0
```

程序现在会对全部原始结果文件做内容指纹；任何标记成功但无法恢复的源轨迹都会立即报错，而不是静默忽略。

### 8.2 只运行一代

```bash
./run_stage2_2_one_generation_native.sh
```

若已经prepare过，脚本会自动选择latest run并以resume模式继续。

### 8.3 只做最终确认和分析

```bash
export STAGE2_2_RUN_DIR=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage2_2_runs/具体目录
./run_stage2_2_confirm_only.sh
```

### 8.4 只重做分析

```bash
export STAGE2_2_RUN_DIR=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage2_2_runs/具体目录
./run_stage2_2_analyze_only.sh
```

## 9. 中断恢复

```bash
export STAGE2_2_RUN_DIR=/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage2_2_runs/具体目录
export STAGE2_2_RESUME=1
./run_stage2_2_svd3_corner_nohup.sh
```

已完成的候选JSON会被复用；只补做缺失候选。源catalog带有两个CSV、两个配置文件和3072个原始gzip结果的内容指纹，恢复时若源历史发生变化会拒绝继续。

## 10. 立即停止

```bash
./run_stop_stage2_2_now.sh
```

它会停止Stage2.2进程组、停止Ray并清理 `/tmp/tsc_workspace` 和Stage2.2 Ray临时目录，但不会删除 `stage2_2_runs/` 中已经保存的结果。

## 11. 主要输出

```text
stage2_2_runs/stage2_2_svd3_corner_feasibility_100ms_<timestamp>/
```

重点文件：

```text
stage2_2_manifest.json
stage2_2_state.json
source_candidate_catalog.json.gz
source_candidate_catalog_summary.json

stage2_2_generations/gen_*/
  candidate_manifest.json
  generation_results.json
  corner_archive_after.csv
  damped_archive_after.csv
  precise_archive_after.csv
  strict_archive_after.csv

stage2_2_evaluations/gen_*/*.json.gz

stage2_2_confirmations/
  confirmation_results.csv
  confirmation_summary.csv
  stage2_2_verdict.json

stage2_2_analysis/
  all_generation_results.csv
  corner_hall_of_fame.csv
  speed_safe_hall_of_fame.csv
  position_hall_of_fame.csv
  strict_hall_of_fame.csv
  corner_feasibility_scatter.png
  max_violation_by_generation.png
  best_corner_trajectory_rz.png
  stage2_2_analysis_summary.json

STAGE2_2_REPORT.md
```

`corner_feasibility_scatter.png`的横轴是真正Gate使用的“最后3步最大矩形盒误差”，不是此前容易误读的终端欧氏误差。

## 12. 诚实边界

这套代码已经用你上传的完整Stage2和Stage2.1结果执行过真实源数据warm-start、3072条轨迹重算、2965向量去重、代理模型跨代验证、96候选构造、JSON安全检查以及无TSC的完整模拟一代/确认/分析流程。

当前环境没有你的gotsc二进制和服务器TSC运行条件，因此没有替你执行96-worker真实TSC一代，也不能保证Stage2.2必然找到strict解。程序能够保证的是：搜索目标、Archive、候选构造、恢复、确认和数据写盘按照上述定义运行；真实控制效果仍以你的服务器结果为准。
