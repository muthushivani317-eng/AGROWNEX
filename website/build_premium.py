"""AgrowNex premium site: home, solutions and one page per business engine.

Run:  python website/build_premium.py   (also rebuilds the inner pages via build_pages)
"""
import re

from build_pages import W, t, page, seo_head, SOLUTIONS, SITE_URL, ORG  # noqa: F401  (import also rebuilds old pages)

IMG = '/assets/img/x/'


# ---------------------------------------------------------------- small helpers
def kick(ta, en):
    return f'<p class="kicker" lang="ta">{ta}</p><p class="kicker" lang="en">{en}</p>'


def h2(ta, en):
    return f'<h2 lang="ta">{ta}</h2><h2 lang="en">{en}</h2>'


def para(ta, en, cls='intro'):
    return f'<p class="{cls}" lang="ta">{ta}</p><p class="{cls}" lang="en">{en}</p>'


ICON = {
    'seed': '<path d="M12 21V11M12 11c0-4 3-7 8-7 0 5-3 7-8 7zM12 14c0-3-2.5-5-7-5 0 4 2.5 5 7 5z"/>',
    'drop': '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
    'shield': '<path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/>',
    'leaf': '<path d="M5 19c0-9 6-14 15-14 0 9-5 15-14 15"/><path d="M5 19l8-8"/>',
    'gear': '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/>',
    'truck': '<path d="M3 6h11v10H3zM14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
    'scan': '<path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3M4 12h16"/>',
    'chat': '<path d="M4 5h16v11H9l-5 4z"/>',
    'cloud': '<path d="M7 18a5 5 0 1 1 1-9.9A6 6 0 0 1 19 10a4 4 0 0 1-1 8z"/>',
    'chart': '<path d="M4 20V4M4 20h16M8 16v-4M12 16V8M16 16v-6"/>',
    'phone': '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
    'flask': '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/>',
    'ship': '<path d="M3 17l2 4h14l2-4zM6 17V9h12v8M9 9V5h6v4"/>',
    'box': '<path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
    'store': '<path d="M3 9l2-5h14l2 5M4 9v11h16V9M9 20v-6h6v6"/>',
    'bank': '<path d="M3 9l9-5 9 5M5 9v9M10 9v9M14 9v9M19 9v9M3 20h18"/>',
    'umbrella': '<path d="M3 12a9 9 0 0 1 18 0zM12 12v7a2 2 0 0 1-4 0"/>',
    'card': '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18"/>',
    'tag': '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
    'star': '<path d="M12 3l2.7 5.6 6.3.9-4.5 4.4 1 6.1L12 17l-5.5 3 1-6.1L3 9.5l6.3-.9z"/>',
    'doc': '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h7M9 17h7"/>',
    'users': '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.5"/><path d="M16 14c3 0 5 2.2 5 5"/>',
    'tractor': '<circle cx="7" cy="16" r="4"/><circle cx="18" cy="17" r="3"/><path d="M7 12V5h6l2 7h5v5M3 12h8"/>',
    'cert': '<circle cx="12" cy="9" r="5"/><path d="M9 13l-2 8 5-3 5 3-2-8"/>',
    'globe': '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
    'drone': '<rect x="9" y="10" width="6" height="4" rx="1"/><path d="M9 11L5 7M15 11l4-4M9 13l-4 4M15 13l4 4"/><circle cx="5" cy="7" r="2"/><circle cx="19" cy="7" r="2"/><circle cx="5" cy="17" r="2"/><circle cx="19" cy="17" r="2"/>',
    'tree': '<path d="M12 21v-6M12 3l6 8h-3l4 5H5l4-5H6z"/>',
}


def ico(name):
    return (f'<div class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICON[name]}</svg></div>')


STATUS = {'live': ('இப்போது', 'Live now'), 'next': ('அடுத்து', 'Next'), 'later': ('பின்னர்', 'Later')}


def features(items, cls=''):
    out = []
    for it in items:
        icon, ta, en, dta, den = it[:5]
        st = it[5] if len(it) > 5 else None
        badge = f'<span class="status {st}">{t(*STATUS[st])}</span>' if st else ''
        out.append(f'<div class="feature reveal">{ico(icon)}{badge}<b lang="ta">{ta}</b><b lang="en">{en}</b>'
                   f'<p lang="ta">{dta}</p><p lang="en">{den}</p></div>')
    return f'<div class="features {cls}">{"".join(out)}</div>'


def flow(steps, cls=''):
    lis = ''.join(f'<li><b lang="ta">{a}</b><b lang="en">{b}</b><span lang="ta">{c}</span><span lang="en">{d}</span></li>'
                  for a, b, c, d in steps)
    return f'<ol class="flow {cls}">{lis}</ol>'


def checks(items):
    return '<ul class="checks">' + ''.join(
        f'<li lang="ta"><span><b>{a}</b> {c}</span></li><li lang="en"><span><b>{b}</b> {d}</span></li>'
        for a, b, c, d in items) + '</ul>'


def chips(items):
    return '<ul class="chips">' + ''.join(f'<li>{t(a, b)}</li>' for a, b in items) + '</ul>'


def media(img, alt, video=None, badge=None):
    if video:
        m = (f'<img src="{img}" alt="{alt}" width="1344" height="752" loading="lazy" style="position:absolute;inset:0">'
             f'<video muted loop playsinline preload="none" aria-hidden="true" poster="{img}" data-loop="{video}" style="position:relative"></video>')
    else:
        m = f'<img src="{img}" alt="{alt}" width="1344" height="752" loading="lazy">'
    b = ''
    if badge:
        b = f'<div class="badge"><b>{t(badge[0], badge[1])}</b>{t(badge[2], badge[3])}</div>'
    return f'<figure class="media-card reveal" style="margin:0">{m}{b}</figure>'


def cta(ta, en, lta, len_, actions):
    return f'''  <section class="band">
    <div class="wrap">
      <div class="cta reveal">
        {h2(ta, en)}
        {para(lta, len_, '')}
        <div class="hero-actions">{actions}</div>
      </div>
    </div>
  </section>'''


def btn(href, ta, en, cls='btn-soil'):
    return f'<a class="btn {cls}" href="{href}">{t(ta, en)}</a>'


def sub_hero(img, alt, crumb_ta, crumb_en, h_ta, h_en, l_ta, l_en, actions='', video=None):
    vid = (f'<video muted loop playsinline preload="none" aria-hidden="true" poster="{img}" data-loop="{video}"></video>'
           if video else '')
    return f'''  <section class="hero hero-page hero-sub hero-premium" id="top">
    <div class="hero-media"><img src="{img}" alt="{alt}" width="1344" height="752">{vid}</div>
    <div class="wrap">
      <p class="crumb"><a href="/solutions">{t("தீர்வுகள்", "Solutions")}</a> / {t(crumb_ta, crumb_en)}</p>
      <h1 lang="ta">{h_ta}</h1>
      <h1 lang="en">{h_en}</h1>
      <p class="lede" lang="ta">{l_ta}</p>
      <p class="lede" lang="en">{l_en}</p>
      {f'<div class="hero-actions">{actions}</div>' if actions else ''}
    </div>
  </section>'''


ORDER = [s for s in SOLUTIONS]


def pager(slug):
    i = [s[0] for s in ORDER].index(slug)
    prev, nxt = ORDER[i - 1], ORDER[(i + 1) % len(ORDER)]
    return f'''  <section class="band band-mist" style="padding-block:48px">
    <div class="wrap pager">
      <a href="/{prev[0]}"><small>{t("முந்தையது", "Previous")}</small><b>← {t(prev[2], prev[3])}</b></a>
      <a href="/{nxt[0]}"><small>{t("அடுத்தது", "Next")}</small><b>{t(nxt[2], nxt[3])} →</b></a>
    </div>
  </section>'''


