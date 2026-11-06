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
            
            # Load sheet utama
            df_list = pd.read_excel(xls, sheet_name='List Volvo Connect', header=0)
            df_list.columns = df_list.columns.astype(str).str.strip()
            
            # Deteksi otomatis sheet "Growth Week"
            growth_sheet_name = None
            for s in xls.sheet_names:
                # Mengakomodasi nama "Growth Week", "Growth Week 33 '26", dll.
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
