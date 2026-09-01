import os
os.chdir(r'C:\Users\lord cedrick cama\OneDrive\Desktop\final4_xample.new.1\high_end_ws_lounge')
import database_fixed as m
print('has DateTimeField', hasattr(m, 'DateTimeField'))
print('DateTimeField', getattr(m, 'DateTimeField', None))
