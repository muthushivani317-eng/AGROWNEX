"""Generate AgrowNex inner pages with a shared header and footer."""
import re
from pathlib import Path

W = Path(__file__).resolve().parent  # run: python website/build_pages.py

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Catamaran:wght@600;700;800&family=Hind+Madurai:wght@400;500;600'
         '&family=IBM+Plex+Mono:wght@500&family=Noto+Sans+Tamil:wght@400;600;800&display=swap" rel="stylesheet">')

NAV = [
    ('/#app', 'செயலி', 'The app', 'home'),
    ('/wholesale', 'மொத்த வாங்குபவர்கள்', 'Wholesale buyers', 'wholesale'),
    ('/partners', 'FPO · KVK', 'FPO & KVK', 'partners'),
    ('/about', 'எங்களைப் பற்றி', 'About', 'about'),
    ('/contact', 'தொடர்பு', 'Contact', 'contact'),
]


def t(ta, en, tag='span', cls=''):
    c = f' class="{cls}"' if cls else ''
    return f'<{tag}{c} lang="ta">{ta}</{tag}><{tag}{c} lang="en">{en}</{tag}>'


def header(current):
    cur = ' aria-current="page"'
    links = '\n'.join(
        f'      <a href="{h}"{cur if k == current else ""}>{t(ta, en)}</a>'
        for h, ta, en, k in NAV)
    return f'''<a class="skip" href="#main">{t("உள்ளடக்கத்துக்குச் செல்", "Skip to content")}</a>

<header class="site-header">
  <div class="wrap">
    <a class="brand" href="/" aria-label="AgrowNex home">
      <img src="/assets/img/emblem-128.png" alt="" width="40" height="40">
      <b>Agrow<span>Nex</span></b>
    </a>
    <nav class="nav" id="nav" aria-label="Main">
{links}
    </nav>
    <div class="lang-switch" role="group" aria-label="Language / மொழி">
      <button type="button" data-set-lang="ta" aria-pressed="true">தமிழ்</button>
      <button type="button" data-set-lang="en" aria-pressed="false">EN</button>
    </div>
    <button class="menu-btn" type="button" aria-controls="nav" aria-expanded="false" aria-label="Menu">
      <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M2 5h16M2 10h16M2 15h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
    </button>
  </div>
</header>'''


FOOTER = f'''<footer>
  <div class="wrap foot">
    <div class="brandline">
      <b>Agrow<span>Nex</span></b>
      <p>{t("தமிழ் விவசாயிகளுக்கான செயலி. தூத்துக்குடியில் உருவாக்கப்பட்டது.", "A farming app for Tamil Nadu, built in Thoothukudi.")}</p>
      <a href="mailto:agrowai.tn@gmail.com">agrowai.tn@gmail.com</a>
    </div>
    <div><h4>{t("விவசாயிகள்", "Farmers")}</h4><ul>
      <li><a href="/#app">{t("செயலி", "The app")}</a></li>
      <li><a href="/#faq">{t("கேள்விகள்", "Questions")}</a></li>
      <li><a href="/#get">{t("முன்பதிவு", "Early access")}</a></li></ul></div>
    <div><h4>{t("வணிகம்", "Business")}</h4><ul>
      <li><a href="/wholesale">{t("மொத்த வாங்குபவர்கள்", "Wholesale buyers")}</a></li>
      <li><a href="/partners">{t("FPO, KVK கூட்டாண்மை", "FPO & KVK partners")}</a></li></ul></div>
    <div><h4>{t("நிறுவனம்", "Company")}</h4><ul>
      <li><a href="/about">{t("எங்களைப் பற்றி", "About")}</a></li>
      <li><a href="/contact">{t("தொடர்பு", "Contact")}</a></li>
      <li><a href="/privacy">{t("தனியுரிமைக் கொள்கை", "Privacy policy")}</a></li>
      <li><a href="/delete-account">{t("கணக்கை நீக்குதல்", "Delete account")}</a></li></ul></div>
  </div>
  <div class="wrap foot-bottom">© <span id="year">2026</span> AgrowNex · SANTA MARIA ENTERPRISES, Thoothukudi, Tamil Nadu</div>
</footer>'''


def page(slug, title, desc, current, body, og='/assets/img/og.jpg'):
    return f'''<!doctype html>
<html lang="ta" data-lang="ta" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#1c3a27">
<link rel="icon" type="image/png" href="/assets/img/emblem-64.png">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="https://www.agrowai.in{og}">
<meta property="og:type" content="website">
{FONTS}
<link rel="stylesheet" href="/assets/site.css">
<script src="/assets/site.js" defer></script>
</head>
<body>
{header(current)}

<main id="main">
{body}
</main>

{FOOTER}
</body>
</html>
'''


def hero(img, alt, eyebrow, h_ta, h_en, lede_ta, lede_en, actions=''):
    return f'''  <section class="hero hero-page" id="top">
    <div class="hero-media"><img src="{img}" alt="{alt}" width="1600" height="1000"></div>
    <div class="wrap">
      <p class="hero-eyebrow">{eyebrow}</p>
      <h1 lang="ta">{h_ta}</h1>
      <h1 lang="en">{h_en}</h1>
      <p class="lede" lang="ta">{lede_ta}</p>
      <p class="lede" lang="en">{lede_en}</p>
      {actions}
    </div>
  </section>'''


