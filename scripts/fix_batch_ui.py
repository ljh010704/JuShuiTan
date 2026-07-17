import sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'F:/JuShuiTan/templates/profit_check.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    # Fix type names (mojibake ones are ASCII-only)
    if "'all':" in line and i > 0 and "typeNames" in lines[i-1]:
        lines[i] = "        'all': '\u5168\u90e8\uff08\u4f9b\u5e94\u5546\u5df2\u4e0b\u67b6 + \u7981\u552e\u5e73\u53f0\uff09',\n"
    if "'supplier':" in line and i > 0:
        lines[i] = "        'supplier': '\u4f9b\u5e94\u5546\u5df2\u4e0b\u67b6\u5546\u54c1',\n"
    if "'banned':" in line and i > 0:
        lines[i] = "        'banned': '\u7981\u552e\u5e73\u53f0\u5546\u54c1',\n"
    if 'confirm' in line and 'typeNames' in line:
        lines[i] = "    if (!confirm('\u786e\u8ba4\u8981\u6267\u884c\u3010' + typeNames[type] + '\u3011\u7684\u4e0b\u67b6\u64cd\u4f5c\u5417\uff1f\\\\n\\\\n\u6b64\u64cd\u4f5c\u4e0d\u53ef\u64a4\u9500\uff01')) return;\n"
    if '\u6b63\u5728\u6267\u884c\u6279\u91cf\u4e0b\u67b6' in line:
        lines[i] = "    statusText.textContent = '\u6b63\u5728\u6267\u884c\u6279\u91cf\u4e0b\u67b6\uff0c\u8bf7\u52ff\u5173\u95ed\u9875\u9762...';\n"
    if '\u6210\u529f\uff01' in line and 'statusText' in line:
        lines[i] = "            statusText.textContent = '\u6210\u529f\uff01' + (res.message || '\u4e0b\u67b6\u5b8c\u6210');\n"
    if '\u5931\u8d25: ' in line and 'statusText' in line:
        lines[i] = "            statusText.textContent = '\u5931\u8d25: ' + (res.message || '\u672a\u77e5\u9519\u8bef');\n"
    if '\u8bf7\u6c42\u5931\u8d25: ' in line and 'statusText' in line:
        lines[i] = "        statusText.textContent = '\u8bf7\u6c42\u5931\u8d25: ' + e.message;\n"

with open(r'F:/JuShuiTan/templates/profit_check.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed Chinese text in batchRemove')
