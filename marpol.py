import os
import io
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, time
import streamlit as st

# ReportLab Kütüphaneleri (PDF Oluşturma)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Gemilerden Atık Alım Hizmeti Ücret Hesaplayıcı",
    page_icon="🚢",
    layout="wide"
)

# Özel CSS
st.markdown("""
    <style>
    .main { padding: 1.5rem; }
    .stButton>button { width: 100%; background-color: #00407A; color: white; font-weight: bold; height: 48px; border-radius: 6px; }
    .stDownloadButton>button { width: 100%; background-color: #28a745; color: white; font-weight: bold; height: 50px; border-radius: 6px; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# TÜRKÇE FONT KAYDI (UNICODE / UTF-8)
# ---------------------------------------------------------

@st.cache_resource
def setup_turkish_fonts():
    """PDF için tam Türkçe karakter (UTF-8) destekli fontları kaydeder."""
    reg_path, bold_path = None, None
    
    # 1. Sistem Fontlarını Kontrol Et (Linux / Windows / Mac)
    if os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        reg_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    elif os.path.exists("C:\\Windows\\Fonts\\arial.ttf"):
        reg_path = "C:\\Windows\\Fonts\\arial.ttf"
        bold_path = "C:\\Windows\\Fonts\\arialbd.ttf"
    
    # 2. Sistemde Yoksa Google Fonts'tan Roboto İndir/Kullan
    if not reg_path or not os.path.exists(reg_path):
        if not os.path.exists("Roboto-Regular.ttf"):
            try:
                urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/roboto/Roboto-Regular.ttf", "Roboto-Regular.ttf")
            except Exception:
                pass
        reg_path = "Roboto-Regular.ttf" if os.path.exists("Roboto-Regular.ttf") else None

    if not bold_path or not os.path.exists(bold_path):
        if not os.path.exists("Roboto-Bold.ttf"):
            try:
                urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/roboto/Roboto-Bold.ttf", "Roboto-Bold.ttf")
            except Exception:
                pass
        bold_path = "Roboto-Bold.ttf" if os.path.exists("Roboto-Bold.ttf") else None

    # Fontları ReportLab'a kaydet
    if reg_path and os.path.exists(reg_path):
        pdfmetrics.registerFont(TTFont('TRFont', reg_path))
        if bold_path and os.path.exists(bold_path):
            pdfmetrics.registerFont(TTFont('TRFont-Bold', bold_path))
        else:
            pdfmetrics.registerFont(TTFont('TRFont-Bold', reg_path))
        registerFontFamily('TRFont', normal='TRFont', bold='TRFont-Bold')
        return 'TRFont', 'TRFont-Bold'
    
    return 'Helvetica', 'Helvetica-Bold'

# ---------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------

@st.cache_data(ttl=3600)
def get_tcmb_eur_kuru():
    """TCMB resmi sitesinden güncel EUR döviz satış kurunu çeker."""
    try:
        url = "https://www.tcmb.gov.tr/kurlar/today.xml"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        for currency in root.findall('Currency'):
            if currency.get('Kod') == 'EUR':
                forex_selling = currency.find('ForexSelling').text
                return float(forex_selling)
    except Exception:
        return 55.2385

def get_sabit_ucret_ve_haklar(grt):
    """GRT'ye göre Sabit Ücret (€) ve Ücretsiz Atık Haklarını (m³) döndürür."""
    if grt <= 1000:
        return 80, 1, 2, 1
    elif grt <= 5000:
        return 140, 3, 2, 1
    elif grt <= 10000:
        return 210, 4, 3, 2
    elif grt <= 15000:
        return 250, 5, 4, 2
    elif grt <= 20000:
        return 300, 6, 5, 2
    elif grt <= 25000:
        return 350, 7, 5, 3
    elif grt <= 35000:
        return 400, 8, 6, 3
    elif grt <= 60000:
        return 540, 10, 10, 4
    else:
        return 720, 13, 15, 5

def generate_pdf(detay_veri):
    """Hesaplama özetini Türkçe karakter destekli resmi PDF dosyası olarak üretir."""
    font_norm, font_bold = setup_turkish_fonts()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    mbb_blue = colors.HexColor('#00407A')
    dark_text = colors.HexColor('#212529')

    style_title = ParagraphStyle('DocTitle', parent=styles['Normal'], fontName=font_bold, fontSize=14, leading=18, textColor=mbb_blue)
    style_subtitle = ParagraphStyle('DocSubTitle', parent=styles['Normal'], fontName=font_norm, fontSize=9, leading=12, textColor=colors.HexColor('#555555'))
    style_bold = ParagraphStyle('BoldTxt', parent=styles['Normal'], fontName=font_bold, fontSize=9, leading=12, textColor=dark_text)
    style_normal = ParagraphStyle('NormTxt', parent=styles['Normal'], fontName=font_norm, fontSize=9, leading=12, textColor=dark_text)

    story = []

    # Antet Başlığı
    story.append(Paragraph("T.C. MUĞLA BÜYÜKŞEHİR BELEDİYESİ", style_title))
    story.append(Paragraph("Gemilerden Atık Alım Hizmeti Ücret Hesaplama Fişi (Tebliğ No: 2009/3)", style_subtitle))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=mbb_blue, spaceBefore=0, spaceAfter=12))

    # Gemi ve İşlem Bilgileri Tablosu
    info_data = [
        [Paragraph("<b>Gemi ve Sefer Parametreleri</b>", style_bold), Paragraph("", style_normal)],
        [Paragraph("Gemi Tonajı (GRT):", style_normal), Paragraph(f"{detay_veri['grt']:,} GRT", style_bold)],
        [Paragraph("Gemi Statüsü:", style_normal), Paragraph(detay_veri['gemi_turu_label'], style_normal)],
        [Paragraph("İşlem Yeri / Durumu:", style_normal), Paragraph("Açıkta / Demir Alanında" if detay_veri['acikta_mi'] else "Liman İçi / Yanaşık", style_normal)],
        [Paragraph("İşlem Tarihi ve Saati:", style_normal), Paragraph(f"{detay_veri['islem_tarihi']} - {detay_veri['islem_saati']}", style_normal)],
        [Paragraph("Uygulanan EUR/TRY Kuru:", style_normal), Paragraph(f"{detay_veri['eur_try_kuru']:.4f} TL", style_bold)],
    ]

    t_info = Table(info_data, colWidths=[200, 322])
    t_info.setStyle(TableStyle([
        ('SPAN', (0,0), (1,0)),
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#EBF3FA')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DDDDDD')),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 10))

    # Atık Miktarları ve Ücretsiz Hak Dökümü Tablosu
    atik_data = [
        [Paragraph("<b>Atık Türü</b>", style_bold), Paragraph("<b>Teslim Edilen</b>", style_bold), Paragraph("<b>Ücretsiz Hak</b>", style_bold), Paragraph("<b>Ücrete Tabi Miktar</b>", style_bold)],
        [Paragraph("MARPOL EK-I (Sintine, Slaç, Yağ)", style_normal), Paragraph(f"{detay_veri['sintine_m3']} m³", style_normal), Paragraph(f"{detay_veri['ek1_hak']} m³", style_normal), Paragraph(f"{detay_veri['ucretli_ek1']:.2f} m³", style_bold)],
        [Paragraph("MARPOL EK-IV (Pis Su)", style_normal), Paragraph(f"{detay_veri['pissu_m3']} m³", style_normal), Paragraph(f"{detay_veri['ek4_hak']} m³", style_normal), Paragraph(f"{detay_veri['ucretli_ek4']:.2f} m³", style_bold)],
        [Paragraph("MARPOL EK-V (Evsel / Çöp)", style_normal), Paragraph(f"{detay_veri['evsel_m3']} m³", style_normal), Paragraph(f"{detay_veri['ek5_hak']} m³", style_normal), Paragraph(f"{detay_veri['ucretli_ek5']:.2f} m³", style_bold)],
        [Paragraph("MARPOL EK-I (Slop / Kirli Balast)", style_normal), Paragraph(f"{detay_veri['slop_m3']} m³", style_normal), Paragraph("0 m³", style_normal), Paragraph(f"{detay_veri['ucretli_slop']:.2f} m³", style_bold)],
    ]

    t_atik = Table(atik_data, colWidths=[200, 100, 100, 122])
    t_atik.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EBF3FA')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DDDDDD')),
    ]))
    story.append(t_atik)
    story.append(Spacer(1, 10))

    # Ücret Özeti Tablosu (Tavan / Taban)
    ucret_data = [
        [Paragraph("<b>Ücret Bileşeni</b>", style_bold), Paragraph("<b>AZAMİ (TAVAN) ÜCRET</b>", style_bold), Paragraph("<b>ASGARİ (TABAN) ÜCRET</b>", style_bold)],
        [Paragraph("Sabit Ücret:", style_normal), Paragraph(f"{detay_veri['sabit_ucret_eur']:,.2f} EUR", style_normal), Paragraph(f"{detay_veri['sabit_ucret_eur']:,.2f} EUR", style_normal)],
        [Paragraph("Atık Alım Ücreti:", style_normal), Paragraph(f"{detay_veri['atik_ucreti_tavan_eur']:,.2f} EUR", style_normal), Paragraph(f"{detay_veri['atik_ucreti_taban_eur']:,.2f} EUR (%40 ind.)", style_normal)],
        [Paragraph("<b>TOPLAM ÜCRET (EUR):</b>", style_bold), Paragraph(f"<b>{detay_veri['toplam_tavan_eur']:,.2f} EUR</b>", style_bold), Paragraph(f"<b>{detay_veri['toplam_taban_eur']:,.2f} EUR</b>", style_bold)],
        [Paragraph("<b>TOPLAM ÜCRET (TRY):</b>", style_bold), Paragraph(f"<b>{detay_veri['toplam_tavan_tl']:,.2f} TL</b>", style_bold), Paragraph(f"<b>{detay_veri['toplam_taban_tl']:,.2f} TL</b>", style_bold)],
    ]

    t_ucret = Table(ucret_data, colWidths=[180, 171, 171])
    t_ucret.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EBF3FA')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DDDDDD')),
        ('BACKGROUND', (1,3), (1,4), colors.HexColor('#FADBD8')),
        ('BACKGROUND', (2,3), (2,4), colors.HexColor('#D4EFDF')),
    ]))
    story.append(t_ucret)
    story.append(Spacer(1, 15))

    # Not
    story.append(Paragraph("<b>Yasal Not:</b> Bu belge 2009/3 sayılı Tebliğ hükümlerine göre bilgilendirme amacıyla otomatik üretilmiştir. Resmi tahsilatlarda ilgili işletmenin resmi tarifesi esastır.", style_subtitle))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------
