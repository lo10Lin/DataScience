import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple


st.set_page_config(page_title="ACNH – Popularité par région", layout="wide")

PALETTE = {
    'bg': '#0e1117',          
    'panel': '#1a1f2b',        
    'text': '#e5e7eb',         
    'grid': '#334155',         
    'primary': '#91c9ff',     
    'secondary': '#7dd3fc',    
    'violet': '#a78bfa',      
    'pink': '#f472b6',         
    'amber': '#f59e0b',        
    'teal': '#14b8a6',         
}


plt.rcParams.update({
    'figure.facecolor': PALETTE['bg'],
    'axes.facecolor':   PALETTE['panel'],
    'axes.edgecolor':   PALETTE['grid'],
    'axes.labelcolor':  PALETTE['text'],
    'xtick.color':      PALETTE['text'],
    'ytick.color':      PALETTE['text'],
    'text.color':       PALETTE['text'],
    'grid.color':       PALETTE['grid'],
    'grid.alpha':       0.25,
})

st.title(" Animal Crossing – Popularité des villageois par région")


@st.cache_data(show_spinner=False)
def load_data():
    df_ranked = pd.read_csv("DATA/acnh_popularity_ranked.csv")
    df_vill = pd.read_csv("DATA/villagers.csv")
   
    df = df_ranked.merge(df_vill, left_on="villager", right_on="Name", how="left")
    return df, df_ranked, df_vill

df, df_ranked, df_vill = load_data()

REQUIRED_SCORE_COLS = ["index_Global", "index_Europe", "index_America", "index_Japan"]
missing = [c for c in REQUIRED_SCORE_COLS if c not in df.columns]
if missing:
    st.error(f"Colonnes manquantes dans acnh_popularity_ranked.csv: {missing}")
    st.stop()


REGION_LABELS = {
    "Europe": "index_Europe",
    "America": "index_America",
    "Japan": "index_Japan",
}
DISPLAY_REGION = {
    "Europe": "🇪🇺 Europe",
    "America": "🇺🇸 America",
    "Japan": "🇯🇵 Japan",
}
FR_GENDER = {"Male": "Homme", "Female": "Femme"}

ZODIAC_LIST = [
    (120, 218, "Verseau"), (219, 320, "Poissons"), (321, 419, "Bélier"), (420, 520, "Taureau"),
    (521, 620, "Gémeaux"), (621, 722, "Cancer"), (723, 822, "Lion"), (823, 922, "Vierge"),
    (923, 1022, "Balance"), (1023, 1121, "Scorpion"), (1122, 1221, "Sagittaire")
]


def to_md(month: int, day: int) -> int:
    return month * 100 + day

def zodiac_from_mmdd(mmdd: int) -> str:
    if mmdd >= 1222 or mmdd <= 119:
        return "Capricorne"
    for start, end, sign in ZODIAC_LIST:
        if start <= mmdd <= end:
            return sign
    return "?"

def parse_birthday(bday: str) -> Tuple[int, int, str]:
    if pd.isna(bday):
        return (None, None, None)
    try:
        m, d = str(bday).split("/")
        m = int(m); d = int(d)
        return (m, d, zodiac_from_mmdd(to_md(m, d)))
    except Exception:
        return (None, None, None)


def compute_figsize(n_items: int) -> tuple:
    height = max(2.2, min(5.5, 0.28 * n_items))  
    return (6.0, height)


def prepare_region_slice(df_all: pd.DataFrame, region_key: str) -> pd.DataFrame:
    score_col = REGION_LABELS[region_key]
    cols_keep = [
        "villager", score_col, "Gender", "Personality", "Species", "Hobby",
        "Birthday", "Color 1", "Color 2", "Icon Image"
    ]
    sub = df_all[cols_keep].copy()
    sub.rename(columns={score_col: "score"}, inplace=True)
    sub = sub[~sub["score"].isna()]  
    return sub


def bar_chart_all(series: pd.Series, title: str, xlabel: str = "Score moyen", color_key: str = 'primary'):
    series = series.dropna().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=compute_figsize(len(series)))

    color_hex = PALETTE.get(color_key, PALETTE['primary'])

    ax.set_facecolor(PALETTE['panel'])
    ax.grid(axis='x', alpha=0.25, color=PALETTE['grid'])

    series.iloc[::-1].plot(kind="barh", ax=ax, color=color_hex, edgecolor=PALETTE['grid'])
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("")
    fig.tight_layout()
    st.pyplot(fig)


