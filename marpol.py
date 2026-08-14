import streamlit as st
from datetime import datetime, time

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Gemilerden Atık Alım Ücreti Hesaplayıcı",
    page_icon="🚢",
    layout="wide"
)

# Canva içi ve mobilde düzgün görünüm için özel CSS
st.markdown("""
    <style>
    .main { padding: 1.5rem; }
    .stButton>button { width: 100%; background-color: #0066cc; color: white; font-weight: bold; }
    .metric-box { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #0066cc; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# MANTIKSAL FONKSİYONLAR (Tebliğ No: 2009/3)
# ---------------------------------------------------------

def get_sabit_ucret_ve_haklar(grt):
    """GRT'ye göre Sabit Ücret (€) ve Ücretsiz Atık Haklarını ($m^3$) döndürür."""
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

# ---------------------------------------------------------
# ARAYÜZ (STREAMLIT)
# ---------------------------------------------------------

st.title("🚢 Gemilerden Atık Alım Hizmeti Ücret Hesaplayıcı")
st.caption("Tebliğ No: 2009/3 Çerçevesinde Güncel Hesaplama Modülü")

col_sol, col_sag = st.columns([1, 1], gap="large")

with col_sol:
    st.subheader("📋 Gemi ve Sefer Bilgileri")
    
    grt = st.number_input("Gemi Tonajı (GRT)", min_value=1, value=5000, step=100)
    
    gemi_turu = st.selectbox(
        "Gemi Türü / Statüsü",
        options=[
            ("normal", "Ticari / Diğer Gemiler"),
            ("kamu_devlet", "Devlete Ait / Ticari Olmayan Hizmet Gemisi (Madde 4 - Muaf)"),
            ("kabotaj_tanker", "Kabotaj Hattı Tanker (< 150 GRT)"),
            ("kabotaj_diger", "Kabotaj Hattı Diğer Gemi (< 400 GRT)"),
            ("yat_tekne", "Yat / Tekne (Max 12 Yolcu)")
        ],
        format_func=lambda x: x[1]
    )[0]
    
    acikta_mi = st.checkbox("İşlem Açıkta/Demir Alanında mı Yapılıyor? (Madde 8)")
    sabit_ucret_odendi_mi = st.checkbox("Sabit Ücret Daha Önce Başka Limanda Ödendi mi? (Madde 6)")
    
    st.subheader("📅 Tarih ve Mesai Bilgisi")
    islem_tarihi = st.date_input("İşlem Tarihi", value=datetime.now())
    islem_saati = st.time_input("İşlem Saati", value=time(10, 0))
    
    st.subheader("💶 Döviz Kuru")
    eur_try_kuru = st.number_input("EUR / TRY Kuru", min_value=1.0, value=55.39, step=0.1)

with col_sag:
    st.subheader("🛢️ Verilecek Atık Miktarları (m³)")
    
    slop_balast_m3 = st.number_input("MARPOL EK-I: Slop / Kirli Balast (m³)", min_value=0.0, value=0.0, step=0.5)
    sintine_slac_yag_m3 = st.number_input("MARPOL EK-I: Sintine Suyu, Slaç, Atık Yağ (m³)", min_value=0.0, value=5.0, step=0.5)
    ek4_pissu_m3 = st.number_input("MARPOL EK-IV: Pis Su (m³)", min_value=0.0, value=2.0, step=0.5)
    ek5_evsel_m3 = st.number_input("MARPOL EK-V: Evsel / Katı Çöp (m³)", min_value=0.0, value=1.0, step=0.5)
    
    st.subheader("🏷️ İndirim Oranı (Madde 13)")
    esnek_indirim = st.slider("Uygulanacak İndirim Oranı (%)", min_value=0, max_value=40, value=0) / 100.0

# ---------------------------------------------------------
# HESAPLAMA MOTORU
# ---------------------------------------------------------

# 1. Sabit Ücret ve Haklar
sabit_ucret_eur, ek1_hak, ek4_hak, ek5_hak = get_sabit_ucret_ve_haklar(grt)

# Muafiyet Kontrolü
if gemi_turu in ["kamu_devlet", "yat_tekne"] or sabit_ucret_odendi_mi:
    sabit_ucret_eur = 0
    ek1_hak = ek4_hak = ek5_hak = 0

# Ücrete Tabi Miktarlar
ucretli_slop = slop_balast_m3
ucretli_ek1 = max(0.0, sintine_slac_yag_m3 - ek1_hak)
ucretli_ek4 = max(0.0, ek4_pissu_m3 - ek4_hak)
ucretli_ek5 = max(0.0, ek5_evsel_m3 - ek5_hak)

# Birim Fiyatlar (€)
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

# Madde 5 İndirimleri
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

# Esnek İndirim (Madde 13)
fiyat_slop *= (1 - esnek_indirim)
fiyat_ek1 *= (1 - esnek_indirim)
fiyat_ek4 *= (1 - esnek_indirim)
fiyat_ek5 *= (1 - esnek_indirim)

# Atık Ücreti Toplamı
atik_ucreti_eur = (
    (ucretli_slop * fiyat_slop) +
    (ucretli_ek1 * fiyat_ek1) +
    (ucretli_ek4 * fiyat_ek4) +
    (ucretli_ek5 * fiyat_ek5)
)

# Mesai Dışı Zammı (Pazar günü veya 08:00-17:00 dışı)
is_pazar = islem_tarihi.weekday() == 6
is_mesai_disi = not (time(8, 0) <= islem_saati <= time(17, 0))

if is_pazar or is_mesai_disi:
    atik_ucreti_eur *= 1.25
    mesai_zammi_var = True
else:
    mesai_zammi_var = False

toplam_eur = sabit_ucret_eur + atik_ucreti_eur
toplam_tl = toplam_eur * eur_try_kuru

# ---------------------------------------------------------
# SONUÇ EKRANI
# ---------------------------------------------------------

st.divider()
st.header("📊 Hesaplama Özeti")

res1, res2, res3, res4 = st.columns(4)

with res1:
    st.metric("Sabit Ücret", f"{sabit_ucret_eur:,.2f} €")
with res2:
    st.metric("Atık Alım Ücreti", f"{atik_ucreti_eur:,.2f} €")
with res3:
    st.metric("Toplam (€)", f"{toplam_eur:,.2f} €")
with res4:
    st.metric("Toplam (₺)", f"{toplam_tl:,.2f} ₺")

if mesai_zammi_var:
    st.warning("⚠️ İşlem saati mesai dışı / tatil gününe denk geldiği için atık ücretlerine %25 zam uygulanmıştır.")

with st.expander("🔍 Detaylı Ücretsiz Hak ve Ücretlendirme Dökümü"):
    st.write(f"- **MARPOL EK-I Ücretsiz Hak:** {ek1_hak} m³ | **Ücrete Tabi:** {ucretli_ek1:.2f} m³")
    st.write(f"- **MARPOL EK-IV Ücretsiz Hak:** {ek4_hak} m³ | **Ücrete Tabi:** {ucretli_ek4:.2f} m³")
    st.write(f"- **MARPOL EK-V Ücretsiz Hak:** {ek5_hak} m³ | **Ücrete Tabi:** {ucretli_ek5:.2f} m³")
    st.write(f"- **Slop / Kirli Balas,t Ücretli Miktar:** {ucretli_slop:.2f} m³")