# HEADER / LOGO ALANI
# ---------------------------------------------------------

logo_dosyasi = "mbblogo.svg"
mbb_kurumsal_mavi = "#00407A"

if os.path.exists(logo_dosyasi):
    col_logo, col_title = st.columns([2, 4], gap="large")
    with col_logo:
        st.markdown("<div style='display: flex; align-items: center; height: 100%; margin-top: 10px;'>", unsafe_allow_html=True)
        st.image(logo_dosyasi, width=500)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_title:
        st.markdown(f"<h1 style='color: {mbb_kurumsal_mavi}; margin-bottom: 0px; font-weight: 600;'>Gemilerden Atık Alım Hizmeti Ücret Hesaplayıcı</h1>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 1.1rem; color: #4A5568; margin-top: 5px; font-weight: 400;'>Tebliğ No: 2009/3 Çerçevesinde Asgari ve Azami Fiyat Hesaplama Modülü</p>", unsafe_allow_html=True)
else:
    st.markdown(f"<h1 style='color: {mbb_kurumsal_mavi};'>🚢 Gemilerden Atık Alım Hizmeti Ücret Hesaplayıcı</h1>", unsafe_allow_html=True)
    st.caption("Tebliğ No: 2009/3 Çerçevesinde Asgari ve Azami Fiyat Hesaplama Modülü")

