#!/usr/bin/env python3
"""Mako vs Daheng ROI fps — expert-panel figure.

Scale: `figure` = log–log (primary for paper); `figure_linear` = both axes linear.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import xlsxwriter

HERE = Path(__file__).resolve().parent
OUT = HERE / "mako_vs_daheng_roi_fps.xlsx"

COL_MAKO = "#1B4F72"
COL_DAHENG = "#1F8A65"
COL_REF = "#888888"
COL_MUTED = "#555555"

X_LINEAR = (0, 500, 50)  # min, max, major_unit
Y_LINEAR = (0, 6000, 1000)
X_LOG = (1, 1000)
Y_LOG = (100, 10000)

# Chart series: increasing H so polylines do not zigzag.
MAKO = [
    # h, fps, label (empty = no callout)
    (2, 4971, ""),
    (8, 4118, ""),
    (16, 3710, ""),
    (32, 3097, ""),
    (240, 1350, "320×240  1,350 fps"),
    (480, 550, ""),
]
DAHENG = [
    (2, 5780, ""),
    (8, 5076, ""),
    (16, 4386, ""),
    (32, 3436, ""),
    (100, 1792, "296×100  1,792"),
    (200, 1053, "200×200  1,053"),
    (240, 903, "320×240  903 fps"),
    (480, 488, ""),
]
# Table: decreasing H (paragraph order).
TABLE = [
    # roi, w, h, mako or None, daheng, note
    ("640×480", 640, 480, 550, 488, "Mako full sensor; Daheng crop of 1440×1080"),
    ("320×240", 320, 240, 1350, 903, "Manuscript Mako point (datasheet 1,350; lab notes 1,359)"),
    ("200×200", 200, 200, None, 1053, "Not in Mako Table 7. Largest Daheng ROI measured at ≥1,000 fps"),
    ("296×100", 296, 100, None, 1792, "Nearest valid MER2 ROI to 300×100 (Width increment = 8)"),
    ("640×32", 640, 32, 3097, 3436, "Matched datasheet ROI"),
    ("640×16", 640, 16, 3710, 4386, "Matched datasheet ROI"),
    ("640×8", 640, 8, 4118, 5076, "Matched datasheet ROI"),
    ("16×2", 16, 2, 4971, 5780, "Matched datasheet ROI; readout floor / FOT intercept"),
]


def pct(daheng: float, mako: float | None) -> float | None:
    if mako is None:
        return None
    return (daheng - mako) / mako


def _ref_ranges(scale: str) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """Return (h_1k_lo, h_1k_hi), (fps_1k_lo, fps_1k_hi), (h_cross, y_lo, y_hi)."""
    if scale == "log":
        return (1, 1000), (1000, 1000), (50, 100, 10000)
    return (0, 500), (1000, 1000), (50, 0, 6000)


def _make_chart(
    wb: xlsxwriter.Workbook,
    wd_name: str,
    scale: str,
    y_range: tuple[int, int, int] | None = None,
) -> Any:
    """Build scatter chart; y_range overrides Y limits for zoom inset."""
    wd = wb.get_worksheet_by_name(wd_name)
    if wd is None:
        raise RuntimeError(f"missing worksheet {wd_name}")

    mako_labels = [{"delete": True} if not lab else {"value": lab} for _h, _fps, lab in MAKO]
    daheng_labels = [{"delete": True} if not lab else {"value": lab} for _h, _fps, lab in DAHENG]

    daheng_points = []
    for i in range(len(DAHENG)):
        if i in (4, 5):
            daheng_points.append(
                {
                    "marker": {
                        "type": "triangle",
                        "size": 11,
                        "border": {"color": COL_DAHENG, "width": 1.25},
                        "fill": {"none": True},
                    }
                }
            )
        else:
            daheng_points.append(
                {
                    "marker": {
                        "type": "square",
                        "size": 8,
                        "border": {"color": COL_DAHENG},
                        "fill": {"color": COL_DAHENG},
                    }
                }
            )

    ref_h_col = 4 if scale == "linear" else 8
    ref_fps_col = 5 if scale == "linear" else 9
    ref_x_col = 6 if scale == "linear" else 10
    ref_y_col = 7 if scale == "linear" else 11

    chart = wb.add_chart({"type": "scatter", "subtype": "straight_with_markers"})
    chart.add_series(
        {
            "name": "1,000 fps requirement",
            "categories": [wd_name, 1, ref_h_col, 2, ref_h_col],
            "values": [wd_name, 1, ref_fps_col, 2, ref_fps_col],
            "line": {"color": COL_REF, "width": 1.25, "dash_type": "dash"},
            "marker": {"type": "none"},
        }
    )
    chart.add_series(
        {
            "name": "Crossover (~50 lines)",
            "categories": [wd_name, 1, ref_x_col, 2, ref_x_col],
            "values": [wd_name, 1, ref_y_col, 2, ref_y_col],
            "line": {"color": "#BBBBBB", "width": 1.25, "dash_type": "dash"},
            "marker": {"type": "none"},
        }
    )
    chart.add_series(
        {
            "name": "Mako U-029B (datasheet)",
            "categories": [wd_name, 1, 0, len(MAKO), 0],
            "values": [wd_name, 1, 1, len(MAKO), 1],
            "line": {"color": COL_MAKO, "width": 2.25},
            "marker": {
                "type": "circle",
                "size": 9,
                "border": {"color": COL_MAKO},
                "fill": {"color": COL_MAKO},
            },
            "data_labels": {
                "custom_labels": mako_labels,
                "font": {"size": 8, "color": COL_MAKO, "bold": True},
                "position": "left",
            },
        }
    )
    chart.add_series(
        {
            "name": "Daheng MER2 (measured)",
            "categories": [wd_name, 1, 2, len(DAHENG), 2],
            "values": [wd_name, 1, 3, len(DAHENG), 3],
            "line": {"color": COL_DAHENG, "width": 2.25},
            "marker": {
                "type": "square",
                "size": 8,
                "border": {"color": COL_DAHENG},
                "fill": {"color": COL_DAHENG},
            },
            "points": daheng_points,
            "data_labels": {
                "custom_labels": daheng_labels,
                "font": {"size": 8, "color": COL_DAHENG, "bold": True},
                "position": "right",
            },
        }
    )

    axis_base = {
        "major_tick_mark": "outside",
        "minor_tick_mark": "none",
        "num_format": "#,##0",
        "name_font": {"size": 10, "color": COL_MUTED},
        "num_font": {"size": 9},
        "major_gridlines": {"visible": True, "line": {"color": "#DDDDDD"}},
        "line": {"color": "#AAAAAA"},
    }
    if scale == "log":
        x_min, x_max = X_LOG
        y_min, y_max = Y_LOG
        y_major = None
        x_major = None
        axis_base["log_base"] = 10
    else:
        x_min, x_max, x_major = X_LINEAR
        if y_range:
            y_min, y_max, y_major = y_range
        else:
            y_min, y_max, y_major = Y_LINEAR

    x_opts = {**axis_base, "name": "ROI height, H (lines)", "min": x_min, "max": x_max}
    y_opts = {**axis_base, "name": "Frame rate (fps)", "min": y_min, "max": y_max}
    if scale == "linear":
        x_opts["major_unit"] = x_major
        y_opts["major_unit"] = y_major

    chart.set_x_axis(x_opts)
    chart.set_y_axis(y_opts)
    chart.set_legend({"position": "top", "font": {"size": 9}})
    chart.set_chartarea({"border": {"none": True}})
    chart.set_plotarea({"border": {"none": True}, "fill": {"color": "#FCFCFC"}})
    chart.set_size({"width": 920, "height": 520})
    return chart


def _write_data_sheet(wb: xlsxwriter.Workbook, name: str = "data") -> None:
    wd = wb.add_worksheet(name)
    wd.write_row(
        0,
        0,
        [
            "H_mako",
            "fps_mako",
            "H_daheng",
            "fps_daheng",
            "H_1k_lin",
            "fps_1k_lin",
            "H_x_lin",
            "fps_x_lin",
            "H_1k_log",
            "fps_1k_log",
            "H_x_log",
            "fps_x_log",
        ],
    )
    for i, (h, fps, _lab) in enumerate(MAKO, 1):
        wd.write_number(i, 0, h)
        wd.write_number(i, 1, fps)
    for i, (h, fps, _lab) in enumerate(DAHENG, 1):
        wd.write_number(i, 2, h)
        wd.write_number(i, 3, fps)
    # linear reference lines (cols E–H)
    (h1_lo, h1_hi), (fps1, fps2), (hx, y_lo, y_hi) = _ref_ranges("linear")
    wd.write_number(1, 4, h1_lo)
    wd.write_number(2, 4, h1_hi)
    wd.write_number(1, 5, fps1)
    wd.write_number(2, 5, fps2)
    wd.write_number(1, 6, hx)
    wd.write_number(2, 6, hx)
    wd.write_number(1, 7, y_lo)
    wd.write_number(2, 7, y_hi)
    # log reference lines (cols I–L)
    (h1_lo, h1_hi), (fps1, fps2), (hx, y_lo, y_hi) = _ref_ranges("log")
    wd.write_number(1, 8, h1_lo)
    wd.write_number(2, 8, h1_hi)
    wd.write_number(1, 9, fps1)
    wd.write_number(2, 9, fps2)
    wd.write_number(1, 10, hx)
    wd.write_number(2, 10, hx)
    wd.write_number(1, 11, y_lo)
    wd.write_number(2, 11, y_hi)


def build(out: Path = OUT) -> Path:
    wb = xlsxwriter.Workbook(str(out))

    fmt_title = wb.add_format({"bold": True, "font_size": 14, "font_color": "#222222"})
    fmt_h = wb.add_format(
        {
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": "#333333",
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
        }
    )
    fmt_c = wb.add_format({"align": "center", "valign": "vcenter"})
    fmt_int = wb.add_format({"num_format": "#,##0", "align": "center"})
    fmt_pct = wb.add_format({"num_format": "0.0%", "align": "center"})
    fmt_mako = wb.add_format(
        {"num_format": "#,##0", "align": "center", "bold": True, "font_color": COL_MAKO, "bg_color": "#EAF2F8"}
    )
    fmt_daheng = wb.add_format(
        {"num_format": "#,##0", "align": "center", "bold": True, "font_color": COL_DAHENG, "bg_color": "#E8F6F3"}
    )
    fmt_na = wb.add_format({"align": "center", "italic": True, "font_color": "#888888"})
    fmt_note = wb.add_format({"font_size": 9, "text_wrap": True, "valign": "top", "font_color": "#333333"})
    fmt_cap = wb.add_format({"font_size": 10, "text_wrap": True, "valign": "top", "font_color": "#222222"})
    fmt_src = wb.add_format({"font_size": 8, "italic": True, "font_color": "#888888", "text_wrap": True})
    fmt_log_note = wb.add_format(
        {"font_size": 8, "italic": True, "font_color": "#888888", "align": "left", "valign": "top"}
    )

    _write_data_sheet(wb, "data")

    cap_body = (
        "X is numeric row count H, not an equally spaced ROI label: fps is limited by height "
        "(frame period ≈ overhead + H × row time), not by pixel count. "
        "At 320×240 (H = 240), the 1,000 fps requirement (horizontal dash) is met by the Mako (1,350 fps, datasheet) "
        "but not by the MER2 (903 fps, measured). "
        "Open triangles are Daheng-only sizes (no Mako pair): 200×200 is the largest MER2 ROI measured at ≥1,000 fps (1,053 fps); "
        "300×100 is invalid (Width step = 8)—use 296×100 (1,792 fps). "
        "Vertical dash (~50 lines) marks the crossover: Mako is faster at large H (faster row time), Daheng at small H (lower per-frame overhead). "
        "Mako: Allied Vision technical manual Table 7. Daheng: SN FDQ23120254, 20 µs, free-run, C++ SDK fps."
    )

    # ----- figure (log–log) — primary for manuscript -----
    ws = wb.add_worksheet("figure")
    ws.hide_gridlines(2)
    ws.set_tab_color(COL_DAHENG)
    ws.set_column(0, 12, 11)
    ws.merge_range(0, 0, 0, 11, "Figure — Mako U-029B vs Daheng MER2-160", fmt_title)
    ws.insert_chart("A2", _make_chart(wb, "data", "log"), {"x_offset": 8, "y_offset": 8})
    ws.write("A27", "Log scale", fmt_log_note)
    ws.write("B27", "(both axes)", fmt_log_note)
    ws.merge_range(
        29,
        0,
        32,
        11,
        "Frame rate versus ROI height for Allied Vision Mako U-029B and Daheng MER2-160. "
        "Both axes use logarithmic spacing (decade ticks; see “Log scale” note on the figure). "
        + cap_body,
        fmt_cap,
    )
    for r in range(29, 33):
        ws.set_row(r, 22)

    # ----- figure_linear (both axes linear, full range) -----
    wl = wb.add_worksheet("figure_linear")
    wl.hide_gridlines(2)
    wl.set_tab_color(COL_MAKO)
    wl.set_column(0, 12, 11)
    wl.merge_range(0, 0, 0, 11, "Figure — linear axes (full range)", fmt_title)
    wl.insert_chart("A2", _make_chart(wb, "data", "linear"), {"x_offset": 8, "y_offset": 8})
    wl.merge_range(
        29,
        0,
        32,
        11,
        "Same data as sheet ‘figure’, with both axes linear (H: 0–500 lines, ticks every 50; fps: 0–6,000, ticks every 1,000). "
        + cap_body,
        fmt_cap,
    )
    for r in range(29, 33):
        wl.set_row(r, 22)

    # ----- table: decreasing H -----
    wt = wb.add_worksheet("table")
    wt.hide_gridlines(2)
    wt.merge_range(0, 0, 0, 7, "Data for the figure (rows ordered by decreasing height)", fmt_title)
    headers = ["ROI", "Width", "Height H", "Pixels", "Mako U-029B (fps)", "Daheng MER2 (fps)", "% vs Mako", "Notes"]
    for c, h in enumerate(headers):
        wt.write(2, c, h, fmt_h)
    wt.set_row(2, 26)
    for i, (roi, w, h, mako, daheng, note) in enumerate(TABLE, 3):
        wt.write(i, 0, roi, fmt_c)
        wt.write_number(i, 1, w, fmt_int)
        wt.write_number(i, 2, h, fmt_int)
        wt.write_number(i, 3, w * h, fmt_int)
        if mako is None:
            wt.write(i, 4, "not reported", fmt_na)
            wt.write(i, 6, "—", fmt_na)
        else:
            wt.write_number(i, 4, mako, fmt_mako)
            wt.write_number(i, 6, pct(daheng, mako), fmt_pct)
        wt.write_number(i, 5, daheng, fmt_daheng)
        wt.write(i, 7, note, fmt_note)
        wt.set_row(i, 26)
    wt.set_column(0, 0, 12)
    wt.set_column(1, 3, 12)
    wt.set_column(4, 6, 20)
    wt.set_column(7, 7, 64)
    wt.merge_range(
        12,
        0,
        14,
        7,
        "Panel decision: do not use clustered columns on a linear fps axis (hides −11% at 640×480 next to 5,000 fps bars, "
        "and equal-spaced ROI labels lie about distance in H). Do not split into two Y scales. "
        "Chart data on sheet ‘data’ are sorted by increasing H so the polylines follow readout physics.",
        fmt_src,
    )

    wb.close()
    return out


if __name__ == "__main__":
    print(build())