def service_ld(name, desc, slug):
    return {"@type": "Service", "@id": f"{SITE_URL}/{slug}#service", "name": name, "description": desc,
            "provider": {"@id": SITE_URL + "/#org"}, "areaServed": {"@type": "State", "name": "Tamil Nadu"},
            "url": f"{SITE_URL}/{slug}"}


def write(slug, html):
    (W / f'{slug}.html').write_text(html, encoding='utf-8')
    print('wrote', slug, len(html))


TALK = btn('/contact', 'எங்களுடன் பேசுங்கள்', 'Talk to us')
PARTNER = btn('/partners#join', 'கூட்டாளராகுங்கள்', 'Become a partner', 'btn-ghost')

# ================================================================= HOME
engine_cards = [
    ('inputs', 'inputs.jpg', 'விதை முதல் சொட்டு நீர் வரை — FPO, கூட்டாளர் கடைகள் மூலம் நம்பகமான இடுபொருட்கள்.',
     'Seeds to drip kits — trusted inputs through FPOs and partner shops.', ''),
    ('advisory', 'scan.jpg', 'இலைப் படத்தில் நோய் கண்டறிதல், தமிழில் AI உதவி, வானிலை, மண்டி விலை — இலவசம்.',
     'Leaf-photo disease checks, Tamil AI help, weather and mandi prices — free.', 'wide'),
    ('produce', 'warehouse.jpg', 'விவசாயக் குழுக்களின் விளைச்சலைப் பெரிய வாங்குபவர்களுக்கும் வெளிநாட்டுக்கும்.',
     "Farmer groups' harvests to large buyers and overseas markets.", ''),
    ('finance', 'finance.jpg', 'வங்கி, காப்பீட்டுக் கூட்டாளர்கள் மூலம் கடனும் காப்பீடும்.',
     'Credit and insurance through regulated banks and insurers.', ''),
    ('brands', 'brands.jpg', 'AgrowNex பெயரில் மசாலா, GI பொருட்கள், கருவிகள்.',
     'Spices, GI products and equipment under the AgrowNex name.', ''),
    ('export-support', 'port.jpg', 'FPO-க்கள் முதல் முறையாக ஏற்றுமதி செய்ய முழு உதவி.',
     'End-to-end help for FPOs shipping abroad for the first time.', 'wide'),
    ('programmes', 'training.jpg', 'பயிற்சி, கருவி வாடகை, இயற்கைச் சான்றிதழ் உதவி.',
     'Training, equipment hire and organic certification support.', 'wide'),
    ('future', 'carbon.jpg', 'கார்பன் வரவுகள், சந்தை அறிக்கைகள், இறக்குமதி, ட்ரோன் இணைப்பு.',
     'Carbon credits, market insights, imports and drone assembly.', 'future wide'),
]
SOL = {s[0]: s for s in SOLUTIONS}


def engine_grid():
    cards = []
    for slug, img, dta, den, cls in engine_cards:
        s = SOL[slug]
        num = t('எதிர்காலம்', 'Future') if slug == 'future' else f'ENGINE {s[1]}'
        cards.append(f'''<a class="engine reveal {cls}" href="/{slug}"><img src="{IMG}{img}" alt="" width="1344" height="752" loading="lazy">
          <span class="num">{num}</span><div class="body"><h3>{t(s[2], s[3])}</h3><p lang="ta">{dta}</p><p lang="en">{den}</p>
          <span class="go">{t("மேலும் →", "Explore →")}</span></div></a>''')
    return '<div class="engines">' + '\n        '.join(cards) + '</div>'


CROPS = [('வாழை', 'Banana'), ('காய்ந்த மிளகாய்', 'Dry chilli'), ('நெல்', 'Paddy'), ('தேங்காய்', 'Coconut'),
         ('நிலக்கடலை', 'Groundnut'), ('உளுந்து', 'Black gram'), ('பருத்தி', 'Cotton'), ('வெங்காயம்', 'Onion'),
         ('மஞ்சள்', 'Turmeric'), ('பனை வெல்லம்', 'Palm jaggery'), ('முருங்கை', 'Moringa'), ('மாம்பழம்', 'Mango')]
marquee_items = ''.join(f'<span>{t(a, b)}</span>' for a, b in CROPS)