def field(fid, name, ta, en, kind='text', req=True, opts=None, ph=''):
    label = f'<label for="{fid}">{t(ta, en)}{"" if req else " " + t("(விருப்பம்)", "(optional)")}</label>'
    r = ' required' if req else ''
    p = f' placeholder="{ph}"' if ph else ''
    if kind == 'textarea':
        ctl = f'<textarea id="{fid}" name="{name}"{r}{p}></textarea>'
    elif kind == 'select':
        o = ''.join(f'<option value="{v}">{v}</option>' for v in opts)
        ctl = f'<select id="{fid}" name="{name}"{r}><option value="">—</option>{o}</select>'
    else:
        ac = {'tel': ' autocomplete="tel" inputmode="tel"', 'email': ' autocomplete="email"'}.get(kind, '')
        ctl = f'<input id="{fid}" name="{name}" type="{kind}"{ac}{r}{p}>'
    return f'<div>{label}{ctl}</div>'


def form(subject, rows, note_ta, note_en):
    inner = []
    for row in rows:
        if isinstance(row, tuple) and len(row) == 2 and isinstance(row[0], str) and row[0].startswith('<div>'):
            inner.append(f'<div class="row">{row[0]}{row[1]}</div>')
        else:
            inner.append(row)
    return f'''<form class="enquiry" data-enquiry="{subject}" novalidate>
        {"".join(inner)}
        <div class="actions">
          <button class="btn btn-soil" type="submit" value="email">{t("மின்னஞ்சலில் அனுப்பு", "Send by email")}</button>
          <button class="btn btn-wa" type="submit" value="whatsapp">{t("WhatsApp-ல் அனுப்பு", "Send on WhatsApp")}</button>
        </div>
        <p class="fine" lang="ta">{note_ta}</p><p class="fine" lang="en">{note_en}</p>
      </form>'''


FORM_NOTE = ("உங்கள் மின்னஞ்சல் அல்லது WhatsApp செயலி செய்தியுடன் திறக்கும். இந்தத் தளத்தில் எதுவும் சேமிக்கப்படாது.",
             "Your email app or WhatsApp opens with the message ready. Nothing is stored on this website.")

# ---------------------------------------------------------------- wholesale
CROPS = [('நெல்', 'Paddy'), ('வாழை', 'Banana'), ('காய்ந்த மிளகாய்', 'Dry red chilli'), ('தேங்காய்', 'Coconut'),
         ('நிலக்கடலை', 'Groundnut'), ('உளுந்து, பாசிப்பயறு', 'Black & green gram'), ('பருத்தி', 'Cotton'),
         ('காய்கறிகள்', 'Vegetables')]
crop_chips = ''.join(f'<li>{t(a, b)}</li>' for a, b in CROPS) + \
    f'<li class="org">{t("சான்றளிக்கப்பட்ட இயற்கை விளைபொருள்", "Certified organic lots")}</li>'

