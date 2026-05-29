# DSLite F28034 烧录工具

TI C2000 DSP (F28034) 专用 DSLite 烧录调试上位机。

## 版本

| 版本 | 说明 |
|------|------|
| v1 (原始版) | dslite_tool.py - 基础功能版 |
| v2 (改进版) | 2_改进版/dslite_tool_v2.py - 自动检测、进度条、配置持久化等 |

## v2 改进内容

- 路径自动检测（不再硬编码）
- 配置持久化（保存窗口路径）
- 进度条显示
- 操作超时保护
- 日志导出
- 内存预览优化
- 多种芯片支持
- 自动检测工具链

## 使用方法

\\\powershell
pip install PyQt5
python dslite_tool_v2.py
\\\

## 依赖

- Python 3.8+
- PyQt5
- TI DSLite (DebugServer)

## 许可证

MIT
