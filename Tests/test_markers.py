import time
import numpy as np
import pyEEGPlot as pyep


print("=== Test marker realistici: 1 stimolo ogni 2 secondi ===")

# Dati EEG simulati
sr = 128
duration_sec = 20
T = sr * duration_sec
N = 4

X = np.random.randn(T, N)
sensors = ["Fp1", "Fp2", "C3", "C4"]

# Stimolazioni distanziate: una ogni secondo
stim = np.zeros(T, dtype=np.int64)

for i in range(0, T,2* sr):
    stim[i] = 1

pyep.init_plotting(backend="dynamic", do_warmup=True, use_marker_warmup=True)
print("=== Test marker rettangoli ===")
t0 = time.perf_counter()

fig = pyep.eegplot(
    X,
    sr,
    X_labels=sensors,
    stim=stim,
    stim_wl=sr,   # rettangolo di 1 secondo
    fig_size=(800, 600),
    block=False,
    _display=True
)

t1 = time.perf_counter()

print(f"Tempo di generazione plot: {t1 - t0:.2f}s")
#print("Chiudi la finestra per terminare il test.")