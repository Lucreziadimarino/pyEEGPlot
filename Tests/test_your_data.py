import pyEEGPlot as pyep
import numpy as np

# Configure once (first time only)
pyep.configure()

# Use your own EEG data
# X should be: samples x channels numpy array
# sr should be: sampling rate (Hz)
# sensors should be: list of channel names
fig = pyep.eegplot(your_data, your_sr, your_channel_names)
