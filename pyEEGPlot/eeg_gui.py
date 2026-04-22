# ---------------------------------------------------------------
# Import Python modules
# ---------------------------------------------------------------
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import multiprocessing as mp
import queue

try:
    from .core import init_plotting, eegplot, save_figure
    from .dynamic_worker import run_dynamic_worker
    from .data_utils import build_demo_signal, load_eeg_file_for_plot
except ImportError:
    from core import init_plotting, eegplot, save_figure
    from dynamic_worker import run_dynamic_worker
    from data_utils import build_demo_signal, load_eeg_file_for_plot

class EEGPlotGUI:
    
    def __init__(self, root):
        """
        Initialize the main GUI window, control variables, 
        and multiprocessing queues for the dynamic worker.
        """
        self.root = root
        self.root.title("EEGPlot - Developer Interface")
        self.root.geometry("700x550") 
        self.root.resizable(True, True)

        self.backend_var = tk.StringVar(value="dynamic")
        self.progress_var = tk.IntVar(value=0)

        self.dynamic_process = None
        self.dynamic_command_q = None
        self.dynamic_status_q = None
        self.dynamic_ready = False

        self._build_ui()
        self.update_button_texts()
        self.root.after(100, self._poll_dynamic_worker)

    def _build_ui(self):
        # -----------------------------------------------------------------
        # BACKEND INIZIALIZATION SECTION
        # -----------------------------------------------------------------
        frame_init = ttk.LabelFrame(self.root, text="1. Backend Initialization", padding=15)
        frame_init.pack(fill="x", padx=10, pady=10)

        ttk.Radiobutton(frame_init, text="Dynamic (GLMakie - Interactive, needs warm-up)", 
                        variable=self.backend_var, value="dynamic",
                        command=self.update_button_texts).pack(anchor="w", pady=2)
        ttk.Radiobutton(frame_init, text="Static (CairoMakie - Fast, non-interactive)", 
                        variable=self.backend_var, value="static",
                        command=self.update_button_texts).pack(anchor="w", pady=2)

        self.init_btn = ttk.Button(frame_init, text="Initialize and run warm-up", command=self.start_init)
        self.init_btn.pack(pady=10, fill="x")
        # Progrress bar used during backend initialization
        self.progress_bar = ttk.Progressbar(frame_init, variable=self.progress_var, maximum=100) # Progress bar for initialization
        self.progress_bar.pack(fill="x", pady=5)
        self.status_label = ttk.Label(frame_init, text="Waiting...", foreground="gray")
        self.status_label.pack(anchor="w")

        # -----------------------------------------------------------------
        # PLOT GENERATION SECTION
        # -----------------------------------------------------------------
        self.frame_plot = ttk.LabelFrame(self.root, text="2. Plotting Panel", padding=15)
        self.frame_plot.pack(fill="x", padx=10, pady=10)

        self.demo_btn = ttk.Button(self.frame_plot, text="Generate Demo Plot", state="disabled", command=self.plot_demo)
        self.demo_btn.pack(fill="x", pady=5)

        ttk.Separator(self.frame_plot, orient="horizontal").pack(fill="x", pady=15)

        ttk.Label(self.frame_plot, text="File plotting options:").pack(anchor="w", pady=(0, 5))
        
        grid_frame = ttk.Frame(self.frame_plot)
        grid_frame.pack(fill="x", pady=5)
        
        # Plot parameters
        ttk.Label(grid_frame, text="Sampling rate (Hz):").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_sr = ttk.Entry(grid_frame, width=12)
        self.entry_sr.insert(0, "250")
        self.entry_sr.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        # Figure size and optional stimulation settings
        ttk.Label(grid_frame, text="Figure size (X, Y):").grid(row=1, column=0, sticky="w", pady=2)
        dim_frame = ttk.Frame(grid_frame)
        dim_frame.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        self.entry_fig_x = ttk.Entry(dim_frame, width=5)
        self.entry_fig_x.insert(0, "500")
        self.entry_fig_x.pack(side="left")
        ttk.Label(dim_frame, text="x").pack(side="left", padx=2)
        self.entry_fig_y = ttk.Entry(dim_frame, width=5)
        self.entry_fig_y.insert(0, "500")
        self.entry_fig_y.pack(side="left")

        self.var_use_stim = tk.BooleanVar(value=True)
        ttk.Checkbutton(grid_frame, text="Show markers (stim)", variable=self.var_use_stim).grid(row=2, column=0, columnspan=2, sticky="w", pady=4)
    
        self.load_btn = ttk.Button(self.frame_plot, text="Load a File to plot(.edf, .txt)", 
                                state="disabled", command=self.load_and_plot)
        self.load_btn.pack(fill="x", pady=5)
        

    def update_progress(self, value, message):
        """
        Update the progress bar.
        """
        self.progress_var.set(value)
        self.status_label.config(text=message)
        if value >= 100:
            self.status_label.config(foreground="green", text="Ready!")
            self._enable_plotting()
        self.root.update_idletasks()


    def update_button_texts(self):
        """
        Update button labels and interface messages to reflect 
        the behavior of the currently selected backend. 
        """
        # Update button labels to reflect the behavior of the selected backend.
        if self.backend_var.get() == "static":
            self.init_btn.config(text="Initialize")
            self.demo_btn.config(text="Save an image of Demo Plot")
            self.load_btn.config(text="Load and save an image of File")
            # In static mode, plots are exported instead of being opened interactively
            self.status_label.config(text="Static mode: plots will be saved as .png, not shown.", foreground="orange")
        else:
            self.init_btn.config(text="Initialize and run warm-up")
            self.demo_btn.config(text="Generate Demo Plot")
            self.load_btn.config(text="Load a File to plot(.edf, .txt)")
            self.status_label.config(text="Dynamic selected.", foreground="green")

        self.demo_btn.config(state="disabled")
        self.load_btn.config(state="disabled")

        self.dynamic_ready = False

    def _enable_plotting(self):
        """
        Enable plotting buttons once the backend is ready. 
        """
        self.demo_btn.config(state="normal")
        self.load_btn.config(state="normal")
        self.status_label.config(foreground="green")


    def _ensure_dynamic_worker(self):
        """
        Check if dynamic worker process is running. If not, 
        initialize the queues and start the background process. 
        """
        if self.dynamic_process is not None and self.dynamic_process.is_alive():
            return

        self.dynamic_command_q = mp.Queue()
        self.dynamic_status_q = mp.Queue()

        self.dynamic_process = mp.Process(
            target=run_dynamic_worker,
            args=(self.dynamic_command_q, self.dynamic_status_q),
            daemon=False
        )
        self.dynamic_process.start()
        self.dynamic_ready = False


    def _poll_dynamic_worker(self):
        """
        Periodically check the status queue for updates or errors.
        """
        if self.dynamic_status_q is not None:
            while True:
                try:
                    msg = self.dynamic_status_q.get_nowait()
                except queue.Empty:
                    break

                msg_type = msg.get("type")
                message = msg.get("message", "")

                if msg_type == "progress":
                    self.progress_var.set(msg.get("value", 0))
                    self.status_label.config(text=message, foreground="blue")

                elif msg_type == "ready":
                    self.progress_var.set(100)
                    self.status_label.config(text=message, foreground="green")
                    self.dynamic_ready = True
                    self._enable_plotting()
                    self.init_btn.config(state="normal")

                elif msg_type == "state":
                    self.status_label.config(text=message, foreground="blue")

                elif msg_type == "error":
                    self.status_label.config(text="Error.", foreground="red")
                    self.init_btn.config(state="normal")
                    messagebox.showerror("Dynamic worker error", message)

        self.root.after(100, self._poll_dynamic_worker)


    def _get_fig_size(self):
        """
        Parse the user input for figure dimensions.
        Returns a tuple of (width, height) in integers.
        """
        return (int(float(self.entry_fig_x.get())), int(float(self.entry_fig_y.get())))


    def start_init(self):
        """
        Trigger the initialization of the selected backend.
        Delegates to the worker for 'dynamic' or main thread for 'static'.
        """
        self.init_btn.config(state="disabled")
        self.demo_btn.config(state="disabled")
        self.load_btn.config(state="disabled")
        self.progress_var.set(0)

        backend = self.backend_var.get()

        if backend == "dynamic":
            self._ensure_dynamic_worker()
            self.dynamic_ready = False
            self.status_label.config(text="Sending initialize command...", foreground="blue")
            self.dynamic_command_q.put({"action": "initialize"})
            return

        self.status_label.config(text="Initializing...", foreground="blue")
        self.root.after(50, self._run_init_main_thread)

    def on_close(self):
        """
        Handle window close event to cleanly shut down background processes.
        """
        try:
            if self.dynamic_command_q is not None:
                self.dynamic_command_q.put({"action": "quit"})
        except Exception:
            pass

        try:
            if self.dynamic_process is not None and self.dynamic_process.is_alive():
                self.dynamic_process.join(timeout=1.0)
                if self.dynamic_process.is_alive():
                    self.dynamic_process.terminate()
        except Exception:
            pass

        self.root.destroy()

    
    def _run_init_main_thread(self):
        """
        Execute static backend initialization directly on the main thread.
        """
        backend = self.backend_var.get()
        try:
            init_plotting(
                backend=backend,
                progressbar_cb=self.update_progress
            )
            
            self._enable_plotting()
            self.init_btn.config(state="normal")
        except Exception as e:
            messagebox.showerror("Initialization Failed!", str(e))
            self.init_btn.config(state="normal")
            self.status_label.config(text="Error.", foreground="red")

    def plot_demo(self):
        """
        Generate a demo plot using either the dynamic worker process
        or the local static backend.
        """
        fig_size = self._get_fig_size()

        if self.backend_var.get() == "dynamic":
            self._ensure_dynamic_worker()

            if not self.dynamic_ready:
                messagebox.showwarning(
                    "Backend not ready",
                    "Initialize the dynamic backend first."
                )
                return

            self.status_label.config(
                text="Sending demo plot command...",
                foreground="blue"
            )
            self.dynamic_command_q.put({
                "action": "demo_plot",
                "fig_size": fig_size,
            })
            return

        self.status_label.config(text="Generating demo plot...", foreground="blue")
        self.root.update_idletasks()

        try:
            init_plotting(backend="static", do_warmup=False)

            X = build_demo_signal()
            fig = eegplot(X, sr=250, block=False, fig_size=fig_size)

            if self._save_static_plot(fig, title="Save demo plot"):
                self.status_label.config(text="Demo plot saved.", foreground="green")

        except Exception as e:
            messagebox.showerror("Plot error", str(e))
            self.status_label.config(text="Error.", foreground="red")
    
    def load_and_plot(self):
        """
        Load an EEG file and plot it using either the dynamic worker
        or the local static backend.
        """
        file_path = filedialog.askopenfilename(
            title="Select EEG file",
            filetypes=[("EEG files", "*.edf *.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return

        fig_size = self._get_fig_size()
        use_stim = self.var_use_stim.get()

        txt_sr = None
        labels_path = None

        if file_path.lower().endswith(".txt"):
            try:
                txt_sr = float(self.entry_sr.get())
            except ValueError:
                messagebox.showerror(
                    "SR Error",
                    "Please enter a valid sampling rate before loading a .txt file."
                )
                return

            load_channels = messagebox.askyesno(
                "Channel Labels",
                "Do you want to load a separate text file containing channel names?",
                parent=self.root
            )

            if load_channels:
                labels_path = filedialog.askopenfilename(
                    title="Select channels file",
                    filetypes=[("Text files", "*.txt")],
                    parent=self.root
                )

        if self.backend_var.get() == "dynamic":
            self._ensure_dynamic_worker()

            if not self.dynamic_ready:
                messagebox.showwarning(
                    "Backend not ready",
                    "Initialize the dynamic backend first."
                )
                return

            self.status_label.config(
                text=f"Sending file to dynamic worker: {os.path.basename(file_path)}",
                foreground="blue"
            )

            self.dynamic_command_q.put({
                "action": "load_plot",
                "file_path": file_path,
                "fig_size": fig_size,
                "use_stim": use_stim,
                "txt_sr": txt_sr,
                "labels_path": labels_path,
            })
            return

        self.status_label.config(
            text=f"Loading {os.path.basename(file_path)}...",
            foreground="blue"
        )
        self.root.update_idletasks()

        try:
            init_plotting(backend="static", do_warmup=False)

            plot_data = load_eeg_file_for_plot(
                file_path,
                use_stim=use_stim,
                txt_sr=txt_sr,
                labels_path=labels_path,
            )

            fig = eegplot(
                plot_data["X"],
                sr=plot_data["sr"],
                X_labels=plot_data["labels"],
                fig_size=fig_size,
                stim=plot_data["stim"],
                stim_labels=plot_data["stim_labels"],
                stim_wl=plot_data["stim_wl"],
                block=False,
            )

            if self._save_static_plot(fig, title="Save file plot"):
                self.status_label.config(
                    text="Plot image saved successfully.",
                    foreground="green"
                )

        except Exception as e:
            messagebox.showerror(
                "Loading Error",
                f"Unable to read the selected file:\n{str(e)}"
            )
            self.status_label.config(text="Error.", foreground="red")

    def _save_static_plot(self, fig, title="Save plot image"): 
        """
        Ask the user for an output path and save the current figure.
        """
        file_path = filedialog.asksaveasfilename(
            title=title,
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )

        if not file_path: 
            self.status_label.config(text="Save cancelled.", foreground="orange")
            return False

        save_figure(fig, file_path)
        return True

if __name__ == "__main__":
    mp.freeze_support()
    root = tk.Tk()
    app = EEGPlotGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()