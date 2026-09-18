```python
import io
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go


# ==========================================================
# 기본 설정
# ==========================================================

st.set_page_config(
    page_title="전국 고령화 지도",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ 전국 고령화 지도")


# ==========================================================
# 데이터 주소
# ==========================================================

POPULATION_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/"
    "data/population_yearly.csv.gz"
)

GEOJSON_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/"
    "data/boundaries/sigungu_kr.geojson"
)


# ==========================================================
# 데이터 불러오기
# ==========================================================

@st.cache_data
def get_population():

    r = requests.get(POPULATION_URL, timeout=120)
    r.raise_for_status()

    # 코드가 숫자로 바뀌지 않도록 문자열로 읽습니다.
    return pd.read_csv(
        io.BytesIO(r.content),
        compression="gzip",
        dtype={"코드": str}
    )


@st.cache_data
def get_geojson():

    r = requests.get(GEOJSON_URL, timeout=120)
    r.raise_for_status()

    return r.json()


# 데이터 가져오기
try:
    population = get_population()
    geojson = get_geojson()

except Exception as e:
    st.error("데이터를 불러오지 못했습니다.")
    st.code(str(e))
    st.stop()


# ==========================================================
# 최신 연도 선택
# ==========================================================

population["연도"] = pd.to_numeric(
    population["연도"],
    errors="coerce"
)

latest_year = int(population["연도"].max())

df = population[
    population["연도"] == latest_year
].copy()


# ==========================================================
# 행정동 코드 → 시군구 코드
# ==========================================================

# 코드는 숫자가 아니라 이름표이므로 문자열로 처리합니다.
df["코드"] = (
    df["코드"]
    .astype(str)
    .str.strip()
    .str.replace(".0", "", regex=False)
)

# 행정동 코드 앞 5자리가 시군구 코드입니다.
df["시군구코드"] = df["코드"].str[:5]


# ==========================================================
# 나이별 열 찾기
# ==========================================================

# 전체 인구 열
total_columns = [
    c for c in df.columns
    if c.startswith("계_")
]


# 65세 이상 열
elderly_total_columns = []

for age in range(65, 100):
    column = f"계_{age}"

    if column in df.columns:
        elderly_total_columns.append(column)

if "계_100세 이상" in df.columns:
    elderly_total_columns.append("계_100세 이상")


# 65세 이상 남성
elderly_male_columns = []

for age in range(65, 100):
    column = f"남_{age}"

    if column in df.columns:
        elderly_male_columns.append(column)

if "남_100세 이상" in df.columns:
    elderly_male_columns.append("남_100세 이상")


# 65세 이상 여성
elderly_female_columns = []

for age in range(65, 100):
    column = f"여_{age}"

    if column in df.columns:
        elderly_female_columns.append(column)

if "여_100세 이상" in df.columns:
    elderly_female_columns.append("여_100세 이상")


# ==========================================================
# 숫자로 변환
# ==========================================================

for column in total_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    ).fillna(0)


for column in elderly_male_columns + elderly_female_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    ).fillna(0)


# =================================================
```
