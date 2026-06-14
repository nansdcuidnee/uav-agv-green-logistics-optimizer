"""生成演示视频 - 基于已有结果的可视化展示"""

import argparse
import json
import os
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


def parse_args():
    parser = argparse.ArgumentParser(description="生成演示视频")
    parser.add_argument("--run-dir", required=True, help="单次运行结果目录")
    parser.add_argument("--ablation-dir", required=True, help="消融实验结果目录")
    parser.add_argument("--output", required=True, help="输出视频路径")
    parser.add_argument("--duration", type=int, default=30, help="视频时长(秒)")
    parser.add_argument("--fps", type=int, default=24, help="帧率")
    parser.add_argument("--width", type=int, default=1280, help="视频宽度")
    parser.add_argument("--height", type=int, default=720, help="视频高度")
    return parser.parse_args()


def load_steps_data(run_dir):
    """加载steps.csv数据"""
    steps_path = Path(run_dir) / "records" / "steps.csv"
    if not steps_path.exists():
        raise FileNotFoundError(f"缺少文件: {steps_path}")
    df = pd.read_csv(steps_path)
    return df


def load_metrics(run_dir):
    """加载metrics.json数据"""
    metrics_path = Path(run_dir) / "metrics.json"
    if not metrics_path.exists():
        raise FileNotFoundError(f"缺少文件: {metrics_path}")
    with open(metrics_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_ablation_data(ablation_dir):
    """加载消融实验数据"""
    ablation_path = Path(ablation_dir)

    figures_dir = ablation_path / "figures"
    plots_dir = ablation_path / "plots_summary"
    agg_path = ablation_path / "aggregate_by_variant.csv"

    missing = []
    if not figures_dir.exists():
        missing.append(f"{figures_dir}/ablation_overview.png")
        missing.append(f"{figures_dir}/ablation_vs_full_delta.png")
    if not plots_dir.exists():
        missing.append(f"{plots_dir}/completion_rate_by_variant.png")
        missing.append(f"{plots_dir}/total_energy_by_variant.png")
        missing.append(f"{plots_dir}/avg_delivery_time_by_variant.png")
    if not agg_path.exists():
        missing.append(str(agg_path))

    if missing:
        raise FileNotFoundError(f"缺少文件:\n" + "\n".join(f"  - {m}" for m in missing))

    agg_df = pd.read_csv(agg_path)
    scene_data = agg_df[agg_df["scene_name"] == "pickup_delivery_generated"]
    if scene_data.empty:
        scene_data = agg_df[agg_df["scene_name"] == agg_df["scene_name"].iloc[0]]

    variants = scene_data["variant_name"].tolist()

    return {
        "overview": str(figures_dir / "ablation_overview.png"),
        "delta": str(figures_dir / "ablation_vs_full_delta.png"),
        "completion": str(plots_dir / "completion_rate_by_variant.png"),
        "energy": str(plots_dir / "total_energy_by_variant.png"),
        "delivery_time": str(plots_dir / "avg_delivery_time_by_variant.png"),
        "variants": variants,
    }


def create_frame(width, height, bg_color=(20, 20, 30)):
    """创建空白帧"""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = bg_color
    return frame


def get_font(font_size):
    """获取支持中文的字体"""
    import os

    windows_fonts = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simkai.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]

    linux_fonts = [
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    mac_fonts = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial.ttf",
    ]

    all_fonts = windows_fonts + linux_fonts + mac_fonts

    for font_path in all_fonts:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except:
                continue

    return ImageFont.load_default()


def put_text(img, text, position, font_size=32, color=(255, 255, 255)):
    """在图像上添加文字"""
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font = get_font(font_size)
    draw.text(position, text, font=font, fill=color)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def draw_energy_curve(frame, df, progress, metrics, width, height):
    """绘制能耗曲线随时间推进的动画"""
    curve_x, curve_y = width // 2 + 50, 100
    curve_w, curve_h = width // 2 - 100, 300

    total_rows = len(df)
    current_rows = max(1, int(total_rows * progress))

    times = df["sim_time"].values[:current_rows]
    energies = df["total_energy_cumulative"].values[:current_rows]

    if len(times) > 1:
        max_energy = energies.max() if energies.max() > 0 else 1
        max_time = times.max() if times.max() > 0 else 1

        points = []
        for t, e in zip(times, energies):
            x = curve_x + int((t / max_time) * curve_w)
            y = curve_y + curve_h - int((e / max_energy) * curve_h)
            points.append((x, y))

        for i in range(1, len(points)):
            cv2.line(frame, points[i - 1], points[i], (0, 255, 200), 2)

        cv2.circle(frame, points[-1], 5, (0, 255, 200), -1)

    cv2.rectangle(frame, (curve_x, curve_y), (curve_x + curve_w, curve_y + curve_h), (100, 100, 100), 1)
    put_text(frame, "累计能耗", (curve_x, curve_y - 30), 20, (200, 200, 200))

    return frame


