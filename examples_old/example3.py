#This example shows how to use CodeV convetor to build a F/2 Petzval lens with CodeV seq file
#The "petzval.seq" file is in the "CodeV_examples" folder

from opticspy.ray_tracing import *

New_Lens = codev.readseq("petzval.seq",output=True)

New_Lens.lens_info()
New_Lens.list_wavelengths()
New_Lens.list_fields()
New_Lens.FNO = 2

New_Lens.refresh_paraxial()
New_Lens.solve_imageposition()

trace.trace_draw_ray(New_Lens)
draw.draw_system(New_Lens)

analysis.spotdiagram(New_Lens,[1,2,3],[1,2,3],n=6,grid_type='circular')

analysis.Ray_fan(New_Lens,[1,2,3],[1,2,3])