home_body = f'''  <section class="hero hero-premium" id="top">
    <div class="hero-media">
      <img src="{IMG}aerial.jpg" alt="" width="1344" height="752">
      <video muted loop playsinline preload="none" aria-hidden="true" poster="{IMG}aerial.jpg" data-loop="/assets/video/aerial.mp4" data-loop-mobile="/assets/video/aerial-mobile.mp4"></video>
    </div>
    <div class="wrap">
      <p class="hero-tag"><b>AGRITECH</b>{t("தூத்துக்குடி · தமிழ்நாடு", "Thoothukudi · Tamil Nadu")}</p>
      <h1 lang="ta">விதை முதல் <em>விற்பனை வரை,</em> ஒரே தளம்.</h1>
      <h1 lang="en">From seed <em>to sale,</em> one platform.</h1>
      <p class="lede" lang="ta">AI ஆலோசனை, தரமான இடுபொருட்கள், நியாயமான சந்தை, கடன், ஏற்றுமதி — தென் தமிழக விவசாயிகளுக்கும் FPO-க்களுக்கும் ஒரே நிறுவனம்.</p>
      <p class="lede" lang="en">AI advice, quality inputs, fair markets, credit and export — one company for South Tamil Nadu's farmers and FPOs.</p>
      <div class="hero-actions">
        {btn('/solutions', 'எங்கள் தீர்வுகள்', 'Explore our solutions')}
        {btn('/app', 'செயலியைப் பாருங்கள்', 'See the app', 'btn-ghost')}
      </div>
    </div>
    <span class="scroll-cue" aria-hidden="true"></span>
  </section>

  <section class="band" style="padding-top:0">
    <div class="wrap">
      <div class="stats reveal">
        <div><b data-count="5000" data-suffix="+">5,000+</b><span>{t("முதல் ஆண்டு இலக்கு — விவசாயிகள்", "Farmers — year-one target")}</span></div>
        <div><b data-count="5">5</b><span>{t("கூட்டாளர் FPO-க்கள்", "Partner FPOs")}</span></div>
        <div><b data-count="50">50</b><span>{t("கூட்டாளர் கடைகள்", "Partner shops")}</span></div>
        <div><b data-count="7">7</b><span>{t("வணிகப் பிரிவுகள், ஒரே தளம்", "Business engines, one platform")}</span></div>
      </div>
    </div>
  </section>

  <div class="marquee" aria-hidden="true"><div class="marquee-track">{marquee_items}{marquee_items}</div></div>

  <section class="band" id="solutions">
    <div class="wrap">
      {kick("ஏழு பிரிவுகள்", "Seven engines")}
      {h2("ஒரு விவசாயிக்குத் தேவையான அனைத்தும், ஒரே இடத்தில்.", "Everything a farmer needs, under one roof.")}
      {para("இலவச ஆலோசனை விவசாயிகளை அழைத்து வருகிறது. இடுபொருட்கள், சந்தை, கடன், ஏற்றுமதி அவர்களுடன் சேர்ந்து வளர்கின்றன.",
            "Free advice brings farmers in. Inputs, markets, credit and export grow with them.")}
      {engine_grid()}
    </div>
  </section>

  <section class="band band-mist">
    <div class="wrap split">
      <div class="reveal">
        {kick("AgrowNex செயலி", "The AgrowNex app")}
        {h2("இலையைக் காட்டுங்கள். பதில் தமிழில்.", "Show the leaf. Get the answer in Tamil.")}
        {para("ஒரு புகைப்படத்தில் பயிர் நோய், அரசு மண்டி விலை, கிராம வானிலை, இந்த வாரப் பணிகள் — விவசாயிகளுக்கு இலவசம்.",
              "Crop disease from one photo, official mandi prices, village weather and this week's tasks — free for farmers.")}
        {checks([("இயற்கை முறை முதலில்", "Organic care first", "— ரசாயனம் தேவைப்பட்டால் மட்டும்.", "— chemicals only when needed."),
                 ("அதிகாரப்பூர்வ தரவு", "Official data", "— கற்பனை விலைகள் இல்லை.", "— no made-up prices."),
                 ("உறுதியில்லையெனில் சொல்லும்", "Says when it's unsure", "— நிபுணரிடம் அனுப்பும்.", "— and sends you to an expert.")])}
        <p style="margin-top:28px">{btn('/app', 'செயலி விவரம்', 'Explore the app')}</p>
      </div>
      {media(IMG + 'scan.jpg', 'A farmer scanning a chilli leaf with the AgrowNex app', '/assets/video/scan.mp4',
             ('தமிழில்', 'In Tamil', 'நோய் · விலை · வானிலை', 'Disease · prices · weather'))}
    </div>
  </section>

  <section class="band band-ink">
    <div class="wrap">
      {kick("எப்படி இணைகிறது", "How it fits together")}
      {h2("வயலிலிருந்து சந்தை வரை, ஒவ்வொரு படியிலும்.", "With the farmer at every step, field to market.")}
      {flow([("ஆலோசனை", "Advise", "AI பயிர் மருத்துவர், வானிலை, பணிகள்.", "AI crop doctor, weather, tasks."),
             ("இடுபொருள்", "Supply", "சரியான விதை, உரம், பாதுகாப்பு.", "The right seed, nutrition and care."),
             ("நிதி", "Finance", "கூட்டாளர் வங்கிகள் மூலம் கடன், காப்பீடு.", "Credit and insurance via partners."),
             ("விற்பனை", "Sell", "பெரிய வாங்குபவர்கள், ஏற்றுமதி.", "Large buyers and export."),
             ("மதிப்புக் கூட்டல்", "Add value", "பிராண்ட், பதப்படுத்தல், GI.", "Brands, processing, GI.")])}
    </div>
  </section>

  <section class="band">
    <div class="wrap split rev">
      <div class="reveal">
        {kick("உலகச் சந்தை", "Global markets")}
        {h2("தூத்துக்குடி துறைமுகத்திலிருந்து உலகுக்கு.", "From Thoothukudi port to the world.")}
        {para("காய்ந்த மிளகாய், வாழை, தேங்காய், மசாலா — தரம் பிரித்து, கண்டறியக்கூடிய தொகுதிகளாக இலங்கை, UAE மற்றும் பிற நாடுகளுக்கு.",
              "Dry chilli, banana, coconut and spices — graded, traceable lots for Sri Lanka, the UAE and beyond.")}
        {chips([("இலங்கை", "Sri Lanka"), ("UAE", "UAE"), ("வியட்நாம்", "Vietnam"), ("மலேசியா", "Malaysia"), ("சவுதி அரேபியா", "Saudi Arabia"), ("அமெரிக்கா", "USA")])}
        <p style="margin-top:28px">{btn('/produce', 'விளைபொருள், ஏற்றுமதி', 'Produce & export')} {btn('/export-support', 'FPO ஏற்றுமதி உதவி', 'Export support for FPOs', 'btn-line')}</p>
      </div>
      {media(IMG + 'port.jpg', 'Container ship loading at a South Indian port', '/assets/video/port.mp4',
             ('துறைமுகம் அருகில்', 'Port next door', 'தூத்துக்குடி வ.உ.சி. துறைமுகம்', 'V.O. Chidambaranar Port, Thoothukudi'))}
    </div>
  </section>

  <section class="band band-mist">
    <div class="wrap">
      {kick("ஏன் AgrowNex", "Why AgrowNex")}
      {h2("நம்பிக்கையின் மேல் கட்டப்பட்டது.", "Built on trust, not hype.")}
      {features([
        ('chat', 'தமிழ் முதலில்', 'Tamil first', 'எளிய தமிழ், குரல் வசதி, பெரிய எழுத்து.', 'Plain Tamil, voice input and large text.'),
        ('chart', 'அதிகாரப்பூர்வ தரவு', 'Official data', 'Agmarknet விலை, IMD வானிலை, TNAU/ICAR வழிகாட்டல்.', 'Agmarknet prices, IMD weather, TNAU and ICAR guidance.'),
        ('users', 'FPO வழியாக', 'Through FPOs', 'விவசாயக் குழுக்களுடன் இணைந்து, கிராம அளவில்.', 'Working with farmer groups, at village level.'),
        ('shield', 'ஒப்புதல் முதலில்', 'Consent first', 'விவசாயி ஒப்புக்கொண்டால் மட்டுமே தரவுப் பகிர்வு.', 'Farm data is shared only when the farmer agrees.'),
        ('leaf', 'இயற்கை முறை', 'Organic-first', 'இயற்கைத் தீர்வு முதலில், சான்றிதழ் உதவியுடன்.', 'Organic care first, with certification support.'),
        ('store', 'உள்ளூர் கடைகள்', 'Local shops', 'கிராமத்தருகே கூட்டாளர் கடைகள் மூலம் விநியோகம்.', 'Delivered through partner shops near the village.'),
      ])}
    </div>
  </section>

{cta("உங்கள் FPO, கடை அல்லது நிறுவனத்துடன் இணைந்து வளர்வோம்.", "Let's grow together — your FPO, shop or company.",
     "FPO, KVK, வாங்குபவர், இடுபொருள் நிறுவனம், வங்கி — எங்களுடன் பேசுங்கள்.",
     "FPOs, KVKs, buyers, input makers and banks — talk to us.",
     TALK + PARTNER)}
'''

HOME_TITLE = 'AgrowNex – Tamil AI Farming App for Farmers & FPOs | Grow better. Sell better.'
HOME_DESC = ('AgrowNex is a Tamil-first agri-tech platform for farmers and FPOs in South Tamil Nadu – AI crop disease '
             'detection, mandi prices, quality inputs and market linkages.')
home = page('', HOME_TITLE, HOME_DESC, 'home', home_body, og='/assets/img/og.jpg',
            preload=f'\n<link rel="preload" as="image" href="{IMG}aerial.jpg">')
write('index', home)