st.divider()

# ---------------------------------------------------------
# ARAYÜZ (GİRDİ ALANLARI)
# ---------------------------------------------------------

col_sol, col_sag = st.columns([1, 1], gap="large")

gemi_turleri = [
    ("normal", "Ticari / Diğer Gemiler"),
    ("kamu_devlet", "Devlete Ait / Ticari Olmayan Hizmet Gemisi (Madde 4 - Muaf)"),
    ("kabotaj_tanker", "Kabotaj Hattı Tanker (< 150 GRT)"),
    ("kabotaj_diger", "Kabotaj Hattı Diğer Gemi (< 400 GRT)"),
    ("yat_tekne", "Yat / Tekne (Max 12 Yolcu)")
]

with col_sol:
    st.subheader("📋 Gemi ve Sefer Bilgileri")
    grt = st.number_input("Gemi Tonajı (GRT)", min_value=1, value=150, step=100)
    
    gemi_turu_tuple = st.selectbox(
        "Gemi Türü / Statüsü",
        options=gemi_turleri,
        format_func=lambda x: x[1]
    )
    gemi_turu = gemi_turu_tuple[0]
    gemi_turu_label = gemi_turu_tuple[1]
    
    acikta_mi = st.checkbox("İşlem Açıkta/Demir Alanında mı Yapılıyor? (Madde 8)")
    sabit_ucret_odendi_mi = st.checkbox("Sabit Ücret Daha Önce Başka Limanda Ödendi mi? (Madde 6)")
    
    st.subheader("📅 Tarih ve Mesai Bilgisi")
    islem_tarihi = st.date_input("İşlem Tarihi", value=datetime.now())
    islem_saati = st.time_input("İşlem Saati", value=time(10, 0))

