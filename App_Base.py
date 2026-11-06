import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# 1. Konfigurasi Halaman Dashboard
st.set_page_config(
    page_title="Volvo Connect Dashboard",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

DROPBOX_DEFAULT_URL = "https://www.dropbox.com/scl/fi/j1cak1bp9zgpm7besmlmp/Volvo-Connect-Weekly-Monitor.xlsx?rlkey=lcuvedyrhykl95nh4m21ok2ir&e=1&dl=1"

# 2. Fungsi Load Data Semua Sheet dari Dropbox
@st.cache_data(ttl=300)
def load_all_sheets_from_url(url: str):
    if "dropbox.com" in url and "dl=0" in url:
        url = url.replace("dl=0", "dl=1")
    elif "dropbox.com" in url and "dl=1" not in url:
        url += "&dl=1" if "?" in url else "?dl=1"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=25)
        if response.status_code == 200:
            file_bytes = io.BytesIO(response.content)
            xls = pd.ExcelFile(file_bytes)
            
            # Load sheet utama 'List Volvo Connect'
            df_list = pd.read_excel(xls, sheet_name='List Volvo Connect', header=0)
            df_list.columns = df_list.columns.astype(str).str.strip()
            
            # Deteksi sheet 'Growth Week'
            growth_sheet_name = None
            for s in xls.sheet_names:
                if 'growth' in s.lower():
                    growth_sheet_name = s
                    break
            
            df_growth = None
            if growth_sheet_name:
                df_growth = pd.read_excel(xls, sheet_name=growth_sheet_name)
                
            return df_list, df_growth, growth_sheet_name
        else:
            st.error(f"Gagal mengunduh file dari Dropbox. Status Code: {response.status_code}")
            return None, None, None
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memuat data: {e}")
        return None, None, None

# 3. Sidebar Configuration
st.sidebar.title("⚙️ Sumber Data Cloud")
excel_url = st.sidebar.text_input("URL Direct Link Dropbox:", value=DROPBOX_DEFAULT_URL)
st.sidebar.markdown("---")

# 4. Main App Layout
st.title("🚛 Volvo Connect - Weekly Monitor Dashboard")
st.markdown("Dashboard monitoring real-time unit aktif, customer aktif, rincian fleet, dan tren pertumbuhan (Growth).")

if excel_url:
    with st.spinner("Mengunduh data terbaru dari Dropbox..."):
        df_raw, df_growth_raw, growth_sheet_name = load_all_sheets_from_url(excel_url)

    if df_raw is not None:
        required_cols = ['Customer', 'Status']
        missing_cols = [col for col in required_cols if col not in df_raw.columns]

        if missing_cols:
            st.error(f"⚠️ Kolom berikut tidak ditemukan pada Excel: **{', '.join(missing_cols)}**.")
        else:
            # Data Cleaning & Preprocessing
            df_clean = df_raw.dropna(subset=['Customer', 'Status']).copy()

            # Pengelompokan Kategori Remark (Goodwill vs Retail)
            if 'Remark' in df_clean.columns:
                def categorize_remark(val):
                    val_str = str(val).strip().upper()
                    if 'RETAIL' in val_str:
                        return 'Retail'
                    elif 'GOODWILL' in val_str:
                        return 'Goodwill'
                    else:
                        return 'Lainnya'

                df_clean['Kategori_Remark'] = df_clean['Remark'].apply(categorize_remark)
            else:
                df_clean['Kategori_Remark'] = 'Lainnya'

            # Normalisasi Kolom Remarks+
            if 'Remarks+' in df_clean.columns:
                df_clean['Remarks+'] = df_clean['Remarks+'].fillna('Lainnya').astype(str).str.strip()
            else:
                df_clean['Remarks+'] = 'Lainnya'

            # Konversi Kolom Left days ke Numerik
            if 'Left days' in df_clean.columns:
                df_clean['Left_days_num'] = pd.to_numeric(df_clean['Left days'], errors='coerce')
            else:
                df_clean['Left_days_num'] = None

            # Sidebar Filters
            st.sidebar.subheader("🔍 Filter Data")
            
            # Filter Status
            status_list = sorted(df_clean['Status'].astype(str).unique().tolist())
            selected_status = st.sidebar.multiselect(
                "Filter Status Unit:", 
                status_list, 
                default=["Active"] if "Active" in status_list else status_list
            )

            # Filter Customer
            customer_list = sorted(df_clean['Customer'].astype(str).unique().tolist())
            selected_customers = st.sidebar.multiselect("Filter Customer:", customer_list, default=customer_list)

            # Filter Remarks+ (Aktivasi)
            all_remarks = sorted(df_clean['Remarks+'].unique().tolist())
            filtered_remarks_options = [r for r in all_remarks if r != 'Carry Over Subs from 2025 - INACTIVE']
            
            selected_remarks = st.sidebar.multiselect(
                "Filter Kategori Aktivasi (Remarks+):",
                filtered_remarks_options,
                default=filtered_remarks_options
            )

            # Filtered DataFrame
            filtered_df = df_clean[
                (df_clean['Status'].astype(str).isin(selected_status)) &
                (df_clean['Customer'].astype(str).isin(selected_customers)) &
                (df_clean['Remarks+
