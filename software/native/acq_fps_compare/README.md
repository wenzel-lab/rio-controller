# Acq.FPS compare — Python vs C++

Paired 20 s logs at **200×200 / 20 µs** (MER2 `FDQ23120254`).

| File | Backend |
|---|---|
| `acq_cpp_200x200_20us.csv` | `RIO_DAHENG_CPP=1` (`DahengCppCamera`) |
| `acq_python_200x200_20us.csv` | gxipy A+B (`DahengCamera`) |
| **`acq_fps_python_vs_cpp.xlsx`** | **Excel chart for PowerPoint** (data + KPIs + line chart) |

Columns in CSV: `t_s`, `acq_fps` (UI metric), `count_fps` (1 s wall-clock note rate — **prefer this for Python**), `sdk_fps`, `label`, `backend`.

## PowerPoint Excel workbook

Open [`acq_fps_python_vs_cpp.xlsx`](acq_fps_python_vs_cpp.xlsx) → sheet **`chart`**:

- Title states the takeaway (C++ ≈ SDK; Python lags ~213 fps)
- KPI strip: C++ / Python / **Δ gap** / SDK
- Line chart of `count_fps`, Y-axis **800–1100**, SDK dashed
- Gap callout `Δ ≈ 213 fps` under the plot
- Sheets `summary` (who-wins tags) and `data` (auditable numbers)

**Paste into PPT:** select the chart (and optionally rows 1–5 / the Δ box) → Copy → PowerPoint → Paste as Excel Chart / Keep Source Formatting.

> **Note:** This machine may not have Excel/LibreOffice installed — the `.xlsx` then shows “failed to open file”. Use:
> - [`acq_fps_python_vs_cpp.html`](acq_fps_python_vs_cpp.html) — open in Firefox (chart + KPIs)
> - [`acq_fps_python_vs_cpp.csv`](acq_fps_python_vs_cpp.csv) — upload to Google Sheets / Excel Online
> - Or install Calc: `sudo apt install libreoffice-calc`

Regenerate after new CSVs:

```bash
cd software/native/acq_fps_compare
python3 build_acq_xlsx.py
# needs openpyxl (e.g. pip install openpyxl)
```

## Re-run logs

```bash
# Close Rio first
export GALAXY_ROOT=$HOME/Galaxy_camera
export LD_LIBRARY_PATH=$GALAXY_ROOT/lib/x86_64:$PWD/../daheng_grabber:$LD_LIBRARY_PATH
export PYTHONPATH=../../  # software/
export RIO_DAHENG_SN=FDQ23120254

RIO_DAHENG_CPP=1 python3 ../../scripts/log_acq_fps.py --out acq_cpp_200x200_20us.csv --label cpp
unset RIO_DAHENG_CPP
python3 ../../scripts/log_acq_fps.py --out acq_python_200x200_20us.csv --label python
python3 build_acq_xlsx.py
```

Cursor preview (optional): canvas `daheng-acq-python-vs-cpp.canvas.tsx`.