wholesale = page('wholesale', 'Wholesale buyers — AgrowNex',
    'Source paddy, banana, chilli, coconut, pulses and organic produce directly from farmer groups in South Tamil Nadu through AgrowNex.',
    'wholesale', f'''{hero("/assets/img/mandi.jpg", "Heaps of dried red chillies and onions at a wholesale market",
    "For processors · traders · exporters",
    "தென் தமிழக விவசாயிகளிடமிருந்து <em>நேரடியாக வாங்குங்கள்.</em>",
    "Buy direct from <em>South Tamil Nadu's farmers.</em>",
    "உங்களுக்குத் தேவையான பயிர், அளவு, தரத்தைச் சொல்லுங்கள். அறுவடை தேதியுடன் பட்டியலிட்ட விவசாயக் குழுக்களுடன் இணைக்கிறோம்.",
    "Tell us the crop, volume and grade you need. We match you with farmer groups who have listed that harvest, with dates.",
    '<div class="hero-actions"><a class="btn btn-soil" href="#enquire">' + t("தேவையைப் பதிவு செய்யுங்கள்", "Send your requirement") + '</a>'
    '<a class="btn btn-ghost" href="#how">' + t("எப்படி வேலை செய்கிறது", "How it works") + '</a></div>')}

  <section class="band">
    <div class="wrap grid-2">
      <div class="reveal">
        <p class="kicker" lang="ta">என்ன வாங்கலாம்</p><p class="kicker" lang="en">What you can source</p>
        <h2 lang="ta">பருவத்துக்குப் பருவம், வயலிலிருந்து நேரடியாக.</h2>
        <h2 lang="en">Season by season, straight from the field.</h2>
        <p class="intro" lang="ta">தூத்துக்குடி, திருநெல்வேலி, கன்னியாகுமரி, ராமநாதபுரம் பகுதி விவசாயிகளும் FPO-க்களும் AgrowNex செயலியில் தங்கள் அறுவடையைப் பட்டியலிடுகிறார்கள்.</p>
        <p class="intro" lang="en">Farmers and FPOs across Thoothukudi, Tirunelveli, Kanyakumari and Ramanathapuram list their coming harvests in the AgrowNex app.</p>
        <ul class="crops">{crop_chips}</ul>
      </div>
      <figure class="split-photo reveal"><img src="/assets/img/chilli.jpg" alt="Chilli plants with red and green chillies in a field" width="1600" height="1200" loading="lazy"></figure>
    </div>
  </section>

  <section class="band band-mist" id="how">
    <div class="wrap">
      <p class="kicker" lang="ta">செயல்முறை</p><p class="kicker" lang="en">How it works</p>
      <h2 lang="ta">தேவை முதல் அனுப்புதல் வரை, நான்கு படிகள்.</h2>
      <h2 lang="en">From requirement to dispatch, in four steps.</h2>
      <ol class="steps tiles four" style="counter-reset: step">
        <li class="tile"><div><b lang="ta">தேவையை அனுப்புங்கள்</b><b lang="en">Send your requirement</b>
          <span lang="ta">பயிர், ரகம், தரம், அளவு, இடம், தேதி.</span><span lang="en">Crop, variety, grade, volume, delivery point and dates.</span></div></li>
        <li class="tile"><div><b lang="ta">பொருத்தமான விவசாயிகள்</b><b lang="en">We match supply</b>
          <span lang="ta">அந்த அறுவடையைப் பட்டியலிட்ட FPO, விவசாயிகளின் படங்கள், அளவு, அறுவடை தேதியுடன்.</span><span lang="en">Listed lots from FPOs and farmers, with photos, quantity and harvest date.</span></div></li>
        <li class="tile"><div><b lang="ta">தர சோதனை</b><b lang="en">Check the quality</b>
          <span lang="ta">மாதிரி, படங்கள் அல்லது நேரடிப் பார்வை — அனுப்பும் முன்.</span><span lang="en">Samples, photos or a field visit — before anything is dispatched.</span></div></li>
        <li class="tile"><div><b lang="ta">எழுத்து ஒப்பந்தம்</b><b lang="en">Agree in writing</b>
          <span lang="ta">விலை, கட்டணம், போக்குவரத்து — எழுத்தில். எங்கள் சேவைக் கட்டணம் முன்கூட்டியே தெரிவிக்கப்படும்.</span><span lang="en">Price, payment and transport in writing. Our service fee is agreed upfront.</span></div></li>
      </ol>
    </div>
  </section>

  <section class="band band-ink">
    <div class="wrap grid-2">
      <div class="reveal">
        <p class="kicker" lang="ta">ஏன் AgrowNex</p><p class="kicker" lang="en">Why buy through AgrowNex</p>
        <h2 lang="ta">அறுவடைக்கு முன்பே தெரியும். யாரிடமிருந்து என்றும் தெரியும்.</h2>
        <h2 lang="en">Know the harvest before it's cut, and who grew it.</h2>
        <ul class="checks">
          <li lang="ta"><b>முன்கூட்டிய பார்வை:</b> விவசாயிகள் எதிர்பார்க்கும் அறுவடை தேதி, அளவை முன்பே பட்டியலிடுகிறார்கள்.</li>
          <li lang="en"><b>See supply early:</b> farmers list expected harvest dates and quantities ahead of time.</li>
          <li lang="ta"><b>கண்டறியும் தன்மை:</b> ஒவ்வொரு தொகுதிக்கும் பண்ணை, பயிர், ரகம், அறுவடை தேதி.</li>
          <li lang="en"><b>Traceable lots:</b> farm, crop, variety and harvest date for every lot.</li>
          <li lang="ta"><b>உண்மையான இயற்கை முத்திரை:</b> சரிபார்க்கப்பட்ட சான்றிதழ் உள்ள பண்ணைகளுக்கு மட்டும். காலாவதியானால் உடனே நீங்கும்.</li>
          <li lang="en"><b>Organic label you can trust:</b> shown only for farms with a verified certificate, and removed the day it expires.</li>
          <li lang="ta"><b>நியாயமான விலைக் குறிப்பு:</b> Agmarknet அரசு மண்டி விலை இருபுறமும் தெரியும்.</li>
          <li lang="en"><b>Fair price reference:</b> both sides see official Agmarknet mandi prices.</li>
        </ul>
      </div>
      <div class="reveal">
        <div class="tiles" style="grid-template-columns:1fr; margin-top:0">
          <div class="tile" style="background:rgba(255,255,255,.06);border:0"><span class="mono" style="color:var(--turmeric)">{t("யாருக்கு", "Who it's for")}</span>
            <p lang="ta" style="color:#d6e2d2">உணவு பதப்படுத்தும் நிறுவனங்கள், அரிசி ஆலைகள், மசாலா நிறுவனங்கள், ஏற்றுமதியாளர்கள், மொத்த வியாபாரிகள், சில்லறை சங்கிலிகள், ஹோட்டல்கள்.</p>
            <p lang="en" style="color:#d6e2d2">Food processors, rice mills, spice companies, exporters, wholesale traders, retail chains and hotels.</p></div>
        </div>
        <p class="honest" lang="ta">இந்தப் பருவத்தில் முதல் வாங்குபவர்களுடன் தொடங்குகிறோம். எந்தக் கொள்முதலும் உறுதியாகும் முன் அளவும் தரமும் நேரில் சரிபார்க்கப்படும்.</p>
        <p class="honest" lang="en">We're onboarding our first buyers this season. Volume and quality are confirmed lot by lot before any purchase is committed.</p>
      </div>
    </div>
  </section>

  <section class="band" id="enquire">
    <div class="wrap grid-2">
      <div class="reveal">
        <p class="kicker" lang="ta">தேவையைப் பதிவு செய்யுங்கள்</p><p class="kicker" lang="en">Send your requirement</p>
        <h2 lang="ta">உங்கள் தேவையைச் சொல்லுங்கள்.</h2>
        <h2 lang="en">Tell us what you need.</h2>
        <p class="intro" lang="ta">குறைந்தபட்ச அளவு பயிருக்குப் பயிர் மாறும். தெரியவில்லை என்றால் தோராயமாகச் சொல்லுங்கள்.</p>
        <p class="intro" lang="en">Minimum volumes depend on the crop. If you're unsure, give a rough figure and we'll work it out together.</p>
      </div>
      {form("AgrowNex wholesale requirement", [
        (field("w-co", "company", "நிறுவனம்", "Company"), field("w-name", "name", "உங்கள் பெயர்", "Your name")),
        (field("w-phone", "phone", "கைபேசி", "Phone", "tel"), field("w-city", "city", "ஊர் / டெலிவரி இடம்", "City / delivery point")),
        (field("w-crop", "crop", "பயிர், ரகம்", "Crop and variety", ph="e.g. Ponni paddy"), field("w-qty", "quantity", "அளவு (டன் / மாதம்)", "Volume (tonnes / month)")),
        field("w-notes", "notes", "தரம், சான்றிதழ், தேதி", "Grade, certification, dates", "textarea", req=False),
      ], *FORM_NOTE)}
    </div>
  </section>''', og='/assets/img/mandi.jpg')

