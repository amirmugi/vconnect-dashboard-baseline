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

DROPBOX_DEFAULT_URL = "https://www.dropbox.com/scl/fi/j1cak1bp9zgpm7besmlmp/Volvo-Connect-Weekly-Monitor.xlsx?rlkey=lcuvedyrhykl95nh4m21ok2ir&e=1&dl=1"

# 2. Fungsi Load Data
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
        else:
            # Data Cleaning
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

            # Display Metrics (Native Border Container untuk Dark/Light Mode Fix)
            st.subheader("📊 Key Performance Indicators (KPI)")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                with st.container(border=True):
                    st.metric(label="🟢 Total Unit Aktif", value=f"{total_active_units:,} Unit")

            with col2:
                with st.container(border=True):
                    st.metric(label="🏢 Customer Aktif", value=f"{total_active_customers} Customer")

            with col3:
                with st.container(border=True):
                    st.metric(label="🚛 Unit Terfilter", value=f"{len(filtered_df):,} Unit")

            with col4:
                with st.container(border=True):
                    sites_count = filtered_df['Site'].nunique() if 'Site' in filtered_df.columns else 0
                    st.metric(label="📍 Total Site Operational", value=f"{sites_count} Site")

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
                type_counts = filtered_df['Kategori_Remark'].value_counts().reset_index()
                type_counts.columns = ['Tipe', 'Total']
                type_counts = type_counts[type_counts['Tipe'].isin(['Retail', 'Goodwill'])]

                fig_status = px.pie(
                    type_counts,
                    names='Tipe',
                    values='Total',
                    hole=0.4,
                    color='Tipe',
                    color_discrete_map={'Retail': '#0068c9', 'Goodwill': '#ff2b2b'}
                )
                fig_status.update_traces(textposition='inside', textinfo='percent+label+value')
                st.plotly_chart(fig_status, use_container_width=True)

            st.markdown("---")

            # 7. Pivot Summary Table (Jumlah Unit per Customer & Site)
            st.subheader("📌 Ringkasan Unit Customer Aktif")
            
            if 'Site' in filtered_df.columns:
                # Membuat Pivot Table berdasarkan Customer & Site
                pivot_df = pd.pivot_table(
                    filtered_df,
                    index=['Customer', 'Site'],
                    columns='Kategori_Remark',
                    values='Chassis ID' if 'Chassis ID' in filtered_df.columns else 'Status',
                    aggfunc='count',
                    fill_value=0
                ).reset_index()

                # Memastikan kolom Goodwill & Retail tersedia
                for col in ['Goodwill', 'Retail']:
                    if col not in pivot_df.columns:
                        pivot_df[col] = 0

                pivot_df['Total Unit'] = pivot_df['Goodwill'] + pivot_df['Retail']
                
                # Mengganti nilai 0 dengan spasi kosong agar sesuai contoh tampilan Excel
                pivot_display = pivot_df[['Customer', 'Site', 'Goodwill', 'Retail', 'Total Unit']].copy()
                
                st.dataframe(
                    pivot_display,
                    use_container_width=True,
                    hide_index=True
                )

            # 8. Data Table Detail Section
            with st.expander("🔍 Lihat Detail Data Mentah"):
                cols_to_show = [c for c in ['Customer', 'Site', 'Chassis ID', 'Unit Code', 'Truck Type', 'Status', 'Remark'] if c in filtered_df.columns]
                st.dataframe(filtered_df[cols_to_show], use_container_width=True, hide_index=True)
