import time
import numpy as np
import pyEEGPlot as pyep


# Test data
X = np.random.randn(128*4, 4)
sr = 128
sensors = ['Fp1', 'Fp2', 'C3', 'C4']


fig1 = pyep.eegplot(X, sr, sensors, fig_size=(600, 600))
print("This will only print after window is closed.")

print("\n=== Test 2: Non-blocking plot (same dynamic session)===")
fig2 = pyep.eegplot(X, sr, sensors, fig_size=(600, 600), block=False)
print("This prints immediately, but plot will close when script ends.")

print("\n=== Test 3: Static plot with CairoMakie ===")
pyep.init_plotting(backend="static", do_warmup=False)
fig3 = pyep.eegplot(X, sr, sensors, fig_size=(600, 600), block=False)
print("Static plot created successfully!")
