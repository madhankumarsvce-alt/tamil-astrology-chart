from pathlib import Path
# -*- coding: utf-8 -*-
"""
தமிழ் ஜாதகம் / Tamil Kundli Calculator
Features
--------
1. பிறப்பு விவரங்கள்
2. லக்னம் / ராசி / நட்சத்திரம் / பாதம்
3. கிரக நிலைகள் - degree, ராசி, நட்சத்திரம், பாதம்
4. தென் இந்திய முறையில் ராசி கட்டம்
5. நவாம்சம் (D9) கட்டம்
6. விம்சோத்தரி மகாதசை
7. மகாதசை - புத்தி (Bhukti / Antardasha)
8. மகாதசை - புத்தி - அந்தரம் (Pratyantardasha)
9. தற்போதைய மகாதசை / புத்தி / அந்தரம்
10. அனைத்து காலங்களின் தொடக்கம் மற்றும் முடிவு
11. CSV export
"""

import streamlit as st
import streamlit.components.v1 as components
import swisseph as swe
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import pandas as pd
import math
import html


# ------------------------------------------------------------
# BHAVA / ASPECT / YOGA / INTERPRETATION HELPERS
# ------------------------------------------------------------
PLANET_SHORT = {
    "சூரியன்": "சூ",
    "சந்திரன்": "சந்",
    "செவ்வாய்": "செ",
    "புதன்": "பு",
    "குரு": "கு",
    "சுக்கிரன்": "சுக்",
    "சனி": "ச",
    "ராகு": "ரா",
    "கேது": "கே",
}

def house_from_lagna(planet_rasi, lagna_rasi):
    return ((planet_rasi - lagna_rasi) % 12) + 1


def planet_houses(chart):
    lagna_rasi = chart["lagna"]["rasi"]
    result = {}
    for p, x in chart["planets"].items():
        result[p] = house_from_lagna(x["rasi"], lagna_rasi)
    return result


def graha_aspects(chart):
    """
    Traditional Parashari graha drishti:
    - All planets: 7th aspect
    - Mars: 4th and 8th
    - Jupiter: 5th and 9th
    - Saturn: 3rd and 10th
    Rahu/Ketu aspects are kept optional and are not included by default.
    """
    houses = planet_houses(chart)
    out = []

    special = {
        "செவ்வாய்": [4, 7, 8],
        "குரு": [5, 7, 9],
        "சனி": [3, 7, 10],
    }

    for p, h in houses.items():
        aspect_houses = special.get(p, [7])
        for ah in aspect_houses:
            target = ((h - 1 + ah - 1) % 12) + 1
            out.append({
                "கிரகம்": p,
                "இருக்கும் பாவம்": h,
                "பார்வை": f"{ah}ஆம் பார்வை",
                "பார்க்கும் பாவம்": target,
            })
    return pd.DataFrame(out)


def basic_yoga_checks(chart):
    """
    Rule-based traditional checks.
    These are screening indicators, not a complete classical judgement.
    """
    lagna = chart["lagna"]["rasi"]
    houses = planet_houses(chart)

    rasi_lords = {
        0: "செவ்வாய்", 1: "சுக்கிரன்", 2: "புதன்", 3: "சந்திரன்",
        4: "சூரியன்", 5: "புதன்", 6: "சுக்கிரன்", 7: "செவ்வாய்",
        8: "குரு", 9: "சனி", 10: "சனி", 11: "குரு"
    }

    house_lord = {}
    for h in range(1, 13):
        sign = (lagna + h - 1) % 12
        house_lord[h] = rasi_lords[sign]

    findings = []

    # Gaja Kesari: Jupiter and Moon in mutual kendras
    moon_h = houses["சந்திரன்"]
    guru_h = houses["குரு"]
    distance = ((guru_h - moon_h) % 12) + 1
    if distance in [1, 4, 7, 10]:
        findings.append((
            "கஜகேசரி யோக சாத்தியம்",
            "சந்திரன் மற்றும் குரு கேந்திர உறவில் உள்ளனர். "
            "பாரம்பரிய ஜோதிடத்தில் அறிவு, மதிப்பு மற்றும் ஆதரவு தொடர்பான நல்ல குறியீடாக கருதப்படுகிறது."
        ))

    # Budha-Aditya: Sun + Mercury same sign
    if chart["planets"]["சூரியன்"]["rasi"] == chart["planets"]["புதன்"]["rasi"]:
        findings.append((
            "புதாதித்ய யோக சாத்தியம்",
            "சூரியன் மற்றும் புதன் ஒரே ராசியில் உள்ளனர். "
            "புத்திசாலித்தனம், நிர்வாகம் மற்றும் தொடர்புத்திறனுடன் இணைத்து பாரம்பரியமாக பார்க்கப்படுகிறது."
        ))

    # Dharma/Karma lord relationship: 9th and 10th lords same sign
    if house_lord[9] == house_lord[10]:
        findings.append((
            "தர்ம-கர்மாதிபதி தொடர்பு",
            "9ஆம் மற்றும் 10ஆம் பாவ அதிபதிகள் ஒரே கிரகமாக இருப்பது பாரம்பரியமாக கவனிக்கப்படும் அமைப்பு."
        ))
    else:
        p9 = house_lord[9]
        p10 = house_lord[10]
        if houses[p9] == 10 or houses[p10] == 9:
            findings.append((
                "தர்ம-கர்ம தொடர்பு",
                "9ஆம் மற்றும் 10ஆம் பாவ அதிபதிகளுக்கு பரஸ்பர தொடர்பு இருப்பதற்கான சாத்தியம் உள்ளது."
            ))

    # Simple Vipareeta Raja Yoga screening:
    # 6th/8th/12th lords occupying another dusthana.
    dusthana = {6, 8, 12}
    for h in [6, 8, 12]:
        lord = house_lord[h]
        if houses[lord] in dusthana:
            findings.append((
                "விபரீத ராஜயோக சாத்தியம்",
                f"{h}ஆம் பாவ அதிபதி மற்றொரு துஷ்டான பாவத்தில் இருப்பது காணப்படுகிறது."
            ))

    # Neecha screening by classical debilitation signs
    debil = {
        "சூரியன்": 6, "சந்திரன்": 7, "செவ்வாய்": 3,
        "புதன்": 11, "குரு": 9, "சுக்கிரன்": 5, "சனி": 0
    }
    for p, sign in debil.items():
        if chart["planets"][p]["rasi"] == sign:
            findings.append((
                f"{p} நீச நிலை",
                f"{p} {RASI_TA[sign]} ராசியில் இருப்பதால் பாரம்பரிய நீச நிலை குறிக்கப்படுகிறது. "
                "நீசபங்கம் உள்ளதா என்பதை தனியாக பரிசோதிக்க வேண்டும்."
            ))

    if not findings:
        findings.append((
            "முக்கிய யோக screening",
            "தற்போதைய அடிப்படை விதிகளில் குறிப்பிடத்தக்க யோக குறியீடு கண்டறியப்படவில்லை."
        ))

    return findings


def tamil_house_meaning(h):
    meanings = {
        1: "தன்மை, உடல், தனிப்பட்ட முயற்சி",
        2: "குடும்பம், செல்வம், பேச்சு",
        3: "துணிவு, சகோதரர்கள், தொடர்பு",
        4: "தாய், வீடு, சொத்து, மன அமைதி",
        5: "புத்தி, கல்வி, குழந்தைகள், படைப்பாற்றல்",
        6: "வேலை, கடன், நோய், போட்டி",
        7: "திருமணம், கூட்டாண்மை, பொதுமக்கள்",
        8: "மாற்றம், ஆயுள், ஆராய்ச்சி, ரகசியம்",
        9: "தர்மம், அதிர்ஷ்டம், உயர்கல்வி, தந்தை",
        10: "தொழில், பதவி, புகழ், நிர்வாகம்",
        11: "லாபம், நண்பர்கள், ஆசை நிறைவேற்றம்",
        12: "செலவு, வெளிநாடு, ஆன்மிகம், தனிமை",
    }
    return meanings[h]


def current_dasha_tamil_explanation(md, ad, pd):
    if not md or not ad or not pd:
        return "தற்போதைய தசா விவரம் கிடைக்கவில்லை."

    text = (
        f"தற்போது **{md['lord']} மகாதசை – {ad['ad']} புத்தி – {pd['pd']} அந்தரம்** "
        "என்ற காலப்பகுதி இயங்குகிறது. "
        "தசா காலத்தின் பலனை மதிப்பிடும்போது அந்த கிரகங்களின் ராசி, பாவம், "
        "அதிபத்தியம், பார்வை, சேர்க்கை, பலம் மற்றும் நவாம்ச நிலை ஆகியவற்றையும் "
        "ஒன்றாகப் பார்க்க வேண்டும்."
    )
    return text


def build_house_table(chart):
    lagna = chart["lagna"]["rasi"]
    houses = []
    for h in range(1, 13):
        sign = (lagna + h - 1) % 12
        occupants = []
        for p, x in chart["planets"].items():
            if x["rasi"] == sign:
                occupants.append(p)
        houses.append({
            "பாவம்": h,
            "ராசி": RASI_TA[sign],
            "பாவ பொருள்": tamil_house_meaning(h),
            "உள்ள கிரகங்கள்": ", ".join(occupants) if occupants else "-"
        })
    return pd.DataFrame(houses)



# ------------------------------------------------------------
# DIGNITY / COMBUSTION / VARGOTTAMA / TRANSIT HELPERS
# ------------------------------------------------------------
EXALTATION = {
    "சூரியன்": 0, "சந்திரன்": 1, "செவ்வாய்": 9,
    "புதன்": 5, "குரு": 3, "சுக்கிரன்": 11, "சனி": 6
}

DEBILITATION = {
    "சூரியன்": 6, "சந்திரன்": 7, "செவ்வாய்": 3,
    "புதன்": 11, "குரு": 9, "சுக்கிரன்": 5, "சனி": 0
}

OWN_SIGNS = {
    "சூரியன்": [4],
    "சந்திரன்": [3],
    "செவ்வாய்": [0, 7],
    "புதன்": [2, 5],
    "குரு": [8, 11],
    "சுக்கிரன்": [1, 6],
    "சனி": [9, 10],
}

FRIEND_SIGNS = {
    "சூரியன்": [0, 4, 8, 9],
    "சந்திரன்": [0, 2, 3, 4, 5, 8, 11],
    "செவ்வாய்": [0, 3, 4, 8, 9, 11],
    "புதன்": [0, 2, 5, 6, 9, 10],
    "குரு": [0, 3, 4, 8, 11],
    "சுக்கிரன்": [1, 2, 5, 6, 9, 10],
    "சனி": [1, 2, 6, 9, 10],
}

def dignity_of(planet, rasi):
    if planet in EXALTATION and rasi == EXALTATION[planet]:
        return "உச்சம்"
    if planet in DEBILITATION and rasi == DEBILITATION[planet]:
        return "நீசம்"
    if rasi in OWN_SIGNS.get(planet, []):
        return "சுயராசி"
    if rasi in FRIEND_SIGNS.get(planet, []):
        return "நட்பு ராசி"
    return "சமம் / பகை ஆய்வு தேவை"


def is_combust(planet, sun_longitude, planet_longitude):
    if planet in ["சூரியன்", "ராகு", "கேது"]:
        return False

    diff = abs(normalize_deg(planet_longitude - sun_longitude))
    diff = min(diff, 360 - diff)

    # Approximate classical combustion limits.
    limits = {
        "சந்திரன்": 12.0,
        "செவ்வாய்": 17.0,
        "புதன்": 14.0,
        "குரு": 11.0,
        "சுக்கிரன்": 10.0,
        "சனி": 15.0,
    }
    return diff <= limits.get(planet, 0)


def planet_strength_table(chart):
    sun_lon = chart["planets"]["சூரியன்"]["longitude"]
    rows = []

    for p in ["சூரியன்", "சந்திரன்", "செவ்வாய்", "புதன்", "குரு", "சுக்கிரன்", "சனி", "ராகு", "கேது"]:
        x = chart["planets"][p]
        if p in ["ராகு", "கேது"]:
            dignity = "நிழல் கிரகம்"
            combustion = "பொருந்தாது"
        else:
            dignity = dignity_of(p, x["rasi"])
            combustion = "அஸ்தம் / Combust" if is_combust(
                p, sun_lon, x["longitude"]
            ) else "இல்லை"

        d9 = navamsa_sign(x["longitude"])
        vargottama = "வர்க்கோத்தமம்" if d9 == x["rasi"] else "இல்லை"

        rows.append({
            "கிரகம்": p,
            "ராசி": RASI_TA[x["rasi"]],
            "நிலை": dignity,
            "அஸ்தம்": combustion,
            "வக்ரம்": "ஆம்" if x["retro"] else "இல்லை",
            "நவாம்சம்": RASI_TA[d9],
            "வர்க்கோத்தமம்": vargottama
        })

    return pd.DataFrame(rows)


def current_transit_snapshot(chart, tzname):
    """
    Calculates today's sidereal planetary positions using the same
    Lahiri setting as the birth chart.
    """
    now = datetime.now(ZoneInfo(tzname))
    hour_ut = (
        now.astimezone(ZoneInfo("UTC")).hour
        + now.astimezone(ZoneInfo("UTC")).minute / 60
        + now.astimezone(ZoneInfo("UTC")).second / 3600
    )
    utc = now.astimezone(ZoneInfo("UTC"))

    jd = swe.julday(
        utc.year, utc.month, utc.day, hour_ut
    )

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

    rows = []
    for p, pid in PLANET_EN.items():
        result = swe.calc_ut(jd, pid, flags)
        lon = normalize_deg(result[0][0])
        speed = result[0][3]
        rows.append({
            "கிரகம்": p,
            "ராசி": RASI_TA[rasi_index(lon)],
            "பாகை": dms(deg_in_rasi(lon)),
            "நட்சத்திரம்": NAK_TA[nakshatra_info(lon)[0]],
            "வக்ரம்": "ஆம்" if speed < 0 else "இல்லை"
        })

    rahu_lon = rows[-1] if rows else None
    rahu_result = swe.calc_ut(jd, swe.MEAN_NODE, flags)
    rahu_lon_value = normalize_deg(rahu_result[0][0])
    ketu_lon = normalize_deg(rahu_lon_value + 180)

    rows.append({
        "கிரகம்": "கேது",
        "ராசி": RASI_TA[rasi_index(ketu_lon)],
        "பாகை": dms(deg_in_rasi(ketu_lon)),
        "நட்சத்திரம்": NAK_TA[nakshatra_info(ketu_lon)[0]],
        "வக்ரம்": "ஆம்" if rahu_result[0][3] < 0 else "இல்லை"
    })

    return pd.DataFrame(rows), now


def transit_from_moon(chart, transit_df):
    moon_rasi = chart["planets"]["சந்திரன்"]["rasi"]
    rows = []

    for _, row in transit_df.iterrows():
        # Transit sign is obtained from Tamil sign name.
        tr_sign = RASI_TA.index(row["ராசி"])
        house = ((tr_sign - moon_rasi) % 12) + 1

        rows.append({
            "கிரகம்": row["கிரகம்"],
            "கோச்சார ராசி": row["ராசி"],
            "சந்திரனிலிருந்து பாவம்": house,
            "பாரம்பரிய குறிப்பு": tamil_house_meaning(house)
        })

    return pd.DataFrame(rows)


def life_area_summary(chart):
    """
    Conservative rule-based indicators for software display.
    Not a deterministic prediction engine.
    """
    houses = planet_houses(chart)
    lagna = chart["lagna"]["rasi"]

    summaries = []

    # Career: 10th house and its occupants
    tenth_sign = (lagna + 9) % 12
    tenth_occ = [p for p, x in chart["planets"].items() if x["rasi"] == tenth_sign]
    summaries.append({
        "வாழ்க்கை பகுதி": "தொழில் / பதவி",
        "ஆய்வு செய்யப்படும் பாவம்": "10ஆம் பாவம்",
        "உள்ள கிரகங்கள்": ", ".join(tenth_occ) if tenth_occ else "-",
        "குறிப்பு": "10ஆம் பாவம், அதன் அதிபதி, சூரியன், சனி மற்றும் தசா காலங்களை இணைத்து ஆய்வு செய்ய வேண்டும்."
    })

    fifth_sign = (lagna + 4) % 12
    fifth_occ = [p for p, x in chart["planets"].items() if x["rasi"] == fifth_sign]
    summaries.append({
        "வாழ்க்கை பகுதி": "கல்வி / குழந்தைகள் / படைப்பாற்றல்",
        "ஆய்வு செய்யப்படும் பாவம்": "5ஆம் பாவம்",
        "உள்ள கிரகங்கள்": ", ".join(fifth_occ) if fifth_occ else "-",
        "குறிப்பு": "5ஆம் பாவம், குரு, புதன், சந்திரன் மற்றும் D9/D7 போன்ற துணைவர்க்கங்களை இணைத்து ஆய்வு செய்ய வேண்டும்."
    })

    seventh_sign = (lagna + 6) % 12
    seventh_occ = [p for p, x in chart["planets"].items() if x["rasi"] == seventh_sign]
    summaries.append({
        "வாழ்க்கை பகுதி": "திருமணம் / கூட்டாண்மை",
        "ஆய்வு செய்யப்படும் பாவம்": "7ஆம் பாவம்",
        "உள்ள கிரகங்கள்": ", ".join(seventh_occ) if seventh_occ else "-",
        "குறிப்பு": "7ஆம் பாவம், 7ஆம் அதிபதி, சுக்கிரன், குரு, D9 மற்றும் தொடர்புடைய தசா காலங்களை இணைத்து ஆய்வு செய்ய வேண்டும்."
    })

    eleventh_sign = (lagna + 10) % 12
    eleventh_occ = [p for p, x in chart["planets"].items() if x["rasi"] == eleventh_sign]
    summaries.append({
        "வாழ்க்கை பகுதி": "லாபம் / வருமான வாய்ப்பு",
        "ஆய்வு செய்யப்படும் பாவம்": "11ஆம் பாவம்",
        "உள்ள கிரகங்கள்": ", ".join(eleventh_occ) if eleventh_occ else "-",
        "குறிப்பு": "11ஆம் பாவம், 2ஆம் பாவம், அவற்றின் அதிபதிகள் மற்றும் தசா/கோச்சாரத்தை இணைத்து ஆய்வு செய்ய வேண்டும்."
    })

    return pd.DataFrame(summaries)



# ------------------------------------------------------------
# EXPLAINABLE RULE ENGINE
# ------------------------------------------------------------
def kendra_house(h):
    return h in [1, 4, 7, 10]

def trikona_house(h):
    return h in [1, 5, 9]

def dusthana_house(h):
    return h in [6, 8, 12]

def house_lords_for_lagna(lagna_rasi):
    lords = {
        0: "செவ்வாய்", 1: "சுக்கிரன்", 2: "புதன்", 3: "சந்திரன்",
        4: "சூரியன்", 5: "புதன்", 6: "சுக்கிரன்", 7: "செவ்வாய்",
        8: "குரு", 9: "சனி", 10: "சனி", 11: "குரு"
    }
    return {
        h: lords[(lagna_rasi + h - 1) % 12]
        for h in range(1, 13)
    }

def rule_engine(chart):
    """
    Explainable, conservative rule engine.
    Every finding contains:
    விதி -> ஆதாரம் -> முடிவு.
    """
    houses = planet_houses(chart)
    lagna = chart["lagna"]["rasi"]
    hl = house_lords_for_lagna(lagna)
    findings = []

    # Kendra / Trikona occupants
    for p, h in houses.items():
        if kendra_house(h):
            findings.append({
                "பகுதி": "கேந்திர நிலை",
                "விதி": f"{p} கேந்திர பாவத்தில் இருப்பது",
                "ஆதாரம்": f"{p} {h}ஆம் பாவத்தில் உள்ளது",
                "விளக்கம்": "கேந்திர பாவங்கள் ஜாதகத்தின் முக்கிய செயல்பாட்டு பாவங்களாக பாரம்பரியமாக கருதப்படுகின்றன."
            })

    # Trikona occupants
    for p, h in houses.items():
        if trikona_house(h):
            findings.append({
                "பகுதி": "திரிகோண நிலை",
                "விதி": f"{p} திரிகோண பாவத்தில் இருப்பது",
                "ஆதாரம்": f"{p} {h}ஆம் பாவத்தில் உள்ளது",
                "விளக்கம்": "1, 5, 9 பாவங்கள் தர்ம/திரிகோண பாவங்களாக பாரம்பரியமாக கருதப்படுகின்றன."
            })

    # Career rule
    tenth_lord = hl[10]
    tenth_lord_house = houses.get(tenth_lord)
    findings.append({
        "பகுதி": "தொழில்",
        "விதி": "10ஆம் பாவம் + 10ஆம் அதிபதி",
        "ஆதாரம்": f"10ஆம் பாவ அதிபதி {tenth_lord}; அது {tenth_lord_house}ஆம் பாவத்தில் உள்ளது",
        "விளக்கம்": "தொழில் ஆய்வில் 10ஆம் பாவம், அதன் அதிபதி, சூரியன், சனி மற்றும் நடப்பு தசா ஆகியவை இணைந்து பார்க்கப்பட வேண்டும்."
    })

    # Marriage rule
    seventh_lord = hl[7]
    seventh_house = houses.get(seventh_lord)
    findings.append({
        "பகுதி": "திருமணம்",
        "விதி": "7ஆம் பாவம் + 7ஆம் அதிபதி + சுக்கிரன்",
        "ஆதாரம்": f"7ஆம் பாவ அதிபதி {seventh_lord}; அது {seventh_house}ஆம் பாவத்தில் உள்ளது",
        "விளக்கம்": "திருமண ஆய்வில் 7ஆம் பாவம், 7ஆம் அதிபதி, சுக்கிரன், குரு, D9 மற்றும் தசா காலம் இணைந்து பார்க்கப்பட வேண்டும்."
    })

    # Wealth rule
    second_lord = hl[2]
    eleventh_lord = hl[11]
    findings.append({
        "பகுதி": "செல்வம் / லாபம்",
        "விதி": "2ஆம் மற்றும் 11ஆம் பாவங்கள்",
        "ஆதாரம்": f"2ஆம் அதிபதி {second_lord}; 11ஆம் அதிபதி {eleventh_lord}",
        "விளக்கம்": "வருமானம், சேமிப்பு மற்றும் லாபத்திற்கு 2, 5, 9, 11 பாவங்கள் மற்றும் அவற்றின் அதிபதிகள் முக்கியம்."
    })

    return findings


def neecha_bhanga_screening(chart):
    """
    Conservative screening for possible cancellation of debilitation.
    This is deliberately labelled 'சாத்தியம்'; full classical verification
    requires all traditional conditions.
    """
    lagna = chart["lagna"]["rasi"]
    houses = planet_houses(chart)

    rules = {
        "சூரியன்": {"debil": 6, "dispositor": "சுக்கிரன்", "exalt_lord": "சூரியன்"},
        "சந்திரன்": {"debil": 7, "dispositor": "செவ்வாய்", "exalt_lord": "சுக்கிரன்"},
        "செவ்வாய்": {"debil": 3, "dispositor": "புதன்", "exalt_lord": "குரு"},
        "புதன்": {"debil": 11, "dispositor": "சனி", "exalt_lord": "செவ்வாய்"},
        "குரு": {"debil": 9, "dispositor": "சனி", "exalt_lord": "சனி"},
        "சுக்கிரன்": {"debil": 5, "dispositor": "சூரியன்", "exalt_lord": "செவ்வாய்"},
        "சனி": {"debil": 0, "dispositor": "செவ்வாய்", "exalt_lord": "சூரியன்"},
    }

    rows = []
    for p, rule in rules.items():
        x = chart["planets"][p]
        if x["rasi"] != rule["debil"]:
            continue

        dispositor = rule["dispositor"]
        dispositor_house = houses.get(dispositor)

        possible = False
        reasons = []

        if dispositor_house in [1, 4, 7, 10]:
            possible = True
            reasons.append(f"நீச ராசி அதிபதி {dispositor} கேந்திரத்தில் உள்ளது")

        exalt_lord = rule["exalt_lord"]
        exalt_lord_house = houses.get(exalt_lord)
        if exalt_lord_house in [1, 4, 7, 10]:
            possible = True
            reasons.append(f"உச்ச ராசி தொடர்புடைய அதிபதி {exalt_lord} கேந்திரத்தில் உள்ளது")

        rows.append({
            "கிரகம்": p,
            "நீச ராசி": RASI_TA[x["rasi"]],
            "நிலை": "நீசபங்கம் சாத்தியம்" if possible else "முழுமையான நீசபங்க விதி உறுதி செய்யப்படவில்லை",
            "காரணம்": "; ".join(reasons) if reasons else "-"
        })

    if not rows:
        rows.append({
            "கிரகம்": "-",
            "நீச ராசி": "-",
            "நிலை": "பாரம்பரிய நீச நிலையில் கிரகம் இல்லை",
            "காரணம்": "-"
        })

    return pd.DataFrame(rows)


def scoring_summary(chart):
    """
    Educational score only, not a predictive probability.
    """
    houses = planet_houses(chart)
    score = 50
    reasons = []

    for p, h in houses.items():
        if kendra_house(h):
            score += 2
        if trikona_house(h):
            score += 2
        if dusthana_house(h):
            score -= 1

    for p in ["சூரியன்", "சந்திரன்", "செவ்வாய்", "புதன்", "குரு", "சுக்கிரன்", "சனி"]:
        dignity = dignity_of(p, chart["planets"][p]["rasi"])
        if dignity in ["உச்சம்", "சுயராசி"]:
            score += 4
        elif dignity == "நீசம்":
            score -= 4

    score = max(0, min(100, score))

    if score >= 70:
        label = "வலுவான அடிப்படை குறியீடுகள்"
    elif score >= 55:
        label = "மிதமான சாதக குறியீடுகள்"
    else:
        label = "மேலும் ஆழமான ஆய்வு தேவை"

    reasons.append("இந்த score பாரம்பரிய விதிகளை சுருக்கமாக காட்டும் educational indicator மட்டுமே.")

    return score, label, reasons



# ------------------------------------------------------------
# DETAILED LIFE-AREA PREDICTION ENGINE
# ------------------------------------------------------------
def sign_lord(rasi):
    return {
        0: "செவ்வாய்", 1: "சுக்கிரன்", 2: "புதன்", 3: "சந்திரன்",
        4: "சூரியன்", 5: "புதன்", 6: "சுக்கிரன்", 7: "செவ்வாய்",
        8: "குரு", 9: "சனி", 10: "சனி", 11: "குரு"
    }[rasi]


def house_lord_location(chart, house):
    lagna = chart["lagna"]["rasi"]
    sign = (lagna + house - 1) % 12
    lord = sign_lord(sign)
    location = planet_houses(chart)[lord]
    return lord, location


def benefic_score_for_house(chart, target_house):
    houses = planet_houses(chart)
    score = 0
    reasons = []

    benefics = {"குரு", "சுக்கிரன்", "புதன்", "சந்திரன்"}
    malefics = {"சனி", "செவ்வாய்", "சூரியன்", "ராகு", "கேது"}

    for p, h in houses.items():
        if h == target_house:
            if p in benefics:
                score += 2
                reasons.append(f"{p} {target_house}ஆம் பாவத்தில் இருப்பது சாதக குறியீடு")
            elif p in malefics:
                score -= 1
                reasons.append(f"{p} {target_house}ஆம் பாவத்தில் இருப்பது கவனிக்க வேண்டிய குறியீடு")

    lord, lord_house = house_lord_location(chart, target_house)

    if lord_house in [1, 4, 5, 7, 9, 10, 11]:
        score += 2
        reasons.append(f"{target_house}ஆம் பாவ அதிபதி {lord}, {lord_house}ஆம் பாவத்தில் உள்ளது")
    elif lord_house in [6, 8, 12]:
        score -= 1
        reasons.append(f"{target_house}ஆம் பாவ அதிபதி {lord}, {lord_house}ஆம் பாவத்தில் உள்ளது")

    return score, reasons, lord, lord_house


def detailed_area_analysis(chart):
    areas = [
        ("💼 தொழில்", 10,
         "10ஆம் பாவம், 10ஆம் அதிபதி, சூரியன், சனி மற்றும் 10ஆம் பாவத்திற்கான பார்வைகள்."),
        ("💍 திருமணம்", 7,
         "7ஆம் பாவம், 7ஆம் அதிபதி, சுக்கிரன், குரு மற்றும் D9."),
        ("👶 குழந்தைகள் / கல்வி", 5,
         "5ஆம் பாவம், 5ஆம் அதிபதி, குரு மற்றும் எதிர்காலத்தில் D7."),
        ("💰 செல்வம் / லாபம்", 11,
         "11ஆம் பாவம், 11ஆம் அதிபதி, 2ஆம் பாவம் மற்றும் 5/9 தொடர்புகள்."),
        ("🏠 சொத்து / வீடு", 4,
         "4ஆம் பாவம், 4ஆம் அதிபதி, சந்திரன் மற்றும் சொத்து தொடர்பான தசா."),
        ("✈️ வெளிநாடு", 12,
         "12ஆம் பாவம், 12ஆம் அதிபதி, 9ஆம் பாவம் மற்றும் ராகு தொடர்புகள்."),
        ("📚 உயர்கல்வி / அதிர்ஷ்டம்", 9,
         "9ஆம் பாவம், 9ஆம் அதிபதி, குரு மற்றும் உயர்கல்வி தொடர்புகள்."),
        ("🩺 போட்டி / சேவை", 6,
         "6ஆம் பாவம், 6ஆம் அதிபதி, செவ்வாய் மற்றும் சனி தொடர்புகள்.")
    ]

    rows = []

    for title, house, basis in areas:
        score, reasons, lord, lord_house = benefic_score_for_house(
            chart, house
        )

        if score >= 4:
            level = "சாதகமான குறியீடுகள் அதிகம்"
        elif score >= 1:
            level = "மிதமான சாதக குறியீடுகள்"
        elif score == 0:
            level = "கலப்பு நிலை"
        else:
            level = "கவனமாக ஆய்வு செய்ய வேண்டிய நிலை"

        rows.append({
            "வாழ்க்கை பகுதி": title,
            "பாவம்": f"{house}ஆம் பாவம்",
            "பாவ அதிபதி": lord,
            "அதிபதி இருக்கும் பாவம்": lord_house,
            "மதிப்பீட்டு நிலை": level,
            "ஆதார காரணங்கள்": " | ".join(reasons) if reasons else "கூடுதல் ஆய்வு தேவை",
            "ஆய்வு அடிப்படை": basis
        })

    return pd.DataFrame(rows)


