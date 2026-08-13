# LibreHardwareMonitor 单次采集迁移设计

## 目标

将当前依赖 HWiNFO 免费版 GUI 和 CSV 日志的每小时采集流程，替换为基于官方
`LibreHardwareMonitorLib` 的无界面单次采集流程。Windows Task Scheduler 每小时以
最高权限启动一次，采集、发送邮件后退出，不驻留后台、不操作鼠标。

## 选定方案

安装官方 LibreHardwareMonitor 便携发行版，并新增一个小型 .NET 控制台采集器。
采集器引用 `LibreHardwareMonitorLib`，直接枚举硬件和传感器，将一次快照写为 JSON
到标准输出。Python 入口启动采集器、解析 JSON，并继续复用现有 Windows 系统信息、
每日 CSV、趋势图、HTML 邮件、SMTP、互斥锁和错误日志模块。

未采用 LibreHardwareMonitor GUI Web Server，因为它需要启动应用并维护 HTTP 服务，
不符合单次执行后退出的要求。未采用 Python 直接加载 .NET DLL，因为额外的 Python/.NET
桥接层会增加部署和运行时兼容风险。

## 安装布局

- `tools/LibreHardwareMonitor/`：从官方 GitHub Release 安装的便携发行版。
- `collector/`：.NET 控制台采集器源码与项目文件。
- `collector/publish/`：可直接由计划任务调用的自包含采集器输出。
- `hwLog/sensor_inventory.json`：首次扫描或显式扫描生成的完整传感器清单。

第三方二进制和构建输出不提交 Git；来源、版本和重新安装步骤记录在 README。

## 采集器接口

采集器一次运行执行以下步骤：

1. 启用 CPU、GPU、主板、内存和存储设备采集。
2. 打开 LibreHardwareMonitor `Computer`。
3. 更新所有硬件及其子硬件。
4. 枚举所有当前有数值的传感器。
5. 输出 UTF-8 JSON 后关闭 `Computer` 并退出。

JSON 顶层包含采集时间和 `sensors` 数组。每个传感器包含稳定标识符、硬件名称、
硬件类型、传感器名称、传感器类型和数值。采集器失败时向标准错误输出原因并返回非零
退出码。Python 为子进程设置明确超时。

## Python 映射与数据流

配置入口改为 LibreHardwareMonitor 采集器路径、超时和传感器映射。映射优先使用稳定
标识符；首次安装后先保存完整 inventory，再依据本机实际结果填写映射。原日报字段尽量
保持不变，以便当天趋势图继续读取。

数据流为：

`任务计划 → Python 入口 → .NET 采集器 JSON → 映射/验证 → Windows 系统信息 → HTML 邮件 → 每日 CSV → 退出`

CPU、GPU、主板温度及 CPU/GPU 使用率属于趋势图必需字段。实际存在的 DIMM、硬盘温度
和电压按 inventory 映射。魔改 X99 主板上 LibreHardwareMonitor 未暴露的非必需传感器
从报告和日报字段中移除，不伪造数值。缺失必需字段时本次不写日报、不发不完整邮件。

## 任务计划

安装脚本更新现有 `HWiNFO Hardware Monitor - Send Hourly Report` 任务，或以兼容名称重建，
使其每小时直接执行新的 Python 单次采集入口。任务使用最高权限，但不要求交互登录令牌，
因为新流程不控制 GUI。任务重叠时继续使用现有 Windows 命名互斥锁跳过新实例。

## 错误处理

以下异常写入现有 UTF-8 按日错误日志并以非零状态退出：采集器缺失、管理员权限不足、
采集器超时/崩溃、JSON 无效、必需传感器缺失、文件权限、图表、网络和 SMTP 异常。
错误不会导致程序等待用户输入或常驻。

## 测试与验收

- 先写失败测试，再实现 JSON 解析、标识符映射、数值验证和必需字段检查。
- 验证采集器超时、非零退出、无效 JSON 和缺失传感器均记录错误且不写日报。
- 验证成功流程继续生成当日 CSV、两张 CID 趋势图和 HTML 邮件。
- 在本机以管理员权限运行 inventory 扫描，检查 X99 主板、CPU、GPU、DIMM 和所有硬盘的
  实际传感器覆盖范围。
- 手动触发计划任务一次，验收返回码 `0x0`、日报新增一行、邮件送达且采集器进程已退出。

## 回退

HWiNFO 解析和旧入口暂时保留，但新任务不再调用。若 LibreHardwareMonitor 无法提供排障所需
的关键 X99 电压，可恢复旧配置进行手动 HWiNFO 采样，或后续决定使用 HWiNFO Pro。
