# DSLite 烧录工具 v2 改进版

更新日期：2026-05-29

这是当前主线版本，已完成发布适配和硬件非破坏性联调。

## 核心改进

- 自动检测项目随包 DSLite：`test\ccs_base\DebugServer\bin\DSLite.exe`
- 支持手动选择 DSLite 目录
- 配置持久化：`dslite_config.json`
- 后台任务进度显示
- 日志导出
- 内存读取结果预览
- 烧录 `.out/.elf`
- 按指定 Flash 地址烧录 `.bin`
- 全擦除加解锁
- 仅解锁
- 检测设备连接
- 读取 DEVEMU/芯片标识寄存器
- 后台调用 DSLite 时隐藏黑色控制台窗口
- 禁止并发 DSLite 任务，避免 XDS100/FTDI 连接冲突
- 固定代码目录，集中选择 `.out/.elf/.bin`
- 最近文件路径保存
- CSM 密码保存/加载
- 写入 CSM 密码并上锁

## 2026-05-29 修复记录

- 修复 exe 发布后找不到 `_internal` 依赖导致无法启动的问题。
- 修复每次点击功能弹出黑框的问题。
- 修复 `GetDeviceID` 不是当前 DSLite 可用操作导致读取芯片ID失败的问题。
- 修复检测设备命令，改为 `flash --list-ops`。
- 修复读取芯片ID逻辑，改为读取 `0x0880,0x08`。
- 修复 XDS100 不支持并发会话导致 `Error -151` 的问题。
- 修复打包后资源路径按 exe 所在目录解析。
- 增加固定代码目录配置，文件选择默认打开该目录。
- 增加 CSM 密码保存到 `dslite_config.json`。
- 增加“写入密码+上锁”按钮，执行前二次确认。

## 固定代码目录

日期：2026-05-29

在 Flash 烧录参数区设置“代码目录”，用于集中存放程序文件：

- `.out`
- `.elf`
- `.bin`

选择 RAM 加载、ELF 烧录、BIN 烧录文件时会默认打开该目录。最近选择的文件也会保存到配置文件。

## CSM 密码和上锁

日期：2026-05-29

CSM Key0 到 Key7 支持保存和自动加载。配置文件：

```text
dslite_config.json
```

功能说明：

- `仅解锁`：执行 `Unlock`
- `全擦除+解锁`：执行 `Unlock` 和 `Erase`
- `写入密码+上锁`：执行 `ProgramPassword` 和 `Lock`

风险提示：

- `写入密码+上锁` 会改变芯片安全状态。
- 密码丢失可能导致芯片无法正常访问。
- 不建议使用全 `FFFF` 写入并上锁。

## 硬件测试

日期：2026-05-29

环境：

- XDS100v2
- TMS320F28034
- DSLite 7.2.0.1988

已通过：

```powershell
DSLite.exe help
DSLite.exe flash --config=f28034.ccxml --list-ops --verbose
DSLite.exe flash --config=f28034.ccxml --list-settings --verbose
DSLite.exe memory --config=f28034.ccxml --range=0x0880,0x08 --output=device_id_verify.bin --verbose
```

DEVEMU/芯片标识结果：

```text
6B 0F BB 01 00 00 F7 FF
```

## 发布说明

桌面发布目录：

```text
C:\Users\hjs\Desktop\DSLite_F28034_Tool_Release
```

必须保留：

- `DSLite_F28034_Tool.exe`
- `_internal\`
- `f28034.ccxml`
- `test\ccs_base\`
- `dslite_config.json`

## 开发运行

```powershell
python dslite_tool_v2.py
```

## 打包命令

```powershell
python -m PyInstaller --noconfirm --clean --windowed --name DSLite_F28034_Tool "v2_改进版\dslite_tool_v2.py"
```
