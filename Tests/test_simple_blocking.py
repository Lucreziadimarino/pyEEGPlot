import numpy as np
import pyEEGPlot as pyep

print("=== Simple Blocking Test ===")
# Test data
X = np.random.randn(128*4, 4)
sr = 128
sensors = ['Fp1', 'Fp2', 'C3', 'C4']

print("Creating blocking plot (will wait for window close)...")
fig = pyep.eegplot(X, sr, sensors, fig_size=(600, 600))
print("Plot created and window closed - test completed!")
