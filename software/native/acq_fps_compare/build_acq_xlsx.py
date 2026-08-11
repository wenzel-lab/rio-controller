#!/usr/bin/env python3
"""Build a clean, PowerPoint-ready Excel workbook: Python vs C++ Daheng Acq.FPS.

Uses xlsxwriter (more reliable chart axis labels / legend layout than openpyxl).

Reads paired CSVs, keeps count_fps for t_s >= 2 s.

Usage:
  python3 build_acq_xlsx.py
  python3 build_acq_xlsx.py --out acq_fps_python_vs_cpp.xlsx
"""

from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path

import xlsxwriter

HERE = Path(__file__).resolve().parent
CPP_CSV = HERE / "acq_cpp_200x200_20us.csv"
PY_CSV = HERE / "acq_python_200x200_20us.csv"
DEFAULT_OUT = HERE / "acq_fps_python_vs_cpp.xlsx"

T_MIN = 2.0
Y_MIN = 800
Y_MAX = 1100

# Semantic colors
COL_CPP = "#1F8A65"
COL_PY = "#C06028"
COL_SDK = "#2E79B5"
COL_GAP = "#856404"
FILL_CPP = "#E6F4EE"
FILL_PY = "#F8EDE4"
FILL_SDK = "#E8F1F8"
FILL_GAP = "#FFF3CD"


def load_count_fps(path: Path) -> list[tuple[float, float, float]]:
    rows: list[tuple[float, float, float]] = []
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            t = float(r["t_s"])
            c = float(r["count_fps"])
            sdk = float(r["sdk_fps"])
            if t >= T_MIN and c > 0:
                rows.append((t, c, sdk))
    return rows


def nearest(rows: list[tuple[float, float, float]], t: float) -> tuple[float, float]:
    best = min(rows, key=lambda x: abs(x[0] - t))
    return best[1], best[2]


def align_series(
    cpp: list[tuple[float, float, float]],
    py: list[tuple[float, float, float]],
) -> list[tuple[float, float, float, float]]:
    out: list[tuple[float, float, float, float]] = []
    for t, c_cpp, sdk in cpp:
        c_py, _ = nearest(py, t)
        out.append((t, c_cpp, c_py, sdk))
    return out


