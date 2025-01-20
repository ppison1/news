import streamlit as st
import requests
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
import dateutil.parser
from datetime import datetime, timedelta
import pytz
import google.generativeai as genai


user = st.secrets["user"]
passwd = st.secrets["password"]
g_id = st.secrets["g_id"]
timeout = int(st.secrets["timeout"])

# List of RSS feeds
# RSS_FEEDS = {
#     "Calendario economico": None,
#     "Investing.com Più Rilevanti": "https://it.investing.com/rss/news_285.rss",
#     "Investing.com Economia": "https://it.investing.com/rss/news_14.rss",
#     "Investing.com Mercato azionario": "https://it.investing.com/rss/news_25.rss",
#     "Il sole 24 ore Italia": "https://www.ilsole24ore.com/rss/italia.xml",
#     "Il sole 24 ore Mondo": "https://www.ilsole24ore.com/rss/mondo.xml",
#     "Il sole 24 ore Economia": "https://www.ilsole24ore.com/rss/economia.xml",
#     "Il sole 24 ore Finanza": "https://www.ilsole24ore.com/rss/finanza.xml",
#     # "Corriere Esteri": "https://www.corriere.it/dynamic-feed/rss/section/Esteri.xml",
#     # "Corriere Economia": "https://www.corriere.it/dynamic-feed/rss/section/Economia.xml",
#     # "Corriere Scienza": "https://www.corriere.it/dynamic-feed/rss/section/Scienza.xml",
#     "Corriere Motori": "https://xml2.corriereobjects.it/rss/motori.xml",
#     "Corriere Milano": "https://www.corriere.it/dynamic-feed/rss/section/Milano.xml",
#     "F1": "https://it.motorsport.com/rss/f1/news/",
#     "MotoGP": "https://www.moto.it/rss/news-motogp.xml",
#     "Focus Tecnologia": "https://www.focus.it/rss/tecnologia.rss",
#     "Focus Comportamento": "https://www.focus.it/rss/comportamento.rss",
#     "Focus Scienza": "https://www.focus.it/rss/scienza.rss",
# }
RSS_FEEDS = {
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
        else:
            feed_urls = RSS_FEEDS[feed_name]

            st.write(f"### Articles from {feed_name}")

            # Fetch and display articles
            articles = fetch_rss_articles(feed_urls)
            sorted_articles = sorted(articles, key=lambda x: x['pub_date'], reverse=True)

            for idx, article in enumerate(sorted_articles):
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
