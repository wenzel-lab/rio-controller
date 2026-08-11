# libdaheng_grabber — native Acq for Rio

Shared library used when `RIO_DAHENG_CPP=1` (see [`daheng_cpp_camera.py`](../../drivers/camera/daheng_cpp_camera.py)).

Build shared lib (**use g++ / conda `cxx-compiler`, not Zig** — Zig-linked `.so` aborts on Galaxy `CNotImplementedError`):

```bash
cd software/native/daheng_grabber
# with micromamba env gxbuild:
export MAMBA_ROOT_PREFIX=$HOME/.local/mamba
$HOME/.local/micromamba/bin/micromamba run -n gxbuild make
```
