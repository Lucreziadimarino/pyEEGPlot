import numpy as np
import os

def build_demo_signal(
    duration_s: float = 4.0,
    sr: float = 250.0,
    n_samples: int = 1000,
    n_channels: int = 16,
    freq_hz: float = 5.0,
) -> np.ndarray:
    """
    Build a synthetic multi-channel EEG-like demo signal.

    Returns
    -------
    np.ndarray
        Array shaped as (samples, channels).
    """
    t = np.linspace(0, duration_s, n_samples)
    return np.sin(2 * np.pi * freq_hz * t).reshape(-1, 1) * np.random.randn(1, n_channels)


def edf_annotations_to_stim(raw, n_samples: int):
    """
    Convert EDF annotations into a sparse stimulus vector.

    Only annotation onsets are marked.
    """
    sr = raw.info["sfreq"]
    stim = np.zeros(n_samples, dtype=int)

    ordered_labels = []
    for desc in raw.annotations.description:
        label = str(desc)
        if label not in ordered_labels:
            ordered_labels.append(label)

    label_to_id = {label: i + 1 for i, label in enumerate(ordered_labels)}
    stim_labels = ordered_labels

    for onset, _duration, desc in zip(
        raw.annotations.onset,
        raw.annotations.duration,
        raw.annotations.description,
    ):
        label = str(desc)
        tag = label_to_id[label]
        s0 = max(0, min(n_samples - 1, int(round(float(onset) * sr))))
        stim[s0] = tag

    return stim, stim_labels, label_to_id


def load_channel_labels(labels_path: str | None, n_channels: int):
    """
    Load channel labels from a text file.

    Returns None if the file is missing or the number of labels does not match
    the number of channels.
    """
    if not labels_path or not os.path.exists(labels_path):
        return None

    with open(labels_path, "r", encoding="utf-8") as f:
        labels = [line.strip() for line in f.readlines() if line.strip()]

    if labels and labels[0].isdigit():
        labels = labels[1:]

    if len(labels) != n_channels:
        return None

    return labels


def load_eeg_file_for_plot(
    file_path: str,
    *,
    use_stim: bool = True,
    txt_sr: float | None = None,
    labels_path: str | None = None,
):
    """
    Load an EDF or TXT file and convert it into plotting inputs.

    Returns
    -------
    dict
        Keys: X, sr, labels, stim, stim_labels, stim_wl
    """
    stim = None
    stim_labels = None
    stim_wl = 1
    lower_path = file_path.lower()

    if lower_path.endswith(".edf"):
        import mne
        raw = mne.io.read_raw_edf(file_path, preload=True)
        raw_eeg = raw.copy().pick("eeg")
        X = raw_eeg.get_data().T
        sr = raw_eeg.info["sfreq"]
        labels = raw_eeg.ch_names
        if use_stim and len(raw.annotations) > 0:
            stim, stim_labels, _ = edf_annotations_to_stim(raw, X.shape[0])

    elif lower_path.endswith(".txt"):
        X = np.loadtxt(file_path)
        X = np.atleast_2d(X)
        if X.shape[0] < X.shape[1]:
            X = X.T
        if txt_sr is None:
            raise ValueError("Sampling rate is required for .txt files.")
        sr = float(txt_sr)
        labels = load_channel_labels(labels_path, X.shape[1]) or [f"CH{i + 1}" for i in range(X.shape[1])]
    else:
        raise ValueError(f"Unsupported file format: {file_path}")

    # Return for both file formats. 
    return {
        "X": X, "sr": sr, "labels": labels,
        "stim": stim, "stim_labels": stim_labels, "stim_wl": stim_wl,
    }