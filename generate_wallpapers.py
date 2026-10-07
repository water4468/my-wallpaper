# -*- coding: utf-8 -*-
"""
自动扫描 images 分类文件夹，生成缩略图并输出 wallpapers-data.js。
用法：双击 “更新壁纸.bat” 即可，无需手动改代码。
卡片显示缩略图（清晰、加载快），original 字段保留原图路径供查看大图/下载。
"""
import os, json, sys, re
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(ROOT, "images")
THUMB_DIR = os.path.join(IMG_DIR, ".thumbs")
OUT = os.path.join(ROOT, "wallpapers-data.js")

# 分类文件夹 -> category 值
CATEGORIES = [
    ("pc-static",    "pc-static"),
    ("pc-dynamic",   "pc-dynamic"),
    ("phone-static", "phone-static"),
    ("phone-dynamic","phone-dynamic"),
    ("dynamic-bg",   "dynamic-bg"),
    ("other",        "other"),
]
TAGS = {"scenery", "anime", "people", "simple", "scifi"}
EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp")
VIDEO_EXTS = (".mp4", ".webm", ".ogv", ".ogg", ".mov", ".m4v")
THUMB_W = 640          # 缩略图宽度（足以在高分屏卡片上清晰显示）
JPEG_Q = 86            # 缩略图质量

# 文件名末尾用于手动排序的“-数字”，例如 “OS娘-Q版-卡通-可爱-3.mp4”
TRAILING_NUM = re.compile(r'[-_](\d+)\s*$')

def strip_trailing_num(stem):
    """去掉文件名末尾仅用于排序的“-数字”，避免它进入标题/标签。"""
    return TRAILING_NUM.sub('', stem).strip('-_ ')

def order_key(name):
    """按文件名末尾数字从小到大；没有数字的排在后面，再按名字兜底。"""
    m = TRAILING_NUM.search(os.path.splitext(name)[0])
    if m:
        return (0, int(m.group(1)), name)
    return (1, 0, name)

def title_from_name(name):
    stem = strip_trailing_num(os.path.splitext(name)[0])
    for ch in ("_", "-"):
        stem = stem.replace(ch, " ")
    return stem.strip()

def tags_from_name(name):
    """从文件名按分隔符（- _）提取标签数组，去空、去重、去除首尾空格"""
    stem = strip_trailing_num(os.path.splitext(name)[0])
    parts = re.split(r"[-_]+", stem)
    tags, seen = [], set()
    for p in parts:
        t = p.strip()
        if t and t not in seen:
            seen.add(t)
            tags.append(t)
    return tags

def make_thumb(rel_path, full_path):
    """生成缩略图，返回 (缩略图相对项目根路径, 原图宽, 原图高)；失败返回 (None, w, h)"""
    base = os.path.splitext(rel_path)[0]
    thumb_rel = "images/.thumbs/" + base + ".jpg"
    thumb_full = os.path.join(THUMB_DIR, base + ".jpg")
    w = h = None
    try:
        with Image.open(full_path) as im:
            w, h = im.size
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, (20, 20, 22))
                im = Image.alpha_composite(bg, im.convert("RGBA")).convert("RGB")
            else:
                im = im.convert("RGB")
            if w > THUMB_W:
                nh = max(1, round(h * THUMB_W / w))
                im = im.resize((THUMB_W, nh), Image.LANCZOS)
            os.makedirs(os.path.dirname(thumb_full), exist_ok=True)
            im.save(thumb_full, "JPEG", quality=JPEG_Q, optimize=True)
        return thumb_rel, w, h
    except Exception as e:
        print("  [WARN] 缩略图生成失败 %s: %s" % (rel_path, e))
        return None, w, h

def make_video_poster(rel_path, full_path):
    """提取视频首帧作为卡片封面；未安装 ffmpeg 或失败时返回 None。"""
    import shutil, subprocess
    if not shutil.which("ffmpeg"):
        return None
    base = os.path.splitext(rel_path)[0]
    poster_rel = "images/.thumbs/" + base + ".jpg"
    poster_full = os.path.join(THUMB_DIR, base + ".jpg")
    try:
        os.makedirs(os.path.dirname(poster_full), exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-i", full_path, "-frames:v", "1",
             "-vf", "scale='min(640,iw)':-2", "-q:v", "4", poster_full],
            check=True, capture_output=True, timeout=120)
        return poster_rel
    except Exception as e:
        print("  [WARN] 视频封面生成失败 %s: %s" % (rel_path, e))
        return None