def draw_task_progress(frame, df, progress, metrics, width, height):
    """绘制任务完成进度随时间推进的动画"""
    prog_x, prog_y = 100, 100
    prog_w, prog_h = width // 2 - 150, 300

    total_rows = len(df)
    current_rows = max(1, int(total_rows * progress))

    completed = df["completed_tasks_cumulative"].values[:current_rows]

    if len(completed) > 0:
        max_completed = max(metrics.get("total_tasks", 5), completed.max())
        current_completed = completed[-1]

        bar_h = 30
        bar_y = prog_y + prog_h // 2
        cv2.rectangle(frame, (prog_x, bar_y), (prog_x + prog_w, bar_y + bar_h), (50, 50, 50), -1)

        fill_w = int((current_completed / max_completed) * prog_w)
        cv2.rectangle(frame, (prog_x, bar_y), (prog_x + fill_w, bar_y + bar_h), (0, 200, 100), -1)

        put_text(frame, f"已完成任务: {current_completed}/{max_completed}", (prog_x, bar_y - 40), 24, (255, 255, 255))
        put_text(frame, f"{current_completed / max_completed * 100:.0f}%", (prog_x + fill_w + 10, bar_y), 20, (0, 255, 100))

    put_text(frame, "任务完成进度", (prog_x, prog_y - 30), 20, (200, 200, 200))

    return frame


def draw_kpi_overlay(frame, metrics, width, height):
    """在帧上叠加KPI信息"""
    kpi_items = [
        ("完成率", f"{metrics.get('completion_rate', 0) * 100:.0f}%"),
        ("总能耗", f"{metrics.get('total_energy', 0):.1f}"),
        ("平均配送时间", f"{metrics.get('avg_delivery_time', 0):.2f}"),
        ("中继次数", str(metrics.get("relay_count", 0))),
    ]

    start_x = width - 250
    start_y = height - 150

    for i, (label, value) in enumerate(kpi_items):
        y = start_y + i * 35
        put_text(frame, f"{label}: {value}", (start_x, y), 22, (200, 220, 255))

    return frame


