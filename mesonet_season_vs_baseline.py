# !pip install -q ksmesopy

# %% STEP 1 - INPUTS
FARM_LAT, FARM_LON = 38.040880, -101.036685   
STATION      = "Roth Tech Farm"   # Kansas Mesonet station; None = nearest one
SEASON_YEAR  = 2026
SEASON       = (5, 9)        # first and last month of the growing season (5-9 = May to September)
BASE_YEARS   = None          # None = all complete years the station has before SEASON_YEAR; or e.g. (2016, 2025)
OUT_CSV      = "/content/mesonet_daily.csv"

# %% STEP 2 - run
import numpy as np, pandas as pd
import ksmesopy as ms
from IPython.display import display

# ---- 1. station: nearest to the farm, and its record length ----
st = ms.get_stations()
low = {c.lower(): c for c in st.columns}
name_c = st.columns[0]
lat_c = next(low[k] for k in low if k.startswith("lat"))
lon_c = next(low[k] for k in low if k.startswith("lon"))
elev_c = next((low[k] for k in low if k.startswith("elev")), None)
st["dist_km"] = 6371 * 2 * np.arcsin(np.sqrt(
    np.sin(np.radians(st[lat_c] - FARM_LAT) / 2) ** 2 +
    np.cos(np.radians(FARM_LAT)) * np.cos(np.radians(st[lat_c])) * np.sin(np.radians(st[lon_c] - FARM_LON) / 2) ** 2))
near = st.sort_values("dist_km").head(5)
print("Nearest Kansas Mesonet stations:"); display(near[[name_c, lat_c, lon_c] + ([elev_c] if elev_c else []) + ["dist_km"]].round(3))
row = near.iloc[0] if STATION is None else st[st[name_c] == STATION].iloc[0]
STN = row[name_c]; S_LAT = float(row[lat_c])
S_ELEV = float(row[elev_c]) if elev_c else 900.0     # m; used only for ETo
print(f"Using station: {STN} ({row['dist_km']:.1f} km from the farm), elevation {S_ELEV:.0f} m")

# ---- 2. daily data: from the station's first date to the end of SEASON_YEAR ----
first, last = pd.Timestamp("2000-01-01"), pd.Timestamp.today().normalize() - pd.Timedelta(days=1)
try:
    act = ms.get_stations_active()
    a = act[act.iloc[:, 0] == STN]
    if len(a):
        first = pd.Timestamp(a["START"].iloc[0]).normalize() + pd.Timedelta(days=1)
        if pd.notna(a["END"].iloc[0]):
            last = min(last, pd.Timestamp(a["END"].iloc[0]).normalize() - pd.Timedelta(days=1))
        print(f"{STN} record: {a['START'].iloc[0]} to {a['END'].iloc[0]}")
except Exception:
    pass
start = max(first, pd.Timestamp(f"{BASE_YEARS[0] if BASE_YEARS else 2000}-01-01"))
end = min(pd.Timestamp(f"{SEASON_YEAR}-12-31"), last)          
print(f"Requesting {start.date()} to {end.date()}")

WANT = ["TEMP2MAVG", "TEMP2MMIN", "TEMP2MMAX", "PRECIP", "SRAVG", "WSPD2MAVG", "RELHUM2MMIN", "RELHUM2MMAX", "VPDEFAVG"]
VARS = []                                     
for v in WANT:
    try:
        ms.request_data(STN, f"{SEASON_YEAR}-07-01", f"{SEASON_YEAR}-07-02", "day", [v]); VARS.append(v)
    except Exception:
        print(f"  {v} not available at {STN} - skipped")
parts = []                                    
for y in range(start.year, end.year + 1):
    a0 = max(start, pd.Timestamp(f"{y}-01-01")); a1 = min(end, pd.Timestamp(f"{y}-12-31"))
    try:
        parts.append(ms.request_data(STN, a0.strftime("%Y-%m-%d"), a1.strftime("%Y-%m-%d"), "day", VARS))
        print(f"  {y}: ok")
    except Exception as e:
        print(f"  {y}: failed ({str(e)[:80]})")
d = pd.concat(parts, ignore_index=True)
d["TIMESTAMP"] = pd.to_datetime(d["TIMESTAMP"])
d = d[d.TIMESTAMP.dt.month.between(*SEASON)].copy()
for v in WANT:
    if v not in d: d[v] = np.nan

