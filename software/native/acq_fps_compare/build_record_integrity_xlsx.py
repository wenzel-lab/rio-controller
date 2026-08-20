#!/usr/bin/env python3
"""Record ROI frame integrity — expert-panel planned figures (English).

Sheets:
  expert_plan   — chart rationale (plan before design)
  summary       — one-page conclusions
  before_after  — pre-fix bug vs post-fix
  tests         — full validation matrix
  chart_data    — series used by charts (do not edit manually)
  figure        — primary figure panels (A–C)
  figure_throughput — Panel D: acq vs save fps parity
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import xlsxwriter

HERE = Path(__file__).resolve().parent
OUT = HERE / "record_frame_integrity_summary.xlsx"

COL_OK = "#1F8A65"
COL_BAD = "#C0392B"
COL_HDR = "#1B4F72"
COL_MAKO = "#1B4F72"
COL_DAHENG = "#1F8A65"
COL_REF = "#888888"
COL_MUTED = "#555555"

# --- Expert panel plan (displayed on sheet) ---
EXPERT_PLAN = [
    ("EXPERT PANEL — Figure planning (Record ROI frame integrity)", ""),
    ("", ""),
    ("Primary claim", "Saved JPEGs are distinct, consecutive acquisition frames (no frame_id gaps)."),
    ("Audience", "Manuscript supplement / lab handoff — must read in <60 s."),
    ("", ""),
    ("Panel", "Chart type", "Content & rationale"),
    (
        "A — Bug vs fix",
        "Clustered columns",
        "Unique frame content (1 vs 50) alongside wall time (16 vs 53 ms). "
        "Shows pre-fix wrote duplicates fast; post-fix matches real ~1 kfps pacing.",
    ),
    (
        "B — frame_id continuity",
        "Scatter + straight line",
        "User UI run: saved index vs GenICam frame_id (82338–82387). "
        "Unit slope = consecutive frames; gold standard for reviewers.",
    ),
    (
        "C — Stress matrix",
        "Columns (log Y) + loss overlay",
        "Frames saved 50→20 000 across ROIs; red series = gaps+dropped+overflow (all 0). "
        "Log scale needed because frame count spans 3 decades.",
    ),
    (
        "D — Throughput parity",
        "Grouped columns",
        "Effective save fps vs acquisition fps per test. Matching heights → pipeline keeps pace.",
    ),
    ("", ""),
    ("Rejected", "Pie chart of pass/fail — trivial (100% pass); no information density."),
    ("Rejected", "Single bar ‘0 drops’ — hides scale of stress tests."),
    ("Rejected", "MD5 hash table — too low-level for main figure (keep in methods text)."),
]

SUMMARY_ROWS = [
    ("Question", "Does Record ROI lose frames under lab conditions?"),
    ("Answer", "No — 0 gaps, 0 dropped, 0 queue overflow in all real tests (Aug 2026)."),
    ("Evidence", "manifest.csv frame_id sequence; UI status ‘no gaps’; disk verification."),
    ("Fix applied", "wait_frame_array + C++ FIFO queue (libdaheng_grabber.so rebuild)."),
    ("User validation", "50/50 @ 200×200, 20 µs — frame_id 82338–82387, ~1 075 fps effective save."),
    ("Stress limit tested", "Up to 20 000 frames @ 104×80 (~2 087 fps) — still zero loss."),
    ("Not tested today", "Strobe-lit frames, hardware trigger, droplet pipeline (planned next)."),
]

TESTS = [
    # label, category, roi, frames, acq_fps, save_fps, fid0, fid1, gaps, dropped, overflow, ms, notes
    (
        "User UI",
        "Manuscript ROI",
        "200×200",
        50,
        1054,
        1075,
        82338,
        82387,
        0,
        0,
        0,
        53,
        "Exposure 20 µs; folder 20260819_163902",
    ),
    (
        "Post-fix verify",
        "Manuscript ROI",
        "200×200",
        50,
        1054,
        1063,
        287,
        336,
        0,
        0,
        0,
        46,
        "Automated script after wait_frame fix",
    ),
    (
        "Stress 10×",
        "Manuscript ROI",
        "200×200",
        500,
        1055,
        1055,
        296,
        795,
        0,
        0,
        0,
        473,
        "",
    ),
    (
        "Stress 100×",
        "Manuscript ROI",
        "200×200",
        5000,
        1055,
        1055,
        268,
        5267,
        0,
        0,
        0,
        4800,
        "~5 s wall time",
    ),
    (
        "Max fps short",
        "Max fps ROI",
        "104×80",
        500,
        2090,
        2090,
        584,
        1083,
        0,
        0,
        0,
        239,
        "MER2 sweep ~2 088 fps @ 104×80",
    ),
    (
        "Max fps 10k",
        "Max fps ROI",
        "104×80",
        10000,
        2087,
        2087,
        585,
        10584,
        0,
        0,
        0,
        4800,
        "",
    ),
    (
        "Max fps 20k",
        "Max fps ROI",
        "104×80",
        20000,
        2087,
        2087,
        589,
        20588,
        0,
        0,
        0,
        9600,
        "Upper bound tested on host",
    ),
    (
        "Full sensor",
        "Full FOV",
        "1440×1080",
        500,
        227,
        227,
        64,
        563,
        0,
        0,
        0,
        876,
        "Large JPEG; low fps",
    ),
]

BEFORE_AFTER = [
    ("Pre-fix (bug)", 50, 1, 16, "50 identical JPEGs (1 MD5); ~16 ms total"),
    ("Post-fix (script)", 50, 50, 46, "50 unique frame_ids; ~46 ms"),
    ("User UI (today)", 50, 50, 53, "frame_id 82338–82387; manifest.csv"),
]

USER_FID_START = 82338
USER_FID_N = 50


def _hdr(wb: xlsxwriter.Workbook) -> Any:
    return wb.add_format({"bold": True, "bg_color": "#D6EAF8", "border": 1})


def _cell(wb: xlsxwriter.Workbook) -> Any:
    return wb.add_format({"border": 1, "text_wrap": True, "valign": "top"})


def main() -> None:
    wb = xlsxwriter.Workbook(str(OUT))
    fmt_title = wb.add_format({"bold": True, "font_size": 14, "font_color": COL_HDR})
    fmt_hdr = _hdr(wb)
    fmt_cell = _cell(wb)
    fmt_ok = wb.add_format({"border": 1, "font_color": COL_OK, "bold": True})
    fmt_bad = wb.add_format({"border": 1, "font_color": COL_BAD})
    fmt_num = wb.add_format({"border": 1, "num_format": "#,##0"})
    fmt_plan_hdr = wb.add_format({"bold": True, "bg_color": "#E8DAEF", "border": 1})

    # ----- expert_plan -----
    ep = wb.add_worksheet("expert_plan")
    ep.set_column("A:A", 22)
    ep.set_column("B:B", 28)
    ep.set_column("C:C", 72)
    ep.write(0, 0, EXPERT_PLAN[0][0], fmt_title)
    for r, row in enumerate(EXPERT_PLAN[2:], start=2):
        if len(row) == 2:
            ep.write(r, 0, row[0], fmt_plan_hdr if row[0] in ("Panel", "Rejected") else fmt_cell)
            if row[1]:
                ep.write(r, 1, row[1], fmt_cell)
        elif len(row) == 3:
            ep.write(r, 0, row[0], fmt_cell)
            ep.write(r, 1, row[1], fmt_cell)
            ep.write(r, 2, row[2], fmt_cell)

    # ----- summary -----
    sm = wb.add_worksheet("summary")
    sm.set_column("A:A", 22)
    sm.set_column("B:B", 70)
    sm.write(0, 0, "Record ROI — frame integrity summary", fmt_title)
    sm.write(1, 0, "Daheng MER2 · RIO_DAHENG_CPP · Aug 2026", fmt_cell)
    for r, (k, v) in enumerate(SUMMARY_ROWS, start=3):
        sm.write(r, 0, k, fmt_hdr)
        f = fmt_ok if k == "Answer" else fmt_cell
        sm.write(r, 1, v, f)

    # ----- before_after -----
    ba = wb.add_worksheet("before_after")
    ba_h = ["Condition", "Files written", "Unique frames", "Wall time (ms)", "Notes"]
    ba.set_column("E:E", 44)
    for c, h in enumerate(ba_h):
        ba.write(0, c, h, fmt_hdr)
    for r, row in enumerate(BEFORE_AFTER, start=1):
        for c, val in enumerate(row):
            f = fmt_bad if r == 1 and c == 2 else (fmt_ok if r == 3 else fmt_cell)
            ba.write(r, c, val, f if c != 2 or r in (1, 3) else fmt_num)

    # ----- tests -----
    td = wb.add_worksheet("tests")
    t_headers = [
        "Test",
        "Category",
        "ROI",
        "Frames",
        "Acq fps",
        "Save fps",
        "frame_id first",
        "frame_id last",
        "Gaps",
        "Dropped",
        "Overflow",
        "Wall ms",
        "Notes",
    ]
    for c, h in enumerate(t_headers):
        td.write(0, c, h, fmt_hdr)
    td.set_column("M:M", 36)
    for r, row in enumerate(TESTS, start=1):
        for c, val in enumerate(row):
            td.write(r, c, val, fmt_num if c in (3, 4, 5, 6, 7, 8, 9, 10, 11) else fmt_cell)

    n = len(TESTS)

    # ----- chart_data -----
    cd = wb.add_worksheet("chart_data")
    cd.hide()
    # Panel A: before/after (cols 0-3)
    cd.write(0, 0, "Condition", fmt_hdr)
    cd.write(0, 1, "Unique frames", fmt_hdr)
    cd.write(0, 2, "Wall ms", fmt_hdr)
    cd.write(0, 3, "Files", fmt_hdr)
    for r, row in enumerate(BEFORE_AFTER, start=1):
        cd.write(r, 0, row[0])
        cd.write(r, 1, row[2])
        cd.write(r, 2, row[3])
        cd.write(r, 3, row[1])

    # Panel B: frame_id continuity (cols 5-6)
    cd.write(0, 5, "Index", fmt_hdr)
    cd.write(0, 6, "frame_id", fmt_hdr)
    for i in range(USER_FID_N):
        cd.write(i + 1, 5, i)
        cd.write(i + 1, 6, USER_FID_START + i)

    # Panel C/D: from tests (cols 8+)
    cd.write(0, 8, "Short label", fmt_hdr)
    cd.write(0, 9, "Frames", fmt_hdr)
    cd.write(0, 10, "Total loss", fmt_hdr)
    cd.write(0, 11, "Acq fps", fmt_hdr)
    cd.write(0, 12, "Save fps", fmt_hdr)
    short = ["UI 50", "Fix 50", "200² 500", "200² 5k", "104×80 500", "104×80 10k", "104×80 20k", "Full 500"]
    for r, (label, *rest) in enumerate(TESTS, start=1):
        gaps, drop, ov = rest[8], rest[9], rest[10]
        loss = gaps + drop + ov
        cd.write(r, 8, short[r - 1])
        cd.write(r, 9, rest[3])  # frames
        cd.write(r, 10, loss)
        cd.write(r, 11, rest[4])  # acq
        cd.write(r, 12, rest[5])  # save

    # ----- figure -----
    wf = wb.add_worksheet("figure")
    wf.set_column("A:A", 100)
    wf.write(
        0,
        0,
        "Figure — Record ROI frame integrity (expert panel layout)",
        fmt_title,
    )
    wf.write(
        1,
        0,
        "Panel A: bug vs fix  ·  Panel B: frame_id continuity (user run)  ·  Panel C: stress scale, zero loss",
        fmt_cell,
    )

    # Panel A
    ch_a = wb.add_chart({"type": "column"})
    ch_a.add_series(
        {
            "name": "Unique frames captured",
            "categories": ["chart_data", 1, 0, 3, 0],
            "values": ["chart_data", 1, 1, 3, 1],
            "fill": {"color": COL_DAHENG},
            "data_labels": {"value": True},
        }
    )
    ch_a.add_series(
        {
            "name": "Wall time (ms)",
            "categories": ["chart_data", 1, 0, 3, 0],
            "values": ["chart_data", 1, 2, 3, 2],
            "fill": {"color": COL_BAD},
            "data_labels": {"value": True, "num_format": "#,##0"},
            "y2_axis": True,
        }
    )
    ch_a.set_title({"name": "A — Pre-fix duplicated frames vs post-fix real capture"})
    ch_a.set_y_axis({"name": "Unique frames", "min": 0, "max": 55})
    ch_a.set_y2_axis({"name": "Wall time (ms)", "min": 0, "max": 60})
    ch_a.set_x_axis({"name": ""})
    ch_a.set_legend({"position": "bottom"})
    ch_a.set_size({"width": 520, "height": 340})
    wf.insert_chart("A3", ch_a)

    # Panel B
    ch_b = wb.add_chart({"type": "scatter", "subtype": "straight_with_markers"})
    ch_b.add_series(
        {
            "name": "User UI recording",
            "categories": ["chart_data", 1, 5, USER_FID_N, 5],
            "values": ["chart_data", 1, 6, USER_FID_N, 6],
            "line": {"color": COL_HDR, "width": 1.5},
            "marker": {"type": "circle", "size": 5, "fill": {"color": COL_HDR}},
        }
    )
    ch_b.set_title({"name": "B — frame_id vs save index (consecutive = slope 1)"})
    ch_b.set_x_axis(
        {
            "name": "Saved frame index",
            "min": 0,
            "max": 49,
            "major_unit": 10,
        }
    )
    ch_b.set_y_axis(
        {
            "name": "GenICam frame_id",
            "min": 82335,
            "max": 82390,
            "num_format": "#,##0",
        }
    )
    ch_b.set_legend({"none": True})
    ch_b.set_size({"width": 520, "height": 340})
    wf.insert_chart("H3", ch_b)

    # Panel C — log scale frames + loss
    ch_c = wb.add_chart({"type": "column"})
    ch_c.add_series(
        {
            "name": "Frames saved",
            "categories": ["chart_data", 1, 8, n, 8],
            "values": ["chart_data", 1, 9, n, 9],
            "fill": {"color": COL_HDR},
            "data_labels": {"value": True, "num_format": "#,##0"},
        }
    )
    ch_c.add_series(
        {
            "name": "Total loss (gaps+dropped+overflow)",
            "categories": ["chart_data", 1, 8, n, 8],
            "values": ["chart_data", 1, 10, n, 10],
            "fill": {"color": COL_BAD},
            "data_labels": {"value": True},
            "y2_axis": True,
        }
    )
    ch_c.set_title({"name": "C — Stress tests: 50 to 20 000 frames (all loss = 0)"})
    ch_c.set_y_axis({"name": "Frames saved", "log_base": 10, "min": 40, "max": 30000})
    ch_c.set_y2_axis({"name": "Frames lost", "min": 0, "max": 5})
    ch_c.set_x_axis({"name": "Test"})
    ch_c.set_legend({"position": "bottom"})
    ch_c.set_size({"width": 1060, "height": 380})
    wf.insert_chart("A22", ch_c)

    wf.write(
        "A42",
        "Caption: Real lab tests only (no artificial save delay). manifest.csv logs frame_id and gap_before per file.",
        fmt_cell,
    )

    # ----- figure_throughput -----
    ft = wb.add_worksheet("figure_throughput")
    ft.write(0, 0, "Panel D — Acquisition vs save throughput", fmt_title)
    ch_d = wb.add_chart({"type": "column"})
    ch_d.add_series(
        {
            "name": "Acquisition fps",
            "categories": ["chart_data", 1, 8, n, 8],
            "values": ["chart_data", 1, 11, n, 11],
            "fill": {"color": COL_MAKO},
            "data_labels": {"value": True, "num_format": "#,##0"},
        }
    )
    ch_d.add_series(
        {
            "name": "Effective save fps",
            "categories": ["chart_data", 1, 8, n, 8],
            "values": ["chart_data", 1, 12, n, 12],
            "fill": {"color": COL_DAHENG},
            "data_labels": {"value": True, "num_format": "#,##0"},
        }
    )
    ch_d.set_title({"name": "D — Save rate matches acquisition (no sustained backlog)"})
    ch_d.set_y_axis({"name": "fps", "min": 0, "max": 2200})
    ch_d.set_x_axis({"name": "Test"})
    ch_d.set_legend({"position": "bottom"})
    ch_d.set_size({"width": 920, "height": 400})
    ft.insert_chart("A2", ch_d)
    ft.write(
        "A24",
        "Matching bar pairs confirm the FIFO queue drains as fast as frames arrive (200×200 ~1 kfps; 104×80 ~2 kfps).",
        fmt_cell,
    )

    wb.close()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