def create_intro_frame(width, height, elapsed, duration):
    """创建片头帧"""
    frame = create_frame(width, height)

    alpha = min(1.0, elapsed / 1.0)
    title = "UAV-AGV 绿色物流优化系统"
    subtitle = "结果演示"

    frame = put_text(frame, title, (width // 2 - 300, height // 2 - 50), 48, (255, 255, 255))
    frame = put_text(frame, subtitle, (width // 2 - 100, height // 2 + 30), 32, (180, 180, 180))

    if alpha < 1.0:
        frame = (frame * alpha).astype(np.uint8)

    return frame


def create_single_run_segment(df, metrics, fps, width, height):
    """创建单次运行结果动画段 (15秒: 3-18秒)"""
    segment_duration = 15
    total_frames = segment_duration * fps
    segment = []

    for i in range(total_frames):
        progress = i / total_frames
        frame = create_frame(width, height)

        put_text(frame, "单次运行结果", (50, 50), 36, (255, 255, 255))

        frame = draw_energy_curve(frame, df, progress, metrics, width, height)

        frame = draw_task_progress(frame, df, progress, metrics, width, height)

        frame = draw_kpi_overlay(frame, metrics, width, height)

        bar_y = height - 30
        bar_w = int(width * progress)
        cv2.rectangle(frame, (0, bar_y), (bar_w, bar_y + 10), (0, 150, 255), -1)

        segment.append(frame)

    return segment


def create_ablation_segment(ablation_data, fps, width, height):
    """创建消融实验结果段 (9秒: 18-27秒)"""
    segment_duration = 9
    total_frames = segment_duration * fps
    segment = []

    images_to_show = [
        ("消融实验概览", ablation_data["overview"]),
        ("与Full ALNS对比", ablation_data["delta"]),
        ("各变体完成率", ablation_data["completion"]),
        ("各变体能耗", ablation_data["energy"]),
        ("各变体配送时间", ablation_data["delivery_time"]),
    ]

    frames_per_image = total_frames // len(images_to_show)

    for img_idx, (title, img_path) in enumerate(images_to_show):
        img = cv2.imread(img_path)
        if img is None:
            continue

        img = cv2.resize(img, (width, height))

        for frame_i in range(frames_per_image):
            progress = frame_i / frames_per_image
            frame = img.copy()

            put_text(frame, f"消融实验 - {title}", (50, 50), 36, (255, 255, 255))

            if img_idx < 2 and ablation_data["variants"]:
                variants_text = "变体: " + ", ".join(ablation_data["variants"][:5])
                put_text(frame, variants_text, (50, height - 50), 20, (200, 200, 200))

            if progress < 0.1:
                alpha = progress / 0.1
                frame = cv2.addWeighted(frame, alpha, create_frame(width, height), 1 - alpha, 0)
            elif progress > 0.9:
                alpha = (1 - progress) / 0.1
                frame = cv2.addWeighted(frame, alpha, create_frame(width, height), 1 - alpha, 0)

            segment.append(frame)

    while len(segment) < total_frames:
        segment.append(segment[-1] if segment else create_frame(width, height))
    segment = segment[:total_frames]

    return segment


def create_ending_frame(width, height, metrics, variants):
    """创建结尾帧"""
    frame = create_frame(width, height)

    put_text(frame, "演示完成", (width // 2 - 150, height // 2 - 80), 48, (255, 255, 255))

    summary_items = [
        f"最终完成率: {metrics.get('completion_rate', 0) * 100:.0f}%",
        f"总能耗: {metrics.get('total_energy', 0):.1f}",
        f"测试变体数: {len(variants)}",
    ]

    for i, item in enumerate(summary_items):
        put_text(frame, item, (width // 2 - 150, height // 2 + i * 40), 28, (200, 200, 200))

    return frame


def generate_video(args):
    """生成视频主函数"""
    width, height = args.width, args.height
    fps = args.fps
    total_duration = args.duration

    print("加载数据...")
    df = load_steps_data(args.run_dir)
    metrics = load_metrics(args.run_dir)
    ablation_data = load_ablation_data(args.ablation_dir)

    print(f"  - steps.csv: {len(df)} 行")
    print(f"  - metrics: {metrics.get('strategy_name', 'unknown')}")
    print(f"  - 消融实验变体: {ablation_data['variants']}")

    print("生成视频段...")

    intro_frames = 3 * fps
    intro = [create_intro_frame(width, height, i / fps, 3) for i in range(intro_frames)]

    single_run = create_single_run_segment(df, metrics, fps, width, height)

    ablation = create_ablation_segment(ablation_data, fps, width, height)

    ending_frames = 3 * fps
    ending = [create_ending_frame(width, height, metrics, ablation_data["variants"])] * ending_frames

    print("合并视频段...")
    frames = intro + single_run + ablation + ending

    target_frames = total_duration * fps
    while len(frames) < target_frames:
        frames.append(frames[-1])
    frames = frames[:target_frames]

    print(f"写入视频: {args.output}...")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(args.output, fourcc, fps, (width, height))

    for i, frame in enumerate(frames):
        out.write(frame)
        if (i + 1) % 100 == 0:
            print(f"  进度: {i + 1}/{len(frames)} 帧")

    out.release()
    print(f"完成! 输出: {args.output}")


def main():
    args = parse_args()

    if not Path(args.run_dir).exists():
        print(f"错误: 目录不存在: {args.run_dir}")
        print("提示: 请检查 --run-dir 参数")
        return

    if not Path(args.ablation_dir).exists():
        print(f"错误: 目录不存在: {args.ablation_dir}")
        print("提示: 请检查 --ablation-dir 参数")
        return

    try:
        generate_video(args)
    except FileNotFoundError as e:
        print(f"错误: {e}")
        return
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    main()
