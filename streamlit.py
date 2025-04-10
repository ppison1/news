import streamlit as st
import requests
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
import dateutil.parser
from datetime import datetime, timedelta
# import pytz
# import google.generativeai as genai
from googletrans import Translator
import asyncio
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
# import io
import re
from extra_streamlit_components import CookieManager
from datetime import datetime, timedelta
from threading import Thread

cookie_manager = CookieManager()

COOKIE_NAME = "user_auth"
COOKIE_EXPIRY_DAYS = 1
user = st.secrets["user"]
passwd = st.secrets["password"]

RSS_FEEDS = {
    "Pnl": None,
    "Calendario": None,
    "Mondo": ["https://it.investing.com/rss/news_285.rss", "https://www.ilsole24ore.com/rss/mondo.xml"],
    "Economia": ["https://it.investing.com/rss/news_14.rss", "https://www.ilsole24ore.com/rss/economia.xml", "https://feeds.content.dowjones.io/public/rss/socialeconomyfeed", "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness"],
    "Finanza": ["https://it.investing.com/rss/news_25.rss", "https://www.ilsole24ore.com/rss/finanza.xml", "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain"],
}
# RSS_FEEDS["All"] = sum((v for v in RSS_FEEDS.values() if v is not None), [])
RSS_FEEDS["Italia"] = ["https://www.ilsole24ore.com/rss/italia.xml", "https://www.corriere.it/dynamic-feed/rss/section/Milano.xml"]
RSS_FEEDS["Motori"] = ["https://xml2.corriereobjects.it/rss/motori.xml", "https://it.motorsport.com/rss/f1/news/", "https://www.moto.it/rss/news-motogp.xml"]
RSS_FEEDS["Tecnologia"] = ["https://feeds.content.dowjones.io/public/rss/RSSWSJD"]
RSS_FEEDS["All"] = sum((v for v in RSS_FEEDS.values() if v is not None), [])


def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
         if username == user and password == passwd:
            expiry_date = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)
            cookie_manager.set(COOKIE_NAME, "authenticated", expires_at=expiry_date)
            st.success("Login successful!")
         else:
             st.error("Invalid username or password")


async def to_it(text, src='en', dest='it'):
    try:
        translator = Translator()
        traduzione = await translator.translate(text, src=src, dest=dest)
        return traduzione.text
    except Exception as ex:
        print(ex)
        return text


def fetch_rss_articles(feed_urls):
    def run(feed_url):
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
        elif "dowjones" in feed_url:
            source = "WSJ"

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
                    pub_date = dateutil.parser.parse(pub_date)#.astimezone(pytz.timezone('Europe/Rome'))

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
    
    articles = []
    threads = []
    for feed_url in feed_urls:
        threads.append(Thread(target=run, args=(feed_url,)))
        threads[-1].start()
    for thread in threads:
        thread.join()
    return articles


cookies = cookie_manager.get_all()
if not cookies.get(COOKIE_NAME) == "authenticated":
    login()
else:
    st.title("NEWS")
    feed_name = st.sidebar.radio(
        "Select an RSS Feed",
        list(RSS_FEEDS.keys()),
        index=8,
    )

    if feed_name:
        if feed_name == "Calendario":
            st.write("### Economic Calendar")
            st.components.v1.html("""<iframe src="https://sslecal2.investing.com?columns=exc_importance&importance=2,3&features=datepicker,timeselector&countries=5&calType=day&timeZone=8&lang=9" width="475" height="467" frameborder="0" allowtransparency="true" marginwidth="0" marginheight="0"></iframe><div class="poweredBy" style="font-family: Arial, Helvetica, sans-serif;"><span style="font-size: 11px;color: #333333;text-decoration: none;">Calendario economico fornito da <a href="https://it.investing.com/" rel="nofollow" target="_blank" style="font-size: 11px;color: #06529D; font-weight: bold;" class="underline_link">Investing.com Italia</a> - Il Portale di Trading sul Forex e sui titoli di borsa.</span></div>""", height=600)
        elif feed_name == "Pnl":
            st.write("### Analisi del PNL")
            uploaded_file = st.file_uploader("Carica il tuo file CSV", type=["csv"])
            if uploaded_file is not None:
                df_merged = pd.read_csv(uploaded_file, index_col=0)
                st.subheader("Tabella degli ultimi 10 record")
                st.dataframe(df_merged[::-1])
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.1,
                    subplot_titles=("Total USD Cumulative", "Bar Chart: Total Realized PNL")
                )
                fig.add_trace(
                    go.Scatter(
                        x=df_merged['Trade Date'],
                        y=df_merged['Total USD Cumulative'],
                        mode='lines',
                        name='Cumulative PNL'
                    ),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Bar(
                        x=df_merged['Trade Date'],
                        y=df_merged['Total Realized PNL'],
                        name='Daily PNL',
                        marker_color=df_merged['Total Realized PNL'].apply(lambda x: 'green' if x > 0 else 'red')
                    ),
                    row=2, col=1
                )
                fig.update_xaxes(type='category', categoryorder='array', categoryarray=df_merged['Trade Date'], showticklabels=False)
                fig.update_layout(
                    title_text="Total USD Cumulative & Daily PNL",
                    height=800,
                )
                st.subheader("Grafico: Total USD Cumulative & Daily PNL")
                st.plotly_chart(fig)
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
                    if article['source'] == "WSJ":
                        title = asyncio.run(to_it(article['title']))
                    else:
                        title = article['title']
                    clean_title = re.sub(r'[^A-Za-z0-9]', ' ', article['title'])
                    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
                    clean_title = f"Raccontami in italiano articolo del periodico {article['source']} con titolo: {clean_title} e approfondisci con alte fonti."
                    title = f"{title}"
                    with col1:
                        st.write(f"<span style='color:#1f77b4; font-size: 20px; font-weight: bold;'>{title}</span>", unsafe_allow_html=True)
                        st.write(f"Published on: {article['pub_date']} - {article['source']}")
                    with col2:
                        copy_button_html = f"""
                        <button onclick="navigator.clipboard.writeText('{clean_title}')">Copy</button>
                        """
                        st.components.v1.html(copy_button_html, height=35)
                except Exception as e:
                    pass