# ---------------------------------------------------------------- partners
partners = page('partners', 'FPO & KVK partners — AgrowNex',
    'Bring your member farmers onto AgrowNex: join requests with consent, member crops, harvest calendar, needs and a data feed for FPOs, KVKs and NGOs in Tamil Nadu.',
    'partners', f'''{hero("/assets/img/aerial.jpg", "Aerial view of small farm plots in different growth stages",
    "For FPOs · KVKs · NGOs · CSR programmes",
    "உங்கள் விவசாயிகள் அனைவரும் <em>ஒரே திரையில்.</em>",
    "All your farmers, <em>on one screen.</em>",
    "உறுப்பினர்களின் பயிர், அறுவடை, தேவைகளைப் பாருங்கள். தமிழில் அவர்களுக்கு உதவுங்கள். விளைபொருளை வாங்குபவர்களுடன் இணையுங்கள்.",
    "See your members' crops, harvests and needs. Support them in Tamil. Connect their produce to buyers.",
    '<div class="hero-actions"><a class="btn btn-soil" href="#join">' + t("கூட்டாளராகுங்கள்", "Become a partner") + '</a></div>')}

  <section class="band">
    <div class="wrap">
      <p class="kicker" lang="ta">FPO-களுக்கு</p><p class="kicker" lang="en">For FPOs</p>
      <h2 lang="ta">உறுப்பினர் பதிவேட்டை நோட்டுப் புத்தகத்திலிருந்து விடுவியுங்கள்.</h2>
      <h2 lang="en">Take your member register off paper.</h2>
      <div class="tiles">
        <div class="tile"><b lang="ta">இணைப்புக் கோரிக்கைகள்</b><b lang="en">Join requests</b>
          <p lang="ta">விவசாயிகள் செயலியிலிருந்தே உங்கள் FPO-வில் சேரக் கேட்கிறார்கள். நீங்கள் ஏற்கலாம் அல்லது மறுக்கலாம்.</p><p lang="en">Farmers ask to join your FPO from the app. You accept or decline.</p></div>
        <div class="tile"><b lang="ta">உறுப்பினர், பயிர் பட்டியல்</b><b lang="en">Members and crops</b>
          <p lang="ta">கிராமம், நிலம், பயிர் வாரியாக வடிகட்டி, CSV ஆக இறக்கலாம்.</p><p lang="en">Filter by village, land and crop, and export to CSV.</p></div>
        <div class="tile"><b lang="ta">அறுவடை காலண்டர்</b><b lang="en">Harvest calendar</b>
          <p lang="ta">எந்த மாதம் எவ்வளவு விற்பனைக்கு வரும் என்று முன்பே தெரியும்.</p><p lang="en">Know how much will be ready to sell, month by month.</p></div>
        <div class="tile"><b lang="ta">உறுப்பினர் தேவைகள்</b><b lang="en">Member needs</b>
          <p lang="ta">விதை, இடுபொருள், உபகரணத் தேவைகள் — கூட்டாக வாங்கத் திட்டமிடுங்கள்.</p><p lang="en">Seed, input and equipment needs — plan bulk buying together.</p></div>
        <div class="tile"><b lang="ta">பயிர் வாரியம்</b><b lang="en">Crop board</b>
          <p lang="ta">உங்கள் உறுப்பினர்கள் எந்தப் பயிர் எவ்வளவு பரப்பில் வளர்க்கிறார்கள்.</p><p lang="en">Which crops your members grow, and on how much land.</p></div>
        <div class="tile"><b lang="ta">தரவு இணைப்பு (API)</b><b lang="en">Data feed (API)</b>
          <p lang="ta">உங்கள் சொந்த டாஷ்போர்டுக்கு — உங்கள் FPO தரவு மட்டும், பாதுகாப்பான சாவியுடன்.</p><p lang="en">For your own dashboard — only your FPO's data, behind a secure key.</p></div>
      </div>
    </div>
  </section>

  <section class="band band-mist">
    <div class="wrap grid-2">
      <div class="reveal">
        <p class="kicker" lang="ta">KVK, வேளாண் துறைக்கு</p><p class="kicker" lang="en">For KVKs and extension teams</p>
        <h2 lang="ta">உங்கள் ஆலோசனை, ஒவ்வொரு விவசாயியின் கைபேசியிலும்.</h2>
        <h2 lang="en">Your advice, in every farmer's pocket.</h2>
        <ul class="checks">
          <li lang="ta"><b>மாவட்ட நோய் அறிக்கைகள்:</b> உங்களுடன் இணைய ஒப்புக்கொண்ட விவசாயிகளின் நோய் கண்டறிதல், அபாய எச்சரிக்கைகள்.</li>
          <li lang="en"><b>District disease reports:</b> disease checks and risk alerts from farmers who chose to link with you.</li>
          <li lang="ta"><b>நிபுணர் சரிபார்ப்பு:</b> செயலியில் உறுதியில்லாத நோய் முடிவுகள் நிபுணர் பார்வைக்குக் குறிக்கப்படுகின்றன.</li>
          <li lang="en"><b>Expert review:</b> uncertain disease results are flagged for an expert to look at.</li>
          <li lang="ta"><b>விழிப்புணர்வு முகாம்கள்:</b> உங்கள் விவசாயிகள் கூட்டங்களில் செயலியை நாங்கள் நேரில் அறிமுகப்படுத்துவோம்.</li>
          <li lang="en"><b>Awareness camps:</b> we demonstrate the app in person at your farmer meetings.</li>
          <li lang="ta"><b>உள்ளடக்க ஆய்வு:</b> பயிர் காலண்டர், நோய் தகவல்களை உங்கள் விஞ்ஞானிகள் சரிபார்க்கலாம்.</li>
          <li lang="en"><b>Content review:</b> your scientists can review our crop calendars and disease guidance.</li>
        </ul>
      </div>
      <figure class="split-photo reveal"><img src="/assets/img/kvk-talk.jpg" alt="Speaking to farmers about AgrowNex at the Agricultural Science Centre, Thirupathisaram, Kanyakumari" width="900" height="1200" loading="lazy">
        <figcaption>{t("கன்னியாகுமரி மாவட்டம், திருப்பதிசாரம் வேளாண்மை அறிவியல் நிலையத்தில் விவசாயிகளுடன்.", "With farmers at the Agricultural Science Centre (KVK), Thirupathisaram, Kanyakumari.")}</figcaption></figure>
    </div>
  </section>

  <section class="band band-ink">
    <div class="wrap grid-2">
      <div class="reveal">
        <p class="kicker" lang="ta">ஒப்புதல் முதலில்</p><p class="kicker" lang="en">Consent comes first</p>
        <h2 lang="ta">விவசாயி சொன்னால் மட்டுமே பகிர்வு.</h2>
        <h2 lang="en">Shared only when the farmer says yes.</h2>
        <p class="intro" lang="ta">சேரும் முன், "உங்கள் பெயர், கைபேசி, கிராமம், நிலம், பயிர்கள் இந்த அமைப்புடன் பகிரப்படும்" என்று செயலி தெளிவாகக் காட்டும். விவசாயி எப்போது வேண்டுமானாலும் விலகலாம்.</p>
        <p class="intro" lang="en">Before joining, the app shows exactly what will be shared: name, phone, village, land and crops. The farmer can leave at any time.</p>
      </div>
      <ol class="steps reveal" style="margin-top:0">
        <li><div><b lang="ta">எங்களுடன் பேசுங்கள்</b><b lang="en">Talk to us</b><span lang="ta">உங்கள் அமைப்பு, மாவட்டம், உறுப்பினர் எண்ணிக்கை.</span><span lang="en">Your organisation, district and member count.</span></div></li>
        <li><div><b lang="ta">செயலியில் உங்கள் பெயர்</b><b lang="en">You appear in the app</b><span lang="ta">உங்கள் மாவட்ட விவசாயிகளுக்கு உங்கள் அமைப்பு தெரியும்.</span><span lang="en">Farmers in your district see your organisation listed.</span></div></li>
        <li><div><b lang="ta">விவசாயிகள் சேருகிறார்கள்</b><b lang="en">Farmers join</b><span lang="ta">ஒப்புதலுடன் கோரிக்கை அனுப்புகிறார்கள். நீங்கள் அழைப்பும் அனுப்பலாம்.</span><span lang="en">They request to join with consent, or accept your invite.</span></div></li>
        <li><div><b lang="ta">ஒரே இடத்தில் நிர்வாகம்</b><b lang="en">Manage in one place</b><span lang="ta">உறுப்பினர், பயிர், அறுவடை, தேவைகள்.</span><span lang="en">Members, crops, harvests and needs.</span></div></li>
      </ol>
    </div>
  </section>

  <section class="band" id="join">
    <div class="wrap grid-2">
      <div class="reveal">
        <p class="kicker" lang="ta">கூட்டாளராகுங்கள்</p><p class="kicker" lang="en">Become a partner</p>
        <h2 lang="ta">ஒரு கிராமம், ஒரு பருவம் — சோதனையாகத் தொடங்குங்கள்.</h2>
        <h2 lang="en">Start with a pilot: one cluster, one season.</h2>
        <p class="intro" lang="ta">கட்டண விவரங்கள் உங்கள் அமைப்பின் அளவைப் பொறுத்தது. எங்களுடன் பேசுங்கள்.</p>
        <p class="intro" lang="en">Terms depend on the size of your organisation and what you need. Talk to us.</p>
        <p style="margin-top:22px"><a href="/wholesale">{t("உங்கள் உறுப்பினர்களின் விளைபொருளுக்கு வாங்குபவர்கள் →", "Buyers for your members' produce →")}</a></p>
      </div>
      {form("AgrowNex partner enquiry", [
        (field("p-org", "organisation", "அமைப்பின் பெயர்", "Organisation"), field("p-type", "type", "வகை", "Type", "select", opts=["FPO", "KVK", "Agriculture department", "NGO / CSR", "Other"])),
        (field("p-name", "name", "உங்கள் பெயர், பதவி", "Your name and role"), field("p-phone", "phone", "கைபேசி", "Phone", "tel")),
        (field("p-dist", "district", "மாவட்டம்", "District"), field("p-members", "members", "விவசாயிகள் எண்ணிக்கை", "Number of farmers", req=False)),
        field("p-notes", "notes", "உங்களுக்கு என்ன தேவை", "What you'd like to do", "textarea", req=False),
      ], *FORM_NOTE)}
    </div>
  </section>''', og='/assets/img/kvk-talk.jpg')

