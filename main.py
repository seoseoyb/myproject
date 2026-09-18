```python
import io
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go


# ============================================================
# 1. 화면 기본 설정
# ============================================================

st.set_page_config(
    page_title="전국 고령화 지도",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ 전국 시군구 고령화 지도")
st.caption("최신 연도의 시군구별 65세 이상 인구 비율을 나타낸 지도입니다.")


# ============================================================
# 2. 데이터 주소
# ============================================================

# 전국 읍·면·동 인구 데이터
POPULATION_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/"
    "data/population_yearly.csv.gz"
)

# 전국 시군구 경계 데이터
GEOJSON_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/main/"
    "data/boundaries/sigungu_kr.geojson"
)


# ============================================================
# 3. 인구 데이터 불러오기
# ============================================================

@st.cache_data
def load_population_data():
    """인터넷에서 인구 CSV 파일을 받아옵니다."""

    response = requests.get(
        POPULATION_URL,
        timeout=60
    )
    response.raise_for_status()

    # '코드'는 계산용 숫자가 아니라 행정구역을 구분하는 이름표입니다.
    # 따라서 반드시 문자열(string)로 읽습니다.
    df = pd.read_csv(
        io.BytesIO(response.content),
        compression="gzip",
        dtype={"코드": "string"}
    )

    return df


# ============================================================
# 4. 지도 경계 데이터 불러오기
# ============================================================

@st.cache_data
def load_geojson():
    """전국 시군구 경계 GeoJSON을 받아옵니다."""

    response = requests.get(
        GEOJSON_URL,
        timeout=60
    )
    response.raise_for_status()

    return response.json()


# 데이터 불러오기
try:
    population = load_population_data()
    geojson = load_geojson()

except Exception as e:
    st.error("데이터를 불러오는 중 문제가 발생했습니다.")
    st.exception(e)
    st.stop()


# ============================================================
# 5. 가장 최신 연도의 자료만 사용
# ============================================================

population["연도"] = pd.to_numeric(
    population["연도"],
    errors="coerce"
)

latest_year = int(population["연도"].max())

latest = population[
    population["연도"] == latest_year
].copy()


# ============================================================
# 6. 행정동 코드를 시군구 코드로 바꾸기
# ============================================================

# 코드를 문자열로 처리합니다.
latest["코드"] = (
    latest["코드"]
    .astype("string")
    .str.strip()
)

# 혹시 11110515.0처럼 들어온 경우를 대비합니다.
latest["코드"] = latest["코드"].str.replace(
    r"\.0$",
    "",
    regex=True
)

# 행정동 코드의 앞 5자리가 시군구 코드입니다.
latest["시군구코드"] = latest["코드"].str[:5]


# ============================================================
# 7. 나이별 인구 열 찾기
# ============================================================

# '계_'로 시작하는 열은 남녀 전체 인구입니다.
total_age_columns = [
    column
    for column in latest.columns
    if column.startswith("계_")
]


# 65세 이상 나이
elderly_ages = list(range(65, 100)) + ["100세 이상"]


# 65세 이상 전체 인구 열
elderly_total_columns = [
    f"계_{age}"
    for age in elderly_ages
    if f"계_{age}" in latest.columns
]


# 65세 이상 남성 인구 열
elderly_male_columns = [
    f"남_{age}"
    for age in elderly_ages
    if f"남_{age}" in latest.columns
]


# 65세 이상 여성 인구 열
elderly_female_columns = [
    f"여_{age}"
    for age in elderly_ages
    if f"여_{age}" in latest.columns
]


if not total_age_columns:
    st.error("전체 나이별 인구 열을 찾지 못했습니다.")
    st.stop()

if not elderly_total_columns:
    st.error("65세 이상 인구 열을 찾지 못했습니다.")
    st.stop()


# ============================================================
# 8. 인구 열을 숫자로 변환
# ============================================================

# 계산할 수 있도록 인구 데이터를 숫자로 바꿉니다.
for column in total_age_columns:
    latest[column] = pd.to_numeric(
        latest[column],
        errors="coerce"
    ).fillna(0)


for column in elderly_male_columns + elderly_female_columns:
    latest[column] = pd.to_numeric(
        latest[column],
        errors="coerce"
    ).fillna(0)


# ============================================================
# 9. 읍·면·동별 인구 계산
# ============================================================

# 전체 인구
latest["전체인구"] = latest[
    total_age_columns
].sum(axis=1)


# 65세 이상 전체 인구
latest["고령인구"] = latest[
    elderly_total_columns
].sum(axis=1)


# 65세 이상 남성 인구
if elderly_male_columns:
    latest["고령남성인구"] = latest[
        elderly_male_columns
    ].sum(axis=1)
else:
    latest["고령남성인구"] = 0


# 65세 이상 여성 인구
if elderly_female_columns:
    latest["고령여성인구"] = latest[
        elderly_female_columns
    ].sum(axis=1)
else:
    latest["고령여성인구"] = 0


# ============================================================
# 10. 시군구별로 합치기
# ============================================================

# 읍·면·동 자료를 시군구 코드 앞 5자리를 기준으로 합칩니다.
sigungu = (
    latest
    .groupby("시군구코드", as_index=False)
    .agg(
        전체인구=("전체인구", "sum"),
        고령인구=("고령인구", "sum"),
        고령남성인구=("고령남성인구", "sum"),
        고령여성인구=("고령여성인구", "sum")
    )
)


# ============================================================
# 11. 고령화율 계산
# ============================================================

# 고령화율
# = 65세 이상 인구 ÷ 전체 인구 × 100
sigungu["고령화율"] = (
    sigungu["고령인구"]
    / sigungu["전체인구"]
    * 100
)


# ============================================================
# 12. 65세 이상 인구의 남녀 비율 계산
# ============================================================

# 고령인구가 0명인 경우 0으로 처리합니다.

sigungu["남성비율"] = (
    sigungu["고령남성인구"]
    / sigungu["고령인구"]
    * 100
).fillna(0)


sigungu["여성비율"] = (
    sigungu["고령여성인구"]
    / sigungu["고령인구"]
    * 100
).fillna(0)


# ============================================================
# 13. GeoJSON의 시군구 정보 가져오기
# ============================================================

features = geojson.get("features", [])


# GeoJSON의 코드도 문자열로 맞춥니다.
for feature in features:

    properties = feature.get(
        "properties",
        {}
    )

    if "코드" in properties:
        properties["코드"] = str(
            properties["코드"]
        ).strip()[:5]


# GeoJSON에서 시군구 이름과 시도 이름을 가져옵니다.
boundary_info = pd.DataFrame([
    {
        "시군구코드": str(
            feature["properties"].get("코드", "")
        ).strip()[:5],

        "시군구": feature["properties"].get(
            "시군구",
            ""
        ),

        "시도": feature["properties"].get(
            "시도",
            ""
        )
    }

    for feature in features
])


# ============================================================
# 14. 지도 경계 + 인구 데이터를 코드로 연결
# ============================================================

# ★ 이름이 아니라 시군구 코드로 결합합니다.
map_data = boundary_info.merge(
    sigungu,
    on="시군구코드",
    how="left"
)


# ============================================================
# 15. 고령화율을 5단계로 나누기
# ============================================================

# 기준값
# 19% / 23% / 28% / 38%

def classify_ageing_rate(rate):

    if pd.isna(rate):
        return None

    if rate < 19:
        return 0

    elif rate < 23:
        return 1

    elif rate < 28:
        return 2

    elif rate < 38:
        return 3

    else:
        return 4


map_data["단계"] = map_data[
    "고령화율"
].apply(classify_ageing_rate)


# ============================================================
# 16. 지도 범례 문구
# ============================================================

legend_labels = [
    "19% 미만",
    "19% 이상 ~ 23% 미만",
    "23% 이상 ~ 28% 미만",
    "28% 이상 ~ 38% 미만",
    "38% 이상"
]


# ============================================================
# 17. Plotly 단계구분도 만들기
# ============================================================

fig = go.Figure(
    go.Choropleth(

        # GeoJSON 경계
        geojson=geojson,

        # ★ GeoJSON의 '코드'와 데이터의 시군구코드를 연결
        featureidkey="properties.코드",

        locations=map_data[
            "시군구코드"
        ],

        # 지도 색깔을 결정하는 단계
        z=map_data[
            "단계"
        ],

        # 보라색 5단계
        colorscale=[
            [0.00, "#F3E8FF"],
            [0.1999, "#F3E8FF"],

            [0.20, "#D8B4FE"],
            [0.3999, "#D8B4FE"],

            [0.40, "#A855F7"],
            [0.5999, "#A855F7"],

            [0.60, "#7E22CE"],
            [0.7999, "#7E22CE"],

            [0.80, "#4C1D95"],
            [1.00, "#4C1D95"],
        ],

        zmin=0,
        zmax=4,

        # 시군구 경계선
        marker_line_color="white",
        marker_line_width=0.6,

        # 마우스를 올렸을 때 사용할 정보
        customdata=map_data[
            [
                "시군구",
                "시도",
                "고령화율"
            ]
        ].values,

        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "시도: %{customdata[1]}<br>"
            "고령화율: %{customdata[2]:.2f}%"
            "<extra></extra>"
        ),

        # 범례
        colorbar=dict(
            title="고령화율",
            tickmode="array",
            tickvals=[0, 1, 2, 3, 4],
            ticktext=legend_labels,
            len=0.75,
            thickness=18
        )
    )
)


# ============================================================
# 18. 지도 모양 설정
# ============================================================

fig.update_geos(

    # 데이터가 있는 지역에 맞춰 지도 크기 조절
    fitbounds="locations",

    # 기본 Geo 지도 배경을 숨깁니다.
    visible=False,

    # 배경 지도 타일을 사용하지 않습니다.
    showland=False,
    showocean=False,
    showcountries=False,
    showcoastlines=False,

    projection_type="mercator"
)


fig.update_layout(
    height=850,

    margin=dict(
        l=0,
        r=0,
        t=10,
        b=0
    ),

    paper_bgcolor="white",

    font=dict(
        family="Arial, sans-serif"
    )
)


# ============================================================
# 19. 지도 출력
# ============================================================

st.plotly_chart(
    fig,
    use_container_width=True,

    config={
        "displayModeBar": False,
        "scrollZoom": False
    }
)


# ============================================================
# 20. 순위 데이터 만들기
# ============================================================

ranking_data = map_data.dropna(
    subset=["고령화율"]
).copy()


# 고령화율 높은 곳 10개
highest = (
    ranking_data
    .sort_values(
        "고령화율",
        ascending=False
    )
    .head(10)
    .copy()
)


# 고령화율 낮은 곳 10개
lowest = (
    ranking_data
    .sort_values(
        "고령화율",
        ascending=True
    )
    .head(10)
    .copy()
)


# ============================================================
# 21. 표에 표시할 열
# ============================================================

highest_table = highest[
    [
        "시도",
        "시군구",
        "고령화율",
        "남성비율",
        "여성비율"
    ]
].copy()


lowest_table = lowest[
    [
        "시도",
```
