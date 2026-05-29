import sys
import os
import subprocess
import xml.etree.ElementTree as ET
import json
import glob
import re
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTextEdit, QGroupBox, QComboBox,
    QFileDialog, QSplitter, QMessageBox, QProgressBar, QCheckBox,
    QTabWidget, QGridLayout, QListWidget, QAbstractItemView
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer

# ====================== 版本信息 =======================
VERSION = "v2.0 — 2026-05-29"
AUTHOR = "基于原始版全面改进"

# ====================== 配置管理 =======================
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dslite_config.json")

def load_config():
    defaults = {
        "bin_dir": "",
        "ccxml": "f28034.ccxml",
        "chip": "F28034",
        "last_bin_flash_addr": "0x3E8000",
        "last_load_file": "",
        "last_elf_file": "",
        "last_bin_file": "",
        "window_w": 1100,
        "window_h": 1000,
        "auto_detect_dslite": True,
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**defaults, **json.load(f)}
        except:
            pass
    return defaults

def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except:
        pass

# ====================== DSLite 自动检测 =======================
def find_dslite():
    """自动查找 DSLite.exe"""
    search_patterns = [
        r"C:\ti\ccs*\ccs_base\DebugServer\bin\DSLite.exe",
        r"C:\ti\*\DebugServer\bin\DSLite.exe",
        r"C:\Program Files\TI\ccs*\ccs_base\DebugServer\bin\DSLite.exe",
        r"C:\Program Files (x86)\TI\ccs*\ccs_base\DebugServer\bin\DSLite.exe",
    ]
    for pattern in search_patterns:
        matches = glob.glob(pattern)
        if matches:
            return os.path.dirname(matches[0])
    return ""