def build(out: Path) -> Path:
    cpp = load_count_fps(CPP_CSV)
    py = load_count_fps(PY_CSV)
    if not cpp or not py:
        raise SystemExit("No steady-state rows (t>=2, count_fps>0) in CSVs")

    aligned = align_series(cpp, py)
    n = len(aligned)
    cpp_vals = [r[1] for r in aligned]
    py_vals = [r[2] for r in aligned]
    sdk = aligned[0][3]
    cpp_mean = statistics.fmean(cpp_vals)
    py_mean = statistics.fmean(py_vals)
    gap = cpp_mean - py_mean
    gap_pct = (gap / sdk) * 100.0

    wb = xlsxwriter.Workbook(str(out))

    # --- formats ---
    fmt_title = wb.add_format({"bold": True, "font_size": 16, "font_color": "#222222"})
    fmt_sub = wb.add_format({"font_size": 10, "font_color": "#666666"})
    fmt_h = wb.add_format(
        {"bold": True, "font_color": "#FFFFFF", "bg_color": "#444444", "align": "center"}
    )
    fmt_num = wb.add_format({"num_format": "0.00", "align": "center"})
    fmt_t = wb.add_format({"num_format": "0.0", "align": "center"})

    def kpi_fmt(fg: str, bg: str, size: int = 14) -> object:
        return wb.add_format(
            {
                "bold": True,
                "font_size": size,
                "font_color": fg,
                "bg_color": bg,
                "align": "center",
                "valign": "vcenter",
                "border": 1,
                "border_color": "#CCCCCC",
            }
        )

    fmt_lab_cpp = wb.add_format(
        {"bold": True, "font_color": COL_CPP, "align": "center", "valign": "vcenter"}
    )
    fmt_lab_py = wb.add_format(
        {"bold": True, "font_color": COL_PY, "align": "center", "valign": "vcenter"}
    )
    fmt_lab_sdk = wb.add_format(
        {"bold": True, "font_color": COL_SDK, "align": "center", "valign": "vcenter"}
    )
    fmt_lab_gap = wb.add_format(
        {"bold": True, "font_color": COL_GAP, "align": "center", "valign": "vcenter"}
    )
    fmt_val_cpp = kpi_fmt(COL_CPP, FILL_CPP)
    fmt_val_py = kpi_fmt(COL_PY, FILL_PY)
    fmt_val_sdk = kpi_fmt(COL_SDK, FILL_SDK)
    fmt_val_gap = kpi_fmt(COL_GAP, FILL_GAP, size=16)
    fmt_verdict = wb.add_format(
        {"bold": True, "font_size": 12, "font_color": COL_CPP, "align": "left"}
    )
    fmt_gap_box = wb.add_format(
        {
            "bold": True,
            "font_size": 18,
            "font_color": COL_GAP,
            "bg_color": FILL_GAP,
            "align": "center",
            "valign": "vcenter",
            "border": 2,
            "border_color": COL_GAP,
        }
    )
    fmt_note = wb.add_format({"font_size": 10, "font_color": "#444444", "valign": "vcenter"})
    fmt_src = wb.add_format({"font_size": 9, "font_color": "#888888"})
    fmt_tag = wb.add_format({"bold": True, "font_size": 10, "font_color": "#666666"})

    # ========== sheet: data ==========
    ws_data = wb.add_worksheet("data")
    headers = ["t_s", "C++ (native)", "Python (gxipy)", "SDK (device)"]
    for c, h in enumerate(headers):
        ws_data.write(0, c, h, fmt_h)
    for i, (t, c_cpp, c_py, s) in enumerate(aligned):
        r = i + 1
        ws_data.write_number(r, 0, round(t, 3), fmt_t)
        ws_data.write_number(r, 1, round(c_cpp, 2), fmt_num)
        ws_data.write_number(r, 2, round(c_py, 2), fmt_num)
        ws_data.write_number(r, 3, round(s, 2), fmt_num)
    ws_data.write(0, 5, "Notes")
    ws_data.write(
        1,
        5,
        "Metric is count_fps. Do not use Python acq_fps (~2k) — catch-up artefact.",
    )
    ws_data.set_column(0, 0, 10)
    ws_data.set_column(1, 3, 16)
    ws_data.set_column(5, 5, 70)
    last_data_row = n  # 1-based last data row index in Excel terms = n (0-header)

    # ========== sheet: chart (PPT) ==========
    ws = wb.add_worksheet("chart")
    ws.hide_gridlines(2)
    ws.set_tab_color(COL_CPP)

    ws.merge_range(
        0,
        0,
        0,
        9,
        f"Host Acq.FPS — C++ matches SDK; Python lags ~{gap:.0f} fps",
        fmt_title,
    )
    ws.merge_range(
        1,
        0,
        1,
        9,
        "MER2 200×200 @ 20 µs · count_fps · t ≥ 2 s · SN FDQ23120254",
        fmt_sub,
    )

    # KPI strip
    ws.set_row(3, 30)
    ws.write(3, 0, "C++", fmt_lab_cpp)
    ws.write(3, 1, f"{cpp_mean:.0f} fps", fmt_val_cpp)
    ws.write(3, 2, "Python", fmt_lab_py)
    ws.write(3, 3, f"{py_mean:.0f} fps", fmt_val_py)
    ws.write(3, 4, "Δ gap", fmt_lab_gap)
    ws.write(3, 5, f"≈ {gap:.0f} fps", fmt_val_gap)
    ws.write(3, 6, "SDK", fmt_lab_sdk)
    ws.write(3, 7, f"{sdk:.0f}", fmt_val_sdk)

    ws.merge_range(
        4,
        0,
        4,
        9,
        f"Takeaway: C++ sits on the device SDK band; Python is ~{gap:.0f} fps (~{gap_pct:.0f}%) lower",
        fmt_tag,
    )

    # Line chart — legend RIGHT (no overlap with axis titles), Y ticks visible
    chart = wb.add_chart({"type": "line"})
    chart.add_series(
        {
            "name": "C++ (native)",
            "categories": ["data", 1, 0, last_data_row, 0],
            "values": ["data", 1, 1, last_data_row, 1],
            "line": {"color": COL_CPP, "width": 2.5},
            "marker": {
                "type": "circle",
                "size": 5,
                "border": {"color": COL_CPP},
                "fill": {"color": COL_CPP},
            },
        }
    )
    chart.add_series(
        {
            "name": "Python (gxipy)",
            "categories": ["data", 1, 0, last_data_row, 0],
            "values": ["data", 1, 2, last_data_row, 2],
            "line": {"color": COL_PY, "width": 2.5},
            "marker": {
                "type": "circle",
                "size": 5,
                "border": {"color": COL_PY},
                "fill": {"color": COL_PY},
            },
        }
    )
    chart.add_series(
        {
            "name": "SDK (device)",
            "categories": ["data", 1, 0, last_data_row, 0],
            "values": ["data", 1, 3, last_data_row, 3],
            "line": {"color": COL_SDK, "width": 1.75, "dash_type": "dash"},
            "marker": {"type": "none"},
        }
    )

    chart.set_title({"none": True})
    chart.set_legend({"position": "right", "font": {"size": 10}})
    chart.set_style(10)

    chart.set_y_axis(
        {
            "name": "Acq.FPS",
            "name_font": {"size": 11, "bold": True},
            "num_font": {"size": 10},
            "min": Y_MIN,
            "max": Y_MAX,
            "major_unit": 100,
            "minor_unit": 50,
            "major_gridlines": {"visible": True, "line": {"color": "#DDDDDD", "width": 0.75}},
            "line": {"color": "#888888"},
            "num_format": "0",
        }
    )
    chart.set_x_axis(
        {
            "name": "Time (s)",
            "name_font": {"size": 11, "bold": True},
            "num_font": {"size": 10},
            "major_gridlines": {"visible": False},
            "line": {"color": "#888888"},
            "label_position": "low",
            # skip labels so they don't crowd
            "interval_unit": 4,
            "num_format": "0",
        }
    )

    chart.set_size({"width": 860, "height": 460})
    chart.set_plotarea({"border": {"none": True}, "fill": {"color": "#FAFAFA"}})
    chart.set_chartarea({"border": {"color": "#CCCCCC", "width": 0.75}, "fill": {"color": "#FFFFFF"}})

    ws.insert_chart("A7", chart)

    # Gap callout under chart (always visible, no overlap with legend)
    ws.set_row(30, 28)
    ws.set_row(31, 28)
    ws.merge_range(30, 0, 31, 1, f"Δ ≈ {gap:.0f} fps", fmt_gap_box)
    ws.merge_range(
        30,
        2,
        31,
        9,
        "C++ band ≈ SDK (~1053–1055). Python band ≈ 840. Y-axis zoomed 800–1100 so the gap reads clearly.",
        fmt_note,
    )

    ws.write(33, 0, "Source", fmt_src)
    ws.merge_range(
        33,
        1,
        33,
        9,
        "acq_cpp_200x200_20us.csv · acq_python_200x200_20us.csv · regenerate: python3 build_acq_xlsx.py",
        fmt_src,
    )

    ws.set_column(0, 0, 10)
    ws.set_column(1, 1, 12)
    ws.set_column(2, 3, 11)
    ws.set_column(4, 5, 12)
    ws.set_column(6, 7, 10)
    ws.set_column(8, 9, 12)

    # ========== sheet: summary ==========
    ws_s = wb.add_worksheet("summary")
    ws_s.write(0, 0, "Acq.FPS comparison — callouts", fmt_title)
    ws_s.write(1, 0, "MER2 200×200 @ 20 µs · count_fps · t ≥ 2 s", fmt_sub)

    for c, h in enumerate(["Backend", "Metric", "Value", "Tag"]):
        ws_s.write(3, c, h, fmt_h)

    rows = [
        ("C++ (native)", "mean count_fps", f"{cpp_mean:.1f}", "matches SDK", FILL_CPP, COL_CPP),
        ("Python (gxipy)", "mean count_fps", f"{py_mean:.1f}", "below SDK", FILL_PY, COL_PY),
        ("Device SDK", "CurrentAcquisitionFrameRate", f"{sdk:.2f}", "reference", FILL_SDK, COL_SDK),
        (
            "Gap C++ − Python",
            "Δ fps (≈ % of SDK)",
            f"{gap:.0f}  (~{gap_pct:.0f}%)",
            "MAIN TAKEAWAY",
            FILL_GAP,
            COL_GAP,
        ),
    ]
    for i, (backend, metric, value, tag, bg, fg) in enumerate(rows):
        r = 4 + i
        cell = wb.add_format(
            {
                "bold": True,
                "font_color": fg,
                "bg_color": bg,
                "border": 1,
                "border_color": "#CCCCCC",
                "valign": "vcenter",
            }
        )
        cell_v = wb.add_format(
            {
                "bold": True,
                "font_size": 14 if i == 3 else 12,
                "font_color": fg,
                "bg_color": bg,
                "border": 1,
                "border_color": "#CCCCCC",
                "align": "center",
                "valign": "vcenter",
            }
        )
        ws_s.write(r, 0, backend, cell)
        ws_s.write(r, 1, metric, cell)
        ws_s.write(r, 2, value, cell_v)
        ws_s.write(r, 3, tag, cell)

    ws_s.write(9, 0, "Verdict", fmt_lab_cpp)
    ws_s.merge_range(
        9,
        1,
        9,
        3,
        f"C++ matches device SDK Acq.FPS; Python lags ~{gap:.0f} fps",
        fmt_verdict,
    )
    ws_s.write(11, 0, "How to paste into PowerPoint", fmt_tag)
    ws_s.merge_range(
        12,
        0,
        13,
        3,
        "Open sheet 'chart' → click the chart → Copy → PowerPoint → Paste (Keep Source Formatting / Excel Chart).",
        fmt_note,
    )
    ws_s.set_column(0, 0, 22)
    ws_s.set_column(1, 1, 32)
    ws_s.set_column(2, 2, 18)
    ws_s.set_column(3, 3, 16)

    # Ensure 'chart' is the first sheet
    wb.worksheets_objs.insert(0, wb.worksheets_objs.pop(wb._worksheets_name_to_index_map["chart"]))

    wb.close()
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    path = build(args.out)
    # also refresh Desktop copy if present
    desk = Path.home() / "Desktop" / path.name
    try:
        desk.write_bytes(path.read_bytes())
    except OSError:
        pass
    print(f"Wrote {path}")
    if desk.exists():
        print(f"Also {desk}")


if __name__ == "__main__":
    main()
