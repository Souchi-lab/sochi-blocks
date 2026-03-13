#!/usr/bin/env python3
"""
SoChi BLOCKS — Puzzle Video Generator

パズルを解く様子のMP4動画を自動生成します。
縦動画 (9:16, 1080×1920) で出力します。

使い方:
  python generate_puzzle_video.py 20260304_001
  python generate_puzzle_video.py 20260304_001 --output /path/to/output.mp4
  python generate_puzzle_video.py 20260304_001 --hook "Can YOU do it?"

必要なもの:
  pip install matplotlib numpy
  ffmpeg (システムインストール: https://ffmpeg.org/)
"""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend (no display required)
import matplotlib.pyplot as plt
import numpy as np

# ── 動画設定 ──────────────────────────────────────────────────────
FPS = 30
WIDTH = 1080
HEIGHT = 1920
DPI = 100

# ── アニメーション設定 ────────────────────────────────────────────
FLOAT_HEIGHT = 3.5    # パズル上空の浮遊高さ (ボクセル単位)
BOB_AMPLITUDE = 0.45  # ふわふわ振幅 (ボクセル単位)
BOB_CYCLES = 2.0      # 浮遊中のぼよんぼよん回数
AZIM_SWEEP_DEG = 12.0 # 浮遊中の通常カメラスイング±幅 (度)
HESITATE_DROP = 0.45  # Hesitation 最大降下率 (0=浮遊高さ, 1=着地)

# ── 難易度テーブル ────────────────────────────────────────────────
# n_pieces → 設定辞書 (範囲外は get_difficulty() が最近傍を返す)
DIFFICULTY_TABLE = {
    2: dict(h_frames=0,  hesitate_azim=12,  hesitate_n=0, misplace_indices=[],    label="EASY",   hook="Can you solve this?"),
    3: dict(h_frames=24, hesitate_azim=35,  hesitate_n=1, misplace_indices=[1],   label="MEDIUM", hook="Think you can solve this?"),
    4: dict(h_frames=24, hesitate_azim=35,  hesitate_n=1, misplace_indices=[1],   label="MEDIUM", hook="Think you can solve this?"),
    5: dict(h_frames=16, hesitate_azim=52,  hesitate_n=1, misplace_indices=[1,3], label="HARD",   hook="Only the sharpest can solve this."),
    6: dict(h_frames=16, hesitate_azim=70,  hesitate_n=1, misplace_indices=[1,3], label="HARD",   hook="Only the sharpest can solve this."),
}

def get_difficulty(n_pieces: int) -> dict:
    """n_pieces が範囲外なら最近傍の設定を使う。"""
    if n_pieces in DIFFICULTY_TABLE:
        return DIFFICULTY_TABLE[n_pieces]
    return DIFFICULTY_TABLE[max(DIFFICULTY_TABLE)]

# ── フェーズ別フレーム数 ──────────────────────────────────────────
INTRO_FRAMES             = 30   # 1.0s: パズル即表示 + フックテキスト
FLOAT_FRAMES             = 30   # 1.0s / ピース: 浮遊・3Dスイング
MISPLACE_SNAP_FRAMES     = 15   # 0.5s: 誤った位置にスナップ
MISPLACE_PAUSE_FRAMES    =  6   # 0.2s: 誤配置静止 (赤フラッシュ + ✗アイコン)
MISPLACE_RETRACT_FRAMES  = 15   # 0.5s: 「やっぱり違う！」で引き剥がし
SNAP_FRAMES              = 18   # 0.6s / ピース: バウンス着地
SETTLE_FRAMES            = 12   # 0.4s / ピース: 着地後静止 (白フラッシュ強化)
VICTORY_FRAMES           = 45   # 1.5s: 完成演出 + ★カウントアップ

# ── 色・デザイン ──────────────────────────────────────────────────
BG_COLOR    = "#0d1117"
TEXT_COLOR  = "#e6edf3"
ACCENT_COLOR = "#58a6ff"
GOLD_COLOR  = "#ffd700"
ERROR_COLOR = "#ff4c4c"   # 誤配置フラッシュ色