def dasha_area_activation(chart, current_md, current_ad, current_pd):
    if not current_md:
        return pd.DataFrame()

    houses = planet_houses(chart)

    rows = []
    lords = [current_md["lord"]]
    if current_ad:
        lords.append(current_ad["ad"])
    if current_pd:
        lords.append(current_pd["pd"])

    for p in lords:
        if p in houses:
            h = houses[p]
            rows.append({
                "தசா கிரகம்": p,
                "ஜாதக பாவம்": h,
                "பாவ பொருள்": tamil_house_meaning(h),
                "தசா செயல்படுத்தும் பகுதி": (
                    "முக்கியமான செயல்பாடு" if h in [1, 5, 9, 10, 11]
                    else "ஆய்வு / மாற்றம் தேவை" if h in [6, 8, 12]
                    else "குடும்ப / உறவு / நடைமுறை வாழ்க்கை"
                )
            })

    return pd.DataFrame(rows)


def generate_tamil_report_text(chart, current_md, current_ad, current_pd, name):
    lagna = chart["lagna"]
    moon = chart["planets"]["சந்திரன்"]

    report = []
    report.append(f"ஜாதக அறிக்கை — {name}")
    report.append("=" * 55)
    report.append("")
    report.append(f"லக்னம் : {RASI_TA[lagna['rasi']]}")
    report.append(f"ஜன்ம ராசி : {RASI_TA[moon['rasi']]}")
    report.append(f"ஜன்ம நட்சத்திரம் : {NAK_TA[moon['nak']]} — {moon['pada']}ஆம் பாதம்")
    report.append("")

    report.append("தற்போதைய விம்சோத்தரி தசா")
    report.append("-" * 40)
    if current_md:
        report.append(f"மகாதசை : {current_md['lord']}")
    if current_ad:
        report.append(f"புத்தி : {current_ad['ad']}")
    if current_pd:
        report.append(f"அந்தரம் : {current_pd['pd']}")
    report.append("")

    report.append("வாழ்க்கை பகுதி ஆய்வு")
    report.append("-" * 40)

    for row in detailed_area_analysis(chart).to_dict("records"):
        report.append(
            f"{row['வாழ்க்கை பகுதி']}: {row['மதிப்பீட்டு நிலை']}"
        )
        report.append(
            f"ஆதாரம்: {row['ஆதார காரணங்கள்']}"
        )

    report.append("")
    report.append(
        "குறிப்பு: இது பாரம்பரிய வேத ஜோதிட விதிகளை அடிப்படையாகக் கொண்ட "
        "ஆய்வு உதவி. உறுதியான எதிர்கால தீர்ப்பாக எடுத்துக்கொள்ளக் கூடாது."
    )

    return "\n".join(report)



# ------------------------------------------------------------
# RESPONSIVE TABLE - NO HORIZONTAL SCROLL
# ------------------------------------------------------------
def display_wrapped_table(df, column_widths=None, font_size=14, **kwargs):
    """
    Render a readable HTML table that wraps long Tamil text.
    Unlike st.dataframe, this table does not create a horizontal
    scrollbar. Long content wraps inside cells.
    """
    if df is None or df.empty:
        st.info("தரவு இல்லை.")
        return

    data = df.copy()

    def cell(v):
        if pd.isna(v):
            return ""
        return html.escape(str(v)).replace("\n", "<br>")

    table_style = """
    <style>
    .wrap-table-container {
        width: 100%;
        overflow-x: visible !important;
        margin: 8px 0 18px 0;
    }
    table.wrap-table {
        width: 100% !important;
        max-width: 100% !important;
        table-layout: fixed !important;
        border-collapse: collapse !important;
        font-family: "Noto Sans Tamil", "Latha", Arial, sans-serif;
        font-size: __FONT__px;
        line-height: 1.45;
        word-break: normal;
        overflow-wrap: anywhere;
    }
    table.wrap-table th {
        background: #f1f3f6;
        color: #52606d;
        font-weight: 700;
        text-align: left;
        vertical-align: middle;
        padding: 9px 8px;
        border: 1px solid #d8dde3;
        white-space: normal !important;
    }
    table.wrap-table td {
        color: #303846;
        vertical-align: top;
        padding: 9px 8px;
        border: 1px solid #d8dde3;
        white-space: normal !important;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    table.wrap-table tr:nth-child(even) td {
        background: #fbfcfd;
    }
    @media (max-width: 900px) {
        table.wrap-table {
            font-size: 12px;
        }
        table.wrap-table th,
        table.wrap-table td {
            padding: 6px 5px;
        }
    }
    </style>
    """.replace("__FONT__", str(font_size))

    widths = ""
    if column_widths:
        widths = "<colgroup>"
        for w in column_widths:
            widths += f"<col style='width:{w};'>"
        widths += "</colgroup>"

    header = "".join(f"<th>{cell(c)}</th>" for c in data.columns)
    body = ""
    for _, row in data.iterrows():
        body += "<tr>" + "".join(f"<td>{cell(v)}</td>" for v in row.tolist()) + "</tr>"

    st.markdown(
        table_style
        + "<div class='wrap-table-container'>"
        + "<table class='wrap-table'>"
        + widths
        + f"<thead><tr>{header}</tr></thead>"
        + f"<tbody>{body}</tbody>"
        + "</table></div>",
        unsafe_allow_html=True
    )



# ------------------------------------------------------------
# PROPERTY / HOME / LAND / RELOCATION / FOREIGN
# ------------------------------------------------------------
def d4_sign(longitude):
    """Traditional Parashari D4 Chaturthamsa sign.
    Four quarters of each sign start from the natal sign and advance by 3 signs.
    """
    ri = rasi_index(longitude)
    deg = deg_in_rasi(longitude)
    n = min(int(deg / 7.5), 3)
    return (ri + n * 3) % 12


def d4_chart_analysis(chart):
    lagna = d4_sign(chart["lagna"]["longitude"])
    placements = [{"வகை": "லக்னம்", "கிரகம்": "லக்னம்", "ராசி": RASI_TA[lagna]}]
    for p, x in chart["planets"].items():
        placements.append({"வகை": "கிரகம்", "கிரகம்": p, "ராசி": RASI_TA[d4_sign(x["longitude"])]})
    houses = {p: house_from_lagna(d4_sign(x["longitude"]), lagna) for p, x in chart["planets"].items()}
    return lagna, placements, houses


def property_core_analysis(chart):
    lagna = chart["lagna"]["rasi"]
    hl = house_lords_for_lagna(lagna)
    houses = planet_houses(chart)
    fourth_lord = hl[4]
    fourth_house = houses.get(fourth_lord, 0)
    occ = [p for p, h in houses.items() if h == 4]
    mars_h = houses.get("செவ்வாய்", 0)
    venus_h = houses.get("சுக்கிரன்", 0)
    moon_h = houses.get("சந்திரன்", 0)
    score = 50
    evidence = []
    if occ:
        score += 5 * len(occ)
        evidence.append("4ஆம் பாவத்தில் " + ", ".join(occ) + " இருப்பது")
    if fourth_house in [1,2,4,5,7,9,10,11]:
        score += 10
        evidence.append(f"4ஆம் அதிபதி {fourth_house}ஆம் பாவத்தில் இருப்பது")
    elif fourth_house in [6,8,12]:
        score -= 10
        evidence.append(f"4ஆம் அதிபதி {fourth_house}ஆம் பாவத்தில் இருப்பது")
    if mars_h in [1,2,4,7,10,11]:
        score += 5
        evidence.append(f"செவ்வாய் {mars_h}ஆம் பாவத்தில் இருப்பது — நிலம்/கட்டிடம் செயல்பாடு")
    if venus_h in [1,4,5,7,9,10,11]:
        score += 5
        evidence.append(f"சுக்கிரன் {venus_h}ஆம் பாவத்தில் இருப்பது — வீட்டு வசதி/சுகம்")
    if moon_h in [1,4,5,7,9,10,11]:
        score += 5
        evidence.append(f"சந்திரன் {moon_h}ஆம் பாவத்தில் இருப்பது — வீடு/இடமாற்றம்")
    score=max(0,min(100,score))
    level="வலுவான சொத்து / வீட்டு ஆதரவு" if score>=70 else ("மிதமான சொத்து / வீட்டு ஆதரவு" if score>=50 else "கூடுதல் ஆய்வு தேவை")
    return {"fourth_lord": fourth_lord, "fourth_house": fourth_house, "occupants": occ,
            "mars_house": mars_h, "venus_house": venus_h, "moon_house": moon_h,
            "score": score, "level": level, "evidence": evidence}


def d4_property_analysis(chart):
    lagna, placements, houses = d4_chart_analysis(chart)
    hl = house_lords_for_lagna(lagna)
    fourth_lord = hl[4]
    fourth_house = houses.get(fourth_lord, 0)
    occ = [p for p,h in houses.items() if h == 4]
    score=50; evidence=[]
    if occ:
        score += 8*len(occ); evidence.append("D4 4ஆம் பாவத்தில் " + ", ".join(occ) + " இருப்பது")
    if fourth_house in [1,2,4,5,7,9,10,11]:
        score += 12; evidence.append(f"D4 4ஆம் அதிபதி {fourth_house}ஆம் பாவத்தில்")
    elif fourth_house in [6,8,12]:
        score -= 12; evidence.append(f"D4 4ஆம் அதிபதி {fourth_house}ஆம் பாவத்தில்")
    score=max(0,min(100,score))
    level="வலுவான D4 ஆதரவு" if score>=70 else ("மிதமான D4 ஆதரவு" if score>=50 else "சவாலான D4 நிலை")
    return {"lagna":lagna,"placements":placements,"houses":houses,"fourth_lord":fourth_lord,
            "fourth_house":fourth_house,"occupants":occ,"score":score,"level":level,"evidence":evidence}


def property_source_screening(chart):
    h=planet_houses(chart); hl=house_lords_for_lagna(chart["lagna"]["rasi"])
    rows=[]
    rules=[
        ("சுய முயற்சியில் வீடு/நிலம்", [1,10,11], ["செவ்வாய்","சூரியன்","சனி"]),
        ("நிலம் / கட்டிடம்", [4,10,11], ["செவ்வாய்","சனி"]),
        ("வீட்டு வசதி / ஆடம்பரம்", [4,7,11], ["சுக்கிரன்","சந்திரன்"]),
        ("பாரம்பரிய / குடும்ப சொத்து", [2,4,8,9], ["குரு","சந்திரன்","சனி"]),
        ("வாகனம் / வசதி", [4,11], ["சுக்கிரன்","சந்திரன்"]),
    ]
    for name, houses_req, planets in rules:
        hits=[p for p in planets if h.get(p) in houses_req]
        lord_hits=[f"{x}ஆம் அதிபதி={hl[x]}" for x in houses_req if h.get(hl[x]) in [1,2,4,5,7,9,10,11]]
        score=min(100,40+15*len(hits)+10*len(lord_hits))
        rows.append({"சொத்து வகை":name,"ஆதார கிரகங்கள்":", ".join(hits) or "-","அதிபதி ஆதாரம்":", ".join(lord_hits) or "-","குறியீடு":score})
    return pd.DataFrame(rows)


def relocation_foreign_analysis(chart):
    h=planet_houses(chart); lagna=chart["lagna"]["rasi"]; hl=house_lords_for_lagna(lagna)
    score=0; evidence=[]
    for p in ["ராகு","கேது"]:
        if h.get(p) in [3,7,9,12]: score+=15; evidence.append(f"{p} {h[p]}ஆம் பாவத்தில்")
    for p in ["சந்திரன்","சுக்கிரன்","குரு"]:
        if h.get(p) in [7,9,12]: score+=8; evidence.append(f"{p} {h[p]}ஆம் பாவத்தில்")
    for house in [9,12]:
        lord=hl[house]
        if h.get(lord) in [3,7,9,12]: score+=12; evidence.append(f"{house}ஆம் அதிபதி {lord} {h[lord]}ஆம் பாவத்தில்")
    if h.get(hl[4]) in [3,7,9,12]: score+=10; evidence.append(f"4ஆம் அதிபதி {hl[4]} {h[hl[4]]}ஆம் பாவத்தில்")
    score=max(0,min(100,score))
    level="வெளியூர் / வெளிநாடு / இடமாற்ற வாய்ப்பு வலுவாக உள்ளது" if score>=60 else ("இடமாற்ற வாய்ப்பு மிதமாக உள்ளது" if score>=35 else "நிலையான வசிப்பிட ஆதாரம் அதிகம்")
    settlement = "நீண்டகால குடியேற்ற சாத்தியம் பார்க்கலாம்" if h.get(hl[4]) in [7,9,12] or h.get(hl[9]) in [9,12] else "மாற்றம்/பயணம் சாத்தியம்; நிரந்தர குடியேற்றத்திற்கு கூடுதல் ஆதாரம் தேவை"
    return {"score":score,"level":level,"settlement":settlement,"evidence":evidence,"ninth_lord":hl[9],"twelfth_lord":hl[12]}


def property_timing_v20(chart, md_list):
    h=planet_houses(chart); hl=house_lords_for_lagna(chart["lagna"]["rasi"])
    relevant={hl[4],hl[2],hl[8],hl[9],hl[11],"செவ்வாய்","சுக்கிரன்","சந்திரன்","குரு","சனி","ராகு"}
    foreign={hl[3],hl[7],hl[9],hl[12],"ராகு","கேது","சந்திரன்","குரு"}
    rows=[]
    for md in md_list:
        lord=md.get("lord","")
        try:
            bhuktis=generate_bhukti(lord, md["start"], md["end"])
        except Exception:
            bhuktis=[]
        for ad in bhuktis:
            adlord=ad.get("ad","")
            prop_score=(18 if lord in relevant else 0)+(14 if adlord in relevant else 0)
            for p in ["செவ்வாய்","சுக்கிரன்","சந்திரன்","குரு"]:
                if adlord==p: prop_score+=8
            foreign_score=(16 if lord in foreign else 0)+(12 if adlord in foreign else 0)
            if prop_score>=25 or foreign_score>=25:
                rows.append({"மகாதசை":lord,"புத்தி":adlord,"தொடக்கம்":tamil_date(ad["start"]),"முடிவு":tamil_date(ad["end"]),
                             "சொத்து குறியீடு":min(100,prop_score),"வெளிநாடு/இடமாற்ற குறியீடு":min(100,foreign_score),
                             "விளக்கம்":"சொத்து/வீடு/நிலம் activation" if prop_score>=foreign_score else "இடமாற்றம்/வெளியூர்/வெளிநாடு activation"})
    return pd.DataFrame(rows)


def property_summary_v20(core,d4,reloc):
    return (f"சொத்து நிலை: {core['level']} (D1 {core['score']}/100); "
            f"D4 நிலை: {d4['level']} ({d4['score']}/100); "
            f"இடமாற்ற/வெளிநாடு நிலை: {reloc['level']} ({reloc['score']}/100).")



# ------------------------------------------------------------
# GOCHARA / TRANSIT + DASHA SYNTHESIS
# ------------------------------------------------------------
def transit_chart_now(tzname="Asia/Kolkata"):
    tz = ZoneInfo(tzname)
    dt = datetime.now(tz)
    return calculate_chart(dt.replace(tzinfo=None), 13.0827, 80.2707, tzname), dt

def transit_house_from_reference(transit_rasi, reference_rasi):
    return ((transit_rasi - reference_rasi) % 12) + 1

def gochara_analysis(chart, transit_chart):
    moon_rasi = chart["planets"]["சந்திரன்"]["rasi"]
    lagna_rasi = chart["lagna"]["rasi"]
    rows=[]
    for p in ["சூரியன்","சந்திரன்","செவ்வாய்","புதன்","குரு","சுக்கிரன்","சனி","ராகு","கேது"]:
        tr = transit_chart["planets"][p]
        rows.append({
            "கிரகம்": p,
            "தற்போதைய ராசி": RASI_TA[tr["rasi"]],
            "சந்திர ராசியிலிருந்து": transit_house_from_reference(tr["rasi"], moon_rasi),
            "லக்னத்திலிருந்து": transit_house_from_reference(tr["rasi"], lagna_rasi),
            "நிலை": "வக்கிரம்" if tr.get("retro") else "நேர்கதி"
        })
    return pd.DataFrame(rows)

def major_transit_screening(chart, transit_chart):
    moon_rasi=chart["planets"]["சந்திரன்"]["rasi"]
    lagna_rasi=chart["lagna"]["rasi"]
    rows=[]
    rules={
        "குரு": ([2,5,7,9,11], "வளர்ச்சி / வாய்ப்பு / ஆதரவு"),
        "சனி": ([3,6,10,11], "முயற்சி / பொறுப்பு / நீண்டகால பலன்"),
        "ராகு": ([3,6,10,11], "திடீர் மாற்றம் / புதிய திசை"),
        "கேது": ([3,6,9,12], "விடுபாடு / ஆன்மிகம் / மாற்றம்")
    }
    for p,(good,meaning) in rules.items():
        h_m=transit_house_from_reference(transit_chart["planets"][p]["rasi"],moon_rasi)
        h_l=transit_house_from_reference(transit_chart["planets"][p]["rasi"],lagna_rasi)
        score=50
        if h_m in good: score+=20
        if h_l in good: score+=15
        score=max(0,min(100,score))
        level="சாதகமான கோச்சார ஆதரவு" if score>=70 else ("மிதமான கோச்சார ஆதரவு" if score>=50 else "கூடுதல் கவனம் தேவை")
        rows.append({"கிரகம்":p,"சந்திர ராசியிலிருந்து பாவம்":h_m,"லக்னத்திலிருந்து பாவம்":h_l,"குறியீடு":score,"மதிப்பீடு":level,"முக்கிய பொருள்":meaning})
    return pd.DataFrame(rows)

def current_dasha_transit_synthesis(chart, current_md, current_ad, transit_chart):
    houses=planet_houses(chart)
    active=[x for x in [current_md.get("lord") if current_md else None, current_ad.get("ad") if current_ad else None] if x]
    rows=[]
    for p in active:
        h=houses.get(p,0)
        tr=transit_chart["planets"].get(p)
        if not tr: continue
        moon_h=transit_house_from_reference(tr["rasi"], chart["planets"]["சந்திரன்"]["rasi"])
        lag_h=transit_house_from_reference(tr["rasi"], chart["lagna"]["rasi"])
        score=50
        if h in [1,2,5,9,10,11]: score+=15
        if moon_h in [2,5,7,9,10,11]: score+=15
        if lag_h in [1,4,5,7,9,10,11]: score+=10
        score=min(100,score)
        rows.append({"தசா கிரகம்":p,"ஜாதக பாவம்":h,"கோச்சார ராசி":RASI_TA[tr["rasi"]],"சந்திரனிலிருந்து":moon_h,"லக்னத்திலிருந்து":lag_h,"ஒருங்கிணைந்த குறியீடு":score,"விளக்கம்":"தசா + கோச்சாரம் இணைந்து செயல்படும் காலம்"})
    return pd.DataFrame(rows)

def gochara_summary_v21(gochara_df, major_df):
    if gochara_df.empty: return "தற்போதைய கோச்சார தரவு இல்லை."
    best=major_df.sort_values("குறியீடு",ascending=False).iloc[0] if not major_df.empty else None
    if best is not None:
        return f"தற்போதைய கோச்சாரத்தில் {best['கிரகம்']} முக்கியமாக {best['மதிப்பீடு']} — குறியீடு {best['குறியீடு']}/100. தசா + கோச்சாரத்தை இணைத்து timing பார்க்க வேண்டும்."
    return "தற்போதைய கோச்சாரத்தை தசா மற்றும் ஜாதக பாவங்களுடன் இணைத்து பார்க்க வேண்டும்."

# ------------------------------------------------------------
# DIVISIONAL CHARTS D7 / D10 / D12
# ------------------------------------------------------------
def varga_sign(longitude, divisions, mode):
    """
    Generic Parashari-style divisional sign calculation for selected Vargas.

    mode:
      D7  : odd sign starts from itself; even sign starts 7th from itself
      D10 : odd sign starts from itself; even sign starts 9th from itself
      D12 : starts from the natal sign for each sign, then advances one sign
    """
    ri = rasi_index(longitude)
    deg = deg_in_rasi(longitude)
    part = 30.0 / divisions
    n = min(int(deg / part), divisions - 1)

    if mode == "D7":
        start = ri if ri % 2 == 0 else (ri + 6) % 12
    elif mode == "D10":
        start = ri if ri % 2 == 0 else (ri + 8) % 12
    elif mode == "D12":
        start = ri
    else:
        start = ri

    return (start + n) % 12


def varga_chart_data(chart, mode):
    planets = chart["planets"]
    if mode == "D7":
        divisions = 7
        title = "சப்தாம்சம் — D7"
    elif mode == "D10":
        divisions = 10
        title = "தசாம்சம் — D10"
    else:
        divisions = 12
        title = "த்வாதசாம்சம் — D12"

    lagna_sign = varga_sign(chart["lagna"]["longitude"], divisions, mode)

    rows = [{
        "வகை": "லக்னம்",
        "கிரகம்": "லக்னம்",
        "வகுப்பு ராசி": RASI_TA[lagna_sign]
    }]

    placements = [{
        "rasi": lagna_sign,
        "text": "லக்னம்"
    }]

    for p in ["சூரியன்", "சந்திரன்", "செவ்வாய்", "புதன்",
              "குரு", "சுக்கிரன்", "சனி", "ராகு", "கேது"]:
        sign = varga_sign(planets[p]["longitude"], divisions, mode)
        rows.append({
            "வகை": "கிரகம்",
            "கிரகம்": p,
            "வகுப்பு ராசி": RASI_TA[sign]
        })
        placements.append({
            "rasi": sign,
            "planet": p
        })

    return title, pd.DataFrame(rows), placements


def highlight_current_dasha_table(data, current_lord):
    if data is None or data.empty or not current_lord:
        return data

    # Return unchanged dataframe; visual highlighting is handled
    # through a Streamlit dataframe style.
    return data


def dasha_style(row, current_lord):
    styles = []
    for value in row:
        if str(value) == str(current_lord):
            styles.append("font-weight:700; background-color:#fff1b8;")
        else:
            styles.append("")
    return styles



# ------------------------------------------------------------
# ADVANCED BALA / YOGA / ASHTAKAVARGA DIAGNOSTICS
# ------------------------------------------------------------
NATURAL_STRENGTH = {
    "சூரியன்": 60,
    "சந்திரன்": 51,
    "செவ்வாய்": 17,
    "புதன்": 26,
    "குரு": 34,
    "சுக்கிரன்": 43,
    "சனி": 9,
}

DIRECTIONAL_HOUSES = {
    "சூரியன்": 10,
    "செவ்வாய்": 10,
    "சந்திரன்": 4,
    "சுக்கிரன்": 4,
    "புதன்": 1,
    "குரு": 1,
    "சனி": 7,
}

def qualitative_bala_table(chart):
    """
    Practical diagnostic version of Bala.
    It deliberately does not claim to be a complete classical Shadbala
    computation because Kala Bala and several sub-components require
    additional astronomical inputs and traditional conventions.
    """
    houses = planet_houses(chart)
    rows = []

    for p in ["சூரியன்", "சந்திரன்", "செவ்வாய்", "புதன்",
              "குரு", "சுக்கிரன்", "சனி"]:

        x = chart["planets"][p]
        h = houses[p]
        dignity = dignity_of(p, x["rasi"])

        dignity_score = {
            "உச்சம்": 5,
            "சுயராசி": 4,
            "நட்பு ராசி": 3,
            "சமம் / பகை ஆய்வு தேவை": 2,
            "நீசம்": 1
        }.get(dignity, 2)

        digbala = "ஆம்" if h == DIRECTIONAL_HOUSES[p] else "இல்லை"
        natural = NATURAL_STRENGTH[p]

        motion = "வக்ரம்" if x["retro"] else "நேர்கதி"
        motion_score = 2 if x["retro"] else 1

        total_indicator = dignity_score * 10 + natural / 10 + motion_score * 5

        rows.append({
            "கிரகம்": p,
            "ஸ்தான பல குறியீடு": dignity,
            "திக் பலம்": digbala,
            "இயக்க நிலை": motion,
            "இயற்கை பலம்": natural,
            "மொத்த குறியீடு": round(total_indicator, 1)
        })

    return pd.DataFrame(rows)


# A compact, transparent Ashtakavarga-style support indicator.
# This is intentionally labelled an indicator rather than a full
# bindu-for-bindu classical calculation.
ASHTA_SUPPORT = {
    "சூரியன்": [1, 2, 4, 7, 8, 9, 10, 11],
    "சந்திரன்": [1, 3, 6, 7, 10, 11],
    "செவ்வாய்": [1, 3, 6, 10, 11],
    "புதன்": [1, 2, 4, 6, 8, 10, 11],
    "குரு": [1, 2, 4, 5, 7, 9, 10, 11],
    "சுக்கிரன்": [1, 2, 3, 4, 5, 8, 9, 11],
    "சனி": [3, 5, 6, 10, 11],
}

def ashtakavarga_indicator(chart):
    """
    Generates a transparent sign-wise support indicator from the
    traditional favourable-house lists for each of the seven visible
    planets, measured from each planet's natal sign.
    """
    rows = []

    for sign in range(12):
        bindu = 0
        contributors = []

        for p, fav_houses in ASHTA_SUPPORT.items():
            source_sign = chart["planets"][p]["rasi"]
            relative_house = ((sign - source_sign) % 12) + 1
            if relative_house in fav_houses:
                bindu += 1
                contributors.append(p)

        rows.append({
            "ராசி": RASI_TA[sign],
            "ஆதரவு புள்ளிகள்": bindu,
            "ஆதரவு கிரகங்கள்": ", ".join(contributors) if contributors else "-"
        })

    return pd.DataFrame(rows)


def advanced_yoga_engine(chart):
    houses = planet_houses(chart)
    lagna = chart["lagna"]["rasi"]
    hl = house_lords_for_lagna(lagna)

    rows = []

    def add(name, status, evidence, interpretation):
        rows.append({
            "யோகம் / விதி": name,
            "நிலை": status,
            "ஆதாரம்": evidence,
            "பாரம்பரிய விளக்கம்": interpretation
        })

    # Gaja Kesari
    mh = houses["சந்திரன்"]
    jh = houses["குரு"]
    if ((jh - mh) % 12) in [0, 3, 6, 9]:
        add(
            "கஜகேசரி யோக சாத்தியம்",
            "காணப்படுகிறது",
            f"சந்திரன் {mh}ஆம் பாவம்; குரு {jh}ஆம் பாவம்",
            "சந்திரன்–குரு கேந்திர உறவு அறிவு, ஆதரவு மற்றும் மதிப்புடன் தொடர்புபடுத்தப்படுகிறது."
        )
    else:
        add(
            "கஜகேசரி யோக சாத்தியம்",
            "காணப்படவில்லை",
            f"சந்திரன் {mh}ஆம் பாவம்; குரு {jh}ஆம் பாவம்",
            "முழுமையான கஜகேசரி அமைப்பிற்கான கேந்திர உறவு இல்லை."
        )

    # Budha Aditya
    if chart["planets"]["சூரியன்"]["rasi"] == chart["planets"]["புதன்"]["rasi"]:
        add(
            "புதாதித்ய யோகம்",
            "காணப்படுகிறது",
            "சூரியன் மற்றும் புதன் ஒரே ராசியில் உள்ளனர்",
            "அறிவு, நிர்வாகம் மற்றும் தொடர்புத்திறனுடன் பாரம்பரியமாக இணைக்கப்படுகிறது."
        )
    else:
        add(
            "புதாதித்ய யோகம்",
            "காணப்படவில்லை",
            "சூரியன் மற்றும் புதன் வெவ்வேறு ராசிகளில் உள்ளனர்",
            "முழுமையான சேர்க்கை இல்லை."
        )

    # Raja Yoga screening: 5th/9th lords connected with 1/4/7/10 lords by placement.
    kendra_lords = {hl[h] for h in [1, 4, 7, 10]}
    trikona_lords = {hl[h] for h in [1, 5, 9]}
    connected = []

    for p in trikona_lords:
        if p in houses and houses[p] in [1, 4, 7, 10]:
            connected.append(p)

    if connected:
        add(
            "ராஜயோக screening",
            "சாத்தியம்",
            "திரிகோண அதிபதி கேந்திர பாவத்தில் உள்ளது",
            f"{', '.join(connected)} போன்ற அதிபதிகளின் கேந்திர நிலை அதிகாரம்/முன்னேற்றத்திற்கான சாதக குறியீடாக பார்க்கப்படுகிறது."
        )
    else:
        add(
            "ராஜயோக screening",
            "மேலும் ஆய்வு தேவை",
            "எளிய கேந்திர-திரிகோண விதியில் நேரடி அமைப்பு இல்லை",
            "முழுமையான ராஜயோக ஆய்விற்கு சேர்க்கை, பார்வை, பரிவர்த்தனை மற்றும் தசா தேவை."
        )

    # Dhana Yoga screening: 2/5/9/11 lord relationship by same house.
    dhana_lords = [hl[2], hl[5], hl[9], hl[11]]
    dhana_connections = []
    for i, p1 in enumerate(dhana_lords):
        for p2 in dhana_lords[i + 1:]:
            if p1 in houses and p2 in houses and houses[p1] == houses[p2]:
                dhana_connections.append(f"{p1}-{p2}")

    if dhana_connections:
        add(
            "தன யோக screening",
            "சாத்தியம்",
            "2/5/9/11 பாவ அதிபதிகளில் ஒரே பாவ அமைப்பு உள்ளது",
            "செல்வம், சேமிப்பு மற்றும் லாபத்திற்கான தொடர்பாக பாரம்பரியமாக ஆய்வு செய்யப்படுகிறது."
        )
    else:
        add(
            "தன யோக screening",
            "மேலும் ஆய்வு தேவை",
            "எளிய same-house விதி கிடைக்கவில்லை",
            "பார்வை, பரிவர்த்தனை, உச்சம்/சுயராசி மற்றும் தசா ஆகியவற்றையும் சேர்த்து பார்க்க வேண்டும்."
        )

    return pd.DataFrame(rows)


