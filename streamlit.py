import streamlit as st
import requests
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
import dateutil.parser
from datetime import datetime, timedelta
import pytz
import google.generativeai as genai
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import plotly.graph_objects as go
import io
import re
from extra_streamlit_components import CookieManager
from datetime import datetime, timedelta

cookie_manager = CookieManager()
COOKIE_NAME = "user_auth"
COOKIE_EXPIRY_DAYS = 30
user = st.secrets["user"]
passwd = st.secrets["password"]
g_id = st.secrets["g_id"]
timeout = int(st.secrets["timeout"])

RSS_FEEDS = {
    # "Chart": None,
    "Calendario": None,
    "Mondo": ["https://it.investing.com/rss/news_285.rss", "https://www.ilsole24ore.com/rss/mondo.xml"],
    "Economia": ["https://it.investing.com/rss/news_14.rss", "https://www.ilsole24ore.com/rss/economia.xml"],
    "Finanza": ["https://it.investing.com/rss/news_25.rss", "https://www.ilsole24ore.com/rss/finanza.xml"],
}
RSS_FEEDS["All"] = sum((v for v in RSS_FEEDS.values() if v is not None), [])
RSS_FEEDS["Italia"] = ["https://www.ilsole24ore.com/rss/italia.xml", "https://www.corriere.it/dynamic-feed/rss/section/Milano.xml"]
RSS_FEEDS["Motori"] = ["https://xml2.corriereobjects.it/rss/motori.xml", "https://it.motorsport.com/rss/f1/news/", "https://www.moto.it/rss/news-motogp.xml"]


def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == user and password == passwd:
            expiry_date = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)
            cookie_manager.set(COOKIE_NAME, "authenticated", expires_at=expiry_date)
            st.success("Login effettuato con successo!")
        else:
            st.error("Username o password non validi")


def check_cookie():
    # Controlla se il cookie esiste
    cookies = cookie_manager.get_all()
    if cookies.get(COOKIE_NAME) == "authenticated":
        st.success("Sei già autenticato!")
        return True
    return False


# Check for inactivity
def check_inactivity():
    if "last_activity" in st.session_state:
        now = datetime.now()
        if now - st.session_state["last_activity"] > timedelta(minutes=timeout):
            st.session_state["authenticated"] = False
            st.sidebar.warning("You have been logged out due to inactivity.")
    st.session_state["last_activity"] = datetime.now()


# Function to fetch articles from an RSS feed
def fetch_rss_articles(feed_urls):
    articles = []

    for feed_url in feed_urls:
        source = ""
        if "ilsole24ore" in feed_url:
            source = "Il Sole 24 Ore"
        elif "corriere" in feed_url:
            source = "Corriere della Sera"
        elif "investing" in feed_url:
            source = "Investing"
        elif "motorsport" in feed_url:
            source = "Motorsport"
        elif "moto" in feed_url:
            source = "Moto.it"

        response = requests.get(feed_url)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        for channel in root.findall("channel"):
            for item in channel.findall("item"):
                try:
                    title = item.find("title").text
                    link = item.find("link").text
                    try:
                        description = item.find("description").text
                    except:
                        description = ""
                    pub_date = item.find("pubDate").text
                    pub_date = dateutil.parser.parse(pub_date).astimezone(pytz.timezone('Europe/Rome'))

                    # Clean up description using BeautifulSoup
                    soup = BeautifulSoup(description, 'html.parser')
                    description_text = soup.get_text()

                    articles.append({
                        "title": title,
                        "link": link,
                        "clean_link": f"https://12ft.io/{link}",
                        "description": description_text,
                        "pub_date": pub_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "source": source
                    })
                except Exception as e:
                    pass
    return articles


# Function to process the link
def process_link(link):
    # Replace this with your actual processing logic
    genai.configure(api_key=g_id)
    # Create the model
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=generation_config,
    )

    chat_session = model.start_chat(
        history=[
        ]
    )
    response = chat_session.send_message(f"Riassumi in italiano {link}")
    return response.text


