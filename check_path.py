import os, sys

print("=== cwd ===")
print(os.getcwd())

print("\n=== sys.path (top 10) ===")
for i, p in enumerate(sys.path[:10]):
    print(f"{i:2d}: {p!r}")

print("\n=== OPTICSPY_ROOT env ===")
print(os.environ.get("OPTICSPY_ROOT"))

print("\n=== import opticspy ===")
import opticspy
print("opticspy module file:", getattr(opticspy, "__file__", None))
print("opticspy package path:", getattr(opticspy, "__path__", None))

print("\n=== import glass_funcs (used by get_refractive_index_nm) ===")
from opticspy.ray_tracing import glass_funcs
print("glass_funcs file:", getattr(glass_funcs, "__file__", None))

