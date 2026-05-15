from __future__ import annotations

import sys
from typing import Optional

import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from tsc_rzip_rllib.core.coil_order import (
    DISPLAY_NAME_TO_INDEX,
    TSC_NAME_TO_INDEX,
    tsc_to_display,
)
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner


COIL_PAIR_GROUPS = [
    ("CS1", ["CS1U", "CS1L"]),
    ("CS2", ["CS2U", "CS2L"]),
    ("CS3", ["CS3U", "CS3L"]),
    ("CS4", ["CS4U", "CS4L"]),
    ("PF2", ["PF2U", "PF2L"]),
    ("PF3", ["PF3U", "PF3L"]),
    ("PF4", ["PF4U", "PF4L"]),
]


class OneEpisodeWorker(QThread):
    result = pyqtSignal(dict)
    failed = pyqtSignal(str)
    finished_ok = pyqtSignal()

    def __init__(self, cfg: TSCConfig, target: np.ndarray, kp: np.ndarray, max_steps: int):
        super().__init__()
        self.cfg = cfg
        self.target = target
        self.kp = kp
        self.max_steps = int(max_steps)
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            runner = TSCStepRunner(self.cfg)

            state = runner.reset()
            zero_command_a_tsc = np.zeros(14, dtype=float)
            history = self._pack_history(
                [],
                state,
                reward=0.0,
                command_delta_a_tsc=zero_command_a_tsc,
            )
            self.result.emit(history)

            for _ in range(self.max_steps):
                if self._stop:
                    break

                err = np.array(
                    [
                        self.target[0] - state["R"],
                        self.target[1] - state["Z"],
                        (self.target[2] - state["Ip"]) / 3.0e4,
                    ],
                    dtype=float,
                )

                # 单匝电流变化量命令，单位 A，TSC 顺序。
                # 这里只是可视化验证用的 sanity controller；
                # 真实 RL 时会由 policy 输出 action。
                command_delta_a_tsc = np.zeros(14, dtype=float)

                # R: PF3/PF4 上下对称 common-mode 试探。
                for name in ["PF3U", "PF3L", "PF4U", "PF4L"]:
                    command_delta_a_tsc[TSC_NAME_TO_INDEX[name]] += self.kp[0] * err[0]

                # Z: PF3/PF4 上下反对称试探。
                for upper, lower in [("PF3U", "PF3L"), ("PF4U", "PF4L")]:
                    command_delta_a_tsc[TSC_NAME_TO_INDEX[upper]] += self.kp[1] * err[1]
                    command_delta_a_tsc[TSC_NAME_TO_INDEX[lower]] -= self.kp[1] * err[1]

                # Ip: CS common-mode 试探。
                for name in [
                    "CS1U", "CS2U", "CS3U",
                    "CS1L", "CS2L", "CS3L",
                    "CS4U", "CS4L",
                ]:
                    command_delta_a_tsc[TSC_NAME_TO_INDEX[name]] += self.kp[2] * err[2]

                # 裁剪后再记录，这样“命令变化量图”显示的是实际送给 runner 的命令。
                max_delta = runner.max_delta_current_a_per_step
                command_delta_a_tsc = np.clip(command_delta_a_tsc, -max_delta, max_delta)

                state = runner.step_delta_current_a(command_delta_a_tsc)

                reward = -float(np.sum(err**2))
                history = self._pack_history(
                    history,
                    state,
                    reward=reward,
                    command_delta_a_tsc=command_delta_a_tsc,
                )
                self.result.emit(history)

                if state.get("abnormal", False):
                    break

            self.finished_ok.emit()

        except Exception as exc:
            self.failed.emit(str(exc))

    def _pack_history(self, history, state, reward: float, command_delta_a_tsc: np.ndarray):
        if isinstance(history, list):
            hist = {
                "time_ms": [],
                "R": [],
                "Z": [],
                "Ip": [],

                # display order, 单匝电流 A
                "currents_a_display": [],

                # display order, 每一步命令变化量 A
                "command_delta_a_display": [],

                # TSC-side kA-turn，仅保留给后续调试，不默认画
                "currents_kat_display": [],

                "reward": [],
                "psi": None,
                "rr": None,
                "zz": None,
            }
        else:
            hist = history

        hist["time_ms"].append(state["time_ms"])
        hist["R"].append(state["R"])
        hist["Z"].append(state["Z"])
        hist["Ip"].append(state["Ip"])

        hist["currents_a_display"].append(state["currents_a_display"])
        hist["command_delta_a_display"].append(tsc_to_display(command_delta_a_tsc))
        hist["currents_kat_display"].append(state["currents_kat_display"])

        hist["reward"].append(reward)

        hist["psi"] = state["gfile"]["psiaux"]
        hist["rr"] = state["gfile"]["rr"]
        hist["zz"] = state["gfile"]["zz"]

        return hist


