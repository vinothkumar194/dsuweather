import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import io
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="DSU - DSAC Weather Portal",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CONFIGURATION & URL SANITIZATION
# ============================================================

RAW_BASE_URL = "https://api.ritu.ai"
if "[" in RAW_BASE_URL and "]" in RAW_BASE_URL:
    RAW_BASE_URL = RAW_BASE_URL.split("]")[0].replace("[", "")
RITU_BASE_URL = RAW_BASE_URL.strip().rstrip("/")

LATITUDE = 11.2295
LONGITUDE = 78.8835
IST = ZoneInfo("Asia/Kolkata")

RITU_API_KEY = st.secrets.get("RITU_API_KEY", "").strip()
OPENWEATHER_API_KEY = st.secrets.get("OPENWEATHER_API_KEY", "").strip()


# Helper to prevent Streamlit from turning HTML with indents into markdown code blocks
def render_clean_html(html_str):
    clean = " ".join(line.strip() for line in html_str.splitlines())
    st.markdown(clean, unsafe_allow_html=True)


# Helper function to get clean system fonts
def get_font(size, bold=False):
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "Arial Bold.ttf" if bold else "Arial.ttf"
    ]
    for candidate in font_candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def create_gradient(width, height, top_rgb, bottom_rgb):
    base = Image.new("RGB", (width, height), top_rgb)
    bottom = Image.new("RGB", (width, height), bottom_rgb)
    mask = Image.new("L", (width, height))
    mask_data = []
    for y in range(height):
        mask_data.extend([int(255 * (y / height))] * width)
    mask.putdata(mask_data)
    base.paste(bottom, (0, 0), mask)
    return base


# ============================================================
# BRAND STYLING: NAVY BLUE (#001F3F, #0A2540) & GOLDEN YELLOW (#FFC72C)
# ============================================================

render_clean_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=Inter:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.main-title {
    font-family: 'Montserrat', sans-serif;
    font-size: 2.3rem;
    font-weight: 800;
    color: #001F3F;
    margin-bottom: 0.15rem;
    letter-spacing: -0.5px;
}

.subtitle {
    font-size: 1.05rem;
    color: #334155;
    margin-bottom: 1.6rem;
    font-weight: 500;
}

/* Vertical Mobile-Friendly Morning Card */
.morning-card-wrapper {
    display: flex;
    justify-content: center;
    margin-bottom: 20px;
}

.morning-card {
    width: 100%;
    max-width: 460px;
    background: linear-gradient(165deg, #001F3F 0%, #08284d 60%, #00142b 100%);
    border-radius: 24px;
    padding: 24px;
    color: white;
    box-shadow: 0 16px 32px rgba(0, 31, 63, 0.28);
    border: 2px solid #FFC72C;
}

.card-univ-tag {
    color: #FFC72C;
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    text-align: center;
    margin-bottom: 4px;
}

.card-title-main {
    font-family: 'Montserrat', sans-serif;
    font-size: 1.45rem;
    font-weight: 800;
    text-align: center;
    color: #FFFFFF;
    margin-bottom: 12px;
}

.card-time-pill {
    background: rgba(255, 199, 44, 0.15);
    border: 1px solid #FFC72C;
    color: #FFD700;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    text-align: center;
    margin: 0 auto 20px auto;
    width: fit-content;
}

.temp-container {
    text-align: center;
    margin-bottom: 18px;
}

.temp-primary {
    font-family: 'Montserrat', sans-serif;
    font-size: 4.4rem;
    font-weight: 800;
    color: #FFC72C;
    line-height: 1;
    margin-bottom: 6px;
    text-shadow: 0 2px 8px rgba(0,0,0,0.4);
}

.extremes-vertical {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 199, 44, 0.35);
    padding: 14px;
    border-radius: 16px;
    margin-bottom: 16px;
}

.extreme-item {
    font-size: 0.85rem;
}

.extreme-item strong {
    font-size: 1.1rem;
    color: #FFFFFF;
}

.grid-metrics {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
}

.metric-item {
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.12);
    padding: 12px;
    border-radius: 14px;
    text-align: center;
}

.metric-item-full {
    grid-column: span 2;
    background: rgba(255, 199, 44, 0.12);
    border: 1px solid #FFC72C;
}

.metric-value {
    font-size: 1.35rem;
    font-weight: 700;
    color: #FFC72C;
    margin-bottom: 2px;
}

.metric-item-full .metric-value {
    color: #FFD700;
    font-size: 1.5rem;
}

.metric-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #E2E8F0;
}

