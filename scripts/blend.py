"""Crop a padded 16:9 Flow clip back to its region, match colour to the
original crop, and replace an edge band with the original pixels.

usage: python3 blend.py RAW.mp4 ORIG_CROP.jpg OUT.mp4 [--band 24] [--feather 96] [--no-color] [--no-edge]
"""
import argparse, subprocess, json
import numpy as np, cv2

ap = argparse.ArgumentParser()
ap.add_argument('raw'); ap.add_argument('orig'); ap.add_argument('out')
ap.add_argument('--band', type=int, default=24)
ap.add_argument('--feather', type=int, default=96)
ap.add_argument('--no-color', action='store_true')
ap.add_argument('--no-edge', action='store_true')
a = ap.parse_args()

probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
    'stream=width,height,r_frame_rate', '-of', 'json', a.raw], capture_output=True, text=True).stdout)['streams'][0]
RW, RH, fps = probe['width'], probe['height'], probe['r_frame_rate']

orig = cv2.imread(a.orig)  # BGR, unpadded region
ow, oh = orig.shape[1], orig.shape[0]
# same rule as movie/scripts/prepare_crops.py + process_raw.py
th = int(ow * 9 / 16)
if th < oh:
    tw, th = int(oh * 16 / 9), oh
else:
    tw = ow
px, py = (tw - ow) // 2, (th - oh) // 2
s = RW / tw
cx, cy, cw, ch = int(px * s), int(py * s), int(ow * s), int(oh * s)
cw -= cw % 2; ch -= ch % 2
ref = cv2.resize(orig, (cw, ch), interpolation=cv2.INTER_AREA)
ref_lab = cv2.cvtColor(ref, cv2.COLOR_BGR2LAB).astype(np.float32)
rm, rs = ref_lab.reshape(-1, 3).mean(0), ref_lab.reshape(-1, 3).std(0)

# edge mask: 1 inside the outer band, smooth fall-off to 0 over `feather`
yy, xx = np.mgrid[0:ch, 0:cw]
d = np.minimum.reduce([xx, yy, cw - 1 - xx, ch - 1 - yy]).astype(np.float32)
t = np.clip((d - a.band) / a.feather, 0, 1)
mask = (1 - (t * t * (3 - 2 * t)))[..., None]
if a.no_edge:
    mask[:] = 0

dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', a.raw, '-vf', f'crop={cw}:{ch}:{cx}:{cy}',
    '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
    '-s', f'{cw}x{ch}', '-r', fps, '-i', '-', '-i', a.raw, '-map', '0:v', '-map', '1:a?',
    '-c:v', 'libx264', '-crf', '18', '-preset', 'slow', '-pix_fmt', 'yuv420p',
    '-vf', 'scale=out_color_matrix=bt709:out_range=tv',
    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv',
    '-bsf:v', 'h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0',
    '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', a.out], stdin=subprocess.PIPE)

n = 0; fsz = cw * ch * 3
edge_before, edge_after = [], []
ring = mask[..., 0] > 0.99
while True:
    buf = dec.stdout.read(fsz)
    if len(buf) < fsz:
        break
    f = np.frombuffer(buf, np.uint8).reshape(ch, cw, 3)
    g = f.astype(np.float32)
    if not a.no_color:
        lab = cv2.cvtColor(f, cv2.COLOR_BGR2LAB).astype(np.float32)
        m, sd = lab.reshape(-1, 3).mean(0), lab.reshape(-1, 3).std(0) + 1e-6
        lab = (lab - m) / sd * rs + rm
        g = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32)
    o = g * (1 - mask) + ref.astype(np.float32) * mask
    edge_before.append(np.abs(f.astype(np.float32) - ref)[ring].mean())
    edge_after.append(np.abs(o - ref)[ring].mean())
    enc.stdin.write(np.clip(o + 0.5, 0, 255).astype(np.uint8).tobytes())
    n += 1
enc.stdin.close(); enc.wait(); dec.wait()
print(f'frames={n} size={cw}x{ch} crop=({cx},{cy}) edge|diff| before={np.mean(edge_before):.1f} after={np.mean(edge_after):.1f}')
