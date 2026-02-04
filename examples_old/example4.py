#Real Ray Tracing Example: Microscope. This example is immature. 
#Because an microscope system is a finite conjugate system and it should be defined by NA, etc. 
#But opticspy shows some ability to trace it.

from opticspy.ray_tracing import *

New_Lens = codev.readseq("microscope.seq")
New_Lens.lens_info()

New_Lens.FNO = 0.7
New_Lens.refresh_paraxial()
trace.trace_draw_ray(New_Lens)
draw.draw_system(New_Lens)

analysis.spotdiagram(New_Lens,[1,2,3],[1,2,3],n=12,grid_type='grid')

analysis.Ray_fan(New_Lens,[1,2,3],[1,2,3])
