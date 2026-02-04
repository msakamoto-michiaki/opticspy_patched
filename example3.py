from opticspy.ray_tracing import codev, trace, draw, analysis
from utils.codev_io import find_seq_path  # ← utils化
from utils.plotting import rename_fixed_png, rename_latest_spotdiagram
import os

outdir = os.path.join("out", "examples", "example3")
os.makedirs(outdir, exist_ok=True)

seq_path = find_seq_path("petzval.seq")      # ←ここがポイント
New_Lens = codev.readseq(seq_path, output=True)

New_Lens.FNO = 2
New_Lens.refresh_paraxial()
New_Lens.solve_imageposition()

trace.trace_draw_ray(New_Lens)
draw.draw_system(New_Lens)
newpath = rename_fixed_png(
    "out/opticspy_ray_tracing_draw__draw_system.png",
    outdir,
    tag="example3_"
)

# draw_system が out/ に固定名 png を吐くなら回収（固定名が分かれば rename_fixed_png）
# 分からないなら move_new_pngs を使う
# rename_fixed_png("out/（固定名）.png", outdir, tag="example3_layout")

analysis.spotdiagram(New_Lens, [1,2,3], [1,2,3], n=6, grid_type="circular")
rename_latest_spotdiagram(outdir, tag="example3_spot_circular_n6")
