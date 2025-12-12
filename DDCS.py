import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import numpy as np

class ElectronCountsApp:
    def __init__(self, root):
        """
        Initialize the main GUI application.
        """
        self.root = root
        self.root.title("Electron Counts Calculator")

        # Dictionary to store files for each energy window
        self.energy_windows = {}

        # --- GUI ELEMENTS ---
        self.window_label = tk.Label(root, text="Energy Window Number:")
        self.window_label.pack()
        self.window_entry = tk.Entry(root)
        self.window_entry.pack()

        self.load_measurements_btn = tk.Button(root, text="Load Measurements", command=self.load_measurements)
        self.load_measurements_btn.pack()

        self.load_bkgs_btn = tk.Button(root, text="Load Backgrounds", command=self.load_bkgs)
        self.load_bkgs_btn.pack()

        self.calculate_btn = tk.Button(root, text="Calculate Final", command=self.calculate_final)
        self.calculate_btn.pack()

        self.result_text = tk.Text(root, height=20, width=60)
        self.result_text.pack()

    def get_window_number(self):
        try:
            window_num = int(self.window_entry.get())
            if window_num < 1:
                raise ValueError
            return window_num
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid energy window number (>=1).")
            return None

    # --- DEVIATION CHECK FUNCTION (Average per file, all channels, safe divide) ---
    def check_deviation(self, files, category_name, threshold=0.20):
        """
        Checks if the average channel-wise deviation of each file from the channel-wise average exceeds threshold.
        All channels (1-256) are considered. Channels with average=0 are skipped to avoid division by zero.
        """
        if len(files) < 2:
            return  # No test needed for a single file

        counts_list = []
        for file in files:
            df = pd.read_csv(file, sep=r'\s+', header=None, usecols=[2])
            if len(df) != 256:
                messagebox.showerror("Error", f"File {file} does not have 256 channels.")
                return
            counts_list.append(df[2].values.astype(float))  # ensure float

        counts_array = np.stack(counts_list, axis=1)  # shape: (256, n_files)
        avg_counts = counts_array.mean(axis=1)

        warnings = []
        for i, file_counts in enumerate(counts_list):
            valid_idx = avg_counts != 0  # skip channels where average = 0
            deviation = np.abs(file_counts[valid_idx] - avg_counts[valid_idx]) / avg_counts[valid_idx]
            avg_deviation = np.mean(deviation)
            if avg_deviation > threshold:
                warnings.append(f"{files[i]} (avg deviation: {avg_deviation*100:.1f}%)")

        if warnings:
            messagebox.showwarning(
                "Deviation Warning",
                f"The following {category_name} file(s) have average deviation above {int(threshold*100)}%:\n" +
                "\n".join(warnings)
            )

    # --- FILE LOADING ---
    def load_measurements(self):
        window_num = self.get_window_number()
        if window_num is None:
            return

        files = filedialog.askopenfilenames(title="Select Measurement Files", filetypes=[("Text files", "*.txt")])
        if not files:
            return

        self.energy_windows.setdefault(window_num, {"measurements": [], "bkgs": []})
        self.energy_windows[window_num]["measurements"].extend(files)

        self.check_deviation(self.energy_windows[window_num]["measurements"], "Measurement")

        messagebox.showinfo("Info", f"{len(files)} measurement file(s) loaded for window {window_num}.")

    def load_bkgs(self):
        window_num = self.get_window_number()
        if window_num is None:
            return

        files = filedialog.askopenfilenames(title="Select Background Files", filetypes=[("Text files", "*.txt")])
        if not files:
            return

        self.energy_windows.setdefault(window_num, {"measurements": [], "bkgs": []})
        self.energy_windows[window_num]["bkgs"].extend(files)

        self.check_deviation(self.energy_windows[window_num]["bkgs"], "Background")

        messagebox.showinfo("Info", f"{len(files)} background file(s) loaded for window {window_num}.")

    # --- CHANNEL-WISE SUM FUNCTION ---
    def sum_counts_per_channel(self, files):
        if not files:
            return pd.DataFrame(columns=[0, 2])

        df_total = pd.read_csv(files[0], sep=r'\s+', header=None, usecols=[0, 2])
        df_total.columns = ["Channel", "Counts"]
        df_total["Counts"] = df_total["Counts"].astype(float)

        for file in files[1:]:
            df = pd.read_csv(file, sep=r'\s+', header=None, usecols=[0, 2])
            df.columns = ["Channel", "Counts"]
            df_total["Counts"] += df["Counts"].astype(float)

        return df_total.sort_values("Channel").reset_index(drop=True)

    # --- FINAL CALCULATION ---
    def calculate_final(self):
        self.result_text.delete("1.0", tk.END)

        for window_num, data in self.energy_windows.items():
            sum_measurements = self.sum_counts_per_channel(data["measurements"])
            sum_bkgs = self.sum_counts_per_channel(data["bkgs"])

            final_df = pd.merge(sum_measurements, sum_bkgs, on="Channel", how="outer", suffixes=('_meas', '_bkg')).fillna(0)
            final_df["Final"] = final_df["Counts_meas"] - final_df["Counts_bkg"]

            self.result_text.insert(tk.END, f"Energy Window {window_num}:\n")
            self.result_text.insert(tk.END, f"{'Channel':>10} {'Measurement':>12} {'Background':>12} {'Final':>12}\n")
            for _, row in final_df.iterrows():
                self.result_text.insert(
                    tk.END,
                    f"{int(row['Channel']):>10} {row['Counts_meas']:>12.0f} {row['Counts_bkg']:>12.0f} {row['Final']:>12.0f}\n"
                )
            self.result_text.insert(tk.END, "\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = ElectronCountsApp(root)
    root.mainloop()
