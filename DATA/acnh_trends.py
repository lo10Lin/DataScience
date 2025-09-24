import pandas as pd
import numpy as np
import time, math, re, json
from pytrends.request import TrendReq
import warnings


BATCH_SIZE = 4
SLEEP_BETWEEN_CALLS = 8
TIMEFRAME = 'today 12-m'
WEIGHTS_TRENDS = dict(mean=0.7, p95=0.2, recent=0.1)
LAMBDA = 0.6


REGIONS = {
    "Global":  {"geo": "",   "anchor": "animal crossing", "villager_word": "villager"},
    "America": {"geo": "US", "anchor": "animal crossing", "villager_word": "villager"},
    "Europe":  {"geo": "FR", "anchor": "animal crossing", "villager_word": "villageois"},
    "Japan":   {"geo": "JP", "anchor": "どうぶつの森",       "villager_word": "住民"}, 
}


LOCALE_KEY = {
    "Global":  "name-EUen",
    "America": "name-USen",
    "Europe":  "name-EUfr",
    "Japan":   "name-JPja",
}


AMBIGUOUS = {
    "Al","Tom","May","Kit","Kitty","Ann","Ana","Nan","Bud","Ken","Ben","Gus","Ray","Art",
    "Ace","Ava","Stu","Flo","Bob","Bea","Bella","June","Bill","Moe","Dotty","Cherry","Kid",
}

warnings.simplefilter("ignore", category=FutureWarning)

def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

def is_ambiguous(name: str) -> bool:
    return (len(name) <= 3) or (name in AMBIGUOUS)


def load_locale_names(json_path="villagers.json"):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    name_map = {}
    for _, obj in data.items():
        names = obj.get("name", {})
        en_us = names.get("name-USen") or names.get("name-EUen")
        if not en_us:
            continue
        name_map[en_us] = names 
    return name_map

def get_localized_name(en_name, region, name_map):

    names = name_map.get(en_name, {})
    key = LOCALE_KEY[region]
    return names.get(key) or names.get("name-USen") or names.get("name-EUen") or en_name

def make_keyword(en_name: str, species: str, region: str, name_map) -> str:
    """
    Construit la requête Trends locale :
    - nom localisé (FR/JP/EN)
    - ancre locale (animal crossing / どうぶつの森)
    - mot 'villager' traduit pour désambiguïsation + species si ambigu
    """
    loc = get_localized_name(en_name, region, name_map)
    anchor = REGIONS[region]["anchor"]
    word  = REGIONS[region]["villager_word"]

    base = f"{loc} {anchor}".strip()
    if is_ambiguous(en_name):
   
        species = (species or "").lower()
        return f"{loc} {anchor} {word} {species}".strip()
    return base

def safe_trends_batch(pytrends, keywords, geo, timeframe, backoff_start=120, backoff_cap=900):
    backoff = backoff_start
    while True:
        try:
            pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo=geo, gprop='')
            df = pytrends.interest_over_time()
            return df
        except Exception as e:
            msg = str(e)
            if "429" in msg:
                print(f"\n 429 on geo='{geo or 'GLOBAL'}' for batch {keywords[:2]}... sleeping {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, backoff_cap)
            else:
                print(f"\n Error on batch (geo={geo or 'GLOBAL'}): {e}")
                return pd.DataFrame()

def metrics_from_series(s):
    if s is None or s.empty:
        return None, None, None
    s = s.astype(float)
    mean_val = float(s.mean())
    p95_val  = float(s.quantile(0.95))
    recent4  = float(s.tail(4).mean())
    return mean_val, p95_val, recent4

def compute_trends_score(mean_val, p95_val, recent4):
    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in [mean_val, p95_val, recent4]):
        return None
    return (WEIGHTS_TRENDS['mean']  * mean_val +
            WEIGHTS_TRENDS['p95']   * p95_val  +
            WEIGHTS_TRENDS['recent']* recent4)

def minmax_norm(x):
    if x.isna().all():
        return x
    xmin, xmax = x.min(skipna=True), x.max(skipna=True)
    if pd.isna(xmin) or pd.isna(xmax) or xmax == xmin:
        return (x - xmin)
    return (x - xmin) / (xmax - xmin)