with col_sag:
    st.subheader("🛢️ Verilecek Atık Miktarları (m³)")
    slop_balast_m3 = st.number_input("MARPOL EK-I: Slop / Kirli Balast (m³)", min_value=0.0, value=0.0, step=0.5)
    sintine_slac_yag_m3 = st.number_input("MARPOL EK-I: Sintine Suyu, Slaç, Atık Yağ (m³)", min_value=0.0, value=0.0, step=0.5)
    ek4_pissu_m3 = st.number_input("MARPOL EK-IV: Pis Su (m³)", min_value=0.0, value=1.0, step=0.5)
    ek5_evsel_m3 = st.number_input("MARPOL EK-V: Evsel / Katı Çöp (m³)", min_value=0.0, value=1.0, step=0.5)
    
    st.subheader("💶 Döviz Kuru")
    otomatik_kur = get_tcmb_eur_kuru()
    eur_try_kuru = st.number_input(
        "EUR / TRY Kuru (TCMB Otomatik / Manuel Değiştirilebilir)", 
        min_value=1.0, 
        value=otomatik_kur, 
        step=0.0001,
        format="%.4f"
    )

# ---------------------------------------------------------
# HESAPLAMA MOTORU
# ---------------------------------------------------------

sabit_ucret_eur, ek1_hak, ek4_hak, ek5_hak = get_sabit_ucret_ve_haklar(grt)

if gemi_turu in ["kamu_devlet", "yat_tekne"] or sabit_ucret_odendi_mi:
    sabit_ucret_eur = 0
    ek1_hak = ek4_hak = ek5_hak = 0

ucretli_slop = slop_balast_m3
ucretli_ek1 = max(0.0, sintine_slac_yag_m3 - ek1_hak)
ucretli_ek4 = max(0.0, ek4_pissu_m3 - ek4_hak)
ucretli_ek5 = max(0.0, ek5_evsel_m3 - ek5_hak)

if acikta_mi:
    fiyat_slop = 5.0
    fiyat_ek1 = 35.0 * 1.30
    fiyat_ek4 = 15.0 * 1.30
    fiyat_ek5 = 25.0 * 1.30
else:
    fiyat_slop = 1.5
    fiyat_ek1 = 35.0
    fiyat_ek4 = 15.0
    fiyat_ek5 = 25.0

if (gemi_turu == "kabotaj_tanker" and grt < 150) or (gemi_turu == "kabotaj_diger" and grt < 400):
    fiyat_slop *= 0.75
    fiyat_ek1 *= 0.75
    fiyat_ek4 *= 0.75
    fiyat_ek5 *= 0.75
elif gemi_turu == "yat_tekne":
    fiyat_slop *= 0.50
    fiyat_ek1 *= 0.50
    fiyat_ek4 *= 0.50
    fiyat_ek5 *= 0.50

atik_ucreti_tavan_eur = (
    (ucretli_slop * fiyat_slop) +
    (ucretli_ek1 * fiyat_ek1) +
    (ucretli_ek4 * fiyat_ek4) +
    (ucretli_ek5 * fiyat_ek5)
)

is_pazar = islem_tarihi.weekday() == 6
is_mesai_disi = not (time(8, 0) <= islem_saati <= time(17, 0))

if is_pazar or is_mesai_disi:
    atik_ucreti_tavan_eur *= 1.25
    mesai_zammi_var = True
else:
    mesai_zammi_var = False

atik_ucreti_taban_eur = atik_ucreti_tavan_eur * 0.60