# ---------------------------------------------------------------- about
about = page('about', 'About AgrowNex — SANTA MARIA ENTERPRISES, Thoothukudi',
    'AgrowNex is built in Thoothukudi by SANTA MARIA ENTERPRISES, an Udyam-registered MSME, to give Tamil Nadu farmers clear answers in Tamil from sources they can check.',
    'about', f'''{hero("/assets/img/soil.jpg", "A farmer's hand holding red soil over a ploughed field with young seedlings",
    "Thoothukudi · since 2026",
    "விவசாயிகளின் கேள்விகளுக்கு, <em>அவர்களின் மொழியில்.</em>",
    "Farmers' questions, answered <em>in their own language.</em>",
    "AgrowNex தூத்துக்குடியில் உருவாக்கப்படுகிறது — ஊகத்தால் பணத்தை இழக்கும் விவசாயிகளுக்காக.",
    "AgrowNex is built in Thoothukudi, for farmers who lose money to guesswork.")}

  <section class="band">
    <div class="wrap grid-2">
      <div class="reveal">
        <p class="kicker" lang="ta">ஏன் தொடங்கினோம்</p><p class="kicker" lang="en">Why we started</p>
        <h2 lang="ta">தவறான மருந்து. தெரியாத விலை. எதிர்பாராத மழை.</h2>
        <h2 lang="en">The wrong spray. An unknown price. Rain no one warned about.</h2>
        <p lang="ta">தென் தமிழகத்தில் ஒரு சிறு விவசாயி ஒரு பருவத்தில் இழக்கும் பணம் பெரும்பாலும் இந்த மூன்றிலிருந்துதான். பதில்கள் இருக்கின்றன — ஆனால் ஆங்கிலத்தில், பல இணையதளங்களில், அலுவலக நேரத்தில்.</p>
        <p lang="en">Much of what a small farmer in South Tamil Nadu loses in a season comes from these three. The answers exist — but in English, spread across websites, during office hours.</p>
        <p lang="ta">AgrowNex அவற்றை ஒரே செயலியில், தமிழில், அரசு மற்றும் ஆய்வு நிறுவனங்களின் தரவுடன் கொண்டு வருகிறது.</p>
        <p lang="en">AgrowNex brings them into one app, in Tamil, built on government and research data.</p>
      </div>
      <div class="tiles reveal" style="grid-template-columns:1fr 1fr; margin-top:0">
        <div class="tile"><span class="mono">01 · {t("மொழி", "Language")}</span><b lang="ta">தமிழ் முதலில்</b><b lang="en">Tamil first</b><p lang="ta">எளிய தமிழ், பெரிய எழுத்து, குரல் வசதி.</p><p lang="en">Plain Tamil, large text, voice input.</p></div>
        <div class="tile"><span class="mono">02 · {t("தரவு", "Data")}</span><b lang="ta">கற்பனை எண்கள் இல்லை</b><b lang="en">No made-up numbers</b><p lang="ta">விலை, வானிலை, திட்டங்கள் — அதிகாரப்பூர்வ மூலங்களிலிருந்து மட்டும்.</p><p lang="en">Prices, weather and schemes only from official sources.</p></div>
        <div class="tile"><span class="mono">03 · {t("பயிர்", "Crop")}</span><b lang="ta">இயற்கை முறை முதலில்</b><b lang="en">Organic care first</b><p lang="ta">ரசாயனம் தேவைப்பட்டால் மட்டும், பாதுகாப்புக் குறிப்புடன்.</p><p lang="en">Chemicals only when needed, with safety notes.</p></div>
        <div class="tile"><span class="mono">04 · {t("நம்பிக்கை", "Trust")}</span><b lang="ta">"தெரியவில்லை" என்று சொல்லும்</b><b lang="en">It says "not sure"</b><p lang="ta">உறுதியில்லாதபோது நிபுணரை அணுகச் சொல்லும்.</p><p lang="en">When unsure, it sends you to an expert.</p></div>
      </div>
    </div>
  </section>

  <section class="band band-mist" id="field">
    <div class="wrap">
      <p class="kicker" lang="ta">களத்தில்</p><p class="kicker" lang="en">In the field</p>
      <h2 lang="ta">விவசாயிகளுடன் நேரில்.</h2>
      <h2 lang="en">Out with farmers, in person.</h2>
      <p class="intro" lang="ta">கன்னியாகுமரி மாவட்டம், திருப்பதிசாரம் வேளாண்மை அறிவியல் நிலையத்தில் (KVK) நடந்த விவசாயிகள் விழிப்புணர்வு முகாமில் AgrowNex பற்றி விளக்கினோம்.</p>
      <p class="intro" lang="en">We presented AgrowNex at a farmers' awareness camp at the Agricultural Science Centre (KVK), Thirupathisaram, Kanyakumari district.</p>
      <div class="gallery">
        <figure class="reveal"><img src="/assets/img/kvk-talk.jpg" alt="Speaking to farmers at the Agricultural Science Centre, Thirupathisaram" width="900" height="1200" loading="lazy">
          <figcaption>{t("விவசாயிகள் விழிப்புணர்வு முகாம், KVK திருப்பதிசாரம்.", "Farmers' awareness camp, KVK Thirupathisaram.")}</figcaption></figure>
        <figure class="reveal"><img src="/assets/img/kvk-handover.jpg" alt="Handing over the AgrowNex information booklet at the KVK office" width="1100" height="997" loading="lazy">
          <figcaption>{t("KVK அலுவலகத்தில் எங்கள் செயலி விவரக் கையேட்டை வழங்கியபோது.", "Handing over our app booklet at the KVK office.")}</figcaption></figure>
      </div>
      <h3 style="margin-top:56px">{t("விவசாயிகள் சொன்னது", "Farmers speaking up")}</h3>
      <p class="intro" lang="ta">அதே முகாமில், AgrowNex-ஐப் பற்றி விவசாயிகள் தங்கள் கருத்துகளை நேரடியாகப் பகிர்ந்தனர்.</p>
      <p class="intro" lang="en">At the same camp, farmers took the microphone to share their views on AgrowNex.</p>
      <div class="gallery pair">
        <figure class="reveal"><img src="/assets/img/farmer-feedback-1.jpg" alt="A farmer speaking into a microphone about AgrowNex at the KVK camp" width="719" height="1280" loading="lazy">
          <figcaption>{t("ஒரு விவசாயி தன் கருத்தைப் பகிர்கிறார், KVK திருப்பதிசாரம்.", "A farmer shares his feedback, KVK Thirupathisaram.")}</figcaption></figure>
        <figure class="reveal"><img src="/assets/img/farmer-feedback-2.jpg" alt="Another farmer giving feedback on AgrowNex at the KVK camp" width="720" height="1280" loading="lazy">
          <figcaption>{t("விவசாயிகளின் கேள்விகளுக்கு நேரடிப் பதில்.", "Answering farmers' questions in person.")}</figcaption></figure>
      </div>
    </div>
  </section>

  <section class="band">
    <div class="wrap grid-2">
      <div class="reveal">
        <p class="kicker" lang="ta">நிறுவனம்</p><p class="kicker" lang="en">The company</p>
        <h2 lang="ta">பதிவு செய்யப்பட்ட இந்திய நிறுவனம்.</h2>
        <h2 lang="en">A registered Indian business.</h2>
        <p class="intro" lang="ta">செயலி, இணையதளம், வாங்குபவர் சேவைகள் அனைத்தையும் இயக்குவது SANTA MARIA ENTERPRISES.</p>
        <p class="intro" lang="en">The app, this website and our buyer services are operated by SANTA MARIA ENTERPRISES.</p>
      </div>
      <dl class="facts reveal">
        <dt>{t("சட்டப் பெயர்", "Legal name")}</dt><dd>SANTA MARIA ENTERPRISES</dd>
        <dt>{t("பதிவு", "Registration")}</dt><dd>{t("உத்யம் (MSME)", "Udyam (MSME)")} · UDYAM-TN-26-0095328</dd>
        <dt>{t("முகவரி", "Address")}</dt><dd>232/1 North Raja Street, Near Mattakadai, Thoothukudi 628001, Tamil Nadu</dd>
        <dt>{t("மின்னஞ்சல்", "Email")}</dt><dd><a href="mailto:agrowai.tn@gmail.com">agrowai.tn@gmail.com</a></dd>
        <dt>{t("தனியுரிமை", "Privacy")}</dt><dd><a href="/privacy">{t("தனியுரிமைக் கொள்கை", "Privacy policy")}</a> · <a href="/delete-account">{t("கணக்கை நீக்குதல்", "Delete account")}</a></dd>
      </dl>
    </div>
  </section>

  <section class="band band-ink">
    <div class="wrap">
      <p class="kicker" lang="ta">எங்களுடன் இணையுங்கள்</p><p class="kicker" lang="en">Work with us</p>
      <h2 lang="ta">விவசாயி, வாங்குபவர், கூட்டாளர் — எல்லோருக்கும் இடம்.</h2>
      <h2 lang="en">Farmer, buyer or partner — there's a place for you.</h2>
      <div class="biz">
        <a href="/wholesale"><img src="/assets/img/mandi.jpg" alt="" width="1400" height="1045" loading="lazy">
          <div class="t"><h3>{t("மொத்த வாங்குபவர்கள்", "Wholesale buyers")}</h3><span lang="ta">விவசாயக் குழுக்களிடமிருந்து நேரடியாக வாங்குங்கள் <em>→</em></span><span lang="en">Source directly from farmer groups <em>→</em></span></div></a>
        <a href="/partners"><img src="/assets/img/kvk-handover.jpg" alt="" width="1100" height="997" loading="lazy">
          <div class="t"><h3>{t("FPO, KVK கூட்டாளர்கள்", "FPO & KVK partners")}</h3><span lang="ta">உங்கள் விவசாயிகளை ஒரே திரையில் <em>→</em></span><span lang="en">All your farmers on one screen <em>→</em></span></div></a>
      </div>
    </div>
  </section>''', og='/assets/img/kvk-talk.jpg')