# ================================================================= SOLUTIONS
sol_body = f'''  <section class="hero hero-page hero-sub hero-premium" id="top">
    <div class="hero-media"><img src="{IMG}drone.jpg" alt="An agricultural drone over green farmland" width="1344" height="752">
      <video muted loop playsinline preload="none" aria-hidden="true" poster="{IMG}drone.jpg" data-loop="/assets/video/drone.mp4"></video></div>
    <div class="wrap">
      <p class="crumb">{t("தீர்வுகள்", "Solutions")}</p>
      <h1 lang="ta">ஏழு பிரிவுகள். <em>ஒரே நோக்கம்.</em></h1>
      <h1 lang="en">Seven engines. <em>One purpose.</em></h1>
      <p class="lede" lang="ta">விவசாயி அதிகம் சம்பாதிக்க வேண்டும், குறைவாக இழக்க வேண்டும். ஒவ்வொரு பிரிவும் அதற்காகவே.</p>
      <p class="lede" lang="en">Help farmers earn more and lose less. Every engine serves that one goal.</p>
    </div>
  </section>

  <section class="band">
    <div class="wrap">
      {kick("எங்கள் தீர்வுகள்", "Our solutions")}
      {h2("ஒவ்வொரு பிரிவும் மற்றதை வலுப்படுத்துகிறது.", "Each engine makes the others stronger.")}
      {engine_grid()}
    </div>
  </section>

  <section class="band band-ink">
    <div class="wrap">
      {kick("இன்று, அடுத்து, பின்னர்", "Now, next, later")}
      {h2("படிப்படியாக வளர்கிறோம்.", "We grow step by step.")}
      <div class="rows">
        <div><b>{t("இப்போது", "Live now")}</b><span>{t("AI ஆலோசனை செயலி · இடுபொருட்கள் · மொத்த வாங்குபவர் இணைப்பு · சொந்த பிராண்ட் கருவிகள்", "AI advisory app · farm inputs · wholesale buyer matching · own-brand equipment")}</span></div>
        <div><b>{t("அடுத்து", "Next")}</b><span>{t("ஏற்றுமதி · கடன், காப்பீடு · பதப்படுத்திய உணவு, GI பொருட்கள் · FPO ஏற்றுமதி உதவி · பயிற்சித் திட்டங்கள்", "Export · credit and insurance · processed foods and GI products · FPO export support · training programmes")}</span></div>
        <div><b>{t("பின்னர்", "Later")}</b><span>{t("கார்பன் வரவுகள் · பயிர், சந்தை அறிக்கைகள் · இறக்குமதி · ட்ரோன், இயந்திர இணைப்பு", "Carbon credits · crop and market insight reports · imports · drone and machine assembly")}</span></div>
      </div>
    </div>
  </section>

{cta("எந்தப் பிரிவு உங்களுக்குப் பொருந்தும்?", "Which engine fits you?",
     "உங்கள் தேவையைச் சொல்லுங்கள் — சரியான குழுவுடன் இணைக்கிறோம்.",
     "Tell us what you need and we'll connect you with the right team.", TALK + PARTNER)}
'''
write('solutions', page('solutions', 'Agritech solutions — inputs, advisory, produce, finance, brands | AgrowNex',
                        'The seven AgrowNex engines: farm inputs, AI advisory, produce and export, finance, own brands, export support and programmes for Tamil Nadu farmers and FPOs.',
                        'solutions', sol_body, og=IMG + 'drone.jpg'))

# ================================================================= ENGINE PAGES
ENGINES = {}

ENGINES['inputs'] = dict(
    title='Farm inputs — seeds, fertiliser, crop protection, drip | AgrowNex',
    desc='Quality seeds, fertiliser, crop protection, organic inputs, irrigation and machinery for Tamil Nadu farmers through FPOs and AgrowNex partner shops.',
    img='inputs.jpg', alt='A village farm input shop with seed and fertiliser bags',
    h=('சரியான இடுபொருள், <em>சரியான நேரத்தில்.</em>', 'The right input, <em>at the right time.</em>'),
    lede=('தரமான விதை, உரம், பயிர் பாதுகாப்பு, இயற்கை இடுபொருட்கள், சொட்டு நீர், கருவிகள் — FPO-க்களும் கூட்டாளர் கடைகளும் வழியாக.',
          'Quality seeds, nutrition, crop protection, organic inputs, drip and machinery — through FPOs and partner shops.'),
    intro=('ஆலோசனையும் இடுபொருளும் ஒன்றாக.', 'Advice and supply, joined up.',
           'செயலி என்ன தேவை என்று சொல்கிறது. அருகிலுள்ள கூட்டாளர் கடை அதையே, நியாயமான விலையில், நம்பகமான பிராண்டில் தருகிறது.',
           'The app tells the farmer what is needed. A nearby partner shop supplies exactly that — trusted brands, fair prices.'),
    feats=[('seed', 'தரமான விதைகள்', 'Quality seeds', 'பகுதிக்கு ஏற்ற, சான்றளிக்கப்பட்ட ரகங்கள்.', 'Certified varieties suited to the area.', 'live'),
           ('flask', 'உரம், ஊட்டச்சத்து', 'Fertiliser & nutrition', 'மண் பரிசோதனை அடிப்படையில் சரியான அளவு.', 'Right doses, guided by soil tests.', 'live'),
           ('shield', 'பயிர் பாதுகாப்பு', 'Crop protection', 'இயற்கை முதலில்; ரசாயனம் பாதுகாப்புக் குறிப்புடன்.', 'Organic first; chemicals with safety guidance.', 'live'),
           ('leaf', 'இயற்கை இடுபொருட்கள்', 'Organic inputs', 'உயிர் உரங்கள், வேப்பம் சார்ந்த பொருட்கள், கம்போஸ்ட்.', 'Bio-fertilisers, neem products and compost.', 'live'),
           ('drop', 'சொட்டு நீர் பாசனம்', 'Drip & irrigation', 'குழாய்கள், வால்வுகள், சொட்டு நீர் கிட்கள்.', 'Pipes, valves and drip kits.', 'live'),
           ('tractor', 'பண்ணைக் கருவிகள்', 'Farm machinery', 'தெளிப்பான்கள், சிறு இயந்திரங்கள், உதிரி பாகங்கள்.', 'Sprayers, small machines and spares.', 'live')],
    flow=[('ஆலோசனை', 'Advice', 'செயலி பயிருக்குத் தேவையானதைச் சொல்கிறது.', 'The app recommends what the crop needs.'),
          ('ஆர்டர்', 'Order', 'FPO அல்லது கூட்டாளர் கடையில்.', 'Through the FPO or a partner shop.'),
          ('விநியோகம்', 'Delivery', 'கிராமத்துக்கு அருகில்.', 'Close to the village.'),
          ('பின்தொடர்வு', 'Follow-up', 'பயன்பாட்டு முறை, முடிவுகள் செயலியில்.', 'Usage and results tracked in the app.')],
    who=[('விவசாயிகள்', 'Farmers'), ('FPO-க்கள்', 'FPOs'), ('இடுபொருள் கடைகள்', 'Input shops'),
         ('உற்பத்தியாளர்கள்', 'Manufacturers'), ('விநியோகஸ்தர்கள்', 'Distributors')],
    who_text=('கூட்டாளர் கடையாக இணையுங்கள்', 'Become a partner shop',
              'உங்கள் கடைக்கு அருகிலுள்ள செயலிப் பயனர்களின் தேவைகள் உங்களுக்கு வரும். உற்பத்தியாளர்கள் FPO நெட்வொர்க்கை அடையலாம்.',
              'Get demand from app users near your shop. Manufacturers can reach our FPO network.'),
)

