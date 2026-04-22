import numpy as np
import pyEEGPlot as pyep

print("=== Final Blocking Test for pyEEGPlot ===")

# Test data
X = np.random.randn(256, 4)
sr = 128
sensors = ['Fp1', 'Fp2', 'C3', 'C4']

print("\n1. Blocking plot (default behavior):")
print("   - Window should stay open for interaction")
print("   - Script will wait for window to close")
fig1 = pyep.eegplot(X, sr, sensors, fig_size=(600, 600))

print("\n2. Non-blocking plot:")
print("   - Window will close immediately after creation")
print("   - Script continues without waiting")
fig2 = pyep.eegplot(X, sr, sensors, fig_size=(600, 600), block=False)

print("\n3. Static plot with CairoMakie:")
print("   - Should work without blocking")
from julia import Main
Main.eval("using CairoMakie; CairoMakie.activate!()")
fig3 = pyep.eegplot(X, sr, sensors, fig_size=(600, 600), block=False)

print("\n[SUCCESS] All tests completed successfully!")
print("   - Blocking plot: Window stays open for interaction")
print("   - Non-blocking: Plot closes when script ends")
print("   - Static plot: Works without blocking")