def find_cl2000():
    """自动查找 TI C2000 编译器"""
    patterns = [
        r"C:\ti\ccs*\ccs\tools\compiler\ti-cgt-c2000*\bin\cl2000.exe",
        r"C:\ti\ti-cgt-c2000*\bin\cl2000.exe",
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return os.path.dirname(matches[0])
    return ""

# ====================== 后台执行线程（改进版）=======================
class CmdThread(QThread):
    log_sig = pyqtSignal(str)
    progress_sig = pyqtSignal(int, str)
    done_sig = pyqtSignal(bool, str)
    error_sig = pyqtSignal(str)

    def __init__(self, task_name, args, work_dir, output_file=""):
        super().__init__()
        self.task_name = task_name
        self.args = args
        self.work_dir = work_dir
        self.output_file = output_file

    def run(self):
        try:
            self.progress_sig.emit(10, f"正在执行: {self.task_name}")
            
            res = subprocess.run(
                self.args,
                cwd=self.work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=120
            )
            
            full_log = res.stdout + "\n" + res.stderr
            self.log_sig.emit(full_log)
            
            self.progress_sig.emit(90, "处理完成")
            is_ok = res.returncode == 0
            
            if is_ok:
                self.progress_sig.emit(100, "✅ 成功")
            else:
                self.progress_sig.emit(100, "❌ 失败")
            
            self.done_sig.emit(is_ok, self.output_file)
            
        except subprocess.TimeoutExpired:
            self.log_sig.emit("[超时] 操作超过120秒，可能已无响应")
            self.error_sig.emit("操作超时")
            self.done_sig.emit(False, "")
        except Exception as e:
            self.log_sig.emit(f"[执行异常] {str(e)}")
            self.error_sig.emit(str(e))
            self.done_sig.emit(False, "")


# ====================== 主窗口（全面改进版）=======================
class FullDSLiteTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.setWindowTitle(f"DSLite 烧录工具 {VERSION}")
        self.resize(self.config.get("window_w", 1100), self.config.get("window_h", 1000))

        # 自动检测 DSLite 路径
        self.BIN_DIR = self.config.get("bin_dir", "")
        if not self.BIN_DIR or not os.path.exists(os.path.join(self.BIN_DIR, "DSLite.exe")):
            detected = find_dslite()
            if detected:
                self.BIN_DIR = detected
                self.config["bin_dir"] = detected
                save_config(self.config)
        
        self.CCXML_FILE = self.config.get("ccxml", "f28034.ccxml")
        self.active_threads = []  # 线程池，支持多线程
        self.log_file_path = ""
        
        # F28034 地址预设
        self.addr_preset = {
            "GPIOA数据寄存器 (0x7200)": {"addr": "0x7200", "len": "0x10"},
            "GPIOB数据寄存器 (0x7201)": {"addr": "0x7201", "len": "0x10"},
            "CPU Timer0 寄存器 (0x7010)": {"addr": "0x7010", "len": "0x08"},
            "系统控制寄存器 (0x7010)": {"addr": "0x7010", "len": "0x20"},
            "Flash起始区 (0x0000)": {"addr": "0x0000", "len": "0x100"},
            "程序运行区 (0x0800)": {"addr": "0x0800", "len": "0x200"},
            "ADC结果寄存器 (0x0B00)": {"addr": "0x0B00", "len": "0x10"},
        }

        self.flash_addr_preset = {
            "Flash H扇区 (0x3E8000)": "0x3E8000",
            "Flash G扇区 (0x3EA000)": "0x3EA000",
            "Flash F扇区 (0x3EC000)": "0x3EC000",
            "Flash E扇区 (0x3EE000)": "0x3EE000",
            "Flash D扇区 (0x3F0000)": "0x3F0000",
            "Flash C扇区 (0x3F2000)": "0x3F2000",
            "Flash B扇区 (0x3F4000)": "0x3F4000",
            "Flash A扇区 (0x3F6000)": "0x3F6000",
        }

        self.init_ui()
        self.log("=" * 60)
        self.log(f"DSLite 烧录工具 {VERSION}")
        self.log(f"工作目录: {self.BIN_DIR}")
        self.log(f"芯片配置: {self.CCXML_FILE}")
        if os.path.exists(os.path.join(self.BIN_DIR, "DSLite.exe")):
            self.log("✅ DSLite.exe 已找到")
        else:
            self.log("⚠️ DSLite.exe 未找到！请配置工具链路径")
        self.log("=" * 60)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # ========== 顶部工具栏 ==========
        toolbar = QHBoxLayout()
        
        self.status_icon = QLabel("⚙️")
        self.status_icon.setStyleSheet("font-size: 18px;")
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 13px;")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setVisible(False)
        
        self.btn_detect = QPushButton("🔍 自动检测")
        self.btn_detect.clicked.connect(self.auto_detect)
        
        self.btn_save_log = QPushButton("💾 保存日志")
        self.btn_save_log.clicked.connect(self.save_log)
        
        self.btn_clear_log = QPushButton("🗑️ 清空日志")
        self.btn_clear_log.clicked.connect(lambda: self.log_text.clear())
        
        self.btn_save_config = QPushButton("⚙️ 保存配置")
        self.btn_save_config.clicked.connect(self.save_current_config)
        
        toolbar.addWidget(self.status_icon)
        toolbar.addWidget(self.status_label)
        toolbar.addWidget(self.progress_bar)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_detect)
        toolbar.addWidget(self.btn_save_log)
        toolbar.addWidget(self.btn_clear_log)
        toolbar.addWidget(self.btn_save_config)
        main_layout.addLayout(toolbar)

        # ========== 标签页 ==========
        self.tabs = QTabWidget()
        
        # ---- 标签1: 烧录与调试 ----
        tab_main = QWidget()
        tab_main_layout = QVBoxLayout(tab_main)
        
        # 工具链配置组
        conf_group = QGroupBox("工具链配置")
        conf_grid = QGridLayout(conf_group)
        self.lbl_workdir = QLabel(f"工作目录：{self.BIN_DIR}")
        self.lbl_workdir.setWordWrap(True)
        self.btn_browse_dir = QPushButton("📁 选择DSLite目录")
        self.btn_browse_dir.clicked.connect(self.select_bin_dir)
        self.ccxml_edit = QLineEdit(self.CCXML_FILE)
        self.ccxml_edit.setPlaceholderText("ccxml 文件名")
        self.chip_combo = QComboBox()
        self.chip_combo.addItems(["F28034", "F28035", "F28027", "F28069", "F28335", "F28379D"])
        self.chip_combo.setCurrentText(self.config.get("chip", "F28034"))
        
        conf_grid.addWidget(QLabel("芯片型号："), 0, 0)
        conf_grid.addWidget(self.chip_combo, 0, 1)
        conf_grid.addWidget(QLabel("配置："), 0, 2)
        conf_grid.addWidget(self.ccxml_edit, 0, 3)
        conf_grid.addWidget(self.btn_browse_dir, 0, 4)
        conf_grid.addWidget(self.lbl_workdir, 1, 0, 1, 5)
        tab_main_layout.addWidget(conf_group)
        
        # 功能按钮区域
        func_group = QGroupBox("常用操作")
        func_layout = QGridLayout(func_group)
        
        self.btn_read_mem = QPushButton("📥 读取内存")
        self.btn_read_mem.setMinimumHeight(40)
        self.btn_read_mem.clicked.connect(self.start_read_memory)
        self.btn_load_ram = QPushButton("🚀 加载 RAM")
        self.btn_load_ram.setMinimumHeight(40)
        self.btn_load_ram.clicked.connect(self.start_load_program)
        self.btn_flash_elf = QPushButton("🔥 烧录 .out/.elf")
        self.btn_flash_elf.setMinimumHeight(40)
        self.btn_flash_elf.clicked.connect(self.start_elf_flash)
        self.btn_flash_bin = QPushButton("🔥 烧录 .bin")
        self.btn_flash_bin.setMinimumHeight(40)
        self.btn_flash_bin.clicked.connect(self.start_bin_flash)
        self.btn_erase = QPushButton("🔓 全擦除+解锁")
        self.btn_erase.setMinimumHeight(40)
        self.btn_erase.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold;")
        self.btn_erase.clicked.connect(self.start_erase_all)
        self.btn_unlock = QPushButton("🔑 仅解锁")
        self.btn_unlock.setMinimumHeight(40)
        self.btn_unlock.setStyleSheet("background-color: #ff9800; color: white; font-weight: bold;")
        self.btn_unlock.clicked.connect(self.start_unlock_only)
        self.btn_erase_sectors = QPushButton("擦除扇区")
        self.btn_erase_sectors.setMinimumHeight(40)
        self.btn_erase_sectors.clicked.connect(self.start_erase_sectors)
        self.btn_check = QPushButton("🔍 检测设备")
        self.btn_check.setMinimumHeight(40)
        self.btn_check.clicked.connect(self.check_device_status)
        self.btn_read_id = QPushButton("📋 读取芯片ID")
        self.btn_read_id.setMinimumHeight(40)
        self.btn_read_id.clicked.connect(self.read_device_id)
        
        func_layout.addWidget(self.btn_read_mem, 0, 0)
        func_layout.addWidget(self.btn_load_ram, 0, 1)
        func_layout.addWidget(self.btn_flash_elf, 0, 2)
        func_layout.addWidget(self.btn_flash_bin, 1, 0)
        func_layout.addWidget(self.btn_erase, 1, 1)
        func_layout.addWidget(self.btn_unlock, 1, 2)
        func_layout.addWidget(self.btn_erase_sectors, 2, 0)
        func_layout.addWidget(self.btn_check, 2, 1)
        func_layout.addWidget(self.btn_read_id, 2, 2)
        tab_main_layout.addWidget(func_group)
        
        # ---- 读取内存参数 ----
        mem_group = QGroupBox("内存读取参数")
        mem_layout = QGridLayout(mem_group)
        
        mem_layout.addWidget(QLabel("地址预设："), 0, 0)
        self.addr_combo = QComboBox()
        self.addr_combo.addItems(list(self.addr_preset.keys()))
        self.addr_combo.currentIndexChanged.connect(self.on_preset_change)
        mem_layout.addWidget(self.addr_combo, 0, 1, 1, 2)
        
        mem_layout.addWidget(QLabel("起始地址："), 1, 0)
        self.addr_edit = QLineEdit("0x7200")
        mem_layout.addWidget(self.addr_edit, 1, 1)
        mem_layout.addWidget(QLabel("长度："), 1, 2)
        self.len_edit = QLineEdit("0x10")
        mem_layout.addWidget(self.len_edit, 1, 3)
        mem_layout.addWidget(QLabel("输出："), 1, 4)
        self.outfile_edit = QLineEdit("mem_read.bin")
        mem_layout.addWidget(self.outfile_edit, 1, 5)
        tab_main_layout.addWidget(mem_group)
        
        # ---- Flash 烧录参数 ----
        flash_group = QGroupBox("Flash 烧录参数")
        flash_layout = QGridLayout(flash_group)
        
        self.flash_addr_combo = QComboBox()
        self.flash_addr_combo.addItems(list(self.flash_addr_preset.keys()))
        self.flash_addr_combo.currentIndexChanged.connect(self.on_bin_addr_preset_change)
        flash_layout.addWidget(QLabel("Flash地址预设："), 0, 0)
        flash_layout.addWidget(self.flash_addr_combo, 0, 1, 1, 3)
        
        flash_layout.addWidget(QLabel("bin烧录地址："), 1, 0)
        self.bin_addr_edit = QLineEdit(self.config.get("last_bin_flash_addr", "0x3E8000"))
        flash_layout.addWidget(self.bin_addr_edit, 1, 1)
        
        self.load_path_edit = QLineEdit()
        self.load_path_edit.setPlaceholderText("RAM加载 .out/.elf 文件路径")
        self.btn_sel_load = QPushButton("📂 选文件")
        self.btn_sel_load.clicked.connect(lambda: self.select_file(self.load_path_edit, "程序文件(*.out *.elf)"))
        flash_layout.addWidget(QLabel("RAM加载："), 2, 0)
        flash_layout.addWidget(self.load_path_edit, 2, 1, 1, 4)
        flash_layout.addWidget(self.btn_sel_load, 2, 5)
        
        self.elf_path_edit = QLineEdit()
        self.elf_path_edit.setPlaceholderText("Flash烧录 .out/.elf 文件路径")
        self.btn_sel_elf = QPushButton("📂 选文件")
        self.btn_sel_elf.clicked.connect(lambda: self.select_file(self.elf_path_edit, "程序文件(*.out *.elf)"))
        flash_layout.addWidget(QLabel("ELF烧录："), 3, 0)
        flash_layout.addWidget(self.elf_path_edit, 3, 1, 1, 4)
        flash_layout.addWidget(self.btn_sel_elf, 3, 5)
        
        self.bin_path_edit = QLineEdit()
        self.bin_path_edit.setPlaceholderText("Flash烧录 .bin 文件路径")
        self.btn_sel_bin = QPushButton("📂 选文件")
        self.btn_sel_bin.clicked.connect(lambda: self.select_file(self.bin_path_edit, "二进制文件(*.bin)"))
        flash_layout.addWidget(QLabel("BIN烧录："), 4, 0)
        flash_layout.addWidget(self.bin_path_edit, 4, 1, 1, 4)
        flash_layout.addWidget(self.btn_sel_bin, 4, 5)
        
        tab_main_layout.addWidget(flash_group)
        
        # ---- CSM 密码输入（简化版）----
        csm_group = QGroupBox("CSM 密码设置（擦除解锁用）")
        csm_layout = QHBoxLayout(csm_group)
        csm_layout.addWidget(QLabel("128位密码（默认全FFFF）："))
        
        self.csm_keys = []
        for i in range(4):
            vlayout = QVBoxLayout()
            edit = QLineEdit("FFFF")
            edit.setFixedWidth(70)
            edit.setMaxLength(4)
            vlayout.addWidget(QLabel(f"K{i*2}-{i*2+1}"))
            vlayout.addWidget(edit)
            csm_layout.addLayout(vlayout)
            self.csm_keys.append(edit)
            vlayout2 = QVBoxLayout()
            edit2 = QLineEdit("FFFF")
            edit2.setFixedWidth(70)
            edit2.setMaxLength(4)
            vlayout2.addWidget(QLabel(f"K{i*2+2}-{i*2+3}"))
            vlayout2.addWidget(edit2)
            csm_layout.addLayout(vlayout2)
            self.csm_keys.append(edit2)
        
        csm_layout.addStretch()
        self.chk_auto_reset = QCheckBox("连接后自动复位")
        self.chk_auto_reset.setChecked(True)
        csm_layout.addWidget(self.chk_auto_reset)
        tab_main_layout.addWidget(csm_group)
        
        # ---- 内存预览 ----
        preview_group = QGroupBox("内存预览")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(120)
        self.preview_text.setPlaceholderText("内存读取后预览...")
        preview_layout.addWidget(self.preview_text)
        tab_main_layout.addWidget(preview_group)
        
        tab_main_layout.addStretch()
        self.tabs.addTab(tab_main, "🔧 烧录与调试")
        
        # ---- 标签2: 运行日志 ----
        tab_log = QWidget()
        tab_log_layout = QVBoxLayout(tab_log)
        
        log_btn_layout = QHBoxLayout()
        self.btn_export_log = QPushButton("📤 导出日志")
        self.btn_export_log.clicked.connect(self.save_log)
        self.btn_clear_log2 = QPushButton("🗑️ 清空")
        self.btn_clear_log2.clicked.connect(lambda: self.log_text.clear())
        self.check_auto_scroll = QCheckBox("自动滚动")
        self.check_auto_scroll.setChecked(True)
        log_btn_layout.addWidget(self.btn_export_log)
        log_btn_layout.addWidget(self.btn_clear_log2)
        log_btn_layout.addStretch()
        log_btn_layout.addWidget(self.check_auto_scroll)
        tab_log_layout.addLayout(log_btn_layout)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas; font-size: 11px;")
        self.log_text.setMinimumHeight(300)
        tab_log_layout.addWidget(self.log_text)
        self.tabs.addTab(tab_log, "📋 运行日志")
        
        main_layout.addWidget(self.tabs)
        
        # 状态栏
        self.statusBar().showMessage(f"就绪 | {self.BIN_DIR}")

    # ====================== 通用方法 ======================
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {msg}")
        if self.check_auto_scroll.isChecked():
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )

    def set_busy(self, busy):
        widgets = [
            self.btn_read_mem, self.btn_load_ram, self.btn_flash_elf,
            self.btn_flash_bin, self.btn_erase, self.btn_unlock,
            self.btn_erase_sectors, self.btn_check, self.btn_read_id
        ]
        for w in widgets:
            w.setEnabled(not busy)
        self.progress_bar.setVisible(busy)
        self.status_icon.setText("⏳" if busy else "⚙️")
        self.status_label.setText("执行中..." if busy else "就绪")
        if not busy:
            self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")

    def update_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"{text} ({value}%)")

    def select_file(self, edit, filter_str):
        path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", filter_str)
        if path:
            edit.setText(path)

    def select_bin_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择 DSLite.exe 所在目录", self.BIN_DIR)
        if path:
            if os.path.exists(os.path.join(path, "DSLite.exe")):
                self.BIN_DIR = path
                self.lbl_workdir.setText(f"工作目录：{path}")
                self.config["bin_dir"] = path
                save_config(self.config)
                self.log(f"✅ 工作目录已更新: {path}")
            else:
                QMessageBox.warning(self, "警告", "该目录下未找到 DSLite.exe！")

    def auto_detect(self):
        self.log("🔍 正在自动检测工具链...")
        dslite = find_dslite()
        cl2000 = find_cl2000()
        if dslite:
            self.BIN_DIR = dslite
            self.lbl_workdir.setText(f"工作目录：{dslite}")
            self.config["bin_dir"] = dslite
            save_config(self.config)
            self.log(f"✅ DSLite 工具链: {dslite}")
        else:
            self.log("⚠️ 未找到 DSLite，请手动选择目录")
        if cl2000:
            self.log(f"✅ C2000 编译器: {cl2000}")
        else:
            self.log("ℹ️ 未找到 C2000 编译器（如需编译请安装 CCS）")
    
    def save_current_config(self):
        self.config["chip"] = self.chip_combo.currentText()
        self.config["ccxml"] = self.ccxml_edit.text()
        self.config["last_bin_flash_addr"] = self.bin_addr_edit.text()
        save_config(self.config)
        self.log("✅ 配置已保存")

    def save_log(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", f"DSLite_日志_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "文本文件(*.txt);;所有文件(*.*)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.log_text.toPlainText())
                self.log(f"✅ 日志已保存: {path}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")

    def run_cmd(self, task_name, args, output_file=""):
        if not os.path.exists(os.path.join(self.BIN_DIR, "DSLite.exe")):
            QMessageBox.warning(self, "错误", f"DSLite.exe 未找到！\n当前目录: {self.BIN_DIR}")
            return
        
        self.set_busy(True)
        self.log(f"\n▶️ {task_name}")
        self.log(f"命令: {' '.join(args)}")
        
        thread = CmdThread(task_name, args, self.BIN_DIR, output_file)
        thread.log_sig.connect(self.log)
        thread.progress_sig.connect(self.update_progress)
        thread.done_sig.connect(lambda ok, f: self.on_task_done(ok, f, thread))
        thread.error_sig.connect(lambda e: QMessageBox.warning(self, "错误", e))
        
        self.active_threads.append(thread)
        thread.start()

    def on_task_done(self, is_ok, output_file, thread):
        if thread in self.active_threads:
            self.active_threads.remove(thread)
        if not self.active_threads:
            self.set_busy(False)
        if is_ok:
            self.log("✅ 操作成功！")
            if output_file:
                self.load_hex_preview(output_file)
        else:
            self.log("❌ 操作失败！")

    # ====================== 内存读取 ======================
    def on_preset_change(self):
        key = self.addr_combo.currentText()
        if key in self.addr_preset:
            c = self.addr_preset[key]
            self.addr_edit.setText(c["addr"])
            self.len_edit.setText(c["len"])

    def start_read_memory(self):
        addr = self.addr_edit.text().strip()
        length = self.len_edit.text().strip()
        out_file = self.outfile_edit.text().strip()

        if not addr or not length:
            QMessageBox.warning(self, "警告", "请填写地址和长度！")
            return
        
        out_full = os.path.join(self.BIN_DIR, out_file)
        args = ["DSLite.exe", "memory",
                f"--config={self.CCXML_FILE}",
                f"--range={addr},{length}",
                f"--output={out_file}", "--verbose"]
        
        self.run_cmd(f"读取内存: addr={addr} len={length}", args, out_full)

    def load_hex_preview(self, file_path):
        if not os.path.exists(file_path):
            self.preview_text.setText("[错误] 文件不存在")
            return
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            
            # 大文件只显示前 512 字节
            display_data = data[:512]
            truncated = len(data) > 512
            
            hex_str = display_data.hex(" ", 1).upper()
            lines = []
            for i in range(0, len(hex_str), 48):
                offset = (i // 48) * 16
                line = f"{offset:08X}  {hex_str[i:i+48]}"
                lines.append(line)
            
            info = f"总大小: {len(data)} 字节"
            if truncated:
                info += " (仅显示前512字节)"
            self.preview_text.setText(f"{info}\n" + "\n".join(lines[:20]))
            
        except Exception as e:
            self.preview_text.setText(f"预览失败: {str(e)}")

    # ====================== RAM加载 ======================
    def start_load_program(self):
        file_path = self.load_path_edit.text().strip()
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "警告", "请选择有效文件！")
            return
        args = ["DSLite.exe", "load", f"--config={self.CCXML_FILE}", file_path, "--verbose"]
        self.run_cmd(f"加载RAM: {os.path.basename(file_path)}", args)

    # ====================== Flash 烧录 ======================
    def start_elf_flash(self):
        file_path = self.elf_path_edit.text().strip()
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "警告", "请选择有效文件！")
            return
        args = ["DSLite.exe", "flash", f"--config={self.CCXML_FILE}", file_path, "--verbose"]
        self.run_cmd(f"烧录ELF: {os.path.basename(file_path)}", args)

    def start_bin_flash(self):
        file_path = self.bin_path_edit.text().strip()
        flash_addr = self.bin_addr_edit.text().strip()
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "警告", "请选择有效文件！")
            return
        if not flash_addr:
            QMessageBox.warning(self, "警告", "请填写地址！")
            return
        bin_target = f"{file_path},{flash_addr}"
        args = ["DSLite.exe", "flash", f"--config={self.CCXML_FILE}", bin_target, "--verbose"]
        self.run_cmd(f"烧录BIN: {os.path.basename(file_path)} -> {flash_addr}", args)

    def on_bin_addr_preset_change(self):
        key = self.flash_addr_combo.currentText()
        if key in self.flash_addr_preset:
            self.bin_addr_edit.setText(self.flash_addr_preset[key])

    # ====================== 擦除解锁 ======================
    def start_erase_all(self):
        keys = []
        for i, edit in enumerate(self.csm_keys):
            k = edit.text().strip().upper()
            if not k:
                k = "FFFF"
            try:
                int(k, 16)
                keys.append(k)
            except:
                QMessageBox.warning(self, "警告", f"CSM Key{i} 无效！")
                return

        self.log("\n" + "=" * 60)
        self.log("【全擦除 + 解锁】")
        self.log("⚠️ 点击确定后请立即给目标板上电！")

        args = ["DSLite.exe", "flash", f"--config={self.CCXML_FILE}"]
        for i, k in enumerate(keys):
            args.extend(["-s", f"FlashKey{i}={k}"])
        if self.chk_auto_reset.isChecked():
            args.extend(["-s", "AutoResetOnConnect=true", "-s", "HaltOnConnect=true"])
        args.extend(["-a", "Unlock", "-a", "Erase", "--verbose"])

        self.run_cmd("全擦除+解锁", args)

    def start_erase_sectors(self):
        args = ["DSLite.exe", "flash", f"--config={self.CCXML_FILE}", "-a", "Erase", "--verbose"]
        self.run_cmd("擦除扇区", args)

    def start_unlock_only(self):
        """仅解锁芯片，不擦除"""
        keys = []
        for i, edit in enumerate(self.csm_keys):
            k = edit.text().strip().upper()
            if not k: k = "FFFF"
            try:
                int(k, 16)
                keys.append(k)
            except:
                QMessageBox.warning(self, "警告", f"CSM Key{i} 无效！")
                return

        self.log("\n" + "=" * 60)
        self.log("【仅解锁芯片】")

        args = ["DSLite.exe", "flash", f"--config={self.CCXML_FILE}"]
        for i, k in enumerate(keys):
            args.extend(["-s", f"FlashKey{i}={k}"])
        if self.chk_auto_reset.isChecked():
            args.extend(["-s", "AutoResetOnConnect=true", "-s", "HaltOnConnect=true"])
        args.extend(["-a", "Unlock", "--verbose"])

        self.log(f"命令: {' '.join(args)}")
        self.log("⚠️ 点击确定后立即给目标板上电！")
        self.run_cmd("仅解锁", args)

    def check_device_status(self):
        """检测设备连接状态"""
        args = ["DSLite.exe", "-s", f"--config={self.CCXML_FILE}", "-a", "Connect", "--verbose"]
        self.log("\n" + "=" * 60)
        self.log("【检测设备连接】")
        self.log("⚠️ 请确保目标板已上电并连接调试器")
        self.run_cmd("检测设备", args)

    def read_device_id(self):
        """读取芯片ID"""
        args = ["DSLite.exe", "-s", f"--config={self.CCXML_FILE}", "-a", "GetDeviceID", "--verbose"]
        self.log("\n" + "=" * 60)
        self.log("【读取芯片ID】")
        self.run_cmd("读取芯片ID", args)


# ====================== 启动 =======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = FullDSLiteTool()
    window.show()
    sys.exit(app.exec_())