ENGINES['advisory'] = dict(
    title='AI crop advisory in Tamil — crop doctor, weather, prices | AgrowNex',
    desc='Free AI crop doctor from a leaf photo, Tamil AI chat, village weather, official mandi prices, crop calendars and expert help for Tamil Nadu farmers.',
    img='advisory.jpg', alt='An agronomist advising a farmer in a banana plantation', video='/assets/video/scan.mp4',
    h=('ஒவ்வொரு விவசாயிக்கும் <em>ஒரு வேளாண் நிபுணர்.</em>', 'An agronomist <em>in every pocket.</em>'),
    lede=('இலைப் படத்தில் நோய் கண்டறிதல், தமிழில் AI உதவி, கிராம வானிலை, அரசு மண்டி விலை — அடிப்படை சேவைகள் இலவசம்.',
          'Leaf-photo disease checks, Tamil AI help, village weather and official mandi prices — core services are free.'),
    actions=btn('/app', 'செயலியைப் பாருங்கள்', 'See the app'),
    intro=('இலவச முன் வாசல்.', 'The free front door.',
           'ஆலோசனை விவசாயிகளின் நம்பிக்கையைப் பெறுகிறது. அதன் மேல்தான் மற்ற அனைத்துச் சேவைகளும் கட்டப்படுகின்றன.',
           "Advice earns farmers' trust. Every other service is built on top of it."),
    feats=[('scan', 'AI பயிர் மருத்துவர்', 'AI crop doctor', 'ஒரு இலைப் படத்தில் நோய், தீர்வு.', 'Disease and treatment from one leaf photo.', 'live'),
           ('chat', 'தமிழ் AI உதவி', 'Tamil AI chat', 'குரல் அல்லது எழுத்தில் கேளுங்கள்.', 'Ask by voice or text.', 'live'),
           ('cloud', 'கிராம வானிலை', 'Village weather', 'மழை, தெளிப்பு ஏற்ற நேரம்.', 'Rain alerts and spray windows.', 'live'),
           ('chart', 'மண்டி விலை', 'Mandi prices', 'Agmarknet அதிகாரப்பூர்வ விலை, தேதியுடன்.', 'Official Agmarknet prices, with dates.', 'live'),
           ('doc', 'பயிர் காலண்டர்', 'Crop calendar', 'TNAU/ICAR அடிப்படையில் வாராந்திரப் பணிகள்.', 'Weekly tasks based on TNAU and ICAR.', 'live'),
           ('phone', 'நிபுணர் உதவி, மண் பரிசோதனை', 'Expert help & soil tests', 'நிபுணர் அழைப்பு, மண் பரிசோதனை ஏற்பாடு.', 'Expert calls and soil-test bookings.', 'next')],
    flow=[('படம் எடுங்கள்', 'Snap', 'இலை அல்லது பயிரைப் படம் எடுங்கள்.', 'Photograph the leaf or crop.'),
          ('AI சரிபார்ப்பு', 'AI check', 'பயிர், பகுதி, வானிலையுடன் சேர்த்து.', 'Read with crop, area and weather.'),
          ('தமிழில் பதில்', 'Answer in Tamil', 'இயற்கை முதலில், பிறகு ரசாயனம்.', 'Organic first, then chemical.'),
          ('நிபுணர்', 'Expert', 'உறுதியில்லையெனில் நிபுணரிடம்.', 'Flagged to an expert if unsure.')],
    who=[('விவசாயிகள்', 'Farmers'), ('FPO-க்கள்', 'FPOs'), ('KVK-க்கள்', 'KVKs'), ('வேளாண் துறை', 'Agriculture department')],
    who_text=('KVK, FPO-க்களுடன் இணைந்து', 'Built with KVKs and FPOs',
              'உங்கள் விஞ்ஞானிகள் எங்கள் உள்ளடக்கத்தைச் சரிபார்க்கலாம்; ஒப்புக்கொண்ட விவசாயிகளின் நோய் அறிக்கைகளைப் பார்க்கலாம்.',
              'Your scientists can review our content and see disease reports from farmers who opt in.'),
)

ENGINES['produce'] = dict(
    title='Produce trading and export from Tamil Nadu — chilli, banana, coconut | AgrowNex',
    desc='AgrowNex buys through FPOs and sells to retail chains, wholesalers, processors and exporters, with graded, traceable lots for Sri Lanka, UAE and more.',
    img='warehouse.jpg', alt='Sacks of dry red chilli being graded in a warehouse', video='/assets/video/port.mp4',
    h=('விவசாயியின் விளைச்சல், <em>சரியான வாங்குபவருக்கு.</em>', "The farmer's harvest, <em>to the right buyer.</em>"),
    lede=('FPO-க்கள் மூலம் வாங்கி, சில்லறை நிறுவனங்கள், மொத்த வியாபாரிகள், ஏற்றுமதியாளர்கள், வெளிநாட்டுச் சந்தைகளுக்கு விற்கிறோம்.',
          'We buy through FPOs and sell to retail chains, wholesalers, exporters and overseas markets.'),
    actions=btn('/wholesale#enquire', 'தேவையைப் பதிவு செய்யுங்கள்', 'Send a requirement'),
    intro=('குறைவான இடைத்தரகர், அதிக வருமானம்.', 'Fewer middlemen, better prices.',
           'அறுவடைக்கு முன்பே அளவும் தேதியும் தெரியும். தரம் பிரித்த, கண்டறியக்கூடிய தொகுதிகள்.',
           'Volume and dates are known before harvest. Lots are graded and traceable.'),
    feats=[('store', 'பெரிய வாங்குபவர்கள்', 'Large buyers', 'சில்லறைச் சங்கிலிகள், விரைவு வணிகம், மொத்த வியாபாரிகள்.', 'Retail chains, quick-commerce and wholesalers.', 'live'),
           ('ship', 'ஏற்றுமதி', 'Export', 'இலங்கை, UAE, பின்னர் மற்ற நாடுகள்.', 'Sri Lanka, UAE, then more markets.', 'next'),
           ('doc', 'அரசு டெண்டர்கள்', 'Government tenders', 'பொது கொள்முதல் வாய்ப்புகள்.', 'Public procurement opportunities.', 'next'),
           ('users', 'சந்தை தொழில்முனைவோர்', 'Market entrepreneurs', 'கிராம அளவில் சேகரிப்பாளர்கள்.', 'Village-level aggregators.', 'next'),
           ('box', 'தரம் பிரித்தல்', 'Grading & packing', 'தரம், எடை, பேக்கிங் தரநிலை.', 'Quality, weight and packing standards.', 'live'),
           ('leaf', 'இயற்கைத் தொகுதிகள்', 'Organic lots', 'சான்றிதழ் சரிபார்க்கப்பட்டவை மட்டும்.', 'Only with a verified certificate.', 'live')],
    flow=[('பட்டியல்', 'List', 'FPO-க்கள் அறுவடையைப் பட்டியலிடுகின்றன.', 'FPOs list coming harvests.'),
          ('பொருத்தம்', 'Match', 'வாங்குபவர் தேவையுடன்.', 'Matched with buyer demand.'),
          ('தரம்', 'Grade', 'மாதிரி, தர சோதனை.', 'Samples and quality checks.'),
          ('அனுப்புதல்', 'Ship', 'லாரி அல்லது கண்டெய்னர்.', 'By truck or container.'),
          ('பணம்', 'Pay', 'விவசாயிக்கு வெளிப்படையாக.', 'Paid to farmers transparently.')],
    who=[('காய்ந்த மிளகாய்', 'Dry chilli'), ('வாழை', 'Banana'), ('தேங்காய்', 'Coconut'), ('நெல்', 'Paddy'),
         ('பருப்பு வகைகள்', 'Pulses'), ('நிலக்கடலை', 'Groundnut'), ('வெங்காயம்', 'Onion'), ('மசாலா', 'Spices')],
    who_text=('வாங்குபவர்களுக்கு', 'For buyers',
              'பயிர், அளவு, தரம், தேதியைச் சொல்லுங்கள் — பொருத்தமான FPO தொகுதிகளுடன் இணைக்கிறோம்.',
              'Tell us crop, volume, grade and dates — we match you with FPO lots.'),
)