toplam_tavan_eur = sabit_ucret_eur + atik_ucreti_tavan_eur
toplam_taban_eur = sabit_ucret_eur + atik_ucreti_taban_eur

toplam_tavan_tl = toplam_tavan_eur * eur_try_kuru
toplam_taban_tl = toplam_taban_eur * eur_try_kuru

# ---------------------------------------------------------
# SONUÇ EKRANI
# ---------------------------------------------------------

st.divider()
st.header("📊 Uygulanabilecek Ücret Sınırları")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔴 AZAMİ (TAVAN) ÜCRET")
    st.caption("Herhangi bir esnek indirim uygulanmamış üst sınır ücretidir.")
    st.metric("Tavan Fiyat (€)", f"{toplam_tavan_eur:,.2f} €")
    st.metric("Tavan Fiyat (₺)", f"{toplam_tavan_tl:,.2f} ₺")
    st.write(f"*(Sabit Ücret: {sabit_ucret_eur:,.2f} € + Atık Ücreti: {atik_ucreti_tavan_eur:,.2f} €)*")

with col2:
    st.markdown("### 🟢 ASGARİ (TABAN) ÜCRET")
    st.caption("Madde 13 uyarınca azami %40 indirim uygulanmış alt sınır ücretidir.")
    st.metric("Taban Fiyat (€)", f"{toplam_taban_eur:,.2f} €")
    st.metric("Taban Fiyat (₺)", f"{toplam_taban_tl:,.2f} ₺")
    st.write(f"*(Sabit Ücret: {sabit_ucret_eur:,.2f} € + %40 İndirimli Atık Ücreti: {atik_ucreti_taban_eur:,.2f} €)*")

if mesai_zammi_var:
    st.warning("⚠️ İşlem saati mesai dışı / tatil gününe denk geldiği için atık ücretlerine %25 zam uygulanmıştır.")

with st.expander("🔍 Detaylı Ücretsiz Hak ve Ücretlendirme Dökümü"):
    st.write(f"- **MARPOL EK-I Ücretsiz Hak:** {ek1_hak} m³ | **Ücrete Tabi:** {ucretli_ek1:.2f} m³")
    st.write(f"- **MARPOL EK-IV Ücretsiz Hak:** {ek4_hak} m³ | **Ücrete Tabi:** {ucretli_ek4:.2f} m³")
    st.write(f"- **MARPOL EK-V Ücretsiz Hak:** {ek5_hak} m³ | **Ücrete Tabi:** {ucretli_ek5:.2f} m³")
    st.write(f"- **Slop / Kirli Balast Ücretli Miktar:** {ucretli_slop:.2f} m³")

# ---------------------------------------------------------
# PDF İNDİRME BUTONU
# ---------------------------------------------------------

st.divider()

detay_veri = {
    'grt': grt,
    'gemi_turu_label': gemi_turu_label,
    'acikta_mi': acikta_mi,
    'islem_tarihi': islem_tarihi.strftime('%d.%m.%Y'),
    'islem_saati': islem_saati.strftime('%H:%M'),
    'eur_try_kuru': eur_try_kuru,
    'slop_m3': slop_balast_m3,
    'sintine_m3': sintine_slac_yag_m3,
    'pissu_m3': ek4_pissu_m3,
    'evsel_m3': ek5_evsel_m3,
    'ek1_hak': ek1_hak,
    'ek4_hak': ek4_hak,
    'ek5_hak': ek5_hak,
    'ucretli_slop': ucretli_slop,
    'ucretli_ek1': ucretli_ek1,
    'ucretli_ek4': ucretli_ek4,
    'ucretli_ek5': ucretli_ek5,
    'sabit_ucret_eur': sabit_ucret_eur,
    'atik_ucreti_tavan_eur': atik_ucreti_tavan_eur,
    'atik_ucreti_taban_eur': atik_ucreti_taban_eur,
    'toplam_tavan_eur': toplam_tavan_eur,
    'toplam_taban_eur': toplam_taban_eur,
    'toplam_tavan_tl': toplam_tavan_tl,
    'toplam_taban_tl': toplam_taban_tl
}

pdf_buffer = generate_pdf(detay_veri)

st.download_button(
    label="📄 Hesaplama Çıktısını PDF Olarak İndir",
    data=pdf_buffer,
    file_name=f"MBB_Atik_Hesaplama_Fisi_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
    mime="application/pdf"
)