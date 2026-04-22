import numpy as np
import pyEEGPlot as pyep

# Basic test
X = np.random.randn(128*4, 4)
sr = 128
sensors = ['Fp1', 'Fp2', 'C3', 'C4']
fig = pyep.eegplot(X, sr, sensors, fig_size=(600, 600))
print("Interactive plot created successfully!")
