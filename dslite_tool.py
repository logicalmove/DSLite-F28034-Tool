import sys
import os
import subprocess
import xml.etree.ElementTree as ET
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTextEdit, QGroupBox, QComboBox,
    QFileDialog, QSplitter, QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt

# ====================== 后台执行线程 =======================
class CmdThread(QThread):
    log_sig = pyqtSignal(str)
    done_sig = pyqtSignal(bool, str)

    def __init__(self, args, work_dir, output_file=""):
        super().__init__()
        self.args = args
        self.work_dir = work_dir
        self.output_file = output_file

    def run(self):
        try:
            res = subprocess.run(
                self.args,
                cwd=self.work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            full_log = res.stdout + "\n" + res.stderr
            self.log_sig.emit(full_log)
            is_ok = res.returncode == 0
            self.done_sig.emit(is_ok, self.output_file)
        except Exception as e:
            self.log_sig.emit(f"[执行异常] {str(e)}")
            self.done_sig.emit(False, "")


# ====================== 主窗口 =======================
class FullDSLiteTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DSLite 全功能上位机 | F28034 专用")
        self.resize(1050, 950)

        self.BIN_DIR = r"C:\Users\hjs\Desktop\test\test--2026-4-2\test\ccs_base\DebugServer\bin"
        self.CCXML_FILE = "f28034.ccxml"

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
            "Flash H扇区 起始地址 (0x3E8000)": "0x3E8000",
            "Flash G扇区 起始地址 (0x3EA000)": "0x3EA000",
            "Flash F扇区 起始地址 (0x3EC000)": "0x3EC000",
            "Flash E扇区 起始地址 (0x3EE000)": "0x3EE000",
            "Flash D扇区 起始地址 (0x3F0000)": "0x3F0000",
            "Flash C扇区 起始地址 (0x3F2000)": "0x3F2000",
            "Flash B扇区 起始地址 (0x3F4000)": "0x3F4000",
            "Flash A扇区 起始地址 (0x3F6000)": "0x3F6000",
        }

        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # -------------------- 1. 基础配置 --------------------
        conf_group = QGroupBox("基础配置")
        conf_layout = QHBoxLayout(conf_group)
        conf_layout.addWidget(QLabel(f"工作目录：{self.BIN_DIR}"))
        conf_layout.addWidget(QLabel(f"芯片配置：{self.CCXML_FILE}"))
        main_layout.addWidget(conf_group)

        # -------------------- 2. 内存读取 --------------------
        mem_group = QGroupBox("一、内存读取 Memory")
        mem_layout = QVBoxLayout(mem_group)

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("常用地址预设："))
        self.addr_combo = QComboBox()
        self.addr_combo.addItems(list(self.addr_preset.keys()))
        self.addr_combo.currentIndexChanged.connect(self.on_preset_change)
        preset_layout.addWidget(self.addr_combo)
        preset_layout.addStretch()
        mem_layout.addLayout(preset_layout)

        input_layout = QHBoxLayout()
        self.addr_edit = QLineEdit("0x7200")
        self.len_edit = QLineEdit("0x10")
        self.outfile_edit = QLineEdit("mem_read.bin")
        self.read_btn = QPushButton("📥 开始读取内存")
        self.read_btn.setFixedWidth(150)
        self.read_btn.clicked.connect(self.start_read_memory)

        input_layout.addWidget(QLabel("起始地址："))
        input_layout.addWidget(self.addr_edit)
        input_layout.addWidget(QLabel("读取长度："))
        input_layout.addWidget(self.len_edit)
        input_layout.addWidget(QLabel("输出文件："))
        input_layout.addWidget(self.outfile_edit)
        input_layout.addWidget(self.read_btn)
        mem_layout.addLayout(input_layout)

        preview_layout = QHBoxLayout()
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumHeight(150)
        self.preview_text.setPlaceholderText("内存读取成功后，将在这里显示十六进制内容...")
        preview_layout.addWidget(self.preview_text)
        mem_layout.addLayout(preview_layout)
        main_layout.addWidget(mem_group)

        # -------------------- 3. RAM加载 --------------------
        load_group = QGroupBox("二、加载程序到 RAM Load（掉电丢失）")
        load_layout = QVBoxLayout(load_group)
        self.load_path_edit = QLineEdit()
        self.load_path_edit.setPlaceholderText("选择要加载的 .out/.elf 程序文件")
        load_sel_btn = QPushButton("📂 选择程序文件")
        load_sel_btn.clicked.connect(self.select_load_file)
        self.load_run_btn = QPushButton("🚀 执行加载到RAM")
        self.load_run_btn.clicked.connect(self.start_load_program)

        load_layout.addWidget(self.load_path_edit)
        load_btn_layout = QHBoxLayout()
        load_btn_layout.addWidget(load_sel_btn)
        load_btn_layout.addWidget(self.load_run_btn)
        load_layout.addLayout(load_btn_layout)
        main_layout.addWidget(load_group)

        # -------------------- 4. Flash烧录 --------------------
        flash_splitter = QSplitter(Qt.Horizontal)

        flash_elf_group = QGroupBox("三、烧录程序到 Flash（out/elf格式）")
        flash_elf_layout = QVBoxLayout(flash_elf_group)
        self.elf_flash_path_edit = QLineEdit()
        self.elf_flash_path_edit.setPlaceholderText("选择要烧录的 .out/.elf 程序文件")
        elf_sel_btn = QPushButton("📂 选择程序文件")
        elf_sel_btn.clicked.connect(self.select_elf_flash_file)
        self.elf_flash_btn = QPushButton("🔥 开始烧录程序")
        self.elf_flash_btn.clicked.connect(self.start_elf_flash)

        flash_elf_layout.addWidget(self.elf_flash_path_edit)
        elf_btn_layout = QHBoxLayout()
        elf_btn_layout.addWidget(elf_sel_btn)
        elf_btn_layout.addWidget(self.elf_flash_btn)
        flash_elf_layout.addLayout(elf_btn_layout)
        flash_splitter.addWidget(flash_elf_group)

        flash_bin_group = QGroupBox("四、烧录二进制文件到 Flash（bin格式）")
        flash_bin_layout = QVBoxLayout(flash_bin_group)

        bin_addr_layout = QHBoxLayout()
        bin_addr_layout.addWidget(QLabel("Flash地址预设："))
        self.bin_addr_combo = QComboBox()
        self.bin_addr_combo.addItems(list(self.flash_addr_preset.keys()))
        self.bin_addr_combo.currentIndexChanged.connect(self.on_bin_addr_preset_change)
        bin_addr_layout.addWidget(self.bin_addr_combo)
        bin_addr_layout.addStretch()
        flash_bin_layout.addLayout(bin_addr_layout)

        addr_input_layout = QHBoxLayout()
        self.bin_addr_edit = QLineEdit("0x3E8000")
        addr_input_layout.addWidget(QLabel("烧录起始地址："))
        addr_input_layout.addWidget(self.bin_addr_edit)
        flash_bin_layout.addLayout(addr_input_layout)

        self.bin_flash_path_edit = QLineEdit()
        self.bin_flash_path_edit.setPlaceholderText("选择要烧录的 .bin 二进制文件")
        bin_sel_btn = QPushButton("📂 选择bin文件")
        bin_sel_btn.clicked.connect(self.select_bin_flash_file)
        self.bin_flash_btn = QPushButton("🔥 开始烧录bin文件")
        self.bin_flash_btn.clicked.connect(self.start_bin_flash)

        flash_bin_layout.addWidget(self.bin_flash_path_edit)
        bin_btn_layout = QHBoxLayout()
        bin_btn_layout.addWidget(bin_sel_btn)
        bin_btn_layout.addWidget(self.bin_flash_btn)
        flash_bin_layout.addLayout(bin_btn_layout)
        flash_splitter.addWidget(flash_bin_group)

        main_layout.addWidget(flash_splitter)

        # -------------------- 5. 擦除解锁 --------------------
        erase_group = QGroupBox("五、Flash擦除与解锁")
        erase_layout = QVBoxLayout(erase_group)

        pwd_layout = QHBoxLayout()
        pwd_layout.addWidget(QLabel("CSM密码（128位，默认全FFFF）："))
        self.csm_keys = []
        for i in range(8):
            key_edit = QLineEdit("FFFF")
            key_edit.setFixedWidth(60)
            key_edit.setMaxLength(4)
            pwd_layout.addWidget(QLabel(f"Key{i}:"))
            pwd_layout.addWidget(key_edit)
            self.csm_keys.append(key_edit)
        erase_layout.addLayout(pwd_layout)

        tip_label = QLabel("⚠️ 先断开电源 → 点击按钮 → 立即上电")
        tip_label.setStyleSheet("color: #d32f2f; font-weight: bold; font-size: 14px;")
        erase_layout.addWidget(tip_label)

        erase_btn_layout = QHBoxLayout()
        self.erase_all_btn = QPushButton("🔓 全擦除解锁（推荐）")
        self.erase_all_btn.setFixedHeight(45)
        self.erase_all_btn.clicked.connect(self.start_erase_all)
        self.erase_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f; color: white;
                font-weight: bold; font-size: 14px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #b71c1c; }
            QPushButton:disabled { background-color: #9e9e9e; }
        """)

        self.erase_sectors_btn = QPushButton("擦除所有Flash扇区（无需解锁）")
        self.erase_sectors_btn.setFixedHeight(45)
        self.erase_sectors_btn.clicked.connect(self.start_erase_sectors)

        erase_btn_layout.addWidget(self.erase_all_btn)
        erase_btn_layout.addWidget(self.erase_sectors_btn)
        erase_layout.addLayout(erase_btn_layout)
        main_layout.addWidget(erase_group)

        # -------------------- 6. 运行日志 --------------------
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        log_btn_layout = QHBoxLayout()
        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        log_btn_layout.addStretch()
        log_btn_layout.addWidget(self.clear_log_btn)
        log_layout.addLayout(log_btn_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_group)

    # ====================== 通用功能 ======================
    def log(self, msg):
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def set_btn_enable(self, enable):
        self.read_btn.setEnabled(enable)
        self.load_run_btn.setEnabled(enable)
        self.elf_flash_btn.setEnabled(enable)
        self.bin_flash_btn.setEnabled(enable)
        self.erase_all_btn.setEnabled(enable)
        self.erase_sectors_btn.setEnabled(enable)

    # ====================== 内存读取 ======================
    def on_preset_change(self):
        select_key = self.addr_combo.currentText()
        if select_key in self.addr_preset:
            config = self.addr_preset[select_key]
            self.addr_edit.setText(config["addr"])
            self.len_edit.setText(config["len"])

    def start_read_memory(self):
        addr = self.addr_edit.text().strip()
        length = self.len_edit.text().strip()
        out_file = self.outfile_edit.text().strip()
        out_full_path = os.path.join(self.BIN_DIR, out_file)

        if not addr or not length:
            QMessageBox.warning(self, "警告", "请填写地址和长度！")
            return

        args = [
            "DSLite.exe", "memory",
            f"--config={self.CCXML_FILE}",
            f"--range={addr},{length}",
            f"--output={out_file}",
            "--verbose"
        ]

        self.log("\n" + "=" * 60)
        self.log(f"【读取内存】地址：{addr}，长度：{length}")
        self.log(f"命令：{' '.join(args)}")
        self.set_btn_enable(False)

        self.thread = CmdThread(args, self.BIN_DIR, out_full_path)
        self.thread.log_sig.connect(self.log)
        self.thread.done_sig.connect(self.on_read_finish)
        self.thread.start()

    def on_read_finish(self, is_ok, out_file):
        self.set_btn_enable(True)
        if is_ok:
            self.log("\n✅ 内存读取成功！")
            self.load_hex_preview(out_file)
        else:
            self.log("\n❌ 内存读取失败！")
            self.preview_text.clear()

    def load_hex_preview(self, file_path):
        if not os.path.exists(file_path):
            self.preview_text.setText("[错误] 文件不存在")
            return
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            hex_str = data.hex(" ", 1).upper()
            format_hex = "\n".join([hex_str[i:i + 48] for i in range(0, len(hex_str), 48)])
            self.preview_text.setText(f"===== 十六进制内容（共 {len(data)} 字节）=====\n{format_hex}")
        except Exception as e:
            self.preview_text.setText(f"预览失败：{str(e)}")

    # ====================== RAM加载 ======================
    def select_load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择程序", "", "程序文件(*.out *.elf);;所有文件(*.*)"
        )
        if path:
            self.load_path_edit.setText(path)

    def start_load_program(self):
        file_path = self.load_path_edit.text().strip()
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "警告", "请选择有效文件！")
            return

        args = [
            "DSLite.exe", "load",
            f"--config={self.CCXML_FILE}",
            file_path, "--verbose"
        ]

        self.log("\n" + "=" * 60)
        self.log(f"【加载到RAM】{file_path}")
        self.set_btn_enable(False)

        self.thread = CmdThread(args, self.BIN_DIR)
        self.thread.log_sig.connect(self.log)
        self.thread.done_sig.connect(self.on_common_finish)
        self.thread.start()

    # ====================== out/elf烧录 ======================
    def select_elf_flash_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择程序", "", "程序文件(*.out *.elf);;所有文件(*.*)"
        )
        if path:
            self.elf_flash_path_edit.setText(path)

    def start_elf_flash(self):
        file_path = self.elf_flash_path_edit.text().strip()
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "警告", "请选择有效文件！")
            return

        args = [
            "DSLite.exe", "flash",
            f"--config={self.CCXML_FILE}",
            file_path, "--verbose"
        ]

        self.log("\n" + "=" * 60)
        self.log(f"【烧录Flash】{file_path}")
        self.set_btn_enable(False)

        self.thread = CmdThread(args, self.BIN_DIR)
        self.thread.log_sig.connect(self.log)
        self.thread.done_sig.connect(self.on_common_finish)
        self.thread.start()

    # ====================== bin烧录 ======================
    def on_bin_addr_preset_change(self):
        select_key = self.bin_addr_combo.currentText()
        if select_key in self.flash_addr_preset:
            self.bin_addr_edit.setText(self.flash_addr_preset[select_key])

    def select_bin_flash_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择bin文件", "", "二进制文件(*.bin);;所有文件(*.*)"
        )
        if path:
            self.bin_flash_path_edit.setText(path)

    def start_bin_flash(self):
        file_path = self.bin_flash_path_edit.text().strip()
        flash_addr = self.bin_addr_edit.text().strip()

        if not os.path.exists(file_path):
            QMessageBox.warning(self, "警告", "请选择有效文件！")
            return
        if not flash_addr:
            QMessageBox.warning(self, "警告", "请填写地址！")
            return

        bin_target = f"{file_path},{flash_addr}"
        args = [
            "DSLite.exe", "flash",
            f"--config={self.CCXML_FILE}",
            bin_target, "--verbose"
        ]

        self.log("\n" + "=" * 60)
        self.log(f"【烧录bin】{file_path} → {flash_addr}")
        self.set_btn_enable(False)

        self.thread = CmdThread(args, self.BIN_DIR)
        self.thread.log_sig.connect(self.log)
        self.thread.done_sig.connect(self.on_common_finish)
        self.thread.start()

    # ====================== 擦除解锁 ======================
    def start_erase_all(self):
        keys = []
        for i in range(8):
            key_str = self.csm_keys[i].text().strip().upper()
            if not key_str:
                key_str = "FFFF"
            try:
                int(key_str, 16)
                keys.append(key_str)
            except:
                QMessageBox.warning(self, "警告", f"CSMKey{i}无效！")
                return

        self.log("\n" + "=" * 60)
        self.log("【全擦除 + 解锁】")

        args = [
            "DSLite.exe", "flash",
            f"--config={self.CCXML_FILE}",
            "-s", f"FlashKey0={keys[0]}",
            "-s", f"FlashKey1={keys[1]}",
            "-s", f"FlashKey2={keys[2]}",
            "-s", f"FlashKey3={keys[3]}",
            "-s", f"FlashKey4={keys[4]}",
            "-s", f"FlashKey5={keys[5]}",
            "-s", f"FlashKey6={keys[6]}",
            "-s", f"FlashKey7={keys[7]}",
            "-s", "AutoResetOnConnect=true",
            "-s", "HaltOnConnect=true",
            "-a", "Unlock",
            "-a", "Erase",
            "--verbose"
        ]

        self.log(f"命令：{' '.join(args)}")
        self.log("⚠️ 点击按钮后立即上电！")
        self.set_btn_enable(False)

        self.thread = CmdThread(args, self.BIN_DIR)
        self.thread.log_sig.connect(self.log)
        self.thread.done_sig.connect(self.on_erase_finish)
        self.thread.start()

    def start_erase_sectors(self):
        args = [
            "DSLite.exe", "flash",
            f"--config={self.CCXML_FILE}",
            "-a", "Erase",
            "--verbose"
        ]

        self.log("\n" + "=" * 60)
        self.log("【擦除扇区】")
        self.set_btn_enable(False)

        self.thread = CmdThread(args, self.BIN_DIR)
        self.thread.log_sig.connect(self.log)
        self.thread.done_sig.connect(self.on_common_finish)
        self.thread.start()

    def on_erase_finish(self, is_ok, _):
        self.set_btn_enable(True)
        if is_ok:
            self.log("\n✅ 全擦除 + 解锁成功！")
            QMessageBox.information(self, "成功", "解锁成功！")
        else:
            self.log("\n❌ 擦除失败！")
            QMessageBox.warning(self, "失败", "擦除失败！")

    def on_common_finish(self, is_ok, _):
        self.set_btn_enable(True)
        if is_ok:
            self.log("\n✅ 操作成功！")
        else:
            self.log("\n❌ 操作失败！")


# ====================== 启动 ======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FullDSLiteTool()
    window.show()
    sys.exit(app.exec_())
