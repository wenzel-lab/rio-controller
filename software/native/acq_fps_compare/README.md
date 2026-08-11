# Acq.FPS compare — Python vs C++

Paired 20 s logs at **200×200 / 20 µs** (MER2 `FDQ23120254`).

| File | Backend |
|---|---|
| `acq_cpp_200x200_20us.csv` | `RIO_DAHENG_CPP=1` (`DahengCppCamera`) |
| `acq_python_200x200_20us.csv` | gxipy A+B (`DahengCamera`) |

Columns: `t_s`, `acq_fps` (UI metric), `count_fps` (1 s wall-clock note rate — prefer this for Python), `sdk_fps`, `label`, `backend`.

## Re-run

```bash
# Close Rio first
export GALAXY_ROOT=$HOME/Galaxy_camera
export LD_LIBRARY_PATH=$GALAXY_ROOT/lib/x86_64:$PWD/../daheng_grabber:$LD_LIBRARY_PATH
export PYTHONPATH=../../  # software/
export RIO_DAHENG_SN=FDQ23120254

RIO_DAHENG_CPP=1 python3 ../../scripts/log_acq_fps.py --out acq_cpp_200x200_20us.csv --label cpp
unset RIO_DAHENG_CPP
python3 ../../scripts/log_acq_fps.py --out acq_python_200x200_20us.csv --label python
```

Visual summary: Cursor canvas `daheng-acq-python-vs-cpp.canvas.tsx`.
