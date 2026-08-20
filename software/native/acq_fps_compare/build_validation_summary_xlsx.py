#!/usr/bin/env python3
"""Build Excel summary of Daheng/Record ROI validation session (Aug 2026)."""

from __future__ import annotations

from pathlib import Path

import xlsxwriter

HERE = Path(__file__).resolve().parent
OUT = HERE / "daheng_validation_summary.xlsx"

# --- Summary rows (what we demonstrated) ---
SUMMARY = [
    (
        "Manuscrito / adquisición",
        "MER2 ~1 053 fps @ ROI 200×200, exposición 20 µs",
        "Sweep nativo C++ (roi_acq_sweep_20us.csv) + telemetría SDK Acq.FPS",
        "Sí",
    ),
    (
        "Manuscrito / adquisición",
        "320×240 Daheng ~903 fps (Mako datasheet ~1 350 fps @ 320×240)",
        "mako_vs_daheng_roi_fps.xlsx",
        "Sí",
    ),
    (
        "Manuscrito / ROI",
        "300×100 inválido (Width inc=8); usar 296×100 o 304×100 (~1 792 fps)",
        "GenICam / sweep",
        "Sí",
    ),
    (
        "UI exposición",
        "Mínimo UI 20 µs (antes 100 µs hardcoded)",
        "index.html + DahengCppCamera fallback",
        "Sí",
    ),
    (
        "Record ROI (bug)",
        "Antes: 50/50 archivos pero mismo frame (1 MD5); timing ~16 ms",
        "Grabación 20260819_152150",
        "Corregido",
    ),
    (
        "Record ROI (fix)",
        "wait_frame_array + cola FIFO C++ (libdaheng_grabber.so)",
        "Código + rebuild .so",
        "Sí",
    ),
    (
        "Record ROI (usuario)",
        "50/50 · frame_id 82338–82387 · no gaps · ~1 075 fps efectivo",
        "recordings/20260819_163902 + manifest.csv",
        "Sí",
    ),
    (
        "Trazabilidad",
        "manifest.csv: index, seq, frame_id, gap_before por frame",
        "Cada grabación Record",
        "Sí",
    ),
    (
        "Stress real",
        "200×200 ×5 000 frames: 0 dropped, 0 overflow",
        "Script verify / stress (servidor)",
        "Sí",
    ),
    (
        "Stress real",
        "104×80 ×20 000 frames @ ~2 087 fps: 0 dropped, 0 overflow",
        "Script verify / stress (servidor)",
        "Sí",
    ),
    (
        "Límite artificial",
        "Pérdidas solo con guardado muy lento simulado (RIO_RECORD_SAVE_DELAY_US)",
        "No es condición de laboratorio normal",
        "N/A",
    ),
]

# --- Detailed record tests ---
RECORD_TESTS = [
    # label, roi, frames, acq_fps, save_fps, fid_first, fid_last, dropped, overflow, gaps, folder_or_note
    ("Usuario UI", "200×200", 50, 1054, 1075, 82338, 82387, 0, 0, 0, "20260819_163902"),
    ("Post-fix verify", "200×200", 50, 1054, 1063, 287, 336, 0, 0, 0, "script verify"),
    ("Stress real", "200×200", 500, 1055, 1055, 296, 795, 0, 0, 0, "script"),
    ("Stress real", "200×200", 5000, 1055, 1055, 268, 5267, 0, 0, 0, "script"),
    ("Stress real", "104×80", 500, 2090, 2090, 584, 1083, 0, 0, 0, "script ~2 kfps"),
    ("Stress real", "104×80", 10000, 2087, 2087, 585, 10584, 0, 0, 0, "script"),
    ("Stress real", "104×80", 20000, 2087, 2087, 589, 20588, 0, 0, 0, "script"),
    ("Full sensor", "1440×1080", 500, 227, 227, 64, 563, 0, 0, 0, "script"),
    ("Bug (pre-fix)", "200×200", 50, 1054, 3085, "—", "—", "—", "—", "50 dup", "20260819_152150 · 1 MD5"),
]

COL_OK = "#1F8A65"
COL_WARN = "#C0392B"
COL_HDR = "#1B4F72"
COL_MUTED = "#555555"


