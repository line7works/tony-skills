"""A test-only kill for the document half of `report` (E13 punch list round 2, NEW-1 and NEW-2).

The stand-in `records.py` of `shimlib.py` can kill the core around its append, but the document
half runs inside `build.py` itself. This writes a `sitecustomize.py` into a scratch folder that,
put first on the child's PYTHONPATH, wraps `build_core.transaction` as it is imported and kills
the process with SIGKILL at one of two points, once (a marker file disarms it):

- `after_write`: right after the build doc's new bytes are written, before the receipt marks the
  document step done;
- `after_step`: right after the document step is receipted done, before `result.json` is written.

Nothing in the build core knows about it; no production code path carries a test hook for it.
"""
import os

SITECUSTOMIZE = r'''
import os, signal, sys
MODE = os.environ.get("PUNCH2_DOCKILL")
MARK = os.environ.get("PUNCH2_DOCKILL_MARK")
if MODE and MARK and not os.path.exists(MARK):
    import importlib.abc, importlib.machinery

    class _Hook(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path, target=None):
            if name != "build_core.transaction":
                return None
            sys.meta_path.remove(self)
            spec = importlib.machinery.PathFinder.find_spec(name, path)
            original = spec.loader.exec_module

            def exec_module(module):
                original(module)
                if MODE == "after_write":
                    real = module.canon.atomic_write

                    def atomic_write(target, data):
                        real(target, data)
                        if str(target).endswith(os.environ["PUNCH2_DOCKILL_DOC"]):
                            open(MARK, "w").write("x")
                            os.kill(os.getpid(), signal.SIGKILL)
                    module.canon.atomic_write = atomic_write
                elif MODE == "after_step":
                    real_step = module.write_document_step

                    def write_document_step(*args, **kwargs):
                        out = real_step(*args, **kwargs)
                        open(MARK, "w").write("x")
                        os.kill(os.getpid(), signal.SIGKILL)
                        return out
                    module.write_document_step = write_document_step
            spec.loader.exec_module = exec_module
            return spec

    sys.meta_path.insert(0, _Hook())
'''


def env(base, scratch, mode, doc):
    """`base` plus the injector for one kill at `mode` on the build doc `doc`."""
    folder = os.path.join(scratch, "punch2-inject")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "sitecustomize.py"), "w", encoding="utf-8") as fh:
        fh.write(SITECUSTOMIZE)
    out = dict(base)
    out["PYTHONPATH"] = folder + ((os.pathsep + base["PYTHONPATH"]) if base.get("PYTHONPATH") else "")
    out["PUNCH2_DOCKILL"] = mode
    out["PUNCH2_DOCKILL_MARK"] = os.path.join(folder, "fired-%s" % mode)
    out["PUNCH2_DOCKILL_DOC"] = doc
    return out


def fired(scratch, mode):
    return os.path.exists(os.path.join(scratch, "punch2-inject", "fired-%s" % mode))