# ピースID → 絵文字 (シェアテキスト用)
PIECE_EMOJI: dict[str, str] = {
    "F": "⬜", "I": "🟦", "L": "🟧", "P": "🟥",
    "N": "🟪", "T": "🟩", "U": "🟨", "V": "🩵",
    "W": "💚", "X": "🔴", "Y": "🟫", "Z": "🔵",
}


# ── ユーティリティ ────────────────────────────────────────────────

def find_project_root() -> Path:
    """frontend/ ディレクトリを含むプロジェクトルートを探す。"""
    p = Path(__file__).resolve()
    for candidate in [p.parent, p.parent.parent, p.parent.parent.parent]:
        if (candidate / "frontend").exists():
            return candidate
    raise FileNotFoundError(
        "プロジェクトルート (frontend/ を含むディレクトリ) が見つかりません。"
    )


def load_puzzle(puzzle_id: str) -> dict:
    root = find_project_root()
    path = root / "frontend" / "public" / "puzzles" / f"puzzle_{puzzle_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"パズルファイルが見つかりません: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_piece_colors() -> dict[str, str]:
    root = find_project_root()
    path = root / "frontend" / "public" / "colors" / "piece_colors.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def hex_to_rgba(hex_color: str, alpha: float = 0.92) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (r, g, b, alpha)


def smoothstep(t: float) -> float:
    """スムーズイージング (0〜1 の範囲でクランプ)。"""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def bounce_ease_out(t: float) -> float:
    """行き過ぎ→戻りのバウンスイージング (SNAPフェーズ用)。"""
    t = max(0.0, min(1.0, t))
    overshoot = 1.06
    if t < 0.82:
        return smoothstep(t / 0.82) * overshoot
    else:
        s = (t - 0.82) / 0.18
        return overshoot - (overshoot - 1.0) * smoothstep(s)


def get_piece_cells(puzzle: dict, piece_id: str) -> list[tuple[int, int, int]]:
    return [(c["x"], c["y"], c["z"]) for c in puzzle["cells"] if c["piece"] == piece_id]


def compute_misplace_offset(puzzle: dict, piece_id: str) -> tuple[int, int]:
    """ピースを安全にずらせるオフセット (dx, dy) を計算。"""
    cells = get_piece_cells(puzzle, piece_id)
    gx = puzzle["grid"]["x"]
    gy = puzzle["grid"]["y"]
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        if all(0 <= cx + dx < gx and 0 <= cy + dy < gy for (cx, cy, _) in cells):
            return (dx, dy)
    return (1, 0)  # フォールバック


def difficulty_stars(n: int) -> str:
    n = max(1, min(5, n))
    return "★" * n + "☆" * (5 - n)


# ── ボクセル描画 ──────────────────────────────────────────────────

def _gz_ext(gz: int) -> int:
    """浮遊ピース用の上方向余白を加えた Z 方向グリッドサイズ。"""
    return gz + int(math.ceil(FLOAT_HEIGHT + BOB_AMPLITUDE + 2))