def dasha_yoga_activation(chart, current_md, current_ad, current_pd):
    if not current_md:
        return pd.DataFrame()

    active = [current_md["lord"]]
    if current_ad:
        active.append(current_ad["ad"])
    if current_pd:
        active.append(current_pd["pd"])

    houses = planet_houses(chart)
    rows = []

    for p in active:
        if p not in houses:
            continue
        h = houses[p]
        rows.append({
            "தசா கிரகம்": p,
            "ஜாதக பாவம்": h,
            "குறிப்பிடத்தக்க நிலை": (
                "கேந்திரம்" if kendra_house(h)
                else "திரிகோணம்" if trikona_house(h)
                else "துஷ்டானம்" if dusthana_house(h)
                else "மற்ற பாவம்"
            ),
            "வாழ்க்கை தொடர்பு": tamil_house_meaning(h)
        })

    return pd.DataFrame(rows)


# ------------------------------------------------------------
# SPECIALIZED LIFE-AREA ANALYSIS + TIMING WINDOWS
# ------------------------------------------------------------
def planet_in_houses(chart, target_houses):
    houses = planet_houses(chart)
    return [p for p, h in houses.items() if h in target_houses]


def specialized_area_engine(chart):
    """
    Transparent rule-based indicators for major life areas.
    These are not deterministic predictions.
    """
    houses = planet_houses(chart)
    lagna = chart["lagna"]["rasi"]
    hl = house_lords_for_lagna(lagna)

    definitions = [
        ("திருமணம்", [7], ["சுக்கிரன்", "குரு"], [1, 5, 7, 9, 11]),
        ("தொழில்", [10], ["சூரியன்", "சனி", "புதன்"], [1, 6, 10, 11]),
        ("செல்வம்", [2, 11], ["குரு", "சுக்கிரன்", "புதன்"], [2, 5, 9, 11]),
        ("குழந்தைகள்", [5], ["குரு", "சந்திரன்"], [1, 5, 9, 11]),
        ("சொத்து", [4], ["சந்திரன்", "செவ்வாய்", "சுக்கிரன்"], [1, 4, 10, 11]),
        ("வெளிநாடு", [9, 12], ["ராகு", "சந்திரன்"], [3, 9, 12]),
    ]

    rows = []

    for area, key_houses, key_planets, favourable_houses in definitions:
        score = 0
        evidence = []

        # Occupants
        for p, h in houses.items():
            if h in key_houses:
                if p in key_planets or p == "குரு":
                    score += 2
                    evidence.append(f"{p} {h}ஆம் பாவத்தில்")
                elif p in ["சனி", "செவ்வாய்", "ராகு", "கேது", "சூரியன்"]:
                    score -= 1
                    evidence.append(f"{p} {h}ஆம் பாவத்தில்")

        # Lords
        for h in key_houses:
            lord = hl[h]
            lord_h = houses[lord]
            if lord_h in favourable_houses:
                score += 2
                evidence.append(f"{h}ஆம் பாவ அதிபதி {lord}, {lord_h}ஆம் பாவத்தில்")
            elif lord_h in [6, 8, 12]:
                score -= 1
                evidence.append(f"{h}ஆம் பாவ அதிபதி {lord}, {lord_h}ஆம் பாவத்தில்")

        if score >= 5:
            level = "வலுவான சாதக குறியீடு"
        elif score >= 2:
            level = "சாதக குறியீடு"
        elif score >= 0:
            level = "கலப்பு நிலை"
        else:
            level = "கூடுதல் ஆய்வு தேவை"

        rows.append({
            "வாழ்க்கை பகுதி": area,
            "மதிப்பீடு": level,
            "குறியீடு": score,
            "ஆதாரம்": " | ".join(evidence) if evidence else "-"
        })

    return pd.DataFrame(rows)


def dasha_timing_windows(chart, md_list, area_houses, area_planets, years_ahead=12):
    """
    Lists Mahadasha/Bhukti periods in the requested future horizon
    where the dasha lords activate the relevant houses or planets.
    """
    now = datetime.now(chart["datetime_local"].tzinfo)
    horizon = add_years_days(now, years_ahead)
    houses = planet_houses(chart)

    rows = []

    for md in md_list:
        if md["end"] < now or md["start"] > horizon:
            continue

        bhuktis = generate_bhukti(md["lord"], md["start"], md["end"])

        for ad in bhuktis:
            if ad["end"] < now or ad["start"] > horizon:
                continue

            active = [md["lord"], ad["ad"]]
            score = 0
            reasons = []

            for p in active:
                if p in houses:
                    h = houses[p]
                    if h in area_houses:
                        score += 2
                        reasons.append(f"{p} → {h}ஆம் பாவம்")
                    if p in area_planets:
                        score += 1
                        reasons.append(f"{p} முக்கிய காரக கிரகம்")

            if score > 0:
                rows.append({
                    "மகாதசை": md["lord"],
                    "புத்தி": ad["ad"],
                    "தொடக்கம்": date_only(ad["start"]),
                    "முடிவு": date_only(ad["end"]),
                    "செயல்பாட்டு குறியீடு": score,
                    "ஆதாரம்": " | ".join(reasons)
                })

    if not rows:
        return pd.DataFrame(columns=[
            "மகாதசை", "புத்தி", "தொடக்கம்", "முடிவு",
            "செயல்பாட்டு குறியீடு", "ஆதாரம்"
        ])

    return pd.DataFrame(rows).sort_values(
        ["செயல்பாட்டு குறியீடு", "தொடக்கம்"],
        ascending=[False, True]
    )


def marriage_timing_table(chart, md_list):
    return dasha_timing_windows(
        chart, md_list,
        area_houses=[7, 2, 11],
        area_planets=["சுக்கிரன்", "குரு"],
        years_ahead=15
    )


def career_timing_table(chart, md_list):
    return dasha_timing_windows(
        chart, md_list,
        area_houses=[6, 10, 11],
        area_planets=["சூரியன்", "சனி", "புதன்"],
        years_ahead=15
    )


def finance_timing_table(chart, md_list):
    return dasha_timing_windows(
        chart, md_list,
        area_houses=[2, 5, 9, 11],
        area_planets=["குரு", "சுக்கிரன்", "புதன்"],
        years_ahead=15
    )


def children_timing_table(chart, md_list):
    return dasha_timing_windows(
        chart, md_list,
        area_houses=[5, 9, 11],
        area_planets=["குரு", "சந்திரன்"],
        years_ahead=15
    )


def property_timing_table(chart, md_list):
    return dasha_timing_windows(
        chart, md_list,
        area_houses=[4, 10, 11],
        area_planets=["சந்திரன்", "செவ்வாய்", "சுக்கிரன்"],
        years_ahead=15
    )


def foreign_timing_table(chart, md_list):
    return dasha_timing_windows(
        chart, md_list,
        area_houses=[3, 9, 12],
        area_planets=["ராகு", "சந்திரன்"],
        years_ahead=15
    )



# ------------------------------------------------------------
# PROFESSIONAL REPORT / EXPORT HELPERS
# ------------------------------------------------------------
def build_complete_report_sections(
    chart, name, gender, full_address, md_list, current_md, current_ad, current_pd,
    specialized_df, yoga_df, strength_df
):
    lagna = chart["lagna"]
    moon = chart["planets"]["சந்திரன்"]

    lines = []
    lines.append("தமிழ் ஜாதக முழுமையான அறிக்கை")
    lines.append("=" * 70)
    lines.append(f"பெயர்: {name}")
    lines.append(f"பிறப்பு: {chart['datetime_local'].strftime('%d-%m-%Y %H:%M')}")
    lines.append("")
    lines.append("2. முக்கிய ஜாதக விவரங்கள் / பிறப்பு & பஞ்சாங்க தகவல்கள்")
    lines.append("-" * 65)
    for label, value in detailed_birth_info(
        chart, name, gender, chart.get("latitude", 0.0), chart.get("longitude", 0.0),
        chart.get("tzname", "Asia/Kolkata"), full_address
    ):
        lines.append(f"{label}: {value}")
    lines.append(f"லக்ன நட்சத்திரம்: {NAK_TA[lagna['nak']]} - {lagna['pada']}ஆம் பாதம்")
    lines.append("")

    lines.append("தற்போதைய விம்சோத்தரி தசா")
    lines.append("-" * 50)
    if current_md:
        lines.append(
            f"மகாதசை: {current_md['lord']} "
            f"({date_only(current_md['start'])} - {date_only(current_md['end'])})"
        )
    if current_ad:
        lines.append(
            f"புத்தி: {current_ad['ad']} "
            f"({date_only(current_ad['start'])} - {date_only(current_ad['end'])})"
        )
    if current_pd:
        lines.append(
            f"அந்தரம்: {current_pd['pd']} "
            f"({date_only(current_pd['start'])} - {date_only(current_pd['end'])})"
        )
    lines.append("")

    lines.append("வாழ்க்கை பகுதி Rule Engine")
    lines.append("-" * 50)
    for row in specialized_df.to_dict("records"):
        lines.append(
            f"{row['வாழ்க்கை பகுதி']}: {row['மதிப்பீடு']} "
            f"(குறியீடு {row['குறியீடு']})"
        )
        lines.append(f"ஆதாரம்: {row['ஆதாரம்']}")
    lines.append("")

    lines.append("யோக ஆய்வு")
    lines.append("-" * 50)
    for row in yoga_df.to_dict("records"):
        lines.append(
            f"{row['யோகம் / விதி']}: {row['நிலை']}"
        )
        lines.append(f"ஆதாரம்: {row['ஆதாரம்']}")
        lines.append(f"விளக்கம்: {row['பாரம்பரிய விளக்கம்']}")
    lines.append("")

    lines.append("கிரக பல diagnostic")
    lines.append("-" * 50)
    for row in strength_df.to_dict("records"):
        # accept either the detailed diagnostic table ()
        # or the earlier dignity table () so report generation
        # cannot fail because of a column-name mismatch.
        strength_status = row.get(
            "ஸ்தான பல குறியீடு",
            row.get("நிலை", row.get("ஸ்தான நிலை", "-"))
        )
        digbala = row.get("திக் பலம்", "-")
        motion = row.get("இயக்க நிலை", row.get("வக்ரம்", "-"))
        total = row.get("மொத்த குறியீடு", row.get("மதிப்பீடு", "-"))

        lines.append(
            f"{row.get('கிரகம்', '-')}: {strength_status}; "
            f"திக் பலம்={digbala}; "
            f"இயக்கம்={motion}; "
            f"குறியீடு={total}"
        )

    lines.append("")
    lines.append("முக்கிய குறிப்பு")
    lines.append("-" * 50)
    lines.append(
        "இந்த அறிக்கை பாரம்பரிய வேத ஜோதிட கணக்கீடு மற்றும் rule-based "
        "analysis உதவிக்காக உருவாக்கப்பட்டுள்ளது. இது உறுதியான எதிர்கால "
        "தீர்ப்பு அல்லது மருத்துவம், சட்டம், முதலீடு போன்ற துறைகளுக்கான "
        "தொழில்முறை ஆலோசனை அல்ல."
    )

    return "\n".join(lines)


