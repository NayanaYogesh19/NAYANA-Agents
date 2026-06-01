import os
import json
import pandas as pd
import streamlit as st

from scrapers.meta_scraper import AdsLibraryBrowser
from scrapers.google_scraper import GoogleAdsScraper
from scrapers.linkedin_scraper import LinkedInAdsScraper


# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(

    page_title="Competitor Ads Intelligence",

    layout="wide",

    page_icon="📢"
)

# ---------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------

st.markdown(
    """
    <style>

    /* Main App */
    .stApp {
        background-color: #F8FAFC !important;
        color: #111827 !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
    }

    /* Headings */
    h1, h2, h3, h4 {
        color: #111827 !important;
    }

    /* Labels */
    label,
    p,
    span,
    div {
        color: #111827 !important;
    }

    /* Sidebar Labels */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {
        color: #111827 !important;
    }

    /* Text Input */
    .stTextInput input {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
    }

    /* Select Box */
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        border-radius: 10px !important;
    }

    /* File Uploader */
    [data-testid="stFileUploader"] {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        border-radius: 10px !important;
    }

    /* Slider */
    .stSlider {
        color: #111827 !important;
    }

    /* Buttons */
    .stButton button {

        width: 100%;

        background-color: #2563EB !important;

        color: white !important;

        border-radius: 10px;

        height: 50px;

        font-size: 18px;

        font-weight: bold;

        border: none;
    }

    .stButton button:hover {

        background-color: #1D4ED8 !important;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------
# TITLE
# ---------------------------------------------------

st.markdown(

    """
    <h1 style='text-align:center;'>

    📢 Competitor Ads Intelligence Agent

    </h1>
    """,

    unsafe_allow_html=True
)

st.markdown("---")

# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------

st.sidebar.title("⚙️ Controls")

# ---------------------------------------------------
# PLATFORM SELECT
# ---------------------------------------------------

platform = st.sidebar.selectbox(

    "Select Ads Platform",

    [

        "Meta Ads",

        "Google Ads",

        "LinkedIn Ads"
    ]
)

# ---------------------------------------------------
# INPUTS
# ---------------------------------------------------

uploaded_files = None
url = None

# ---------------------------------------------------
# LINKEDIN INPUT
# ---------------------------------------------------

if platform == "LinkedIn Ads":

    uploaded_files = st.sidebar.file_uploader(

        "Upload LinkedIn Ad Screenshots",

        type=["png", "jpg", "jpeg"],

        accept_multiple_files=True,

        key="linkedin_multi_upload"
    )

    if uploaded_files:

        st.sidebar.success(
            f"{len(uploaded_files)} images selected"
        )

        for file in uploaded_files:

            st.sidebar.write(
                f"📂 {file.name}"
            )

# ---------------------------------------------------
# META + GOOGLE INPUT
# ---------------------------------------------------

else:

    url = st.sidebar.text_input(

        "Ads Library URL"
    )

# ---------------------------------------------------
# MAX ADS
# ---------------------------------------------------

max_ads = st.sidebar.slider(

    "Max Ads",

    1,

    50,

    10
)

# ---------------------------------------------------
# ANALYZE BUTTON
# ---------------------------------------------------

analyze_button = st.sidebar.button(
    "🚀 Analyze Ads"
)

# ---------------------------------------------------
# MAIN SCRAPE FLOW
# ---------------------------------------------------

if analyze_button:

    scraper = None

    try:

        # ---------------------------------------------------
        # SELECT SCRAPER
        # ---------------------------------------------------

        if platform == "Meta Ads":

            scraper = AdsLibraryBrowser()

        elif platform == "Google Ads":

            scraper = GoogleAdsScraper()

        elif platform == "LinkedIn Ads":

            scraper = LinkedInAdsScraper()

        # ---------------------------------------------------
        # SCRAPE
        # ---------------------------------------------------

        with st.spinner("Scraping ads..."):

            # ---------------------------------------------------
            # LINKEDIN FLOW
            # ---------------------------------------------------

            if platform == "LinkedIn Ads":

                if not uploaded_files:

                    st.warning(
                        "Please upload screenshots."
                    )

                    st.stop()

                os.makedirs(

                    "uploads",

                    exist_ok=True
                )

                image_paths = []

                for uploaded_file in uploaded_files:

                    file_path = os.path.join(

                        "uploads",

                        uploaded_file.name
                    )

                    with open(file_path, "wb") as f:

                        f.write(
                            uploaded_file.getbuffer()
                        )

                    image_paths.append(
                        file_path
                    )

                scraper.open(
                    image_paths
                )

            # ---------------------------------------------------
            # META + GOOGLE FLOW
            # ---------------------------------------------------

            else:

                if not url:

                    st.warning(
                        "Please enter URL."
                    )

                    st.stop()

                scraper.open(url)

            # ---------------------------------------------------
            # COLLECT ADS
            # ---------------------------------------------------

            ads = scraper.collect_ads(

                max_ads=max_ads
            )

            scraper.close()

        # ---------------------------------------------------
        # SUCCESS
        # ---------------------------------------------------

        st.success(
            f"Collected {len(ads)} ads"
        )

        # ---------------------------------------------------
        # METRICS
        # ---------------------------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(

                "Platform",

                platform
            )

        with col2:

            st.metric(

                "Total Ads",

                len(ads)
            )

        with col3:

            st.metric(

                "Active Ads",

                len(ads)
            )

        st.markdown("---")

        # ---------------------------------------------------
        # DISPLAY ADS
        # ---------------------------------------------------

        if len(ads) > 0:

            st.subheader("📢 Collected Ads")

            for ad in ads:

                advertiser = ad.get(

                    "advertiser_name",

                    "Unknown Advertiser"
                )

                status = ad.get(

                    "ad_status",

                    "Active"
                )

                media_type = ad.get(

                    "media_type",

                    "image"
                )

                primary_text = ad.get(

                    "primary_text",

                    "No Text Found"
                )

                snapshot = ad.get(
                    "ad_snapshot_url"
                )

                image_url = ad.get(
                    "creative_image_url"
                )

                video_url = ad.get(
                    "creative_video_url"
                )

                # ---------------------------------------------------
                # CARD
                # ---------------------------------------------------

                with st.container():

                    st.markdown("---")

                    st.markdown(
                        f"## 📢 {advertiser}"
                    )

                    col_a, col_b = st.columns(2)

                    with col_a:

                        st.success(
                            f"Status: {status}"
                        )

                    with col_b:

                        st.info(
                            f"Media Type: {media_type}"
                        )

                    st.write(
                        primary_text
                    )

                    # ---------------------------------------------------
                    # IMAGE
                    # ---------------------------------------------------

                    if image_url:

                        st.image(

                            image_url,

                            width=450
                        )

                    # ---------------------------------------------------
                    # VIDEO
                    # ---------------------------------------------------

                    if video_url:

                        st.video(
                            video_url
                        )

                    # ---------------------------------------------------
                    # SOURCE
                    # ---------------------------------------------------

                    if snapshot:

                        st.caption(
                            f"📂 Source: {snapshot}"
                        )

        # ---------------------------------------------------
        # TABLE
        # ---------------------------------------------------

        st.markdown("---")

        st.subheader("📊 Ads Table")

        df = pd.DataFrame(ads)

        st.dataframe(

            df,

            use_container_width=True
        )

        # ---------------------------------------------------
        # DOWNLOAD JSON
        # ---------------------------------------------------

        json_data = json.dumps(

            ads,

            indent=2
        )

        st.download_button(

            label="⬇ Download JSON",

            data=json_data,

            file_name=f"{platform.lower().replace(' ', '_')}.json",

            mime="application/json"
        )

        # ---------------------------------------------------
        # DOWNLOAD CSV
        # ---------------------------------------------------

        csv_data = df.to_csv(

            index=False,

            encoding="utf-8-sig"
        )

        st.download_button(

            label="⬇ Download CSV",

            data=csv_data,

            file_name=f"{platform.lower().replace(' ', '_')}.csv",

            mime="text/csv"
        )

    except Exception as e:

        st.error(str(e))