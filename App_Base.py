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

            # Filter Remarks+
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
                (df_clean['Remarks+'].isin(selected_remarks))
            ]

            # 5. Key Metrics Calculation
            df_active_overall = df_clean[df_clean['Status'] == 'Active']
            total_active_units = len(df_active_overall)
            total_active_customers = df_active_overall['Customer'].nunique()

            # -----------------------------------------------------------------
            # BARIS 1 KPI (Proporsional 3 Kolom Atas)
            # -----------------------------------------------------------------
            st.subheader("📊 Key Performance Indicators (KPI)")
            top_col1, top_col2, top_col3 = st.columns(3)

            with top_col1:
                with st.container(border=True):
                    st.metric(
                        label="🟢 Total Unit Aktif", 
                        value=f"{len(filtered_df):,} Unit",
                        help="Jumlah unit terfilter saat ini"
                    )

            with top_col2:
                with st.container(border=True):
                    cust_filtered_count = filtered_df['Customer'].nunique()
                    st.metric(label="🏢 Customer Aktif", value=f"{cust_filtered_count} Customer")

            with top_col3:
                with st.container(border=True):
                    sites_count = filtered_df['Site'].nunique() if 'Site' in filtered_df.columns else 0
                    st.metric(label="📍 Total Site Operational", value=f"{sites_count} Site")

            # -----------------------------------------------------------------
            # BARIS 2 KPI (Proporsional 3 Kolom Bawah)
            # -----------------------------------------------------------------
            c_carry_active = (filtered_df['Remarks+'] == 'Carry Over Subs from 2025 - Active').sum()
            c_new_act = (filtered_df['Remarks+'] == 'New Activation, of 2026').sum()
            c_renewal = (filtered_df['Remarks+'] == 'Renewal Subs, of 2026').sum()

            bot_col1, bot_col2, bot_col3 = st.columns(3)

            with bot_col1:
                with st.container(border=True):
                    st.metric(label="🟢 Carry Over Subs 2025 (Active)", value=f"{c_carry_active} Unit")

            with bot_col2:
                with st.container(border=True):
                    st.metric(label="⚡ New Activation (2026)", value=f"{c_new_act} Unit")

            with bot_col3:
                with st.container(border=True):
                    st.metric(label="🔄 Renewal Subs (2026)", value=f"{c_renewal} Unit")

            # -----------------------------------------------------------------
            # PERINGATAN EXPIRING UNITS (< 90 HARI)
            # -----------------------------------------------------------------
            if 'Left_days_num' in filtered_df.columns:
                # Mengambil unit yang sisa harinya <= 90 dan masih >= 0
                expiring_df = filtered_df[(filtered_df['Left_days_num'] <= 90) & (filtered_df['Left_days_num'] >= 0)]
                expiring_units = len(expiring_df)
                expiring_cust = expiring_df['Customer'].nunique()

                st.markdown("##### ⚠️ Warning: Unit Masa Kontrak Segera Habis (< 90 Hari)")
                exp_col1, exp_col2 = st.columns(2)

                with exp_col1:
                    with st.container(border=True):
                        st.metric(
                            label="⏳ Unit Expiring (< 90 Hari)", 
                            value=f"{expiring_units} Unit",
                            help="Jumlah unit terfilter dengan Left days <= 90 hari"
                        )

                with exp_col2:
                    with st.container(border=True):
                        st.metric(
                            label="🏢 Customer Terdampak (< 90 Hari)", 
                            value=f"{expiring_cust} Customer"
                        )

                if expiring_units > 0:
                    with st.expander("📌 Lihat Daftar Unit Expiring (< 90 Hari)"):
                        exp_show_cols = [c for c in ['Customer', 'Site', 'Chassis ID', 'Unit Code', 'Truck Type', 'Left days', 'Kategori_Remark'] if c in expiring_df.columns]
                        st.dataframe(
                            expiring_df[exp_show_cols].sort_values(by='Left days'),
                            use_container_width=True,
                            hide_index=True
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
            st.subheader("📌 Ringkasan Unit Customer berdasarkan Site (Pivot)")
            
            if 'Site' in filtered_df.columns:
                pivot_df = pd.pivot_table(
                    filtered_df,
                    index=['Customer', 'Site'],
                    columns='Kategori_Remark',
                    values='Chassis ID' if 'Chassis ID' in filtered_df.columns else 'Status',
                    aggfunc='count',
                    fill_value=0
                ).reset_index()

                for col in ['Goodwill', 'Retail']:
                    if col not in pivot_df.columns:
                        pivot_df[col] = 0

                pivot_df['Total Unit'] = pivot_df['Goodwill'] + pivot_df['Retail']
                
                pivot_display = pivot_df[['Customer', 'Site', 'Goodwill', 'Retail', 'Total Unit']].copy()
                
                st.dataframe(
                    pivot_display,
                    use_container_width=True,
                    hide_index=True
                )

            # 8. Data Table Detail Section
            with st.expander("🔍 Lihat Detail Data Mentah"):
                cols_to_show = [c for c in ['Customer', 'Site', 'Chassis ID', 'Unit Code', 'Truck Type', 'Status', 'Left days', 'Remark', 'Remarks+'] if c in filtered_df.columns]
                st.dataframe(filtered_df[cols_to_show], use_container_width=True, hide_index=True)
