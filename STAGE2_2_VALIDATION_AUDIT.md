# Stage2.2 validation audit

## 使用的真实输入

- Stage2完整运行：1536/1536成功；
- Stage2.1完整运行：1536/1536成功；
- 两个阶段的原始gzip轨迹、generation CSV、配置和state均被读取；
- 没有使用日志摘要代替原始轨迹。

## 真实历史重算结果

```text
source records before deduplication = 3072
unique 15-D vectors                 = 2965
skipped successful source rows      = 0
source strict candidates            = 0
strict-speed-safe unique vectors    = 882
strict-position-safe unique vectors = 37
```

最低最大违反量的源候选：

```text
candidate = s21g002_aaa2ceeb56d4f784
final-three box max = 31.2759249 mm
terminal box        = 30.3526609 mm
terminal speed      = 0.0100646 m/s
late speed RMS      = 0.1029228 m/s
position violation  = 0.04253083
late-speed violation= 0.02922794
max violation       = 0.04253083
```

## 代理模型交叉验证

在2965个唯一历史向量、16个generation folds上：

```text
final-three box max:
  CV R2  = 0.9331
  CV MAE = 0.000239 m

terminal velocity:
  CV R2  = 0.7762
  CV MAE = 0.02023 m/s

late velocity RMS:
  CV R2  = 0.6299
  CV MAE = 0.01079 m/s
```

三项均通过默认启用阈值。它们只用于候选池排序。

## 第一代候选构造验证

```text
population                  = 96
unique vectors              = 96
anchors                     = 12
multi-center probes         = 24
corner local                = 24
boundary bridge             = 18
trust mix                   = 12
random local                = 6
strict-JSON-safe specs      = 96/96
unvalidated/new node-0      = 0
```

三个探针中心分别落在minimum-violation、strict-speed-safe和precise-transition前沿。

## 代码测试

- Stage2、Stage2.1、Stage2.2自检通过；
- Stage2.2的13项单元测试覆盖：约束计算、hard-gate交叉核对、Archive、precise排序、固定node 0、24探针、分类确认、JSON null和非有限值拒绝；
- 完整单元测试套件共27项通过；
- 全部包内Python编译通过；
- 全部配置JSON解析通过；
- 全部Shell脚本 `bash -n` 通过；
- 在无 `.git` 的空目录中解压后可导入并运行自检；
- 用mock TSC返回完成了96候选generation、state更新、24条确认、分析和全部JSON/GZIP重读。

## 未完成的测试

当前执行环境没有用户服务器上的gotsc/TSC runtime，因此没有真实运行Stage2.2的96-worker一代。真实TSC控制结果和服务器资源行为必须以用户实跑为最终依据。