def create_pdf_report(report_text, filename="tamil_jathaga_report.pdf"):
    """
    Create a Unicode Tamil PDF using ReportLab's built-in Tamil CID font.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from xml.sax.saxutils import escape

    # Prefer a real installed Tamil Unicode font on Windows.
    font_candidates = [
        r"C:\Windows\Fonts\Nirmala.ttf",
        r"C:\Windows\Fonts\NirmalaUI.ttf",
        r"C:\Windows\Fonts\Latha.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansTamil-Regular.ttf",
    ]

    font_path = next((f for f in font_candidates if Path(f).exists()), None)

    if font_path is None:
        raise RuntimeError(
            "Tamil Unicode font கிடைக்கவில்லை. Windows-ல் Nirmala UI அல்லது Latha "
            "font install செய்யப்பட்டுள்ளதா என்பதை சரிபார்க்கவும்."
        )

    font_name = "TamilUnicodeFont"
    pdfmetrics.registerFont(TTFont(font_name, font_path))

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TamilTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        leading=24,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    body_style = ParagraphStyle(
        "TamilBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=10.5,
        leading=16,
        spaceAfter=5
    )

    story = []
    first = True

    for raw_line in report_text.splitlines():
        line = raw_line.strip()

        if not line:
            story.append(Spacer(1, 5))
            continue

        if first:
            story.append(Paragraph(escape(line), title_style))
            first = False
        elif set(line) == {"="} or set(line) == {"-"}:
            story.append(Spacer(1, 3))
        else:
            story.append(Paragraph(escape(line), body_style))

    doc.build(story)
    return filename



# ------------------------------------------------------------
# BHAVA LORD / ASPECT / KARAKA MATRIX
# ------------------------------------------------------------
def aspect_rules_for_planet(planet):
    rules = {
        "செவ்வாய்": [4, 7, 8],
        "குரு": [5, 7, 9],
        "சனி": [3, 7, 10],
        "சூரியன்": [7],
        "சந்திரன்": [7],
        "புதன்": [7],
        "சுக்கிரன்": [7],
        "ராகு": [7],
        "கேது": [7],
    }
    return rules.get(planet, [7])


def house_aspect_target(source_house, aspect_distance):
    return ((source_house - 1 + aspect_distance - 1) % 12) + 1


def planetary_aspect_matrix(chart):
    houses = planet_houses(chart)
    rows = []

    for p in ["சூரியன்", "சந்திரன்", "செவ்வாய்", "புதன்",
              "குரு", "சுக்கிரன்", "சனி", "ராகு", "கேது"]:

        source = houses[p]
        distances = aspect_rules_for_planet(p)

        for distance in distances:
            target = house_aspect_target(source, distance)
            rows.append({
                "கிரகம்": p,
                "இருக்கும் பாவம்": source,
                "பார்வை": f"{distance}ஆம் பார்வை",
                "பார்வை செல்லும் பாவம்": target,
                "பாவ பொருள்": tamil_house_meaning(target)
            })

    return pd.DataFrame(rows)


def bhava_lord_matrix(chart):
    lagna = chart["lagna"]["rasi"]
    hl = house_lords_for_lagna(lagna)
    houses = planet_houses(chart)

    occupants = {h: [] for h in range(1, 13)}
    for p, h in houses.items():
        occupants[h].append(p)

    rows = []
    for h in range(1, 13):
        sign = (lagna + h - 1) % 12
        lord = hl[h]
        lord_house = houses[lord]

        rows.append({
            "பாவம்": f"{h}ஆம் பாவம்",
            "ராசி": RASI_TA[sign],
            "பாவ அதிபதி": lord,
            "அதிபதி இருக்கும் பாவம்": lord_house,
            "உள்ள கிரகங்கள்": ", ".join(occupants[h]) if occupants[h] else "-",
            "பாவ பொருள்": tamil_house_meaning(h)
        })

    return pd.DataFrame(rows)


def karaka_matrix(chart):
    rows = [
        ("சூரியன்", "ஆத்மா / தந்தை / அதிகாரம்", "10ஆம் பாவம் / பதவி ஆய்விலும் முக்கியம்"),
        ("சந்திரன்", "மனம் / தாய் / உணர்வு", "4ஆம் பாவம் / மன அமைதி"),
        ("செவ்வாய்", "துணிவு / சகோதரர் / நிலம்", "3ஆம் மற்றும் 4ஆம் பாவ ஆய்வு"),
        ("புதன்", "புத்தி / கல்வி / வணிகம்", "5ஆம் மற்றும் 10ஆம் பாவ ஆய்வு"),
        ("குரு", "ஞானம் / குழந்தைகள் / தர்மம்", "5ஆம் மற்றும் 9ஆம் பாவ ஆய்வு"),
        ("சுக்கிரன்", "திருமணம் / கலை / வசதி", "7ஆம் மற்றும் 4ஆம் பாவ ஆய்வு"),
        ("சனி", "வேலை / தாமதம் / பொறுப்பு", "6ஆம் மற்றும் 10ஆம் பாவ ஆய்வு"),
        ("ராகு", "அசாதாரணம் / வெளிநாடு / விரிவாக்கம்", "3, 9, 12 தொடர்பு ஆய்வு"),
        ("கேது", "ஆன்மிகம் / பிரிவு / உள்ளார்ந்த தேடல்", "8, 9, 12 தொடர்பு ஆய்வு"),
    ]

    houses = planet_houses(chart)
    out = []

    for p, role, usage in rows:
        out.append({
            "கிரகம்": p,
            "பாவத்தில்": houses.get(p, "-"),
            "முக்கிய காரகத்துவம்": role,
            "ஆய்வில் பயன்பாடு": usage
        })

    return pd.DataFrame(out)


def house_strength_overview(chart):
    houses = planet_houses(chart)
    lagna = chart["lagna"]["rasi"]
    hl = house_lords_for_lagna(lagna)

    rows = []

    for h in range(1, 13):
        lord = hl[h]
        lord_house = houses[lord]
        occupants = [p for p, ph in houses.items() if ph == h]

        score = 0
        evidence = []

        if lord_house in [1, 4, 5, 7, 9, 10, 11]:
            score += 2
            evidence.append(f"அதிபதி {lord_house}ஆம் பாவத்தில்")
        elif lord_house in [6, 8, 12]:
            score -= 1
            evidence.append(f"அதிபதி {lord_house}ஆம் பாவத்தில்")

        for p in occupants:
            if p in ["குரு", "சுக்கிரன்", "புதன்", "சந்திரன்"]:
                score += 1
                evidence.append(f"{p} இருப்பு")
            elif p in ["சனி", "செவ்வாய்", "ராகு", "கேது"]:
                score -= 0.5
                evidence.append(f"{p} இருப்பு")

        if score >= 3:
            level = "வலுவான குறியீடு"
        elif score >= 1:
            level = "சாதக குறியீடு"
        elif score >= 0:
            level = "கலப்பு"
        else:
            level = "கூடுதல் ஆய்வு தேவை"

        rows.append({
            "பாவம்": f"{h}ஆம்",
            "ராசி": RASI_TA[(lagna + h - 1) % 12],
            "அதிபதி": lord,
            "அதிபதி நிலை": lord_house,
            "உள்ள கிரகங்கள்": ", ".join(occupants) if occupants else "-",
            "மதிப்பீடு": level,
            "ஆதாரம்": " | ".join(evidence)
        })

    return pd.DataFrame(rows)



# ------------------------------------------------------------
# COMPLETE MARRIAGE ANALYSIS ENGINE
# ------------------------------------------------------------
def d9_planet_houses(chart):
    d9_lagna = navamsa_sign(chart["lagna"]["longitude"])
    result = {}
    for p, x in chart["planets"].items():
        d9_rasi = navamsa_sign(x["longitude"])
        result[p] = house_from_lagna(d9_rasi, d9_lagna)
    return d9_lagna, result


def marriage_core_analysis(chart):
    lagna = chart["lagna"]["rasi"]
    hl = house_lords_for_lagna(lagna)
    houses = planet_houses(chart)

    seventh_sign = (lagna + 6) % 12
    seventh_lord = hl[7]
    seventh_lord_house = houses[seventh_lord]

    occupants = [p for p, h in houses.items() if h == 7]

    venus_house = houses["சுக்கிரன்"]
    jupiter_house = houses["குரு"]

    score = 0
    evidence = []

    # 7th lord placement
    if seventh_lord_house in [1, 2, 5, 7, 9, 10, 11]:
        score += 2
        evidence.append(f"7ஆம் அதிபதி {seventh_lord} {seventh_lord_house}ஆம் பாவத்தில்")
    elif seventh_lord_house in [6, 8, 12]:
        score -= 1
        evidence.append(f"7ஆம் அதிபதி {seventh_lord} {seventh_lord_house}ஆம் பாவத்தில்")

    # 7th house occupants
    for p in occupants:
        if p in ["குரு", "சுக்கிரன்", "புதன்", "சந்திரன்"]:
            score += 1
            evidence.append(f"{p} 7ஆம் பாவத்தில்")
        elif p in ["சனி", "செவ்வாய்", "ராகு", "கேது", "சூரியன்"]:
            score -= 0.5
            evidence.append(f"{p} 7ஆம் பாவத்தில்")

    # Venus
    if venus_house in [1, 2, 5, 7, 9, 10, 11]:
        score += 1
        evidence.append(f"சுக்கிரன் {venus_house}ஆம் பாவத்தில்")

    # Jupiter
    if jupiter_house in [1, 2, 5, 7, 9, 10, 11]:
        score += 1
        evidence.append(f"குரு {jupiter_house}ஆம் பாவத்தில்")

    # 2nd and 11th lords
    for h in [2, 11]:
        lord = hl[h]
        lord_house = houses[lord]
        if lord_house in [1, 2, 5, 7, 9, 10, 11]:
            score += 1
            evidence.append(f"{h}ஆம் பாவ அதிபதி {lord} {lord_house}ஆம் பாவத்தில்")

    if score >= 5:
        level = "வலுவான சாதக குறியீடு"
    elif score >= 2:
        level = "சாதக குறியீடு"
    elif score >= 0:
        level = "கலப்பு நிலை"
    else:
        level = "சவால் / கூடுதல் ஆய்வு தேவை"

    return {
        "score": score,
        "level": level,
        "seventh_sign": seventh_sign,
        "seventh_lord": seventh_lord,
        "seventh_lord_house": seventh_lord_house,
        "occupants": occupants,
        "venus_house": venus_house,
        "jupiter_house": jupiter_house,
        "evidence": evidence
    }


def marriage_d9_analysis(chart):
    d9_lagna, d9_houses = d9_planet_houses(chart)
    d9_lords = house_lords_for_lagna(d9_lagna)

    seventh_lord = d9_lords[7]
    seventh_lord_house = d9_houses[seventh_lord]
    occupants = [p for p, h in d9_houses.items() if h == 7]

    score = 0
    evidence = []

    if seventh_lord_house in [1, 2, 5, 7, 9, 10, 11]:
        score += 2
        evidence.append(f"D9 7ஆம் அதிபதி {seventh_lord} {seventh_lord_house}ஆம் பாவத்தில்")
    elif seventh_lord_house in [6, 8, 12]:
        score -= 1
        evidence.append(f"D9 7ஆம் அதிபதி {seventh_lord} {seventh_lord_house}ஆம் பாவத்தில்")

    for p in occupants:
        if p in ["குரு", "சுக்கிரன்", "சந்திரன்", "புதன்"]:
            score += 1
            evidence.append(f"D9 7ஆம் பாவத்தில் {p}")
        elif p in ["சனி", "செவ்வாய்", "ராகு", "கேது", "சூரியன்"]:
            score -= 0.5
            evidence.append(f"D9 7ஆம் பாவத்தில் {p}")

    venus_house = d9_houses["சுக்கிரன்"]
    if venus_house in [1, 2, 5, 7, 9, 10, 11]:
        score += 1
        evidence.append(f"D9 சுக்கிரன் {venus_house}ஆம் பாவத்தில்")

    if score >= 3:
        level = "D9 சாதக குறியீடு"
    elif score >= 1:
        level = "D9 கலப்பு / சாதக"
    else:
        level = "D9 கூடுதல் ஆய்வு தேவை"

    return {
        "d9_lagna": d9_lagna,
        "d9_houses": d9_houses,
        "seventh_lord": seventh_lord,
        "seventh_lord_house": seventh_lord_house,
        "occupants": occupants,
        "score": score,
        "level": level,
        "evidence": evidence
    }


def manglik_screening(chart):
    houses = planet_houses(chart)
    mars_house = houses["செவ்வாய்"]

    d9_lagna, d9_houses = d9_planet_houses(chart)
    d9_mars_house = d9_houses["செவ்வாய்"]

    # Common screening positions; exceptions are not applied here.
    screening_houses = [1, 2, 4, 7, 8, 12]

    d1_flag = mars_house in screening_houses
    moon_lagna = chart["planets"]["சந்திரன்"]["rasi"]
    moon_mars_house = house_from_lagna(
        chart["planets"]["செவ்வாய்"]["rasi"],
        moon_lagna
    )

    venus_lagna = chart["planets"]["சுக்கிரன்"]["rasi"]
    venus_mars_house = house_from_lagna(
        chart["planets"]["செவ்வாய்"]["rasi"],
        venus_lagna
    )

    moon_flag = moon_mars_house in screening_houses
    venus_flag = venus_mars_house in screening_houses
    d9_flag = d9_mars_house in screening_houses

    count = sum([d1_flag, moon_flag, venus_flag, d9_flag])

    if count == 0:
        level = "செவ்வாய் தோஷ screening இல்லை"
    elif count == 1:
        level = "மிதமான screening குறியீடு"
    else:
        level = "கவனிக்க வேண்டிய screening குறியீடு"

    return {
        "d1_mars_house": mars_house,
        "moon_mars_house": moon_mars_house,
        "venus_mars_house": venus_mars_house,
        "d9_mars_house": d9_mars_house,
        "d1_flag": d1_flag,
        "moon_flag": moon_flag,
        "venus_flag": venus_flag,
        "d9_flag": d9_flag,
        "count": count,
        "level": level
    }


def marriage_delay_screening(chart):
    core = marriage_core_analysis(chart)
    houses = planet_houses(chart)
    hl = house_lords_for_lagna(chart["lagna"]["rasi"])

    delay_score = 0
    reasons = []

    # Saturn in / strongly connected to 7th house
    if houses["சனி"] == 7:
        delay_score += 2
        reasons.append("சனி 7ஆம் பாவத்தில்")

    if houses["சனி"] == 7:
        delay_score += 1
        reasons.append("7ஆம் பாவத்தில் சனி இருப்பு")

    if houses[hl[7]] in [6, 8, 12]:
        delay_score += 1
        reasons.append("7ஆம் அதிபதி 6/8/12 பாவத்தில்")

    if houses["செவ்வாய்"] == 7:
        delay_score += 1
        reasons.append("செவ்வாய் 7ஆம் பாவத்தில்")

    if houses["ராகு"] == 7 or houses["கேது"] == 7:
        delay_score += 1
        reasons.append("ராகு/கேது 7ஆம் பாவத்தில்")

    if core["venus_house"] in [6, 8, 12]:
        delay_score += 1
        reasons.append("சுக்கிரன் 6/8/12 பாவத்தில்")

    if delay_score >= 4:
        level = "தாமதத்திற்கான பலமான screening குறியீடு"
    elif delay_score >= 2:
        level = "சில தாமதக் குறியீடுகள்"
    else:
        level = "தாமதத்திற்கான வலுவான screening இல்லை"

    return {
        "score": delay_score,
        "level": level,
        "reasons": reasons
    }


def marriage_timing_v16(chart, md_list):
    core = marriage_core_analysis(chart)
    d9 = marriage_d9_analysis(chart)
    houses = planet_houses(chart)

    # D1 + D9 relevant lords/karakas.
    relevant = set([
        core["seventh_lord"],
        "சுக்கிரன்",
        "குரு",
        house_lords_for_lagna(chart["lagna"]["rasi"])[2],
        house_lords_for_lagna(chart["lagna"]["rasi"])[11],
        d9["seventh_lord"]
    ])

    rows = []
    now = datetime.now(chart["datetime_local"].tzinfo)
    horizon = add_years_days(now, 15)

    for md in md_list:
        if md["end"] < now or md["start"] > horizon:
            continue

        for ad in generate_bhukti(md["lord"], md["start"], md["end"]):
            if ad["end"] < now or ad["start"] > horizon:
                continue

            active = [md["lord"], ad["ad"]]
            score = 0
            reasons = []

            for p in active:
                if p in relevant:
                    score += 2
                    reasons.append(f"{p} முக்கிய திருமண காரகம்/அதிபதி")

                if p in houses and houses[p] in [2, 7, 11]:
                    score += 2
                    reasons.append(f"{p} {houses[p]}ஆம் பாவத்தை செயல்படுத்துகிறது")

                if p in houses and houses[p] in [5, 9]:
                    score += 1
                    reasons.append(f"{p} {houses[p]}ஆம் திரிகோண பாவத்தில் உள்ளது")

            # D9 support
            for p in active:
                if p in d9["d9_houses"] and d9["d9_houses"][p] == 7:
                    score += 2
                    reasons.append(f"D9-ல் {p} 7ஆம் பாவத்தில்")

                if p == d9["seventh_lord"]:
                    score += 1
                    reasons.append(f"{p} D9 7ஆம் அதிபதி")

            if score >= 4:
                level = "முக்கிய சாதக கால சாளரம்"
            elif score >= 2:
                level = "சாதக கால சாளரம்"
            else:
                continue

            rows.append({
                "மகாதசை": md["lord"],
                "புத்தி": ad["ad"],
                "தொடக்கம்": date_only(ad["start"]),
                "முடிவு": date_only(ad["end"]),
                "மதிப்பீடு": level,
                "குறியீடு": score,
                "ஆதாரம்": " | ".join(reasons)
            })

    if not rows:
        return pd.DataFrame(columns=[
            "மகாதசை", "புத்தி", "தொடக்கம்", "முடிவு",
            "மதிப்பீடு", "குறியீடு", "ஆதாரம்"
        ])

    return pd.DataFrame(rows).sort_values(
        ["குறியீடு", "தொடக்கம்"],
        ascending=[False, True]
    )


def marriage_summary_text(core, d9, manglik, delay):
    return (
        f"திருமண ஆய்வு: {core['level']}. "
        f"D9 நிலை: {d9['level']}. "
        f"செவ்வாய் screening: {manglik['level']}. "
        f"தாமத screening: {delay['level']}."
    )


# ------------------------------------------------------------
# COMPLETE CAREER / PROFESSION ANALYSIS
# ------------------------------------------------------------
def career_core_analysis(chart):
    lagna = chart["lagna"]["rasi"]
    hl = house_lords_for_lagna(lagna)
    houses = planet_houses(chart)

    tenth_sign = (lagna + 9) % 12
    tenth_lord = hl[10]
    tenth_lord_house = houses[tenth_lord]

    sixth_lord = hl[6]
    eleventh_lord = hl[11]

    tenth_occupants = [p for p, h in houses.items() if h == 10]

    score = 0
    evidence = []

    if tenth_lord_house in [1, 2, 5, 7, 9, 10, 11]:
        score += 2
        evidence.append(f"10ஆம் அதிபதி {tenth_lord} {tenth_lord_house}ஆம் பாவத்தில்")
    elif tenth_lord_house in [6, 8, 12]:
        score -= 1
        evidence.append(f"10ஆம் அதிபதி {tenth_lord} {tenth_lord_house}ஆம் பாவத்தில்")

    for p in tenth_occupants:
        if p in ["சூரியன்", "புதன்", "குரு", "சுக்கிரன்"]:
            score += 1
            evidence.append(f"{p} 10ஆம் பாவத்தில்")
        elif p in ["சனி", "செவ்வாய்", "ராகு", "கேது"]:
            evidence.append(f"{p} 10ஆம் பாவத்தில் — துறை/பணி தன்மை கவனிக்க வேண்டும்")

    for h, lord_name in [(6, sixth_lord), (11, eleventh_lord)]:
        lord_house = houses[lord_name]
        if lord_house in [1, 5, 9, 10, 11]:
            score += 1
            evidence.append(f"{h}ஆம் அதிபதி {lord_name} {lord_house}ஆம் பாவத்தில்")

    for p in ["சூரியன்", "புதன்", "சனி"]:
        if houses[p] in [1, 6, 10, 11]:
            score += 0.5
            evidence.append(f"{p} {houses[p]}ஆம் பாவத்தில்")

    if score >= 6:
        level = "வலுவான தொழில் முன்னேற்ற குறியீடு"
    elif score >= 3:
        level = "சாதக தொழில் குறியீடு"
    elif score >= 1:
        level = "கலப்பு தொழில் குறியீடு"
    else:
        level = "கூடுதல் தொழில் ஆய்வு தேவை"

    return {
        "score": score,
        "level": level,
        "tenth_sign": tenth_sign,
        "tenth_lord": tenth_lord,
        "tenth_lord_house": tenth_lord_house,
        "tenth_occupants": tenth_occupants,
        "sixth_lord": sixth_lord,
        "eleventh_lord": eleventh_lord,
        "evidence": evidence
    }


def career_d10_analysis(chart):
    d10_lagna = varga_sign(chart["lagna"]["longitude"], 10, "D10")
    d10_houses = {}
    for p, x in chart["planets"].items():
        d10_rasi = varga_sign(x["longitude"], 10, "D10")
        d10_houses[p] = house_from_lagna(d10_rasi, d10_lagna)

    d10_lords = house_lords_for_lagna(d10_lagna)
    tenth_lord = d10_lords[10]
    tenth_lord_house = d10_houses[tenth_lord]
    occupants = [p for p, h in d10_houses.items() if h == 10]

    score = 0
    evidence = []

    if tenth_lord_house in [1, 2, 5, 7, 9, 10, 11]:
        score += 2
        evidence.append(f"D10 10ஆம் அதிபதி {tenth_lord} {tenth_lord_house}ஆம் பாவத்தில்")
    elif tenth_lord_house in [6, 8, 12]:
        score -= 1
        evidence.append(f"D10 10ஆம் அதிபதி {tenth_lord} {tenth_lord_house}ஆம் பாவத்தில்")

    for p in occupants:
        if p in ["சூரியன்", "புதன்", "குரு", "சுக்கிரன்", "சனி"]:
            score += 1
            evidence.append(f"D10 10ஆம் பாவத்தில் {p}")

    if score >= 4:
        level = "D10 வலுவான தொழில் குறியீடு"
    elif score >= 2:
        level = "D10 சாதக தொழில் குறியீடு"
    else:
        level = "D10 கூடுதல் ஆய்வு தேவை"

    return {
        "d10_lagna": d10_lagna,
        "d10_houses": d10_houses,
        "tenth_lord": tenth_lord,
        "tenth_lord_house": tenth_lord_house,
        "occupants": occupants,
        "score": score,
        "level": level,
        "evidence": evidence
    }


def career_sector_screening(chart):
    houses = planet_houses(chart)

    sectors = [
        ("நிர்வாகம் / Leadership", ["சூரியன்", "செவ்வாய்"], [1, 10, 11]),
        ("Engineering / Technical", ["செவ்வாய்", "சனி", "புதன்"], [3, 6, 10, 11]),
        ("Finance / Business", ["புதன்", "குரு", "சுக்கிரன்"], [2, 5, 7, 10, 11]),
        ("Education / Consulting", ["குரு", "புதன்"], [5, 9, 10, 11]),
        ("Pharma / Science / Research", ["புதன்", "குரு", "சனி", "ராகு"], [5, 6, 8, 10, 12]),
        ("Operations / Manufacturing", ["செவ்வாய்", "சனி", "புதன்"], [6, 10, 11]),
        ("Foreign / MNC", ["ராகு", "புதன்", "சுக்கிரன்"], [3, 9, 10, 12]),
    ]

    rows = []

    for sector, planets, target_houses in sectors:
        score = 0
        reasons = []

        for p in planets:
            h = houses[p]
            if h in target_houses:
                score += 1
                reasons.append(f"{p} {h}ஆம் பாவம்")

        if score >= 3:
            level = "வலுவான சாத்தியம்"
        elif score >= 2:
            level = "சாதக சாத்தியம்"
        elif score == 1:
            level = "மிதமான சாத்தியம்"
        else:
            level = "கூடுதல் ஆய்வு"

        rows.append({
            "துறை": sector,
            "மதிப்பீடு": level,
            "குறியீடு": score,
            "ஆதாரம்": " | ".join(reasons) if reasons else "-"
        })

    return pd.DataFrame(rows).sort_values(
        ["குறியீடு", "துறை"], ascending=[False, True]
    )


def career_timing_v17(chart, md_list):
    core = career_core_analysis(chart)
    d10 = career_d10_analysis(chart)
    houses = planet_houses(chart)
    hl = house_lords_for_lagna(chart["lagna"]["rasi"])

    relevant = set([
        core["tenth_lord"],
        core["sixth_lord"],
        core["eleventh_lord"],
        "சூரியன்",
        "புதன்",
        "சனி"
    ])

    rows = []
    now = datetime.now(chart["datetime_local"].tzinfo)
    horizon = add_years_days(now, 15)

    for md in md_list:
        if md["end"] < now or md["start"] > horizon:
            continue

        for ad in generate_bhukti(md["lord"], md["start"], md["end"]):
            if ad["end"] < now or ad["start"] > horizon:
                continue

            score = 0
            reasons = []

            for p in [md["lord"], ad["ad"]]:
                if p in relevant:
                    score += 2
                    reasons.append(f"{p} தொழில் காரகம்/அதிபதி")

                if p in houses and houses[p] in [6, 10, 11]:
                    score += 2
                    reasons.append(f"{p} {houses[p]}ஆம் பாவம்")

                if p in d10["d10_houses"] and d10["d10_houses"][p] in [1, 6, 10, 11]:
                    score += 1
                    reasons.append(f"D10-ல் {p} {d10['d10_houses'][p]}ஆம் பாவம்")

                if p == d10["tenth_lord"]:
                    score += 1
                    reasons.append(f"{p} D10 10ஆம் அதிபதி")

            if score >= 4:
                level = "முக்கிய தொழில் கால சாளரம்"
            elif score >= 2:
                level = "சாதக தொழில் கால சாளரம்"
            else:
                continue

            rows.append({
                "மகாதசை": md["lord"],
                "புத்தி": ad["ad"],
                "தொடக்கம்": date_only(ad["start"]),
                "முடிவு": date_only(ad["end"]),
                "மதிப்பீடு": level,
                "குறியீடு": score,
                "ஆதாரம்": " | ".join(reasons)
            })

    if not rows:
        return pd.DataFrame(columns=[
            "மகாதசை", "புத்தி", "தொடக்கம்", "முடிவு",
            "மதிப்பீடு", "குறியீடு", "ஆதாரம்"
        ])

    return pd.DataFrame(rows).sort_values(
        ["குறியீடு", "தொடக்கம்"], ascending=[False, True]
    )


def career_summary_text(core, d10):
    return (
        f"தொழில் D1 மதிப்பீடு: {core['level']}. "
        f"D10 மதிப்பீடு: {d10['level']}. "
        f"10ஆம் அதிபதி: {core['tenth_lord']} — "
        f"{core['tenth_lord_house']}ஆம் பாவம்."
    )


# ------------------------------------------------------------
# COMPLETE WEALTH / FINANCE ANALYSIS
# ------------------------------------------------------------
def hora_sign(longitude):
    """
    Classical Parashari D2/Hora sign mapping:
    - Odd signs: first half Sun, second half Moon
    - Even signs: first half Moon, second half Sun
    The two Hora lords are represented by Sun/Moon signs.
    """
    ri = rasi_index(longitude)
    deg = deg_in_rasi(longitude)
    first_half = deg < 15.0

    if ri % 2 == 0:  # odd sign in zero-based Aries=0
        lord = "சூரியன்" if first_half else "சந்திரன்"
    else:
        lord = "சந்திரன்" if first_half else "சூரியன்"

    # D2 chart uses Leo for Sun Hora and Cancer for Moon Hora.
    return 4 if lord == "சூரியன்" else 3


def d2_chart_data(chart):
    d2_lagna = hora_sign(chart["lagna"]["longitude"])
    d2_houses = {}

    for p, x in chart["planets"].items():
        d2_houses[p] = house_from_lagna(
            hora_sign(x["longitude"]),
            d2_lagna
        )

    return d2_lagna, d2_houses


def wealth_core_analysis(chart):
    lagna = chart["lagna"]["rasi"]
    hl = house_lords_for_lagna(lagna)
    houses = planet_houses(chart)

    second_lord = hl[2]
    fifth_lord = hl[5]
    ninth_lord = hl[9]
    eleventh_lord = hl[11]

    score = 0
    evidence = []

    wealth_houses = [2, 5, 9, 11]

    for h, lord in [
        (2, second_lord),
        (5, fifth_lord),
        (9, ninth_lord),
        (11, eleventh_lord)
    ]:
        lh = houses[lord]

        if lh in [1, 2, 5, 7, 9, 10, 11]:
            score += 2
            evidence.append(f"{h}ஆம் அதிபதி {lord} {lh}ஆம் பாவத்தில்")
        elif lh in [6, 8, 12]:
            score -= 1
            evidence.append(f"{h}ஆம் அதிபதி {lord} {lh}ஆம் பாவத்தில்")

    for p in ["குரு", "சுக்கிரன்", "புதன்"]:
        h = houses[p]
        if h in wealth_houses:
            score += 1
            evidence.append(f"{p} {h}ஆம் பாவத்தில்")

    for h in wealth_houses:
        occupants = [p for p, ph in houses.items() if ph == h]
        for p in occupants:
            if p in ["குரு", "சுக்கிரன்", "புதன்"]:
                score += 1
                evidence.append(f"{p} {h}ஆம் பாவத்தில்")

    if score >= 10:
        level = "வலுவான செல்வ / லாப குறியீடு"
    elif score >= 6:
        level = "சாதக செல்வ குறியீடு"
    elif score >= 2:
        level = "கலப்பு செல்வ குறியீடு"
    else:
        level = "கூடுதல் செல்வ ஆய்வு தேவை"

    return {
        "score": score,
        "level": level,
        "second_lord": second_lord,
        "fifth_lord": fifth_lord,
        "ninth_lord": ninth_lord,
        "eleventh_lord": eleventh_lord,
        "evidence": evidence
    }


def wealth_d2_analysis(chart):
    d2_lagna, d2_houses = d2_chart_data(chart)
    d2_lords = house_lords_for_lagna(d2_lagna)

    second_lord = d2_lords[2]
    eleventh_lord = d2_lords[11]

    score = 0
    evidence = []

    if d2_houses[second_lord] in [1, 2, 5, 9, 10, 11]:
        score += 2
        evidence.append(
            f"D2 2ஆம் அதிபதி {second_lord} {d2_houses[second_lord]}ஆம் பாவத்தில்"
        )

    if d2_houses[eleventh_lord] in [1, 2, 5, 9, 10, 11]:
        score += 2
        evidence.append(
            f"D2 11ஆம் அதிபதி {eleventh_lord} {d2_houses[eleventh_lord]}ஆம் பாவத்தில்"
        )

    for p in ["குரு", "சுக்கிரன்", "புதன்"]:
        if d2_houses[p] in [1, 2, 5, 9, 10, 11]:
            score += 1
            evidence.append(
                f"D2 {p} {d2_houses[p]}ஆம் பாவத்தில்"
            )

    if score >= 5:
        level = "D2 வலுவான செல்வ குறியீடு"
    elif score >= 3:
        level = "D2 சாதக செல்வ குறியீடு"
    else:
        level = "D2 கூடுதல் ஆய்வு தேவை"

    return {
        "d2_lagna": d2_lagna,
        "d2_houses": d2_houses,
        "second_lord": second_lord,
        "eleventh_lord": eleventh_lord,
        "score": score,
        "level": level,
        "evidence": evidence
    }


def wealth_source_screening(chart):
    houses = planet_houses(chart)

    sources = [
        ("சம்பளம் / வேலை வருமானம்", ["சூரியன்", "சனி", "புதன்"], [2, 6, 10, 11]),
        ("Business / Trading", ["புதன்", "சுக்கிரன்", "குரு"], [2, 5, 7, 11]),
        ("Investment / Long-term wealth", ["குரு", "சுக்கிரன்", "சனி"], [2, 5, 9, 11]),
        ("Property / Fixed assets", ["செவ்வாய்", "சுக்கிரன்", "சந்திரன்"], [2, 4, 11]),
        ("Foreign / MNC income", ["ராகு", "புதன்", "சுக்கிரன்"], [2, 9, 11, 12]),
        ("Knowledge / Consulting income", ["குரு", "புதன்"], [2, 5, 9, 10, 11]),
    ]

    rows = []

    for source, planets, target_houses in sources:
        score = 0
        reasons = []

        for p in planets:
            h = houses[p]
            if h in target_houses:
                score += 1
                reasons.append(f"{p} {h}ஆம் பாவம்")

        if score >= 3:
            level = "வலுவான சாத்தியம்"
        elif score == 2:
            level = "சாதக சாத்தியம்"
        elif score == 1:
            level = "மிதமான சாத்தியம்"
        else:
            level = "கூடுதல் ஆய்வு"

        rows.append({
            "செல்வ மூலாதாரம்": source,
            "மதிப்பீடு": level,
            "குறியீடு": score,
            "ஆதாரம்": " | ".join(reasons) if reasons else "-"
        })

    return pd.DataFrame(rows).sort_values(
        ["குறியீடு", "செல்வ மூலாதாரம்"],
        ascending=[False, True]
    )


def wealth_timing_v18(chart, md_list):
    core = wealth_core_analysis(chart)
    d2 = wealth_d2_analysis(chart)
    houses = planet_houses(chart)

    relevant = {
        core["second_lord"],
        core["fifth_lord"],
        core["ninth_lord"],
        core["eleventh_lord"],
        "குரு",
        "சுக்கிரன்",
        "புதன்"
    }

    rows = []
    now = datetime.now(chart["datetime_local"].tzinfo)
    horizon = add_years_days(now, 15)

    for md in md_list:
        if md["end"] < now or md["start"] > horizon:
            continue

        for ad in generate_bhukti(md["lord"], md["start"], md["end"]):
            if ad["end"] < now or ad["start"] > horizon:
                continue

            score = 0
            reasons = []

            for p in [md["lord"], ad["ad"]]:
                if p in relevant:
                    score += 2
                    reasons.append(f"{p} செல்வ காரகம்/அதிபதி")

                if p in houses and houses[p] in [2, 5, 9, 11]:
                    score += 2
                    reasons.append(f"{p} {houses[p]}ஆம் பாவம்")

                if p in d2["d2_houses"] and d2["d2_houses"][p] in [1, 2, 5, 9, 11]:
                    score += 1
                    reasons.append(f"D2-ல் {p} சாதக பாவம்")

                if p == d2["second_lord"] or p == d2["eleventh_lord"]:
                    score += 1
                    reasons.append(f"{p} D2 செல்வ அதிபதி")

            if score >= 4:
                level = "முக்கிய செல்வ கால சாளரம்"
            elif score >= 2:
                level = "சாதக செல்வ கால சாளரம்"
            else:
                continue

            rows.append({
                "மகாதசை": md["lord"],
                "புத்தி": ad["ad"],
                "தொடக்கம்": date_only(ad["start"]),
                "முடிவு": date_only(ad["end"]),
                "மதிப்பீடு": level,
                "குறியீடு": score,
                "ஆதாரம்": " | ".join(reasons)
            })

    if not rows:
        return pd.DataFrame(columns=[
            "மகாதசை", "புத்தி", "தொடக்கம்", "முடிவு",
            "மதிப்பீடு", "குறியீடு", "ஆதாரம்"
        ])

    return pd.DataFrame(rows).sort_values(
        ["குறியீடு", "தொடக்கம்"],
        ascending=[False, True]
    )


def wealth_summary_text(core, d2):
    return (
        f"செல்வ D1 மதிப்பீடு: {core['level']}. "
        f"D2 மதிப்பீடு: {d2['level']}. "
        f"2ஆம் அதிபதி: {core['second_lord']}; "
        f"11ஆம் அதிபதி: {core['eleventh_lord']}."
    )


# ------------------------------------------------------------
# CHILDREN / EDUCATION / SANTANA ANALYSIS
# ------------------------------------------------------------
def children_core_analysis(chart):
    lagna = chart["lagna"]["rasi"]
    hl = house_lords_for_lagna(lagna)
    houses = planet_houses(chart)

    fifth_sign = (lagna + 4) % 12
    fifth_lord = hl[5]
    fifth_lord_house = houses[fifth_lord]
    occupants = [p for p, h in houses.items() if h == 5]

    score = 0
    evidence = []

    if fifth_lord_house in [1, 2, 5, 7, 9, 10, 11]:
        score += 2
        evidence.append(f"5ஆம் அதிபதி {fifth_lord} {fifth_lord_house}ஆம் பாவத்தில்")
    elif fifth_lord_house in [6, 8, 12]:
        score -= 1
        evidence.append(f"5ஆம் அதிபதி {fifth_lord} {fifth_lord_house}ஆம் பாவத்தில்")

    for p in occupants:
        if p in ["குரு", "சந்திரன்", "புதன்", "சுக்கிரன்"]:
            score += 1
            evidence.append(f"{p} 5ஆம் பாவத்தில்")
        elif p in ["சனி", "செவ்வாய்", "ராகு", "கேது"]:
            score -= 0.5
            evidence.append(f"{p} 5ஆம் பாவத்தில்")

    if houses["குரு"] in [1, 2, 5, 7, 9, 10, 11]:
        score += 1
        evidence.append(f"குரு {houses['குரு']}ஆம் பாவத்தில்")

    if score >= 5:
        level = "வலுவான சாதக சந்தான / கல்வி குறியீடு"
    elif score >= 2:
        level = "சாதக சந்தான / கல்வி குறியீடு"
    elif score >= 0:
        level = "கலப்பு நிலை"
    else:
        level = "கூடுதல் ஆய்வு தேவை"

    return {
        "score": score,
        "level": level,
        "fifth_sign": fifth_sign,
        "fifth_lord": fifth_lord,
        "fifth_lord_house": fifth_lord_house,
        "occupants": occupants,
        "evidence": evidence
    }


def education_core_analysis(chart):
    lagna = chart["lagna"]["rasi"]
    hl = house_lords_for_lagna(lagna)
    houses = planet_houses(chart)

    education_lords = [hl[4], hl[5], hl[9]]
    score = 0
    evidence = []

    for p in education_lords:
        h = houses[p]
        if h in [1, 4, 5, 9, 10, 11]:
            score += 2
            evidence.append(f"{p} {h}ஆம் பாவத்தில்")
        elif h in [6, 8, 12]:
            score -= 1
            evidence.append(f"{p} {h}ஆம் பாவத்தில்")

    for p in ["புதன்", "குரு", "சந்திரன்"]:
        if houses[p] in [1, 4, 5, 9, 10, 11]:
            score += 1
            evidence.append(f"{p} கல்விக்கு சாதக பாவத்தில்")

    if score >= 7:
        level = "வலுவான கல்வி / அறிவுத்திறன் குறியீடு"
    elif score >= 4:
        level = "சாதக கல்வி குறியீடு"
    elif score >= 1:
        level = "கலப்பு கல்வி குறியீடு"
    else:
        level = "கூடுதல் ஆய்வு தேவை"

    return {
        "score": score,
        "level": level,
        "education_lords": education_lords,
        "evidence": evidence
    }


def children_d7_analysis(chart):
    d7_lagna = varga_sign(chart["lagna"]["longitude"], 7, "D7")
    d7_houses = {}

    for p, x in chart["planets"].items():
        d7_rasi = varga_sign(x["longitude"], 7, "D7")
        d7_houses[p] = house_from_lagna(d7_rasi, d7_lagna)

    d7_lords = house_lords_for_lagna(d7_lagna)
    fifth_lord = d7_lords[5]
    fifth_lord_house = d7_houses[fifth_lord]
    occupants = [p for p, h in d7_houses.items() if h == 5]

    score = 0
    evidence = []

    if fifth_lord_house in [1, 2, 5, 7, 9, 10, 11]:
        score += 2
        evidence.append(f"D7 5ஆம் அதிபதி {fifth_lord} {fifth_lord_house}ஆம் பாவத்தில்")

    for p in occupants:
        if p in ["குரு", "சந்திரன்", "சுக்கிரன்", "புதன்"]:
            score += 1
            evidence.append(f"D7 5ஆம் பாவத்தில் {p}")
        elif p in ["சனி", "செவ்வாய்", "ராகு", "கேது"]:
            score -= 0.5
            evidence.append(f"D7 5ஆம் பாவத்தில் {p}")

    if score >= 4:
        level = "D7 வலுவான சாதக குறியீடு"
    elif score >= 2:
        level = "D7 சாதக குறியீடு"
    else:
        level = "D7 கூடுதல் ஆய்வு தேவை"

    return {
        "d7_lagna": d7_lagna,
        "d7_houses": d7_houses,
        "fifth_lord": fifth_lord,
        "fifth_lord_house": fifth_lord_house,
        "occupants": occupants,
        "score": score,
        "level": level,
        "evidence": evidence
    }


def children_timing_v19(chart, md_list):
    core = children_core_analysis(chart)
    d7 = children_d7_analysis(chart)
    houses = planet_houses(chart)
    hl = house_lords_for_lagna(chart["lagna"]["rasi"])

    relevant = {
        core["fifth_lord"],
        hl[9],
        hl[11],
        "குரு",
        "சந்திரன்"
    }

    rows = []
    now = datetime.now(chart["datetime_local"].tzinfo)
    horizon = add_years_days(now, 15)

    for md in md_list:
        if md["end"] < now or md["start"] > horizon:
            continue

        for ad in generate_bhukti(md["lord"], md["start"], md["end"]):
            if ad["end"] < now or ad["start"] > horizon:
                continue

            score = 0
            reasons = []

            for p in [md["lord"], ad["ad"]]:
                if p in relevant:
                    score += 2
                    reasons.append(f"{p} சந்தான/கல்வி காரகம் அல்லது அதிபதி")

                if p in houses and houses[p] in [2, 5, 9, 11]:
                    score += 2
                    reasons.append(f"{p} {houses[p]}ஆம் பாவத்தில்")

                if p in d7["d7_houses"] and d7["d7_houses"][p] in [1, 5, 9, 11]:
                    score += 1
                    reasons.append(f"D7-ல் {p} சாதக பாவத்தில்")

                if p == d7["fifth_lord"]:
                    score += 1
                    reasons.append(f"{p} D7 5ஆம் அதிபதி")

            if score >= 4:
                level = "முக்கிய சந்தான / கல்வி கால சாளரம்"
            elif score >= 2:
                level = "சாதக கால சாளரம்"
            else:
                continue

            rows.append({
                "மகாதசை": md["lord"],
                "புத்தி": ad["ad"],
                "தொடக்கம்": date_only(ad["start"]),
                "முடிவு": date_only(ad["end"]),
                "மதிப்பீடு": level,
                "குறியீடு": score,
                "ஆதாரம்": " | ".join(reasons)
            })

    if not rows:
        return pd.DataFrame(columns=[
            "மகாதசை", "புத்தி", "தொடக்கம்", "முடிவு",
            "மதிப்பீடு", "குறியீடு", "ஆதாரம்"
        ])

    return pd.DataFrame(rows).sort_values(
        ["குறியீடு", "தொடக்கம்"], ascending=[False, True]
    )


def education_stream_screening(chart):
    houses = planet_houses(chart)

    streams = [
        ("Engineering / Technology", ["செவ்வாய்", "புதன்", "சனி"], [4, 5, 6, 10]),
        ("Medicine / Life Science", ["சூரியன்", "செவ்வாய்", "குரு", "சந்திரன்"], [4, 5, 6, 8, 9]),
        ("Commerce / Finance", ["புதன்", "சுக்கிரன்", "குரு"], [2, 5, 9, 10, 11]),
        ("Law / Administration", ["சூரியன்", "குரு", "சனி", "புதன்"], [5, 6, 9, 10]),
        ("Research / Higher Studies", ["குரு", "புதன்", "ராகு", "சனி"], [5, 8, 9, 12]),
        ("Arts / Communication", ["சுக்கிரன்", "சந்திரன்", "புதன்"], [3, 4, 5, 7, 10]),
    ]

    rows = []
    for stream, planets, target_houses in streams:
        score = 0
        reasons = []
        for p in planets:
            if houses[p] in target_houses:
                score += 1
                reasons.append(f"{p} {houses[p]}ஆம் பாவம்")

        if score >= 3:
            level = "வலுவான சாத்தியம்"
        elif score == 2:
            level = "சாதக சாத்தியம்"
        elif score == 1:
            level = "மிதமான சாத்தியம்"
        else:
            level = "கூடுதல் ஆய்வு"

        rows.append({
            "கல்வித் துறை": stream,
            "மதிப்பீடு": level,
            "குறியீடு": score,
            "ஆதாரம்": " | ".join(reasons) if reasons else "-"
        })

    return pd.DataFrame(rows).sort_values(
        ["குறியீடு", "கல்வித் துறை"], ascending=[False, True]
    )


def children_summary_text(core, education, d7):
    return (
        f"சந்தான D1 மதிப்பீடு: {core['level']}. "
        f"கல்வி மதிப்பீடு: {education['level']}. "
        f"D7 மதிப்பீடு: {d7['level']}."
    )

# ------------------------------------------------------------
# PAGE
# ------------------------------------------------------------
st.set_page_config(
    page_title="Tamil Astrology Chart",
    page_icon="🪔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------
# THEME COLOR
# ------------------------------------------------------------
# Fixed Teal theme for a consistent public/mobile presentation.
# The theme selector is intentionally removed from the sidebar.
THEME = {
    "accent": "#0f766e",
    "soft": "#f0fdfa",
    "border": "#73aaa5",
    "dark": "#115e59",
}

# ------------------------------------------------------------
# STYLE
# ------------------------------------------------------------
GLOBAL_STYLE = """
<style>
.main-title {
    font-size: 40px;
    font-weight: 800;
    text-align: center;
    padding: 12px 0 4px 0;
    color: #111827 !important;
}
.sub-title {
    text-align: center;
    font-size: 18px;
    margin-bottom: 18px;
    color: #374151 !important;
}
.section-title {
    font-size: 23px;
    font-weight: 750;
    padding: 9px 12px;
    border-left: 6px solid {accent};
    background: {theme_soft};
    color: #111827 !important;
    margin-top: 18px;
    margin-bottom: 12px;
}
.section-title * {
    color: #111827 !important;
}

/* Phase-1 public typography and responsive birth-details cards */
.birth-detail-card {
    min-width: 0 !important;
    overflow: visible !important;
}
.birth-detail-label {
    font-size: 17px;
    line-height: 1.35;
    margin-bottom: 5px;
}
.birth-detail-value {
    font-size: 22px;
    line-height: 1.25;
    white-space: normal !important;
    overflow-wrap: anywhere !important;
    word-break: normal !important;
}

.info-card {
    padding: 14px;
    border-radius: 10px;
    background: #faf7ff;
    border: 1px solid {theme_border};
    margin-bottom: 8px;
    color: #111827 !important;
}
.info-card h1,
.info-card h2,
.info-card h3,
.info-card h4,
.info-card h5,
.info-card h6,
.info-card p,
.info-card span,
.info-card div {
    color: #111827 !important;
}

/* Prevent page-level horizontal overflow */
html, body, [data-testid="stAppViewContainer"] {
    overflow-x: hidden !important;
}
.small-note {
    font-size: 13px;
    color: #666;
}

/* responsive table safety */
div[data-testid="stDataFrame"] {
    width: 100% !important;
    max-width: 100% !important;
}

.dasha-current {
    padding: 16px;
    border-radius: 12px;
    background: #fff7df;
    border: 2px solid #d9a441;
    color: #111827 !important;
}
.dasha-current * {
    color: #111827 !important;
}

