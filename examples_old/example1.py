#Opticspy provides real ray tracing module, primary lens design module as well as analysis.
#1. Build Lens system by adding surfaces, wavelengths, fields
#2. Trace ray through system, draw lens system
#3. Lens system analysis: spotdiagram and ray aberration plot(Ray fan plot)
#4. Real ray tracing through the system
#5. Lens paraxial information calculation by ABCD matrix module

#Following example shows use opticspy ray tracing module building a F/5 triplet with a max field=20 degree. Also it shows the spotdiagram and ray aberration plot of the system.

#1. Build Lens system by adding surfaces, wavelengths, fields:
#%matplotlib inline
from opticspy.ray_tracing import *

New_Lens = lens.Lens(lens_name='Triplet',creator='XF')
New_Lens.FNO = 5
New_Lens.lens_info()

New_Lens.add_wavelength(wl = 656.30)
New_Lens.add_wavelength(wl = 587.60)
New_Lens.add_wavelength(wl = 486.10)
New_Lens.list_wavelengths()

New_Lens.add_field_YAN(angle=0)
New_Lens.add_field_YAN(angle=14)
New_Lens.add_field_YAN(angle=20)
New_Lens.list_fields()

New_Lens.add_surface(number=1,radius=10000000,thickness=1000000,glass='air',output=True)
New_Lens.add_surface(number=2,radius=41.15909,thickness=6.097555 ,glass='S-BSM18_ohara',output=True)
New_Lens.add_surface(number=3,radius=-957.83146,thickness=9.349584,glass='air',output=True)
New_Lens.add_surface(number=4,radius=-51.32104,thickness=2.032518,glass='N-SF2_schott',output=True)
New_Lens.add_surface(number=5,radius=42.37768 ,thickness=5.995929 ,glass='air',output=True)
New_Lens.add_surface(number=6,radius=10000000,thickness=4.065037,glass='air',STO=True,output=True)
New_Lens.add_surface(number=7,radius=247.44562,thickness=6.097555,glass='S-BSM18_ohara',output=True)
New_Lens.add_surface(number=8,radius=-40.04016,thickness=85.593426,glass='air',output=True)
New_Lens.add_surface(number=9,radius=10000000,thickness=0,glass='air',output=True)

#2. Trace ray through system, draw lens system(first do refresh_paraxial function find entrace pupil position):
New_Lens.refresh_paraxial()

dict_list = trace.trace_draw_ray(New_Lens)
draw.draw_system(New_Lens)

#3. Lens system analysis: spotdiagram and ray aberration plot(Ray fan plot):
#Opticspy provide three kinds of tracing grid:
#In grid type, n = rays go through y axis of entrance pupil
#In circular type, n = ray rings in entrance pupil
#In random type, n = rays go through entrance pupil

field.grid_generator(12,grid_type='grid',output = 1)
analysis.spotdiagram(New_Lens,[1,2,3],[1,2,3],n=12,grid_type='grid')

field.grid_generator(6,grid_type='circular',output = 1)
analysis.spotdiagram(New_Lens,[1,2,3],[1,2,3],n=6,grid_type='circular')

field.grid_generator(100,grid_type='random',output = 1)
analysis.spotdiagram(New_Lens,[1,2,3],[1,2,3],n=100,grid_type='random')

analysis.Ray_fan(New_Lens,[1,2,3],[1,2,3])

#4. Real ray tracing through the system: user could choose different ray positions(relative to entrace pupil), fields and wavelengths to trace. Also user could choose output format, there are ray position output X,Y,Z and ray #direction output K,M,L as well as start and end surface choice:
#First example is tracing one ray in field 2(wavelength 1) go through bottom of entracne pupil(sagittal), output ray postion X,Y,Z, start and end surface use default(all surface):

trace.trace_one_ray(New_Lens,field_num=2,wave_num=1,ray=[0,-1],start=0,end=0,output=True,output_list=['X','Y','Z'])

#Second example is tracing chief ray in field 3(wavelength 2), output ray postion X,Y,Z, start surface 3 and end surface 7:
trace.trace_one_ray(New_Lens,3,2,[0,0],start=3,end=7,output=True,output_list=['X','Y','Z','K','L','M'])

#5. Lens paraxial information calculation by ABCD matrix module: image position, effective focal length, back focal length, entrance pupil position and diameter, exit pupil position, focal length from surface x to y, thickness between 2 surfaces, etc:

New_Lens.image_position()
New_Lens.EFY()
New_Lens.EFY(2,3)
New_Lens.BFL()
New_Lens.EP()
New_Lens.EPD
New_Lens.EX()
New_Lens.OAL(2,7)

# ============================================
# added block: ABCD + principal plane report
# ============================================

from opticspy.ray_tracing.first_order_tools import ABCD_start_end
from abcd_report_fixed import cardinals_air_air

print("\n============================================")
print(" Fixed-style ABCD / Principal plane report ")
print(" (reduced-angle [y, nθ], nd = 587.6 nm)")
print("============================================")

# ABCD from surface 2 to 8 (opticspy reduced-angle)
A, B, C, D = ABCD_start_end(New_Lens, 2, 8)

# ★ 計算は abcd_report_fixed に委譲
f, H, Hp, BFL = cardinals_air_air(A, B, C, D)

print(f"A = {A:.9f}")
print(f"B = {B:.9f}")
print(f"C = {C:.9f}")
print(f"D = {D:.9f}")

print("\n--- Cardinal points ---")
print(f"f'  = {f:.6f} mm")
print(f"H   = {H:.6f} mm  (from surface 2 vertex)")
print(f"H'  = {Hp:.6f} mm (from surface 8 vertex)")
print(f"BFL = {BFL:.6f} mm")

# axial positions
z = 0.0
zpos = {}
for i in range(2, 9):
    zpos[i] = z
    z += New_Lens.surface_list[i-1].thickness

z8 = zpos[8]
z9 = z8 + New_Lens.surface_list[7].thickness
z_img = z8 + BFL

print("\n--- Image plane check ---")
print(f"z8           = {z8:.6f}")
print(f"z9 (recipe)  = {z9:.6f}")
print(f"z8 + BFL     = {z_img:.6f}")
print(f"Δz           = {z9 - z_img:.9e} mm")
