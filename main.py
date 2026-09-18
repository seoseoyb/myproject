import re
import requests
import pandas as pd
import streamlit as st
import plotly.express as px


# ----------------------------------------------------------
# 기본 설정
# ----------------------------------------------------------

st.set_page_config(
    page_title="전국 고령화 지도",
    layout="wide"
)

st.title("🗺️ 전국 고령화 지도")
st.caption(
    "시군구별 65세 이상 인구 비율 (행정안전부 주민등록 인구)"
)


# ----------------------------------------------------------
# 데이터 주소
# ----------------------------------------------------------

POP_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/"
    "data/population_yearly.csv.gz"
)

GEO_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/"
    "data/boundaries/sigungu_kr.geojson"
)


# ----------------------------------------------------------
# 데이터 불러오기
# ----------------------------------------------------------

@st.cache_data(show_spinner="인구 데이터를 불러오는 중입니다...")
def load_population():

    # '코드'는 숫자가 아니라 행정구역을 구분하는 이름표이므로
    # 반드시 글자(str)로 읽습니다.
    return pd.read_csv(
        POP_URL,
        dtype={"코드": str}
    )


@st.cache_data(show_spinner="지도 경계를 불러오는 중입니다...")
def load_geojson():

    response = requests.get(
        GEO_URL,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


df = load_population()
geojson = load_geojson()


# ----------------------------------------------------------
# 1. 가장 최신 연도만 사용
# ----------------------------------------------------------

latest_year = int(
    df["연도"].max()
)

df = df[
    df["연도"] == latest_year
].copy()


# ----------------------------------------------------------
# 2. '계_'로 시작하는 전체 인구 나이 열 찾기
# ----------------------------------------------------------

# '계_'는 남녀를 합친 전체 인구입니다.
# 남_ / 여_ 열을 여기에 더하면 안 됩니다.
total_cols = [
    c for c in df.columns
    if c.startswith("계_")
]


# ----------------------------------------------------------
# 3. 나이 숫자를 찾는 함수
# ----------------------------------------------------------

def age_of(col):

    # 예: 계_65세 → 65
    m = re.match(
        r"계_(\d+)세",
        col
    )

    if m:
        return int(m.group(1))

    # 계_100세 이상 → 100
    if col == "계_100세 이상":
        return 100

    return None


# ----------------------------------------------------------
# 4. 65세 이상 전체 인구 열
# ----------------------------------------------------------

elderly_cols = [
    c
    for c in total_cols
    if age_of(c) is not None
    and age_of(c) >= 65
]


# ----------------------------------------------------------
# 5. 65세 이상 남성 / 여성 열
# ----------------------------------------------------------

# 남성 65세 이상
elderly_male_cols = []

# 여성 65세 이상
elderly_female_cols = []


for age in range(65, 100):

    male_col = f"남_{age}세"
    female_col = f"여_{age}세"

    if male_col in df.columns:
        elderly_male_cols.append(male_col)

    if female_col in df.columns:
        eld