/* Keep the application readable when the device/browser uses dark mode. */
@media (prefers-color-scheme: dark) {
    .section-title, .info-card, .dasha-current {
        color: #111827 !important;
    }
    .section-title *, .info-card *, .dasha-current * {
        color: #111827 !important;
    }
}
</style>
""".replace("{accent}", THEME["accent"]).replace("{theme_soft}", THEME["soft"]).replace("{theme_border}", THEME["border"])
st.markdown(GLOBAL_STYLE, unsafe_allow_html=True)

# ------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------
RASI_EN = [
    "Mesha", "Rishabha", "Mithuna", "Kataka",
    "Simha", "Kanya", "Tula", "Vrischika",
    "Dhanus", "Makara", "Kumbha", "Meena"
]

RASI_TA = [
    "மேஷம்", "ரிஷபம்", "மிதுனம்", "கடகம்",
    "சிம்மம்", "கன்னி", "துலாம்", "விருச்சிகம்",
    "தனுசு", "மகரம்", "கும்பம்", "மீனம்"
]

PLANET_TA = {
    "சூரியன்": "சூரியன்",
    "சந்திரன்": "சந்திரன்",
    "செவ்வாய்": "செவ்வாய்",
    "புதன்": "புதன்",
    "குரு": "குரு",
    "சுக்கிரன்": "சுக்கிரன்",
    "சனி": "சனி",
    "ராகு": "ராகு",
    "கேது": "கேது",
    "லக்னம்": "லக்னம்",
}

PLANET_EN = {
    "சூரியன்": swe.SUN,
    "சந்திரன்": swe.MOON,
    "செவ்வாய்": swe.MARS,
    "புதன்": swe.MERCURY,
    "குரு": swe.JUPITER,
    "சுக்கிரன்": swe.VENUS,
    "சனி": swe.SATURN,
    "ராகு": swe.MEAN_NODE,
}

NAK_TA = [
    "அஸ்வினி", "பரணி", "கார்த்திகை", "ரோகிணி",
    "மிருகசீரிஷம்", "திருவாதிரை", "புனர்பூசம்", "பூசம்",
    "ஆயில்யம்", "மகம்", "பூரம்", "உத்திரம்",
    "ஹஸ்தம்", "சித்திரை", "சுவாதி", "விசாகம்",
    "அனுஷம்", "கேட்டை", "மூலம்", "பூராடம்",
    "உத்திராடம்", "திருவோணம்", "அவிட்டம்", "சதயம்",
    "பூரட்டாதி", "உத்திரட்டாதி", "ரேவதி"
]

NAK_LORD_TA = [
    "கேது", "சுக்கிரன்", "சூரியன்", "சந்திரன்",
    "செவ்வாய்", "ராகு", "குரு", "சனி", "புதன்"
] * 3

NAK_LORD_EN = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"
] * 3

# Vimshottari years
DASHA_YEARS = {
    "கேது": 7,
    "சுக்கிரன்": 20,
    "சூரியன்": 6,
    "சந்திரன்": 10,
    "செவ்வாய்": 7,
    "ராகு": 18,
    "குரு": 16,
    "சனி": 19,
    "புதன்": 17,
}

DASHA_ORDER = [
    "கேது", "சுக்கிரன்", "சூரியன்", "சந்திரன்",
    "செவ்வாய்", "ராகு", "குரு", "சனி", "புதன்"
]

DASHA_COLOR = {
    "கேது": "#eadcff",
    "சுக்கிரன்": "#ffe1f0",
    "சூரியன்": "#ffe4c4",
    "சந்திரன்": "#e4f2ff",
    "செவ்வாய்": "#ffd9d9",
    "ராகு": "#e4e4e4",
    "குரு": "#fff1b8",
    "சனி": "#dfe7ef",
    "புதன்": "#ddf4df",
}

# ------------------------------------------------------------
# UTILITY FUNCTIONS
# ------------------------------------------------------------
def safe_ayanamsa(jd):
    value = swe.get_ayanamsa_ut(jd)
    if isinstance(value, tuple):
        return float(value[0])
    return float(value)


def normalize_deg(x):
    return x % 360.0


def rasi_index(longitude):
    return int(normalize_deg(longitude) // 30)


def deg_in_rasi(longitude):
    return normalize_deg(longitude) % 30.0


def nakshatra_info(longitude):
    lon = normalize_deg(longitude)
    span = 360.0 / 27.0
    idx = int(lon // span)
    within = lon - idx * span
    pada = int(within / (span / 4.0)) + 1
    fraction = within / span
    return idx, pada, fraction


def dms(deg):
    d = int(deg)
    m_float = (deg - d) * 60
    m = int(m_float)
    s = int(round((m_float - m) * 60))
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        d += 1
    return f"{d:02d}° {m:02d}' {s:02d}\""


def tamil_date(dt):
    return dt.strftime("%d-%m-%Y")


def tamil_datetime(dt):
    return dt.strftime("%d-%m-%Y %H:%M")


def add_years_days(start_dt, years):
    # Astronomical/Jyotish software often uses 365.2425 days per year.
    return start_dt + timedelta(days=years * 365.2425)


def date_only(dt):
    return dt.strftime("%d-%m-%Y")


# ------------------------------------------------------------
# LOCATION
# ------------------------------------------------------------
@st.cache_data(show_spinner=False)
def geocode_place(place):
    geolocator = Nominatim(user_agent="tamil_astrology_chart_phase1_public")
    loc = geolocator.geocode(place, timeout=10)
    if loc is None:
        raise ValueError("இடத்தை கண்டுபிடிக்க முடியவில்லை.")
    tf = TimezoneFinder()
    tzname = tf.timezone_at(lat=loc.latitude, lng=loc.longitude)
    if tzname is None:
        raise ValueError("இந்த இடத்திற்கான Time Zone கிடைக்கவில்லை.")
    return float(loc.latitude), float(loc.longitude), tzname, loc.address


@st.cache_data(show_spinner=False)
def search_place_candidates(query, limit=6):
    """
    Search for multiple place candidates so the user can select the exact
    birthplace instead of relying on free-text spelling.
    """
    query = (query or "").strip()
    if len(query) < 3:
        return []

    geolocator = Nominatim(user_agent="tamil_astrology_chart_phase1_public")
    locations = geolocator.geocode(
        query,
        timeout=10,
        exactly_one=False,
        limit=limit,
        addressdetails=True
    ) or []

    tf = TimezoneFinder()
    candidates = []
    seen = set()

    for loc in locations:
        lat = float(loc.latitude)
        lon = float(loc.longitude)
        tzname = tf.timezone_at(lat=lat, lng=lon)
        if not tzname:
            continue

        raw = loc.raw or {}
        address = raw.get("address", {}) or {}
        display = loc.address or query
        key = (round(lat, 6), round(lon, 6), display)
        if key in seen:
            continue
        seen.add(key)

        candidates.append({
            "display": display,
            "latitude": lat,
            "longitude": lon,
            "timezone": tzname,
            "city": address.get("city") or address.get("town") or address.get("village") or address.get("municipality") or "",
            "state": address.get("state") or "",
            "country": address.get("country") or "",
        })

    return candidates


# ------------------------------------------------------------
# PLANET CALCULATION
# ------------------------------------------------------------
def calculate_chart(dt_local, latitude, longitude, tzname):
    tz = ZoneInfo(tzname)
    dt_aware = dt_local.replace(tzinfo=tz)
    dt_utc = dt_aware.astimezone(ZoneInfo("UTC"))

    hour_ut = (
        dt_utc.hour
        + dt_utc.minute / 60
        + dt_utc.second / 3600
        + dt_utc.microsecond / 3_600_000_000
    )

    jd_ut = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        hour_ut
    )

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    ayanamsa = safe_ayanamsa(jd_ut)

    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

    planets = {}

    for name_ta, planet_id in PLANET_EN.items():
        result = swe.calc_ut(jd_ut, planet_id, flags)
        pos = result[0]
        lon = normalize_deg(pos[0])
        speed = float(pos[3])
        ri = rasi_index(lon)
        nak, pada, _ = nakshatra_info(lon)

        planets[name_ta] = {
            "longitude": lon,
            "rasi": ri,
            "degree": deg_in_rasi(lon),
            "nak": nak,
            "pada": pada,
            "retro": speed < 0,
            "speed": speed
        }

    # Ketu = Rahu + 180°
    rahu_lon = planets["ராகு"]["longitude"]
    ketu_lon = normalize_deg(rahu_lon + 180)
    nak, pada, _ = nakshatra_info(ketu_lon)

    planets["கேது"] = {
        "longitude": ketu_lon,
        "rasi": rasi_index(ketu_lon),
        "degree": deg_in_rasi(ketu_lon),
        "nak": nak,
        "pada": pada,
        "retro": planets["ராகு"]["retro"],
        "speed": -planets["ராகு"]["speed"]
    }

    # Tropical Ascendant from houses, then convert to Lahiri sidereal.
    cusps, ascmc = swe.houses(
        jd_ut,
        latitude,
        longitude,
        b"W"
    )

    asc_tropical = normalize_deg(float(ascmc[0]))
    asc_sidereal = normalize_deg(asc_tropical - ayanamsa)
    asc_ri = rasi_index(asc_sidereal)
    asc_nak, asc_pada, _ = nakshatra_info(asc_sidereal)

    lagna = {
        "longitude": asc_sidereal,
        "rasi": asc_ri,
        "degree": deg_in_rasi(asc_sidereal),
        "nak": asc_nak,
        "pada": asc_pada
    }

    return {
        "jd_ut": jd_ut,
        "ayanamsa": ayanamsa,
        "planets": planets,
        "lagna": lagna,
        "datetime_local": dt_aware,
        "datetime_utc": dt_utc,
        "latitude": float(latitude),
        "longitude": float(longitude),
        "tzname": tzname
    }


# ------------------------------------------------------------
# DETAILED BIRTH / PANCHANGA INFORMATION
# ------------------------------------------------------------
WEEKDAY_TA = [
    "திங்கள்", "செவ்வாய்", "புதன்", "வியாழன்",
    "வெள்ளி", "சனி", "ஞாயிறு"
]

TITHI_TA = [
    "பிரதமை", "துவிதியை", "திரிதியை", "சதுர்த்தி", "பஞ்சமி",
    "சஷ்டி", "சப்தமி", "அஷ்டமி", "நவமி", "தசமி",
    "ஏகாதசி", "துவாதசி", "திரயோதசி", "சதுர்த்தசி", "பௌர்ணமி",
    "பிரதமை", "துவிதியை", "திரிதியை", "சதுர்த்தி", "பஞ்சமி",
    "சஷ்டி", "சப்தமி", "அஷ்டமி", "நவமி", "தசமி",
    "ஏகாதசி", "துவாதசி", "திரயோதசி", "சதுர்த்தசி", "அமாவாசை"
]

YOGA_TA = [
    "விஷ்கம்பம்", "ப்ரீதி", "ஆயுஷ்மான்", "சௌபாக்யம்", "சோபனம்",
    "அதிகண்டம்", "சுகர்மம்", "த்ருதி", "சூலம்", "கண்டம்",
    "விருத்தி", "த்ருவம்", "வியாகாதம்", "ஹர்ஷணம்", "வஜ்ரம்",
    "சித்தி", "வியதீபாதம்", "வரியான்", "பரிகம்", "சிவம்",
    "சித்தம்", "சாத்தியம்", "சுபம்", "சுக்லம்", "பிரம்மம்",
    "இந்திரம்", "வைத்ருதி"
]

KARANA_FIXED = {
    0: "கிம்ஸ்துக்னம்", 1: "பவம்", 2: "பாலவம்", 3: "கௌலவம்",
    4: "தைதிலம்", 5: "கரசை", 6: "வணிஜம்", 7: "விஷ்டி",
}
KARANA_MOVING = ["பவம்", "பாலவம்", "கௌலவம்", "தைதிலம்", "கரசை", "வணிஜம்", "விஷ்டி"]

TAMIL_MONTHS = {
    0: "சித்திரை", 1: "வைகாசி", 2: "ஆனி", 3: "ஆடி", 4: "ஆவணி", 5: "புரட்டாசி",
    6: "ஐப்பசி", 7: "கார்த்திகை", 8: "மார்கழி", 9: "தை", 10: "மாசி", 11: "பங்குனி"
}

# 60-year Tamil cycle, indexed from Prabhava.
TAMIL_YEAR_NAMES = [
    "பிரபவ", "விபவ", "சுக்ல", "பிரமோதூத", "பிரசோத்பத்தி", "ஆங்கீரச", "ஸ்ரீமுக", "பவ", "யுவ", "தாது",
    "ஈஸ்வர", "வெகுதான்ய", "பிரமாதி", "விக்கிரம", "விஷு", "சித்திரபானு", "சுபானு", "தாரண", "பார்த்திப", "விய",
    "சர்வஜித்", "சர்வதாரி", "விரோதி", "விக்ருதி", "கர", "நந்தன", "விஜய", "ஜய", "மன்மத", "துர்முகி",
    "ஹேவிளம்பி", "விளம்பி", "விகாரி", "சார்வரி", "பிலவ", "சுபகிருது", "சோபகிருது", "குரோதி", "விசுவாவசு", "பராபவ",
    "பிலவங்க", "கீலக", "சௌம்ய", "சாதாரண", "விரோதிகிருது", "பரிதாபி", "பிரமாதீச", "ஆனந்த", "ராட்சச", "நள",
    "பிங்கள", "காளயுக்தி", "சித்தார்த்தி", "ரௌத்திரி", "துர்மதி", "துந்துபி", "ருத்ரோத்காரி", "ரக்தாட்சி", "குரோதன", "அட்சய"
]

RASI_LORD_TA = {
    0: "செவ்வாய்", 1: "சுக்கிரன்", 2: "புதன்", 3: "சந்திரன்", 4: "சூரியன்", 5: "புதன்",
    6: "சுக்கிரன்", 7: "செவ்வாய்", 8: "குரு", 9: "சனி", 10: "சனி", 11: "குரு"
}

INDHU_LAGNA_VALUES = {
    "சூரியன்": 30, "சந்திரன்": 16, "செவ்வாய்": 6, "புதன்": 8,
    "குரு": 10, "சுக்கிரன்": 12, "சனி": 1
}


def _jd_to_local(jd_value, tzname):
    unix_seconds = (jd_value - 2440587.5) * 86400.0
    return datetime.fromtimestamp(unix_seconds, ZoneInfo("UTC")).astimezone(ZoneInfo(tzname))


def sunrise_sunset_local(chart, latitude, longitude, tzname):
    """Return local sunrise/sunset for the birth date using Swiss Ephemeris."""
    dt_local = chart["datetime_local"]
    midnight = datetime(dt_local.year, dt_local.month, dt_local.day, 0, 0, tzinfo=ZoneInfo(tzname))
    midnight_utc = midnight.astimezone(ZoneInfo("UTC"))
    jd0 = swe.julday(midnight_utc.year, midnight_utc.month, midnight_utc.day,
                     midnight_utc.hour + midnight_utc.minute / 60.0 + midnight_utc.second / 3600.0)
    geopos = (float(longitude), float(latitude), 0.0)
    try:
        rise = swe.rise_trans(jd0, swe.SUN, swe.CALC_RISE, geopos, 0.0, 0.0)[1][0]
        setting = swe.rise_trans(jd0, swe.SUN, swe.CALC_SET, geopos, 0.0, 0.0)[1][0]
        return _jd_to_local(rise, tzname), _jd_to_local(setting, tzname)
    except Exception:
        return None, None


def tithi_yoga_karana(chart):
    sun = chart["planets"]["சூரியன்"]["longitude"]
    moon = chart["planets"]["சந்திரன்"]["longitude"]
    elong = normalize_deg(moon - sun)
    tithi_no = min(30, int(elong // 12.0) + 1)
    paksha = "சுக்ல பக்ஷம்" if tithi_no <= 15 else "கிருஷ்ண பக்ஷம்"
    tithi_name = TITHI_TA[tithi_no - 1]

    yoga_value = normalize_deg(sun + moon)
    yoga_no = min(27, int(yoga_value // (360.0 / 27.0)) + 1)
    yoga_name = YOGA_TA[yoga_no - 1]

    half_tithi_no = min(60, int(elong // 6.0) + 1)
    if half_tithi_no == 1:
        karana_name = KARANA_FIXED[0]
    elif half_tithi_no in [2, 3, 4, 5, 6, 7, 8]:
        karana_name = KARANA_FIXED[half_tithi_no - 1]
    elif half_tithi_no >= 9 and half_tithi_no <= 57:
        karana_name = KARANA_MOVING[(half_tithi_no - 9) % 7]
    elif half_tithi_no == 58:
        karana_name = "சகுனி"
    elif half_tithi_no == 59:
        karana_name = "சதுஷ்பாதம்"
    else:
        karana_name = "நாகவம்"

    return {
        "tithi_no": tithi_no,
        "tithi": tithi_name,
        "paksha": paksha,
        "yoga_no": yoga_no,
        "yoga": yoga_name,
        "karana": karana_name,
        "elongation": elong,
        "yoga_value": yoga_value,
    }


def tamil_solar_date(chart):
    """Approximate Tamil solar month/day from Lahiri sidereal Sun longitude."""
    sun_lon = chart["planets"]["சூரியன்"]["longitude"]
    sign = rasi_index(sun_lon)
    month = TAMIL_MONTHS[sign]
    ingress = sign * 30.0
    dt = chart["datetime_local"]
    # Find the most recent solar ingress by bisection over a 40-day window.
    end = dt.astimezone(ZoneInfo("UTC"))
    end_jd = chart["jd_ut"]
    start_jd = end_jd - 40.0
    target = ingress
    def sun_sid(jd):
        return normalize_deg(swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0])
    lo, hi = start_jd, end_jd
    # Find a bracket by scanning backward.
    prev_jd = hi
    prev = sun_sid(prev_jd)
    bracket = None
    step = 0.5
    x = hi
    for _ in range(90):
        x2 = x - step
        v2 = sun_sid(x2)
        if target == 0:
            crossed = (v2 > 330 and prev < 30) or (v2 <= target <= prev)
        else:
            crossed = (v2 <= target <= prev) or (prev < 5 and v2 > 350)
        if crossed:
            bracket = (x2, x)
            break
        x, prev_jd, prev = x2, x2, v2
    if bracket is None:
        # Fallback: use the current solar longitude proportionally.
        day = int((sun_lon % 30.0) // 1.0) + 1
        return month, day
    lo, hi = bracket
    for _ in range(60):
        mid = (lo + hi) / 2.0
        vm = sun_sid(mid)
        if target == 0:
            # unwrap around 360/0
            if vm < 180:
                hi = mid
            else:
                lo = mid
        elif vm < target:
            lo = mid
        else:
            hi = mid
    ingress_dt = _jd_to_local((lo + hi) / 2.0, chart["datetime_local"].tzinfo.key)
    day = (dt.date() - ingress_dt.date()).days + 1
    return month, max(1, day)


def tamil_year_name(gregorian_year, month, day):
    # The traditional Tamil year is commonly labelled by its ending Gregorian year:
    # Feb-1980 therefore belongs to Tamil year 1980-81 (Siddharthi).
    tamil_year_label = gregorian_year + 1 if (month > 4 or (month == 4 and day >= 14)) else gregorian_year
    # 1980-81 = Siddharthi, corresponding to index 52 in the cycle.
    index = (tamil_year_label - 1980 + 52) % 60
    return TAMIL_YEAR_NAMES[index]


def yogi_avayogi(chart):
    sun = chart["planets"]["சூரியன்"]["longitude"]
    moon = chart["planets"]["சந்திரன்"]["longitude"]
    yogi_lon = normalize_deg(sun + moon)
    avayogi_lon = normalize_deg(yogi_lon + 93.3333333333)  # 93°20'
    yn, yp, _ = nakshatra_info(yogi_lon)
    an, ap, _ = nakshatra_info(avayogi_lon)
    return yogi_lon, yn, yp, avayogi_lon, an, ap


def indhu_lagna(chart):
    lagna = chart["lagna"]["rasi"]
    moon_rasi = chart["planets"]["சந்திரன்"]["rasi"]
    lagna_9th = (lagna + 8) % 12
    moon_9th = (moon_rasi + 8) % 12
    p1 = RASI_LORD_TA[lagna_9th]
    p2 = RASI_LORD_TA[moon_9th]
    v1 = INDHU_LAGNA_VALUES.get(p1, 0)
    v2 = INDHU_LAGNA_VALUES.get(p2, 0)
    sign = (moon_rasi + ((v1 + v2) % 12)) % 12
    return sign, p1, p2


def hora_lagna(chart):
    """Traditional time-based Hora Lagna using local solar day from sunrise."""
    rise, _ = sunrise_sunset_local(chart, chart.get("latitude", 0.0), chart.get("longitude", 0.0), chart["datetime_local"].tzinfo.key)
    if rise is None:
        return chart["lagna"]["rasi"]
    elapsed_hours = (chart["datetime_local"] - rise).total_seconds() / 3600.0
    # 2.5 hours per sign; for pre-sunrise use the previous sign sequence.
    sign = (int(elapsed_hours / 2.5) + chart["lagna"]["rasi"]) % 12
    return sign


def detailed_birth_info(chart, name, gender, latitude, longitude, tzname, full_address):
    dt = chart["datetime_local"]
    panch = tithi_yoga_karana(chart)
    rise, setting = sunrise_sunset_local(chart, latitude, longitude, tzname)
    udayadi = None
    if rise is not None:
        udayadi = max(0.0, (dt - rise).total_seconds() / 86400.0 * 60.0)
    tamil_month, tamil_day = tamil_solar_date(chart)
    tamil_year = tamil_year_name(dt.year, dt.month, dt.day)
    yogi_lon, yn, yp, av_lon, an, ap = yogi_avayogi(chart)
    indhu_sign, indhu_p1, indhu_p2 = indhu_lagna(chart)

    tz = ZoneInfo(tzname)
    offset = dt.utcoffset().total_seconds() / 3600.0 if dt.utcoffset() else 0.0
    weekday = WEEKDAY_TA[dt.weekday()]

    # Calendar eras, following the conventional Indian civil-year transitions.
    saka_year = dt.year - 78 if (dt.month > 3 or (dt.month == 3 and dt.day >= 22)) else dt.year - 79
    vikrama_year = dt.year + 57
    kollam_year = dt.year - 825
    kali_year = dt.year + 3101

    sunrise_txt = rise.strftime("%H:%M") if rise else "-"
    sunset_txt = setting.strftime("%H:%M") if setting else "-"
    udayadi_txt = f"{udayadi:.2f} நாழி" if udayadi is not None else "-"

    return [
        ("பெயர்", name),
        ("பிறந்த தேதி", dt.strftime("%d-%m-%Y")),
        ("பிறந்த நேரம்", dt.strftime("%I:%M:%S %p").lower()),
        ("பாலினம்", gender),
        ("பிறந்த கிழமை", weekday),
        ("ஜன்ம நட்சத்திரம்", f"{NAK_TA[chart['planets']['சந்திரன்']['nak']]} - {chart['planets']['சந்திரன்']['pada']}ஆம் பாதம்"),
        ("ஜன்ம இராசி", RASI_TA[chart['planets']['சந்திரன்']['rasi']]),
        ("ஜன்ம லக்கினம்", RASI_TA[chart['lagna']['rasi']]),
        ("பொதுநேரம் / Time Zone", f"{offset:+.2f} GMT ({tzname})"),
        ("பிறந்த ஊர்", full_address),
        ("தமிழ் நேரம் / உதயாதி நாழிகை", udayadi_txt),
        ("சூரிய உதயம்", sunrise_txt),
        ("சூரிய அஸ்தமனம்", sunset_txt),
        ("அயனாம்சம்", f"{chart['ayanamsa']:.2f}° (லஹிரி)"),
        ("தமிழ் தேதி", f"{tamil_month}-{tamil_day} — {tamil_year}"),
        ("திதி", panch["tithi"]),
        ("பட்சம்", panch["paksha"]),
        ("கரணம்", panch["karana"]),
        ("யோகம்", panch["yoga"]),
        ("அயனம்", "உத்தராயணம்" if chart["planets"]["சூரியன்"]["longitude"] < 180 or chart["planets"]["சூரியன்"]["longitude"] >= 270 else "தட்சிணாயணம்"),
        ("அட்சாம்சம்", f"{latitude:.4f} N"),
        ("தீர்க்காம்சம்", f"{longitude:.4f} E" if longitude >= 0 else f"{abs(longitude):.4f} W"),
        ("யோகி", f"{NAK_TA[yn]} ({yogi_lon:.2f}°)"),
        ("அவயோகி", f"{NAK_TA[an]} ({av_lon:.2f}°)"),
        ("இந்த லக்கினம்", RASI_TA[indhu_sign]),
        ("ஹோரா லக்கினம்", RASI_TA[hora_lagna(chart)]),
        ("கலியுகாதி ஆண்டு", str(kali_year)),
        ("சாலிவாகன சகாப்தம்", str(saka_year)),
        ("கொல்லம்", str(kollam_year)),
        ("விக்ரம சகாப்தம்", str(vikrama_year)),
    ]


# ------------------------------------------------------------
# NAVAMSA
# ------------------------------------------------------------
def navamsa_sign(longitude):
    ri = rasi_index(longitude)
    deg = deg_in_rasi(longitude)

    nav_no = int(deg / (30.0 / 9.0))
    nav_no = min(nav_no, 8)

    # Standard D9 starting signs:
    # Movable: same sign
    # Fixed: 9th from sign = +8
    # Dual: 5th from sign = +4
    if ri in [0, 3, 6, 9]:       # movable
        start = ri
    elif ri in [1, 4, 7, 10]:    # fixed
        start = (ri + 8) % 12
    else:                         # dual
        start = (ri + 4) % 12

    return (start + nav_no) % 12


# ------------------------------------------------------------
# CHART HTML
# ------------------------------------------------------------
SOUTH_POSITION = {
    11: (0, 0),  # Meena
    0:  (0, 1),  # Mesha
    1:  (0, 2),  # Rishabha
    2:  (0, 3),  # Mithuna
    3:  (1, 3),  # Kataka
    4:  (2, 3),  # Simha
    5:  (3, 3),  # Kanya
    6:  (3, 2),  # Tula
    7:  (3, 1),  # Vrischika
    8:  (3, 0),  # Dhanus
    9:  (2, 0),  # Makara
    10: (1, 0),  # Kumbha
}


def make_chart_html(title, placements, show_lagna=True):
    cells = [["" for _ in range(4)] for _ in range(4)]

    # House numbering is always relative to the Lagna: Lagna = 1,
    # then 2, 3, ... 12 clockwise around the South Indian chart.
    lagna_rasi = placements[0]["rasi"] if placements else 0

    for ri in range(12):
        row, col = SOUTH_POSITION[ri]
        label = RASI_TA[ri]
        house_no = ((ri - lagna_rasi) % 12) + 1
        cells[row][col] = (
            f"<div class='house-no'>{house_no}</div>"
            f"<div class='rasi-label'>{label}</div>"
        )

    for item in placements:
        ri = item["rasi"]
        row, col = SOUTH_POSITION[ri]

        if "planet" in item:
            p = item["planet"]
            if p not in cells[row][col]:
                cells[row][col] += f"<div class='planet'>{p}</div>"
        elif "text" in item:
            cells[row][col] += f"<div class='planet'>{item['text']}</div>"

    theme_accent = THEME["accent"]
    theme_soft = THEME["soft"]
    theme_border = THEME["border"]
    theme_dark = THEME["dark"]

    html = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        html, body {{
            margin:0 !important;
            padding:0 !important;
            width:100% !important;
            overflow:hidden !important;
            background:#ffffff !important;
            color:#111827 !important;
            color-scheme:light !important;
            font-family:"Noto Sans Tamil", "Latha", Arial, sans-serif;
        }}
        .title {{
            width:100%;
            box-sizing:border-box;
            text-align:center;
            font-size:24px;
            line-height:1.25;
            font-weight:800;
            margin:8px 0 14px;
            color:#111827 !important;
            overflow-wrap:anywhere;
        }}
        .chart {{
            width:min(720px, 100%);
            max-width:100%;
            aspect-ratio:1 / 1;
            height:auto;
            box-sizing:border-box;
            margin:0 auto;
            display:grid;
            grid-template-columns:repeat(4, minmax(0, 1fr));
            grid-template-rows:repeat(4, minmax(0, 1fr));
            border:3px solid {theme_dark};
        }}
        .cell {{
            min-width:0;
            min-height:0;
            box-sizing:border-box;
            border:1px solid {theme_border};
            padding:clamp(3px, 1.1vw, 7px);
            position:relative;
            overflow:hidden;
            text-align:center;
            background:#fffdf8 !important;
            color:#111827 !important;
        }}
        .house-no {{
            position:absolute;
            top:3px;
            left:5px;
            font-size:clamp(9px, 2.0vw, 12px);
            line-height:1;
            font-weight:800;
            color:{theme_accent} !important;
        }}
        .rasi-label {{
            font-size:clamp(10px, 2.35vw, 15px);
            line-height:1.15;
            font-weight:700;
            color:{theme_dark} !important;
            margin:2px 0 3px;
            overflow-wrap:anywhere;
            word-break:break-all;
            white-space:normal;
        }}
        .planet {{
            font-size:clamp(10px, 2.55vw, 17px);
            line-height:1.18;
            font-weight:700;
            margin:2px 0;
            color:#111827 !important;
            overflow-wrap:anywhere;
            word-break:break-all;
            white-space:normal;
        }}
        .empty {{
            background:#f8f6fb !important;
            border:0;
        }}
        .center {{
            grid-column:2 / 4;
            grid-row:2 / 4;
            border:1px solid {theme_border};
            display:flex;
            align-items:center;
            justify-content:center;
            text-align:center;
            background:{theme_soft} !important;
            font-size:clamp(14px, 3.5vw, 20px);
            line-height:1.25;
            font-weight:800;
            color:{theme_dark} !important;
        }}
        @media (max-width:600px) {{
            .title {{ font-size:22px; margin:5px 0 10px; }}
            .chart {{ width:100%; border-width:2px; }}
            .cell {{ padding:3px; }}
        }}
    </style>
    </head>
    <body>
    <div class="title">{title}</div>
    <div class="chart">
    """

    for r in range(4):
        for c in range(4):
            if r in [1, 2] and c in [1, 2]:
                if r == 1 and c == 1:
                    html += "<div class='center'>ஜாதக<br>கட்டம்</div>"
                continue

            content = cells[r][c]
            if not content:
                content = "<div class='rasi-label'> </div>"
            html += f"<div class='cell'>{content}</div>"

    html += "</div></body></html>"
    return html


