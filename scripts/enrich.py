"""Add descriptive metadata to manifest.json (run after convert.py; running it again gives the same result).

- Manifest: label and summary in Japanese and English, metadata about the original scroll and the clips,
  requiredStatement in both languages (the General Library asks to name the holder and to say the image was modified),
  provider, homepage, thumbnail
- Canvas: label
- Each video: a short label in both languages (convert.py cut the start of the prompt, which often stopped mid-phrase),
  and width, height and duration measured from the file in videos/ with ffprobe

No `rights`: the General Library's terms (https://www.lib.u-tokyo.ac.jp/ja/library/general/reuse) are not a
Creative Commons or RightsStatements.org URI, and no new licence is given to the generated clips.
The catalogue fields come from the University of Tokyo Digital Archive Portal, whose metadata is CC0.

The motion prompts and the model of each clip are in scripts/prompts.json (video name → model, short labels, en, ja).

Usage: python3 scripts/enrich.py   (in the repository root; edits manifest.json in place)
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / 'manifest.json'
PAGES = 'https://nakamura196.github.io/hyakki-video-layers/'
ITEM = 'https://da.dl.itc.u-tokyo.ac.jp/portal/assets/fbd0479b-dbb4-4eaa-95b8-f27e1c423e4b'
SOURCE_MANIFEST = 'https://da.dl.itc.u-tokyo.ac.jp/portal/repo/iiif/fbd0479b-dbb4-4eaa-95b8-f27e1c423e4b/manifest'
REUSE = 'https://www.lib.u-tokyo.ac.jp/ja/library/general/reuse'
IMAGE_SERVICE = 'https://iiif.dl.itc.u-tokyo.ac.jp/iiif/hyakki/images/hyakki.tif'
USECASE = {'ja': 'https://kasane.ldas.jp/ja/usecases/hyakki-video-layers/', 'en': 'https://kasane.ldas.jp/en/usecases/hyakki-video-layers/'}
REPO = 'https://github.com/nakamura196/hyakki-video-layers'
PROMPTS = json.loads((ROOT / 'scripts' / 'prompts.json').read_text())

# Models, as Google Flow names them. Most clips are Omni; Omni refused some crops (Google's policy on sexual content,
# likely the nearly naked figures), and for one crop it ignored the start frame, so those were made with Veo 3.1 Fast.
MODELS = {
    'omni': {'ja': 'Gemini Omni 1.2 Flash、Google Flow', 'en': 'Gemini Omni 1.2 Flash, Google Flow'},
    'veo': {'ja': 'Veo 3.1 Fast、Google Flow', 'en': 'Veo 3.1 Fast, Google Flow'},
}
VEO_NOTE_TEXT = ('この動画は Veo 3.1 Fast で作った（Gemini Omni 1.2 Flash では作れなかったため）。'
                '始まりと終わりのコマは原資料と同じだが、途中で人物が太い線の別の絵柄に描き直され、配置も変わる。'
                '原資料に無いものが現れ、元の人物が消える所もある',
                'This clip was made with Veo 3.1 Fast, because Gemini Omni 1.2 Flash could not make it. '
                'Its first and last frames match the original, but in between the figures are redrawn in a different style with bolder lines, '
                'and their layout changes. Things not in the picture appear, and some figures of the original disappear')

# Short names for the list of clips (file name → ja, en), from scripts/prompts.json
LABELS = {k: (v['label_ja'], v['label_en']) for k, v in PROMPTS.items()}


def lang(ja, en):
    return {'ja': [ja], 'en': [en]}


POST = ('動画は、切り出した範囲に合わせて端を切り、色を原資料に合わせたうえで、二つの処理をしている。'
        '(a) 縁の帯（幅 24 画素、内側へ 96 画素でなじませる）は原資料の画素に置き換えた。'
        '(b) 動いている所だけ動画を使い、ほかは原資料の画素のままにした。動いている所は、ぼかした明るさが時間の中央値から 6 を超えてずれる画素を、'
        '24 画素広げ、32 画素でぼかして決めた（動画 1 本につき 1 枚の範囲）。そのため、止まっている紙や線は原資料のままで、ちらつかない',
        'Each clip was trimmed to its region and colour-matched to the original, then two steps were applied. '
        '(a) A band at the edge (24 px, blended over 96 px inwards) is replaced with the pixels of the original. '
        '(b) Only the parts that move come from the video; everything else is the original pixels. The moving parts are the pixels whose blurred '
        'brightness deviates from the temporal median by more than 6, grown by 24 px and feathered by 32 px (one mask per clip). '
        'So the still paper and lines are the original and do not flicker')


def entry(label_ja, label_en, value_ja, value_en=None):
    return {'label': lang(label_ja, label_en), 'value': lang(value_ja, value_en if value_en is not None else value_ja)}


VEO_NOTE = lang(*VEO_NOTE_TEXT)


def a(url, text):
    return f'<a href="{url}">{text}</a>'


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration',
                          '-of', 'json', str(path)], check=True, capture_output=True, text=True).stdout
    j = json.loads(out)
    s = j['streams'][0]
    return s['width'], s['height'], round(float(j['format']['duration']), 3)


m = json.loads(MANIFEST.read_text())
canvas = m['items'][0]
pages = {p['id'].rsplit('/', 1)[-1]: p for p in canvas['items']}
videos = pages['videos']['items']
names = [v['body']['id'].rsplit('/', 1)[-1].removesuffix('.mp4') for v in videos]
missing = [n for n in names if n not in PROMPTS]
if missing:
    raise SystemExit(f'no prompt for {missing}')
veo = [n.removeprefix('video_') for n in names if PROMPTS[n]['model'] == 'veo']
n_veo, n_omni = len(veo), len(names) - len(veo)
veo_ja, veo_en = '・'.join(veo), ', '.join(veo)

new = {
    '@context': m['@context'],
    'id': m['id'],
    'type': 'Manifest',
    'label': lang('百鬼夜行図（改変版：AI 生成の動画を重ねたもの）',
                  'Hyakki Yagyō-zu (Night Parade of One Hundred Demons), modified: with AI-generated video layers'),
    'summary': lang(
        '【AI 生成のコンテンツを含む改変版です】'
        f'東京大学総合図書館が所蔵する絵巻『百鬼夜行図』の画像に、絵の一部を AI で動かした 8 秒の動画 {len(videos)} 本を、'
        '切り出した元の場所に重ねたマニフェストです。'
        '動画の動き・音・細部は AI が作ったもので、原資料に描かれたものでも、学術的な復元でもありません。'
        '原資料の画像そのものには手を加えておらず、東京大学の IIIF Image API から読み込んでいます。'
        '原資料の姿を確かめるときや研究の典拠には、動画を隠すか、原資料のマニフェストをご覧ください。'
        'IIIF Cookbook のレシピ 0036（複数の画像からの合成）と同じ形で、'
        '追加の画像の代わりに動画（Video）を、#xywh で Canvas の一部に描いています。Canvas には duration を持たせていません。'
        '各動画の summary には、動画を作るときに使った動きの指示文が入っています。',
        '[A modified version that contains AI-generated content] '
        f'The handscroll Hyakki Yagyō-zu, held by The University of Tokyo General Library, with {len(videos)} eight-second '
        'AI-generated clips placed back on the regions of the picture they were made from. '
        'The motion, sound and details of the clips were made by AI: they are not in the original, and they are not a scholarly reconstruction. '
        'The image of the original itself is not altered; it is loaded from the IIIF Image API of The University of Tokyo. '
        'To see the original as it is, or to cite it in research, hide the clips or use the original manifest. The manifest has the shape of '
        'IIIF Cookbook recipe 0036 (Composition from Multiple Images): each added resource is a Video, painted on a region '
        'of the Canvas with #xywh. The Canvas has no duration. The summary of each clip is the motion prompt used to generate it.'),
    'metadata': [
        entry('資料名', 'Title', '百鬼夜行図（ヒャッキヤコウズ）', 'Hyakki Yagyō-zu (百鬼夜行図)'),
        entry('別資料名', 'Alternative title', '百鬼夜行絵巻', 'Hyakki Yagyō emaki (百鬼夜行絵巻)'),
        entry('編著者', 'Creator', '藤原行秀 [原] 筆; 源廣迢 [摸] 冩'),
        entry('書写年', 'Date', '[江戸中期]', 'Mid Edo period'),
        entry('形態', 'Physical description', '紙本著色 絵巻 1軸; 28cm', 'Handscroll, colour on paper, 1 scroll; 28 cm'),
        entry('請求記号', 'Call number', 'A00:6275'),
        entry('所蔵', 'Holding institution', '東京大学総合図書館', 'The University of Tokyo General Library'),
        entry('原資料', 'Original',
              f'{a(ITEM, "東京大学デジタルアーカイブポータル")}（{a(SOURCE_MANIFEST, "IIIF マニフェスト")}）',
              f'{a(ITEM, "The University of Tokyo Digital Archive Portal")} ({a(SOURCE_MANIFEST, "IIIF manifest")})'),
        entry('画像の利用条件', 'Image terms of use', a(REUSE, '東京大学総合図書館「画像データ等の利用について」'),
              a(REUSE, 'The University of Tokyo General Library, Use of Digital Contents')),
        entry('AI 生成のコンテンツ', 'AI-generated content',
              '重ねた動画はすべて AI が生成したもので、原資料には含まれません。'
              '動き・表情・音（効果音や環境音）・原画に無い細部は AI の想像で、原画の作者の意図や、当時の見せ方を示すものではありません。'
              '形や色が原画と違う所や、原画に無いものが現れる所があります。',
              'All the clips are AI-generated and are not part of the original. '
              "Their motion, expressions, sound (effects and ambience) and any details not in the picture are the AI's invention; "
              'they do not show what the original artist intended or how the scroll was presented. '
              'Shapes and colours differ from the picture in places, and things not in the picture appear.'),
        entry('改変の内容', 'Modifications',
              '(1) 原資料の画像から、人物・妖怪の描かれた範囲を切り出した。'
              '(2) 切り出した画像を始まりと終わりの両方のコマに指定し、動きの指示文とともに AI で 8 秒の動画を作った。'
              '(3) 縁は原資料の画素に置き換え、動いている所だけ動画を使い、ほかは原資料の画素のままにした（下の「後処理」）。'
              '(4) 切り出した元の範囲（#xywh）に重ねた。原資料の画像は変えていない。',
              '(1) Regions with figures were cropped from the image of the original. '
              '(2) Each crop was given as both the start frame and the end frame, and turned into an 8-second clip by AI with a motion prompt. '
              '(3) The edge was replaced with the pixels of the original, and only the moving parts were taken from the video; everything else is the original pixels (see Post-processing). '
              '(4) The clips were painted back on the regions they were cropped from (#xywh). The image of the original is unchanged.'),
        entry('後処理', 'Post-processing', POST[0], POST[1]),
        entry('動画', 'Clips',
              f'{len(videos)} 本、各 8 秒、音あり。絵の一部を切り出した画像と動きの指示文から、Google Flow で生成した。'
              f'{n_omni} 本は Gemini Omni 1.2 Flash、{n_veo} 本（{veo_ja}）は Veo 3.1 Fast（Omni では作れなかったため。途中で絵柄が描き直される）。'
              '指示文は Claude（Anthropic）が、切り出した画像を見て場面ごとに書いた。人物を位置と衣で名指しし、入れ替わらずに大きく動くよう指示している。',
              f'{len(videos)} clips, 8 seconds each, with sound. Generated in Google Flow from a crop of the picture and a motion prompt. '
              f'{n_omni} were made with Gemini Omni 1.2 Flash and {n_veo} ({veo_en}) with Veo 3.1 Fast, because Omni could not make them; those are redrawn in between. '
              'The prompts were written by Claude (Anthropic) for each scene from the crop. They name each figure by its place and clothing, '
              'and ask it to move clearly without turning into another figure.'),
        entry('作成', 'Made by', '中村 覚（東京大学）', 'Satoru Nakamura (The University of Tokyo)'),
        entry('関連', 'Related',
              f'{a(USECASE["ja"], "IIIF Kasane のユースケース")}、{a(REPO, "GitHub のリポジトリ")}',
              f'{a(USECASE["en"], "IIIF Kasane use case")}, {a(REPO, "GitHub repository")}'),
    ],
    'requiredStatement': entry('帰属表示', 'Attribution',
                               '『百鬼夜行図』（東京大学総合図書館所蔵）を改変。重ねた動画は、この画像をもとに AI（Gemini Omni 1.2 Flash・Veo 3.1 Fast、Google Flow）が生成したもので、原資料には含まれない',
                               'Hyakki Yagyō-zu (The University of Tokyo General Library), modified. The clips are generated by AI (Gemini Omni 1.2 Flash and Veo 3.1 Fast, Google Flow) from this image and are not part of the original'),
    'provider': [
        {
            'id': 'https://www.lib.u-tokyo.ac.jp/',
            'type': 'Agent',
            'label': lang('東京大学総合図書館', 'The University of Tokyo General Library'),
            'homepage': [{'id': 'https://www.lib.u-tokyo.ac.jp/', 'type': 'Text', 'format': 'text/html',
                          'label': lang('東京大学総合図書館', 'The University of Tokyo General Library')}],
        },
        {
            'id': 'https://github.com/nakamura196',
            'type': 'Agent',
            'label': lang('中村 覚（東京大学）', 'Satoru Nakamura (The University of Tokyo)'),
            'homepage': [{'id': 'https://github.com/nakamura196', 'type': 'Text', 'format': 'text/html',
                          'label': lang('中村 覚（GitHub）', 'Satoru Nakamura (GitHub)')}],
        },
    ],
    'homepage': [{'id': PAGES, 'type': 'Text', 'format': 'text/html', 'label': lang('このマニフェストの説明', 'About this manifest')}],
    'thumbnail': [],  # filled below
    'viewingDirection': m.get('viewingDirection', 'right-to-left'),
    'items': m['items'],
}

# thumbnail: the region of the kappa-like demon (video_005), from the IIIF Image API
kappa = next(v for v in videos if v['body']['id'].endswith('video_005.mp4'))
x, y, w, h = map(int, kappa['target'].split('#xywh=')[1].split(','))
th = 400
new['thumbnail'] = [{'id': f'{IMAGE_SERVICE}/{x},{y},{w},{h}/,{th}/0/default.jpg', 'type': 'Image', 'format': 'image/jpeg',
                     'width': round(w * th / h), 'height': th,
                     'service': [{'id': IMAGE_SERVICE, 'type': 'ImageService2', 'profile': 'level2'}]}]

canvas_new = {'id': canvas['id'], 'type': 'Canvas', 'label': lang('百鬼夜行図', 'Hyakki Yagyō-zu'),
              'summary': lang('原資料の画像（全巻）の上に、AI が生成した動画を重ねている',
                              'The image of the whole scroll, with AI-generated clips painted on it')}
canvas_new.update({k: v for k, v in canvas.items() if k not in ('id', 'type', 'label')})
new['items'] = [canvas_new]

# Each clip says it is AI-generated, and with which model: in its summary (shown in viewers' layer lists) and in its own metadata.
def prefix(model):
    return {'ja': f'AI（{MODELS[model]["ja"]}）が生成した動画。原資料には無い。動きの指示文：',
            'en': f'AI-generated clip ({MODELS[model]["en"]}), not part of the original. Motion prompt: '}


for v in videos:
    b = v['body']
    name = b['id'].rsplit('/', 1)[-1].removesuffix('.mp4')
    if name not in LABELS:
        raise SystemExit(f'no label for {name}')
    width, height, duration = probe(ROOT / 'videos' / f'{name}.mp4')
    ja, en = LABELS[name]
    p = PROMPTS[name]
    model = p['model']
    pre = prefix(model)
    region = v['target'].split('#xywh=')[1]
    meta = [
        entry('種類', 'Type', f'AI 生成の動画（{MODELS[model]["ja"]}）。原資料には含まれない',
              f'AI-generated video ({MODELS[model]["en"]}), not part of the original'),
        entry('もとにした範囲', 'Made from', f'原資料の画像の xywh={region} を切り出したもの。始まりと終わりのコマに指定した',
              f'A crop of the image of the original, xywh={region}, given as both the start and the end frame'),
        entry('後処理', 'Post-processing', '縁は原資料の画素。動いている所だけ動画で、ほかは原資料の画素',
              'The edge is the original pixels; only the moving parts come from the video, everything else is the original pixels'),
        entry('動きの指示文', 'Motion prompt', p['ja'], p['en']),
    ]
    if model == 'veo':
        meta.insert(1, {'label': lang('注意', 'Note'), 'value': VEO_NOTE})
    v['body'] = {'id': b['id'], 'type': 'Video', 'format': b.get('format', 'video/mp4'),
                 'width': width, 'height': height, 'duration': duration,
                 'label': lang(ja, en),
                 'summary': {'ja': [pre['ja'] + p['ja']], 'en': [pre['en'] + p['en']]},
                 'metadata': meta}

MANIFEST.write_text(json.dumps(new, ensure_ascii=False, indent=2) + '\n')
print(f'{len(videos)} videos, {len(new["metadata"])} metadata entries → {MANIFEST}')