def build_voxel_arrays(
    puzzle: dict,
    piece_colors: dict,
    placed: set[str],
    float_piece: str | None = None,
    float_z_offset: float = 0.0,
    float_xy_offset: tuple[int, int] = (0, 0),
) -> tuple[np.ndarray, np.ndarray]:
    """
    ax.voxels() 用の filled / facecolors 配列を構築する。

    float_xy_offset: (dx, dy) — MISPLACEフェーズでピースをずらす際に使用。
    """
    gx = puzzle["grid"]["x"]
    gy = puzzle["grid"]["y"]
    gz = puzzle["grid"]["z"]
    gz_e = _gz_ext(gz)
    removed_set = set(puzzle.get("removed_pieces", []))

    filled = np.zeros((gx, gy, gz_e), dtype=bool)
    fc = np.zeros((gx, gy, gz_e, 4), dtype=float)

    def place(x: int, y: int, z: int, color_hex: str, alpha: float = 0.92):
        if 0 <= x < gx and 0 <= y < gy and 0 <= z < gz_e:
            filled[x, y, z] = True
            fc[x, y, z] = hex_to_rgba(color_hex, alpha)

    # 固定ピース
    for cell in puzzle["cells"]:
        pid = cell["piece"]
        if pid not in removed_set:
            place(cell["x"], cell["y"], cell["z"], piece_colors.get(pid, "#888888"))

    # 配置済みの削除ピース
    for cell in puzzle["cells"]:
        pid = cell["piece"]
        if pid in removed_set and pid in placed:
            place(cell["x"], cell["y"], cell["z"], piece_colors.get(pid, "#888888"))

    # 浮遊中 / 誤配置中のピース
    if float_piece is not None:
        color_hex = piece_colors.get(float_piece, "#888888")
        dx, dy = float_xy_offset
        for (cx, cy, cz) in get_piece_cells(puzzle, float_piece):
            rz = int(round(cz + float_z_offset))
            place(cx + dx, cy + dy, rz, color_hex, alpha=0.82)

    return filled, fc


def setup_axes(ax, gx: int, gy: int, gz: int, azim: float = 225.0):
    """3D軸を毎フレームのデフォルト設定にリセットする。"""
    gz_e = _gz_ext(gz)
    ax.set_facecolor(BG_COLOR)
    ax.set_xlim(0, gx)
    ax.set_ylim(0, gy)
    ax.set_zlim(0, gz_e)
    ax.set_box_aspect([gx, gy, gz_e * 0.55])
    ax.axis("off")
    ax.view_init(elev=28, azim=azim)
    try:
        ax.set_proj_type("persp")
        ax.dist = 9
    except AttributeError:
        pass


def render_voxels(ax, filled: np.ndarray, fc: np.ndarray):
    if not filled.any():
        return
    ec = fc.copy()
    ec[..., :3] = np.clip(fc[..., :3] * 0.55, 0, 1)
    ax.voxels(filled, facecolors=fc, edgecolors=ec, shade=True)


# ── テキストオーバーレイ管理 ──────────────────────────────────────

class TextOverlay:
    """fig.text() で追加したテキストを一括管理・削除するヘルパー。"""

    def __init__(self, fig):
        self.fig = fig
        self._texts: list = []

    def add(self, x: float, y: float, s: str, **kwargs):
        t = self.fig.text(x, y, s, **kwargs)
        self._texts.append(t)
        return t

    def clear(self):
        for t in self._texts:
            try:
                t.remove()
            except Exception:
                pass
        self._texts.clear()


# ── ffmpeg パイプ ──────────────────────────────────────────────────

def find_ffmpeg() -> str:
    """
    ffmpeg バイナリを探す。優先順位:
      1. システムPATH上の ffmpeg
      2. frontend/node_modules/ffmpeg-static/ffmpeg.exe (npm パッケージ)
    """
    import shutil
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    root = find_project_root()
    candidates = [
        root / "frontend" / "node_modules" / "ffmpeg-static" / "ffmpeg.exe",
        root / "frontend" / "node_modules" / "ffmpeg-static" / "ffmpeg",
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    raise FileNotFoundError(
        "ffmpeg が見つかりません。\n"
        "  システムにインストールするか (https://ffmpeg.org/)、\n"
        "  または frontend/ ディレクトリで `npm install` を実行してください。"
    )


def open_ffmpeg(output_path: str) -> subprocess.Popen:
    """ffmpegプロセスを起動し、標準入力にRAWフレームを受け取る。"""
    ffmpeg_bin = find_ffmpeg()
    cmd = [
        ffmpeg_bin, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS),
        "-i", "pipe:0",
        "-vcodec", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "23",
        "-preset", "fast",
        output_path,
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)


