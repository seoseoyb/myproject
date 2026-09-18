import re
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="전국 고령화 지도", layout="wide")
st.title("🗺️ 전국 고령화 지도")
st.caption("시군구별 65세 이상 인구 비율 및 고령인구 성별 비율")

POP_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"
GEO_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"


@st.cache_data(show_spinner="인구 데이터를 불러오는 중입니다...")
def load_population():
    return pd.read_csv(POP_URL, dtype={"코드": str})


@st.cache_data(show_spinner="지도 경계를 불러오는 중입니다...")
def load_geojson():
    response = requests.get(GEO_URL, timeout=30)
    response.raise_for_status()
    return response.json()


df = load_population()
geojson = load_geojson()


# 1. 가장 최신 연도만 사용
latest_year = int(df["연도"].max())
df = df[df["연도"] == latest_year].copy()


# 2. 전체 인구 열 찾기
total_cols = [c for c in df.columns if c.startswith("계_")]


def age_of(col):
    m = re.match(r"계_(\d+)세", col)
    return int(m.group(1)) if m else None


# 3. 65세 이상 전체 인구 열
elderly_cols = [
    c for c in total_cols
    if age_of(c) is not None and age_of(c) >= 65
]


# 4. 65세 이상 남성/여성 인구 열
male_cols = [
    c for c in df.columns
    if c.startswith("남_") and re.match(r"남_(\d+)세", c)
    and int(re.match(r"남_(\d+)세", c).group(1)) >= 65
]

female_cols = [
    c for c in df.columns
    if c.startswith("여_") and re.match(r"여_(\d+)세", c)
    and int(re.match(r"여_(\d+)세", c).group(1)) >= 65
]


# 5. 동 단위로 전체 인구·고령 인구·고령 남녀 인구 계산
df["전체인구"] = df[total_cols].sum(axis=1)
df["고령인구"] = df[elderly_cols].sum(axis=1)
df["고령남성"] = df[male_cols].sum(axis=1)
df["고령여성"] = df[female_cols].sum(axis=1)


# 6. 코드 앞 5자리 = 시군구 코드
df["시군구코드"] = df["코드"].str[:5]


# 7. 시군구별로 합계
grouped = df.groupby("시군구코드")[
    ["전체인구", "고령인구", "고령남성", "고령여성"]
].sum().reset_index()


# 8. 고령화율 계산
grouped["고령화율"] = (
    grouped["고령인구"] / grouped["전체인구"] * 100
).round(2)


# 9. 65세 이상 인구 중 남성·여성 비율 계산
grouped["남성비율"] = (
    grouped["고령남성"] / grouped["고령인구"] * 100
).round(2)

grouped["여성비율"] = (
    grouped["고령여성"] / grouped["고령인구"] * 100
).round(2)


# 10. 지도 경계 파일에서 코드 → 시군구·시도 이름 연결
names = pd.DataFrame([
    {
        "시군구코드": str(f["properties"]["코드"]),
        "시군구": f["properties"]["시군구"],
        "시도": f["properties"]["시도"],
    }
    for f in geojson["features"]
])


merged = grouped.merge(
    names,
    on="시군구코드",
    how="left"
)


# 11. 5단계 고령화율 구간
BINS = [0, 19, 23, 28, 38, 100]
LABELS = [
    "19% 미만",
    "19~23%",
    "23~28%",
    "28~38%",
    "38% 이상"
]


# 보라색 계열
COLORS = {
    "19% 미만": "#F1E6FF",
    "19~23%": "#D8B4FE",
    "23~28%": "#B57EDC",
    "28~38%": "#8B5FBF",
    "38% 이상": "#542788",
}


merged["단계"] = pd.cut(
    merged["고령화율"],
    bins=BINS,
    labels=LABELS,
    right=False
)


# 12. 지도 그리기
fig = px.choropleth(
    merged,
    geojson=geojson,
    locations="시군구코드",
    featureidkey="properties.코드",
    color="단계",
    category_orders={"단계": LABELS},
    color_discrete_map=COLORS,
    hover_name="시군구",
    hover_data={
        "고령화율": True,
        "시도": True,
        "시군구코드": False,
        "단계": False,
    },
    labels={
        "고령화율": "고령화율(%)",
        "시도": "시도",
    },
)


fig.update_geos(
    fitbounds="locations",
    visible=False
)


fig.update_layout(
    margin=dict(l=0, r=0, t=10, b=0),
    height=700,
    legend_title_text=f"65세 이상 비율 ({latest_year}년)",
)


st.plotly_chart(
    fig,
    use_container_width=True
)


# 13. 표에 표시할 열
display_cols = [
    "시도",
    "시군구",
    "고령화율",
    "남성비율",
    "여성비율",
]


# 14. 표용 컬럼 이름 변경
def make_table(data):
    table = data[display_cols].reset_index(drop=True).copy()

    table.columns = [
        "시도",
        "시군구",
        "고령화율 (%)",
        "65세 이상 남성 비율 (%)",
        "65세 이상 여성 비율 (%)",
    ]

    return table


# 15. 높은 곳 / 낮은 곳 표를 좌우로 배치
c1, c2 = st.columns(2)


with c1:
    st.subheader("🔴 고령화율 높은 곳 10")

    high = merged.nlargest(
        10,
        "고령화율"
    )

    st.dataframe(
        make_table(high),
        use_container_width=True,
        hide_index=True
    )


with c2:
    st.subheader("🟢 고령화율 낮은 곳 10")

    low = merged.nsmallest(
        10,
        "고령화율"
    )

    st.dataframe(
        make_table(low),
        use_container_width=True,
        hide_index=True
    )
