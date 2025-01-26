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


user = st.secrets["user"]
passwd = st.secrets["password"]
g_id = st.secrets["g_id"]
timeout = int(st.secrets["timeout"])


RSS_FEEDS = {
    "Chart": None,
    "Calendario": None,
    "Mondo": ["https://it.investing.com/rss/news_285.rss", "https://www.ilsole24ore.com/rss/mondo.xml"],
    "Economia": ["https://it.investing.com/rss/news_14.rss", "https://www.ilsole24ore.com/rss/economia.xml"],
    "Finanza": ["https://it.investing.com/rss/news_25.rss", "https://www.ilsole24ore.com/rss/finanza.xml"],
    "Italia": ["https://www.ilsole24ore.com/rss/italia.xml", "https://www.corriere.it/dynamic-feed/rss/section/Milano.xml"],
    "Motori": ["https://xml2.corriereobjects.it/rss/motori.xml", "https://it.motorsport.com/rss/f1/news/", "https://www.moto.it/rss/news-motogp.xml"],
}


def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == user and password == passwd:
            st.session_state["authenticated"] = True
            st.session_state["last_activity"] = datetime.now()
            st.success("Login successful!")
        else:
            st.error("Invalid username or password")


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

    response = chat_session.send_message("riesci a darmi i prezzi chiave di questo grafico. almeno 10")
    return response.text
    

# Check login status
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    login()
else:
    check_inactivity()

    if not st.session_state["authenticated"]:
        st.stop()

    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False

    # Streamlit app layout
    st.title("NEWS")

    # feed_name = st.sidebar.selectbox("Select an RSS Feed", list(RSS_FEEDS.keys()))
    feed_name = st.sidebar.radio(
        "Select an RSS Feed",
        list(RSS_FEEDS.keys()),
        index=1,
    )

    if feed_name:
        if feed_name == "Calendario":
            st.write("### Economic Calendar")
            st.components.v1.html("""<iframe src="https://sslecal2.investing.com?columns&category=_employment,_economicActivity,_inflation,_credit,_centralBanks,_confidenceIndex,_balance,_Bonds&importance=2,3&features=timeselector&countries=5&calType=week&timeZone=16&lang=9" width="450" height="467" frameborder="0" allowtransparency="true" marginwidth="0" marginheight="0"></iframe><div class="poweredBy" style="font-family: Arial, Helvetica, sans-serif;"><span style="font-size: 11px;color: #333333;text-decoration: none;">Calendario economico fornito da <a href="https://it.investing.com/" rel="nofollow" target="_blank" style="font-size: 11px;color: #06529D; font-weight: bold;" class="underline_link">Investing.com Italia</a> - Il Portale di Trading sul Forex e sui titoli di borsa.</span></div>""", height=600)
        elif feed_name == "Chart":
            st.write("### Charts")
            tv = TvDatafeed()
            df = tv.get_hist(symbol='NQH2025',exchange='CME_MINI',interval=Interval.in_1_minute, n_bars=5000)
            df['datetime_ny'] = pd.to_datetime(df.index).tz_localize('Etc/GMT-1')  # UTC+1 timezone
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
            st.write(f"#### {process_image(fig.to_image(format="png"))}")
        else:
            feed_urls = RSS_FEEDS[feed_name]

            st.write(f"### Articles from {feed_name}")

            # Fetch and display articles
            articles = fetch_rss_articles(feed_urls)
            sorted_articles = sorted(articles, key=lambda x: x['pub_date'], reverse=True)

            for idx, article in enumerate(sorted_articles):
                try:
                    col1, col2 = st.columns([10, 1])
                    article_key = f"output_{article['title']}"  # Unique key for each article
                    with col1:
                        st.write(f"#### [{article['title']}]({article['link']})")
                        st.write(f"Published on: {article['pub_date']}")
                        # st.write(article['description'])
                        if article_key not in st.session_state:
                            st.session_state[article_key] = ""  # Initialize state
                        output_placeholder = st.empty()
                        output_placeholder.write(f"{st.session_state[article_key]}")

                    with col2:
                        if st.button(f"AI", key=article['link']):
                            if "ilsole24ore" in article['link'] or "corriere" in article['link']:
                                output = process_link(article['clean_link'])
                            else:
                                output = process_link(article['link'])
                            st.session_state[article_key] = output
                            output_placeholder.write(f"{output}")

                    st.write("---")
                except Exception as e:
                    pass
