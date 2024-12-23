import streamlit as st
import requests
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
import dateutil.parser
import pytz

# Function to fetch articles from an RSS feed
def fetch_rss_articles(feed_url):
    response = requests.get(feed_url)
    response.raise_for_status()
    root = ET.fromstring(response.content)

    articles = []
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

# List of RSS feeds
RSS_FEEDS = {
    "Calendario economico": None,
    "Investing.com Più Rilevanti": "https://it.investing.com/rss/news_285.rss",
    "Investing.com Economia": "https://it.investing.com/rss/news_14.rss",
    "Investing.com Mercato azionario": "https://it.investing.com/rss/news_25.rss",
    "Il sole 24 ore Italia": "https://www.ilsole24ore.com/rss/italia.xml",
    "Il sole 24 ore Mondo": "https://www.ilsole24ore.com/rss/mondo.xml",
    "Il sole 24 ore Economia": "https://www.ilsole24ore.com/rss/economia.xml",
    "Il sole 24 ore Finanza": "https://www.ilsole24ore.com/rss/finanza.xml",
    "Corriere Esteri": "https://www.corriere.it/dynamic-feed/rss/section/Esteri.xml",
    "Corriere Economia": "https://www.corriere.it/dynamic-feed/rss/section/Economia.xml",
    "Corriere Scienza": "https://www.corriere.it/dynamic-feed/rss/section/Scienza.xml",
    "Corriere Motori": "https://xml2.corriereobjects.it/rss/motori.xml",
    "Corriere Milano": "https://www.corriere.it/dynamic-feed/rss/section/Milano.xml",
    "F1": "https://it.motorsport.com/rss/f1/news/",
    "MotoGP": "https://www.moto.it/rss/news-motogp.xml",
    "Focus Tecnologia": "https://www.focus.it/rss/tecnologia.rss",
    "Focus Comportamento": "https://www.focus.it/rss/comportamento.rss",
    "Focus Scienza": "https://www.focus.it/rss/scienza.rss",
}

# Streamlit app layout
st.title("RSS Feed Viewer")

# feed_name = st.sidebar.selectbox("Select an RSS Feed", list(RSS_FEEDS.keys()))
feed_name = st.sidebar.radio(
    "Select an RSS Feed",
    list(RSS_FEEDS.keys()),
    index=None,
)
if feed_name:
    if feed_name == "Calendario economico":
        st.write("### Economic Calendar")
        st.components.v1.html("""
            <iframe src="https://sslecal2.investing.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&category=_employment,_economicActivity,_inflation,_credit,_centralBanks,_confidenceIndex,_balance,_Bonds&importance=2,3&features=datepicker,timezone&countries=5&calType=day&timeZone=16&lang=9" width="650" height="467" frameborder="0" allowtransparency="true" marginwidth="0" marginheight="0"></iframe>
            <div class="poweredBy" style="font-family: Arial, Helvetica, sans-serif;">
                <span style="font-size: 11px;color: #333333;text-decoration: none;">
                    Calendario economico fornito da 
                    <a href="https://it.investing.com/" rel="nofollow" target="_blank" style="font-size: 11px;color: #06529D; font-weight: bold;" class="underline_link">Investing.com Italia</a> 
                    - Il Portale di Trading sul Forex e sui titoli di borsa.
                </span>
            </div>
        """, height=500)

    else:
        feed_url = RSS_FEEDS[feed_name]

        st.write(f"### Articles from {feed_name}")

        # Fetch and display articles
        articles = fetch_rss_articles(feed_url)
        sorted_articles = sorted(articles, key=lambda x: x['pub_date'], reverse=True)

        for article in sorted_articles:
            st.write(f"#### [{article['title']}]({article['link']})")
            st.write(f"Published on: {article['pub_date']}")
            st.write(article['description'])
            st.write(article['clean_link'])
            st.write("---")
