# 芯片BIN文件解析工具 - 专为 TMS320F28034 寄存器/内存设计
def read_bin_file(file_name):
    try:
        # 以二进制模式读取文件
        with open(file_name, 'rb') as f:
            binary_data = f.read()

        print(f"✅ 成功读取文件：{file_name}")
        print(f"📊 数据长度：{len(binary_data)} 字节\n")
        print("地址偏移    十六进制数据 (寄存器/内存值)")
        print("-" * 50)

        # 按16字节分行打印（带地址偏移，方便查看寄存器）
        for i in range(0, len(binary_data), 16):
            # 地址偏移（十六进制）
            offset = f"0x{i:04X}"
            # 截取16字节数据
            chunk = binary_data[i:i+16]
            # 转十六进制
            hex_str = ' '.join(f"{byte:02X}" for byte in chunk)
            print(f"{offset}      {hex_str}")

    except FileNotFoundError:
        print(f"❌ 错误：没找到文件 {file}，请确认文件名正确！")

# ===================== 你只需要改这里 =====================
# 把这里改成你的BIN文件名（比如 flash.bin / adc_reg.bin）
BIN_FILE_NAME = "flash.bin"
# ==========================================================

if __name__ == "__main__":
    read_bin_file(BIN_FILE_NAME)