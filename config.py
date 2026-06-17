STANDARD_FIELDS = {
    'record_date': '记录日期',
    'style_name': '样式名称',
    'group_no': '分组编号',
    'missing_parts': '缺件名称',
    'completed_count': '完成数量',
    'rework_count': '返工数量',
    'helper_name': '助理姓名',
    'note': '备注',
}

FIELD_TYPES = {
    'record_date': 'datetime',
    'style_name': 'string',
    'group_no': 'string',
    'missing_parts': 'string',
    'completed_count': 'numeric',
    'rework_count': 'numeric',
    'helper_name': 'string',
    'note': 'string',
}

MISSING_NEGATIVE_VALUES = frozenset([
    '', 'nan', 'none', '无', '没有', '无缺件', '0', '-', '/', 'n/a', 'null',
])

COLUMN_KEYWORDS = {
    'record_date': ['日期', 'date', '时间'],
    'style_name': ['样式', '款', 'style', 'name'],
    'group_no': ['组', 'group', '编号'],
    'missing_parts': ['缺', 'missing', '少', '材料'],
    'completed_count': ['完成', 'complete', 'done'],
    'rework_count': ['返工', 'rework'],
    'helper_name': ['助理', 'helper', '负责', '老师'],
    'note': ['备注', 'note', '说明'],
}

DATA_TYPE_OPTIONS = {
    '材料发放记录': 'material',
    '完成清单': 'completion',
    '返工台账': 'rework',
    '综合数据': 'general',
}

NUMERIC_FIELDS = frozenset(['completed_count', 'rework_count'])

STRING_FIELDS = frozenset(['style_name', 'group_no', 'missing_parts', 'helper_name', 'note'])

MISSING_PARTS_DELIMITER = r'[,，、;；]'

REWORK_RATE_THRESHOLD = 10.0
HIGH_REWORK_RATE_THRESHOLD = 20.0
HIGH_FREQ_MISSING_THRESHOLD = 3
MATERIAL_BUFFER_RATIO = 0.2
