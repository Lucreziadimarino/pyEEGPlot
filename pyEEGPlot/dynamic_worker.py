import traceback
import queue

try:
    from .core import init_plotting, eegplot
    from .data_utils import build_demo_signal, load_eeg_file_for_plot
except ImportError:
    from core import init_plotting, eegplot
    from data_utils import build_demo_signal, load_eeg_file_for_plot


def pump_glmakie_until_closed(
    fig,
    poll_s: float = 0.02,
    teardown_cycles: int = 12,
):
    """
    Keep the GLMakie window responsive while it is open, then
    continue pumping briefly so the backend can shut down cleanly.
    """
    from julia import Main

    Main.fig_to_display = fig
    Main.poll_s = float(poll_s)
    Main.teardown_cycles = int(teardown_cycles)

    Main.eval("""
    begin
        # Serve events while the window is open.
        while true
            yield()
            sleep(poll_s)
            try
                events(fig_to_display).window_open[] || break
            catch
                break
            end
        end

        # Give GLMakie/GLFW time to process the close request.
        for _ in 1:teardown_cycles
            yield()
            sleep(poll_s)
        end

        # Close any remaining windows/screens.
        try
            GLMakie.closeall()
        catch
        end

        # Pump a little longer so shutdown can complete cleanly.
        for _ in 1:teardown_cycles
            yield()
            sleep(poll_s)
        end
    end
    """)

def run_dynamic_worker(command_q, status_q):
    """
    Run a persistent dynamic plotting worker.

    This process stays alive, receives commands from the GUI, initializes
    the dynamic backend once, and reuses the same warm state for subsequent
    dynamic plots.
    """
    initialized = False

    def progress_cb(value, message):
        """
        Forward progress messages from core.init_plotting to the GUI.
        """
        status_q.put({
            "type": "progress",
            "value": int(value),
            "message": str(message),
        })

    while True:
        try:
            cmd = command_q.get(timeout=1.0)
        except queue.Empty: 
            continue

        action = cmd.get("action")

        if action == "quit":
            status_q.put({
                "type": "state",
                "message": "Dynamic worker stopped."
            })
            break

        if action == "initialize":
            initialized = False
            try:
                status_q.put({
                    "type": "state",
                    "message": "Initializing dynamic backend..."
                })

                init_plotting(
                    backend="dynamic",
                    do_warmup=True,
                    progressbar_cb=progress_cb,
                )

                initialized = True
                status_q.put({
                    "type": "ready",
                    "message": "Dynamic backend ready."
                })

            except Exception as e:
                status_q.put({
                    "type": "error",
                    "message": f"{e}\n\n{traceback.format_exc()}"
                })

        elif action == "demo_plot":
            if not initialized:
                status_q.put({
                    "type": "error",
                    "message": "Dynamic backend is not initialized yet."
                })
                continue

            try:
                fig_size = tuple(cmd.get("fig_size", (800, 400)))

                status_q.put({
                    "type": "state",
                    "message": "Opening dynamic demo plot..."
                })

                X = build_demo_signal()

                fig = eegplot(
                    X,
                    sr=250,
                    block=False,
                    fig_size=fig_size,
                    _display=True,
                )

                pump_glmakie_until_closed(fig)

                status_q.put({
                    "type": "state",
                    "message": "Dynamic plot closed."
                })

            except Exception as e:
                status_q.put({
                    "type": "error",
                    "message": f"{e}\n\n{traceback.format_exc()}"
                })

        elif action == "load_plot":
            if not initialized:
                status_q.put({
                    "type": "error",
                    "message": "Dynamic backend is not initialized yet."
                })
                continue

            try:
                file_path = cmd.get("file_path")
                if not file_path:
                    raise ValueError("Missing file_path in load_plot comand.")
                fig_size = tuple(cmd.get("fig_size", (500, 500)))
                use_stim = bool(cmd.get("use_stim", True))
                txt_sr = cmd.get("txt_sr")
                labels_path = cmd.get("labels_path")

                status_q.put({
                    "type": "state",
                    "message": f"Loading file: {file_path}"
                })

                plot_data = load_eeg_file_for_plot(
                    file_path,
                    use_stim=use_stim,
                    txt_sr=txt_sr,
                    labels_path=labels_path,
                )

                status_q.put({
                    "type": "state",
                    "message": "Opening dynamic plot..."
                })

                fig = eegplot(
                    plot_data["X"],
                    sr=plot_data["sr"],
                    X_labels=plot_data["labels"],
                    fig_size=fig_size,
                    stim=plot_data["stim"],
                    stim_labels=plot_data["stim_labels"],
                    stim_wl=plot_data["stim_wl"],
                    block=False,
                    _display=True,
                )

                pump_glmakie_until_closed(fig)

                status_q.put({
                    "type": "state",
                    "message": "Dynamic plot closed."
                })

            except Exception as e:
                status_q.put({
                    "type": "error",
                    "message": f"{e}\n\n{traceback.format_exc()}"
                })

