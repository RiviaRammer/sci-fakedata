"""Structured analysis findings and text/JSON reports."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
import json
import re
from pathlib import Path
from typing import Any


_RULES = {
    "sum_mismatch": ("总和翻车", "The totals do not add up", "在指定容差内，合计不等于预期总和。"),
    "duplicate_series": ("两组数据撞脸了", "Same numbers, different series", "两组序列在所有共同有效位置上的数值相同。"),
    "repeated_block": ("这一段竟然一模一样", "This block matches exactly", "两组序列中出现连续相同的数据段。"),
    "constant_offset": ("整列平移得明明白白", "One constant shifts the whole series", "逐项相减得到固定差值；请核对换算、派生关系和数据来源。"),
    "affine_relation": ("一条公式串起两列", "One formula links both series", "两组序列可由同一线性公式关联。"),
    "repeated_decimal_tail": ("数值变了，尾巴没变", "Different values, same decimal tails", "符合比较条件的对应小数尾部高度一致。"),
    "coarse_difference_grid": ("小数很精细，差值很整齐", "Fine decimals, oddly tidy differences", "多数对应差值落在同一较粗网格上；请检查舍入或派生关系。"),
    "arithmetic_difference": ("连差值都在排队", "Even the differences march in step", "两组数据的对应差值形成等差序列。"),
    "terminal_digit_concentration": ("末位数字偏心了", "A favourite final digit", "某个小数末位数字出现得较多。"),
    "repeated_tail_within_series": ("小数尾巴反复出镜", "The same tail keeps returning", "同一序列中出现重复的小数尾部。"),
    "repeated_value": ("一个数字反复出镜", "One value keeps appearing", "序列中存在重复值。"),
    "arithmetic_sequence": ("等差数列安排上了", "An arithmetic sequence", "相邻有效位置的差值一致。"),
    "constant_series": ("这一列一动不动", "Nothing changes in this series", "序列中的有效数值均相同。"),
    "uniform_precision": ("小数精度很整齐", "Uniform decimal precision", "记录的小数位数一致；统一格式也会产生这种现象。"),
}
_LABELS = {
    "expected": "预期 / Expected", "actual": "实际 / Actual", "difference": "差额 / Difference",
    "atol": "容差 / Tolerance", "offset": "固定偏移 / Offset", "slope": "斜率 / Slope",
    "intercept": "截距 / Intercept", "max_residual": "最大残差 / Max residual",
    "difference_mean": "差值均值 / Mean difference", "difference_std": "差值标准差 / Difference SD",
    "tail_digits": "尾部位数 / Tail digits", "matches": "匹配数 / Matches",
    "eligible_samples": "可比样本 / Eligible samples", "fraction": "比例 / Fraction",
    "grid_step": "网格步长 / Grid step", "threshold": "阈值 / Threshold",
    "digit": "末位数字 / Final digit", "count": "出现次数 / Count",
    "decimal_samples": "小数样本 / Decimal samples", "decimal_places": "小数位数 / Decimal places",
    "step": "步长 / Step", "adjacent_pairs": "相邻对数 / Adjacent pairs",
    "difference_step": "差值步长 / Difference step", "tail": "小数尾部 / Decimal tail",
    "value": "重复值 / Repeated value", "block_length": "连续长度 / Block length",
    "matching_values": "相同数值数 / Matching values", "match_fraction": "匹配比例 / Match fraction",
    "samples": "样本数 / Samples", "length": "序列长度 / Series length",
    "finite_overlap": "共同有效数 / Finite overlap",
}
_ORDER = {code: index for index, code in enumerate(_RULES)}


def _number(value):
    if isinstance(value, float):
        return format(value, ".12g")
    return str(value)


def _note_zh(note):
    if "input:" in note:
        return "输入文件：" + note.replace(" input:", "：")
    if note.startswith("Public source:"):
        return "公开来源：" + note.split(": ", 1)[1]
    if note.startswith("Publisher Source Data snapshot date:"):
        return "出版社数据下载日期：" + note.split(": ", 1)[1]
    if note.startswith("Digit inspection"):
        return "小数检查受最大位数限制；CSV 文本中的尾随零会在该范围内保留。"
    if note.startswith("Coordinates"):
        return "JSON 证据索引从 0 开始；文本报告中标明的行、列和位置从 1 开始。"
    if note.startswith("Text/blank"):
        return "文本和空白单元格视为 NaN，原始相对位置保留。"
    if note.startswith("NumPy/Excel"):
        return "NumPy 和 Excel 数值无法还原原始尾随零或仪器精度。"
    if note.startswith("Equal length"):
        return "长度相同不保证科学上可比，请核对维度、数据集和图板标签。"
    if note.startswith("Rounding"):
        return "舍入、重复测量、单位换算和派生量均可能解释这些关系。"
    if note.startswith("The paper"):
        return "论文有作者更正，详见来源记录；本报告不构成学术不端判定。"
    if "budget reached" in note:
        return "已达到计算预算，部分序列或比较尚未检查，数量见下方。"
    if note.startswith("No axis line"):
        return "没有达到最小样本数的维度序列，请调整阈值或选取更大的数值区域。"
    return "输入处理详情见下方。"


@dataclass
class Finding:
    code: str
    message: str
    series: tuple[str, ...]
    metrics: dict[str, Any] = field(default_factory=dict)
    severity: str = "review"


@dataclass
class Report:
    shapes: dict[str, tuple[int, ...]]
    profiles: list[dict[str, Any]]
    findings: list[Finding]
    comparisons: dict[str, int]
    notes: list[str] = field(default_factory=list)
    declared_conclusions: dict[str, str] = field(default_factory=dict)
    dataset_info: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self):
        result = asdict(self)
        for finding in result["findings"]:
            zh, en, message = _RULES.get(finding["code"], (finding["code"], finding["code"], "数值模式需要复核。"))
            finding.update(title_zh=zh, title_en=en, message_zh=message)
        return result

    def to_json(self, *, indent=2):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, allow_nan=False)

    def summary(self, *, max_findings=30):
        if max_findings is not None and (not isinstance(max_findings, int) or max_findings < 0):
            raise ValueError("max_findings must be a nonnegative integer or None")
        counts = Counter(finding.code for finding in self.findings)
        divider, rule = "=" * 78, "-" * 78
        lines = [
            divider, "SCI-FAKEDATA | 数据体检单 / numerical pattern report", divider,
            f"待复核 / Review: {sum(f.severity != 'info' for f in self.findings)}    "
            f"信息 / Info: {sum(f.severity == 'info' for f in self.findings)}    "
            f"序列 / Series: {len(self.profiles)}",
            f"已比较 / Checked pairs: {self.comparisons.get('checked_pairs', 0)}    "
            f"跨维度 / Cross-axis: {self.comparisons.get('cross_axis_pairs', 0)}    "
            f"跨数据集 / Cross-dataset: {self.comparisons.get('cross_dataset_pairs', 0)}",
            rule, "输入数据 / INPUT DATA", rule,
        ]
        for name, shape in self.shapes.items():
            info = self.dataset_info.get(name, {})
            lines.append(f"  {name}    {' x '.join(map(str, shape))}")
            if info:
                lines.append(f"    原表范围 / Source cells: {info.get('source_excel_range', '')}")
                lines.append(f"    原表标题 / Original panel title: {info.get('description', '')}")
        for name, conclusion in self.declared_conclusions.items():
            lines.append(f"用户填写的结论 / Declared conclusion ({name}; not verified): {conclusion}")
        lines.extend([rule, "模式一览 / PATTERN COUNTS", rule])
        if counts:
            for code, count in sorted(counts.items(), key=lambda item: _ORDER.get(item[0], 99)):
                zh, en, _ = _RULES.get(code, (code, code, ""))
                lines.append(f"  {count:>3}  {zh} / {en} [{code}]")
        else:
            lines.append("  未触发规则 / No rules triggered")
        ranked = sorted(self.findings, key=lambda f: (f.severity == "info", _ORDER.get(f.code, 99)))
        shown = ranked if max_findings is None else ranked[:max_findings]
        for index, finding in enumerate(shown, 1):
            zh, en, message = _RULES.get(finding.code, (finding.code, finding.code, "数值模式需要复核。"))
            lines.extend(["", divider, f"{index:02d} | {'信息 / INFO' if finding.severity == 'info' else '待复核 / REVIEW'} | {zh}",
                          en, rule, f"RULE: {finding.code}"])
            lines.extend("  " + self._location(label) for label in finding.series)
            lines.extend(["", "  " + message, "  " + finding.message])
            metrics = finding.metrics
            if metrics.get("components"):
                lines.append("  算术现场 / Arithmetic: " + " + ".join(_number(v) for v in metrics["components"]) + " = " + _number(metrics["actual"]))
            if "block_start" in metrics:
                lines.append(f"  连续位置 / Consecutive positions: {metrics['block_start'] + 1}..{metrics['block_stop']}")
            if "off_grid_indices" in metrics:
                lines.append("  网格例外位置 / Off-grid positions: " + ", ".join(str(i + 1) for i in metrics["off_grid_indices"]))
            for key, value in metrics.items():
                if key not in _LABELS or isinstance(value, (dict, list, tuple)):
                    continue
                display = f"{value:.1%}" if key in ("fraction", "threshold", "match_fraction") else _number(value)
                lines.append(f"  {_LABELS[key]}: {display}")
            samples = metrics.get("samples")
            if isinstance(samples, list) and samples:
                lines.extend(["", "  对应值现场 / Paired values (A: above first series; B: second)", "  A 为上方第一组，B 为第二组；位置从 1 开始 / Positions start at 1", "  位置 / Index           A                 B               B - A", "  " + "-" * 70])
                for sample in samples:
                    lines.append(f"  {sample['index'] + 1:>12} {_number(sample['left']):>17} {_number(sample['right']):>17} {_number(sample['difference']):>17}")
        if len(shown) < len(self.findings):
            lines.extend([rule, f"另有 {len(self.findings) - len(shown)} 项未展开 / More findings in the full report."])
        lines.extend(["", divider, "精度速览 / PRECISION PROFILES", rule])
        for profile in self.profiles[:12]:
            precision = ", ".join(f"{places}位 / places: {count}" for places, count in profile["decimal_places"].items())
            endings = ", ".join(f"{digit}: {count}" for digit, count in profile["terminal_digits"].items())
            lines.extend(["  " + self._location(profile["series"]), "    小数位数 / Decimal places: " + precision,
                          "    末位数字 / Final digit counts: " + (endings or "无 / None")])
        if len(self.profiles) > 12:
            lines.append(f"  另有 {len(self.profiles) - 12} 条序列见 JSON / More profiles in JSON")
        lines.extend(["", divider, "读取说明 / READING NOTES", rule,
                      "这些模式是复核线索，不是造假判定，也不是造假概率。",
                      "Patterns are review leads, not proof of fabrication or a fabrication probability.",
                      "同一数据可能触发多条相关规则；命中数不代表独立证据数。",
                      "Multiple rules may describe the same pattern; counts are not independent evidence."])
        for note in self.notes:
            lines.extend([rule, "  " + _note_zh(note), "  " + note])
        lines.append(divider)
        return "\n".join(lines)

    def _location(self, label):
        match = re.match(r"^(.*):axis=(\d+)\[(.*)\]$", label)
        if match:
            name, axis, fixed = match.groups()
            if len(self.shapes.get(name, ())) == 2:
                coordinate = int(fixed.split("=")[-1])
                noun = "列 / Column" if axis == "0" else "行 / Row"
                labels = self.dataset_info.get(name, {}).get("column_labels", [])
                title = f" ({labels[coordinate]})" if axis == "0" and coordinate < len(labels) else ""
                return f"{name} | {noun} {coordinate + 1}{title}"
        match = re.match(r"^(.*):sum_axis=1\[\((\d+),\)\]$", label)
        if match:
            name, row = match.groups()
            source = self.dataset_info.get(name, {}).get("source_excel_range", "")
            start = re.match(r"[A-Z]+(\d+):", source)
            origin = f" | 原表行 / Excel row {int(start[1]) + int(row)}" if start else ""
            return f"{name} | 行 / Row {int(row) + 1}{origin}"
        return label

    def write(self, path, *, max_findings=None):
        """Save locally; JSON for .json paths, complete text otherwise."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = self.to_json() if path.suffix.lower() == ".json" else self.summary(max_findings=max_findings)
        path.write_text(body + "\n", encoding="utf-8")

    def __str__(self):
        return self.summary()
