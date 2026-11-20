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

# Short names for the list of clips (file name → ja, en)
LABELS = {
    'video_002': ('燃える器を抱えてよろめく白髪の鬼', 'White-haired demon staggering with a flaming vessel'),
    'video_003': ('跳ね回る木の箱と、引き出しの妖怪', 'Bouncing wooden chest with spirits in its drawers'),
    'video_004': ('踊りながら練り歩く三体の妖怪', 'Three yōkai dancing in procession'),
    'video_005': ('蓮の葉を掲げて歩く河童のような鬼', 'Kappa-like demon holding up a lotus leaf'),
    'video_006': ('シンバルを打ち鳴らして踊る鬼', 'Demon dancing with cymbals'),
    'video_007': ('緑の縄を振り回す赤い顔の鬼', 'Red-faced demon swinging a green rope'),
    'video_008': ('頭に皿を載せ、蝋燭を持って揺れる妖怪', 'Candle-bearing yōkai balancing a dish on its head'),
    'video_009': ('空をうねって進む白い龍', 'White dragon undulating through the air'),
    'video_010': ('霧の中を漂う黒髪の細長い妖怪', 'Long dark-haired yōkai floating in the mist'),
    'video_011': ('うねりながら進む蛇のような龍', 'Serpentine dragon slithering forward'),
    'video_012': ('逃げる人を追う荒い髪の鬼', 'Wild-haired demon chasing a fleeing man'),
    'video_013': ('舞う巫女と、首を伸ばす大きな亀', 'Dancing miko and a large turtle stretching its neck'),
    'video_014': ('練り歩く異形の鬼と精霊', 'Grotesque demons and spirits in procession'),
    'video_015': ('右から左へ行進する妖怪たち', 'Yōkai marching from right to left'),
    'video_016': ('巻物を持つターバンの者、青い衣の獣、杖を握る赤い鬼', 'Turbaned figure with a scroll, blue-robed beast and red demon with a staff'),
    'video_017': ('白い布を掲げて退く角の鬼と、しゃがむ斑の妖怪', 'Horned demon backing away with a white cloth, and a spotted yōkai'),
    'video_018': ('炎が踊る、揺れる籠', 'Swaying basket with dancing flames'),
    'video_019': ('衣をなびかせて跳ぶ角のある鬼', 'Horned demon leaping with flowing robes'),
    'video_020': ('大きな弓を構えて進む弓矢の付喪神', 'Bow-and-arrow tsukumogami striding with a large bow'),
}


def lang(ja, en):
    return {'ja': [ja], 'en': [en]}


def entry(label_ja, label_en, value_ja, value_en=None):
    return {'label': lang(label_ja, label_en), 'value': lang(value_ja, value_en if value_en is not None else value_ja)}


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
              '(1) 原資料の画像から、人物・妖怪の描かれた範囲を切り出した。(2) 切り出した画像と動きの指示文から、AI で 8 秒の動画を作った。'
              '(3) 動画の端を切りそろえ、切り出した元の範囲（#xywh）に重ねた。原資料の画像は変えていない。',
              '(1) Regions with figures were cropped from the image of the original. (2) Each crop and a motion prompt were turned into an 8-second clip by AI. '
              '(3) The clips were trimmed and painted back on the regions they were cropped from (#xywh). The image of the original is unchanged.'),
        entry('動画', 'Clips',
              f'{len(videos)} 本、各 8 秒、音あり。絵の一部を切り出した画像と動きの指示文から、Google Veo 3 で生成した。'
              '指示文は Claude Sonnet が、資料の説明と切り出した画像をもとに書いた。',
              f'{len(videos)} clips, 8 seconds each, with sound. Generated with Google Veo 3 from a crop of the picture and a motion prompt. '
              'The prompts were written by Claude Sonnet from a description of the scroll and the crop.'),
        entry('作成', 'Made by', '中村 覚（東京大学）', 'Satoru Nakamura (The University of Tokyo)'),
        entry('関連', 'Related',
              f'{a(USECASE["ja"], "IIIF Kasane のユースケース")}、{a(REPO, "GitHub のリポジトリ")}',
              f'{a(USECASE["en"], "IIIF Kasane use case")}, {a(REPO, "GitHub repository")}'),
    ],
    'requiredStatement': entry('帰属表示', 'Attribution',
                               '『百鬼夜行図』（東京大学総合図書館所蔵）を改変。重ねた動画は、この画像をもとに AI（Google Veo 3）が生成したもので、原資料には含まれない',
                               'Hyakki Yagyō-zu (The University of Tokyo General Library), modified. The clips are generated by AI (Google Veo 3) from this image and are not part of the original'),
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

# Each clip says it is AI-generated: in its summary (shown in viewers' layer lists) and in its own metadata.
# The prompt is kept after the prefix; on a re-run the prefix is taken off first.
PREFIX = {'ja': 'AI（Google Veo 3）が生成した動画。原資料には無い。動きの指示文：',
          'en': 'AI-generated clip (Google Veo 3), not part of the original. Motion prompt: '}


def prompt_of(text, key):
    return text[len(PREFIX[key]):] if text.startswith(PREFIX[key]) else text


for v in videos:
    b = v['body']
    name = b['id'].rsplit('/', 1)[-1].removesuffix('.mp4')
    if name not in LABELS:
        raise SystemExit(f'no label for {name}')
    width, height, duration = probe(ROOT / 'videos' / f'{name}.mp4')
    ja, en = LABELS[name]
    prompts = {k: prompt_of(t[0], k) for k, t in b['summary'].items()}
    region = v['target'].split('#xywh=')[1]
    v['body'] = {'id': b['id'], 'type': 'Video', 'format': b.get('format', 'video/mp4'),
                 'width': width, 'height': height, 'duration': duration,
                 'label': lang(ja, en),
                 'summary': {k: [PREFIX[k] + t] for k, t in prompts.items()},
                 'metadata': [
                     entry('種類', 'Type', 'AI 生成の動画（Google Veo 3）。原資料には含まれない',
                           'AI-generated video (Google Veo 3), not part of the original'),
                     entry('もとにした範囲', 'Made from', f'原資料の画像の xywh={region} を切り出したもの',
                           f'A crop of the image of the original, xywh={region}'),
                     entry('動きの指示文', 'Motion prompt', prompts['ja'], prompts['en']),
                 ]}

MANIFEST.write_text(json.dumps(new, ensure_ascii=False, indent=2) + '\n')
print(f'{len(videos)} videos, {len(new["metadata"])} metadata entries → {MANIFEST}')