def frame_to_bytes(fig) -> bytes:
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())  # (H, W, 4)
    return buf[:, :, :3].tobytes()


# ── メインの動画生成 ──────────────────────────────────────────────

def generate_video(
    puzzle: dict,
    piece_colors: dict,
    output_path: str,
    hook_override: str | None = None,
):
    removed: list[str] = puzzle.get("removed_pieces", [])
    if not removed:
        print("警告: removed_pieces が空です。固定ピースのみで動画を生成します。")

    gx = puzzle["grid"]["x"]
    gy = puzzle["grid"]["y"]
    gz = puzzle["grid"]["z"]

    n_pieces = len(removed)
    diff = get_difficulty(n_pieces)
    h_frames          = diff["h_frames"]
    hesitate_n        = diff["hesitate_n"]
    hesitate_azim     = diff["hesitate_azim"]
    misplace_indices  = set(diff["misplace_indices"])
    diff_label        = diff["label"]
    hook_text         = hook_override or diff["hook"]

    # ── 総フレーム数計算 ──────────────────────────────────────────
    hesitate_total = max(0, n_pieces - 1) * hesitate_n * h_frames
    n_misplace = len([i for i in misplace_indices if i < n_pieces])
    misplace_total = n_misplace * (
        MISPLACE_SNAP_FRAMES + MISPLACE_PAUSE_FRAMES + MISPLACE_RETRACT_FRAMES
    )
    per_piece_base = FLOAT_FRAMES + SNAP_FRAMES + SETTLE_FRAMES
    total_frames = (
        INTRO_FRAMES
        + n_pieces * per_piece_base
        + hesitate_total
        + misplace_total
        + VICTORY_FRAMES
    )
    total_secs = total_frames / FPS
    print(f"  難易度: {diff_label} / ピース数: {n_pieces} / Hesitation: {hesitate_n}回 / Misplace: {n_misplace}回")
    print(f"  総フレーム数: {total_frames} ({total_secs:.1f}秒)")

    # ffmpeg プロセス起動
    proc = open_ffmpeg(output_path)
    frame_count = 0

    def write_frame():
        nonlocal frame_count
        proc.stdin.write(frame_to_bytes(fig))
        frame_count += 1
        if frame_count % 30 == 0:
            pct = frame_count / total_frames * 100
            print(f"  [{pct:5.1f}%] {frame_count}/{total_frames} フレーム", end="\r")

    # フィギュアセットアップ
    fig = plt.figure(figsize=(WIDTH / DPI, HEIGHT / DPI), dpi=DPI)
    fig.patch.set_facecolor(BG_COLOR)

    # 3Dビューエリア: 縦動画の中央〜やや下に配置
    ax = fig.add_axes([0.0, 0.08, 1.0, 0.70], projection="3d")
    setup_axes(ax, gx, gy, gz)

    overlay = TextOverlay(fig)
    placed: set[str] = set()
    puzzle_id: str = puzzle["puzzle_id"]
    n_removed = len(removed)

    # ── テキスト描画ヘルパー ──────────────────────────────────────

    def draw_watermark(alpha: float = 0.55):
        """右下の小さなブランド透かし — 常時表示。"""
        overlay.add(
            0.97, 0.03, "SoChi BLOCKS",
            ha="right", va="bottom",
            fontsize=11, fontweight="bold",
            color=TEXT_COLOR, alpha=alpha,
            fontfamily="DejaVu Sans",
        )

    def draw_hook_text(hook: str, sub: str = "", alpha: float = 1.0):
        """チャレンジフックテキスト (中央上部)。"""
        overlay.add(
            0.5, 0.94, hook,
            ha="center", va="top",
            fontsize=22, fontweight="bold",
            color=TEXT_COLOR, alpha=alpha,
            fontfamily="DejaVu Sans",
        )
        if sub:
            overlay.add(
                0.5, 0.90, sub,
                ha="center", va="top",
                fontsize=14, color=ACCENT_COLOR, alpha=alpha * 0.85,
                fontfamily="DejaVu Sans",
            )

    def draw_progress(piece_idx: int, current_color: str, alpha: float = 1.0):
        """ピース進行状況ドット (下部中央)。"""
        dot_spacing = 0.045
        x_start = 0.5 - (n_removed - 1) * dot_spacing / 2.0
        for i in range(n_removed):
            dot_x = x_start + i * dot_spacing
            if i < piece_idx:
                char, color = "●", "#aaaaaa"
            elif i == piece_idx:
                char, color = "●", current_color
            else:
                char, color = "○", "#444444"
            overlay.add(
                dot_x, 0.07, char,
                ha="center", va="bottom",
                fontsize=16, color=color, alpha=alpha,
            )

    # ── シーン描画ヘルパー ────────────────────────────────────────

    def render_scene(
        float_piece: str | None = None,
        float_z: float = 0.0,
        azim: float = 225.0,
        float_xy: tuple[int, int] = (0, 0),
    ):
        ax.cla()
        setup_axes(ax, gx, gy, gz, azim=azim)
        filled, fc = build_voxel_arrays(
            puzzle, piece_colors, placed,
            float_piece, float_z, float_xy_offset=float_xy,
        )
        render_voxels(ax, filled, fc)

    # ════════════════════════════════════════════════════════════════
    # フェーズ 1: イントロ (パズル即表示 + チャレンジフックテキスト)
    # ════════════════════════════════════════════════════════════════
    print("  [1/3] イントロ...")
    for i in range(INTRO_FRAMES):
        t = i / INTRO_FRAMES
        overlay.clear()
        render_scene()
        alpha_hook = smoothstep(min(1.0, t * 3.0))
        draw_hook_text(hook_text, sub=f"#{puzzle_id}", alpha=alpha_hook)
        draw_watermark(alpha=alpha_hook * 0.55)
        write_frame()

    # ════════════════════════════════════════════════════════════════
    # フェーズ 2: ピース配置アニメーション
    # ════════════════════════════════════════════════════════════════
    print("\n  [2/3] ピース配置アニメーション...")
    for piece_idx, pid in enumerate(removed):
        print(f"    ピース {pid} ({piece_idx + 1}/{n_pieces})")
        piece_color = piece_colors.get(pid, "#ffffff")
        do_misplace = piece_idx in misplace_indices

        # ── FLOAT: 浮遊フェーズ ──────────────────────────────────
        for i in range(FLOAT_FRAMES):
            t = i / FLOAT_FRAMES
            bob = BOB_AMPLITUDE * math.sin(t * 2.0 * math.pi * BOB_CYCLES)
            float_z = FLOAT_HEIGHT + bob
            azim = 225.0 + AZIM_SWEEP_DEG * math.sin(t * 2.0 * math.pi * BOB_CYCLES)
            overlay.clear()
            hook = hook_text if piece_idx == 0 else f"Piece {piece_idx + 1} of {n_removed}"
            draw_hook_text(hook, sub=f"#{puzzle_id}")
            draw_watermark()
            draw_progress(piece_idx, piece_color)
            render_scene(float_piece=pid, float_z=float_z, azim=azim)
            write_frame()

        # ── MISPLACE: 誤配置フェーズ (Medium以上の指定ピース) ────
        if do_misplace:
            mp_offset = compute_misplace_offset(puzzle, pid)
            piece_label = f"Piece {piece_idx + 1} of {n_removed}"

            # --- 誤配置スナップ: 誤った位置にズレながら降りる ---
            for i in range(MISPLACE_SNAP_FRAMES):
                t = smoothstep(i / MISPLACE_SNAP_FRAMES)
                float_z = FLOAT_HEIGHT * (1.0 - t)
                azim = 225.0 + AZIM_SWEEP_DEG * (1.0 - t)
                overlay.clear()
                draw_hook_text(piece_label, sub=f"#{puzzle_id}")
                draw_watermark()
                draw_progress(piece_idx, piece_color)
                render_scene(float_piece=pid, float_z=float_z, azim=azim, float_xy=mp_offset)
                write_frame()

            # --- 誤配置静止: 着地！でも赤フラッシュ + ✗ アイコン ---
            for i in range(MISPLACE_PAUSE_FRAMES):
                overlay.clear()
                draw_hook_text(piece_label, sub=f"#{puzzle_id}")
                draw_watermark()
                draw_progress(piece_idx, piece_color)
                render_scene(float_piece=pid, float_z=0.0, azim=225.0, float_xy=mp_offset)
                # 赤フラッシュ (最初が最大 → フェードアウト)
                flash_alpha = (1.0 - i / MISPLACE_PAUSE_FRAMES) * 0.35
                overlay.add(
                    0.5, 0.5, "■",
                    ha="center", va="center",
                    fontsize=600,
                    color=ERROR_COLOR,
                    alpha=flash_alpha,
                )
                # ✗ アイコン (フェードイン)
                err_alpha = smoothstep(min(1.0, i / (MISPLACE_PAUSE_FRAMES * 0.5))) * 0.85
                overlay.add(
                    0.5, 0.5, "✗",
                    ha="center", va="center",
                    fontsize=120, fontweight="bold",
                    color=ERROR_COLOR,
                    alpha=err_alpha,
                )
                write_frame()

            # --- 引き剥がし: 「やっぱり違う！」でピースが浮上 + カメラ揺れ ---
            for i in range(MISPLACE_RETRACT_FRAMES):
                t = smoothstep(i / MISPLACE_RETRACT_FRAMES)
                float_z = FLOAT_HEIGHT * t
                # カメラが驚いて大きく揺れる
                shake_azim = 225.0 + AZIM_SWEEP_DEG * 3.0 * math.sin(t * math.pi * 2.5)
                overlay.clear()
                draw_hook_text(piece_label, sub=f"#{puzzle_id}")
                draw_watermark()
                draw_progress(piece_idx, piece_color)
                render_scene(float_piece=pid, float_z=float_z, azim=shake_azim, float_xy=mp_offset)
                write_frame()

        # ── HESITATE: 試行錯誤 (2ピース目以降、Medium/Hard) ──────
        if piece_idx > 0:
            azim_scale = 1.0 + 0.5 * max(0, n_pieces - 4)  # 5p以上で1.5倍
            for h in range(hesitate_n):
                azim_sign = 1.0 if h % 2 == 0 else -1.0
                for i in range(h_frames):
                    t = i / h_frames
                    drop = HESITATE_DROP * FLOAT_HEIGHT * math.sin(t * math.pi)
                    float_z = FLOAT_HEIGHT - drop
                    azim = 225.0 + azim_sign * hesitate_azim * azim_scale * math.sin(t * math.pi)
                    overlay.clear()
                    draw_hook_text(f"Piece {piece_idx + 1} of {n_removed}", sub=f"#{puzzle_id}")
                    draw_watermark()
                    draw_progress(piece_idx, piece_color)
                    render_scene(float_piece=pid, float_z=float_z, azim=azim)
                    write_frame()

        # ── SNAP: バウンス着地 ───────────────────────────────────
        for i in range(SNAP_FRAMES):
            t = bounce_ease_out(i / SNAP_FRAMES)
            float_z = FLOAT_HEIGHT * (1.0 - t)
            azim = 225.0 + AZIM_SWEEP_DEG * (1.0 - i / SNAP_FRAMES)
            overlay.clear()
            draw_hook_text(f"Piece {piece_idx + 1} of {n_removed}", sub=f"#{puzzle_id}")
            draw_watermark()
            draw_progress(piece_idx, piece_color)
            render_scene(float_piece=pid, float_z=float_z, azim=azim)
            write_frame()

        placed.add(pid)

        # ── SETTLE: 着地後静止 + 白フラッシュ強化 ───────────────
        for i in range(SETTLE_FRAMES):
            overlay.clear()
            draw_hook_text(f"Piece {piece_idx + 1} of {n_removed}", sub=f"#{puzzle_id}")
            draw_watermark()
            draw_progress(piece_idx + 1, piece_color)
            render_scene()
            # 強化白フラッシュ (alpha 0.45 / 旧: 0.18)
            if i < 5:
                flash_alpha = (1.0 - i / 5.0) * 0.45
                overlay.add(
                    0.5, 0.5, "■",
                    ha="center", va="center",
                    fontsize=600,
                    color="#ffffff",
                    alpha=flash_alpha,
                )
            write_frame()

    # ════════════════════════════════════════════════════════════════
    # フェーズ 3: 完成演出 (VICTORY) — ★カウントアップ + 難易度ラベル
    # ════════════════════════════════════════════════════════════════
    print("\n  [3/3] 完成演出...")
    piece_emojis = "".join(PIECE_EMOJI.get(p, "🧩") for p in removed)

    for i in range(VICTORY_FRAMES):
        t = i / VICTORY_FRAMES
        overlay.clear()
        render_scene()

        v_alpha = smoothstep(min(1.0, t * 3.5))
        overlay.add(
            0.5, 0.90, "Solved!",
            ha="center", va="top",
            fontsize=40, fontweight="bold",
            color=GOLD_COLOR, alpha=v_alpha,
            fontfamily="DejaVu Sans",
        )
        # ★ カウントアップ (1つずつ点灯)
        n_stars_shown = min(n_removed, int(t * (n_removed + 1)))
        stars_str = "★" * n_stars_shown + "☆" * (n_removed - n_stars_shown)
        overlay.add(
            0.5, 0.84, f"{diff_label}  {stars_str}",
            ha="center", va="top",
            fontsize=22, color=TEXT_COLOR, alpha=v_alpha,
            fontfamily="DejaVu Sans",
        )
        overlay.add(
            0.5, 0.80, piece_emojis,
            ha="center", va="top",
            fontsize=26, alpha=v_alpha,
        )
        # CTA は少し遅れてフェードイン
        cta_alpha = smoothstep(max(0.0, (t - 0.3) * 2.0)) * v_alpha
        overlay.add(
            0.5, 0.07, "Play via link in bio  souchi-lab.github.io/sochi-blocks",
            ha="center", va="bottom",
            fontsize=12, color=ACCENT_COLOR, alpha=cta_alpha,
            fontfamily="DejaVu Sans",
        )
        draw_watermark(alpha=cta_alpha * 0.5)
        write_frame()

    # ── クリーンアップ ────────────────────────────────────────────
    overlay.clear()
    plt.close(fig)

    proc.stdin.close()
    proc.wait()

    print(f"\n  完了: {frame_count} フレーム書き込み済み")


# ── エントリーポイント ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SoChi BLOCKS パズル動画ジェネレーター",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("puzzle_id", help="パズルID (例: 20260304_001)")
    parser.add_argument(
        "--output", "-o",
        help="出力MP4ファイルパス (省略時: docs/sns_videos/<puzzle_id>.mp4)",
    )
    parser.add_argument(
        "--hook",
        default=None,
        help="イントロフックテキスト上書き (省略時は難易度に応じて自動選択)",
    )
    args = parser.parse_args()

    # データロード
    print(f"パズル {args.puzzle_id} を読み込み中...")
    puzzle = load_puzzle(args.puzzle_id)
    piece_colors = load_piece_colors()

    # 出力先の決定
    if args.output:
        output_path = args.output
    else:
        root = find_project_root()
        out_dir = root / "docs" / "sns_videos"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / f"{args.puzzle_id}.mp4")

    print(f"出力先: {output_path}")

    # 動画生成
    generate_video(puzzle, piece_colors, output_path, hook_override=args.hook)

    print(f"\nOK 動画を生成しました: {output_path}")


if __name__ == "__main__":
    main()