ENGINES['finance'] = dict(
    title='Farm credit and crop insurance through partners | AgrowNex',
    desc='AgrowNex connects Tamil Nadu farmers and FPOs to crop loans, input credit, crop insurance and infrastructure loans from regulated banks, NBFCs and insurers.',
    img='finance.jpg', alt='A farmer meeting a bank officer at a rural branch',
    h=('சரியான நேரத்தில் <em>கடனும் காப்பீடும்.</em>', 'Credit and cover, <em>when it matters.</em>'),
    lede=('முறைப்படுத்தப்பட்ட வங்கிகள், NBFC-கள், காப்பீட்டு நிறுவனங்களுடன் இணைக்கிறோம். நாங்கள் கடன் கொடுப்பதில்லை; பணத்தை வைத்திருப்பதில்லை.',
          'We connect farmers with regulated banks, NBFCs and insurers. We never lend, and we never hold your money.'),
    intro=('பண்ணைத் தரவு, கடனுக்கு வழி.', 'Farm data that opens doors.',
           'விவசாயியின் ஒப்புதலுடன், பயிர், நிலம், கொள்முதல், விற்பனைப் பதிவுகளைக் கூட்டாளருக்குக் காட்டுகிறோம் — கடன் எளிதாகிறது.',
           'With consent, we show partners the crop, land, purchase and sales record — making credit easier to get.'),
    feats=[('bank', 'பயிர்க் கடன், KCC', 'Crop loans & KCC', 'கூட்டாளர் வங்கிகள் மூலம்.', 'Through partner banks.', 'next'),
           ('card', 'இடுபொருள் கடன்', 'Input credit', 'இப்போது வாங்கி, அறுவடையில் செலுத்துங்கள்.', 'Buy now, repay at harvest.', 'next'),
           ('umbrella', 'பயிர்க் காப்பீடு', 'Crop insurance', 'உரிமம் பெற்ற காப்பீட்டாளர்கள் மூலம்.', 'Through licensed insurers.', 'next'),
           ('gear', 'உள்கட்டமைப்புக் கடன்', 'Infrastructure loans', 'உலர்த்தி, தரம் பிரிக்கும் இயந்திரம், கிடங்கு.', 'Dryers, sorters and storage.', 'next'),
           ('shield', 'ஒப்புதல் முதலில்', 'Consent first', 'பதிவுசெய்த ஒப்புதலுடன் மட்டுமே பகிர்வு.', 'Shared only with recorded consent.'),
           ('chat', 'தமிழில் விளக்கம்', 'Explained in Tamil', 'வட்டி, கட்டணம், திருப்பிச் செலுத்துதல் — அழுத்தம் இல்லை.', 'Interest, fees and repayment — no pressure.')],
    flow=[('விண்ணப்பம்', 'Apply', 'செயலி அல்லது FPO வழியாக.', 'Through the app or FPO.'),
          ('ஒப்புதல்', 'Consent', 'எந்தத் தரவு பகிரப்படும் என்று தெரியும்.', 'See exactly what is shared.'),
          ('கூட்டாளர் முடிவு', 'Partner decides', 'வங்கி அல்லது காப்பீட்டாளர்.', 'The bank or insurer decides.'),
          ('நேரடிப் பணம்', 'Direct payout', 'விவசாயியின் கணக்குக்கே.', "Straight to the farmer's account.")],
    who=[('வங்கிகள்', 'Banks'), ('NBFC-கள்', 'NBFCs'), ('காப்பீட்டு நிறுவனங்கள்', 'Insurers'), ('FPO-க்கள்', 'FPOs')],
    who_text=('நிதிக் கூட்டாளர்களுக்கு', 'For finance partners',
              'சரிபார்க்கப்பட்ட பண்ணைத் தரவுடன் கிராமப்புற வாடிக்கையாளர்களை அடையுங்கள். RBI விதிகளின்படி எழுத்து ஒப்பந்தத்துடன்.',
              'Reach rural borrowers with verified farm data — under a written agreement that follows RBI rules.'),
)

ENGINES['brands'] = dict(
    title='AgrowNex brands — spices, GI products, value-added foods | AgrowNex',
    desc='Own-brand equipment, branded export produce, processed foods and GI products such as Udangudi palm jaggery and Kovilpatti kadalai mittai.',
    img='brands.jpg', alt='Spices, red chillies and palm jaggery on a wooden table', video='/assets/video/brands.mp4',
    h=('தென் தமிழகத்தின் சுவை, <em>எங்கள் பெயரில்.</em>', 'The taste of South Tamil Nadu, <em>under our name.</em>'),
    lede=('மதிப்புக் கூட்டல் விவசாயிக்கும் நிறுவனத்துக்கும் அதிக வருமானம் தருகிறது. ஒவ்வொரு பொருளும் கடைச் சோதனைக்குப் பிறகே.',
          'Adding value earns more for farmers and for us. Each product launches only after a shop test.'),
    intro=('மூலப்பொருளிலிருந்து பிராண்டுக்கு.', 'From raw produce to a brand.',
           'எங்கள் FPO-க்களின் விளைச்சலைத் தரம் பிரித்து, பதப்படுத்தி, AgrowNex பெயரில் விற்கிறோம்.',
           'We grade, process and pack our FPOs\' produce and sell it under the AgrowNex name.'),
    feats=[('gear', 'சொந்த பிராண்ட் கருவிகள்', 'Own-brand equipment', 'பாசனக் குழாய்கள், வால்வுகள், இயந்திரங்கள்.', 'Irrigation pipes, valves and machinery.', 'live'),
           ('ship', 'பிராண்ட் ஏற்றுமதி விளைபொருள்', 'Branded export produce', 'தரம் பிரித்த காய்ந்த மிளகாய், வாழை.', 'Graded dry chilli and banana.', 'next'),
           ('box', 'பதப்படுத்திய உணவு', 'Processed foods', 'மசாலாப் பொடி, பொடி வகைகள், எண்ணெய், பருப்பு.', 'Masala powders, podis, oils and dal.', 'next'),
           ('star', 'GI பொருட்கள்', 'GI products', 'உடன்குடி பனை வெல்லம், கோவில்பட்டி கடலை மிட்டாய்.', 'Udangudi palm jaggery, Kovilpatti kadalai mittai.', 'next'),
           ('seed', 'சொந்த பிராண்ட் இடுபொருட்கள்', 'Own-brand inputs', 'ஒப்பந்த உற்பத்தியாளர்கள் மூலம்.', 'Made by contract manufacturers.', 'later'),
           ('leaf', 'நுகர்வோர் உணவு பிராண்ட்', 'Consumer food brand', 'பூச்சிக்கொல்லி இல்லாத அன்றாடப் பொருட்கள்.', 'Pesticide-free staples.', 'later')],
    flow=[('வாங்குதல்', 'Source', 'FPO-க்களிடமிருந்து.', 'From our FPOs.'),
          ('பதப்படுத்தல்', 'Process', 'சுத்தம், உலர்த்தல், அரைத்தல்.', 'Clean, dry and mill.'),
          ('பேக்கிங்', 'Pack', 'FSSAI தரநிலையில்.', 'To FSSAI standards.'),
          ('விற்பனை', 'Sell', 'கடைகள், ஆன்லைன், ஏற்றுமதி.', 'Shops, online and export.')],
    who=[('சில்லறைக் கடைகள்', 'Retailers'), ('சூப்பர் மார்க்கெட்டுகள்', 'Supermarkets'), ('விரைவு வணிகம்', 'Quick-commerce'),
         ('ஏற்றுமதி வாங்குபவர்கள்', 'Export buyers'), ('ஹோட்டல்கள்', 'Hotels')],
    who_text=('விநியோகஸ்தர்கள், வாங்குபவர்களுக்கு', 'For distributors and buyers',
              'எங்கள் பிராண்ட் பொருட்களை விற்க அல்லது தனியார் லேபிளுக்கு எங்களுடன் பேசுங்கள்.',
              'Talk to us about stocking our brands or private label.'),
)