# ---------------------------------------------------------------- contact
contact = page('contact', 'Contact AgrowNex',
    'Contact AgrowNex by email or WhatsApp — for farmers, wholesale buyers, FPOs, KVKs and partners.',
    'contact', f'''{hero("/assets/img/monsoon.jpg", "Monsoon clouds over flat green farmland",
    "agrowai.tn@gmail.com",
    "பேசலாம். <em>தமிழிலோ ஆங்கிலத்திலோ.</em>",
    "Let's talk. <em>In Tamil or English.</em>",
    "மின்னஞ்சல் அல்லது WhatsApp — உங்களுக்கு எளிதானது எதுவோ அதில்.",
    "Email or WhatsApp — whichever is easier for you.")}

  <section class="band">
    <div class="wrap">
      <div class="tiles">
        <div class="tile"><span class="mono">{t("விவசாயிகள்", "Farmers")}</span><b lang="ta">செயலியை முதலில் பெற</b><b lang="en">Get the app first</b>
          <p lang="ta">பெயர், கிராமம், பயிரை அனுப்புங்கள்.</p><p lang="en">Send your name, village and crop.</p>
          <p style="margin-top:14px"><a href="/#get">{t("முன்பதிவு →", "Early access →")}</a></p></div>
        <div class="tile"><span class="mono">{t("வாங்குபவர்கள்", "Buyers")}</span><b lang="ta">மொத்தக் கொள்முதல்</b><b lang="en">Wholesale sourcing</b>
          <p lang="ta">பயிர், அளவு, தரம், தேதி.</p><p lang="en">Crop, volume, grade and dates.</p>
          <p style="margin-top:14px"><a href="/wholesale#enquire">{t("தேவையைப் பதிவு செய்யுங்கள் →", "Send a requirement →")}</a></p></div>
        <div class="tile"><span class="mono">{t("கூட்டாளர்கள்", "Partners")}</span><b lang="ta">FPO, KVK, NGO</b><b lang="en">FPO, KVK, NGO</b>
          <p lang="ta">சோதனை முயற்சி அல்லது கூட்டாண்மை.</p><p lang="en">A pilot or a partnership.</p>
          <p style="margin-top:14px"><a href="/partners#join">{t("கூட்டாளராகுங்கள் →", "Become a partner →")}</a></p></div>
      </div>
    </div>
  </section>

  <section class="band band-mist">
    <div class="wrap grid-2">
      <div class="reveal">
        <p class="kicker" lang="ta">செய்தி அனுப்புங்கள்</p><p class="kicker" lang="en">Send a message</p>
        <h2 lang="ta">வேறு எதுவாக இருந்தாலும்.</h2>
        <h2 lang="en">For anything else.</h2>
        <dl class="facts">
          <dt>{t("மின்னஞ்சல்", "Email")}</dt><dd><a href="mailto:agrowai.tn@gmail.com">agrowai.tn@gmail.com</a></dd>
          <dt>WhatsApp</dt><dd><a href="https://wa.me/918667237404" target="_blank" rel="noopener">+91 86672 37404</a></dd>
          <dt>{t("முகவரி", "Address")}</dt><dd>SANTA MARIA ENTERPRISES, 232/1 North Raja Street, Near Mattakadai, Thoothukudi 628001</dd>
        </dl>
      </div>
      {form("AgrowNex enquiry", [
        (field("c-name", "name", "உங்கள் பெயர்", "Your name"), field("c-phone", "phone", "கைபேசி", "Phone", "tel")),
        field("c-msg", "message", "செய்தி", "Message", "textarea"),
      ], *FORM_NOTE)}
    </div>
  </section>''')