# ------------------------------------------------------------
# DASHA ENGINE
# ------------------------------------------------------------
def next_dasha_lord(lord):
    idx = DASHA_ORDER.index(lord)
    return DASHA_ORDER[(idx + 1) % len(DASHA_ORDER)]


def generate_mahadasha(birth_dt, moon_longitude):
    nak_idx, _, fraction = nakshatra_info(moon_longitude)

    first_lord = NAK_LORD_TA[nak_idx]
    elapsed_fraction = fraction
    remaining_years = DASHA_YEARS[first_lord] * (1.0 - elapsed_fraction)

    periods = []

    start = birth_dt
    lord = first_lord

    # First Mahadasha has balance at birth.
    end = add_years_days(start, remaining_years)
    periods.append({
        "lord": lord,
        "start": start,
        "end": end,
        "years": remaining_years,
        "birth_balance": True
    })

    start = end
    lord = next_dasha_lord(lord)

    # Generate sufficiently long sequence (120 years + small margin)
    while (start - birth_dt).days < 130 * 365.2425:
        years = DASHA_YEARS[lord]
        end = add_years_days(start, years)
        periods.append({
            "lord": lord,
            "start": start,
            "end": end,
            "years": years,
            "birth_balance": False
        })
        start = end
        lord = next_dasha_lord(lord)

    return periods


def generate_bhukti(md_lord, md_start, md_end):
    total_md_days = (md_end - md_start).total_seconds()
    result = []

    lord = md_lord
    start = md_start

    for _ in range(9):
        ad_years = DASHA_YEARS[lord]
        md_years = DASHA_YEARS[md_lord]
        fraction = (md_years * ad_years) / (120.0 * md_years)
        # Simplifies to ad_years / 120, but written clearly.
        duration_seconds = total_md_days * (ad_years / 120.0)
        end = start + timedelta(seconds=duration_seconds)

        result.append({
            "md": md_lord,
            "ad": lord,
            "start": start,
            "end": end,
            "days": duration_seconds / 86400.0
        })

        start = end
        lord = next_dasha_lord(lord)

    # Force final endpoint to exact MD end
    result[-1]["end"] = md_end
    result[-1]["days"] = (md_end - result[-1]["start"]).total_seconds() / 86400.0

    return result


def generate_pratyantar(md_lord, ad_lord, ad_start, ad_end):
    ad_days = (ad_end - ad_start).total_seconds()
    result = []

    lord = ad_lord
    start = ad_start

    for _ in range(9):
        pd_years = DASHA_YEARS[lord]
        duration_seconds = ad_days * (pd_years / 120.0)
        end = start + timedelta(seconds=duration_seconds)

        result.append({
            "md": md_lord,
            "ad": ad_lord,
            "pd": lord,
            "start": start,
            "end": end,
            "days": duration_seconds / 86400.0
        })

        start = end
        lord = next_dasha_lord(lord)

    result[-1]["end"] = ad_end
    result[-1]["days"] = (ad_end - result[-1]["start"]).total_seconds() / 86400.0

    return result


def find_current_dasha(mahadasha_list, now):
    for md in mahadasha_list:
        if md["start"] <= now < md["end"]:
            bhuktis = generate_bhukti(md["lord"], md["start"], md["end"])
            current_ad = None
            for ad in bhuktis:
                if ad["start"] <= now < ad["end"]:
                    current_ad = ad
                    break

            if current_ad:
                pds = generate_pratyantar(
                    md["lord"],
                    current_ad["ad"],
                    current_ad["start"],
                    current_ad["end"]
                )
                current_pd = None
                for pd in pds:
                    if pd["start"] <= now < pd["end"]:
                        current_pd = pd
                        break
            else:
                pds = []
                current_pd = None

            return md, current_ad, current_pd, bhuktis, pds

    return None, None, None, [], []


# ------------------------------------------------------------
# TABLE BUILDERS
# ------------------------------------------------------------
def planet_dataframe(chart):
    rows = []

    # Lagna
    lagna = chart["lagna"]
    rows.append({
        "வகை": "லக்னம்",
        "கிரகம்": "லக்னம்",
        "ராசி": RASI_TA[lagna["rasi"]],
        "ராசியில் பாகை": dms(lagna["degree"]),
        "நட்சத்திரம்": NAK_TA[lagna["nak"]],
        "பாதம்": lagna["pada"],
        "நிலை": "-"
    })

    order = ["சூரியன்", "சந்திரன்", "செவ்வாய்", "புதன்", "குரு", "சுக்கிரன்", "சனி", "ராகு", "கேது"]

    for p in order:
        x = chart["planets"][p]
        rows.append({
            "வகை": "கிரகம்",
            "கிரகம்": p,
            "ராசி": RASI_TA[x["rasi"]],
            "ராசியில் பாகை": dms(x["degree"]),
            "நட்சத்திரம்": NAK_TA[x["nak"]],
            "பாதம்": x["pada"],
            "நிலை": "வக்ரம்" if x["retro"] else "நேர்கதி"
        })

    return pd.DataFrame(rows)


def dasha_dataframe(md_list):
    rows = []
    for i, md in enumerate(md_list, start=1):
        rows.append({
            "எண்": i,
            "மகாதசை": md["lord"],
            "தொடக்கம்": date_only(md["start"]),
            "முடிவு": date_only(md["end"]),
            "காலம் (ஆண்டுகள்)": round(md["years"], 3)
        })
    return pd.DataFrame(rows)


def bhukti_dataframe(bhuktis):
    rows = []
    for i, x in enumerate(bhuktis, start=1):
        rows.append({
            "எண்": i,
            "மகாதசை": x["md"],
            "புத்தி": x["ad"],
            "தொடக்கம்": date_only(x["start"]),
            "முடிவு": date_only(x["end"]),
            "நாட்கள்": round(x["days"], 1)
        })
    return pd.DataFrame(rows)


