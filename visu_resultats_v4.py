# ---------------------------
# IMPORTS
# ---------------------------
import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
import plotly.graph_objects as go
import statsmodels.api as sm
import locale
from PIL import Image
import re
import unicodedata

# ---------------------------
# LOCALE FR
# ---------------------------
try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'fr_FR')
    except locale.Error:
        pass

# ---------------------------
# CONFIG STREAMLIT
# ---------------------------
st.set_page_config(layout="wide")

# ============================================================
# FONCTIONS EXPORT HTML
# ============================================================

def generate_summary_html(summary_df):
    """Export tableau récapitulatif seul (bouton dédié)."""
    html_table = summary_df.to_html(index=False, border=0, classes="styled-table")
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Tableau récapitulatif</title>
<style>
body {{ font-family: Arial; margin: 40px; background-color: #ffffff; }}
h1 {{ text-align: center; margin-bottom: 40px; }}
table {{ margin: auto; width: 90%; border-collapse: collapse; font-size: 14px; }}
th, td {{ padding: 8px; border-bottom: 1px solid #ddd; text-align: center; }}
th {{ background-color: #f2f2f2; }}
tr:nth-child(even) {{ background-color: #fafafa; }}
</style>
</head>
<body>
<h1>Tableau récapitulatif des athlètes</h1>
{html_table}
</body>
</html>"""


def df_changes_to_colored_html(df):
    """Tableau changements de charge avec coloration vert/rouge."""
    if df is None or df.empty:
        return "<p>—</p>"
    diff_cols = ["Arraché 1→2", "Arraché 2→3", "Épaulé-jeté 1→2", "Épaulé-jeté 2→3"]
    rows_html = ""
    for _, row in df.iterrows():
        cells = ""
        for col in df.columns:
            val = row[col]
            style = ""
            if col in diff_cols and isinstance(val, str):
                if "🔴" in val:
                    style = "color:red; font-weight:bold;"
                elif "🟢" in val:
                    style = "color:green; font-weight:bold;"
            if col == "Date" and hasattr(val, "strftime"):
                val = val.strftime("%Y-%m-%d")
            cells += f'<td style="padding:6px 10px; border-bottom:1px solid #ddd; text-align:center; {style}">{val}</td>'
        rows_html += f"<tr>{cells}</tr>\n"
    headers = "".join(
        f'<th style="padding:6px 10px; background:#f2f2f2; border-bottom:2px solid #ccc;">{c}</th>'
        for c in df.columns
    )
    return f"""<table style="width:100%; border-collapse:collapse; font-size:13px;">
<thead><tr>{headers}</tr></thead>
<tbody>{rows_html}</tbody>
</table>"""


def summary_to_html(df):
    """Tableau récapitulatif multi-athlètes en HTML."""
    if df is None or df.empty:
        return "<p>—</p>"
    fmt_cols = [
        "Meilleur total", "Meilleur arraché", "Meilleur épaulé-jeté",
        "Meilleure barre départ arraché", "Meilleure barre départ épaulé-jeté",
        "P.C. au meilleur total"
        # "Date au meilleur total" et "Compétition au meilleur total" sont des strings, pas besoin de format float
    ]
    rows_html = ""
    for i, (_, row) in enumerate(df.iterrows()):
        bg = "#fafafa" if i % 2 == 0 else "#ffffff"
        cells = ""
        for col in df.columns:
            val = row[col]
            if col in fmt_cols and pd.notna(val):
                try:
                    val = f"{float(val):.1f}"
                except Exception:
                    pass
            cells += f'<td style="padding:6px 10px; border-bottom:1px solid #ddd; text-align:center;">{val}</td>'
        rows_html += f'<tr style="background:{bg};">{cells}</tr>\n'
    headers = "".join(
        f'<th style="padding:6px 10px; background:#f2f2f2; border-bottom:2px solid #ccc;">{c}</th>'
        for c in df.columns
    )
    return f"""<table style="width:100%; border-collapse:collapse; font-size:13px;">
<thead><tr>{headers}</tr></thead>
<tbody>{rows_html}</tbody>
</table>"""


def bulles_to_html(df):
    """Tableau bulles (0/3) en HTML."""
    if df is None or df.empty:
        return "<p>Aucune bulle détectée.</p>"
    rows_html = ""
    for i, (_, row) in enumerate(df.iterrows()):
        bg = "#fafafa" if i % 2 == 0 else "#ffffff"
        cells = "".join(
            f'<td style="padding:6px 10px; border-bottom:1px solid #ddd; text-align:center;">{row[c]}</td>'
            for c in df.columns
        )
        rows_html += f'<tr style="background:{bg};">{cells}</tr>\n'
    headers = "".join(
        f'<th style="padding:6px 10px; background:#f2f2f2; border-bottom:2px solid #ccc;">{c}</th>'
        for c in df.columns
    )
    return f"""<table style="width:100%; border-collapse:collapse; font-size:13px;">
<thead><tr>{headers}</tr></thead>
<tbody>{rows_html}</tbody>
</table>"""


def athlete_info_to_html(athlete_info, taux_ar_m, taux_epj_m, taux_total_m, selected_athlete):
    """Bloc profil athlète HTML (identique aux 4 colonnes de l'appli)."""
    return f"""
<h2 style="text-align:center;">{selected_athlete}</h2>
<div style="display:flex; justify-content:center; gap:60px; flex-wrap:wrap; font-size:14px;">
  <div>
    <b>Profil</b><br>
    Sexe : {athlete_info.get('Sexe','N/A')}<br>
    Âge : {athlete_info.get('Age','N/A')}<br>
    Catégorie de poids : {athlete_info.get('Categorie_poids','N/A')}<br>
    Catégorie d'âge : {athlete_info.get('Categorie_age','N/A')}
  </div>
  <div>
    <b>Meilleures performances</b><br>
    Meilleur arraché : {athlete_info.get('_max_snatch', 'N/A')} kg<br>
    Meilleur épaulé-jeté : {athlete_info.get('_max_clean_jerk', 'N/A')} kg<br>
    Meilleur total : {athlete_info.get('_max_total', 'N/A')} kg
  </div>
  <div>
    <b>Taux de réussite (moyennes)</b><br>
    Arraché : {taux_ar_m:.1f}%<br>
    Épaulé-jeté : {taux_epj_m:.1f}%<br>
    Total : {taux_total_m:.1f}%
  </div>
</div>"""


def generate_full_html_report(
    athlete, info_html, fig_perf_html, fig_taux_html,
    changes_summary_html, changes_table_html,
    top5_html, attempts_html, bulles_html, summary_html
):
    """Rapport HTML global complet."""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Rapport – {athlete}</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
body  {{ font-family: Arial, sans-serif; margin: 40px; background: #ffffff; color: #222; }}
h1    {{ text-align: center; margin-bottom: 40px; }}
h2    {{ margin-top: 50px; text-align: center; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
.section {{ margin-bottom: 70px; }}
table {{ margin: auto; width: 95%; border-collapse: collapse; font-size: 13px; }}
th, td {{ padding: 7px 10px; border-bottom: 1px solid #ddd; text-align: center; }}
th    {{ background-color: #f2f2f2; }}
tr:nth-child(even) {{ background-color: #fafafa; }}
</style>
</head>
<body>
<h1>Rapport de performance – {athlete}</h1>

<div class="section">{info_html}</div>

<div class="section">
<h2>Évolution des performances</h2>
{fig_perf_html}
</div>

<div class="section">
<h2>Changements de charge par essai (2 dernières années)</h2>
{changes_summary_html}
<br>
{changes_table_html}
</div>

<div class="section">
<h2>Évolution des taux de réussite</h2>
{fig_taux_html}
</div>

<div class="section">
<h2>Taux de réussite pour les 5 meilleures charges</h2>
{top5_html}
</div>

<div class="section">
<h2>Taux de réussite par essai (2 dernières années)</h2>
{attempts_html}
</div>

<div class="section">
<h2>Analyse des bulles (0/3) par charge</h2>
{bulles_html}
</div>

<div class="section">
<h2>Comparaison entre athlètes, par plateau</h2>
{summary_html}
</div>

</body>
</html>"""


# ============================================================
# SECTION 1 — EXTRACTION & TRAITEMENT
# ============================================================

@st.cache_data
def load_data(path):
    return pd.read_excel(path, engine="openpyxl")

DEFAULT_FILE = "data/all_results_clean_harmonized_fin.xlsx"
uploaded_file = st.file_uploader(
    "Importer un fichier Excel (optionnel)",
    type=["xlsx"]
)

file_to_load = uploaded_file if uploaded_file else DEFAULT_FILE

df = load_data(file_to_load)

# ---------------------------
# CLEAN SOURCE
# ---------------------------
if 'source' not in df.columns:
    df['source'] = np.nan

df["source"] = df["source"].astype(str).str.strip().str.upper()
df["source"] = df["source"].apply(lambda x: unicodedata.normalize('NFKD', x).encode('ascii', 'ignore').decode('utf-8').strip())

# ---------------------------
# Colonnes essais
# ---------------------------
sn_cols = ["1", "2", "3"]
cj_cols = ["1.1", "2.1", "3.1"]

for col in sn_cols + cj_cols:
    if col not in df.columns:
        df[col] = np.nan
    df[f"{col}_raw"] = df[col]

def extract_success(x):
    try:
        if pd.isna(x):
            return np.nan
        s = str(x).strip()
        if s.startswith("-"):
            return np.nan
        return float(s.replace(",", "."))
    except:
        return np.nan

for col in sn_cols + cj_cols:
    df[col] = df[col].apply(extract_success)

# ---------------------------
# Poids de corps
# ---------------------------
def clean_pc(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return np.nan

pc_cols = [c for c in df.columns if c.strip().lower() in ["p.c.", "p. c.", "pc"]]
df["P.C."] = df[pc_cols[0]].apply(clean_pc) if pc_cols else np.nan

# ---------------------------
# Nom Athlète + normalisation
# ---------------------------
names = df["Nom"].astype(str).str.split(" ", n=1, expand=True)
df["Prenom"] = names[0].str.capitalize()
df["Nom_clean"] = names[1].fillna("").str.upper()
df["Athlete"] = (df["Prenom"] + " " + df["Nom_clean"]).str.strip()

def normalize_string(s):
    if pd.isna(s):
        return ""
    s = str(s)
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ascii', 'ignore').decode('utf-8')
    return s.upper().strip()

df["Athlete_norm"] = df["Athlete"].apply(normalize_string)

# ---------------------------
# Détection colonnes flexible
# ---------------------------
def get_col(possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None

col_date_ffhm = get_col(["Date_compétition", "Date compétition", "Date"])
col_event_iwf = get_col(["event_date"])
col_cat_ffhm = get_col(["Catégorie"])
col_comp_ffhm = get_col(["Nom_compétition", "Nom compétition", "Catégorie (H5)", "Competition"])

# ---------------------------
# PARSE DATE FFHM CUSTOM
# ---------------------------
month_map = {
    "jan": 1, "fév": 2, "fev": 2, "mar": 3, "avr": 4, "apr":4,
    "mai": 5, "jun": 6, "jui":7, "jul":7, "aoû": 8, "aou":8, "aug":8,
    "sep": 9, "sept":9, "oct": 10, "nov": 11, "déc":12, "dec":12
}

def parse_ffhm_date(s):
    try:
        if pd.isna(s): return pd.NaT
        s = str(s)
        s = s.rsplit("-", 1)[0].strip()
        s = re.sub(r'^\d{4}/\d{4}', '', s).strip()
        match = re.search(r'(\d{1,2})\s*([A-Za-zéûê]{3})\s*(\d{4})', s)
        if match:
            day, month_str, year = match.groups()
            month_num = month_map.get(month_str.lower()[:3])
            if month_num:
                return pd.Timestamp(year=int(year), month=month_num, day=int(day))
        return pd.NaT
    except:
        return pd.NaT

mask_ffhm = df["source"] == "FFHM"
mask_iwf = df["source"] == "IWF"
mask_other = ~mask_ffhm & ~mask_iwf

df.loc[mask_ffhm, "Date_extrait"] = df.loc[mask_ffhm, col_date_ffhm].apply(parse_ffhm_date)
df.loc[mask_iwf, "Date_extrait"] = pd.to_datetime(df.loc[mask_iwf, col_event_iwf], errors='coerce')
df.loc[mask_other, "Date_extrait"] = pd.to_datetime(df.loc[mask_other, col_date_ffhm], errors='coerce')

df = df.dropna(subset=["Date_extrait"]).copy()
df["Year"] = df["Date_extrait"].dt.year

# ---------------------------
# Âge
# ---------------------------
df["AN"] = pd.to_numeric(df.get("AN", np.nan), errors="coerce")
df["Age"] = df["Year"] - df["AN"]

# ---------------------------
# Sexe + catégories
# ---------------------------
def sexe_ffhm(cat): return "Femme" if "F" in str(cat) else "Homme"
def sexe_iwf(wc): return "Femme" if "women" in str(wc).lower() else "Homme"
def cat_poids_ffhm(cat): return str(cat).split()[-1] if pd.notna(cat) else np.nan
def cat_poids_iwf(wc): return str(wc).split()[0] if pd.notna(wc) else np.nan
def cat_age_ffhm(cat): return str(cat).split()[0] if pd.notna(cat) else np.nan

mask_ffhm_like = df["source"].isin(["FFHM", "ENTREE MANUELLE"])

df["Sexe"] = np.where(
    mask_ffhm_like,
    df[col_cat_ffhm].apply(sexe_ffhm) if col_cat_ffhm else "N/A",
    df.get("weight_class", pd.Series(index=df.index)).apply(sexe_iwf)
)

df["Catégorie de poids"] = np.where(
    mask_ffhm_like,
    df[col_cat_ffhm].apply(cat_poids_ffhm) if col_cat_ffhm else np.nan,
    df.get("weight_class", pd.Series(index=df.index)).apply(cat_poids_iwf)
)

df["Catégorie d'âge"] = np.where(
    mask_ffhm_like,
    df[col_cat_ffhm].apply(cat_age_ffhm) if col_cat_ffhm else np.nan,
    "INTL"
)

# ---------------------------
# Performances
# ---------------------------
df["Snatch"] = df[sn_cols].max(axis=1, numeric_only=True)
df["Clean_Jerk"] = df[cj_cols].max(axis=1, numeric_only=True)
df["Total_calc"] = df["Snatch"] + df["Clean_Jerk"]
df["Total"] = np.where(df.get("TOTAL", pd.Series(index=df.index)).notna(), df["TOTAL"], df["Total_calc"])
df["Total"] = pd.to_numeric(df["Total"], errors="coerce")

# ---------------------------
# Competition
# ---------------------------
df["Competition"] = np.where(
    df["source"] == "IWF",
    df.get("event_name", pd.Series(index=df.index)).astype(str),
    np.where(
        df["source"] == "FFHM",
        df[get_col(["Catégorie (H5)", "Nom_compétition", "Nom compétition", "Competition"])].astype(str) if get_col(["Catégorie (H5)", "Nom_compétition", "Nom compétition", "Competition"]) else "Compétition FFHM",
        df[get_col(["Nom_compétition", "Nom compétition", "Competition"])].astype(str) if get_col(["Nom_compétition", "Nom compétition", "Competition"]) else "Compétition"
    )
)
df["Competition"] = df["Competition"].astype(str).str.split("\n").str[0].str.strip()

# ---------------------------
# Rename pour v2
# ---------------------------
df_traite = df.rename(columns={
    "Catégorie de poids": "Categorie_poids",
    "Catégorie d'âge": "Categorie_age"
})

df_ready = df_traite.copy()

# ============================================================
# FILTRE GLOBAL PAR SOURCE
# ============================================================

sources_available = sorted(df_ready["source"].dropna().unique())
selected_sources_global = st.sidebar.multiselect(
    "Source des données (global)",
    sources_available,
    default=sources_available
)

if selected_sources_global:
    df_ready = df_ready[df_ready["source"].isin(selected_sources_global)].copy()

# ============================================================
# SECTION 2 — VISUALISATIONS
# ============================================================

try:
    logo_path = '/Users/elisagault/Desktop/Pôle haltéro/Rapports/temp_logo_ffhm.png'
    logo = Image.open(logo_path)
    st.sidebar.image(logo, width=150)
except Exception:
    st.sidebar.write("")

page = st.sidebar.radio("Navigation", ["Athlètes internationaux"])

# ── Bouton rapport dans la sidebar ──
st.sidebar.divider()
generate_report_clicked = st.sidebar.button("📄 Générer le rapport HTML global")

if page == "Athlètes internationaux":
    st.title("Évolution des Performances")

    athletes_norm = sorted(df_ready['Athlete_norm'].dropna().unique())
    athlete_map = dict(zip(df_ready['Athlete_norm'], df_ready['Athlete']))

    selected_athlete_norm = st.selectbox("Sélectionnez un athlète", athletes_norm)
    selected_athlete = athlete_map[selected_athlete_norm]

    df_athlete = df_ready[df_ready['Athlete_norm'] == selected_athlete_norm].sort_values(by='Date_extrait')
    df_athlete_all = df_athlete.copy()

    if df_athlete.empty:
        st.warning("Aucune donnée pour cet athlète.")
        st.stop()

    # --------- Métriques profil ----------
    def display_athlete_info(athlete_info):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write(f"**Sexe :** {athlete_info.get('Sexe', 'N/A')}")
            st.write(f"**Meilleur arraché :** {athlete_info.get('_max_snatch', 'N/A')}")
            st.write(f"**Taux de réussite arraché :** {athlete_info.get('_taux_ar', np.nan):.1f}%")
        with col2:
            st.write(f"**Âge :** {athlete_info.get('Age', 'N/A')}")
            st.write(f"**Meilleur épaulé-jeté :** {athlete_info.get('_max_clean_jerk', 'N/A')}")
            st.write(f"**Taux de réussite épaulé-jeté :** {athlete_info.get('_taux_cj', np.nan):.1f}%")
        with col3:
            st.write(f"**Catégorie de poids :** {athlete_info.get('Categorie_poids', 'N/A')}")
            st.write(f"**Meilleur total :** {athlete_info.get('_max_total', 'N/A')}")
            st.write(f"**Taux de réussite total :** {athlete_info.get('_taux_total', np.nan):.1f}%")
        with col4:
            st.write(f"**Catégorie d'âge :** {athlete_info.get('Categorie_age', 'N/A')}")

    def compute_avg_rates(dfX):
        df_tmp = dfX.copy()
        for c in ['1','2','3','1.1','2.1','3.1']:
            if c not in df_tmp.columns:
                df_tmp[c] = np.nan
        df_tmp['Taux_arraché'] = df_tmp[['1','2','3']].notna().sum(axis=1) / 3 * 100
        df_tmp['Taux_epj'] = df_tmp[['1.1','2.1','3.1']].notna().sum(axis=1) / 3 * 100
        df_tmp['Taux_total'] = df_tmp[['1','2','3','1.1','2.1','3.1']].notna().sum(axis=1) / 6 * 100
        return df_tmp['Taux_arraché'].mean(), df_tmp['Taux_epj'].mean(), df_tmp['Taux_total'].mean()

    taux_ar_m, taux_epj_m, taux_total_m = compute_avg_rates(df_athlete)

    athlete_info = df_athlete.iloc[-1].to_dict()
    athlete_info.update({
        '_max_snatch': df_athlete['Snatch'].max(),
        '_max_clean_jerk': df_athlete['Clean_Jerk'].max(),
        '_max_total': df_athlete['Total'].max(),
        '_taux_ar': taux_ar_m,
        '_taux_cj': taux_epj_m,
        '_taux_total': taux_total_m
    })
    display_athlete_info(athlete_info)

    # --------- Filtres catégories ----------
    st.header("Évolution des performances")
    col1, col2, col3 = st.columns(3)
    with col1:
        poids_categories = sorted(df_athlete['Categorie_poids'].dropna().astype(str).unique())
        selected_weight_category = st.multiselect(
            "Catégorie de poids",
            poids_categories,
            default=poids_categories
        )
    with col2:
        age_categories = ['Tous'] + sorted(df_athlete['Categorie_age'].dropna().astype(str).unique())
        selected_age_category = st.selectbox("Catégorie d'âge", age_categories)
    with col3:
        period_options = [
            "Auto",
            "6 derniers mois",
            "1 an",
            "2 ans",
            "3 ans",
            "5 ans",
            "Plage personnalisée",
            "Tout"
        ]
        selected_period = st.selectbox("Choisir une période", period_options)

    filtered_df = df_athlete.copy()
    if selected_weight_category:
        filtered_df = filtered_df[filtered_df['Categorie_poids'].isin(selected_weight_category)]
    if selected_age_category != 'Tous':
        filtered_df = filtered_df[filtered_df['Categorie_age'] == selected_age_category]

    if filtered_df.empty:
        st.warning("Aucune donnée pour ces filtres.")
        st.stop()

    # ======================================================
    # FILTRE TEMPOREL GLOBAL
    # ======================================================

    min_date = filtered_df["Date_extrait"].min()
    max_date = filtered_df["Date_extrait"].max()

    def compute_start_date(period, max_date, min_date):
        if period == "6 derniers mois":
            return max_date - pd.DateOffset(months=6)
        elif period == "1 an":
            return max_date - pd.DateOffset(years=1)
        elif period == "2 ans":
            return max_date - pd.DateOffset(years=2)
        elif period == "3 ans":
            return max_date - pd.DateOffset(years=3)
        elif period == "5 ans":
            return max_date - pd.DateOffset(years=5)
        elif period == "Auto":
            return max_date - pd.DateOffset(years=2)
        elif period == "Tout":
            return min_date
        return min_date

    # ---- CAS plage personnalisée ----
    if selected_period == "Plage personnalisée":
        col_start, col_end, _ = st.columns(3)
        with col_start:
            custom_start_date = st.date_input(
                "Date début",
                value=min_date.date(),
                min_value=min_date.date(),
                max_value=max_date.date()
            )
        with col_end:
            custom_end_date = st.date_input(
                "Date fin",
                value=max_date.date(),
                min_value=min_date.date(),
                max_value=max_date.date()
            )
        filtered_df = filtered_df[
            (filtered_df["Date_extrait"] >= pd.Timestamp(custom_start_date))
            & (filtered_df["Date_extrait"] <= pd.Timestamp(custom_end_date))
        ]
    else:
        start_date = compute_start_date(selected_period, max_date, min_date)
        filtered_df = filtered_df[
            filtered_df["Date_extrait"] >= start_date
        ]
    # --------- Graphique performance ----------
    color_list = [
        'rgba(255, 0, 0, 0.2)',
        'rgba(0, 255, 0, 0.2)',
        'rgba(0, 0, 255, 0.2)',
        'rgba(255, 165, 0, 0.2)',
        'rgba(128, 0, 128, 0.2)',
        'rgba(0, 255, 255, 0.2)'
    ]

    unique_categories = sorted(filtered_df['Categorie_poids'].dropna().astype(str).unique())
    color_map = {cat: color_list[i % len(color_list)] for i, cat in enumerate(unique_categories)}

    fig_performance = go.Figure()
    comp_names = filtered_df['Competition'].fillna("Compétition").astype(str).tolist()

    fig_performance.add_trace(go.Scatter(
        x=filtered_df['Date_extrait'], y=filtered_df['Snatch'],
        mode='lines+markers', name='Arraché',
        customdata=comp_names,
        hovertemplate='<b>Arraché</b><br>%{customdata}<br>%{x}<br>%{y} kg<extra></extra>'
    ))
    fig_performance.add_trace(go.Scatter(
        x=filtered_df['Date_extrait'], y=filtered_df['Clean_Jerk'],
        mode='lines+markers', name='Épaulé-jeté',
        customdata=comp_names,
        hovertemplate='<b>Épaulé-jeté</b><br>%{customdata}<br>%{x}<br>%{y} kg<extra></extra>'
    ))
    fig_performance.add_trace(go.Scatter(
        x=filtered_df['Date_extrait'], y=filtered_df['Total'],
        mode='lines+markers', name='Total',
        customdata=comp_names,
        hovertemplate='<b>Total</b><br>%{customdata}<br>%{x}<br>%{y} kg<extra></extra>'
    ))

    if 'P.C.' in filtered_df and not filtered_df['P.C.'].isna().all():
        fig_performance.add_trace(go.Scatter(
            x=filtered_df['Date_extrait'], y=filtered_df['P.C.'],
            mode='lines+markers', name='Poids de corps (kg)',
            line=dict(color='gray', width=2, dash='dot'),
            marker=dict(color='gray', size=8),
            yaxis='y2'
        ))

    for i in range(len(filtered_df)-1):
        current_category = str(filtered_df.iloc[i]['Categorie_poids'])
        fig_performance.add_shape(
            type="rect",
            x0=filtered_df.iloc[i]['Date_extrait'], y0=0,
            x1=filtered_df.iloc[i+1]['Date_extrait'],
            y1=filtered_df[['Snatch','Clean_Jerk','Total']].max().max()*1.1,
            fillcolor=color_map.get(current_category, 'rgba(255,0,0,0.2)'),
            opacity=0.3, layer="below", line_width=0
        )
    if len(filtered_df) > 0:
        last_category = str(filtered_df.iloc[-1]['Categorie_poids'])
        fig_performance.add_shape(
            type="rect",
            x0=filtered_df.iloc[-1]['Date_extrait'], y0=0,
            x1=filtered_df.iloc[-1]['Date_extrait'] + timedelta(days=30),
            y1=filtered_df[['Snatch','Clean_Jerk','Total']].max().max()*1.1,
            fillcolor=color_map.get(last_category, 'rgba(255,0,0,0.2)'),
            opacity=0.3, layer="below", line_width=0
        )

    unique_categories_perf = sorted(filtered_df['Categorie_poids'].dropna().astype(str).unique())
    n = len(unique_categories_perf)
    legend_y_position = -0.28
    max_total_width = 0.9
    item_width = min(0.08, max_total_width / n)
    item_spacing = min(0.15, max_total_width / n)
    legend_x_position = 0.5 - (n * item_spacing) / 2

    fig_performance.add_annotation(
        x=0.5, y=legend_y_position + 0.06,
        text="<b>Catégories de poids</b>",
        showarrow=False, font=dict(size=14),
        xref="paper", yref="paper", align="center"
    )
    for category in unique_categories_perf:
        color = color_map.get(str(category), 'rgba(255,0,0,0.2)')
        fig_performance.add_shape(
            type="rect",
            x0=legend_x_position, y0=legend_y_position - 0.02,
            x1=legend_x_position + item_width, y1=legend_y_position + 0.02,
            fillcolor=color, opacity=0.6, line=dict(width=0),
            xref="paper", yref="paper"
        )
        fig_performance.add_annotation(
            x=legend_x_position + item_width + 0.02, y=legend_y_position,
            text=f"<b>{category}</b>", showarrow=False, font=dict(size=13),
            xref="paper", yref="paper"
        )
        legend_x_position += item_spacing

    # ── AXES COLORÉS (correction v2) ──────────────────────────
    fig_performance.update_layout(
        height=500,
        template="plotly_white",   # ← AJOUTER comme dans taux_fig
        margin=dict(l=20, r=20, b=150, t=40, pad=4),
        xaxis=dict(
            title="Date",
            title_font=dict(color="#1f77b4"),
            tickfont=dict(color="#1f77b4"),
            linecolor="#1f77b4",
            tickcolor="#1f77b4",
            showline=True,          # ← AJOUTER
            zeroline=False,         # ← AJOUTER
        ),
        yaxis=dict(
            title="Performance (kg)",
            title_font=dict(color="#2ca02c"),
            tickfont=dict(color="#2ca02c"),
            linecolor="#2ca02c",
            tickcolor="#2ca02c",
            showline=True,          # ← AJOUTER
            zeroline=False,         # ← AJOUTER
        ),
        yaxis2=dict(
            title="Poids de corps (kg)",
            title_font=dict(color="#ff7f0e"),
            tickfont=dict(color="#ff7f0e"),
            linecolor="#ff7f0e",
            tickcolor="#ff7f0e",
            showline=True,          # ← AJOUTER
            zeroline=False,
            overlaying="y",
            side="right",
            showgrid=False,
        ),
    )

    st.plotly_chart(fig_performance, use_container_width=True)

    # ======================================================
    # Changements de charge par essai (2 dernières années)

    st.header("Changements de charge par essai")

    df_athlete_raw = df_athlete_all.copy()

    # ---- Filtres ----
    col_ch1, col_ch2, col_ch3 = st.columns(3)
    with col_ch1:
        poids_categories_ch = sorted(df_athlete_raw['Categorie_poids'].dropna().astype(str).unique())
        selected_weight_ch = st.multiselect(
            "Catégorie de poids",
            poids_categories_ch,
            default=poids_categories_ch,
            key="weight_changes"
        )
    with col_ch2:
        age_categories_ch = ['Tous'] + sorted(df_athlete_raw['Categorie_age'].dropna().astype(str).unique())
        selected_age_ch = st.selectbox("Catégorie d'âge", age_categories_ch, key="age_changes")
    with col_ch3:
        period_options_ch = [
            "Auto",
            "6 derniers mois",
            "1 an",
            "2 ans",
            "3 ans",
            "5 ans",
            "Plage personnalisée",
            "Tout"
        ]
        selected_period_ch = st.selectbox("Choisir une période", period_options_ch, key="period_changes")

    if selected_weight_ch:
        df_athlete_raw = df_athlete_raw[df_athlete_raw['Categorie_poids'].isin(selected_weight_ch)]
    if selected_age_ch != 'Tous':
        df_athlete_raw = df_athlete_raw[df_athlete_raw['Categorie_age'] == selected_age_ch]

    min_date_ch = df_athlete_raw["Date_extrait"].min()
    max_date_ch = df_athlete_raw["Date_extrait"].max()

    if selected_period_ch == "Plage personnalisée":
        col_start_ch, col_end_ch, _ = st.columns(3)
        with col_start_ch:
            custom_start_ch = st.date_input(
                "Date début",
                value=min_date_ch.date(),
                min_value=min_date_ch.date(),
                max_value=max_date_ch.date(),
                key="start_changes"
            )
        with col_end_ch:
            custom_end_ch = st.date_input(
                "Date fin",
                value=max_date_ch.date(),
                min_value=min_date_ch.date(),
                max_value=max_date_ch.date(),
                key="end_changes"
            )
        df_2y = df_athlete_raw[
            (df_athlete_raw["Date_extrait"] >= pd.Timestamp(custom_start_ch))
            & (df_athlete_raw["Date_extrait"] <= pd.Timestamp(custom_end_ch))
        ].copy()
    else:
        start_date_ch = compute_start_date(selected_period_ch, max_date_ch, min_date_ch)
        df_2y = df_athlete_raw[
            df_athlete_raw["Date_extrait"] >= start_date_ch
        ].copy()
    if 'Date_extrait' in df_athlete_raw and not df_athlete_raw['Date_extrait'].isna().all():
        last_date = df_athlete_raw["Date_extrait"].max()
        if pd.notna(last_date):
            two_years_ago = last_date - pd.DateOffset(years=2)
            df_2y = df_athlete_raw[df_athlete_raw["Date_extrait"] >= two_years_ago].copy()
        else:
            df_2y = df_athlete_raw.copy()
    else:
        df_2y = df_athlete_raw.copy()

    def calculate_attempt_diffs(df_src, lift_cols, lift_cols_raw):
        diffs = []
        for _, row in df_src.iterrows():
            row_diffs = []
            for i in range(len(lift_cols_raw) - 1):
                raw_current = row.get(lift_cols_raw[i])
                raw_next = row.get(lift_cols_raw[i + 1])
                if pd.isna(raw_current) or pd.isna(raw_next):
                    row_diffs.append(np.nan)
                    continue
                try:
                    w1 = float(str(raw_current).replace("-", "").replace(",", ".").strip())
                    w2 = float(str(raw_next).replace("-", "").replace(",", ".").strip())
                    if w1 == 0 or w2 == 0:
                        row_diffs.append(np.nan)
                        continue
                    diff = w2 - w1
                    if diff == 0.0:        # ← AJOUT : même charge répétée, ignorée
                        row_diffs.append(np.nan)
                        continue
                    row_diffs.append(diff)
                except:
                    row_diffs.append(np.nan)
            diffs.append(row_diffs)
        return diffs

    have_sn_cols = set(sn_cols).issubset(df_2y.columns)
    have_cj_cols = set(cj_cols).issubset(df_2y.columns)

    snatch_diffs = calculate_attempt_diffs(df_2y, sn_cols, ['1_raw','2_raw','3_raw'])
    cj_diffs = calculate_attempt_diffs(df_2y, cj_cols, ['1.1_raw','2.1_raw','3.1_raw'])

    def calculate_avg_diffs(diffs, df_src, raw_next_cols):
        avg_1_2_all, avg_2_3_all = [], []
        avg_1_2_ok, avg_2_3_ok = [], []
        avg_1_2_fail, avg_2_3_fail = [], []
        for d, (_, row) in zip(diffs, df_src.iterrows()):
            raw_2 = str(row.get(raw_next_cols[0], "")).strip()
            raw_3 = str(row.get(raw_next_cols[1], "")).strip()
            if len(d) > 0 and not pd.isna(d[0]):
                avg_1_2_all.append(d[0])
                if raw_2.startswith("-"):
                    avg_1_2_fail.append(d[0])
                elif raw_2 not in ("", "nan"):
                    avg_1_2_ok.append(d[0])
            if len(d) > 1 and not pd.isna(d[1]):
                avg_2_3_all.append(d[1])
                if raw_3.startswith("-"):
                    avg_2_3_fail.append(d[1])
                elif raw_3 not in ("", "nan"):
                    avg_2_3_ok.append(d[1])
        return (
            np.mean(avg_1_2_all) if avg_1_2_all else np.nan,
            np.mean(avg_2_3_all) if avg_2_3_all else np.nan,
            np.mean(avg_1_2_ok) if avg_1_2_ok else np.nan,
            np.mean(avg_2_3_ok) if avg_2_3_ok else np.nan,
            np.mean(avg_1_2_fail) if avg_1_2_fail else np.nan,
            np.mean(avg_2_3_fail) if avg_2_3_fail else np.nan,
        )

    avg_sn_1_2, avg_sn_2_3, avg_sn_1_2_ok, avg_sn_2_3_ok, avg_sn_1_2_fail, avg_sn_2_3_fail = \
        calculate_avg_diffs(snatch_diffs, df_2y, ['2_raw', '3_raw'])
    avg_cj_1_2, avg_cj_2_3, avg_cj_1_2_ok, avg_cj_2_3_ok, avg_cj_1_2_fail, avg_cj_2_3_fail = \
        calculate_avg_diffs(cj_diffs, df_2y, ['2.1_raw', '3.1_raw'])

    def fmt(v):
        return f"{v:.1f} kg" if not pd.isna(v) else "–"

    st.markdown(
        f"""
        <style>.small-metric {{ font-size: 0.9rem; margin-bottom: 0.5rem; }}</style>
        <table style="font-size:0.9rem; border-collapse:collapse;">
        <tr>
            <th style="text-align:left; padding:4px 12px;"></th>
            <th style="padding:4px 12px;">Arraché 1→2</th>
            <th style="padding:4px 12px;">Arraché 2→3</th>
            <th style="padding:4px 12px;">Épaulé-jeté 1→2</th>
            <th style="padding:4px 12px;">Épaulé-jeté 2→3</th>
        </tr>
        <tr>
            <td style="padding:4px 12px;"><b>Tous</b></td>
            <td style="padding:4px 12px;">{fmt(avg_sn_1_2)}</td>
            <td style="padding:4px 12px;">{fmt(avg_sn_2_3)}</td>
            <td style="padding:4px 12px;">{fmt(avg_cj_1_2)}</td>
            <td style="padding:4px 12px;">{fmt(avg_cj_2_3)}</td>
        </tr>
        <tr style="color:green;">
            <td style="padding:4px 12px;"><b>✅ Réussis</b></td>
            <td style="padding:4px 12px;">{fmt(avg_sn_1_2_ok)}</td>
            <td style="padding:4px 12px;">{fmt(avg_sn_2_3_ok)}</td>
            <td style="padding:4px 12px;">{fmt(avg_cj_1_2_ok)}</td>
            <td style="padding:4px 12px;">{fmt(avg_cj_2_3_ok)}</td>
        </tr>
        <tr style="color:red;">
            <td style="padding:4px 12px;"><b>🔴 Ratés</b></td>
            <td style="padding:4px 12px;">{fmt(avg_sn_1_2_fail)}</td>
            <td style="padding:4px 12px;">{fmt(avg_sn_2_3_fail)}</td>
            <td style="padding:4px 12px;">{fmt(avg_cj_1_2_fail)}</td>
            <td style="padding:4px 12px;">{fmt(avg_cj_2_3_fail)}</td>
        </tr>
        </table>
        """,
        unsafe_allow_html=True
    )

    table_data = []
    if have_sn_cols or have_cj_cols:
        if 'Competition' not in df_2y.columns:
            df_2y['Competition'] = df_2y.get('Nom_compétition', pd.Series(index=df_2y.index)).astype(str)
        for i, (_, row) in enumerate(df_2y.iterrows()):
            date_val = row.get('Date_extrait', pd.NaT)
            comp_name = str(row.get('Competition', '')).split('\n')[0].strip()

            sn_attempts = []
            for c, c_raw in zip(['1', '2', '3'], ['1_raw', '2_raw', '3_raw']):
                raw = row.get(c_raw)
                if pd.isna(raw) or str(raw).strip() in ('', 'nan'):
                    continue
                weight = str(raw).strip().replace("-", "").replace(",", ".").strip()
                try:
                    w = float(weight)
                    if w == 0:          # ← AJOUT
                        continue
                    sn_attempts.append(f"-{w:.1f}kg" if str(raw).strip().startswith("-") else f"{w:.1f}kg")
                except:
                    pass

            cj_attempts = []
            for c, c_raw in zip(['1.1', '2.1', '3.1'], ['1.1_raw', '2.1_raw', '3.1_raw']):
                raw = row.get(c_raw)
                if pd.isna(raw) or str(raw).strip() in ('', 'nan'):
                    continue
                weight = str(raw).strip().replace("-", "").replace(",", ".").strip()
                try:
                    w = float(weight)
                    if w == 0:          # ← AJOUT
                        continue
                    cj_attempts.append(f"-{w:.1f}kg" if str(raw).strip().startswith("-") else f"{w:.1f}kg")
                except:
                    pass

            sdiff = snatch_diffs[i] if snatch_diffs else []
            cdiff = cj_diffs[i] if cj_diffs else []

            def format_diff(diff, raw_next):
                if pd.isna(diff):
                    return "–"
                txt = f"+{diff:.1f}" if diff >= 0 else f"{diff:.1f}"
                raw_str = str(raw_next).strip() if raw_next is not None else ""
                if raw_str in ("", "nan"):
                    return txt
                return f"🔴 {txt}" if raw_str.startswith("-") else f"🟢 {txt}"

            raw_sn2 = row.get('2_raw', None)
            raw_sn3 = row.get('3_raw', None)
            raw_cj2 = row.get('2.1_raw', None)
            raw_cj3 = row.get('3.1_raw', None)

            table_data.append({
                "Date": date_val,
                "Compétition": comp_name,
                "Arraché (essais)": " → ".join(sn_attempts) if sn_attempts else "–",
                "Arraché 1→2": format_diff(sdiff[0] if len(sdiff) > 0 else np.nan, raw_sn2),
                "Arraché 2→3": format_diff(sdiff[1] if len(sdiff) > 1 else np.nan, raw_sn3),
                "Épaulé-jeté (essais)": " → ".join(cj_attempts) if cj_attempts else "–",
                "Épaulé-jeté 1→2": format_diff(cdiff[0] if len(cdiff) > 0 else np.nan, raw_cj2),
                "Épaulé-jeté 2→3": format_diff(cdiff[1] if len(cdiff) > 1 else np.nan, raw_cj3),
            })

    df_changes = pd.DataFrame(table_data)
    if not df_changes.empty:
        df_changes = df_changes.sort_values(by="Date", ascending=False)
        st.dataframe(
            df_changes.assign(Date=df_changes["Date"].dt.strftime('%Y-%m-%d')),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Essais individuels non disponibles pour calculer les changements de charge (données manquantes ou format IWF non détaillé).")

    # ======================================================
    # Évolution des taux de réussite
    # ======================================================
    st.header("Évolution des taux de réussite")

    def compute_success_rates(df_src):
        src = df_src.copy()
        needed = ['Date_extrait', 'Competition', 'Categorie_poids'] + sn_cols + cj_cols
        for c in needed:
            if c not in src.columns:
                src[c] = np.nan
        src['_na_ar'] = src[sn_cols].notna().sum(axis=1)
        src['_na_cj'] = src[cj_cols].notna().sum(axis=1)
        grp = (src.groupby(['Date_extrait', 'Competition'], dropna=False)
                   .agg(
                        ar_done=('_na_ar', 'sum'),
                        cj_done=('_na_cj', 'sum'),
                        Categorie_poids=('Categorie_poids', lambda x: x.dropna().iloc[-1] if x.notna().any() else np.nan)
                   )
                   .reset_index())
        grp['Taux_arraché'] = (grp['ar_done'] / 3.0).clip(upper=1.0) * 100.0
        grp['Taux_epj'] = (grp['cj_done'] / 3.0).clip(upper=1.0) * 100.0
        grp['Taux_total'] = ((grp['ar_done'] + grp['cj_done']) / 6.0).clip(upper=1.0) * 100.0
        return grp[['Date_extrait', 'Competition', 'Categorie_poids', 'Taux_arraché', 'Taux_epj', 'Taux_total']]

    rates_all = compute_success_rates(df_athlete_all) if not df_athlete_all.empty else pd.DataFrame(
        columns=['Date_extrait','Competition','Categorie_poids','Taux_arraché','Taux_epj','Taux_total']
    )

    # ---- Filtres ----
    col_tx1, col_tx2, col_tx3 = st.columns(3)
    with col_tx1:
        weight_categories_taux = ['Tous'] + sorted(df_athlete['Categorie_poids'].dropna().astype(str).unique())
        selected_weight_category_taux = st.selectbox("Catégorie de poids pour les taux", weight_categories_taux, index=0, key="weight_taux")
    with col_tx2:
        age_categories_taux = ['Tous'] + sorted(df_athlete['Categorie_age'].dropna().astype(str).unique())
        selected_age_category_taux = st.selectbox("Catégorie d'âge pour les taux", age_categories_taux, index=0, key="age_taux")
    with col_tx3:
        period_options_taux = [
            "Auto",
            "6 derniers mois",
            "1 an",
            "2 ans",
            "3 ans",
            "5 ans",
            "Plage personnalisée",
            "Tout"
        ]
        selected_period_taux = st.selectbox("Choisir une période", period_options_taux, key="period_taux")

    rates = rates_all.merge(
        df_athlete[['Date_extrait','Competition','Categorie_age','Categorie_poids']].drop_duplicates(),
        on=['Date_extrait','Competition','Categorie_poids'],
        how='left'
    )

    if selected_weight_category_taux != 'Tous':
        rates = rates[rates['Categorie_poids'] == selected_weight_category_taux]
    if selected_age_category_taux != 'Tous':
        rates = rates[rates['Categorie_age'] == selected_age_category_taux]

    # ---- Filtre temporel ----
    if not rates.empty:
        min_date_taux = rates["Date_extrait"].min()
        max_date_taux = rates["Date_extrait"].max()

        if selected_period_taux == "Plage personnalisée":
            col_start_tx, col_end_tx, _ = st.columns(3)
            with col_start_tx:
                custom_start_taux = st.date_input(
                    "Date début",
                    value=min_date_taux.date(),
                    min_value=min_date_taux.date(),
                    max_value=max_date_taux.date(),
                    key="start_taux"
                )
            with col_end_tx:
                custom_end_taux = st.date_input(
                    "Date fin",
                    value=max_date_taux.date(),
                    min_value=min_date_taux.date(),
                    max_value=max_date_taux.date(),
                    key="end_taux"
                )
            rates = rates[
                (rates["Date_extrait"] >= pd.Timestamp(custom_start_taux))
                & (rates["Date_extrait"] <= pd.Timestamp(custom_end_taux))
            ]
        else:
            start_date_taux = compute_start_date(selected_period_taux, max_date_taux, min_date_taux)
            rates = rates[rates["Date_extrait"] >= start_date_taux]

    taux_fig = None
    if rates.empty:
        st.info("Pas de données suffisantes pour tracer les taux de réussite avec ces filtres.")
    else:
        taux_fig = go.Figure()
        comp_names_taux = rates['Competition'].fillna("Compétition").astype(str).tolist()
        taux_fig.add_trace(go.Scatter(
            x=rates['Date_extrait'], y=rates['Taux_arraché'],
            mode='lines+markers', name="Taux Arraché",
            customdata=comp_names_taux,
            hovertemplate='<b>Taux Arraché</b><br>%{customdata}<br>%{x}<br>%{y:.1f}%<extra></extra>'
        ))
        taux_fig.add_trace(go.Scatter(
            x=rates['Date_extrait'], y=rates['Taux_epj'],
            mode='lines+markers', name="Taux Épaulé-jeté",
            customdata=comp_names_taux,
            hovertemplate='<b>Taux Épaulé-jeté</b><br>%{customdata}<br>%{x}<br>%{y:.1f}%<extra></extra>'
        ))
        taux_fig.add_trace(go.Scatter(
            x=rates['Date_extrait'], y=rates['Taux_total'],
            mode='lines+markers', name="Taux Total",
            customdata=comp_names_taux,
            hovertemplate='<b>Taux Total</b><br>%{customdata}<br>%{x}<br>%{y:.1f}%<extra></extra>'
        ))

        for i in range(len(rates) - 1):
            current_category = str(rates.iloc[i]['Categorie_poids'])
            taux_fig.add_shape(
                type="rect",
                x0=rates.iloc[i]['Date_extrait'], y0=0,
                x1=rates.iloc[i + 1]['Date_extrait'], y1=100,
                fillcolor=color_map.get(current_category, 'rgba(255,0,0,0.2)'),
                opacity=0.5, layer="below", line_width=0
            )
        if len(rates) > 0:
            last_category = str(rates.iloc[-1]['Categorie_poids'])
            taux_fig.add_shape(
                type="rect",
                x0=rates.iloc[-1]['Date_extrait'], y0=0,
                x1=rates.iloc[-1]['Date_extrait'] + timedelta(days=30), y1=100,
                fillcolor=color_map.get(last_category, 'rgba(255,0,0,0.2)'),
                opacity=0.5, layer="below", line_width=0
            )

        unique_cat_taux = sorted(rates['Categorie_poids'].dropna().astype(str).unique())
        legend_y_position = -0.34
        n = len(unique_cat_taux)
        item_spacing = 0.12
        total_width = n * item_spacing
        legend_x_position = 0.5 - total_width / 2
        taux_fig.add_annotation(
            x=0.5, y=legend_y_position + 0.06,
            text="<b>Catégories de poids</b>", showarrow=False,
            font=dict(size=14), xref="paper", yref="paper", align="center"
        )
        for category in unique_cat_taux:
            color = color_map.get(str(category), 'rgba(255,0,0,0.2)')
            taux_fig.add_shape(
                type="rect",
                x0=legend_x_position, y0=legend_y_position - 0.02,
                x1=legend_x_position + 0.03, y1=legend_y_position + 0.02,
                fillcolor=color, opacity=0.6, line=dict(width=0),
                xref="paper", yref="paper"
            )
            taux_fig.add_annotation(
                x=legend_x_position + 0.045, y=legend_y_position,
                text=f"<b>{category}</b>", showarrow=False, font=dict(size=13),
                xref="paper", yref="paper"
            )
            legend_x_position += item_spacing

        taux_fig.update_layout(
            title="Évolution des taux de réussite",
            xaxis_title="",
            yaxis_title="Taux de réussite (%)",
            yaxis=dict(range=[0, 100]),
            template="plotly_white",
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            margin=dict(l=20, r=20, b=100, t=40, pad=4)
        )

        rates_nonan_ar = rates.dropna(subset=['Date_extrait', 'Taux_arraché']).copy()
        rates_nonan_cj = rates.dropna(subset=['Date_extrait', 'Taux_epj']).copy()
        rates_nonan_total = rates.dropna(subset=['Date_extrait', 'Taux_total']).copy()

        if not rates_nonan_ar.empty:
            x_ar = (rates_nonan_ar['Date_extrait'].astype('int64') // 10**9).to_numpy()
            y_ar = rates_nonan_ar['Taux_arraché'].to_numpy()
            lowess_ar = sm.nonparametric.lowess(y_ar, x_ar, frac=0.5, return_sorted=False)
            taux_fig.add_trace(go.Scatter(
                x=rates_nonan_ar['Date_extrait'], y=lowess_ar,
                mode='lines', name="Tendance Arraché (LOESS)",
                line=dict(color='blue', width=4),
                hovertemplate='<b>Tendance Arraché (LOESS)</b><br>%{x}<br>%{y:.1f}%<extra></extra>'
            ))
        if not rates_nonan_cj.empty:
            x_cj = (rates_nonan_cj['Date_extrait'].astype('int64') // 10**9).to_numpy()
            y_cj = rates_nonan_cj['Taux_epj'].to_numpy()
            lowess_cj = sm.nonparametric.lowess(y_cj, x_cj, frac=0.5, return_sorted=False)
            taux_fig.add_trace(go.Scatter(
                x=rates_nonan_cj['Date_extrait'], y=lowess_cj,
                mode='lines', name="Tendance Épaulé-jeté (LOESS)",
                line=dict(color='red', width=4),
                hovertemplate='<b>Tendance Épaulé-jeté (LOESS)</b><br>%{x}<br>%{y:.1f}%<extra></extra>'
            ))
        if not rates_nonan_total.empty:
            x_total = (rates_nonan_total['Date_extrait'].astype('int64') // 10**9).to_numpy()
            y_total = rates_nonan_total['Taux_total'].to_numpy()
            lowess_total = sm.nonparametric.lowess(y_total, x_total, frac=0.5, return_sorted=False)
            taux_fig.add_trace(go.Scatter(
                x=rates_nonan_total['Date_extrait'], y=lowess_total,
                mode='lines', name="Tendance Total (LOESS)",
                line=dict(color='green', width=4),
                hovertemplate='<b>Tendance Total (LOESS)</b><br>%{x}<br>%{y:.1f}%<extra></extra>'
            ))

        st.plotly_chart(taux_fig, use_container_width=True)

    # ======================================================
    # TOP 5 charges
    # ======================================================
    # ======================================================
    # TOP 5 charges
    # ======================================================
    st.subheader("Taux de réussite pour les 5 meilleures charges")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        age_filter = st.selectbox("Catégorie d'âge", ["Toutes"] + sorted(df_athlete["Categorie_age"].dropna().astype(str).unique()), key="age_top5")
    with col_f2:
        weight_filter = st.selectbox("Catégorie de poids", ["Toutes"] + sorted(df_athlete["Categorie_poids"].dropna().astype(str).unique()), key="weight_top5")
    with col_f3:
        period_options_top5 = [
            "Auto",
            "6 derniers mois",
            "1 an",
            "2 ans",
            "3 ans",
            "5 ans",
            "Plage personnalisée",
            "Tout"
        ]
        selected_period_top5 = st.selectbox("Choisir une période", period_options_top5, key="period_top5")

    df_filtered = df_athlete.copy()
    if age_filter != "Toutes":
        df_filtered = df_filtered[df_filtered["Categorie_age"] == age_filter]
    if weight_filter != "Toutes":
        df_filtered = df_filtered[df_filtered["Categorie_poids"] == weight_filter]

    # ---- Filtre temporel ----
    if not df_filtered.empty:
        min_date_top5 = df_filtered["Date_extrait"].min()
        max_date_top5 = df_filtered["Date_extrait"].max()

        if selected_period_top5 == "Plage personnalisée":
            col_start_top5, col_end_top5, _ = st.columns(3)
            with col_start_top5:
                custom_start_top5 = st.date_input(
                    "Date début",
                    value=min_date_top5.date(),
                    min_value=min_date_top5.date(),
                    max_value=max_date_top5.date(),
                    key="start_top5"
                )
            with col_end_top5:
                custom_end_top5 = st.date_input(
                    "Date fin",
                    value=max_date_top5.date(),
                    min_value=min_date_top5.date(),
                    max_value=max_date_top5.date(),
                    key="end_top5"
                )
            df_filtered = df_filtered[
                (df_filtered["Date_extrait"] >= pd.Timestamp(custom_start_top5))
                & (df_filtered["Date_extrait"] <= pd.Timestamp(custom_end_top5))
            ]
        else:
            start_date_top5 = compute_start_date(selected_period_top5, max_date_top5, min_date_top5)
            df_filtered = df_filtered[df_filtered["Date_extrait"] >= start_date_top5]

    def topN_weights_success_counts(dfX, lift_cols, lift_cols_raw, N=5):
        all_weights = []
        for col in lift_cols:
            if col in dfX:
                all_weights.extend(dfX[col].dropna().tolist())
        top_weights = sorted(set(all_weights), reverse=True)[:N]
        results = []
        for w in top_weights:
            success = 0
            attempts = 0
            for col, col_raw in zip(lift_cols, lift_cols_raw):
                if col not in dfX or col_raw not in dfX:
                    continue
                for _, row in dfX[[col, col_raw]].iterrows():
                    raw = row[col_raw]
                    val = row[col]
                    if pd.isna(raw):
                        continue
                    try:
                        raw_w = float(str(raw).replace(',', '.').replace('-', '').strip())
                    except Exception:
                        raw_w = np.nan
                    if pd.notna(raw_w) and abs(raw_w - float(w)) < 1e-6:
                        attempts += 1
                        if pd.notna(val):
                            success += 1
            results.append(f"{success} / {attempts}")
        while len(top_weights) < N:
            top_weights.append(np.nan)
            results.append("–")
        return top_weights, results

    snatch_top5, snatch_counts = topN_weights_success_counts(
        df_filtered, ['1','2','3'], ['1_raw','2_raw','3_raw'], N=5
    )
    cj_top5, cj_counts = topN_weights_success_counts(
        df_filtered, ['1.1','2.1','3.1'], ['1.1_raw','2.1_raw','3.1_raw'], N=5
    )

    top5_table = pd.DataFrame({
        "Type": ["Arraché", "Épaulé-jeté"],
        "1ère charge": [snatch_top5[0], cj_top5[0]],
        "Réussites 1": [snatch_counts[0], cj_counts[0]],
        "2ème charge": [snatch_top5[1], cj_top5[1]],
        "Réussites 2": [snatch_counts[1], cj_counts[1]],
        "3ème charge": [snatch_top5[2], cj_top5[2]],
        "Réussites 3": [snatch_counts[2], cj_counts[2]],
        "4ème charge": [snatch_top5[3], cj_top5[3]],
        "Réussites 4": [snatch_counts[3], cj_counts[3]],
        "5ème charge": [snatch_top5[4], cj_top5[4]],
        "Réussites 5": [snatch_counts[4], cj_counts[4]],
    })
    st.dataframe(top5_table, use_container_width=True)
    # ======================================================
    # Taux de réussite par essai
    # ======================================================
    # ======================================================
    # Taux de réussite par essai
    # ======================================================
    st.subheader("Taux de réussite par essai")

    col_att1, col_att2, col_att3 = st.columns(3)
    with col_att1:
        weight_filter_att = st.selectbox("Catégorie de poids", ["Toutes"] + sorted(df_athlete["Categorie_poids"].dropna().astype(str).unique()), key="weight_att")
    with col_att2:
        age_filter_att = st.selectbox("Catégorie d'âge", ["Toutes"] + sorted(df_athlete["Categorie_age"].dropna().astype(str).unique()), key="age_att")
    with col_att3:
        period_options_att = [
            "Auto",
            "6 derniers mois",
            "1 an",
            "2 ans",
            "3 ans",
            "5 ans",
            "Plage personnalisée",
            "Tout"
        ]
        selected_period_att = st.selectbox("Choisir une période", period_options_att, key="period_att")

    df_2y_ready = df_athlete.copy()
    if weight_filter_att != "Toutes":
        df_2y_ready = df_2y_ready[df_2y_ready["Categorie_poids"] == weight_filter_att]
    if age_filter_att != "Toutes":
        df_2y_ready = df_2y_ready[df_2y_ready["Categorie_age"] == age_filter_att]

    # ---- Filtre temporel ----
    if not df_2y_ready.empty:
        min_date_att = df_2y_ready["Date_extrait"].min()
        max_date_att = df_2y_ready["Date_extrait"].max()

        if selected_period_att == "Plage personnalisée":
            col_start_att, col_end_att, _ = st.columns(3)
            with col_start_att:
                custom_start_att = st.date_input(
                    "Date début",
                    value=min_date_att.date(),
                    min_value=min_date_att.date(),
                    max_value=max_date_att.date(),
                    key="start_att"
                )
            with col_end_att:
                custom_end_att = st.date_input(
                    "Date fin",
                    value=max_date_att.date(),
                    min_value=min_date_att.date(),
                    max_value=max_date_att.date(),
                    key="end_att"
                )
            df_2y_ready = df_2y_ready[
                (df_2y_ready["Date_extrait"] >= pd.Timestamp(custom_start_att))
                & (df_2y_ready["Date_extrait"] <= pd.Timestamp(custom_end_att))
            ]
        else:
            start_date_att = compute_start_date(selected_period_att, max_date_att, min_date_att)
            df_2y_ready = df_2y_ready[df_2y_ready["Date_extrait"] >= start_date_att]

    attempt_table = None
    if df_2y_ready.empty:
        st.info("Aucune donnée disponible pour ces filtres.")
    else:
        def success_by_attempt(dfX, cols, cols_raw):
            out = []
            for col, col_raw in zip(cols, cols_raw):
                if col not in dfX or col_raw not in dfX:
                    out.append("–")
                    continue
                success = 0
                attempts = 0
                for raw, val in zip(dfX[col_raw], dfX[col]):
                    if pd.isna(raw):
                        continue
                    attempts += 1
                    if pd.notna(val):
                        success += 1
                out.append(f"{success} / {attempts}")
            return out

        snatch_attempts = success_by_attempt(df_2y_ready, ['1','2','3'], ['1_raw','2_raw','3_raw'])
        cj_attempts = success_by_attempt(df_2y_ready, ['1.1','2.1','3.1'], ['1.1_raw','2.1_raw','3.1_raw'])

        attempt_table = pd.DataFrame({
            "Type": ["Arraché", "Épaulé-jeté"],
            "1er essai": [snatch_attempts[0], cj_attempts[0]],
            "2e essai":  [snatch_attempts[1], cj_attempts[1]],
            "3e essai":  [snatch_attempts[2], cj_attempts[2]],
        })
        st.dataframe(attempt_table, use_container_width=True)

    # ======================================================
    # Bulles (0/3) par charge
    # ======================================================
    # ======================================================
    # Bulles (0/3) par charge
    # ======================================================
    st.header("Analyse des bulles (0/3) par charge")

    col_bu1, col_bu2, col_bu3 = st.columns(3)
    with col_bu1:
        weight_filter_bu = st.selectbox("Catégorie de poids", ["Toutes"] + sorted(df_athlete_all["Categorie_poids"].dropna().astype(str).unique()), key="weight_bu")
    with col_bu2:
        age_filter_bu = st.selectbox("Catégorie d'âge", ["Toutes"] + sorted(df_athlete_all["Categorie_age"].dropna().astype(str).unique()), key="age_bu")
    with col_bu3:
        period_options_bu = [
            "Auto",
            "6 derniers mois",
            "1 an",
            "2 ans",
            "3 ans",
            "5 ans",
            "Plage personnalisée",
            "Tout"
        ]
        selected_period_bu = st.selectbox("Choisir une période", period_options_bu, key="period_bu")

    df_bulles_src = df_athlete_all.copy()
    if weight_filter_bu != "Toutes":
        df_bulles_src = df_bulles_src[df_bulles_src["Categorie_poids"] == weight_filter_bu]
    if age_filter_bu != "Toutes":
        df_bulles_src = df_bulles_src[df_bulles_src["Categorie_age"] == age_filter_bu]

    # ---- Filtre temporel ----
    if not df_bulles_src.empty:
        min_date_bu = df_bulles_src["Date_extrait"].min()
        max_date_bu = df_bulles_src["Date_extrait"].max()

        if selected_period_bu == "Plage personnalisée":
            col_start_bu, col_end_bu, _ = st.columns(3)
            with col_start_bu:
                custom_start_bu = st.date_input(
                    "Date début",
                    value=min_date_bu.date(),
                    min_value=min_date_bu.date(),
                    max_value=max_date_bu.date(),
                    key="start_bu"
                )
            with col_end_bu:
                custom_end_bu = st.date_input(
                    "Date fin",
                    value=max_date_bu.date(),
                    min_value=min_date_bu.date(),
                    max_value=max_date_bu.date(),
                    key="end_bu"
                )
            df_bulles_src = df_bulles_src[
                (df_bulles_src["Date_extrait"] >= pd.Timestamp(custom_start_bu))
                & (df_bulles_src["Date_extrait"] <= pd.Timestamp(custom_end_bu))
            ]
        else:
            start_date_bu = compute_start_date(selected_period_bu, max_date_bu, min_date_bu)
            df_bulles_src = df_bulles_src[df_bulles_src["Date_extrait"] >= start_date_bu]

    def is_miss(x):
        if pd.isna(x):
            return False
        return str(x).strip().startswith("-")

    def extract_weight_raw(x):
        try:
            if pd.isna(x):
                return np.nan
            return float(str(x).replace("-", "").replace(",", ".").strip())
        except:
            return np.nan

    def compute_bulles(dfX, cols_raw, lift_name):
        results = []
        for _, row in dfX.iterrows():
            raws = [row[c] for c in cols_raw if c in dfX.columns]
            raws = [r for r in raws if not pd.isna(r)]
            if len(raws) > 0 and all(is_miss(r) for r in raws):
                weights = [extract_weight_raw(r) for r in raws]
                charge_bulle = weights[0]
                date_value = row.get("Date_extrait", None)
                competition_value = row.get("Competition", None)
                results.append({
                    "Date": date_value,
                    "Compétition": competition_value,
                    "Mouvement": lift_name,
                    "Charge": charge_bulle
                })
        if len(results) == 0:
            return pd.DataFrame(columns=["Date", "Compétition", "Mouvement", "Charge"])
        df_res = pd.DataFrame(results)
        df_res = df_res.sort_values(by="Date", ascending=False)
        return df_res

    bulles_snatch = compute_bulles(df_bulles_src, ['1_raw','2_raw','3_raw'], "Arraché")
    bulles_cj = compute_bulles(df_bulles_src, ['1.1_raw','2.1_raw','3.1_raw'], "Épaulé-jeté")
    df_bulles = pd.concat([bulles_snatch, bulles_cj], ignore_index=True)

    if df_bulles.empty:
        st.info("Aucune bulle détectée.")
    else:
        df_bulles["Date"] = df_bulles["Date"].dt.strftime("%Y-%m-%d")
        st.dataframe(df_bulles, use_container_width=True)

    # ======================================================
    # Récap multi-athlètes
    # ======================================================
    # ======================================================
    # Récap multi-athlètes
    # ======================================================
    # ======================================================
    # Récap multi-athlètes
    # ======================================================
    st.subheader("Comparaison entre athlètes, par plateau")
    athletes_norm = sorted(df_ready['Athlete_norm'].dropna().unique())
    athlete_map = dict(zip(df_ready['Athlete_norm'], df_ready['Athlete']))

    # ---- Ligne 1 : sélection athlètes ----
    selected_athletes_norm = st.multiselect(
        "Athlètes",
        athletes_norm,
        default=[selected_athlete_norm],
        key="athletes_summary"
    )
    selected_athletes = [athlete_map[a] for a in selected_athletes_norm]

    # ---- Ligne 2 : autres filtres ----
    col_su1, col_su2, col_su3, col_su4 = st.columns(4)
    with col_su1:
        poids_categories_summary = sorted(
            df_ready[df_ready['Athlete_norm'].isin(selected_athletes_norm)]['Categorie_poids'].dropna().astype(str).unique()
        )
        selected_weight_summary = st.multiselect(
            "Catégorie(s) de poids",
            poids_categories_summary,
            default=poids_categories_summary,
            key="weight_summary"
        )
    with col_su2:
        sources_summary_available = sorted(df_ready["source"].dropna().unique())
        selected_sources_summary = st.multiselect(
            "Source",
            sources_summary_available,
            default=sources_summary_available,
            key="source_summary"
        )
    with col_su3:
        age_filter_su = st.selectbox(
            "Catégorie d'âge",
            ["Toutes"] + sorted(df_ready['Categorie_age'].dropna().astype(str).unique()),
            key="age_summary"
        )
    with col_su4:
        period_options_su = [
            "Auto",
            "6 derniers mois",
            "1 an",
            "2 ans",
            "3 ans",
            "5 ans",
            "Plage personnalisée",
            "Tout"
        ]
        selected_period_su = st.selectbox("Période", period_options_su, key="period_summary")

    summary_df = pd.DataFrame()

    if selected_athletes:
        summary_list = []
        for athlete in selected_athletes:
            df_a = df_ready[
                (df_ready['Athlete_norm'] == normalize_string(athlete)) &
                (df_ready['source'].isin(selected_sources_summary)) &
                (df_ready['Categorie_poids'].isin(selected_weight_summary) if selected_weight_summary else True)
            ].copy()

            if age_filter_su != "Toutes":
                df_a = df_a[df_a["Categorie_age"] == age_filter_su]

            if not df_a.empty:
                min_date_su = df_a["Date_extrait"].min()
                max_date_su = df_a["Date_extrait"].max()

                if selected_period_su != "Plage personnalisée":
                    start_date_su = compute_start_date(selected_period_su, max_date_su, min_date_su)
                    df_a = df_a[df_a["Date_extrait"] >= start_date_su]

            if not df_a.empty:
                best_snatch = df_a['Snatch'].max()
                best_cj = df_a['Clean_Jerk'].max()
                if df_a['Total'].notna().any():
                    best_total = df_a['Total'].max()
                    row_best_total = df_a[df_a['Total'] == best_total].sort_values(by='Date_extrait').iloc[-1]
                    bodyweight_best_total = row_best_total.get('P.C.', np.nan)
                else:
                    best_total = np.nan
                    bodyweight_best_total = np.nan

                def first_success(series):
                    vals = series.dropna().values
                    return vals[0] if len(vals) > 0 else np.nan

                snatch_starts = df_a[['1','2','3']].apply(first_success, axis=1)
                best_start_snatch = snatch_starts.dropna().max()
                cj_starts = df_a[['1.1','2.1','3.1']].apply(first_success, axis=1)
                best_start_cj = cj_starts.dropna().max()

                summary_list.append({
                    "Athlète": athlete,
                    "Meilleur total": best_total,
                    "Meilleur arraché": best_snatch,
                    "Meilleur épaulé-jeté": best_cj,
                    "Meilleure barre départ arraché": best_start_snatch,
                    "Meilleure barre départ épaulé-jeté": best_start_cj,
                    "P.C. au meilleur total": bodyweight_best_total,
                    "Date au meilleur total": row_best_total.get('Date_extrait', pd.NaT) if df_a['Total'].notna().any() else pd.NaT,
                    "Compétition au meilleur total": row_best_total.get('Competition', '') if df_a['Total'].notna().any() else '',
                })

        # ---- Plage personnalisée (hors boucle) ----
        if selected_period_su == "Plage personnalisée":
            df_ref = df_ready[df_ready['Athlete_norm'] == normalize_string(selected_athletes[0])]
            if not df_ref.empty:
                min_date_su_ref = df_ref["Date_extrait"].min()
                max_date_su_ref = df_ref["Date_extrait"].max()
                col_start_su, col_end_su, _, _ = st.columns(4)
                with col_start_su:
                    custom_start_su = st.date_input(
                        "Date début",
                        value=min_date_su_ref.date(),
                        min_value=min_date_su_ref.date(),
                        max_value=max_date_su_ref.date(),
                        key="start_summary"
                    )
                with col_end_su:
                    custom_end_su = st.date_input(
                        "Date fin",
                        value=max_date_su_ref.date(),
                        min_value=min_date_su_ref.date(),
                        max_value=max_date_su_ref.date(),
                        key="end_summary"
                    )
                summary_list = []
                for athlete in selected_athletes:
                    df_a = df_ready[
                        (df_ready['Athlete_norm'] == normalize_string(athlete)) &
                        (df_ready['source'].isin(selected_sources_summary)) &
                        (df_ready['Categorie_poids'].isin(selected_weight_summary) if selected_weight_summary else True)
                    ].copy()
                    if age_filter_su != "Toutes":
                        df_a = df_a[df_a["Categorie_age"] == age_filter_su]
                    df_a = df_a[
                        (df_a["Date_extrait"] >= pd.Timestamp(custom_start_su))
                        & (df_a["Date_extrait"] <= pd.Timestamp(custom_end_su))
                    ]
                    if not df_a.empty:
                        best_snatch = df_a['Snatch'].max()
                        best_cj = df_a['Clean_Jerk'].max()
                        if df_a['Total'].notna().any():
                            best_total = df_a['Total'].max()
                            row_best_total = df_a[df_a['Total'] == best_total].sort_values(by='Date_extrait').iloc[-1]
                            bodyweight_best_total = row_best_total.get('P.C.', np.nan)
                        else:
                            best_total = np.nan
                            bodyweight_best_total = np.nan
                        def first_success(series):
                            vals = series.dropna().values
                            return vals[0] if len(vals) > 0 else np.nan
                        snatch_starts = df_a[['1','2','3']].apply(first_success, axis=1)
                        best_start_snatch = snatch_starts.dropna().max()
                        cj_starts = df_a[['1.1','2.1','3.1']].apply(first_success, axis=1)
                        best_start_cj = cj_starts.dropna().max()
                        summary_list.append({
                            "Athlète": athlete,
                            "Meilleur total": best_total,
                            "Meilleur arraché": best_snatch,
                            "Meilleur épaulé-jeté": best_cj,
                            "Meilleure barre départ arraché": best_start_snatch,
                            "Meilleure barre départ épaulé-jeté": best_start_cj,
                            "P.C. au meilleur total": bodyweight_best_total,
                            "Date au meilleur total": row_best_total.get('Date_extrait', pd.NaT) if df_a['Total'].notna().any() else pd.NaT,
                            "Compétition au meilleur total": row_best_total.get('Competition', '') if df_a['Total'].notna().any() else '',
                        })

        summary_df = pd.DataFrame(summary_list)

        if not summary_df.empty:
            summary_df = summary_df.sort_values(by="Meilleur total", ascending=False)
            summary_df_display = summary_df.copy()
            summary_df_display["Date au meilleur total"] = pd.to_datetime(summary_df_display["Date au meilleur total"]).dt.strftime("%Y-%m-%d")

            st.dataframe(
                summary_df_display.style.format({
                    "Meilleur total": "{:.1f}",
                    "Meilleur arraché": "{:.1f}",
                    "Meilleur épaulé-jeté": "{:.1f}",
                    "Meilleure barre départ arraché": "{:.1f}",
                    "Meilleure barre départ épaulé-jeté": "{:.1f}",
                    "P.C. au meilleur total": "{:.1f}",
                }, na_rep="–"),
                use_container_width=True
            )
        else:
            st.info("Aucune donnée pour les filtres sélectionnés.")
    # ======================================================
    # EXPORTS — tout en bas
    # ======================================================
    st.divider()
    st.subheader("Exports")

    # ── Bouton 1 : tableau récapitulatif seul ──────────────
    if not summary_df.empty:
        if st.button("📊 Exporter le tableau récapitulatif"):
            st.download_button(
                "⬇️ Télécharger le tableau HTML",
                data=generate_summary_html(summary_df),
                file_name="recap_athletes.html",
                mime="text/html",
            )

    st.write("")

    # ── Bouton 2 : rapport global complet ──────────────────
    # ── Bouton 2 : rapport global complet ──────────────────
    if generate_report_clicked:

        taux_ar_m, taux_epj_m, taux_total_m = compute_avg_rates(df_athlete)

        info_html = athlete_info_to_html(
            athlete_info, taux_ar_m, taux_epj_m, taux_total_m, selected_athlete
        )

        changes_summary_html = f"""
<div style="text-align:center; margin-bottom:15px; font-size:14px;">
<b>Moyennes sur 2 ans :</b><br><br>
<table style="margin:auto; font-size:13px; border-collapse:collapse;">
  <tr>
    <th style="padding:4px 14px; background:#f2f2f2;"></th>
    <th style="padding:4px 14px; background:#f2f2f2;">Arraché 1→2</th>
    <th style="padding:4px 14px; background:#f2f2f2;">Arraché 2→3</th>
    <th style="padding:4px 14px; background:#f2f2f2;">Épaulé-jeté 1→2</th>
    <th style="padding:4px 14px; background:#f2f2f2;">Épaulé-jeté 2→3</th>
  </tr>
  <tr>
    <td style="padding:4px 14px;"><b>Tous</b></td>
    <td style="padding:4px 14px;">{fmt(avg_sn_1_2)}</td>
    <td style="padding:4px 14px;">{fmt(avg_sn_2_3)}</td>
    <td style="padding:4px 14px;">{fmt(avg_cj_1_2)}</td>
    <td style="padding:4px 14px;">{fmt(avg_cj_2_3)}</td>
  </tr>
  <tr style="color:green;">
    <td style="padding:4px 14px;"><b>✅ Réussis</b></td>
    <td style="padding:4px 14px;">{fmt(avg_sn_1_2_ok)}</td>
    <td style="padding:4px 14px;">{fmt(avg_sn_2_3_ok)}</td>
    <td style="padding:4px 14px;">{fmt(avg_cj_1_2_ok)}</td>
    <td style="padding:4px 14px;">{fmt(avg_cj_2_3_ok)}</td>
  </tr>
  <tr style="color:red;">
    <td style="padding:4px 14px;"><b>🔴 Ratés</b></td>
    <td style="padding:4px 14px;">{fmt(avg_sn_1_2_fail)}</td>
    <td style="padding:4px 14px;">{fmt(avg_sn_2_3_fail)}</td>
    <td style="padding:4px 14px;">{fmt(avg_cj_1_2_fail)}</td>
    <td style="padding:4px 14px;">{fmt(avg_cj_2_3_fail)}</td>
  </tr>
</table>
</div>"""

        html = generate_full_html_report(
            athlete              = selected_athlete,
            info_html            = info_html,
            fig_perf_html        = fig_performance.to_html(full_html=False, include_plotlyjs="cdn"),
            fig_taux_html        = taux_fig.to_html(full_html=False, include_plotlyjs=False) if taux_fig is not None else "<p>—</p>",
            changes_summary_html = changes_summary_html,
            changes_table_html   = df_changes_to_colored_html(df_changes) if not df_changes.empty else "<p>—</p>",
            top5_html            = top5_table.to_html(index=False, border=0),
            attempts_html        = attempt_table.to_html(index=False, border=0) if attempt_table is not None else "<p>—</p>",
            bulles_html          = bulles_to_html(df_bulles),
            summary_html         = summary_to_html(summary_df) if not summary_df.empty else "<p>Aucune donnée.</p>",
        )

        st.sidebar.download_button(
            "⬇️ Télécharger le rapport HTML global",
            data=html,
            file_name=f"rapport_{selected_athlete.replace(' ', '_')}.html",
            mime="text/html",
        )
