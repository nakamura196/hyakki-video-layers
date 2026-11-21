"""Motion mask: keep video pixels only where figures move; elsewhere use a
static plate (the original crop, or the clip's temporal median). Builds on
blend.py (same crop, colour match and edge band).

usage: python3 motionmask.py RAW.mp4 ORIG_CROP.jpg OUT.mp4 [--plate ref|median]
       [--thr 6] [--grow 24] [--feather 32] [--mask-png M.png]
"""
import argparse, subprocess, json
import numpy as np, cv2

ap = argparse.ArgumentParser()
ap.add_argument('raw'); ap.add_argument('orig'); ap.add_argument('out')
ap.add_argument('--plate', choices=['ref', 'median'], default='ref')
ap.add_argument('--thr', type=float, default=6)
ap.add_argument('--grow', type=int, default=24)
ap.add_argument('--feather', type=int, default=32)
ap.add_argument('--band', type=int, default=24)
ap.add_argument('--edge-feather', type=int, default=96)
ap.add_argument('--mask-png')
a = ap.parse_args()

probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
    'stream=width,height,r_frame_rate', '-of', 'json', a.raw], capture_output=True, text=True).stdout)['streams'][0]
RW, fps = probe['width'], probe['r_frame_rate']
orig = cv2.imread(a.orig); ow, oh = orig.shape[1], orig.shape[0]
th = int(ow * 9 / 16)
tw, th = (int(oh * 16 / 9), oh) if th < oh else (ow, th)
px, py = (tw - ow) // 2, (th - oh) // 2
s = RW / tw
cx, cy, cw, ch = int(px * s), int(py * s), int(ow * s), int(oh * s)
cw -= cw % 2; ch -= ch % 2
ref = cv2.resize(orig, (cw, ch), interpolation=cv2.INTER_AREA)
ref_lab = cv2.cvtColor(ref, cv2.COLOR_BGR2LAB).astype(np.float32)
rm, rs = ref_lab.reshape(-1, 3).mean(0), ref_lab.reshape(-1, 3).std(0)

# pass 1: decode, crop, colour-match, keep frames
dec = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.raw, '-vf', f'crop={cw}:{ch}:{cx}:{cy}',
    '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], capture_output=True).stdout
F = np.frombuffer(dec, np.uint8).reshape(-1, ch, cw, 3)
frames = []
for f in F:
    lab = cv2.cvtColor(f, cv2.COLOR_BGR2LAB).astype(np.float32)
    m, sd = lab.reshape(-1, 3).mean(0), lab.reshape(-1, 3).std(0) + 1e-6
    lab = (lab - m) / sd * rs + rm
    frames.append(cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR))
frames = np.stack(frames); n = len(frames)

# activity: blurred luma (removes fine "boiling"), deviation from temporal median
small = np.stack([cv2.GaussianBlur(cv2.cvtColor(cv2.resize(f, (cw // 2, ch // 2), interpolation=cv2.INTER_AREA),
    cv2.COLOR_BGR2GRAY), (0, 0), 3).astype(np.float32) for f in frames])
med = np.median(small, 0)
act = np.percentile(np.abs(small - med), 95, axis=0)
mv = (act > a.thr).astype(np.uint8)
mv = cv2.morphologyEx(mv, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))  # drop specks
mv = cv2.resize(mv, (cw, ch), interpolation=cv2.INTER_NEAREST)
k = 2 * a.grow + 1
mv = cv2.dilate(mv, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
dist = cv2.distanceTransform(mv, cv2.DIST_L2, 5)  # inside distance
t = np.clip(dist / a.feather, 0, 1)
motion = t * t * (3 - 2 * t)  # 1 = take video

yy, xx = np.mgrid[0:ch, 0:cw]
d = np.minimum.reduce([xx, yy, cw - 1 - xx, ch - 1 - yy]).astype(np.float32)
te = np.clip((d - a.band) / a.edge_feather, 0, 1)
edge = 1 - te * te * (3 - 2 * te)  # 1 = take original
w_vid = (motion * (1 - edge))[..., None].astype(np.float32)

plate = ref.astype(np.float32) if a.plate == 'ref' else np.median(frames, 0).astype(np.float32)
if a.plate == 'median':  # edge band still from the original
    plate = plate * (1 - edge[..., None]) + ref.astype(np.float32) * edge[..., None]

if a.mask_png:
    vis = (ref * 0.5).astype(np.uint8); vis[..., 2] = np.maximum(vis[..., 2], (w_vid[..., 0] * 255).astype(np.uint8))
    cv2.imwrite(a.mask_png, vis)

enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
    '-s', f'{cw}x{ch}', '-r', fps, '-i', '-', '-c:v', 'libx264', '-crf', '18', '-preset', 'slow', '-pix_fmt', 'yuv420p',
    '-vf', 'scale=out_color_matrix=bt709:out_range=tv',
    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv',
    '-bsf:v', 'h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0',
    '-movflags', '+faststart', a.out], stdin=subprocess.PIPE)
for f in frames:
    o = f.astype(np.float32) * w_vid + plate * (1 - w_vid)
    enc.stdin.write(np.clip(o + 0.5, 0, 255).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()
print(f'frames={n} video_share={w_vid.mean()*100:.1f}% act_p50={np.median(act):.1f} act_p90={np.percentile(act,90):.1f}')