def pratyantar_dataframe(pds):
    rows = []
    for i, x in enumerate(pds, start=1):
        rows.append({
            "எண்": i,
            "மகாதசை": x["md"],
            "புத்தி": x["ad"],
            "அந்தரம்": x["pd"],
            "தொடக்கம்": date_only(x["start"]),
            "முடிவு": date_only(x["end"]),
            "நாட்கள்": round(x["days"], 2)
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------
# HEADER
# ------------------------------------------------------------
st.markdown("<div class='main-title'>🪔 Tamil Astrology Chart</div>", unsafe_allow_html=True)
st.markdown(
    """
    <div class='sub-title'>வேத ஜோதிடம் • லஹிரி அயனாம்சம் • ராசி • நவாம்சம் • விம்சோத்தரி தசா</div>
    <div style="text-align:center; margin:6px auto 18px auto;">
    <span style="display:inline-block; padding:5px 14px; border-radius:18px;
    background:#f0e7ff; color:#5b2a86; font-weight:700; font-size:14px;
    letter-spacing:.4px;">PHASE 1 • PUBLIC LAUNCH</span>
    </div>
    """,
    unsafe_allow_html=True
)

# ------------------------------------------------------------
# INPUT
# ------------------------------------------------------------
with st.sidebar:
    st.header("📝 பிறப்பு விவரங்கள்")

    name = st.text_input("பெயர்", "Rohit")
    birth_date = st.date_input(
        "பிறந்த தேதி",
        date(2000, 10, 1),
        min_value=date(1800, 1, 1),
        max_value=date.today(),
        format="DD-MM-YYYY"
    )

    # 12-hour birth-time entry with explicit AM / PM selection.
    time_col1, time_col2, time_col3 = st.columns([1, 1, 1])
    with time_col1:
        birth_hour_12 = st.selectbox("மணி", list(range(1, 13)), index=10, key="birth_hour_12")
    with time_col2:
        birth_minute = st.selectbox("நிமிடம்", list(range(0, 60)), index=30, format_func=lambda x: f"{x:02d}", key="birth_minute")
    with time_col3:
        birth_ampm = st.selectbox("AM / PM", ["AM", "PM"], index=0, key="birth_ampm")

    birth_hour_24 = birth_hour_12 % 12
    if birth_ampm == "PM":
        birth_hour_24 += 12
    birth_time = time(birth_hour_24, birth_minute)

    # --------------------------------------------------------
    # Birthplace autocomplete / location confirmation
    # --------------------------------------------------------
    if "place_query" not in st.session_state:
        st.session_state.place_query = "Chennai, Tamil Nadu, India"
    if "place_candidates" not in st.session_state:
        st.session_state.place_candidates = []
    if "selected_place_index" not in st.session_state:
        st.session_state.selected_place_index = 0

    place_query = st.text_input(
        "பிறந்த இடம்",
        value=st.session_state.place_query,
        key="birth_place_query",
        help="இடத்தின் பெயரை type செய்து ‘இடத்தை தேடு’ என்பதை அழுத்தவும். சரியான இடத்தை பட்டியலில் இருந்து தேர்வு செய்யலாம்."
    )
    st.session_state.place_query = place_query

    search_col, clear_col = st.columns([3, 1])
    with search_col:
        search_place = st.button("🔎 இடத்தை தேடு", use_container_width=True)
    with clear_col:
        clear_place = st.button("✕", use_container_width=True, help="தேடல் முடிவுகளை அழிக்க")

    if clear_place:
        st.session_state.place_candidates = []
        st.session_state.selected_place_index = 0
        st.rerun()

    if search_place:
        if len(place_query.strip()) < 3:
            st.warning("குறைந்தது 3 எழுத்துகள் உள்ளிடவும்.")
        else:
            with st.spinner("இடங்களை தேடுகிறது..."):
                st.session_state.place_candidates = search_place_candidates(place_query.strip())
                st.session_state.selected_place_index = 0
            if not st.session_state.place_candidates:
                st.warning("பொருத்தமான இடம் கிடைக்கவில்லை. நகரம் / மாவட்டம் / மாநிலம் சேர்த்து மீண்டும் தேடவும்.")

    place_candidates = st.session_state.get("place_candidates", [])
    selected_place = None

    if place_candidates:
        labels = [c["display"] for c in place_candidates]
        selected_label = st.selectbox(
            "சரியான பிறந்த இடத்தை தேர்வு செய்யவும்",
            labels,
            index=min(st.session_state.get("selected_place_index", 0), len(labels) - 1),
            key="birth_place_selection"
        )
        st.session_state.selected_place_index = labels.index(selected_label)
        selected_place = place_candidates[st.session_state.selected_place_index]

        st.caption(
            f"📍 {selected_place['latitude']:.4f}° N, "
            f"{abs(selected_place['longitude']):.4f}° {'E' if selected_place['longitude'] >= 0 else 'W'}  •  "
            f"Time Zone: {selected_place['timezone']}"
        )

    gender = st.selectbox("பாலினம் / Gender", ["ஆண் / Male", "பெண் / Female", "மற்றவை / Other"], index=0)

    calculate = st.button("🔮 ஜாதகத்தை கணக்கிடுக", use_container_width=True)

    st.markdown("---")
    st.markdown(
        "<div class='small-note'>கணக்கீட்டில் Swiss Ephemeris மற்றும் Lahiri Ayanamsa பயன்படுத்தப்படுகிறது.</div>",
        unsafe_allow_html=True
    )

# Automatically calculate on first load as well.
if "calculated" not in st.session_state:
    st.session_state.calculated = False

if calculate:
    st.session_state.calculated = True

if st.session_state.calculated:

    try:
        if not name.strip():
            st.warning("தயவுசெய்து பெயரை உள்ளிடவும்.")
            st.stop()
        if not place_query.strip():
            st.warning("தயவுசெய்து பிறந்த இடத்தை உள்ளிடவும்.")
            st.stop()
        with st.spinner("ஜாதகம் கணக்கிடப்படுகிறது..."):
            # Use the user's confirmed location candidate whenever available.
            # This avoids spelling/geocoding ambiguity for public users.
            if selected_place is not None:
                lat = selected_place["latitude"]
                lon = selected_place["longitude"]
                tzname = selected_place["timezone"]
                full_address = selected_place["display"]
            else:
                lat, lon, tzname, full_address = geocode_place(place_query)

            dt_local = datetime.combine(birth_date, birth_time)

            chart = calculate_chart(
                dt_local,
                lat,
                lon,
                tzname
            )

            place = full_address
            birth_dt = chart["datetime_local"]

            # Current date/time in birth-place timezone
            now_local = datetime.now(ZoneInfo(tzname))

            moon_lon = chart["planets"]["சந்திரன்"]["longitude"]

            md_list = generate_mahadasha(
                birth_dt,
                moon_lon
            )

            current_md, current_ad, current_pd, current_bhuktis, current_pds = find_current_dasha(
                md_list,
                now_local
            )

    except Exception as e:
        st.error(f"கணக்கீட்டில் பிழை: {e}")
        st.stop()

    # --------------------------------------------------------
    # BIRTH SUMMARY
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>1. பிறப்பு விவரங்கள்</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1.25, 1.0, 1.0, 1.15])

    c1.metric("பெயர்", name)
    c2.metric("பிறந்த தேதி", birth_date.strftime("%d-%m-%Y"))
    c3.metric("பிறந்த நேரம்", birth_time.strftime("%H:%M"))
    c4.metric("Time Zone", tzname)

    st.info(
        f"**பிறந்த இடம்:** {full_address}  \n"
        f"**அட்சரேகை:** {lat:.6f}°  |  **தீர்க்கரேகை:** {lon:.6f}°  \n"
        f"**லஹிரி அயனாம்சம்:** {chart['ayanamsa']:.6f}°"
    )

    # --------------------------------------------------------
    # BASIC ASTROLOGY
    # --------------------------------------------------------
    lagna = chart["lagna"]
    moon = chart["planets"]["சந்திரன்"]

    st.markdown("<div class='section-title'>2. முக்கிய ஜாதக விவரங்கள் / பிறப்பு & பஞ்சாங்க தகவல்கள்</div>", unsafe_allow_html=True)

    detail_rows = detailed_birth_info(
        chart, name, gender, lat, lon, tzname, full_address
    )
    detail_df = pd.DataFrame(detail_rows, columns=["விவரம்", "மதிப்பு"])
    display_wrapped_table(
        detail_df,
        column_widths=["34%", "66%"],
        font_size=15
    )

    st.info(
        f"**லக்ன நட்சத்திரம்:** {NAK_TA[lagna['nak']]} — "
        f"**{lagna['pada']}ஆம் பாதம்**  |  "
        f"**யோகி / அவயோகி:** விரிவான பஞ்சாங்க விவரங்களில் காட்டப்பட்டுள்ளது."
    )

    # --------------------------------------------------------
    # PLANETARY TABLE
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>3. கிரக நிலைகள்</div>", unsafe_allow_html=True)

    pdf = planet_dataframe(chart)
    st.dataframe(
        pdf,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # RASI CHART
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>4. ராசி கட்டம் — D1</div>", unsafe_allow_html=True)

    rasi_placements = []

    rasi_placements.append({
        "rasi": lagna["rasi"],
        "text": "லக்னம்"
    })

    for p in ["சூரியன்", "சந்திரன்", "செவ்வாய்", "புதன்", "குரு", "சுக்கிரன்", "சனி", "ராகு", "கேது"]:
        rasi_placements.append({
            "rasi": chart["planets"][p]["rasi"],
            "planet": p
        })

    components.html(
        make_chart_html(
            "ராசி கட்டம் — D1",
            rasi_placements
        ),
        height=860,
        scrolling=False
    )

    # --------------------------------------------------------
    # NAVAMSA CHART
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>5. நவாம்சம் — D9</div>", unsafe_allow_html=True)

    nav_placements = []

    nav_lagna = navamsa_sign(lagna["longitude"])
    nav_placements.append({
        "rasi": nav_lagna,
        "text": "நவாம்ச லக்னம்"
    })

    for p in ["சூரியன்", "சந்திரன்", "செவ்வாய்", "புதன்", "குரு", "சுக்கிரன்", "சனி", "ராகு", "கேது"]:
        lon = chart["planets"][p]["longitude"]
        nav_placements.append({
            "rasi": navamsa_sign(lon),
            "planet": p
        })

    components.html(
        make_chart_html(
            "நவாம்ச கட்டம் — D9",
            nav_placements
        ),
        height=860,
        scrolling=False
    )

    # --------------------------------------------------------
    # NAVAMSA TABLE
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>6. நவாம்ச கிரக நிலைகள்</div>", unsafe_allow_html=True)

    nav_rows = [{
        "வகை": "லக்னம்",
        "கிரகம்": "லக்னம்",
        "நவாம்ச ராசி": RASI_TA[nav_lagna]
    }]

    for p in ["சூரியன்", "சந்திரன்", "செவ்வாய்", "புதன்", "குரு", "சுக்கிரன்", "சனி", "ராகு", "கேது"]:
        nav_rows.append({
            "வகை": "கிரகம்",
            "கிரகம்": p,
            "நவாம்ச ராசி": RASI_TA[
                navamsa_sign(chart["planets"][p]["longitude"])
            ]
        })

    st.dataframe(
        pd.DataFrame(nav_rows),
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # DASHA CURRENT
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>7. தற்போதைய விம்சோத்தரி தசா</div>", unsafe_allow_html=True)

    if current_md and current_ad and current_pd:

        st.markdown(
            f"""
            <div class="dasha-current">
            <h3>🔱 தற்போதைய தசா நிலை</h3>
            <p><b>மகாதசை:</b> {current_md['lord']} &nbsp; | &nbsp;
            <b>புத்தி:</b> {current_ad['ad']} &nbsp; | &nbsp;
            <b>அந்தரம்:</b> {current_pd['pd']}</p>

            <p><b>மகாதசை:</b>
            {date_only(current_md['start'])} முதல் {date_only(current_md['end'])} வரை</p>

            <p><b>புத்தி:</b>
            {date_only(current_ad['start'])} முதல் {date_only(current_ad['end'])} வரை</p>

            <p><b>அந்தரம்:</b>
            {date_only(current_pd['start'])} முதல் {date_only(current_pd['end'])} வரை</p>

            <p><b>கணக்கிடப்பட்ட தேதி:</b> {date_only(now_local)}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # ALL MAHADASHA
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>8. முழு மகாதசை கால அட்டவணை</div>", unsafe_allow_html=True)

    st.dataframe(
        dasha_dataframe(md_list),
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # CURRENT MD BHUKTI
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>9. தற்போதைய மகாதசையின் அனைத்து புத்திகள்</div>", unsafe_allow_html=True)

    if current_md:
        st.dataframe(
            bhukti_dataframe(current_bhuktis),
            use_container_width=True,
            hide_index=True
        )

    # --------------------------------------------------------
    # CURRENT AD PRATYANTAR
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>10. தற்போதைய புத்தியின் அனைத்து அந்தரங்கள்</div>", unsafe_allow_html=True)

    if current_ad:
        st.dataframe(
            pratyantar_dataframe(current_pds),
            use_container_width=True,
            hide_index=True
        )

    # --------------------------------------------------------
    # CURRENT PERIOD HIERARCHY
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>11. தற்போதைய தசா அடுக்கு</div>", unsafe_allow_html=True)

    if current_md and current_ad and current_pd:
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown(
                f"""
                <div class="info-card">
                <h4>மகாதசை</h4>
                <h2>{current_md['lord']}</h2>
                <p>{date_only(current_md['start'])} → {date_only(current_md['end'])}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

        with c2:
            st.markdown(
                f"""
                <div class="info-card">
                <h4>புத்தி</h4>
                <h2>{current_ad['ad']}</h2>
                <p>{date_only(current_ad['start'])} → {date_only(current_ad['end'])}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

        with c3:
            st.markdown(
                f"""
                <div class="info-card">
                <h4>அந்தரம்</h4>
                <h2>{current_pd['pd']}</h2>
                <p>{date_only(current_pd['start'])} → {date_only(current_pd['end'])}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

    # --------------------------------------------------------
    # BHAVA ANALYSIS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>12. பாவ நிலை — 12 பாவங்களின் சுருக்கம்</div>", unsafe_allow_html=True)

    house_df = build_house_table(chart)
    display_wrapped_table(
        house_df,
        column_widths=["8%", "14%", "38%", "40%"],
        font_size=13
    )

    # --------------------------------------------------------
    # GRAHA ASPECTS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>13. கிரக பார்வைகள்</div>", unsafe_allow_html=True)

    aspect_df = graha_aspects(chart)
    display_wrapped_table(
        aspect_df,
        column_widths=["18%", "18%", "18%", "46%"],
        font_size=13
    )

    # --------------------------------------------------------
    # YOGA SCREENING
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>14. யோகங்கள் — ஆரம்பகட்ட விதி அடிப்படையிலான ஆய்வு</div>", unsafe_allow_html=True)

    st.warning(
        "இது பாரம்பரிய வேத ஜோதிட விதிகளை அடிப்படையாகக் கொண்ட screening மட்டும். "
        "ஒரு யோகத்தின் முழு பலனை நிர்ணயிக்க கிரக பலம், பாவ அதிபதியம், பார்வை, "
        "நவாம்சம், தசா மற்றும் பிற விதிகளையும் சேர்த்து ஆய்வு செய்ய வேண்டும்."
    )

    for title, explanation in basic_yoga_checks(chart):
        st.markdown(
            f"""
            <div class="info-card">
            <h4>🔹 {title}</h4>
            <p>{explanation}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # TAMIL INTERPRETATION
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>15. தமிழ் ஜாதக சுருக்க விளக்கம்</div>", unsafe_allow_html=True)

    lagna_name = RASI_TA[lagna["rasi"]]
    moon_name = RASI_TA[moon["rasi"]]

    st.markdown(
        f"""
        <div class="info-card">
        <h3>🌿 அடிப்படை நிலை</h3>
        <p>
        உங்கள் லக்னம் <b>{lagna_name}</b>. 
        ஜன்ம ராசி <b>{moon_name}</b>. 
        ஜன்ம நட்சத்திரம் <b>{NAK_TA[moon["nak"]]}</b>,
        <b>{moon["pada"]}ஆம் பாதம்</b>.
        </p>
        <p>
        வாழ்க்கை தொடர்பான எந்த முடிவையும் ஒரு கிரகத்தின் ஒரே நிலையை வைத்து
        முடிவு செய்யாமல், லக்னம், சந்திரன், பாவங்கள், தசா மற்றும் நவாம்சம்
        ஆகியவற்றை ஒருங்கிணைத்து பார்க்க வேண்டும்.
        </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # CURRENT DASHA INTERPRETATION
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>16. தற்போதைய தசா — தமிழ் விளக்க வழிகாட்டி</div>", unsafe_allow_html=True)

    st.markdown(current_dasha_tamil_explanation(
        current_md,
        current_ad,
        current_pd
    ))

    if current_md:
        st.write(
            f"**மகாதசை அதிபதி:** {current_md['lord']} — "
            f"{date_only(current_md['start'])} முதல் {date_only(current_md['end'])} வரை."
        )

    if current_ad:
        st.write(
            f"**புத்தி அதிபதி:** {current_ad['ad']} — "
            f"{date_only(current_ad['start'])} முதல் {date_only(current_ad['end'])} வரை."
        )

    if current_pd:
        st.write(
            f"**அந்தர அதிபதி:** {current_pd['pd']} — "
            f"{date_only(current_pd['start'])} முதல் {date_only(current_pd['end'])} வரை."
        )

    # --------------------------------------------------------
    # DISCLAIMER
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>17. முக்கிய குறிப்பு</div>", unsafe_allow_html=True)

    st.info(
        "இந்த மென்பொருள் ஜோதிட கணக்கீடு மற்றும் பாரம்பரிய விதி அடிப்படையிலான "
        "விளக்கத்திற்காக உருவாக்கப்படுகிறது. இது மருத்துவம், சட்டம், முதலீடு, "
        "திருமணம் அல்லது வாழ்க்கையின் முக்கிய முடிவுகளுக்கான உறுதியான முன்னறிவிப்பு "
        "அல்லது தொழில்முறை ஆலோசனை அல்ல."
    )

    # --------------------------------------------------------
    # PLANETARY STRENGTH / DIGNITY
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>18. கிரக பலம் — உச்சம் / நீசம் / சுயராசி / அஸ்தம் / வர்க்கோத்தமம்</div>", unsafe_allow_html=True)

    strength_df = planet_strength_table(chart)
    st.dataframe(
        strength_df,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "குறிப்பு: அஸ்தம் மற்றும் கிரக பலம் இங்கு ஆரம்பகட்ட rule-based calculation. "
        "முழுமையான Shadbala இதற்கு அடுத்த கட்டத்தில் சேர்க்கலாம்."
    )

    # --------------------------------------------------------
    # TRANSIT
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>19. இன்றைய கோச்சார நிலை</div>", unsafe_allow_html=True)

    try:
        transit_df, transit_now = current_transit_snapshot(chart, tzname)

        st.write(
            f"**கோச்சார கணக்கீட்டு தேதி:** {date_only(transit_now)}"
        )

        st.dataframe(
            transit_df,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("#### 🌙 சந்திர ராசியிலிருந்து கோச்சார நிலை")

        moon_transit_df = transit_from_moon(chart, transit_df)

        st.dataframe(
            moon_transit_df,
            use_container_width=True,
            hide_index=True
        )

    except Exception as e:
        st.warning(f"கோச்சார கணக்கீடு கிடைக்கவில்லை: {e}")

    # --------------------------------------------------------
    # LIFE AREA ANALYSIS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>20. வாழ்க்கையின் முக்கிய பகுதிகள் — ஆய்வு வழிகாட்டி</div>", unsafe_allow_html=True)

    life_df = life_area_summary(chart)

    display_wrapped_table(
        life_df,
        column_widths=["19%", "13%", "28%", "40%"],
        font_size=13
    )

    # --------------------------------------------------------
    # RULE ENGINE ROADMAP
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>21. அடுத்த கட்ட Rule Engine</div>", unsafe_allow_html=True)

    st.markdown("""
    இந்த version-ல் software architecture பின்வரும் விரிவாக்கங்களுக்கு தயாராக உள்ளது:

    - **Shadbala** — ஸ்தான பலம், திக் பலம், கால பலம் போன்றவை
    - **Vargottama** மற்றும் பல துணைவர்க்கங்கள்
    - **Neecha Bhanga Raja Yoga** முழுமையான விதிகள்
    - **Raja Yoga / Dhana Yoga** rule engine
    - **திருமண ஆய்வு** — 7ஆம் பாவம் + 7ஆம் அதிபதி + சுக்கிரன் + D9 + தசா
    - **குழந்தை ஆய்வு** — 5ஆம் பாவம் + குரு + D7
    - **தொழில் ஆய்வு** — 10ஆம் பாவம் + 10ஆம் அதிபதி + சனி + தசா
    - **செல்வ / லாப ஆய்வு** — 2, 5, 9, 11 பாவங்கள்
    - **வெளிநாடு / பயணம்** — 3, 9, 12 பாவங்கள்
    - **கோச்சாரம் + தசா ஒருங்கிணைந்த analysis**
    - **Ashtakavarga**
    - **தமிழில் automatic report generation**
    """)

    # --------------------------------------------------------
    # EXPLAINABLE RULE ENGINE
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>22. Explainable Rule Engine — விதி → ஆதாரம் → விளக்கம்</div>", unsafe_allow_html=True)

    st.info(
        "இந்த பகுதி ஒரு முடிவை மட்டும் காட்டாமல், அந்த முடிவை உருவாக்கிய "
        "அடிப்படை ஜோதிட விதி மற்றும் chart evidence-ஐ காட்டுகிறது."
    )

    rule_df = pd.DataFrame(rule_engine(chart))
    display_wrapped_table(
        rule_df,
        column_widths=["15%", "25%", "25%", "35%"],
        font_size=12
    )

    # --------------------------------------------------------
    # NEECHA BHANGA
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>23. நீசபங்க ஆய்வு</div>", unsafe_allow_html=True)

    st.dataframe(
        neecha_bhanga_screening(chart),
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "இது முழுமையான நீசபங்க ராஜயோக தீர்ப்பு அல்ல; முக்கிய பாரம்பரிய விதிகளுக்கான ஆரம்ப screening."
    )

    # --------------------------------------------------------
    # LIFE AREA CARDS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>24. முக்கிய வாழ்க்கை பகுதிகளின் ஆய்வு</div>", unsafe_allow_html=True)

    area_df = life_area_summary(chart)

    for _, row in area_df.iterrows():
        st.markdown(
            f"""
            <div class="info-card">
            <h4>🔹 {row['வாழ்க்கை பகுதி']}</h4>
            <p><b>ஆய்வு பாவம்:</b> {row['ஆய்வு செய்யப்படும் பாவம்']}</p>
            <p><b>உள்ள கிரகங்கள்:</b> {row['உள்ள கிரகங்கள்']}</p>
            <p>{row['குறிப்பு']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # EDUCATIONAL SCORE
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>25. ஜாதக அடிப்படை Strength Indicator</div>", unsafe_allow_html=True)

    score, label, score_reasons = scoring_summary(chart)

    c1, c2 = st.columns([1, 3])

    with c1:
        st.metric("அடிப்படை குறியீடு", f"{score}/100")

    with c2:
        st.write(f"**வகை:** {label}")
        for r in score_reasons:
            st.caption("• " + r)

    st.warning(
        "இந்த மதிப்பெண் எந்தவிதமான உறுதியான எதிர்கால probability அல்ல. "
        "இது software-இல் chart structure-ஐ சுருக்கமாக புரிந்து கொள்ள உதவும் "
        "educational indicator மட்டுமே."
    )

    # --------------------------------------------------------
    # DETAILED LIFE AREA ANALYSIS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>26. விரிவான வாழ்க்கை பகுதி ஆய்வு</div>", unsafe_allow_html=True)

    detailed_df = detailed_area_analysis(chart)

    detailed_display_df = detailed_df[
        [
            "வாழ்க்கை பகுதி",
            "பாவம்",
            "பாவ அதிபதி",
            "அதிபதி இருக்கும் பாவம்",
            "மதிப்பீட்டு நிலை",
            "ஆதார காரணங்கள்"
        ]
    ]

    display_wrapped_table(
        detailed_display_df,
        column_widths=["17%", "11%", "13%", "14%", "17%", "28%"],
        font_size=12
    )

    st.markdown("#### 📌 ஒவ்வொரு பகுதியின் விளக்கம்")

    for _, row in detailed_df.iterrows():
        st.markdown(
            f"""
            <div class="info-card">
            <h4>{row['வாழ்க்கை பகுதி']}</h4>
            <p><b>ஆய்வு பாவம்:</b> {row['பாவம்']}</p>
            <p><b>பாவ அதிபதி:</b> {row['பாவ அதிபதி']} —
            {row['அதிபதி இருக்கும் பாவம்']}ஆம் பாவம்</p>
            <p><b>மதிப்பீடு:</b> {row['மதிப்பீட்டு நிலை']}</p>
            <p><b>விதி அடிப்படை:</b> {row['ஆய்வு அடிப்படை']}</p>
            <p><b>ஆதாரம்:</b> {row['ஆதார காரணங்கள்']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # DASHA ACTIVATION
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>27. தற்போதைய தசா செயல்படுத்தும் பாவங்கள்</div>", unsafe_allow_html=True)

    activation_df = dasha_area_activation(
        chart,
        current_md,
        current_ad,
        current_pd
    )

    if not activation_df.empty:
        display_wrapped_table(
            activation_df,
            column_widths=["18%", "13%", "24%", "45%"],
            font_size=13
        )

        st.info(
            "தற்போதைய மகாதசை, புத்தி மற்றும் அந்தர கிரகங்கள் ஜாதகத்தில் "
            "எந்த பாவங்களை செயல்படுத்துகின்றன என்பதை இந்த அட்டவணை காட்டுகிறது."
        )

    # --------------------------------------------------------
    # AUTOMATIC TAMIL REPORT
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>28. முழுமையான தமிழ் ஜாதக அறிக்கை</div>", unsafe_allow_html=True)

    report_text = generate_tamil_report_text(
        chart,
        current_md,
        current_ad,
        current_pd,
        name
    )

    st.text_area(
        "அறிக்கை",
        report_text,
        height=500
    )

    st.download_button(
        "⬇️ முழு தமிழ் அறிக்கையை TXT ஆக பதிவிறக்கவும்",
        report_text.encode("utf-8-sig"),
        "tamil_jathaga_report.txt",
        "text/plain",
        use_container_width=True
    )

    # --------------------------------------------------------
    # DIVISIONAL CHARTS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>29. துணைவர்க்க ஜாதகங்கள் — D7 / D10 / D12</div>", unsafe_allow_html=True)

    st.info(
        "துணைவர்க்கங்கள் குறிப்பிட்ட வாழ்க்கைப் பகுதிகளை ஆழமாக ஆய்வு செய்ய பயன்படுகின்றன. "
        "D7 குழந்தைகள், D10 தொழில், D12 பெற்றோர்/வம்சம் தொடர்பான ஆய்வுகளுக்கான முக்கிய வர்க்கங்களாக "
        "பாரம்பரியமாகப் பயன்படுத்தப்படுகின்றன."
    )

    tab_d7, tab_d10, tab_d12 = st.tabs([
        "👶 D7 — சப்தாம்சம்",
        "💼 D10 — தசாம்சம்",
        "🌳 D12 — த்வாதசாம்சம்"
    ])

    for tab, mode in [
        (tab_d7, "D7"),
        (tab_d10, "D10"),
        (tab_d12, "D12")
    ]:
        with tab:
            title, varga_df, varga_placements = varga_chart_data(chart, mode)

            components.html(
                make_chart_html(
                    title,
                    varga_placements
                ),
                height=860,
                scrolling=False
            )

            st.dataframe(
                varga_df,
                use_container_width=True,
                hide_index=True
            )

            if mode == "D7":
                st.caption(
                    "D7 சப்தாம்சம்: குழந்தைகள், சந்தானம் மற்றும் அதனுடன் தொடர்புடைய "
                    "வாழ்க்கைத் துறைகளை ஆய்வு செய்ய பாரம்பரியமாகப் பயன்படுத்தப்படுகிறது."
                )
            elif mode == "D10":
                st.caption(
                    "D10 தசாம்சம்: தொழில், பதவி, நிர்வாகம், பொது வாழ்க்கை மற்றும் "
                    "தொழில்முறை நிலையை ஆய்வு செய்ய பாரம்பரியமாகப் பயன்படுத்தப்படுகிறது."
                )
            else:
                st.caption(
                    "D12 த்வாதசாம்சம்: பெற்றோர், குடும்ப மரபு மற்றும் வம்சத் தொடர்பான "
                    "ஆய்வுகளுக்கு பாரம்பரியமாகப் பயன்படுத்தப்படுகிறது."
                )

    # --------------------------------------------------------
    # CURRENT DASHA HIGHLIGHT
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>30. தசா அட்டவணையில் தற்போதைய காலத்தை Highlight செய்தல்</div>", unsafe_allow_html=True)

    if current_md:
        md_df = dasha_dataframe(md_list)
        md_styled = md_df.style.apply(
            lambda row: dasha_style(row, current_md["lord"]),
            axis=1
        )
        display_wrapped_table(
            md_df,
            use_container_width=True,
            hide_index=True
        )

    if current_ad:
        st.markdown("#### தற்போதைய மகாதசையின் புத்தி")
        ad_df = bhukti_dataframe(current_bhuktis)
        ad_styled = ad_df.style.apply(
            lambda row: dasha_style(row, current_ad["ad"]),
            axis=1
        )
        display_wrapped_table(
            ad_df,
            use_container_width=True,
            hide_index=True
        )

    if current_pd:
        st.markdown("#### தற்போதைய புத்தியின் அந்தரம்")
        pd_df = pratyantar_dataframe(current_pds)
        pd_styled = pd_df.style.apply(
            lambda row: dasha_style(row, current_pd["pd"]),
            axis=1
        )
        display_wrapped_table(
            pd_df,
            use_container_width=True,
            hide_index=True
        )

    # --------------------------------------------------------
    # ADVANCED BALA
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>31. மேம்பட்ட கிரக பல குறியீடுகள்</div>", unsafe_allow_html=True)

    st.info(
        "இந்த பகுதி முழுமையான பாரம்பரிய Shadbala அல்ல. "
        "ஸ்தான நிலை, திக் பலம், இயக்க நிலை மற்றும் இயற்கை பலத்தை "
        "ஒரே diagnostic table-ல் காட்டுகிறது. முழுமையான Shadbala-வை "
        "அடுத்த கட்டத்தில் தனித்தனி sub-components உடன் விரிவாக்கலாம்."
    )

    bala_df = qualitative_bala_table(chart)
    display_wrapped_table(
        bala_df,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # ASHTAKAVARGA INDICATOR
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>32. அஷ்டகவர்க்க ஆதரவு குறியீடு</div>", unsafe_allow_html=True)

    st.info(
        "ராசி வாரியான ஆதரவு புள்ளிகள் இங்கு ஒரு வெளிப்படையான Ashtakavarga-style "
        "indicator ஆக வழங்கப்படுகிறது. இது முழுமையான classical Sarvashtakavarga "
        "bindu calculation என்று கருத வேண்டாம்."
    )

    av_df = ashtakavarga_indicator(chart)
    display_wrapped_table(
        av_df,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # ADVANCED YOGA ENGINE
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>33. மேம்பட்ட யோக ஆய்வு</div>", unsafe_allow_html=True)

    yoga_df = advanced_yoga_engine(chart)

    display_wrapped_table(
        yoga_df,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # DASHA + YOGA ACTIVATION
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>34. தசா + யோக செயல்பாட்டு ஆய்வு</div>", unsafe_allow_html=True)

    dasha_yoga_df = dasha_yoga_activation(
        chart,
        current_md,
        current_ad,
        current_pd
    )

    if not dasha_yoga_df.empty:
        display_wrapped_table(
            dasha_yoga_df,
            use_container_width=True,
            hide_index=True
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>35. ஆய்வு சுருக்கம்</div>", unsafe_allow_html=True)

    st.markdown("""
    **ல் software இப்போது பின்வரும் அடுக்குகளை ஒருங்கிணைக்கிறது:**

    1. D1 ராசி
    2. D9 நவாம்சம்
    3. D7 சப்தாம்சம்
    4. D10 தசாம்சம்
    5. D12 த்வாதசாம்சம்
    6. 12 பாவங்கள்
    7. கிரக பார்வைகள்
    8. கிரக dignity / combustion / retrograde
    9. Mahadasha
    10. Bhukti
    11. Pratyantardasha
    12. கோச்சாரம்
    13. Explainable Rule Engine
    14. வாழ்க்கை பகுதி ஆய்வு
    15. யோக screening
    16. Bala diagnostic
    17. Ashtakavarga-style support indicator
    18. தமிழ் அறிக்கை
    """)

    # --------------------------------------------------------
    # SPECIALIZED ANALYSIS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>36. சிறப்பு வாழ்க்கை பகுதி ஆய்வு — Rule Engine</div>", unsafe_allow_html=True)

    st.info(
        "இந்த பகுதி பாரம்பரிய ஜோதிட விதிகளை software rules ஆக மாற்றி "
        "சாதக/கலப்பு/கூடுதல் ஆய்வு தேவை போன்ற குறியீடுகளை வழங்குகிறது. "
        "இது உறுதியான எதிர்கால prediction அல்ல."
    )

    specialized_df = specialized_area_engine(chart)

    display_wrapped_table(
        specialized_df,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # MARRIAGE TIMING
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>37. திருமணம் — தசா அடிப்படையிலான கால சாளரங்கள்</div>", unsafe_allow_html=True)

    marriage_df = marriage_timing_table(chart, md_list)

    if not marriage_df.empty:
        display_wrapped_table(
            marriage_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("குறிப்பிட்ட rule-engine criteria அடிப்படையில் கால சாளரம் கிடைக்கவில்லை.")

    # --------------------------------------------------------
    # CAREER TIMING
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>38. தொழில் — தசா அடிப்படையிலான கால சாளரங்கள்</div>", unsafe_allow_html=True)

    career_df = career_timing_table(chart, md_list)
    if not career_df.empty:
        display_wrapped_table(
            career_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("குறிப்பிட்ட தொழில் criteria அடிப்படையில் கால சாளரம் கிடைக்கவில்லை.")

    # --------------------------------------------------------
    # FINANCE TIMING
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>39. செல்வம் / லாபம் — தசா அடிப்படையிலான கால சாளரங்கள்</div>", unsafe_allow_html=True)

    finance_df = finance_timing_table(chart, md_list)
    if not finance_df.empty:
        display_wrapped_table(
            finance_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("குறிப்பிட்ட செல்வ criteria அடிப்படையில் கால சாளரம் கிடைக்கவில்லை.")

    # --------------------------------------------------------
    # CHILDREN TIMING
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>40. குழந்தைகள் — தசா அடிப்படையிலான கால சாளரங்கள்</div>", unsafe_allow_html=True)

    children_df = children_timing_table(chart, md_list)
    if not children_df.empty:
        display_wrapped_table(
            children_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("குறிப்பிட்ட குழந்தைகள் criteria அடிப்படையில் கால சாளரம் கிடைக்கவில்லை.")

    # --------------------------------------------------------
    # PROPERTY TIMING
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>41. சொத்து / வீடு — தசா அடிப்படையிலான கால சாளரங்கள்</div>", unsafe_allow_html=True)

    property_df = property_timing_table(chart, md_list)
    if not property_df.empty:
        display_wrapped_table(
            property_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("குறிப்பிட்ட சொத்து criteria அடிப்படையில் கால சாளரம் கிடைக்கவில்லை.")

    # --------------------------------------------------------
    # FOREIGN TRAVEL TIMING
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>42. வெளிநாடு — தசா அடிப்படையிலான கால சாளரங்கள்</div>", unsafe_allow_html=True)

    foreign_df = foreign_timing_table(chart, md_list)
    if not foreign_df.empty:
        display_wrapped_table(
            foreign_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("குறிப்பிட்ட வெளிநாட்டு பயணம் criteria அடிப்படையில் கால சாளரம் கிடைக்கவில்லை.")

    # --------------------------------------------------------
    # REPORT NOTE
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>43. ஆய்வு குறிப்பு</div>", unsafe_allow_html=True)

    st.markdown("""
    **கால சாளரம்** என்பது ஒரு குறிப்பிட்ட தசா/புத்தி காலத்தில் சம்பந்தப்பட்ட
    பாவங்கள் அல்லது காரக கிரகங்கள் செயல்படும் வாய்ப்பை காட்டுகிறது.

    இது “இந்த நிகழ்வு இந்த தேதியில் நிச்சயம் நடக்கும்” என்ற prediction அல்ல.
    தசா + கோச்சாரம் + D9/D7/D10 + பாவ பலம் + கிரக பலம் ஆகியவற்றை இணைத்தே
    இறுதி ஜோதிட விளக்கம் உருவாக்கப்பட வேண்டும்.
    """)

    # --------------------------------------------------------
    # PROFESSIONAL REPORT
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>44. தொழில்முறை தமிழ் ஜாதக அறிக்கை</div>", unsafe_allow_html=True)

    complete_report = build_complete_report_sections(
        chart,
        name,
        gender,
        full_address,
        md_list,
        current_md,
        current_ad,
        current_pd,
        specialized_df,
        yoga_df,
        strength_df
    )

    st.text_area(
        "முழுமையான அறிக்கை Preview",
        complete_report,
        height=650
    )

    st.download_button(
        "⬇️ தமிழ் முழு அறிக்கை — TXT",
        complete_report.encode("utf-8-sig"),
        "tamil_jathaga_full_report.txt",
        "text/plain",
        use_container_width=True
    )

    try:
        pdf_path = "/mnt/data/tamil_jathaga_report.pdf"
        create_pdf_report(complete_report, pdf_path)

        with open(pdf_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()

        st.download_button(
            "📄 தமிழ் முழு அறிக்கை — PDF",
            pdf_bytes,
            "tamil_jathaga_report.pdf",
            "application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.warning(
            "PDF உருவாக்கம் இந்த கணினியில் கிடைக்கவில்லை. "
            f"TXT report தொடர்ந்து பயன்படுத்தலாம். விவரம்: {e}"
        )

    # --------------------------------------------------------
    # BHAVA LORD MATRIX
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>45. 12 பாவ அதிபதி — முழுமையான Matrix</div>", unsafe_allow_html=True)

    st.info(
        "ஒவ்வொரு பாவத்தின் ராசி, அதிபதி, அதிபதி இருக்கும் பாவம், "
        "அந்த பாவத்தில் உள்ள கிரகங்கள் மற்றும் பாவத்தின் பொருள் ஆகியவை "
        "ஒரே அட்டவணையில் காட்டப்படுகின்றன."
    )

    bhava_df = bhava_lord_matrix(chart)
    display_wrapped_table(
        bhava_df,
        column_widths=["8%", "10%", "13%", "14%", "20%", "35%"],
        font_size=13
    )

    # --------------------------------------------------------
    # PLANETARY ASPECT MATRIX
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>46. கிரக பார்வை — முழுமையான Matrix</div>", unsafe_allow_html=True)

    aspect_df = planetary_aspect_matrix(chart)

    display_wrapped_table(
        aspect_df,
        column_widths=["13%", "15%", "14%", "18%", "40%"],
        font_size=13
    )

    st.caption(
        "பார்வை விதிகளில் செவ்வாய்க்கு 4/7/8, குருவுக்கு 5/7/9, "
        "சனிக்கு 3/7/10 மற்றும் பிற கிரகங்களுக்கு 7ஆம் பார்வை பயன்படுத்தப்பட்டுள்ளது."
    )

    # --------------------------------------------------------
    # KARAKA MATRIX
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>47. கிரக காரகத்துவம் — தமிழ் Reference</div>", unsafe_allow_html=True)

    karaka_df = karaka_matrix(chart)

    display_wrapped_table(
        karaka_df,
        column_widths=["12%", "15%", "35%", "38%"],
        font_size=13
    )

    # --------------------------------------------------------
    # HOUSE STRENGTH OVERVIEW
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>48. 12 பாவங்களின் ஒருங்கிணைந்த Strength Overview</div>", unsafe_allow_html=True)

    house_strength_df = house_strength_overview(chart)

    display_wrapped_table(
        house_strength_df,
        column_widths=["8%", "9%", "12%", "12%", "18%", "17%", "24%"],
        font_size=12
    )

    # --------------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>49. ஜாதக ஆய்வு Dashboard</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1.25, 1.0, 1.0, 1.15])

    with c1:
        st.metric("லக்னம்", RASI_TA[chart["lagna"]["rasi"]])

    with c2:
        st.metric("ஜன்ம ராசி", RASI_TA[chart["planets"]["சந்திரன்"]["rasi"]])

    with c3:
        st.metric("நட்சத்திரம்", NAK_TA[chart["planets"]["சந்திரன்"]["nak"]])

    with c4:
        st.metric(
            "தற்போதைய தசை",
            current_md["lord"] if current_md else "-"
        )

    st.success(
        "ல் பாவ அதிபதி, கிரக பார்வை, காரகத்துவம் மற்றும் "
        "12 பாவ Strength ஆகியவை ஒருங்கிணைக்கப்பட்டுள்ளன. "
        "இவை அடுத்த கட்டத்தில் திருமணம், தொழில், செல்வம் போன்ற "
        "தனி ஆய்வு reports-க்கு நேரடியாக பயன்படுத்தக்கூடிய structured data ஆகும்."
    )

    # --------------------------------------------------------
    # COMPLETE MARRIAGE ANALYSIS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>50. ஒருங்கிணைந்த ஜாதக Dashboard — நிறைவு</div>", unsafe_allow_html=True)

    st.success(
        "D1, D9, D7, D10, D12, பாவ அதிபதி, கிரக பார்வை, காரகத்துவம், "
        "யோகங்கள், Bala மற்றும் Ashtakavarga-style indicators ஆகியவை "
        "வரை ஒருங்கிணைக்கப்பட்டுள்ளன. அடுத்த பகுதி திருமண ஆய்வு."
    )

    st.markdown("<div class='section-title'>51. திருமணம் — முழுமையான D1 + D9 ஆய்வு</div>", unsafe_allow_html=True)

    marriage_core = marriage_core_analysis(chart)
    marriage_d9 = marriage_d9_analysis(chart)
    manglik = manglik_screening(chart)
    marriage_delay = marriage_delay_screening(chart)

    st.success(
        marriage_summary_text(
            marriage_core,
            marriage_d9,
            manglik,
            marriage_delay
        )
    )

    marriage_core_df = pd.DataFrame([
        {
            "ஆய்வு": "7ஆம் பாவம்",
            "விவரம்": RASI_TA[marriage_core["seventh_sign"]],
            "முடிவு": "திருமணம் / கூட்டாண்மை ஆய்வின் முக்கிய பாவம்"
        },
        {
            "ஆய்வு": "7ஆம் அதிபதி",
            "விவரம்": f"{marriage_core['seventh_lord']} — {marriage_core['seventh_lord_house']}ஆம் பாவம்",
            "முடிவு": marriage_core["level"]
        },
        {
            "ஆய்வு": "7ஆம் பாவத்தில் உள்ள கிரகங்கள்",
            "விவரம்": ", ".join(marriage_core["occupants"]) if marriage_core["occupants"] else "-",
            "முடிவு": "கூடுதல் ஆய்வு"
        },
        {
            "ஆய்வு": "சுக்கிரன்",
            "விவரம்": f"{marriage_core['venus_house']}ஆம் பாவம்",
            "முடிவு": "திருமண காரகன்"
        },
        {
            "ஆய்வு": "குரு",
            "விவரம்": f"{marriage_core['jupiter_house']}ஆம் பாவம்",
            "முடிவு": "குடும்பம் / தர்மம் / சந்தான காரகன்"
        }
    ])

    display_wrapped_table(
        marriage_core_df,
        column_widths=["25%", "35%", "40%"],
        font_size=13
    )

    st.markdown("#### D1 திருமண ஆய்வு — ஆதாரங்கள்")
    display_wrapped_table(
        pd.DataFrame({
            "ஆதாரம்": marriage_core["evidence"]
        }),
        column_widths=["100%"],
        font_size=13
    )

    # --------------------------------------------------------
    # D9 MARRIAGE CONFIRMATION
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>52. நவாம்சம் D9 — திருமண உறுதி ஆய்வு</div>", unsafe_allow_html=True)

    d9_df = pd.DataFrame([
        {
            "ஆய்வு": "D9 லக்னம்",
            "விவரம்": RASI_TA[marriage_d9["d9_lagna"]],
            "மதிப்பீடு": "திருமணத்தின் நுண்ணிய ஆய்வுக்கான அடிப்படை"
        },
        {
            "ஆய்வு": "D9 7ஆம் அதிபதி",
            "விவரம்": f"{marriage_d9['seventh_lord']} — {marriage_d9['seventh_lord_house']}ஆம் பாவம்",
            "மதிப்பீடு": marriage_d9["level"]
        },
        {
            "ஆய்வு": "D9 7ஆம் பாவ கிரகங்கள்",
            "விவரம்": ", ".join(marriage_d9["occupants"]) if marriage_d9["occupants"] else "-",
            "மதிப்பீடு": "தொடர்புடைய கிரகங்களை இணைத்து பார்க்க வேண்டும்"
        },
        {
            "ஆய்வு": "D9 சுக்கிரன்",
            "விவரம்": f"{marriage_d9['d9_houses']['சுக்கிரன்']}ஆம் பாவம்",
            "மதிப்பீடு": "திருமண காரகன்"
        }
    ])

    display_wrapped_table(
        d9_df,
        column_widths=["25%", "35%", "40%"],
        font_size=13
    )

    display_wrapped_table(
        pd.DataFrame({"D9 ஆதாரம்": marriage_d9["evidence"]}),
        column_widths=["100%"],
        font_size=13
    )

    # --------------------------------------------------------
    # MANGAL DOSHA SCREENING
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>53. செவ்வாய் தோஷம் — பல கோண Screening</div>", unsafe_allow_html=True)

    manglik_df = pd.DataFrame([
        {
            "அடிப்படை": "லக்னம்",
            "செவ்வாய் இருக்கும் பாவம்": manglik["d1_mars_house"],
            "Screening": "ஆம்" if manglik["d1_flag"] else "இல்லை"
        },
        {
            "அடிப்படை": "சந்திர லக்னம்",
            "செவ்வாய் இருக்கும் பாவம்": manglik["moon_mars_house"],
            "Screening": "ஆம்" if manglik["moon_flag"] else "இல்லை"
        },
        {
            "அடிப்படை": "சுக்கிர லக்னம்",
            "செவ்வாய் இருக்கும் பாவம்": manglik["venus_mars_house"],
            "Screening": "ஆம்" if manglik["venus_flag"] else "இல்லை"
        },
        {
            "அடிப்படை": "D9 லக்னம்",
            "செவ்வாய் இருக்கும் பாவம்": manglik["d9_mars_house"],
            "Screening": "ஆம்" if manglik["d9_flag"] else "இல்லை"
        }
    ])

    display_wrapped_table(
        manglik_df,
        column_widths=["30%", "35%", "35%"],
        font_size=13
    )

    st.warning(
        "இது ஒரு screening மட்டும். செவ்வாய் தோஷத்திற்கு பாரம்பரிய விதிவிலக்குகள், "
        "ராசி, அதிபதி நிலை, குரு பார்வை, சுக்கிர நிலை மற்றும் இரு ஜாதக பொருத்தம் "
        "ஆகியவற்றை இணைத்தே இறுதி முடிவு செய்ய வேண்டும்."
    )

    # --------------------------------------------------------
    # MARRIAGE DELAY SCREENING
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>54. திருமண தாமதம் — Rule Based Screening</div>", unsafe_allow_html=True)

    delay_df = pd.DataFrame([
        {
            "குறியீடு": marriage_delay["score"],
            "மதிப்பீடு": marriage_delay["level"],
            "ஆதாரம்": " | ".join(marriage_delay["reasons"]) if marriage_delay["reasons"] else "வலுவான தாமத குறியீடு இல்லை"
        }
    ])

    display_wrapped_table(
        delay_df,
        column_widths=["12%", "32%", "56%"],
        font_size=13
    )

    # --------------------------------------------------------
    # MARRIAGE TIMING
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>55. திருமணம் — Mahadasha / Bhukti கால சாளரங்கள்</div>", unsafe_allow_html=True)

    marriage_timing_df = marriage_timing_v16(chart, md_list)

    if not marriage_timing_df.empty:
        display_wrapped_table(
            marriage_timing_df,
            column_widths=["12%", "12%", "13%", "13%", "18%", "9%", "23%"],
            font_size=12
        )
    else:
        st.info("தற்போதைய 15 ஆண்டு window-ல் இந்த rule engine அடிப்படையில் குறிப்பிடத்தக்க கால சாளரம் கிடைக்கவில்லை.")

    # --------------------------------------------------------
    # MARRIAGE INTERPRETATION
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>56. திருமண ஆய்வு — ஒருங்கிணைந்த விளக்கம்</div>", unsafe_allow_html=True)

    st.markdown(f"""
    **D1:** {marriage_core["level"]}

    **D9:** {marriage_d9["level"]}

    **செவ்வாய் தோஷ screening:** {manglik["level"]}

    **திருமண தாமத screening:** {marriage_delay["level"]}

    **முக்கியமான D1 ஆதாரங்கள்:** {"; ".join(marriage_core["evidence"]) if marriage_core["evidence"] else "குறிப்பிடத்தக்க rule இல்லை"}

    **முக்கியமான D9 ஆதாரங்கள்:** {"; ".join(marriage_d9["evidence"]) if marriage_d9["evidence"] else "குறிப்பிடத்தக்க rule இல்லை"}
    """)

    # --------------------------------------------------------
    # DISCLAIMER
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>57. திருமண ஆய்வு குறிப்பு</div>", unsafe_allow_html=True)

    st.info(
        "திருமண timing மற்றும் தாமத மதிப்பீடுகள் rule-based Jyotish screening ஆகும். "
        "இவை உறுதியான நிகழ்வு prediction அல்ல. D1 + D9 + தசா + கோச்சாரம் + "
        "இரு ஜாதக பொருத்தம் ஆகியவற்றை ஒருங்கிணைத்தால்தான் விரிவான திருமண மதிப்பீடு செய்ய வேண்டும்."
    )

    # --------------------------------------------------------
    # COMPLETE CAREER ANALYSIS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>58. திருமண ஆய்வு — நிறைவு</div>", unsafe_allow_html=True)

    st.success(
        "ல் D1 + D9 திருமண ஆய்வு, செவ்வாய் தோஷ screening, "
        "திருமண தாமத screening மற்றும் Mahadasha/Bhukti timing "
        "ஒருங்கிணைக்கப்பட்டுள்ளது. அடுத்த பகுதி தொழில் ஆய்வு."
    )

    st.markdown("<div class='section-title'>59. தொழில் — முழுமையான D1 + D10 ஆய்வு</div>", unsafe_allow_html=True)

    career_core = career_core_analysis(chart)
    career_d10 = career_d10_analysis(chart)
    career_sector_df = career_sector_screening(chart)

    st.success(
        career_summary_text(career_core, career_d10)
    )

    career_core_df = pd.DataFrame([
        {
            "ஆய்வு": "10ஆம் பாவம்",
            "விவரம்": RASI_TA[career_core["tenth_sign"]],
            "முடிவு": "தொழில் / பதவி / பொறுப்பு ஆய்வின் முக்கிய பாவம்"
        },
        {
            "ஆய்வு": "10ஆம் அதிபதி",
            "விவரம்": f"{career_core['tenth_lord']} — {career_core['tenth_lord_house']}ஆம் பாவம்",
            "முடிவு": career_core["level"]
        },
        {
            "ஆய்வு": "10ஆம் பாவ கிரகங்கள்",
            "விவரம்": ", ".join(career_core["tenth_occupants"]) if career_core["tenth_occupants"] else "-",
            "முடிவு": "தொழில் தன்மையை மாற்றக்கூடிய முக்கிய குறியீடு"
        },
        {
            "ஆய்வு": "6ஆம் அதிபதி",
            "விவரம்": career_core["sixth_lord"],
            "முடிவு": "வேலை / சேவை / போட்டி"
        },
        {
            "ஆய்வு": "11ஆம் அதிபதி",
            "விவரம்": career_core["eleventh_lord"],
            "முடிவு": "லாபம் / முன்னேற்றம் / network"
        }
    ])

    display_wrapped_table(
        career_core_df,
        column_widths=["25%", "35%", "40%"],
        font_size=13
    )

    st.markdown("#### D1 தொழில் ஆய்வு — ஆதாரங்கள்")
    display_wrapped_table(
        pd.DataFrame({"ஆதாரம்": career_core["evidence"]}),
        column_widths=["100%"],
        font_size=13
    )

    # --------------------------------------------------------
    # D10 ANALYSIS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>60. D10 தசாம்சம் — தொழில் நுண்ணிய ஆய்வு</div>", unsafe_allow_html=True)

    d10_df = pd.DataFrame([
        {
            "ஆய்வு": "D10 லக்னம்",
            "விவரம்": RASI_TA[career_d10["d10_lagna"]],
            "மதிப்பீடு": "தொழில் நுண்ணிய ஆய்வின் அடிப்படை"
        },
        {
            "ஆய்வு": "D10 10ஆம் அதிபதி",
            "விவரம்": f"{career_d10['tenth_lord']} — {career_d10['tenth_lord_house']}ஆம் பாவம்",
            "மதிப்பீடு": career_d10["level"]
        },
        {
            "ஆய்வு": "D10 10ஆம் பாவ கிரகங்கள்",
            "விவரம்": ", ".join(career_d10["occupants"]) if career_d10["occupants"] else "-",
            "மதிப்பீடு": "தொழில் துறையின் தன்மைக்கு முக்கியம்"
        }
    ])

    display_wrapped_table(
        d10_df,
        column_widths=["25%", "35%", "40%"],
        font_size=13
    )

    display_wrapped_table(
        pd.DataFrame({"D10 ஆதாரம்": career_d10["evidence"]}),
        column_widths=["100%"],
        font_size=13
    )

    # --------------------------------------------------------
    # CAREER SECTOR
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>61. தொழில் துறை சாத்தியங்கள்</div>", unsafe_allow_html=True)

    display_wrapped_table(
        career_sector_df,
        column_widths=["30%", "22%", "12%", "36%"],
        font_size=12
    )

    # --------------------------------------------------------
    # CAREER TIMING
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>62. தொழில் முன்னேற்றம் — Mahadasha / Bhukti கால சாளரங்கள்</div>", unsafe_allow_html=True)

    career_timing_df = career_timing_v17(chart, md_list)

    if not career_timing_df.empty:
        display_wrapped_table(
            career_timing_df,
            column_widths=["12%", "12%", "13%", "13%", "18%", "9%", "23%"],
            font_size=12
        )
    else:
        st.info(
            "அடுத்த 15 ஆண்டு window-ல் இந்த rule engine அடிப்படையில் "
            "குறிப்பிடத்தக்க தொழில் கால சாளரம் கிடைக்கவில்லை."
        )

    # --------------------------------------------------------
    # CAREER INTERPRETATION
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>63. தொழில் — ஒருங்கிணைந்த விளக்கம்</div>", unsafe_allow_html=True)

    st.markdown(f"""
    **D1 தொழில் நிலை:** {career_core["level"]}

    **D10 தொழில் நிலை:** {career_d10["level"]}

    **10ஆம் அதிபதி:** {career_core["tenth_lord"]} — {career_core["tenth_lord_house"]}ஆம் பாவம்

    **முக்கிய ஆதாரங்கள்:** {"; ".join(career_core["evidence"]) if career_core["evidence"] else "குறிப்பிடத்தக்க rule இல்லை"}

    **D10 ஆதாரங்கள்:** {"; ".join(career_d10["evidence"]) if career_d10["evidence"] else "குறிப்பிடத்தக்க rule இல்லை"}
    """)

    # --------------------------------------------------------
    # DISCLAIMER
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>64. தொழில் ஆய்வு குறிப்பு</div>", unsafe_allow_html=True)

    st.info(
        "தொழில் துறை மற்றும் timing மதிப்பீடுகள் rule-based Jyotish screening ஆகும். "
        "இவை உறுதியான promotion, job change அல்லது income prediction அல்ல. "
        "D1 + D10 + தசா + கோச்சாரம் + பாவ பலம் ஆகியவற்றை ஒருங்கிணைத்தே "
        "விரிவான தொழில் விளக்கம் செய்ய வேண்டும்."
    )

    # --------------------------------------------------------
    # COMPLETE WEALTH ANALYSIS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>65. தொழில் ஆய்வு — நிறைவு</div>", unsafe_allow_html=True)

    st.success(
        "ல் D1 + D10 தொழில் ஆய்வு, தொழில் துறை screening மற்றும் "
        "Mahadasha/Bhukti தொழில் timing ஒருங்கிணைக்கப்பட்டுள்ளது. "
        "அடுத்த பகுதி செல்வ / Finance ஆய்வு."
    )

    st.markdown("<div class='section-title'>66. செல்வம் / Finance — முழுமையான D1 + D2 ஆய்வு</div>", unsafe_allow_html=True)

    wealth_core = wealth_core_analysis(chart)
    wealth_d2 = wealth_d2_analysis(chart)
    wealth_source_df = wealth_source_screening(chart)

    st.success(
        wealth_summary_text(wealth_core, wealth_d2)
    )

    wealth_core_df = pd.DataFrame([
        {
            "ஆய்வு": "2ஆம் பாவம்",
            "விவரம்": f"அதிபதி {wealth_core['second_lord']}",
            "முடிவு": "சேமிப்பு / குடும்ப செல்வம்"
        },
        {
            "ஆய்வு": "5ஆம் பாவம்",
            "விவரம்": f"அதிபதி {wealth_core['fifth_lord']}",
            "முடிவு": "முதலீடு / speculative intelligence"
        },
        {
            "ஆய்வு": "9ஆம் பாவம்",
            "விவரம்": f"அதிபதி {wealth_core['ninth_lord']}",
            "முடிவு": "அதிர்ஷ்டம் / தர்மம் / wealth support"
        },
        {
            "ஆய்வு": "11ஆம் பாவம்",
            "விவரம்": f"அதிபதி {wealth_core['eleventh_lord']}",
            "முடிவு": "லாபம் / வருமான உயர்வு"
        },
        {
            "ஆய்வு": "மொத்த மதிப்பீடு",
            "விவரம்": f"குறியீடு {wealth_core['score']}",
            "முடிவு": wealth_core["level"]
        }
    ])

    display_wrapped_table(
        wealth_core_df,
        column_widths=["25%", "35%", "40%"],
        font_size=13
    )

    st.markdown("#### D1 செல்வ ஆய்வு — ஆதாரங்கள்")
    display_wrapped_table(
        pd.DataFrame({"ஆதாரம்": wealth_core["evidence"]}),
        column_widths=["100%"],
        font_size=13
    )

    # --------------------------------------------------------
    # D2 ANALYSIS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>67. D2 ஹோரா — செல்வ நுண்ணிய ஆய்வு</div>", unsafe_allow_html=True)

    d2_df = pd.DataFrame([
        {
            "ஆய்வு": "D2 லக்னம்",
            "விவரம்": RASI_TA[wealth_d2["d2_lagna"]],
            "மதிப்பீடு": "செல்வத்தின் நுண்ணிய ஆய்வுக்கான அடிப்படை"
        },
        {
            "ஆய்வு": "D2 2ஆம் அதிபதி",
            "விவரம்": f"{wealth_d2['second_lord']} — {wealth_d2['d2_houses'][wealth_d2['second_lord']]}ஆம் பாவம்",
            "மதிப்பீடு": "சேமிப்பு / wealth holding"
        },
        {
            "ஆய்வு": "D2 11ஆம் அதிபதி",
            "விவரம்": f"{wealth_d2['eleventh_lord']} — {wealth_d2['d2_houses'][wealth_d2['eleventh_lord']]}ஆம் பாவம்",
            "மதிப்பீடு": "லாபம் / inflow"
        },
        {
            "ஆய்வு": "D2 மொத்த மதிப்பீடு",
            "விவரம்": f"குறியீடு {wealth_d2['score']}",
            "மதிப்பீடு": wealth_d2["level"]
        }
    ])

    display_wrapped_table(
        d2_df,
        column_widths=["25%", "35%", "40%"],
        font_size=13
    )

    display_wrapped_table(
        pd.DataFrame({"D2 ஆதாரம்": wealth_d2["evidence"]}),
        column_widths=["100%"],
        font_size=13
    )

    # --------------------------------------------------------
    # WEALTH SOURCES
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>68. செல்வம் உருவாகக்கூடிய மூலாதாரங்கள்</div>", unsafe_allow_html=True)

    display_wrapped_table(
        wealth_source_df,
        column_widths=["30%", "22%", "12%", "36%"],
        font_size=12
    )

    # --------------------------------------------------------
    # WEALTH TIMING
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>69. செல்வம் / லாபம் — Mahadasha / Bhukti கால சாளரங்கள்</div>", unsafe_allow_html=True)

    wealth_timing_df = wealth_timing_v18(chart, md_list)

    if not wealth_timing_df.empty:
        display_wrapped_table(
            wealth_timing_df,
            column_widths=["12%", "12%", "13%", "13%", "18%", "9%", "23%"],
            font_size=12
        )
    else:
        st.info(
            "அடுத்த 15 ஆண்டு window-ல் இந்த rule engine அடிப்படையில் "
            "குறிப்பிடத்தக்க செல்வ கால சாளரம் கிடைக்கவில்லை."
        )

    # --------------------------------------------------------
    # WEALTH INTERPRETATION
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>70. செல்வம் — ஒருங்கிணைந்த விளக்கம்</div>", unsafe_allow_html=True)

    st.markdown(f"""
    **D1 செல்வ நிலை:** {wealth_core["level"]}

    **D2 செல்வ நிலை:** {wealth_d2["level"]}

    **2ஆம் அதிபதி:** {wealth_core["second_lord"]}

    **11ஆம் அதிபதி:** {wealth_core["eleventh_lord"]}

    **முக்கிய ஆதாரங்கள்:** {"; ".join(wealth_core["evidence"]) if wealth_core["evidence"] else "குறிப்பிடத்தக்க rule இல்லை"}

    **D2 ஆதாரங்கள்:** {"; ".join(wealth_d2["evidence"]) if wealth_d2["evidence"] else "குறிப்பிடத்தக்க rule இல்லை"}
    """)

    # --------------------------------------------------------
    # FINANCE DISCLAIMER
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>71. செல்வ ஆய்வு குறிப்பு</div>", unsafe_allow_html=True)

    st.warning(
        "இது ஜோதிட rule-based wealth analysis மட்டுமே. "
        "இதை பங்குச்சந்தை, முதலீடு, வருமானம் அல்லது நிதி முடிவுகளுக்கான "
        "உறுதியான prediction அல்லது financial advice ஆக பயன்படுத்தக்கூடாது."
    )

    # --------------------------------------------------------
    # CHILDREN / EDUCATION ANALYSIS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>72. செல்வ / Finance ஆய்வு — நிறைவு</div>", unsafe_allow_html=True)

    st.success(
        "ல் D1 + D2 செல்வ ஆய்வு, செல்வ மூலாதார screening மற்றும் "
        "Mahadasha/Bhukti wealth timing ஒருங்கிணைக்கப்பட்டுள்ளது. "
        "அடுத்த பகுதி குழந்தைகள் / கல்வி ஆய்வு."
    )

    st.markdown("<div class='section-title'>73. குழந்தைகள் / சந்தானம் — D1 ஆய்வு</div>", unsafe_allow_html=True)

    children_core = children_core_analysis(chart)
    education_core = education_core_analysis(chart)
    children_d7 = children_d7_analysis(chart)
    education_stream_df = education_stream_screening(chart)

    st.success(
        children_summary_text(
            children_core,
            education_core,
            children_d7
        )
    )

    children_core_df = pd.DataFrame([
        {
            "ஆய்வு": "5ஆம் பாவம்",
            "விவரம்": RASI_TA[children_core["fifth_sign"]],
            "முடிவு": "சந்தானம் / புத்தி / கல்வியின் முக்கிய பாவம்"
        },
        {
            "ஆய்வு": "5ஆம் அதிபதி",
            "விவரம்": f"{children_core['fifth_lord']} — {children_core['fifth_lord_house']}ஆம் பாவம்",
            "முடிவு": children_core["level"]
        },
        {
            "ஆய்வு": "5ஆம் பாவ கிரகங்கள்",
            "விவரம்": ", ".join(children_core["occupants"]) if children_core["occupants"] else "-",
            "முடிவு": "சந்தான / கல்வி தன்மைக்கு முக்கியம்"
        },
        {
            "ஆய்வு": "குரு",
            "விவரம்": f"{planet_houses(chart)['குரு']}ஆம் பாவம்",
            "முடிவு": "சந்தான காரகன்"
        },
        {
            "ஆய்வு": "மொத்த மதிப்பீடு",
            "விவரம்": f"குறியீடு {children_core['score']}",
            "முடிவு": children_core["level"]
        }
    ])

    display_wrapped_table(
        children_core_df,
        column_widths=["25%", "35%", "40%"],
        font_size=13
    )

    st.markdown("#### சந்தான D1 ஆய்வு — ஆதாரங்கள்")
    display_wrapped_table(
        pd.DataFrame({"ஆதாரம்": children_core["evidence"]}),
        column_widths=["100%"],
        font_size=13
    )

    # --------------------------------------------------------
    # EDUCATION
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>74. கல்வி / அறிவுத்திறன் — முழுமையான ஆய்வு</div>", unsafe_allow_html=True)

    education_df = pd.DataFrame([
        {
            "ஆய்வு": "4ஆம் / 5ஆம் / 9ஆம் பாவங்கள்",
            "விவரம்": "கல்வி, புத்தி, உயர்கல்வி",
            "மதிப்பீடு": education_core["level"]
        },
        {
            "ஆய்வு": "முக்கிய அதிபதிகள்",
            "விவரம்": ", ".join(education_core["education_lords"]),
            "மதிப்பீடு": f"குறியீடு {education_core['score']}"
        }
    ])

    display_wrapped_table(
        education_df,
        column_widths=["28%", "37%", "35%"],
        font_size=13
    )

    display_wrapped_table(
        pd.DataFrame({"கல்வி ஆதாரம்": education_core["evidence"]}),
        column_widths=["100%"],
        font_size=13
    )

    # --------------------------------------------------------
    # D7
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>75. D7 சப்தாம்சம் — சந்தான நுண்ணிய ஆய்வு</div>", unsafe_allow_html=True)

    d7_df = pd.DataFrame([
        {
            "ஆய்வு": "D7 லக்னம்",
            "விவரம்": RASI_TA[children_d7["d7_lagna"]],
            "மதிப்பீடு": "சந்தான நுண்ணிய ஆய்வின் அடிப்படை"
        },
        {
            "ஆய்வு": "D7 5ஆம் அதிபதி",
            "விவரம்": f"{children_d7['fifth_lord']} — {children_d7['fifth_lord_house']}ஆம் பாவம்",
            "மதிப்பீடு": children_d7["level"]
        },
        {
            "ஆய்வு": "D7 5ஆம் பாவ கிரகங்கள்",
            "விவரம்": ", ".join(children_d7["occupants"]) if children_d7["occupants"] else "-",
            "மதிப்பீடு": "தொடர்புடைய கிரகங்களை இணைத்து பார்க்க வேண்டும்"
        }
    ])

    display_wrapped_table(
        d7_df,
        column_widths=["25%", "35%", "40%"],
        font_size=13
    )

    display_wrapped_table(
        pd.DataFrame({"D7 ஆதாரம்": children_d7["evidence"]}),
        column_widths=["100%"],
        font_size=13
    )

    # --------------------------------------------------------
    # EDUCATION STREAMS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>76. கல்வித் துறை சாத்தியங்கள்</div>", unsafe_allow_html=True)

    display_wrapped_table(
        education_stream_df,
        column_widths=["30%", "22%", "12%", "36%"],
        font_size=12
    )

    # --------------------------------------------------------
    # CHILDREN TIMING
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>77. சந்தானம் / கல்வி — Mahadasha / Bhukti கால சாளரங்கள்</div>", unsafe_allow_html=True)

    children_timing_df = children_timing_v19(chart, md_list)

    if not children_timing_df.empty:
        display_wrapped_table(
            children_timing_df,
            column_widths=["12%", "12%", "13%", "13%", "18%", "9%", "23%"],
            font_size=12
        )
    else:
        st.info(
            "அடுத்த 15 ஆண்டு window-ல் இந்த rule engine அடிப்படையில் "
            "குறிப்பிடத்தக்க சந்தான / கல்வி கால சாளரம் கிடைக்கவில்லை."
        )

    # --------------------------------------------------------
    # CHILDREN / EDUCATION INTERPRETATION
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>78. குழந்தைகள் / கல்வி — ஒருங்கிணைந்த விளக்கம்</div>", unsafe_allow_html=True)

    st.markdown(f"""
    **சந்தான D1 நிலை:** {children_core["level"]}

    **கல்வி நிலை:** {education_core["level"]}

    **D7 நிலை:** {children_d7["level"]}

    **5ஆம் அதிபதி:** {children_core["fifth_lord"]} — {children_core["fifth_lord_house"]}ஆம் பாவம்

    **முக்கிய D1 ஆதாரங்கள்:** {"; ".join(children_core["evidence"]) if children_core["evidence"] else "குறிப்பிடத்தக்க rule இல்லை"}

    **D7 ஆதாரங்கள்:** {"; ".join(children_d7["evidence"]) if children_d7["evidence"] else "குறிப்பிடத்தக்க rule இல்லை"}
    """)

    # --------------------------------------------------------
    # DISCLAIMER
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>79. சந்தான / கல்வி ஆய்வு குறிப்பு</div>", unsafe_allow_html=True)

    st.info(
        "சந்தானம், கல்வி மற்றும் timing மதிப்பீடுகள் rule-based Jyotish screening ஆகும். "
        "இவை உறுதியான fertility, குழந்தை பிறப்பு அல்லது கல்வி முடிவு prediction அல்ல. "
        "D1 + D7 + தசா + கோச்சாரம் மற்றும் தேவையான பிற ஜோதிட காரணிகளை இணைத்தே விரிவான ஆய்வு செய்ய வேண்டும்."
    )

    # --------------------------------------------------------
    # PROPERTY / RELOCATION
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>80. சொத்து / வீடு / நிலம் — D1 ஆய்வு</div>", unsafe_allow_html=True)
    property_core = property_core_analysis(chart)
    d4_property = d4_property_analysis(chart)
    relocation = relocation_foreign_analysis(chart)
    property_sources = property_source_screening(chart)
    property_timing = property_timing_v20(chart, md_list)

    st.success(property_summary_v20(property_core, d4_property, relocation))

    property_df = pd.DataFrame([
        {"ஆய்வு":"4ஆம் பாவம்","விவரம்":RASI_TA[(chart['lagna']['rasi']+3)%12],"முடிவு":"வீடு / சொத்து / மன அமைதி"},
        {"ஆய்வு":"4ஆம் அதிபதி","விவரம்":f"{property_core['fourth_lord']} — {property_core['fourth_house']}ஆம் பாவம்","முடிவு":property_core['level']},
        {"ஆய்வு":"4ஆம் பாவ கிரகங்கள்","விவரம்":", ".join(property_core['occupants']) or "-","முடிவு":"வீட்டு/சொத்து தன்மை"},
        {"ஆய்வு":"செவ்வாய்","விவரம்":f"{property_core['mars_house']}ஆம் பாவம்","முடிவு":"நிலம் / கட்டிடம்"},
        {"ஆய்வு":"சுக்கிரன்","விவரம்":f"{property_core['venus_house']}ஆம் பாவம்","முடிவு":"வசதி / வீட்டு சுகம்"},
        {"ஆய்வு":"மொத்த குறியீடு","விவரம்":f"{property_core['score']}/100","முடிவு":property_core['level']},
    ])
    display_wrapped_table(property_df, column_widths=["25%","35%","40%"], font_size=13)
    display_wrapped_table(pd.DataFrame({"D1 சொத்து ஆதாரம்":property_core['evidence']}), column_widths=["100%"], font_size=13)

    st.markdown("<div class='section-title'>81. D4 Chaturthamsa — வீடு / நிலம் / சொத்து நுண்ணிய ஆய்வு</div>", unsafe_allow_html=True)
    d4_df=pd.DataFrame([
        {"ஆய்வு":"D4 லக்னம்","விவரம்":RASI_TA[d4_property['lagna']],"முடிவு":"சொத்து/வசிப்பிட நுண்ணிய அடித்தளம்"},
        {"ஆய்வு":"D4 4ஆம் அதிபதி","விவரம்":f"{d4_property['fourth_lord']} — {d4_property['fourth_house']}ஆம் பாவம்","முடிவு":d4_property['level']},
        {"ஆய்வு":"D4 4ஆம் பாவ கிரகங்கள்","விவரம்":", ".join(d4_property['occupants']) or "-","முடிவு":"சொத்து ஆதாரங்கள்"},
        {"ஆய்வு":"D4 குறியீடு","விவரம்":f"{d4_property['score']}/100","முடிவு":d4_property['level']},
    ])
    display_wrapped_table(d4_df, column_widths=["28%","35%","37%"], font_size=13)
    display_wrapped_table(pd.DataFrame(d4_property['placements']), column_widths=["25%","35%","40%"], font_size=12)
    display_wrapped_table(pd.DataFrame({"D4 ஆதாரம்":d4_property['evidence']}), column_widths=["100%"], font_size=13)

    st.markdown("<div class='section-title'>82. சொத்து வகை / மூலாதார Screening</div>", unsafe_allow_html=True)
    display_wrapped_table(property_sources, column_widths=["25%","23%","32%","20%"], font_size=12)

    st.markdown("<div class='section-title'>83. வெளிநாடு / வெளியூர் / இடமாற்ற ஆய்வு</div>", unsafe_allow_html=True)
    relocation_df=pd.DataFrame([
        {"ஆய்வு":"9ஆம் பாவம்","விவரம்":f"அதிபதி {relocation['ninth_lord']}","முடிவு":"தொலைப் பயணம் / உயர்ந்த அனுபவங்கள்"},
        {"ஆய்வு":"12ஆம் பாவம்","விவரம்":f"அதிபதி {relocation['twelfth_lord']}","முடிவு":"வெளிநாடு / வெளிநாட்டு தங்கல்"},
        {"ஆய்வு":"மொத்த குறியீடு","விவரம்":f"{relocation['score']}/100","முடிவு":relocation['level']},
        {"ஆய்வு":"குடியேற்ற screening","விவரம்":relocation['settlement'],"முடிவு":"D1 rule-based முடிவு"},
    ])
    display_wrapped_table(relocation_df, column_widths=["28%","37%","35%"], font_size=13)
    display_wrapped_table(pd.DataFrame({"வெளிநாடு / இடமாற்ற ஆதாரம்":relocation['evidence']}), column_widths=["100%"], font_size=13)

    st.markdown("<div class='section-title'>84. வெளிநாடு / இடமாற்றம் — முக்கிய விதிகள்</div>", unsafe_allow_html=True)
    st.info("3, 7, 9, 12ஆம் பாவங்கள், அவற்றின் அதிபதிகள், ராகு/கேது, சந்திரன் மற்றும் 4ஆம் அதிபதியின் தொடர்புகள் இணைத்து rule-based screening செய்யப்படுகிறது. இது உறுதியான வெளிநாட்டு குடியேற்ற prediction அல்ல.")

    st.markdown("<div class='section-title'>85. சொத்து / இடமாற்றம் — Mahadasha / Bhukti கால சாளரங்கள்</div>", unsafe_allow_html=True)
    if not property_timing.empty:
        display_wrapped_table(property_timing, column_widths=["12%","12%","14%","14%","14%","18%","16%"], font_size=11)
    else:
        st.info("அடுத்த 15 ஆண்டு window-ல் குறிப்பிடத்தக்க சொத்து அல்லது இடமாற்ற activation window கிடைக்கவில்லை.")

    st.markdown("<div class='section-title'>86. சொத்து / வீடு / வெளிநாடு — ஒருங்கிணைந்த விளக்கம்</div>", unsafe_allow_html=True)
    st.markdown(f"""
    **D1 சொத்து நிலை:** {property_core['level']} — {property_core['score']}/100

    **D4 Chaturthamsa நிலை:** {d4_property['level']} — {d4_property['score']}/100

    **வெளிநாடு / இடமாற்ற நிலை:** {relocation['level']} — {relocation['score']}/100

    **குடியேற்ற screening:** {relocation['settlement']}

    **முக்கிய சொத்து ஆதாரங்கள்:** {"; ".join(property_core['evidence']) if property_core['evidence'] else "குறிப்பிடத்தக்க rule இல்லை"}
    """)

    st.markdown("<div class='section-title'>87. சொத்து / இடமாற்ற ஆய்வு குறிப்பு</div>", unsafe_allow_html=True)
    st.warning("D4, 4ஆம் பாவம், 4ஆம் அதிபதி, செவ்வாய், சுக்கிரன், 9/12ஆம் பாவங்கள் மற்றும் தசா/புத்தி அடிப்படையில் இது ஒரு rule-based Jyotish screening. சொத்து வாங்குதல், விற்பனை, கடன், குடியேற்றம் அல்லது வெளிநாட்டு முடிவுகளுக்கு இது உறுதியான prediction அல்லது சட்ட/நிதி ஆலோசனை அல்ல.")

    # --------------------------------------------------------
    # GOCHARA / TRANSIT
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>89. தற்போதைய கோச்சாரம் — கிரக நிலைகள்</div>", unsafe_allow_html=True)
    transit_chart, transit_dt = transit_chart_now()
    gochara_df = gochara_analysis(chart, transit_chart)
    major_transit_df = major_transit_screening(chart, transit_chart)
    synthesis_df = current_dasha_transit_synthesis(chart, current_md, current_ad, transit_chart)
    st.info(f"கோச்சார கணிப்பு நேரம்: {transit_dt.strftime('%d-%m-%Y %H:%M')} IST")
    display_wrapped_table(gochara_df, column_widths=["14%","20%","22%","22%","22%"], font_size=12)

    st.markdown("<div class='section-title'>90. குரு / சனி / ராகு / கேது — முக்கிய கோச்சார Screening</div>", unsafe_allow_html=True)
    display_wrapped_table(major_transit_df, column_widths=["12%","18%","18%","12%","20%","20%"], font_size=11)

    st.markdown("<div class='section-title'>91. தற்போதைய தசா + கோச்சார ஒருங்கிணைப்பு</div>", unsafe_allow_html=True)
    if not synthesis_df.empty:
        display_wrapped_table(synthesis_df, column_widths=["15%","12%","18%","16%","16%","15%","28%"], font_size=11)
    else:
        st.info("தற்போதைய தசா + கோச்சார synthesis தரவு இல்லை.")

    st.markdown("<div class='section-title'>92. கோச்சாரம் — தற்போதைய முக்கிய விளக்கம்</div>", unsafe_allow_html=True)
    st.success(gochara_summary_v21(gochara_df, major_transit_df))

    st.markdown("<div class='section-title'>93. தொழில் / நிதி / சொத்து / குடும்பம் — கோச்சார Activation</div>", unsafe_allow_html=True)
    area_rows=[]
    for area, ref_houses in [("தொழில்",[10,6,11]),("நிதி",[2,5,9,11]),("சொத்து / வீடு",[4,2,11]),("குடும்பம் / உறவு",[2,7,4])]:
        score=0; evidence=[]
        for p in ["குரு","சனி","ராகு","கேது"]:
            tr=transit_chart["planets"][p]["rasi"]
            h=transit_house_from_reference(tr, chart["lagna"]["rasi"])
            if h in ref_houses:
                score+=20; evidence.append(f"{p} {h}ஆம் பாவத்தில்")
        score=min(100,score)
        area_rows.append({"வாழ்க்கை பகுதி":area,"Activation குறியீடு":score,"முக்கிய ஆதாரம்":"; ".join(evidence) if evidence else "குறிப்பிடத்தக்க முக்கிய கோச்சார தொடர்பு இல்லை","மதிப்பீடு":"சாதகமான activation" if score>=40 else "மிதமான / கூடுதல் ஆய்வு"})
    display_wrapped_table(pd.DataFrame(area_rows), column_widths=["22%","18%","40%","20%"], font_size=12)

    st.markdown("<div class='section-title'>94. கோச்சார முடிவு</div>", unsafe_allow_html=True)
    st.markdown(f"""
    **தற்போதைய முக்கிய கோச்சார நிலை:** {gochara_summary_v21(gochara_df, major_transit_df)}

    **சிறந்த நீண்டகால கோச்சார கிரகம்:** {major_transit_df.sort_values('குறியீடு', ascending=False).iloc[0]['கிரகம்'] if not major_transit_df.empty else '-'}

    கோச்சாரத்தை தனியாகப் பார்க்காமல் D1, D9/D10/D4/D7, தற்போதைய தசா-புத்தி மற்றும் பிற timing indicators உடன் இணைத்தே பயன்படுத்த வேண்டும்.
    """)

    st.markdown("<div class='section-title'>95. கோச்சார ஆய்வு குறிப்பு</div>", unsafe_allow_html=True)
    st.warning("இது தற்போதைய கிரக கோச்சாரத்தின் rule-based Jyotish screening மட்டுமே. உறுதியான எதிர்கால prediction அல்ல; முக்கிய வாழ்க்கை முடிவுகளுக்கு தனித்த நிதி, மருத்துவ, சட்ட அல்லது தொழில்முறை ஆலோசனையை பயன்படுத்தவும்.")
# --------------------------------------------------------
    # CSV DOWNLOADS
    # --------------------------------------------------------
    st.markdown("<div class='section-title'>97. தரவு பதிவிறக்கம்</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        csv1 = pdf.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ கிரக நிலைகள் CSV",
            csv1,
            "graha_nilakal.csv",
            "text/csv",
            use_container_width=True
        )

    with col2:
        csv2 = dasha_dataframe(md_list).to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ மகாதசை CSV",
            csv2,
            "mahadasa.csv",
            "text/csv",
            use_container_width=True
        )

    with col3:
        if current_ad:
            csv3 = pratyantar_dataframe(current_pds).to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ அந்தரம் CSV",
                csv3,
                "pratyantar.csv",
                "text/csv",
                use_container_width=True
            )

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;font-size:13px;color:#666;'>"
        "Tamil Astrology Chart • Lahiri Ayanamsa • Swiss Ephemeris"
        "</div>",
        unsafe_allow_html=True
    )

else:
    st.markdown(
        """
        <div style="text-align:center;padding:60px 20px;">
        <h2>🪔 உங்கள் பிறப்பு விவரங்களை உள்ளிடவும்</h2>
        <p style="font-size:18px;">
        இடது பக்கத்தில் பெயர், பிறந்த தேதி, நேரம் மற்றும் பிறந்த இடத்தை உள்ளிட்டு
        <b>“🔮 ஜாதகத்தை கணக்கிடுக”</b> என்பதை அழுத்தவும்.
        </p>
        </div>
        """,
        unsafe_allow_html=True
    )