class TSCVisualizer(QWidget):
    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("TSC RZIP RL visual sanity check")
        self.worker: Optional[OneEpisodeWorker] = None
        self.config_path = config_path
        self._init_ui()

        if config_path:
            self.config_edit.setText(config_path)

    def _init_ui(self):
        layout = QVBoxLayout(self)

        top = QGridLayout()

        self.config_edit = QLineEdit("")
        browse = QPushButton("选择 config JSON")
        browse.clicked.connect(self._browse)

        top.addWidget(QLabel("TSC/RL config:"), 0, 0)
        top.addWidget(self.config_edit, 0, 1)
        top.addWidget(browse, 0, 2)

        self.r_edit = QLineEdit("0.75")
        self.z_edit = QLineEdit("0.0")
        self.ip_edit = QLineEdit("30000")
        self.steps_edit = QLineEdit("20")

        # sanity controller 参数。
        # runner 内部还会按 current_slew_a_per_ms 限制每步变化量。
        self.kpr_edit = QLineEdit("3000.0")
        self.kpz_edit = QLineEdit("3000.0")
        self.kpip_edit = QLineEdit("100.0")

        items = [
            ("target R [m]", self.r_edit),
            ("target Z [m]", self.z_edit),
            ("target Ip [A]", self.ip_edit),
            ("steps", self.steps_edit),
            ("Kp_R [A/m]", self.kpr_edit),
            ("Kp_Z [A/m]", self.kpz_edit),
            ("Kp_Ip [A]", self.kpip_edit),
        ]

        for col, (name, widget) in enumerate(items):
            top.addWidget(QLabel(name), 1, col)
            top.addWidget(widget, 2, col)

        buttons = QHBoxLayout()
        self.run_btn = QPushButton("Reset + run one episode")
        self.stop_btn = QPushButton("Stop")

        self.run_btn.clicked.connect(self.run_episode)
        self.stop_btn.clicked.connect(self.stop_episode)

        buttons.addWidget(self.run_btn)
        buttons.addWidget(self.stop_btn)

        self.fig = Figure(figsize=(18, 12), constrained_layout=True)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.updateGeometry()

        layout.addLayout(top)
        layout.addLayout(buttons)
        layout.addWidget(self.canvas, stretch=1)

        self.setMinimumSize(1200, 800)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择配置", "", "JSON (*.json)")
        if path:
            self.config_edit.setText(path)

    def run_episode(self):
        try:
            cfg = TSCConfig.from_json(self.config_edit.text())

            target = np.array(
                [
                    float(self.r_edit.text()),
                    float(self.z_edit.text()),
                    float(self.ip_edit.text()),
                ],
                dtype=float,
            )

            kp = np.array(
                [
                    float(self.kpr_edit.text()),
                    float(self.kpz_edit.text()),
                    float(self.kpip_edit.text()),
                ],
                dtype=float,
            )

            max_steps = int(self.steps_edit.text())

            self.worker = OneEpisodeWorker(cfg, target, kp, max_steps)
            self.worker.result.connect(self.update_plots)
            self.worker.failed.connect(self.on_failed)
            self.worker.finished_ok.connect(lambda: self.run_btn.setEnabled(True))

            self.run_btn.setEnabled(False)
            self.worker.start()

        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def stop_episode(self):
        if self.worker:
            self.worker.stop()

    def on_failed(self, msg: str):
        self.run_btn.setEnabled(True)
        QMessageBox.critical(self, "TSC run failed", msg)

    def _plot_pair_group(
        self,
        ax,
        names: list[str],
        t: np.ndarray,
        data_display: np.ndarray,
        ylabel: str,
        show_xlabel: bool = False,
    ):
        for name in names:
            j = DISPLAY_NAME_TO_INDEX[name]
            ax.plot(t, data_display[:, j], lw=1.2, label=name)

        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc="best")

        if show_xlabel:
            ax.set_xlabel("time [ms]")
        else:
            ax.tick_params(labelbottom=False)

    def _make_column_title(self, grid_spec, title: str):
        ax_title = self.fig.add_subplot(grid_spec)
        ax_title.set_axis_off()
        ax_title.text(
            0.5,
            0.5,
            title,
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            transform=ax_title.transAxes,
        )
        return ax_title

    def update_plots(self, hist: dict):
        self.fig.clear()

        t = np.asarray(hist["time_ms"], dtype=float)
        currents_a_display = np.asarray(hist["currents_a_display"], dtype=float)
        command_delta_a_display = np.asarray(hist["command_delta_a_display"], dtype=float)

        # 15 rows:
        #   row 0      : column titles
        #   rows 1-14 : actual plots
        #
        # Left/middle columns:
        #   7 coil groups, each group spans 2 rows.
        #
        # Right column:
        #   R   rows 1:4   -> 3 units
        #   Z   rows 4:7   -> 3 units
        #   Ip  rows 7:10  -> 3 units
        #   psi rows 10:15 -> 5 units
        #
        # This gives 3:3:3:5 = 1.5:1.5:1.5:2.5.
        gs = self.fig.add_gridspec(
            nrows=15,
            ncols=3,
            width_ratios=[1.15, 1.15, 1.35],
            height_ratios=[0.42] + [1.0] * 14,
            wspace=0.25,
            hspace=0.55,
        )

        # ========= column title axes =========
        self._make_column_title(gs[0, 0], "CSPF Single-Turn Currents")
        self._make_column_title(gs[0, 1], "CSPF Current Command Increments")
        self._make_column_title(
            gs[0, 2],
            "TSC-Derived Plasma Position, Current, and Poloidal Flux",
        )

        # ========= column 1: CSPF single-turn currents =========
        share_current_ax = None

        for i, (_, names) in enumerate(COIL_PAIR_GROUPS):
            row0 = 1 + 2 * i
            row1 = row0 + 2

            ax = self.fig.add_subplot(gs[row0:row1, 0], sharex=share_current_ax)
            if share_current_ax is None:
                share_current_ax = ax

            self._plot_pair_group(
                ax=ax,
                names=names,
                t=t,
                data_display=currents_a_display,
                ylabel="I [A]",
                show_xlabel=(i == len(COIL_PAIR_GROUPS) - 1),
            )

        # ========= column 2: current command increments =========
        share_command_ax = None

        for i, (_, names) in enumerate(COIL_PAIR_GROUPS):
            row0 = 1 + 2 * i
            row1 = row0 + 2

            ax = self.fig.add_subplot(gs[row0:row1, 1], sharex=share_command_ax)
            if share_command_ax is None:
                share_command_ax = ax

            self._plot_pair_group(
                ax=ax,
                names=names,
                t=t,
                data_display=command_delta_a_display,
                ylabel="ΔI [A]",
                show_xlabel=(i == len(COIL_PAIR_GROUPS) - 1),
            )

        # ========= column 3: R / Z / Ip / psi =========
        ax_r = self.fig.add_subplot(gs[1:4, 2])
        ax_z = self.fig.add_subplot(gs[4:7, 2], sharex=ax_r)
        ax_ip = self.fig.add_subplot(gs[7:10, 2], sharex=ax_r)
        ax_psi = self.fig.add_subplot(gs[10:15, 2])

        ax_r.plot(t, hist["R"], label="R")
        ax_r.set_ylabel("R [m]")
        ax_r.grid(True, alpha=0.3)
        ax_r.legend(fontsize=8, loc="best")
        ax_r.tick_params(labelbottom=False)

        ax_z.plot(t, hist["Z"], label="Z")
        ax_z.set_ylabel("Z [m]")
        ax_z.grid(True, alpha=0.3)
        ax_z.legend(fontsize=8, loc="best")
        ax_z.tick_params(labelbottom=False)

        ax_ip.plot(t, hist["Ip"], label="Ip")
        ax_ip.set_ylabel("Ip [A]")
        ax_ip.grid(True, alpha=0.3)
        ax_ip.legend(fontsize=8, loc="best")

        # 避免 Ip 的横坐标和 psi 图挤在一起：
        # 保留 Ip 的 x tick，但不写 xlabel，并把 tick label 靠近轴线。
        ax_ip.set_xlabel("")
        ax_ip.tick_params(axis="x", labelsize=8, pad=1)

        rr, zz, psi = hist["rr"], hist["zz"], hist["psi"]
        ax_psi.contour(rr, zz, psi, levels=60)
        ax_psi.set_aspect("equal", adjustable="box")
        ax_psi.set_xlabel("R [m]")
        ax_psi.set_ylabel("Z [m]")

        self.canvas.draw_idle()


def main():
    app = QApplication(sys.argv)
    config_path = sys.argv[1] if len(sys.argv) > 1 else None

    window = TSCVisualizer(config_path=config_path)
    window.resize(1800, 1200)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()