#Real Ray Tracing Example: F/5 Double Gauss
from opticspy.ray_tracing import *
from opticspy.ray_tracing import field, analysis
import os
from utils.plotting import setup_matplotlib_headless, ShowToSavefig, rename_latest_spotdiagram
from utils.plotting import rename_fixed_png

#outputs dir
outdir = os.path.join("out", "examples", "example2")
os.makedirs(outdir, exist_ok=True)
setup_matplotlib_headless()

#settings
New_Lens = lens.Lens(lens_name='Doublegauss',creator='XF')
New_Lens.FNO = 5
New_Lens.lens_info()

New_Lens.add_wavelength(wl = 656.30)
New_Lens.add_wavelength(wl = 587.60)
New_Lens.add_wavelength(wl = 486.10)

New_Lens.add_field_YAN(angle=0)
New_Lens.add_field_YAN(angle=10)
New_Lens.add_field_YAN(angle=14)

New_Lens.add_surface(number=1,radius=10000000,thickness=10000000,glass='air')
New_Lens.add_surface(number=2,radius=56.20238,thickness=8.75 ,glass='N-SSK2_schott')
New_Lens.add_surface(number=3,radius=152.28580,thickness=0.5,glass='air')
New_Lens.add_surface(number=4,radius=37.68262,thickness=12.5,glass='N-SK2_schott')
New_Lens.add_surface(number=5,radius=10000000 ,thickness=3.8 ,glass='F5_schott')
New_Lens.add_surface(number=6,radius=24.23130,thickness=16.369445,glass='air')
New_Lens.add_surface(number=7,radius=10000000,thickness=13.747957,glass='air',STO=True)
New_Lens.add_surface(number=8,radius=-28.37731,thickness=3.8,glass='F5_schott')
New_Lens.add_surface(number=9,radius=100000000,thickness=11,glass='N-SK16_schott')
New_Lens.add_surface(number=10,radius=-37.92546,thickness=0.5,glass='air')
New_Lens.add_surface(number=11,radius=177.41176,thickness=7,glass='N-SK16_schott')
New_Lens.add_surface(number=12,radius=-79.41143,thickness=61.487536,glass='air')
New_Lens.add_surface(number=13,radius=100000000,thickness=0,glass='air')

New_Lens.refresh_paraxial()
New_Lens.solve_imageposition()
trace.trace_draw_ray(New_Lens)
draw.draw_system(New_Lens)
newpath = rename_fixed_png(
    "out/opticspy_ray_tracing_draw__draw_system.png",
    outdir,
    tag="example2_"
)

analysis.spotdiagram(New_Lens,[1,2,3],[1,2,3])
rename_latest_spotdiagram(outdir, tag="example2_spot_random")

analysis.Ray_fan(New_Lens,[1,2,3],[1,2,3])
newpath = rename_fixed_png(
    "out/opticspy_ray_tracing_analysis__Ray_fan.png",
    outdir,
    tag="example2_"
)