def main() -> None:
    wb = xlsxwriter.Workbook(str(OUT))
    fmt_title = wb.add_format({"bold": True, "font_size": 14, "font_color": COL_HDR})
    fmt_hdr = wb.add_format({"bold": True, "bg_color": "#D6EAF8", "border": 1})
    fmt_cell = wb.add_format({"border": 1, "text_wrap": True, "valign": "top"})
    fmt_ok = wb.add_format({"border": 1, "font_color": COL_OK, "bold": True})
    fmt_bad = wb.add_format({"border": 1, "font_color": COL_WARN})
    fmt_num = wb.add_format({"border": 1, "num_format": "#,##0"})

    # ----- Sheet: Resumen -----
    ws = wb.add_worksheet("Resumen")
    ws.set_column("A:A", 22)
    ws.set_column("B:B", 48)
    ws.set_column("C:C", 36)
    ws.set_column("D:D", 12)
    ws.write("A1", "Validación Daheng MER2 + Record ROI — 19 Aug 2026", fmt_title)
    ws.write("A2", "Host CoolerMaster · RIO_DAHENG_CPP=1 · SN FDQ23120254", fmt_cell)
    headers = ["Área", "Qué demostramos", "Evidencia", "Estado"]
    for c, h in enumerate(headers):
        ws.write(3, c, h, fmt_hdr)
    for r, row in enumerate(SUMMARY, start=4):
        for c, val in enumerate(row):
            f = fmt_cell
            if c == 3 and val in ("Sí", "Corregido"):
                f = fmt_ok
            elif c == 3 and val == "N/A":
                f = fmt_bad
            ws.write(r, c, val, f)

    # ----- Sheet: record_tests (data for chart) -----
    wd = wb.add_worksheet("record_data")
    wd.set_column("A:A", 18)
    wd.set_column("B:B", 12)
    chart_headers = [
        "Prueba",
        "ROI",
        "Frames",
        "Acq fps",
        "Save fps",
        "Dropped",
        "Overflow",
        "Gaps",
    ]
    for c, h in enumerate(chart_headers):
        wd.write(0, c, h, fmt_hdr)
    chart_rows = [r for r in RECORD_TESTS if r[6] != "—"]  # skip pre-fix for numeric chart
    for r, row in enumerate(chart_rows, start=1):
        label, roi, frames, acq, save, f0, f1, drop, ov, gaps, note = row
        wd.write(r, 0, label, fmt_cell)
        wd.write(r, 1, roi, fmt_cell)
        wd.write(r, 2, frames, fmt_num)
        wd.write(r, 3, acq, fmt_num)
        wd.write(r, 4, save, fmt_num)
        wd.write(r, 5, drop, fmt_num)
        wd.write(r, 6, ov, fmt_num)
        wd.write(r, 7, gaps, fmt_num)

    n = len(chart_rows)

    # ----- Sheet: pruebas_record (full table) -----
    wt = wb.add_worksheet("Pruebas Record")
    wt.set_column("A:A", 16)
    wt.set_column("K:K", 28)
    full_h = [
        "Prueba",
        "ROI",
        "Frames",
        "Acq fps",
        "Save fps",
        "frame_id ini",
        "frame_id fin",
        "Dropped",
        "Overflow",
        "Gaps",
        "Notas",
    ]
    for c, h in enumerate(full_h):
        wt.write(0, c, h, fmt_hdr)
    for r, row in enumerate(RECORD_TESTS, start=1):
        for c, val in enumerate(row):
            wt.write(r, c, val, fmt_cell)

    # ----- Sheet: figure -----
    wf = wb.add_worksheet("figure")
    wf.write("A1", "Figura: fps efectivo de guardado (Record ROI, pruebas reales)", fmt_title)
    wf.write("A2", "Todas las pruebas reales post-fix: dropped = 0, overflow = 0", fmt_cell)

    chart1 = wb.add_chart({"type": "column"})
    chart1.add_series(
        {
            "name": "Save fps efectivo",
            "categories": ["record_data", 1, 0, n, 0],
            "values": ["record_data", 1, 4, n, 4],
            "fill": {"color": COL_OK},
            "data_labels": {"value": True, "num_format": "#,##0"},
        }
    )
    chart1.add_series(
        {
            "name": "Acq fps (ref.)",
            "categories": ["record_data", 1, 0, n, 0],
            "values": ["record_data", 1, 3, n, 3],
            "fill": {"color": COL_HDR},
            "data_labels": {"value": True, "num_format": "#,##0"},
        }
    )
    chart1.set_title({"name": "Acq vs Save fps por prueba Record"})
    chart1.set_x_axis({"name": "Prueba"})
    chart1.set_y_axis({"name": "fps", "major_gridlines": {"visible": True}})
    chart1.set_legend({"position": "bottom"})
    chart1.set_size({"width": 900, "height": 480})
    wf.insert_chart("A4", chart1)

    chart2 = wb.add_chart({"type": "column"})
    chart2.add_series(
        {
            "name": "Frames guardados",
            "categories": ["record_data", 1, 0, n, 0],
            "values": ["record_data", 1, 2, n, 2],
            "fill": {"color": COL_HDR},
            "data_labels": {"value": True, "num_format": "#,##0"},
        }
    )
    chart2.add_series(
        {
            "name": "Frames dropped",
            "categories": ["record_data", 1, 0, n, 0],
            "values": ["record_data", 1, 5, n, 5],
            "fill": {"color": COL_WARN},
            "data_labels": {"value": True},
        }
    )
    chart2.set_title({"name": "Frames guardados vs perdidos (real: todos 0 dropped)"})
    chart2.set_x_axis({"name": "Prueba"})
    chart2.set_y_axis({"name": "Frames", "major_gridlines": {"visible": True}})
    chart2.set_legend({"position": "bottom"})
    chart2.set_size({"width": 900, "height": 400})
    wf.insert_chart("A28", chart2)

    wf.write(
        "A52",
        "Nota: Bug pre-fix (152150) no aparece en gráficos — 50 JPEGs idénticos, ~16 ms total.",
        fmt_cell,
    )

    wb.close()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