def process_image(image):
    def upload_to_gemini(image, mime_type="image/png"):
        file = genai.upload_file(io.BytesIO(image), mime_type=mime_type)
        return file
    
    genai.configure(api_key=g_id)
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=generation_config,
    )
    files = [
        upload_to_gemini(image, mime_type="image/png"),
    ]
    chat_session = model.start_chat(
    history=[
        {
        "role": "user",
        "parts": [
            files[0],
        ],
        },
    ]
    )

    response = chat_session.send_message("riesci a darmi i prezzi chiave di questo grafico in ordine decrescente.")
    return response.text


def main:
    # Streamlit app layout
    st.title("NEWS")

    # feed_name = st.sidebar.selectbox("Select an RSS Feed", list(RSS_FEEDS.keys()))
    feed_name = st.sidebar.radio(
        "Select an RSS Feed",
        list(RSS_FEEDS.keys()),
        index=4,
    )


    if feed_name:
        if feed_name == "Calendario":
            st.write("### Economic Calendar")
            st.components.v1.html("""<iframe src="https://sslecal2.investing.com?columns=exc_importance&importance=2,3&features=datepicker,timeselector&countries=5&calType=day&timeZone=8&lang=9" width="475" height="467" frameborder="0" allowtransparency="true" marginwidth="0" marginheight="0"></iframe><div class="poweredBy" style="font-family: Arial, Helvetica, sans-serif;"><span style="font-size: 11px;color: #333333;text-decoration: none;">Calendario economico fornito da <a href="https://it.investing.com/" rel="nofollow" target="_blank" style="font-size: 11px;color: #06529D; font-weight: bold;" class="underline_link">Investing.com Italia</a> - Il Portale di Trading sul Forex e sui titoli di borsa.</span></div>""", height=600)
        elif feed_name == "Chart":
            st.write("### Charts")
            tv = TvDatafeed()
            df = tv.get_hist(symbol='NQH2025',exchange='CME_MINI',interval=Interval.in_5_minute, n_bars=5000)
            df['datetime_ny'] = pd.to_datetime(df.index).tz_localize('Etc/GMT')
            df['datetime_ny'] = df['datetime_ny'].dt.tz_convert('America/New_York')
            
            selected_dates = st.date_input("Select dates", None)
            dates_to_filter = pd.to_datetime([selected_dates]).date

            df = df[
                (df.datetime_ny.dt.time >= pd.Timestamp('09:30:00').time()) & 
                (df.datetime_ny.dt.time < pd.Timestamp('16:00:00').time()) &
                (df.datetime_ny.dt.date.isin(dates_to_filter))
            ]
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df['datetime_ny'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name="Candlestick"
            ))
            # Update layout for better visuals
            fig.update_layout(
                title="Stock Prices Over Time",
                xaxis_title="Date",
                yaxis_title="Price",
                xaxis_rangeslider_visible=False,
                yaxis=dict(
                    tickformat='.0f',
                    showgrid=True,
                    gridcolor='lightgray',
                    gridwidth=0,
                    dtick=10 
                )
            )
            # Display in Streamlit
            st.plotly_chart(fig)
            # if len(df) > 0:
            #     st.write(f"#### {process_image(fig.to_image(format="png"))}")
        else:
            feed_urls = RSS_FEEDS[feed_name]

            st.write(f"### Articles from {feed_name}")

            articles = fetch_rss_articles(feed_urls)
            sorted_articles = sorted(articles, key=lambda x: x['pub_date'], reverse=True)

            for idx, article in enumerate(sorted_articles):
                try:
                    col1, col2 = st.columns([10, 1])
                    clean_title = re.sub(r'[^A-Za-z]', ' ', article['title'])
                    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                    clean_title = f"Raccontami articolo del periodico {article['source']} con titolo: {clean_title} e approfondisci con alte fonti."
                    with col1:
                        st.write(f"<span style='color:#1f77b4; font-size: 20px; font-weight: bold;'>{article['title']}</span>", unsafe_allow_html=True)
                        st.write(f"Published on: {article['pub_date']} - {article['source']}")
                    with col2:
                        copy_button_html = f"""
                        <button onclick="navigator.clipboard.writeText('{clean_title}')">Copy</button>
                        """
                        st.components.v1.html(copy_button_html, height=35)
                except Exception as e:
                    pass


    

# Check login status
if not check_cookie():
    login()
main()
