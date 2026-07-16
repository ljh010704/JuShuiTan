# -*- coding: utf-8 -*-
import os

# Add table responsive wrapper in CSS
css_path = r'F:/JuShuiTan/static/css/style.css'
with open(css_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add .table-responsive wrapper styles after .data-table
old_css = '''/* 筛选栏 */'''
new_css = '''/* 表格响应式 */
.table-responsive {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    margin-bottom: 16px;
}
.table-responsive .data-table {
    min-width: 900px;
}

/* 筛选栏 */'''
content = content.replace(old_css, new_css)

with open(css_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('CSS: table-responsive added')