def main():

    name_map = load_locale_names("villagers.json") 


    df_v = pd.read_csv("villagers.csv")
    names = df_v["Name"].tolist()                        
    species_map = dict(zip(df_v["Name"], df_v["Species"]))

   
    df_off = pd.read_csv("acnh_villager_rank_official.csv")
    df_off["name_lc"] = df_off["name"].str.strip().str.lower()
    df_v["name_lc"] = df_v["Name"].str.strip().str.lower()
    df_off_sorted = df_off.sort_values(["tier", "rank"], ascending=[True, True]).reset_index(drop=True)
    df_off_sorted["official_rank_overall"] = df_off_sorted.index + 1
    N = len(df_off_sorted)
    df_off_sorted["OfficialScore"] = 1 - (df_off_sorted["official_rank_overall"] - 1) / max(N - 1, 1)
    off_map = df_off_sorted.set_index("name_lc")[["tier","rank","official_rank_overall","OfficialScore"]]

    pytrends = TrendReq(hl='en-US', tz=360)

    rows = []

  
    for region_name, meta in REGIONS.items():
        geo_code = meta["geo"]
        anchor   = meta["anchor"]

        print(f"\n🌍 Region: {region_name} (geo='{geo_code or 'GLOBAL'}')")
        total = len(names); done = 0

      
        kw_objects = []
        for n in names:
            kw = make_keyword(n, species_map.get(n, ""), region_name, name_map)
            kw_objects.append((n, kw))

        for batch in chunked(kw_objects, BATCH_SIZE):
            kw_list = [anchor] + [kw for _, kw in batch]  
            df = safe_trends_batch(pytrends, kw_list, geo_code, TIMEFRAME)

            if df is None or df.empty or anchor not in df.columns:
                for (n, kw) in batch:
                    rows.append({
                        "region": region_name,
                        "villager": n,
                        "identifier": kw,
                        "mean_trend": None, "p95_trend": None, "recent_4w": None,
                        "TrendsScore": None
                    })
            else:
                a = df[anchor].replace(0, np.nan).ffill().bfill()
                for (n, kw) in batch:
                    if kw in df.columns:
                        series = (df[kw] / a) * 100.0
                        mean_val, p95_val, recent4 = metrics_from_series(series)
                        tscore = compute_trends_score(mean_val, p95_val, recent4)
                    else:
                        mean_val = p95_val = recent4 = tscore = None
                    rows.append({
                        "region": region_name,
                        "villager": n,
                        "identifier": kw,
                        "mean_trend": None if mean_val is None else round(mean_val, 3),
                        "p95_trend":  None if p95_val  is None else round(p95_val, 3),
                        "recent_4w":  None if recent4  is None else round(recent4, 3),
                        "TrendsScore": None if tscore  is None else round(tscore, 3),
                    })

            done += len(batch)
            print(f"\r⏳ Progress {region_name}: {done}/{total} ({(done/total)*100:.1f}%)", end="")
            time.sleep(SLEEP_BETWEEN_CALLS)
        print()

  
    df_long = pd.DataFrame(rows)
    df_long["name_lc"] = df_long["villager"].str.strip().str.lower()
    df_long = df_long.merge(off_map, how="left", left_on="name_lc", right_index=True)

    df_long["TrendsScore_norm"] = (
        df_long.groupby("region")["TrendsScore"].transform(lambda col: minmax_norm(col))
    )

    df_long["PopularityIndex"] = (
        LAMBDA * df_long["TrendsScore_norm"].astype(float) +
        (1 - LAMBDA) * df_long["OfficialScore"].astype(float)
    )

    df_long["rank_region"] = (
        df_long.groupby("region")["PopularityIndex"]
               .rank(method="min", ascending=False)
               .astype("Int64")
    )

    df_long = df_long.drop(columns=["name_lc"])
    df_long.to_csv("acnh_popularity_long.csv", index=False)

    score_wide = df_long.pivot_table(index="villager", columns="region", values="PopularityIndex")
    rank_wide  = df_long.pivot_table(index="villager", columns="region", values="rank_region")

    wide = pd.DataFrame(index=score_wide.index)
    for col in score_wide.columns:
        wide[f"index_{col}"] = score_wide[col]
    for col in rank_wide.columns:
        wide[f"rank_{col}"]  = rank_wide[col]

    off_small = df_off_sorted.rename(columns={"name":"villager"})[["villager","tier","rank","official_rank_overall","OfficialScore"]]
    wide = wide.reset_index().merge(off_small, how="left", on="villager")

    sort_col = "index_Global" if "index_Global" in wide.columns else "index_America"
    wide = wide.sort_values(sort_col, ascending=False)
    wide.to_csv("acnh_popularity_ranked.csv", index=False)

    print("\n✅ Files written:")
    print(" - acnh_popularity_long.csv   (Trends localisés + Official + PopularityIndex + ranks)")
    print(" - acnh_popularity_ranked.csv (wide: index_Region & rank_Region + colonnes officielles)")

if __name__ == "__main__":
    main()
