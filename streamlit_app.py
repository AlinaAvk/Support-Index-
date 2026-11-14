from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "analysis_work"


st.set_page_config(
    page_title="Sephora Nickname Gap",
    page_icon="💄",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem;}
        [data-testid="stMetric"] {
            background: #fff7fb;
            border: 1px solid #f3d9e7;
            border-radius: 14px;
            padding: 14px 16px;
        }
        .finding {
            background: linear-gradient(90deg, #fff2f8, #f3f0ff);
            border-left: 4px solid #d63384;
            border-radius: 10px;
            padding: 0.7rem 1rem;
            margin: 0.4rem 0 1rem 0;
            font-size: 0.94rem;
        }
        .small-note {color: #626262; font-size: 0.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    products = pd.read_csv(DATA_DIR / "searchability_gap_product_results.csv")
    keywords = pd.read_csv(DATA_DIR / "searchability_gap_keyword_results.csv")
    variants = pd.read_csv(DATA_DIR / "searchability_gap_variant_summary.csv")
    return products, keywords, variants


products, keywords, variants = load_data()
recovered = products[products["recovery_status"].eq("Estimate recovered")].copy()
nickname_recovery_rate = variants.loc[
    variants["variant_type"].eq("Nickname"), "search_recovery_rate"
].iloc[0]
measurable_alternate_searches = int(variants["searches_with_estimate"].sum())
nickname_searches_with_estimate = int(
    variants.loc[
        variants["variant_type"].eq("Nickname"), "searches_with_estimate"
    ].iloc[0]
)
nickname_share_of_measurable = (
    nickname_searches_with_estimate / measurable_alternate_searches
)
recovered_loves = int(recovered["loves_count"].sum())
recovered_brand_count = recovered["brand_name"].nunique()
top_search_midpoint = recovered["search_midpoint"].max()

st.title("💄 The Sephora Nickname Gap")
st.caption("How customer wording affects measured product search interest")

metric_1, metric_2, metric_3, metric_4 = st.columns(4)
metric_1.metric(
    "Nickname share",
    f"{nickname_share_of_measurable:.1%}",
    help="33 of the 34 alternate searches with an estimate were nicknames.",
)
metric_2.metric(
    "Total Product Likes",
    f"{recovered_loves / 1_000_000:.1f}M",
    help="Combined Sephora Loves for the products whose demand became measurable.",
)
metric_3.metric(
    "Brands Represented",
    f"{recovered_brand_count:,}",
    help="Distinct brands represented among the recovered products.",
)
metric_4.metric(
    "Product Searches",
    f"{top_search_midpoint / 1_000:.1f}K",
    help="Midpoint of TikTok's largest estimated monthly search range in this test.",
)

st.markdown(
    f"""
    <div class="finding">
      <strong>🔎 Main finding:</strong> Nicknames raise measurable discoverability up to
      <strong>{nickname_recovery_rate:.1%}</strong>.
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("🛍️ Explore the products")
    category_options = sorted(products["primary_category"].dropna().unique())
    selected_categories = st.multiselect("Category", category_options)

    brand_options = sorted(products["brand_name"].dropna().unique())
    selected_brands = st.multiselect("Brand", brand_options)

    status_options = ["Estimate recovered", "Still no estimate"]
    selected_statuses = st.multiselect("Result", status_options, default=status_options)
    product_search = st.text_input("Search product or keyword", placeholder="Try: blush, Tatcha, lip stain")
    st.caption("Filters affect the product explorer below.")

filtered = products.copy()
if selected_categories:
    filtered = filtered[filtered["primary_category"].isin(selected_categories)]
if selected_brands:
    filtered = filtered[filtered["brand_name"].isin(selected_brands)]
if selected_statuses:
    filtered = filtered[filtered["recovery_status"].isin(selected_statuses)]
if product_search:
    needle = product_search.casefold()
    searchable = (
        filtered["brand_name"].fillna("")
        + " "
        + filtered["product_name"].fillna("")
        + " "
        + filtered["best_keyword"].fillna("")
    ).str.casefold()
    filtered = filtered[searchable.str.contains(needle, regex=False)]

explore_tab, meaning_tab, method_tab = st.tabs(
    ["📊 Explore", "💡 Why it matters", "🧪 Method"]
)

with explore_tab:
    left, right = st.columns([1, 1.25])

    with left:
        st.subheader("Which product wording worked?")
        wording_results = pd.concat(
            [
                pd.DataFrame(
                    {
                        "variant_type": ["Official product name"],
                        "search_recovery_rate": [0.0],
                    }
                ),
                variants.loc[
                    ~variants["variant_type"].eq("Abbreviated"),
                    ["variant_type", "search_recovery_rate"],
                ],
            ],
            ignore_index=True,
        )
        variant_chart = wording_results.set_index("variant_type")[
            ["search_recovery_rate"]
        ].copy()
        variant_chart.columns = ["Recovery rate"]
        variant_chart = variant_chart.sort_values("Recovery rate", ascending=False)
        st.bar_chart(variant_chart, color="#d63384", horizontal=True)
        st.caption(
            "Nickname searches recovered 33 products while consumer language searches recovered "
            "only 1 and official product names recovered 0."
        )

    with right:
        st.subheader("Largest recovered search estimates")
        top_search = (
            recovered.nlargest(10, "search_midpoint")
            .assign(label=lambda frame: frame["brand_name"] + " — " + frame["best_keyword"])
            .set_index("label")[["search_midpoint"]]
            .sort_values("search_midpoint")
        )
        top_search.columns = ["Estimated monthly searches (midpoint)"]
        st.bar_chart(top_search, color="#7c3aed", horizontal=True)
        st.caption(
            "Values are based on the midpoint of TikTok's estimated monthly search range."
        )

    st.subheader(f"Product explorer · {len(filtered):,} products")
    display = filtered[
        [
            "brand_name",
            "product_name",
            "primary_category",
            "loves_count",
            "recovery_status",
            "best_keyword",
            "avg_monthly_searches_range",
            "three_month_change",
            "yoy_change",
        ]
    ].rename(
        columns={
            "brand_name": "Brand",
            "product_name": "Product",
            "primary_category": "Category",
            "loves_count": "Sephora Loves",
            "recovery_status": "Result",
            "best_keyword": "Winning nickname",
            "avg_monthly_searches_range": "TikTok monthly estimate",
            "three_month_change": "3-month change",
            "yoy_change": "YoY change",
        }
    )
    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Sephora Loves": st.column_config.NumberColumn(format="localized"),
            "3-month change": st.column_config.NumberColumn(format="percent"),
            "YoY change": st.column_config.NumberColumn(format="percent"),
        },
    )

with meaning_tab:
    st.subheader("What Does the Nickname Effect Mean?")
    st.write(
        "A product can be famous while its formal catalog name is almost invisible in keyword data. "
        "For example, **Rare Beauty Soft Pinch Liquid Blush** returned no estimate under the longer "
        "product wording, while **“rare beauty blush”** returned **10K–25K monthly searches**."
    )
    st.write(
        "This suggests that discoverability lives in a translation layer between the catalog and the "
        "customer. The company does not need to rename the product. It can map the nickname behind the "
        "official name."
    )

    st.markdown(
        """
        **Where this can be used:**

        - Add winning nicknames as synonyms in Sephora and brand-site search.
        - Use them as paid-search and TikTok campaign seed keywords.
        - Put them in creator briefs so videos match the language customers type.
        - Track them in social listening instead of monitoring only official product names.
        - Keep the formal catalog title for accuracy while storing consumer language as metadata.
        """
    )

    st.info(
        "The analysis shows that the wording changes measurable discoverability."
    )

with method_tab:
    st.subheader("How the test worked")
    st.markdown(
        """
        1. Start with **204 high-Loves Sephora products** that had no TikTok estimate in the earlier test.
        2. Create three searches per product: an abbreviation, a likely consumer nickname, and a
           consumer-language phrase ending in “review.”
        3. Upload **604 unique phrases** to TikTok Keyword Planner for the United States.
        4. Join TikTok's export back to all **612 product-to-phrase mappings**.
        5. Count a product as recovered when at least one alternate phrase receives an estimate.
        """
    )

    st.success("✅ No missing records: all 612 mappings joined exactly to TikTok's export.")
    st.caption(
        "Sephora Loves come from the March 2023 product snapshot. TikTok estimates were exported "
        "October 12, 2026. The two metrics measure attention in different systems and periods."
    )

st.divider()
st.caption("💄 Sephora × TikTok search-language prototype · built as a simple first version")

