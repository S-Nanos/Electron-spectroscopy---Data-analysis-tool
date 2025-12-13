import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
import os

class DDCS_GUI:

    def __init__(self, root):
        self.root = root
        self.root.title("DDCS Analysis Tool")

        # Storage per window
        self.measurements = defaultdict(list)
        self.backgrounds = defaultdict(list)

        self.current_window = tk.StringVar(value="1")

        self.build_gui()

    # ---------------- GUI ---------------- #

    def build_gui(self):
        main = tk.Frame(self.root, padx=10, pady=10)
        main.pack(fill="both", expand=True)

        tk.Label(main, text="Energy window:").grid(row=0, column=0, sticky="w")
        tk.Entry(main, textvariable=self.current_window, width=5).grid(row=0, column=1, sticky="w")

        tk.Button(main, text="Load measurements", command=self.load_measurements).grid(row=1, column=0, pady=5)
        tk.Button(main, text="Load backgrounds", command=self.load_backgrounds).grid(row=1, column=1, pady=5)

        tk.Label(main, text="Measurements:").grid(row=2, column=0, sticky="w")
        tk.Label(main, text="Backgrounds:").grid(row=2, column=1, sticky="w")

        meas_frame = tk.Frame(main)
        bkg_frame = tk.Frame(main)

        meas_frame.grid(row=3, column=0, sticky="nsew")
        bkg_frame.grid(row=3, column=1, sticky="nsew")

        # Measurement listbox
        self.meas_list = tk.Listbox(meas_frame, width=45, height=6)
        meas_vscroll = tk.Scrollbar(meas_frame, orient="vertical", command=self.meas_list.yview)
        meas_hscroll = tk.Scrollbar(meas_frame, orient="horizontal", command=self.meas_list.xview)

        self.meas_list.configure(
            yscrollcommand=meas_vscroll.set,
            xscrollcommand=meas_hscroll.set
        )

        self.meas_list.grid(row=0, column=0, sticky="nsew")
        meas_vscroll.grid(row=0, column=1, sticky="ns")
        meas_hscroll.grid(row=1, column=0, sticky="ew")

        # Background listbox
        self.bkg_list = tk.Listbox(bkg_frame, width=45, height=6)
        bkg_vscroll = tk.Scrollbar(bkg_frame, orient="vertical", command=self.bkg_list.yview)
        bkg_hscroll = tk.Scrollbar(bkg_frame, orient="horizontal", command=self.bkg_list.xview)

        self.bkg_list.configure(
            yscrollcommand=bkg_vscroll.set,
            xscrollcommand=bkg_hscroll.set
        )

        self.bkg_list.grid(row=0, column=0, sticky="nsew")
        bkg_vscroll.grid(row=0, column=1, sticky="ns")
        bkg_hscroll.grid(row=1, column=0, sticky="ew")

        # Allow resizing
        meas_frame.grid_columnconfigure(0, weight=1)
        bkg_frame.grid_columnconfigure(0, weight=1)


        tk.Button(main, text="Remove selected", command=self.remove_measurement).grid(row=4, column=0)
        tk.Button(main, text="Remove selected", command=self.remove_background).grid(row=4, column=1)

        # Plot options
        self.plot_opts = {
            "meas_ind": tk.BooleanVar(),
            "bkg_ind": tk.BooleanVar(),
            "meas_sum": tk.BooleanVar(),
            "bkg_sum": tk.BooleanVar(),
            "final": tk.BooleanVar()
        }

        plot_frame = tk.LabelFrame(main, text="Plot options", padx=10, pady=5)
        plot_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky="w")

        tk.Checkbutton(plot_frame, text="Measurements (individual)", variable=self.plot_opts["meas_ind"]).grid(sticky="w")
        tk.Checkbutton(plot_frame, text="Backgrounds (individual)", variable=self.plot_opts["bkg_ind"]).grid(sticky="w")
        tk.Checkbutton(plot_frame, text="Sum measurements", variable=self.plot_opts["meas_sum"]).grid(sticky="w")
        tk.Checkbutton(plot_frame, text="Sum backgrounds", variable=self.plot_opts["bkg_sum"]).grid(sticky="w")
        tk.Checkbutton(plot_frame, text="Final (meas - bkg)", variable=self.plot_opts["final"]).grid(sticky="w")

        tk.Button(main, text="Plot", command=self.plot_window).grid(row=6, column=0, pady=5)
        tk.Button(main, text="Calculate final", command=self.calculate_final).grid(row=6, column=1, pady=5)

        self.result_box = tk.Text(main, width=110, height=12)
        self.result_box.grid(row=7, column=0, columnspan=2, pady=10)

        tk.Button(main, text="Save final to TXT", command=self.save_final).grid(row=8, column=0, columnspan=2)

        self.current_window.trace_add("write", lambda *_: self.update_lists())

    # ---------------- File handling ---------------- #

    def get_window(self):
        try:
            return int(self.current_window.get())
        except ValueError:
            return None

    def load_measurements(self):
        self._load_files(self.measurements, self.meas_list, "Measurements")

    def load_backgrounds(self):
        self._load_files(self.backgrounds, self.bkg_list, "Backgrounds")

    def _load_files(self, store, listbox, label):
        window = self.get_window()
        if window is None:
            return

        files = filedialog.askopenfilenames(filetypes=[("Text files", "*.txt")])
        if not files:
            return

        store[window].extend(files)
        self.update_lists()
        self.consistency_check(store[window], label)

    def update_lists(self):
        window = self.get_window()
        if window is None:
            return

        self.meas_list.delete(0, tk.END)
        self.bkg_list.delete(0, tk.END)

        for f in self.measurements.get(window, []):
            self.meas_list.insert(tk.END, os.path.basename(f))

        for f in self.backgrounds.get(window, []):
            self.bkg_list.insert(tk.END, os.path.basename(f))


    def remove_measurement(self):
        self._remove_selected(self.measurements, self.meas_list)

    def remove_background(self):
        self._remove_selected(self.backgrounds, self.bkg_list)

    def _remove_selected(self, store, listbox):
        window = self.get_window()
        if window is None:
            return

        sel = listbox.curselection()
        for i in reversed(sel):
            store[window].pop(i)

        self.update_lists()

    # ---------------- Core logic ---------------- #

    def read_counts(self, file):
        df = pd.read_csv(file, sep=r'\s+', header=None, engine='python')
        return df.iloc[:, 2].values

    def sum_spectra(self, files):
        spectra = np.array([self.read_counts(f) for f in files])
        return spectra.sum(axis=0)

    def consistency_check(self, files, label, threshold=0.05):
        if len(files) < 2:
            return

        spectra = np.array([self.read_counts(f) for f in files])
        avg = spectra.mean(axis=0)

        deviations = []
        for s in spectra:
            valid = avg != 0
            rel = np.zeros_like(avg, dtype=float)
            rel[valid] = np.abs(s[valid] - avg[valid]) / avg[valid]
            deviations.append(rel.mean())

        for i, d in enumerate(deviations):
            if d > threshold:
                messagebox.showwarning(
                    "Consistency warning",
                    f"{label} file:\n{files[i]}\n\nAverage deviation = {d*100:.1f}%"
                )

    # ---------------- Plotting ---------------- #

    def plot_window(self):
        window = self.get_window()
        if window is None:
            return

        if not any(v.get() for v in self.plot_opts.values()):
            messagebox.showwarning("Plot warning", "No plot option selected.")
            return

        plt.figure()

        if self.plot_opts["meas_ind"].get():
            for f in self.measurements.get(window, []):
                plt.plot(self.read_counts(f), alpha=0.4)

        if self.plot_opts["bkg_ind"].get():
            for f in self.backgrounds.get(window, []):
                plt.plot(self.read_counts(f), alpha=0.4)

        if self.plot_opts["meas_sum"].get() and self.measurements.get(window):
            plt.plot(self.sum_spectra(self.measurements[window]), label="Sum measurements")

        if self.plot_opts["bkg_sum"].get() and self.backgrounds.get(window):
            plt.plot(self.sum_spectra(self.backgrounds[window]), label="Sum backgrounds")

        if self.plot_opts["final"].get():
            if not self.measurements.get(window) or not self.backgrounds.get(window):
                messagebox.showwarning("Plot warning", "Missing measurements or backgrounds.")
                return
            final = self.sum_spectra(self.measurements[window]) - self.sum_spectra(self.backgrounds[window])
            plt.plot(final, label="Final")

        plt.legend()
        plt.xlabel("Channel")
        plt.ylabel("Counts")
        plt.title(f"Energy window {window}")
        plt.show()

    # ---------------- Final calculation ---------------- #

    def calculate_final(self):
        window = self.get_window()
        if window is None:
            return

        if not self.measurements.get(window) or not self.backgrounds.get(window):
            messagebox.showwarning("Calculation warning", "Measurements or backgrounds missing.")
            return

        meas_sum = self.sum_spectra(self.measurements[window])
        bkg_sum = self.sum_spectra(self.backgrounds[window])
        final = meas_sum - bkg_sum

        # NEW: safe average relative difference (no warnings)
        valid = meas_sum != 0
        rel = np.zeros_like(meas_sum, dtype=float)
        rel[valid] = (meas_sum[valid] - bkg_sum[valid]) / meas_sum[valid]
        avg_rel_diff = np.mean(rel)

        if avg_rel_diff < 0:
            messagebox.showwarning("Warning", "Measurements ≤ background on average.")
        elif avg_rel_diff < 0.1:
            messagebox.showwarning("Warning", "Measurements only slightly above background.")

        self.last_result = np.column_stack([
            np.arange(1, len(final)+1),
            meas_sum,
            bkg_sum,
            final
        ])

        self.result_box.delete("1.0", tk.END)
        self.result_box.insert(tk.END, "Channel   Sum_meas   Sum_bkg   Final\n")
        for row in self.last_result:
            self.result_box.insert(tk.END, f"{int(row[0]):6d} {row[1]:10.1f} {row[2]:10.1f} {row[3]:10.1f}\n")

    def save_final(self):
        if not hasattr(self, "last_result"):
            messagebox.showwarning("Save warning", "No result to save.")
            return

        fname = filedialog.asksaveasfilename(defaultextension=".txt")
        if fname:
            np.savetxt(
                fname,
                self.last_result,
                fmt=["%d", "%.6f", "%.6f", "%.6f"],
                header="Channel Sum_measurements Sum_backgrounds Final",
                comments=""
            )

# ---------------- Run ---------------- #

if __name__ == "__main__":
    root = tk.Tk()
    app = DDCS_GUI(root)
    root.mainloop()
