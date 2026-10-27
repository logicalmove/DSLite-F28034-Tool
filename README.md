# DSLite F28034 烧录工具

更新日期：2026-05-29

TI C2000 DSP TMS320F28034 专用 DSLite 烧录调试上位机，基于 PyQt5 开发，随包使用 TI DSLite/DebugServer。

## 当前发布版

桌面发布目录：

```text
C:\Users\hjs\Desktop\DSLite_F28034_Tool_Release
```

主要文件：

- `DSLite_F28034_Tool.exe`：当前可执行程序
- `_internal\`：PyInstaller 运行依赖目录，不能删除
- `f28034.ccxml`：F28034 / XDS100v2 调试配置
- `test\ccs_base\`：随包 DSLite/DebugServer 工具链
- `dslite_config.json`：运行时配置文件

## 版本说明

| 版本 | 文件 | 状态 | 说明 |
| --- | --- | --- | --- |
| v1 | `dslite_tool.py` | 归档 | 基础功能版，存在硬编码路径，不建议继续使用 |
| v2 | `dslite_tool_v2.py` | 保留 | 自动检测、进度条、配置持久化等 |
| v2 改进版 | `v2_改进版\dslite_tool_v2.py` | 当前主线 | 已完成硬件联调、发布适配和黑框隐藏 |

## 已完成修复

日期：2026-05-29

- 修复相对 `ccxml` 路径解析，统一按脚本或 exe 所在目录查找。
- 修复 UI 修改 `ccxml` 后命令仍使用旧缓存值的问题。
- 修复 DSLite 命令使用相对 `DSLite.exe` 导致发布环境不稳定的问题。
- 修复项目自带 DSLite 工具链无法优先检测的问题。
- 修复 `parse_bin.py` 文件不存在时异常变量引用错误。
- 修复 PyInstaller 发布时漏复制 `_internal` 导致 exe 打不开的问题。
- 修复每次点击功能弹出黑色控制台窗口的问题，后台 DSLite 子进程已隐藏窗口。
- 修复程序内可能并发启动多个 DSLite 会话的问题，当前已有任务时会提示等待。
- 将“检测设备”改为非破坏性的 `flash --list-ops`。
- 将“读取芯片ID”改为读取 DEVEMU 寄存器 `0x0880,0x08`。
- 增加固定代码目录配置，选择 `.out/.elf/.bin` 时默认从该目录打开。
- 增加最近使用的 RAM 加载、ELF 烧录、BIN 烧录文件路径保存。
- 增加 CSM 密码保存/加载，密码保存在本机 `dslite_config.json`。
- 增加“写入密码+上锁”功能，执行 `ProgramPassword` 和 `Lock` 前会二次确认。

## 固定代码目录

日期：2026-05-29

程序现在支持设置固定代码目录，用于集中存放待烧录程序文件：

- `.out`
- `.elf`
- `.bin`

设置后，选择 RAM 加载、ELF 烧录、BIN 烧录文件时会默认打开该目录。配置会保存到：

```text
dslite_config.json
```

建议目录示例：

```text
C:\Users\hjs\Desktop\F28034_Code
```

## CSM 密码管理

日期：2026-05-29

程序现在支持保存 8 组 16-bit CSM Key：

```text
FlashKey0 ~ FlashKey7
```

用途：

- `仅解锁`：使用当前保存/输入的密码执行 `Unlock`
- `全擦除+解锁`：使用当前保存/输入的密码执行 `Unlock` 后 `Erase`
- `写入密码+上锁`：写入当前密码并执行 `Lock`

注意：

- 密码保存在本机 `dslite_config.json`，请自行保管该文件。
- 不建议用全 `FFFF` 执行“写入密码+上锁”。
- “写入密码+上锁”会改变芯片安全状态，执行前程序会二次确认。
- 一旦上锁，后续必须使用正确密码解锁；密码丢失可能导致芯片无法正常访问。

## 硬件测试记录

日期：2026-05-29

已连接 XDS100v2 和 F28034 目标板完成非破坏性测试：

- `DSLite.exe help`：通过。
- `flash --config=f28034.ccxml --list-ops --verbose`：通过。
- `flash --config=f28034.ccxml --list-settings --verbose`：通过，需串行执行。
- `memory --config=f28034.ccxml --range=0x0880,0x08 --output=device_id_verify.bin --verbose`：通过。

DEVEMU/芯片标识读取结果：

```text
6B 0F BB 01 00 00 F7 FF
```

注意：XDS100/DSLite 不适合同时启动多个会话。并行执行两个 DSLite 命令时，一个可能成功，另一个可能报 FTDI/XDS100 `Error -151`。程序已改为禁止并发任务。

## 打包发布

当前采用 PyInstaller `onedir` 方式发布。发布时必须同时保留 exe 和 `_internal` 目录：

```powershell
python -m PyInstaller --noconfirm --clean --windowed --name DSLite_F28034_Tool "v2_改进版\dslite_tool_v2.py"
```

发布目录还需要包含：

- `f28034.ccxml`
- `test\ccs_base\`

## 开发运行

```powershell
pip install PyQt5 pyinstaller openpyxl
python "v2_改进版\dslite_tool_v2.py"
```

## 验证命令

```powershell
python -m py_compile "v2_改进版\dslite_tool_v2.py"
python -m unittest tests.test_dslite_tool_v2_helpers
```

## 后续建议

- 对擦除、解锁、烧录 BIN 增加二次确认和参数摘要。
- 增加 F28034 Flash 地址范围、扇区边界和 BIN 文件大小校验。
- 明确顶层 v2 与 `v2_改进版` 的长期维护关系，建议以 `v2_改进版` 为主线。
- 整理仓库中的 TI 工具链二进制文件，区分源码仓库和发布包。
