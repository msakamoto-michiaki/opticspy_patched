#Real Ray Tracing Example: Microscope. This example is immature. 
#Because an microscope system is a finite conjugate system and it should be defined by NA, etc. 
#But opticspy shows some ability to trace it.

from opticspy.ray_tracing import *
from utils.codev_io import find_seq_path  # ← utils化
from utils.plotting import rename_fixed_png, rename_latest_spotdiagram
import os

## out
outdir = os.path.join("out", "examples", "example4")
os.makedirs(outdir, exist_ok=True)

seq_path = find_seq_path("microscope.seq")      # ←ここがポイント
New_Lens = codev.readseq(seq_path,output=True)
New_Lens.lens_info()

New_Lens.FNO = 0.7
New_Lens.refresh_paraxial()
trace.trace_draw_ray(New_Lens)
draw.draw_system(New_Lens)
newpath = rename_fixed_png(
    "out/opticspy_ray_tracing_draw__draw_system.png",
    outdir,
    tag="example4_"
)


analysis.spotdiagram(New_Lens,[1,2,3],[1,2,3],n=12,grid_type='grid')
rename_latest_spotdiagram(outdir, tag="example4_grid_n12")

analysis.Ray_fan(New_Lens,[1,2,3],[1,2,3])
newpath = rename_fixed_png(
    "out/opticspy_ray_tracing_analysis__Ray_fan.png",
    outdir,
    tag="example4_"
)
