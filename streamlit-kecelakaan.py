import streamlit as st
import geopandas as gpd
import pandas as pd
from sklearn.cluster import KMeans
from streamlit_folium import st_folium

# -------------------------------
# CSS Styling untuk kotak putih dengan teks gelap
# -------------------------------
st.markdown("""
    <style>
        .section-title {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        .metric-box-white {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            color: #333333;
            text-align: center;
            font-weight: bold;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# -------------------------------
# Load data
# -------------------------------
shp_path = 'surabaya.shp'  # sesuaikan path
df_sby = gpd.read_file(shp_path)

kskk = pd.read_csv("KSKK.csv") 
loc = kskk['Lokasi'].value_counts().reset_index()
loc.columns = ['Lokasi', 'Jumlah Kecelakaan']

# Bersihkan nama kecamatan
loc['Kecamatan'] = loc['Lokasi'].str.replace('KEC. ', '', regex=False)
loc['Kecamatan'] = loc['Kecamatan'].str.replace(', KOTA SURABAYA', '', regex=False)
loc['Kecamatan'] = loc['Kecamatan'].str.title()

# Mapping koreksi nama kecamatan
mapping_kecamatan = {
    'Karangpilang': 'Karang Pilang',
    'Pabean Cantikan': 'Pabean Cantian',
    'Sukomanunggal': 'Suko Manunggal',
    'Asem Rowo': 'Asemrowo',
    'Dukuhpakis': 'Dukuh Pakis'
}
loc['Kecamatan'] = loc['Kecamatan'].replace(mapping_kecamatan)

# -------------------------------
# K-Means Clustering
# -------------------------------
X = loc[['Jumlah Kecelakaan']]
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
loc['Cluster'] = kmeans.fit_predict(X)

# Tentukan kategori zona berdasarkan rata-rata cluster
cluster_order = loc.groupby('Cluster')['Jumlah Kecelakaan'].mean().sort_values(ascending=False).index
kategori_map = {}
for idx, cluster_label in enumerate(cluster_order):
    if idx == 0:
        kategori_map[cluster_label] = 'Zona Merah (Rawan)'
    elif idx == 1:
        kategori_map[cluster_label] = 'Zona Kuning (Waspada)'
    else:
        kategori_map[cluster_label] = 'Zona Hijau (Aman)'
loc['Kategori'] = loc['Cluster'].map(kategori_map)

# -------------------------------
# Gabungkan data ke GeoDataFrame shapefile
# -------------------------------
df_final = df_sby.set_index('ADM3_EN').join(
    loc.set_index('Kecamatan')[['Jumlah Kecelakaan', 'Cluster', 'Kategori']],
    how='left'
).reset_index()

# Drop kecamatan tanpa data kecelakaan
df_final = df_final.dropna(subset=['Jumlah Kecelakaan'])

# Hitung centroid geometry untuk koordinat
df_final['Longitude'] = df_final.geometry.centroid.x
df_final['Latitude'] = df_final.geometry.centroid.y

# -------------------------------
# Sidebar filter kecamatan
# -------------------------------
st.sidebar.markdown('### Filter Kecamatan')
selected_kecamatan = st.sidebar.multiselect(
    "✅ Pilih atau Cari Kecamatan:",
    options=sorted(df_final['ADM3_EN'].unique()),
    default=sorted(df_final['ADM3_EN'].unique()),
    placeholder="Ketik nama kecamatan..."
)
filtered_df = df_final[df_final['ADM3_EN'].isin(selected_kecamatan)]

# -------------------------------
# Hitung total keseluruhan kecelakaan dan kecamatan terpilih
# -------------------------------
total_kejadian = filtered_df['Jumlah Kecelakaan'].sum()
total_kecamatan = filtered_df['ADM3_EN'].nunique()

# -------------------------------
# total kejadian dan total kecamatan di dua kotak putih terpisah
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
        <div class="metric-box-white">
            <h3>Total Kejadian</h3>
            <p style="font-size: 32px;">{int(total_kejadian)}</p>
            <p>kejadian kecelakaan</p>
        </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
        <div class="metric-box-white">
            <h3>Total Kecamatan</h3>
            <p style="font-size: 32px;">{total_kecamatan}</p>
            <p>kecamatan terpilih</p>
        </div>
    """, unsafe_allow_html=True)

# -------------------------------
# Ringkasan zona tetap dengan warna blok
color_map = {
    'Zona Merah (Rawan)': '#e74c3c',
    'Zona Kuning (Waspada)': '#f1c40f',
    'Zona Hijau (Aman)': '#2ecc71'
}

st.markdown('<div class="section-title">📊 Ringkasan Zona Kecelakaan per Kecamatan</div>', unsafe_allow_html=True)
for zona in ['Zona Merah (Rawan)', 'Zona Kuning (Waspada)', 'Zona Hijau (Aman)']:
    subset = filtered_df[filtered_df['Kategori'] == zona]
    total = subset['Jumlah Kecelakaan'].sum()
    count = len(subset)
    warna = color_map[zona]
    st.markdown(f"""
        <div style="background-color: {warna}; padding: 15px; border-radius: 10px; color: white; margin-bottom: 10px;">
            <h4>{zona}</h4>
            <p>Total Kecelakaan: <b>{int(total)}</b> kejadian</p>
            <p>Jumlah Kecamatan: <b>{count}</b></p>
        </div>
    """, unsafe_allow_html=True)

# -------------------------------
# Tabel rincian dengan Longitude dan Latitude
st.markdown('<div class="section-title">📌 Rincian Jumlah Kecelakaan dan Koordinat Kecamatan</div>', unsafe_allow_html=True)
st.dataframe(
    filtered_df[['ADM3_EN', 'Jumlah Kecelakaan', 'Cluster', 'Kategori', 'Longitude', 'Latitude']]
    .rename(columns={'ADM3_EN': 'Kecamatan'})
)

# -------------------------------
# Peta Interaktif dengan warna gradien berdasarkan jumlah kecelakaan
# -------------------------------
st.markdown('<div class="section-title">🗺️ Peta Interaktif Jumlah Kecelakaan </div>', unsafe_allow_html=True)

try:
    m = filtered_df.explore(
        column='Jumlah Kecelakaan',
        cmap='RdYlGn_r',            # Gradien merah-ke-hijau reversed (merah = tinggi)
        legend=True,
        tooltip=['ADM3_EN', 'Jumlah Kecelakaan', 'Kategori', 'Longitude', 'Latitude'],
        edgecolor='black',
        linewidth=1.5,
        name='Jumlah Kecelakaan'
    )
    st_folium(m, width=700, height=600)
except Exception as e:
    st.error(f"Terjadi kesalahan saat menampilkan peta: {e}")