ENGINES['export-support'] = dict(
    title='Export support for FPOs — registration, buyers, customs | AgrowNex',
    desc='AgrowNex helps FPOs in Tamil Nadu export for the first time: registrations, buyer matching, quality, documents, customs clearance and shipping with partners.',
    img='port.jpg', alt='Containers stacked at a port at sunset', video='/assets/video/port.mp4',
    h=('உங்கள் FPO-வின் <em>முதல் ஏற்றுமதி.</em>', "Your FPO's <em>first export.</em>"),
    lede=('பதிவு முதல் கப்பலேற்றம் வரை — எங்கள் சுங்க அனுமதிக் கூட்டாளருடன் இணைந்து முழு உதவி.',
          'From registration to shipment — end-to-end help, with our customs clearance partner.'),
    intro=('ஏற்றுமதி கடினமாக இருக்க வேண்டியதில்லை.', "Export doesn't have to be hard.",
           'வாங்குபவர்களைக் கொண்டு வருகிறோம்; ஆவணங்கள், சுங்க அனுமதி, கப்பல் போக்குவரத்தை எங்கள் கூட்டாளர் கையாளுகிறார்.',
           'We bring the buyers; our partner handles documents, customs clearance and shipping.'),
    feats=[('doc', 'பதிவுகள்', 'Registrations', 'IEC, APEDA / Spices Board, FSSAI வழிகாட்டல்.', 'Guidance on IEC, APEDA / Spices Board and FSSAI.', 'next'),
           ('globe', 'வாங்குபவர் இணைப்பு', 'Buyer matching', 'சரிபார்க்கப்பட்ட வெளிநாட்டு வாங்குபவர்கள்.', 'Verified overseas buyers.', 'next'),
           ('cert', 'தரம், சான்றிதழ்', 'Quality & certificates', 'மாதிரி, ஆய்வக சோதனை, தாவர சுகாதாரச் சான்று.', 'Samples, lab tests, phytosanitary certificates.', 'next'),
           ('ship', 'சுங்க அனுமதி, கப்பல்', 'Customs & shipping', 'கூட்டாளர் CHA மூலம்.', 'Through our CHA partner.', 'next')],
    feat_cls='four',
    flow=[('பதிவு', 'Register', 'தேவையான உரிமங்கள்.', 'The licences you need.'),
          ('வாங்குபவர்', 'Buyer', 'பொருத்தமான வாங்குபவர்.', 'A matched buyer.'),
          ('மாதிரி', 'Sample', 'தரம் உறுதி.', 'Quality agreed.'),
          ('ஆவணம்', 'Documents', 'சுங்க அனுமதி.', 'Customs clearance.'),
          ('கப்பல்', 'Ship', 'தூத்துக்குடியிலிருந்து.', 'From Thoothukudi.'),
          ('பணம்', 'Get paid', 'பாதுகாப்பான முறையில்.', 'Through secure terms.')],
    flow_cls='six',
    who=[('CBBO நெட்வொர்க் FPO-க்கள்', 'CBBO-network FPOs'), ('சிறு ஏற்றுமதியாளர்கள்', 'Small exporters'), ('விவசாயக் குழுக்கள்', 'Farmer groups')],
    who_text=('FPO-க்களுக்கு', 'For FPOs', 'உங்கள் FPO ஏற்றுமதிக்குத் தயாரா என்று பார்ப்போம் — எங்களுடன் பேசுங்கள்.',
              "Let's check if your FPO is ready to export — talk to us."),
)

ENGINES['programmes'] = dict(
    title='Farmer programmes, equipment rental and organic certification | AgrowNex',
    desc='Funded farmer training and demonstrations, sponsored listings for input makers, equipment rental and organic certification support for FPOs in Tamil Nadu.',
    img='training.jpg', alt='Farmers attending a field training session under a tree',
    h=('விவசாயிகளுடன் <em>களத்தில்.</em>', 'Out in the field, <em>with farmers.</em>'),
    lede=('அரசு, CSR நிதியுதவியுடன் பயிற்சி, கருவி வாடகை, இயற்கைச் சான்றிதழ் உதவி — FPO-க்கள் வளர.',
          'Funded training, equipment hire and organic certification support — so FPOs can grow.'),
    actions=btn('/partners#join', 'கூட்டாளராகுங்கள்', 'Become a partner'),
    intro=('தளமும் மக்களும்.', 'Platform and people.',
           'செயலி மட்டும் போதாது. கிராமக் கூட்டங்கள், செயல்விளக்கங்கள், FPO பயிற்சிகள் மூலம் நேரில் இணைகிறோம்.',
           'An app alone is not enough. We meet farmers in person through village meetings, demos and FPO training.'),
    feats=[('users', 'நிதியுதவித் திட்டங்கள்', 'Funded programmes', 'அரசு, CSR, NGO பயிற்சி, செயல்விளக்கங்கள்.', 'Government, CSR and NGO training and demos.', 'next'),
           ('tag', 'விளம்பரப் பட்டியல்கள்', 'Sponsored listings', 'இடுபொருள் நிறுவனங்கள் விவசாயிகளை அடைய.', 'For input makers to reach farmers.', 'next'),
           ('tractor', 'கருவி வாடகை', 'Equipment rental', 'FPO வாடகை மையங்கள் மூலம் இயந்திரங்கள்.', 'Machines through FPO hiring centres.', 'next'),
           ('cert', 'இயற்கைச் சான்றிதழ்', 'Organic certification', 'PGS, NPOP சான்றிதழுக்கு வழிகாட்டல், பதிவுகள்.', 'Guidance and records for PGS and NPOP.', 'next')],
    feat_cls='two',
    flow=[('திட்டமிடல்', 'Plan', 'கூட்டாளருடன் இலக்குகள்.', 'Goals set with the partner.'),
          ('களப்பணி', 'Deliver', 'பயிற்சி, செயல்விளக்கம்.', 'Training and demos.'),
          ('செயலியில்', 'In the app', 'பின்தொடர்வு, பதிவு.', 'Follow-up and records.'),
          ('அறிக்கை', 'Report', 'முடிவுகள் கூட்டாளருக்கு.', 'Results reported back.')],
    who=[('வேளாண் துறை', 'Agriculture department'), ('KVK-க்கள்', 'KVKs'), ('CSR நிதிகள்', 'CSR funds'), ('NGO-க்கள்', 'NGOs'), ('இடுபொருள் நிறுவனங்கள்', 'Input makers')],
    who_text=('திட்டக் கூட்டாளர்களுக்கு', 'For programme partners', 'உங்கள் திட்டத்தை எங்கள் FPO நெட்வொர்க் மூலம் கிராமங்களுக்குக் கொண்டு செல்லுங்கள்.',
              'Take your programme to villages through our FPO network.'),
    gallery=True,
)