.card-footer-tag {
    text-align: center;
    font-size: 0.78rem;
    color: #94A3B8;
    margin-top: 16px;
    padding-top: 10px;
    border-top: 1px solid rgba(255,255,255,0.1);
}

/* Forecast Horizontal Styles */
.forecast-section {
    background: linear-gradient(135deg, #001F3F 0%, #0A2540 100%);
    border-radius: 20px;
    padding: 22px;
    color: white;
    box-shadow: 0 12px 24px rgba(0, 31, 63, 0.15);
    border: 2px solid #FFC72C;
    margin-bottom: 15px;
}

.forecast-scroll-row {
    display: flex;
    overflow-x: auto;
    gap: 14px;
    padding-bottom: 12px;
}

.forecast-scroll-row::-webkit-scrollbar {
    height: 8px;
}

.forecast-scroll-row::-webkit-scrollbar-thumb {
    background: #FFC72C;
    border-radius: 4px;
}

.forecast-card {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 199, 44, 0.4);
    min-width: 155px;
    padding: 14px;
    border-radius: 14px;
    text-align: center;
}

.fc-time { font-weight: 700; font-size: 1.05rem; color: #FFC72C; }
.fc-date { font-size: 0.78rem; color: #CBD5E1; margin-bottom: 8px; }
.fc-temp { font-size: 1.7rem; font-weight: 800; color: #FFFFFF; margin: 6px 0; }
.fc-desc { font-size: 0.82rem; font-weight: 600; text-transform: capitalize; color: #FFD700; margin-bottom: 8px; }
.fc-detail { font-size: 0.78rem; color: #E2E8F0; line-height: 1.45; text-align: left; background: rgba(0, 0, 0, 0.25); padding: 8px; border-radius: 8px; }

.section-title {
    font-family: 'Montserrat', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    margin-top: 1.8rem;
    margin-bottom: 0.8rem;
    color: #001F3F;
}
</style>
""")

# ============================================================
# HEADER
# ============================================================

render_clean_html('<div class="main-title">DSU • Dhanalakshmi Srinivasan Agriculture College</div>')
render_clean_html(
    '<div class="subtitle">Agrometeorological Observatory & Real-Time Weather Portal — Perambalur, Tamil Nadu</div>')

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("Portal Controls")
history_range = st.sidebar.selectbox("Historical data range", ["24h", "7d", "30d", "90d"], index=1)

if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info(
    "Brand Colors: Navy Blue & Golden Yellow\n\nData refreshed automatically from Ritu Observatory and OpenWeather.")


# ============================================================
# DATA FETCHING & PROCESSING FUNCTIONS
# ============================================================

def ritu_headers():
    return {
        "Authorization": f"Bearer {RITU_API_KEY}",
        "Accept": "application/json"
    }


@st.cache_data(ttl=300)
def get_ritu_history(hrange):
    url = f"{RITU_BASE_URL}/api/v1/stations/history"
    params = {
        "range": hrange,
        "metric": "temperature,humidity,pressure,windSpeed,windDirection,rain",
        "bucket": "10m"
    }
    response = requests.get(url, headers=ritu_headers(), params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def history_to_dataframe(data):
    if not isinstance(data, dict):
        return pd.DataFrame()
    series = data.get("series")
    if not isinstance(series, dict):
        return pd.DataFrame()

    parameters = ["temperature", "humidity", "pressure", "windSpeed", "windDirection", "rain"]
    observations = {}

    for parameter in parameters:
        parameter_data = series.get(parameter, [])
        if not isinstance(parameter_data, list):
            continue
        for point in parameter_data:
            if not isinstance(point, dict):
                continue
            timestamp = point.get("t")
            value = point.get("v")
            if timestamp is None:
                continue

            timestamp = pd.to_datetime(timestamp, utc=True, errors="coerce")
            if pd.isna(timestamp):
                continue

            timestamp_key = timestamp.isoformat()
            if timestamp_key not in observations:
                observations[timestamp_key] = {"timestamp": timestamp}
            observations[timestamp_key][parameter] = value

    if not observations:
        return pd.DataFrame()

    df_new = pd.DataFrame(list(observations.values()))

    for parameter in parameters:
        if parameter not in df_new.columns:
            df_new[parameter] = np.nan
        df_new[parameter] = pd.to_numeric(df_new[parameter], errors="coerce")

    df_new["timestamp"] = pd.to_datetime(df_new["timestamp"], utc=True)
    df_new["timestamp_ist"] = df_new["timestamp"].dt.tz_convert("Asia/Kolkata")
    return df_new.sort_values("timestamp_ist").reset_index(drop=True)


def wind_direction_name(degrees):
    if pd.isna(degrees):
        return "—", "—"
    directions = [
        ("N", "North"), ("NNE", "North-Northeast"), ("NE", "Northeast"), ("ENE", "East-Northeast"),
        ("E", "East"), ("ESE", "East-Southeast"), ("SE", "Southeast"), ("SSE", "South-Southeast"),
        ("S", "South"), ("SSW", "South-Southwest"), ("SW", "Southwest"), ("WSW", "West-Southwest"),
        ("W", "West"), ("WNW", "West-Northwest"), ("NW", "Northwest"), ("NNW", "North-Northwest")
    ]
    index = int((degrees + 11.25) / 22.5) % 16
    return directions[index]


def circular_mean(values):
    values = pd.Series(values).dropna()
    if values.empty:
        return np.nan
    radians = np.deg2rad(values)
    return np.rad2deg(np.arctan2(np.mean(np.sin(radians)), np.mean(np.cos(radians)))) % 360


def calculate_dew_point(temperature, humidity):
    if pd.isna(temperature) or pd.isna(humidity) or humidity <= 0:
        return np.nan
    a, b = 17.27, 237.7
    alpha = ((a * temperature) / (b + temperature) + np.log(humidity / 100))
    return (b * alpha) / (a - alpha)


def create_hourly_dataframe(ten_minute_df):
    if ten_minute_df.empty:
        return pd.DataFrame()
    temp_df = ten_minute_df.set_index("timestamp_ist")
    hourly = temp_df.resample("1h").agg({
        "temperature": "mean",
        "humidity": "mean",
        "pressure": "mean",
        "windSpeed": "mean",
        "rain": "sum"
    }).reset_index()
    wind_direction = temp_df["windDirection"].resample("1h").apply(circular_mean).reset_index(name="windDirection")
    return hourly.merge(wind_direction, on="timestamp_ist", how="left")


def create_daily_dataframe(hourly_df):
    if hourly_df.empty:
        return pd.DataFrame()
    temp_df = hourly_df.set_index("timestamp_ist")
    daily = temp_df.resample("1D").agg({
        "temperature": "mean",
        "humidity": "mean",
        "pressure": "mean",
        "windSpeed": "mean",
        "rain": "sum"
    }).reset_index()
    wind_direction = temp_df["windDirection"].resample("1D").apply(circular_mean).reset_index(name="windDirection")
    return daily.merge(wind_direction, on="timestamp_ist", how="left")


def calculate_daily_extremes(ten_minute_df):
    if ten_minute_df.empty:
        return None
    work = ten_minute_df.copy()
    work["date"] = work["timestamp_ist"].dt.date
    latest_date = work["date"].max()
    day_df = work[work["date"] == latest_date].copy()

    if day_df.empty:
        return None
    result = {"date": latest_date, "temp_max": np.nan, "temp_min": np.nan, "rh_max": np.nan, "rh_min": np.nan}

    temp_vals = day_df["temperature"].dropna()
    if not temp_vals.empty:
        max_idx, min_idx = temp_vals.idxmax(), temp_vals.idxmin()
        result.update({
            "temp_max": float(day_df.loc[max_idx, "temperature"]),
            "temp_min": float(day_df.loc[min_idx, "temperature"]),
            "temp_max_time": day_df.loc[max_idx, "timestamp_ist"],
            "temp_min_time": day_df.loc[min_idx, "timestamp_ist"]
        })

    rh_vals = day_df["humidity"].dropna()
    if not rh_vals.empty:
        max_idx, min_idx = rh_vals.idxmax(), rh_vals.idxmin()
        result.update({
            "rh_max": float(day_df.loc[max_idx, "humidity"]),
            "rh_min": float(day_df.loc[min_idx, "humidity"]),
            "rh_max_time": day_df.loc[max_idx, "timestamp_ist"],
            "rh_min_time": day_df.loc[min_idx, "timestamp_ist"]
        })
    return result


@st.cache_data(ttl=600)
def get_openweather_forecast():
    if not OPENWEATHER_API_KEY:
        return None
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"lat": LATITUDE, "lon": LONGITUDE, "appid": OPENWEATHER_API_KEY, "units": "metric"}
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300)
def get_rainfall_24h():
    now_ist = datetime.now(IST)
    today_0845 = now_ist.replace(hour=8, minute=45, second=0, microsecond=0)
    if now_ist < today_0845:
        today_0845 -= timedelta(days=1)
    yesterday_0845 = today_0845 - timedelta(days=1)

    start_utc = yesterday_0845.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    end_utc = today_0845.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    url = f"{RITU_BASE_URL}/api/v1/stations/rain/series"
    response = requests.get(url, headers=ritu_headers(), params={"from": start_utc, "to": end_utc, "bucket": "minute"},
                            timeout=30)
    response.raise_for_status()

    data = response.json()
    values = []

    if isinstance(data, dict):
        target = data.get("series") or data.get("data")
        if isinstance(target, list):
            for p in target:
                if isinstance(p, dict) and p.get("v") is not None:
                    values.append(float(p["v"]))
    elif isinstance(data, list):
        for p in data:
            if isinstance(p, dict) and p.get("v") is not None:
                values.append(float(p["v"]))

    return (sum(values), yesterday_0845, today_0845) if values else (np.nan, yesterday_0845, today_0845)


# ============================================================
# ROBUST IMAGE GENERATORS (NAVY & YELLOW BRAND PALETTE)
# No broken character fonts, all text clear with high contrast
# ============================================================

def generate_morning_card_image(date_str, temp_val, max_t_val, max_t_tm, min_t_val, min_t_tm, max_rh_val, min_rh_val,
                                hum_val, dew_val, w_kmph_val, dir_str, press_val, rain_str):
    W, H = 820, 1180
    # Brand Navy Gradient (#001F3F to #001226)
    img = create_gradient(W, H, (0, 31, 63), (0, 18, 38))
    draw = ImageDraw.Draw(img)

    # Clean fonts
    f_univ = get_font(22, bold=True)
    f_title = get_font(34, bold=True)
    f_pill = get_font(24, bold=True)
    f_temp = get_font(95, bold=True)
    f_ext_label = get_font(22, bold=True)
    f_ext_val = get_font(25, bold=True)
    f_metric_val = get_font(32, bold=True)
    f_metric_lbl = get_font(18, bold=True)
    f_foot = get_font(20)

    # Border frame in Golden Yellow (#FFC72C)
    draw.rounded_rectangle([15, 15, W - 15, H - 15], radius=25, outline=(255, 199, 44), width=4)

    # University Header
    draw.text((W // 2, 55), "DHANALAKSHMI SRINIVASAN UNIVERSITY", font=f_univ, fill=(255, 199, 44), anchor="mm")
    draw.text((W // 2, 98), "Daily Weather Summary", font=f_title, fill=(255, 255, 255), anchor="mm")

    # Time Pill in Yellow
    pill_w = 460
    pill_box = [W // 2 - pill_w // 2, 135, W // 2 + pill_w // 2, 180]
    draw.rounded_rectangle(pill_box, radius=22, fill=(15, 45, 85), outline=(255, 199, 44), width=2)
    draw.text((W // 2, 157), date_str, font=f_pill, fill=(255, 215, 0), anchor="mm")

    # Big Temperature Display
    draw.text((W // 2, 275), f"{temp_val:.1f}°C", font=f_temp, fill=(255, 199, 44), anchor="mm")
    draw.text((W // 2, 340), "Observation at Weather Station", font=f_metric_lbl, fill=(203, 213, 225), anchor="mm")

    # Daily Extremes Box (Navy background with Yellow accents)
    ext_box = [45, 375, W - 45, 510]
    draw.rounded_rectangle(ext_box, radius=18, fill=(10, 40, 75), outline=(255, 199, 44), width=2)

    # Max Temp
    draw.text((70, 410), "Max Temp:", font=f_ext_label, fill=(255, 180, 180))
    draw.text((215, 410), f"{max_t_val:.1f}°C ({max_t_tm})", font=f_ext_val, fill=(255, 255, 255))
    # Min Temp
    draw.text((70, 465), "Min Temp:", font=f_ext_label, fill=(180, 215, 255))
    draw.text((215, 465), f"{min_t_val:.1f}°C ({min_t_tm})", font=f_ext_val, fill=(255, 255, 255))

    # Max RH
    draw.text((475, 410), "Max RH:", font=f_ext_label, fill=(190, 245, 240))
    draw.text((610, 410), f"{max_rh_val:.1f}%", font=f_ext_val, fill=(255, 255, 255))
    # Min RH
    draw.text((475, 465), "Min RH:", font=f_ext_label, fill=(255, 225, 235))
    draw.text((610, 465), f"{min_rh_val:.1f}%", font=f_ext_val, fill=(255, 255, 255))

    # Metric Grid Tiles (2x2 + full row for rainfall)
    coords = [
        ([45, 535, W // 2 - 15, 665], f"{hum_val:.1f}%", "HUMIDITY"),
        ([W // 2 + 15, 535, W - 45, 665], f"{dew_val:.1f}°C", "DEW POINT"),
        ([45, 685, W // 2 - 15, 815], f"{w_kmph_val:.1f} km/h", f"WIND ({dir_str})"),
        ([W // 2 + 15, 685, W - 45, 815], f"{press_val:.1f} hPa", "PRESSURE"),
        ([45, 835, W - 45, 965], rain_str, "24-HOUR RAINFALL")
    ]

    for idx, (box, val, lbl) in enumerate(coords):
        is_rain = (idx == 4)
        box_bg = (18, 55, 100) if not is_rain else (25, 70, 120)
        border_col = (255, 199, 44) if is_rain else (60, 95, 145)
        border_w = 2 if is_rain else 1

        draw.rounded_rectangle(box, radius=16, fill=box_bg, outline=border_col, width=border_w)
        center_x = (box[0] + box[2]) // 2

        val_col = (255, 215, 0) if is_rain else (255, 199, 44)
        draw.text((center_x, box[1] + 45), val, font=f_metric_val, fill=val_col, anchor="mm")
        draw.text((center_x, box[1] + 90), lbl, font=f_metric_lbl, fill=(226, 232, 240), anchor="mm")

    # Footer
    draw.text((W // 2, 1055), "Dhanalakshmi Srinivasan Agriculture College • Perambalur, Tamil Nadu", font=f_foot,
              fill=(255, 199, 44), anchor="mm")
    draw.text((W // 2, 1090), "Agrometeorological Observatory", font=f_metric_lbl, fill=(148, 163, 184), anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_forecast_image(forecast_items):
    W, H = 880, 1280
    # Navy Blue Gradient
    img = create_gradient(W, H, (0, 31, 63), (0, 18, 38))
    draw = ImageDraw.Draw(img)

    f_univ = get_font(22, bold=True)
    f_title = get_font(32, bold=True)
    f_sub = get_font(20)
    f_box_time = get_font(24, bold=True)
    f_box_temp = get_font(36, bold=True)
    f_box_desc = get_font(20, bold=True)
    f_box_detail = get_font(18)
    f_foot = get_font(19)

    # Yellow Frame Border
    draw.rounded_rectangle([15, 15, W - 15, H - 15], radius=25, outline=(255, 199, 44), width=4)

    draw.text((W // 2, 50), "DHANALAKSHMI SRINIVASAN UNIVERSITY", font=f_univ, fill=(255, 199, 44), anchor="mm")
    draw.text((W // 2, 90), "24-Hour Forecast (3-Hour Intervals)", font=f_title, fill=(255, 255, 255), anchor="mm")
    draw.text((W // 2, 128), "Agrometeorological Observatory • Perambalur, Tamil Nadu", font=f_sub,
              fill=(203, 213, 225), anchor="mm")

    row_height = 230
    col_width = (W - 120) // 2

    for idx, item in enumerate(forecast_items[:8]):
        col = idx % 2
        row = idx // 2

        x0 = 45 + col * (col_width + 30)
        y0 = 160 + row * (row_height + 20)
        x1 = x0 + col_width
        y1 = y0 + row_height

        # Clean Navy Card with Yellow Outline
        draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(10, 42, 80), outline=(255, 199, 44), width=2)

        center_box = (x0 + x1) // 2
        # Text without broken emojis: uses clear abbreviations
        draw.text((center_box, y0 + 30), f"{item['time_str']} | {item['date_str']}", font=f_box_time,
                  fill=(255, 199, 44), anchor="mm")
        draw.text((center_box, y0 + 75), f"{item['temp']:.1f}°C", font=f_box_temp, fill=(255, 255, 255), anchor="mm")
        draw.text((center_box, y0 + 115), item['desc'].title(), font=f_box_desc, fill=(255, 215, 0), anchor="mm")

        # Inner detail text
        d1 = f"Humidity: {item['hum']:.0f}%   |   Wind: {item['wind']:.1f} km/h"
        d2 = f"Rain Prob: {item['prob']:.0f}%   |   Rain: {item['rain']:.1f} mm"
        draw.text((center_box, y0 + 160), d1, font=f_box_detail, fill=(226, 232, 240), anchor="mm")
        draw.text((center_box, y0 + 188), d2, font=f_box_detail, fill=(226, 232, 240), anchor="mm")

    draw.text((W // 2, 1215), "Dhanalakshmi Srinivasan Agriculture College Weather Portal", font=f_foot,
              fill=(255, 199, 44), anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ============================================================
# MAIN EXECUTION
# ============================================================

if not RITU_API_KEY:
    st.error("RITU_API_KEY is not configured in .streamlit/secrets.toml.")
    st.stop()

try:
    history_data = get_ritu_history(history_range)
except requests.exceptions.RequestException as err:
    st.error("Error connecting to Ritu API.")
    st.code(str(err))
    st.stop()

df = history_to_dataframe(history_data)
if df.empty:
    st.error("No observations could be extracted.")
    with st.expander("Show raw API response"):
        st.json(history_data)
    st.stop()

ten_min_df = df.copy()
hourly_df = create_hourly_dataframe(ten_min_df)
daily_df = create_daily_dataframe(hourly_df)
daily_extremes = calculate_daily_extremes(ten_min_df)

current_ist = datetime.now(IST)
target_0845 = current_ist.replace(hour=8, minute=45, second=0, microsecond=0)
if current_ist < target_0845:
    target_0845 -= timedelta(days=1)

nearest_index = (ten_min_df["timestamp_ist"] - target_0845).abs().idxmin()
obs = ten_min_df.loc[nearest_index]

temp = float(obs["temperature"]) if pd.notna(obs["temperature"]) else np.nan
hum = float(obs["humidity"]) if pd.notna(obs["humidity"]) else np.nan
press = float(obs["pressure"]) if pd.notna(obs["pressure"]) else np.nan
w_speed = float(obs["windSpeed"]) if pd.notna(obs["windSpeed"]) else np.nan
w_dir = float(obs["windDirection"]) if pd.notna(obs["windDirection"]) else np.nan

dew = float(calculate_dew_point(temp, hum))
w_kmph = float(w_speed * 3.6) if pd.notna(w_speed) else np.nan
dir_short, dir_long = wind_direction_name(w_dir)

try:
    rain_24h_val, rain_from, rain_to = get_rainfall_24h()
    rain_24h = float(rain_24h_val) if pd.notna(rain_24h_val) else np.nan
except Exception:
    if "rain" in ten_min_df.columns and ten_min_df["rain"].notna().any():
        rain_24h = float(ten_min_df["rain"].sum(min_count=1))
    else:
        rain_24h = np.nan
    rain_from = rain_to = None

rain_display_text = f"{rain_24h:.1f} <small>mm</small>" if pd.notna(rain_24h) else "0.0 <small>mm</small>"
rain_str_raw = f"{rain_24h:.1f} mm" if pd.notna(rain_24h) else "0.0 mm"

# Daily extremes extraction
max_t = float(daily_extremes.get("temp_max", np.nan)) if daily_extremes else np.nan
min_t = float(daily_extremes.get("temp_min", np.nan)) if daily_extremes else np.nan

max_t_time = "N/A"
if daily_extremes and pd.notna(daily_extremes.get("temp_max_time")):
    max_t_time = daily_extremes["temp_max_time"].strftime("%H:%M")

min_t_time = "N/A"
if daily_extremes and pd.notna(daily_extremes.get("temp_min_time")):
    min_t_time = daily_extremes["temp_min_time"].strftime("%H:%M")

max_rh = float(daily_extremes.get("rh_max", np.nan)) if daily_extremes else np.nan
min_rh = float(daily_extremes.get("rh_min", np.nan)) if daily_extremes else np.nan

# Clean date string without "Target:"
time_label_clean = target_0845.strftime('%d %b %Y, %I:%M %p') + " IST"

# ============================================================
# UI RENDER: MORNING STATION OBSERVATION (VERTICAL BRAND CARD)
# ============================================================

render_clean_html('<div class="section-title">🌤️ Morning Station Observation & Extremes</div>')

morning_html = f"""
<div class="morning-card-wrapper">
<div class="morning-card">
    <div class="card-univ-tag">Dhanalakshmi Srinivasan University</div>
    <div class="card-title-main">Daily Weather Summary</div>
    <div class="card-time-pill">{time_label_clean}</div>

    <div class="temp-container">
        <div class="temp-primary">{temp:.1f}°C</div>
        <div style="font-size: 0.88rem; color: #E2E8F0;">Observation at Station: {obs['timestamp_ist'].strftime('%I:%M %p')}</div>
    </div>

    <div class="extremes-vertical">
        <div class="extreme-item">
            <span style="color: #FFB4B4; font-weight: 600;">▲ Max Temp</span><br>
            <strong>{max_t:.1f}°C</strong> <small style="color: #CBD5E1;">({max_t_time})</small>
        </div>
        <div class="extreme-item">
            <span style="color: #BEF5F0; font-weight: 600;">💧 Max RH</span><br>
            <strong>{max_rh:.1f}%</strong>
        </div>
        <div class="extreme-item">
            <span style="color: #B4D7FF; font-weight: 600;">▼ Min Temp</span><br>
            <strong>{min_t:.1f}°C</strong> <small style="color: #CBD5E1;">({min_t_time})</small>
        </div>
        <div class="extreme-item">
            <span style="color: #FFE1EB; font-weight: 600;">☀️ Min RH</span><br>
            <strong>{min_rh:.1f}%</strong>
        </div>
    </div>

    <div class="grid-metrics">
        <div class="metric-item">
            <div class="metric-value">{hum:.1f}%</div>
            <div class="metric-label">Humidity</div>
        </div>
        <div class="metric-item">
            <div class="metric-value">{dew:.1f}°C</div>
            <div class="metric-label">Dew Point</div>
        </div>
        <div class="metric-item">
            <div class="metric-value">{w_kmph:.1f} <small style="font-size:0.75rem;">km/h</small></div>
            <div class="metric-label">{dir_short} Wind</div>
        </div>
        <div class="metric-item">
            <div class="metric-value">{press:.1f} <small style="font-size:0.75rem;">hPa</small></div>
            <div class="metric-label">Pressure</div>
        </div>
        <div class="metric-item metric-item-full">
            <div class="metric-value">{rain_display_text}</div>
            <div class="metric-label">Rainfall (Last 24 Hours)</div>
        </div>
    </div>

    <div class="card-footer-tag">
        Dhanalakshmi Srinivasan Agriculture College • Perambalur
    </div>
</div>
</div>
"""
render_clean_html(morning_html)

# Download Button for the Morning Card Image
morning_card_bytes = generate_morning_card_image(
    time_label_clean, temp, max_t, max_t_time, min_t, min_t_time,
    max_rh, min_rh, hum, dew, w_kmph, dir_short, press, rain_str_raw
)

c_btn_l, c_btn_m, c_btn_r = st.columns([1, 2, 1])
with c_btn_m:
    st.download_button(
        label="📥 Download Today Weather Card (.png)",
        data=morning_card_bytes,
        file_name=f"DSU_Weather_Card_{target_0845.strftime('%Y%m%d')}.png",
        mime="image/png",
        use_container_width=True
    )

# ============================================================
# UI RENDER: 3-HOUR FORECAST FOR 24 HOURS (HORIZONTAL SCROLL)
# ============================================================

render_clean_html('<div class="section-title">🌦️ Weather Forecast – Next 24 Hours (3hr Intervals)</div>')

try:
    forecast_data = get_openweather_forecast()
except Exception:
    st.warning("OpenWeather forecast could not be retrieved.")
    forecast_data = None

if forecast_data:
    forecast_list = forecast_data.get("list", [])[:8]

    if forecast_list:
        cards_html = ""
        forecast_items_for_img = []
        forecast_times, forecast_temps, forecast_probs = [], [], []

        for forecast_item in forecast_list:
            dt_ist = datetime.fromtimestamp(forecast_item["dt"], tz=timezone.utc).astimezone(IST)
            temp_fc = float(forecast_item.get("main", {}).get("temp", 0))
            hum_fc = float(forecast_item.get("main", {}).get("humidity", 0))
            weather_desc = forecast_item.get("weather", [{}])[0].get("description", "—")
            wind_fc = float(forecast_item.get("wind", {}).get("speed", 0)) * 3.6
            prob_fc = float(forecast_item.get("pop", 0)) * 100
            rain_fc = float(forecast_item.get("rain", {}).get("3h", 0))

            forecast_times.append(dt_ist)
            forecast_temps.append(temp_fc)
            forecast_probs.append(prob_fc)

            forecast_items_for_img.append({
                "time_str": dt_ist.strftime("%I:%M %p"),
                "date_str": dt_ist.strftime("%d %b"),
                "temp": temp_fc,
                "desc": weather_desc,
                "hum": hum_fc,
                "wind": wind_fc,
                "prob": prob_fc,
                "rain": rain_fc
            })

            cards_html += f"""
<div class="forecast-card">
    <div class="fc-time">{dt_ist.strftime("%I:%M %p")}</div>
    <div class="fc-date">{dt_ist.strftime("%d %b")}</div>
    <div class="fc-temp">{temp_fc:.1f}°C</div>
    <div class="fc-desc">{weather_desc}</div>
    <div class="fc-detail">
        💧 Hum: {hum_fc:.0f}%<br>
        🌬️ Wind: {wind_fc:.1f} km/h<br>
        🌧️ Rain: {prob_fc:.0f}%<br>
        📏 Vol: {rain_fc:.1f} mm
    </div>
</div>
"""

        forecast_html = f"""
<div class="forecast-section">
    <div style="font-weight: 700; font-size: 1.15rem; margin-bottom: 12px; color: #FFC72C;">
        Daily Weather Summary | Dhanalakshmi Srinivasan University
    </div>
    <div class="forecast-scroll-row">
        {cards_html}
    </div>
</div>
"""
        render_clean_html(forecast_html)
        st.caption("👈 Scroll horizontally on the cards above to see the full 24-hour breakdown.")

        # Download button for Forecast Card Image
        forecast_card_bytes = generate_forecast_image(forecast_items_for_img)

        c_fc_l, c_fc_m, c_fc_r = st.columns([1, 2, 1])
        with c_fc_m:
            st.download_button(
                label="📥 Download 24h Forecast Card (.png)",
                data=forecast_card_bytes,
                file_name=f"DSU_Forecast_Card_{target_0845.strftime('%Y%m%d')}.png",
                mime="image/png",
                use_container_width=True
            )

        # Downloadable forecast trend graph in Navy/Yellow theme
        render_clean_html(
            '<div style="margin-top:20px; font-weight:600; color: #001F3F;">Forecast Trend Chart (Download using the camera icon)</div>')
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=forecast_times,
            y=forecast_temps,
            mode="lines+markers+text",
            text=[f"{t:.1f}°" for t in forecast_temps],
            textposition="top center",
            name="Temperature (°C)",
            line=dict(color="#FFC72C", width=3),
            marker=dict(size=8, color="#FFC72C")
        ))
        fig.add_trace(go.Bar(
            x=forecast_times,
            y=forecast_probs,
            name="Rain Probability (%)",
            yaxis="y2",
            marker_color="rgba(100, 160, 230, 0.45)"
        ))

        fig.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_title="Time (IST)",
            yaxis_title="Temperature (°C)",
            yaxis2=dict(title="Rain Probability (%)", overlaying="y", side="right", range=[0, 100]),
            hovermode="x unified",
            height=350,
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#F8FAFC",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={'displayModeBar': True, 'toImageButtonOptions': {'filename': 'forecast_chart_DSAC'}}
        )

# ============================================================
# HISTORICAL DATA & DOWNLOADS
# ============================================================

render_clean_html('<div class="section-title">📈 Historical Weather Data</div>')

tab1, tab2, tab3 = st.tabs(["10-Minute Observations", "Hourly Means", "Daily Means"])


def plot_history(df_data, x_col, params_list, date_format):
    for column, title, color in params_list:
        fig_hist = go.Figure()
        fig_hist.add_trace(
            go.Scatter(x=df_data[x_col], y=df_data[column], mode="lines", name=title, line=dict(color=color, width=2)))
        fig_hist.update_layout(
            title=title,
            xaxis_title=date_format,
            yaxis_title=title,
            height=280,
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode="x unified",
            plot_bgcolor="#F8FAFC"
        )
        st.plotly_chart(fig_hist, use_container_width=True)


hist_params = [
    ("temperature", "Temperature (°C)", "#001F3F"),
    ("humidity", "Relative Humidity (%)", "#0284C7"),
    ("pressure", "Pressure (hPa)", "#64748B"),
    ("windSpeed", "Wind Speed (m/s)", "#059669"),
    ("rain", "Rainfall (mm)", "#D97706")
]

with tab1:
    plot_history(ten_min_df, "timestamp_ist", hist_params, "Time (IST)")
with tab2:
    plot_history(hourly_df, "timestamp_ist", hist_params, "Time (IST)")
with tab3:
    plot_history(daily_df, "timestamp_ist", hist_params, "Date (IST)")

# ============================================================
# EXPORT
# ============================================================
st.markdown("---")
c1, c2, c3 = st.columns(3)
with c1:
    st.download_button("📥 Download 10-Min CSV", ten_min_df.to_csv(index=False).encode("utf-8"), "dsac_10min.csv",
                       "text/csv", use_container_width=True)
with c2:
    st.download_button("📥 Download Hourly CSV", hourly_df.to_csv(index=False).encode("utf-8"), "dsac_hourly.csv",
                       "text/csv", use_container_width=True)
with c3:
    st.download_button("📥 Download Daily CSV", daily_df.to_csv(index=False).encode("utf-8"), "dsac_daily.csv",
                       "text/csv", use_container_width=True)

st.caption("Dhanalakshmi Srinivasan Agriculture College Weather Portal • Timezone: IST (UTC+05:30)")