for slug, html in [('wholesale', wholesale), ('partners', partners), ('about', about), ('contact', contact)]:
    (W / f'{slug}.html').write_text(html)
    print('wrote', slug, len(html))

# ---------------------------------------------------------------- index: shared header/footer + business section
idx = (W / 'index.html').read_text()
idx = re.sub(r'<a class="skip".*?</header>', header('home').replace('href="/#app"', 'href="#app"'), idx, flags=re.S)
idx = re.sub(r'<footer>.*?</footer>', FOOTER, idx, flags=re.S)
biz = f'''  <!-- For business -->
  <section class="band band-mist" id="business">
    <div class="wrap">
      <p class="kicker" lang="ta">வணிகம், கூட்டாண்மை</p><p class="kicker" lang="en">For business</p>
      <h2 lang="ta">விவசாயிகளின் விளைச்சல் சரியான வாங்குபவரைச் சேர.</h2>
      <h2 lang="en">Helping farmers' harvests reach the right buyers.</h2>
      <div class="biz">
        <a href="/wholesale"><img src="/assets/img/mandi.jpg" alt="" width="1400" height="1045" loading="lazy">
          <div class="t"><h3>{t("மொத்த வாங்குபவர்கள்", "Wholesale buyers")}</h3><span lang="ta">நெல், வாழை, மிளகாய், தேங்காய் — விவசாயக் குழுக்களிடமிருந்து நேரடியாக <em>→</em></span><span lang="en">Paddy, banana, chilli, coconut — direct from farmer groups <em>→</em></span></div></a>
        <a href="/partners"><img src="/assets/img/kvk-talk.jpg" alt="" width="900" height="1200" loading="lazy" style="object-position:50% 35%">
          <div class="t"><h3>{t("FPO, KVK கூட்டாளர்கள்", "FPO & KVK partners")}</h3><span lang="ta">உங்கள் விவசாயிகள் அனைவரும் ஒரே திரையில் <em>→</em></span><span lang="en">All your farmers on one screen <em>→</em></span></div></a>
      </div>
      <p style="margin-top:28px"><a href="/about#field">{t("களத்தில்: கன்னியாகுமரி KVK முகாமில் விவசாயிகளின் கருத்துகள் →", "In the field: farmers' feedback at the Kanyakumari KVK camp →")}</a></p>
    </div>
  </section>

  <!-- FAQ -->'''
if 'id="business"' in idx:
    idx = re.sub(r'  <!-- For business -->.*?  <!-- FAQ -->', lambda m: biz, idx, flags=re.S)
else:
    idx = idx.replace('  <!-- FAQ -->', biz, 1)
idx = idx.replace('href="mailto:agrowai.tn@gmail.com?subject=AgrowNex%20partnership"', 'href="/partners#join"')
(W / 'index.html').write_text(idx)
print('index updated')
