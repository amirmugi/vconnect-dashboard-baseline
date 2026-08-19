import pandas as pd
import streamlit as st
import plotly.express as px
import requests
import io

# 1. Konfigurasi Halaman Dashboard
st.set_page_config(
    page_title="Volvo Connect Dashboard",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling CSS
st.markdown("""
    <style>
    .stMetric {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 1px 1px 5px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

DROPBOX_DEFAULT_URL = "https://www.dropbox.com/scl/fi/j1cak1bp9zgpm7besmlmp/Volvo-Connect-Weekly-Monitor.xlsx?rlkey=lcuvedyrhykl95nh4m21ok2ir&e=1&dl=1"

# 2. Fungsi Load Data dari URL
@st.cache_data(ttl=300)
def load_data_from_url(url: str):
    if "dropbox.com" in url and "dl=0" in url:
        url = url.replace("dl=0", "dl=1")
    elif "dropbox.com" in url and "dl=1" not in url:
        url += "&dl=1" if "?" in url else "?dl=1"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            file_bytes = io.BytesIO(response.content)
            df = pd.read_excel(file_bytes, sheet_name='List Volvo Connect', header=0)
            df.columns = df.columns.astype(str).str.strip()
            return df
        else:
            st.error(f"Gagal mengunduh file dari Dropbox. Status Code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memuat data: {e}")
        return None

# 3. Sidebar Configuration
st.sidebar.title("⚙️ Sumber Data Cloud")
excel_url = st.sidebar.text_input("URL Direct Link Dropbox:", value=DROPBOX_DEFAULT_URL)
st.sidebar.markdown("---")

# 4. Main App Layout
st.title("🚛 Volvo Connect - Weekly Monitor Dashboard")
st.markdown("Dashboard monitoring real-time unit aktif, customer aktif, dan rincian fleet.")

if excel_url:
    with st.spinner("Mengunduh data terbaru dari Dropbox..."):
        df_raw = load_data_from_url(excel_url)

    if df_raw is not None:
        required_cols = ['Customer', 'Status']
        missing_cols = [col for col in required_cols if col not in df_raw.columns]

        if missing_cols:
            st.error(f"⚠️ Kolom berikut tidak ditemukan pada Excel: **{', '.join(missing_cols)}**.")
            st.write("Kolom yang terdeteksi di Excel:", df_raw.columns.tolist())
        else:
            # Cleaning Data
            df_clean = df_raw.dropna(subset=['Customer', 'Status']).copy()

            # Standarisasi Kolom Remark untuk Kategori Retail vs Goodwill
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

            # Sidebar Filters
            st.sidebar.subheader("🔍 Filter Data")
            
            status_list = sorted(df_clean['Status'].astype(str).unique().tolist())
            selected_status = st.sidebar.multiselect(
                "Filter Status Unit:", 
                status_list, 
                default=["Active"] if "Active" in status_list else status_list
            )

            customer_list = sorted(df_clean['Customer'].astype(str).unique().tolist())
            selected_customers = st.sidebar.multiselect("Filter Customer:", customer_list, default=customer_list)

            # Filtered DataFrame
            filtered_df = df_clean[
                (df_clean['Status'].astype(str).isin(selected_status)) &
                (df_clean['Customer'].astype(str).isin(selected_customers))
            ]

            # 5. Key Metrics Calculation
            df_active_overall = df_clean[df_clean['Status'] == 'Active']
            total_active_units = len(df_active_overall)
            total_active_customers = df_active_overall['Customer'].nunique()

            # Display Metrics
            st.subheader("📊 Key Performance Indicators (KPI)")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    label="🟢 Total Unit Aktif",
                    value=f"{total_active_units:,} Unit",
                    help="Total unit dengan status Active di database"
                )

            with col2:
                st.metric(
                    label="🏢 Total Customer Aktif",
                    value=f"{total_active_customers} Customer",
                    help="Total customer unik yang memiliki unit Active"
                )

            with col3:
                st.metric(
                    label="🚛 Unit Terfilter",
                    value=f"{len(filtered_df):,} Unit"
                )

            with col4:
                sites_count = filtered_df['Site'].nunique() if 'Site' in filtered_df.columns else 0
                st.metric(
                    label="📍 Total Site Operational",
                    value=f"{sites_count} Site"
                )

            st.markdown("---")

            # 6. Visualizations Section
            col_left, col_right = st.columns(2)

            with col_left:
                st.subheader("📈 Top Customer Berdasarkan Unit")
                cust_counts = filtered_df['Customer'].value_counts().head(10).reset_index()
                cust_counts.columns = ['Customer', 'Jumlah Unit']
                
                fig_cust = px.bar(
                    cust_counts,
                    x='Jumlah Unit',
                    y='Customer',
                    orientation='h',
                    color='Jumlah Unit',
                    color_continuous_scale='Blues',
                    text='Jumlah Unit'
                )
                fig_cust.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False)
                st.plotly_chart(fig_cust, use_container_width=True)

            with col_right:
                st.subheader("🧩 Komposisi Tipe (Retail vs Goodwill)")
                # Mengambil komposisi berdasarkan kategori Retail dan Goodwill
                type_counts = filtered_df['Kategori_Remark'].value_counts().reset_index()
                type_counts.columns = ['Tipe', 'Total']

                # Filter khusus agar berfokus pada Retail dan Goodwill
                type_counts = type_counts[type_counts['Tipe'].isin(['Retail', 'Goodwill'])]

                color_map = {'Retail': '#0068c9', 'Goodwill': '#ff2b2b'}

                fig_status = px.pie(
                    type_counts,
                    names='Tipe',
                    values='Total',
                    hole=0.4,
                    color='Tipe',
                    color_discrete_map=color_map
                )
                fig_status.update_traces(textposition='inside', textinfo='percent+label+value')
                st.plotly_chart(fig_status, use_container_width=True)

            # 7. Data Table Section
            st.subheader("📋 Detail Data Unit")
            cols_to_show = [c for c in ['Customer', 'Site', 'Chassis ID', 'Unit Code', 'Truck Type', 'Status', 'Remark'] if c in filtered_df.columns]
            st.dataframe(
                filtered_df[cols_to_show],
                use_container_width=True,
                hide_index=True
            )