def top_table(df_region: pd.DataFrame, top=True, n=10):
    d = df_region.sort_values("score", ascending=not top).head(n)
    cols = st.columns(2)
    half = int(np.ceil(len(d)/2))
    for i, chunk in enumerate([d.iloc[:half], d.iloc[half:]]):
        with cols[i]:
            for _, row in chunk.iterrows():
                st.markdown(f"**{row['villager']}** – score: {row['score']:.3f}")
                if isinstance(row.get("Icon Image"), str) and row["Icon Image"].startswith("http"):
                    st.image(row["Icon Image"], width=56)
                st.markdown(":heavy_minus_sign:"*10)


def colors_scores(df_region: pd.DataFrame, how: str = "mean") -> pd.Series:
    """Répartit le score d'un villageois entre ses deux couleurs"""
    records = []
    for _, r in df_region.iterrows():
        colors = []
        c1 = r.get("Color 1"); c2 = r.get("Color 2")
        if pd.notna(c1):
            colors.append(str(c1))
        if pd.notna(c2) and str(c2) != str(c1):
            colors.append(str(c2))
        if not colors:
            continue
        share = r["score"] / len(colors)
        for c in colors:
            records.append((c, share))
    if not records:
        return pd.Series(dtype=float)
    dfc = pd.DataFrame(records, columns=["color", "score"]).groupby("color")["score"]
    return (dfc.mean() if how == "mean" else dfc.sum())


with st.sidebar:
    st.subheader("⚙️ Options")
    region = st.selectbox("Région", list(REGION_LABELS.keys()), format_func=lambda k: DISPLAY_REGION[k])
    agg_mode = "moyenne"
 


df_region = prepare_region_slice(df, region)


left, right = st.columns([1, 1])
with left:
    st.subheader("🏆 Top 10 – plus populaires")
    top_table(df_region, top=True, n=10)
with right:
    st.subheader("🥶 Bottom 10 – moins populaires")
    top_table(df_region, top=False, n=10)

st.divider()


c1, c2 = st.columns(2)

# 1) Genre 
with c1:
    g = df_region.copy()
    g["Genre"] = g["Gender"].map({"Male":"Homme","Female":"Femme"}).fillna(g["Gender"]) 
    series_gender = g.groupby("Genre")["score"].mean().sort_values(ascending=False)
    bar_chart_all(series_gender, "Genre le plus populaire (moyenne du score)", color_key='secondary')

# 2) Personnalités
with c2:
    series_pers = df_region.groupby("Personality")["score"].mean().sort_values(ascending=False)
    bar_chart_all(series_pers, "Personnalités les plus populaires (moyenne du score)", color_key='violet')

# 3) Espèces
c3, c4 = st.columns(2)
with c3:
    series_species = df_region.groupby("Species")["score"].mean().sort_values(ascending=False)
    bar_chart_all(series_species, "Espèces les plus populaires (moyenne du score)", color_key='amber')

# 4) Hobbies
with c4:
    series_hobby = df_region.groupby("Hobby")["score"].mean().sort_values(ascending=False)
    bar_chart_all(series_hobby, "Hobbies favoris (moyenne du score)", color_key='teal')

# 5) Signes astro depuis Birthday 

bd = df_region[["Birthday", "score"]].copy()
mmdd_sign = []
for b in bd["Birthday"].fillna(""):
    try:
        m, d = b.split("/"); m = int(m); d = int(d)
        mmdd_sign.append(zodiac_from_mmdd(m*100 + d))
    except Exception:
        mmdd_sign.append(None)

bd["sign"] = mmdd_sign
series_zod = bd.dropna(subset=["sign"]).groupby("sign")["score"].mean().sort_values(ascending=False)
bar_chart_all(series_zod, "Signes astro les plus populaires (moyenne du score)", color_key='pink')

# 6) Couleurs favorites 


series_colors_mean = colors_scores(df_region, how=("mean" if agg_mode=="moyenne" else "sum"))
bar_chart_all(series_colors_mean.sort_values(ascending=False),
              f"Couleurs favorites les plus populaires (agrégation: {agg_mode})",
              xlabel="Score agrégé",color_key="primary")



