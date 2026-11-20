"""Move the video painting annotations of the Animated Viewer manifest into canvas.items (IIIF 3.0: painting
annotations belong in items; the same shape as Cookbook recipe 0036), make video URLs absolute, and keep each
motion description (the generation prompt) as the video's `summary`, with its start as the `label`. Usage: convert.py <in.json> <out.json> <video base URL> [manifest id]"""
import json, sys

src, out, base = sys.argv[1], sys.argv[2], sys.argv[3].rstrip('/') + '/'
m = json.load(open(src))
if len(sys.argv) > 4:
    m['id'] = sys.argv[4]
canvas = m['items'][0]
cid = canvas['id']
videos, notes = [], []
for page in canvas.get('annotations', []):
    for a in page['items']:
        bodies = a['body'] if isinstance(a['body'], list) else [a['body']]
        for b in bodies:
            if b.get('type') == 'Video':
                vb = dict(b)
                vb['id'] = base + vb['id'].split('/')[-1]
                videos.append({'id': a['id'], 'type': 'Annotation', 'motivation': 'painting', 'body': vb, 'target': a['target']})
        texts = [b for b in bodies if b.get('type') == 'TextualBody']
        if texts and videos and videos[-1]['id'] == a['id']:
            # a short name for the list of videos: the start of each description
            label = {}
            for t in texts:
                v = t['value'].split('。')[0].split('、')[0] if t.get('language') == 'ja' else t['value'].split('.')[0].split(',')[0]
                label[t.get('language', 'none')] = [v if len(v) <= 40 else v[:40] + '…']
            videos[-1]['body']['label'] = label
            videos[-1]['body']['summary'] = {t.get('language', 'none'): [t['value']] for t in texts}
canvas['items'].append({'id': cid + '/page/videos', 'type': 'AnnotationPage', 'items': videos})
canvas.pop('annotations', None)
json.dump(m, open(out, 'w'), ensure_ascii=False, indent=2)
print(len(videos), 'videos')
