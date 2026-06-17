STANDARD_FIELDS = {
    'record_date': '记录日期',
    'style_name': '样式名称',
    'group_no': '分组编号',
    'missing_parts': '缺件名称',
    'completed_count': '完成数量',
    'rework_count': '返工数量',
    'helper_name': '助理姓名',
    'note': '备注'
}

FIELD_TYPES = {
    'record_date': 'datetime',
    'style_name': 'string',
    'group_no': 'string',
    'missing_parts': 'string',
    'completed_count': 'numeric',
    'rework_count': 'numeric',
    'helper_name': 'string',
    'note': 'string'
}

MISSING_PART_EMPTY_VALUES = {
    '', 'nan', 'none', '无', '没有', '无缺件',
    '0', '-', '/', 'n/a', 'null'
}

MISSING_PART_SPLIT_PATTERN = r'[,，、;；]'

STATUS_LABELS = {
    'missing_and_rework': '缺件+返工',
    'missing_only': '缺件待补',
    'rework_only': '返工中',
    'completed': '已完成',
    'in_progress': '进行中'
}

DATA_TYPE_LABELS = {
    'material': '材料发放记录',
    'completion': '完成清单',
    'rework': '返工台账',
    'general': '综合数据'
}

NUMERIC_FIELDS = ['completed_count', 'rework_count']

STRING_FIELDS = ['style_name', 'group_no', 'missing_parts', 'helper_name', 'note']

DEFAULT_SOURCE_TYPE = 'general'