def make_video_preview(rel_path, full_path):
    """生成约640宽、静音、低码率的小预览视频，供壁纸卡片流畅播放
    （对标 haowallpaper 的 getVideoReduce）；原图仍保留在 original 字段。"""
    import shutil, subprocess
    if not shutil.which("ffmpeg"):
        return None
    base = os.path.splitext(rel_path)[0]
    preview_rel = "images/.thumbs/" + base + ".mp4"
    preview_full = os.path.join(THUMB_DIR, base + ".mp4")
    try:
        os.makedirs(os.path.dirname(preview_full), exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-i", full_path,
             "-an",
             "-vf", "scale='min(640,iw)':-2,fps=30",
             "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
             "-crf", "28", "-preset", "veryfast",
             "-movflags", "+faststart",
             preview_full],
            check=True, capture_output=True, timeout=300)
        return preview_rel
    except Exception as e:
        print("  [WARN] 预览视频生成失败 %s: %s" % (rel_path, e))
        return None

def collect():
    items = []
    for folder, category in CATEGORIES:
        cdir = os.path.join(IMG_DIR, folder)
        if not os.path.isdir(cdir):
            continue
        # 直接放在分类文件夹里的图片（默认 tag=simple）
        for name in sorted(os.listdir(cdir), key=order_key):
            p = os.path.join(cdir, name)
            low = name.lower()
            if os.path.isfile(p):
                if low.endswith(VIDEO_EXTS):
                    items.append(make_video_item(category, "simple", folder, name, p))
                elif low.endswith(EXTS):
                    items.append(make_item(category, "simple", folder, name, p))
            # 可选：再下一层以“标签”命名的子文件夹
            elif os.path.isdir(p) and name != ".thumbs":
                tag = name if name in TAGS else "simple"
                for sub in sorted(os.listdir(p), key=order_key):
                    sp = os.path.join(p, sub)
                    sublow = sub.lower()
                    if os.path.isfile(sp):
                        if sublow.endswith(VIDEO_EXTS):
                            items.append(make_video_item(category, tag, folder + "/" + name, sub, sp))
                        elif sublow.endswith(EXTS):
                            items.append(make_item(category, tag, folder + "/" + name, sub, sp))
    return items

def make_item(category, tag, rel_dir, name, full_path):
    rel_path = (rel_dir + "/" + name).replace("\\", "/")
    original = "images/" + rel_path
    thumb, w, h = make_thumb(rel_path, full_path)
    # 卡片优先用缩略图；缩略图失败则回退原图
    src = thumb or original.replace(" ", "%20")
    return {
        "title": title_from_name(name),
        "category": category,
        "tag": tag,
        "tags": tags_from_name(name),
        "src": src,
        "original": original,
        "w": w,
        "h": h,
    }

def make_video_item(category, tag, rel_dir, name, full_path):
    """mp4 动态壁纸：卡片用小预览视频（preview），original 保留完整原视频。"""
    rel_path = (rel_dir + "/" + name).replace("\\", "/")
    original = "images/" + rel_path
    poster = make_video_poster(rel_path, full_path)
    preview = make_video_preview(rel_path, full_path)
    return {
        "title": title_from_name(name),
        "category": category,
        "tag": tag,
        "tags": tags_from_name(name),
        "type": "video",
        "src": preview or original,
        "poster": poster,
        "preview": preview,
        "original": original,
        "w": None,
        "h": None,
    }

def prune_thumbs(items):
    """删除已不存在对应原图的陈旧缩略图"""
    if not os.path.isdir(THUMB_DIR):
        return
    valid = set()
    for it in items:
        for key in ("src", "poster", "preview"):
            v = it.get(key)
            if v and v.startswith("images/.thumbs/"):
                valid.add(os.path.join(ROOT, v.replace("/", os.sep)))
    for dirpath, _, files in os.walk(THUMB_DIR):
        for f in files:
            fp = os.path.join(dirpath, f)
            if fp not in valid:
                try: os.remove(fp)
                except OSError: pass

def main():
    if not os.path.isdir(IMG_DIR):
        print("找不到 images 文件夹")
        sys.exit(1)
    items = collect()
    prune_thumbs(items)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// 自动生成，请勿手动编辑 —— 由 generate_wallpapers.py 生成\n")
        f.write("window.WALLPAPER_MANIFEST = ")
        f.write(json.dumps(items, ensure_ascii=False, indent=2))
        f.write(";\n")
    print("已生成 wallpapers-data.js，共 %d 张壁纸" % len(items))
    for it in items:
        print("  [%s/%s] %s" % (it["category"], it["tag"], it["title"]))
    if not items:
        print("（还没有图片：把图片放进 images 下对应分类文件夹，再运行一次）")

if __name__ == "__main__":
    main()