ENGINES['future'] = dict(
    title='What comes next — carbon credits, insights, imports, drone assembly | AgrowNex',
    desc='AgrowNex future engines: carbon credits for farmers, crop and market insight reports, imports of farm products and machinery, and drone and machine assembly in India.',
    img='carbon.jpg', alt='Agroforestry with trees planted between crop rows', video='/assets/video/drone.mp4',
    h=('நாளைய விவசாயத்துக்கு <em>இன்றே திட்டம்.</em>', "Planning today <em>for tomorrow's farming.</em>"),
    lede=('முதல் ஆண்டுக்குப் பிறகு வரும் பிரிவுகள் — விவசாயிகளும் FPO நெட்வொர்க்கும் வளர்ந்த பின்.',
          'Engines that come after year one — once our farmer and FPO network has grown.'),
    intro=('வலுவான அடித்தளத்தின் மேல்.', 'Built on a strong base.',
           'இவை உடனடித் திட்டங்கள் அல்ல. விவசாயிகள், தரவு, கூட்டாளர்கள் தயாரான பின்பே தொடங்குவோம்.',
           "These are not immediate plans. We start them only when farmers, data and partners are ready."),
    feats=[('tree', 'கார்பன் வரவுகள்', 'Carbon credits', 'மரம் வளர்ப்பு, மண் கார்பன் — வருமானத்தின் பெரும் பங்கு விவசாயிக்கே.', 'Agroforestry and soil carbon — most of the income goes to farmers.', 'later'),
           ('chart', 'பயிர், சந்தை அறிக்கைகள்', 'Insight reports', 'பெயர் நீக்கிய தரவிலிருந்து நிறுவனங்களுக்கு அறிக்கைகள்.', 'Reports for companies from anonymised data.', 'later'),
           ('globe', 'இறக்குமதி', 'Imports', 'லாபம் தரும் விளைபொருள், இயந்திரங்கள், உதிரி பாகங்கள்.', 'Farm products, machinery and parts with real demand.', 'later'),
           ('drone', 'ட்ரோன், இயந்திர இணைப்பு', 'Drone & machine assembly', 'இறக்குமதி பாகங்களை இந்தியாவில் இணைத்தல்.', 'Assembling imported parts in India.', 'later')],
    feat_cls='two',
    flow=[('அடித்தளம்', 'Base', 'விவசாயிகள், FPO நெட்வொர்க்.', 'Farmers and FPO network.'),
          ('தரவு', 'Data', 'இரண்டு பருவத் தரவு.', 'Two seasons of data.'),
          ('கூட்டாளர்', 'Partners', 'சரிபார்ப்பு, உற்பத்தியாளர்கள்.', 'Verifiers and manufacturers.'),
          ('தொடக்கம்', 'Launch', 'சிறிய சோதனையுடன்.', 'Starting with a pilot.')],
    who=[('காலநிலை நிறுவனங்கள்', 'Climate buyers'), ('வேளாண் நிறுவனங்கள்', 'Agri companies'), ('உற்பத்தியாளர்கள்', 'Manufacturers'), ('முதலீட்டாளர்கள்', 'Investors')],
    who_text=('ஆரம்பத்திலேயே இணையுங்கள்', 'Join us early', 'இந்தத் திட்டங்களில் கூட்டாளராக ஆர்வமா? எங்களுடன் பேசுங்கள்.',
              'Interested in partnering on these? Talk to us.'),
    extra_img=('drone.jpg', 'An agricultural spraying drone over a field', 'processing.jpg', 'A solar dryer and colour sorter at a processing unit'),
)


def engine_page(slug, e):
    s = SOL[slug]
    actions = e.get('actions', '') or TALK
    hero_html = sub_hero(IMG + e['img'], e['alt'], s[2], s[3], e['h'][0], e['h'][1], e['lede'][0], e['lede'][1],
                         actions, e.get('video'))
    it = e['intro']
    second = ''
    if e.get('gallery'):
        second = media('/assets/img/kvk-talk.jpg', 'Speaking to farmers at KVK Thirupathisaram', None,
                       ('களத்தில்', 'In the field', 'KVK திருப்பதிசாரம், கன்னியாகுமரி', 'KVK Thirupathisaram, Kanyakumari'))
    elif e.get('extra_img'):
        a, aa, b, bb = e['extra_img']
        second = media(IMG + a, aa, None, ('ட்ரோன்', 'Drones', 'இந்தியாவில் இணைப்பு', 'Assembled in India'))
    else:
        second = media(IMG + e['img'], e['alt'], e.get('video'))
    wt = e['who_text']
    num = t('எதிர்காலம்', 'Future') if slug == 'future' else f'ENGINE {s[1]}'
    body = f'''{hero_html}

  <section class="band">
    <div class="wrap split">
      <div class="reveal">
        <p class="kicker">{num}</p>
        {h2(it[0], it[1])}
        {para(it[2], it[3])}
      </div>
      {second}
    </div>
  </section>

  <section class="band band-mist">
    <div class="wrap">
      {kick("என்ன வழங்குகிறோம்", "What we offer")}
      {h2("சேவைகள்", "Services")}
      {features(e['feats'], e.get('feat_cls', ''))}
    </div>
  </section>

  <section class="band band-ink">
    <div class="wrap">
      {kick("செயல்முறை", "How it works")}
      {h2("படிப்படியாக.", "Step by step.")}
      {flow(e['flow'], e.get('flow_cls', 'four' if len(e['flow']) == 4 else ''))}
    </div>
  </section>

  <section class="band">
    <div class="wrap split">
      <div class="reveal">
        {kick("யாருக்கு", "Who it's for")}
        {h2(wt[0], wt[1])}
        {para(wt[2], wt[3])}
        {chips(e['who'])}
      </div>
      <div class="reveal">
        <div class="cta" style="padding:44px 36px">
          <h3 style="color:#fff;margin-top:0">{t("அடுத்த படி", "Next step")}</h3>
          <p lang="ta">உங்கள் தேவையை WhatsApp அல்லது மின்னஞ்சலில் அனுப்புங்கள். ஒரு வேலை நாளுக்குள் பதில் தருகிறோம்.</p>
          <p lang="en">Send us your requirement on WhatsApp or email. We reply within one working day.</p>
          <div class="hero-actions">{TALK}<a class="btn btn-ghost" href="https://wa.me/918667237404" target="_blank" rel="noopener">WhatsApp</a></div>
        </div>
      </div>
    </div>
  </section>

{pager(slug)}
'''
    og = IMG + e['img']
    return page(slug, e['title'], e['desc'], slug, body, og=og,
                extra=(service_ld(s[3], e['desc'], slug),))


for slug, e in ENGINES.items():
    write(slug, engine_page(slug, e))

# ================================================================= sitemap + llms
PAGES = ['', 'solutions'] + list(ENGINES) + ['app', 'wholesale', 'partners', 'about', 'mabif', 'contact', 'privacy', 'delete-account']
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for p in PAGES:
    pr = '1.0' if p == '' else ('0.9' if p in ENGINES or p in ('solutions', 'app') else '0.6')
    sm.append(f'  <url><loc>{SITE_URL}/{p}</loc><lastmod>2026-10-11</lastmod><priority>{pr}</priority></url>')
sm.append('</urlset>')
(W / 'sitemap.xml').write_text('\n'.join(sm) + '\n', encoding='utf-8')
print('sitemap', len(PAGES))

robots = f'''# AgrowNex — {SITE_URL}
# Search engines and AI assistants are welcome to read this site.
User-agent: *
Allow: /

User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Applebot-Extended
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
'''
(W / 'robots.txt').write_text(robots, encoding='utf-8')


def add_static_seo(slug, title, desc):
    path = W / f'{slug}.html'
    html = path.read_text(encoding='utf-8')
    html = re.sub(r'\n<!-- seo -->.*?<!-- /seo -->', '', html, flags=re.S)
    social = f'''<!-- seo -->
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{SITE_URL}/assets/img/og.jpg">
<meta property="og:type" content="website">
{seo_head('/' + slug, title, desc, '/assets/img/og.jpg')}
<!-- /seo -->'''
    html = html.replace(f'<title>{title}</title>', f'<title>{title}</title>\n{social}', 1)
    path.write_text(html, encoding='utf-8')


add_static_seo('privacy', 'AgrowNex Privacy Policy',
               'AgrowNex privacy policy — what farmer data we collect, why, who we share it with, and how to delete it.')
add_static_seo('delete-account', 'Delete AgrowNex Account', 'How to delete your AgrowNex account and data.')