# FAO-56 Penman-Monteith reference ET (grass), from the Mesonet daily data
d["ETo"] = ms.reference_et_penman_monteith(
    doy=d.TIMESTAMP.dt.dayofyear.values, lat=S_LAT, elev=S_ELEV,
    tmin=d.TEMP2MMIN.values, tmax=d.TEMP2MMAX.values, srad=d.SRAVG.values, wspd=d.WSPD2MAVG.values,
    rhmin=d.RELHUM2MMIN.values if d.RELHUM2MMIN.notna().any() else None,
    rhmax=d.RELHUM2MMAX.values if d.RELHUM2MMAX.notna().any() else None,
    vpd=d.VPDEFAVG.values if d.VPDEFAVG.notna().any() else None, wind_height=2.0)
d.to_csv(OUT_CSV, index=False)

# ---- 3. season totals / means per year (a year counts only if >= 90% of its days have data) ----
d["year"] = d.TIMESTAMP.dt.year; d["month"] = d.TIMESTAMP.dt.month
ndays = pd.Timestamp(f"2001-{SEASON[1]}-01").days_in_month + (pd.Timestamp(f"2001-{SEASON[1]}-01") - pd.Timestamp(f"2001-{SEASON[0]}-01")).days
g = d.groupby("year")
yr = pd.DataFrame({
    "days_with_data": g.TEMP2MAVG.count(),
    "Tmean": g.TEMP2MAVG.mean(), "Tmin": g.TEMP2MMIN.mean(), "Tmax": g.TEMP2MMAX.mean(),
    "precip_mm": g.PRECIP.sum(min_count=1), "precip_days": g.PRECIP.count(),
    "ETo_mm": g.ETo.sum(min_count=1), "ETo_days": g.ETo.count()})
yr["complete"] = (yr.days_with_data >= 0.9 * ndays) & (yr.precip_days >= 0.9 * ndays) & (yr.ETo_days >= 0.9 * ndays)
print(f"\nSeason {SEASON[0]}–{SEASON[1]} ({ndays} days) by year:"); display(yr.round(1))

if SEASON_YEAR not in yr.index:
    raise SystemExit(f"No {SEASON_YEAR} data for months {SEASON}. Check the per-year messages above: "
                     f"if {SEASON_YEAR} 'failed', re-run in a few minutes or shorten SEASON to the months that have data.")
if not yr.loc[SEASON_YEAR, "complete"]:
    print(f"WARNING: {SEASON_YEAR} has data on only {int(yr.loc[SEASON_YEAR, 'days_with_data'])} of {ndays} days.")
base = yr[(yr.index < SEASON_YEAR) & yr.complete]
if BASE_YEARS: base = base.loc[BASE_YEARS[0]:BASE_YEARS[1]]
cur = yr.loc[SEASON_YEAR]
print(f"Baseline uses {len(base)} complete years: {list(base.index)}")
if len(base) == 0:
    raise SystemExit("No complete earlier years at this station. Use a station with a longer record for the baseline.")
print(f"-> In the text write: 'compared with the {base.index.min()}–{base.index.max()} mean ({len(base)} years)'.")
if len(base) < 5:
    print("WARNING: fewer than 5 baseline years. Call it a short-term comparison, not a long-term average.")

summ = pd.DataFrame({
    f"{SEASON_YEAR}": [cur.Tmean, cur.Tmin, cur.Tmax, cur.precip_mm, cur.ETo_mm, cur.ETo_mm / ndays],
    f"Mean {base.index.min()}–{base.index.max()}": [base.Tmean.mean(), base.Tmin.mean(), base.Tmax.mean(),
                                                    base.precip_mm.mean(), base.ETo_mm.mean(), base.ETo_mm.mean() / ndays]},
    index=["Mean air temperature (°C)", "Mean daily min (°C)", "Mean daily max (°C)",
           "Precipitation (mm)", "ETo (mm)", "Mean daily ETo (mm/d)"])
summ["Difference"] = summ.iloc[:, 0] - summ.iloc[:, 1]
summ["Difference (%)"] = 100 * summ["Difference"] / summ.iloc[:, 1]
print("\nSeason summary (current year vs mean of the earlier years):"); display(summ.round(2))

mon = d[d.year == SEASON_YEAR].groupby("month").agg(Tmean=("TEMP2MAVG", "mean"), precip_mm=("PRECIP", "sum"), ETo_mm=("ETo", "sum"))
mon_base = d[d.year.isin(base.index)].groupby(["year", "month"]).agg(precip_mm=("PRECIP", "sum"), ETo_mm=("ETo", "sum"), Tmean=("TEMP2MAVG", "mean")).groupby("month").mean()
print(f"\nMonthly {SEASON_YEAR} (and baseline mean):")
display(mon.join(mon_base, rsuffix="_base").round(1))
print("Missing days in", SEASON_YEAR, ":", int(ndays - cur.days_with_data))
