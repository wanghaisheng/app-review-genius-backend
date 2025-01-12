import os
import time
import hashlib
import logging
import httpx
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
import pandas as pd
import sqlite3

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

D1_DATABASE_ID = os.getenv('CLOUDFLARE_D1_DATABASE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')
RESULT_FOLDER = os.getenv('RESULT_FOLDER')

# Constants
CLOUDFLARE_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}"

# Escape special characters for safe SQL insertion
def escape_sql(value):
    """
    Safely escape a value by using SQLite's quote method, which handles special characters (e.g., single quotes).
    """
    if isinstance(value, str):
        # Use SQLite's quote method to escape the string
        connection = sqlite3.connect(':memory:')  # In-memory SQLite database for escaping
        quoted_value = connection.execute("SELECT quote(?)", (value,)).fetchone()[0]
        connection.close()
        return quoted_value
    return value

# Compute a hash for a row to avoid duplicates
def compute_hash(appid, username, date):
    """Compute a unique hash for each row."""
    hash_input = f"{appid}-{username}-{date}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

# Retry mechanism for API requests
def send_request_with_retries(url, headers, payload, retries=3, delay=2):
    for attempt in range(retries):
        client = httpx.Client()

        try:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()  # Raise exception for bad response codes
            return response
        except httpx.HTTPError as e:
            logging.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                logging.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise
        finally:
           client.close()



def fetch_reviews_from_d1(start_date=None, end_date=None):
    """Fetches reviews from D1 based on the given time frame."""

    sql_query = "SELECT * FROM ios_review_data"

    if start_date and end_date:
        sql_query += f" WHERE date >= '{start_date}' AND date <= '{end_date}'"
    elif start_date:
        sql_query += f" WHERE date >= '{start_date}'"

    payload = {"sql": sql_query}
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = send_request_with_retries(url, headers, payload)
        result = response.json()
        if result and result.get('result', []):
            return result.get('result')
        else:
            logging.warning("No reviews found for the given time range.")
            return []
    except httpx.HTTPError as e:
        logging.error(f"Failed to fetch reviews from D1: {e}")
        return []

def fetch_data_from_d1(start_date=None, end_date=None):
    """Fetches data from D1 based on the given time frame."""

    sql_query = "SELECT * FROM ios_top100_rank_data"

    if start_date and end_date:
        sql_query += f" WHERE updateAt >= '{start_date}' AND updateAt <= '{end_date}'"
    elif start_date:
        sql_query += f" WHERE updateAt >= '{start_date}'"

    payload = {"sql": sql_query}
    url = f"{CLOUDFLARE_BASE_URL}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = send_request_with_retries(url, headers, payload)
        result = response.json()
        if result and result['result']:
             first_result = result['result'][0]
             if 'results' in first_result and first_result['results']:
                data=first_result['results']
                return data
        else:
            logging.warning("No data found for the given time range.")
            return []
    except httpx.HTTPError as e:
        logging.error(f"Failed to fetch data from D1: {e}")
        return []

def get_start_and_end_date(timeframe, custom_date=None):
    """Returns the start and end date for the given timeframe."""
    end_date = datetime.utcnow().isoformat()
    if timeframe == "last week":
        start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        return start_date, end_date
    elif timeframe == "last month":
        start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        return start_date, end_date
    elif timeframe == "custom":
        if custom_date:
            try:
                date_format = "%Y-%m-%d"
                start_date = datetime.strptime(custom_date, date_format).isoformat()
                return start_date, end_date
            except ValueError:
                logging.error("Invalid custom date format. Please use YYYY-MM-DD.")
                return None, None
        else:
            logging.error("Custom date must be set")
            return None, None
    return None, None

def analyze_app_performance(data):
    """Analyzes app performance and trends."""
    if not data:
      logging.warning("No data available to analyze app performance.")
      return {}

    df = pd.DataFrame(data)
    df['updateAt'] = pd.to_datetime(df['updateAt'])
    df['rank'] = pd.to_numeric(df['rank'], errors='coerce')

    analysis = {}
    # --- Start App Performance Analysis ---
    #1. Daily Rank Movement
    df_daily_movement = df.copy()
    df_daily_movement['rank_change'] = df.groupby('appid')['rank'].diff().fillna(0)
    analysis['daily_rank_movement'] = df_daily_movement.groupby('appid').agg(
        average_daily_change = pd.NamedAgg(column="rank_change", aggfunc="mean"),
        std_dev_daily_change = pd.NamedAgg(column="rank_change", aggfunc="std"),
        num_large_daily_change= pd.NamedAgg(column='rank_change', aggfunc=lambda x: (abs(x) > 10).sum())
    ).to_dict('index')

    #2. Top Movers
    df_top_mover = df.copy()
    df_top_mover['rank_change'] = df.groupby('appid')['rank'].diff().fillna(0)
    top_gainers = df_top_mover[df_top_mover['rank_change'] < 0].groupby('appid').agg(
        total_rank_drop=('rank_change', 'sum'),
        total_days=('appid', 'count'),
        average_rank_change_rate = ('rank_change', 'mean')
    ).sort_values(by='total_rank_drop').to_dict('index')

    top_losers = df_top_mover[df_top_mover['rank_change'] > 0].groupby('appid').agg(
        total_rank_gain =('rank_change', 'sum'),
        total_days =('appid','count'),
        average_rank_change_rate = ('rank_change', 'mean')
    ).sort_values(by='total_rank_gain', ascending=False).to_dict('index')
    analysis['top_movers'] = {
        'top_gainers': top_gainers,
        'top_losers':top_losers
    }
    
    #3. Stability of Ranking
    df_stability = df.copy()
    df_stability = df_stability.set_index('updateAt').groupby('appid')['rank'].resample('1D').first().reset_index()
    analysis['rank_stability'] = df_stability.groupby('appid').agg(
        longest_streak_top_10 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: (x <= 10).astype(int).groupby((x <=10).astype(int).diff().ne(0).cumsum()).sum().max()),
        longest_streak_top_50 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: (x <= 50).astype(int).groupby((x <=50).astype(int).diff().ne(0).cumsum()).sum().max()),
        longest_streak_top_100 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: (x <= 100).astype(int).groupby((x <=100).astype(int).diff().ne(0).cumsum()).sum().max()),
        average_time_in_top_10 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: len(x[x <=10])),
         average_time_in_top_50 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: len(x[x <=50])),
         average_time_in_top_100 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: len(x[x <=100]))
        ).to_dict('index')

    #4. Ranking Trend Analysis
    df_rank_trend = df.copy()
    df_rank_trend['rank_change'] = df_rank_trend.groupby('appid')['rank'].diff().fillna(0)
    analysis['ranking_trend_analysis'] = df_rank_trend.groupby('appid').agg(
        average_daily_rank = pd.NamedAgg(column = 'rank', aggfunc = 'mean'),
        rank_fluctuation = pd.NamedAgg(column = 'rank', aggfunc = 'std'),
         total_rank_change = pd.NamedAgg(column = 'rank_change', aggfunc = 'sum'),
         average_rank_change_rate = pd.NamedAgg(column = 'rank_change', aggfunc = 'mean')
        ).to_dict('index')

    #5. Daily Rank Change Volatility
    df_daily_volatility = df.copy()
    df_daily_volatility['rank_change'] = df.groupby('appid')['rank'].diff().fillna(0)
    analysis['daily_rank_volatility'] = df_daily_volatility.groupby('appid').agg(
        range_rank_change = pd.NamedAgg(column = 'rank_change', aggfunc = lambda x: x.max() - x.min()),
       average_rank_change_rate = pd.NamedAgg(column='rank_change', aggfunc='mean')
        ).to_dict('index')

    #6. Average Daily Rank
    df_daily_rank = df.copy()
    analysis['average_daily_rank'] = df_daily_rank.groupby('appid').agg(average_rank = pd.NamedAgg(column = 'rank', aggfunc = 'mean')).to_dict('index')

    #7. Rank Change Rate
    df_rank_change_rate = df.copy()
    df_rank_change_rate['rank_change'] = df_rank_change_rate.groupby('appid')['rank'].diff().fillna(0)
    analysis['rank_change_rate'] = df_rank_change_rate.groupby('appid').agg(
        rank_change_rate = pd.NamedAgg(column = 'rank_change', aggfunc = 'mean')
        ).to_dict('index')

     #8. Daily Rank Change Frequency
    df_rank_change_freq = df.copy()
    df_rank_change_freq['rank_change'] = df_rank_change_freq.groupby('appid')['rank'].diff().fillna(0)
    analysis['daily_rank_change_frequency'] = df_rank_change_freq.groupby('appid').agg(
        daily_rank_change_frequency =  pd.NamedAgg(column ='rank_change', aggfunc = lambda x: (x != 0).sum())
        ).to_dict('index')

    return analysis

def analyze_market_trends(data):
  """Analyzes market trends and category performance."""
  if not data:
     logging.warning("No data available to analyze market trends.")
     return {}

  df = pd.DataFrame(data)
  df['updateAt'] = pd.to_datetime(df['updateAt'])
  df['rank'] = pd.to_numeric(df['rank'], errors='coerce')
  analysis = {}
    # --- Start Market Trends Analysis ---
  #9 Category Trend
  df_category_trend = df.copy()
  category_trends = df_category_trend.groupby(['type']).agg(
       average_rank = pd.NamedAgg(column = 'rank', aggfunc = 'mean'),
       top_app_count = pd.NamedAgg(column = 'appid', aggfunc = 'nunique')
        ).to_dict('index')
  analysis['category_trends'] = category_trends

  #10 Emerging Category
  df_emerging = df.copy()
  df_emerging['first_day_in_top100'] = df_emerging.groupby('appid')['updateAt'].transform('min')
  emerging_categories = df_emerging.groupby('type').agg(
      new_entrants_count=pd.NamedAgg(column = 'appid', aggfunc = 'nunique'),
       average_rank = pd.NamedAgg(column = 'rank', aggfunc = 'mean'),
      average_time_to_top100 = pd.NamedAgg(column = 'first_day_in_top100', aggfunc = lambda x : (x.max() - x.min()) if x.size > 1 else 0)
  ).to_dict('index')
  analysis['emerging_categories'] = emerging_categories

    #11 Declining Category
  df_declining = df.copy()
  df_declining['last_day_in_top100'] = df_declining.groupby('appid')['updateAt'].transform('max')
  declining_categories = df_declining.groupby('type').agg(
    last_entrants_count=pd.NamedAgg(column = 'appid', aggfunc = 'nunique'),
    average_rank = pd.NamedAgg(column = 'rank', aggfunc = 'mean'),
    average_time_in_top100 = pd.NamedAgg(column = 'last_day_in_top100', aggfunc = lambda x : (x.max() - x.min()) if x.size > 1 else 0)
  ).to_dict('index')
  analysis['declining_categories'] = declining_categories

  #12 Seasonal Effects
    # Placeholder, Requires External Data, skipped
  analysis['seasonal_effects'] = "Placeholder, Requires External Data"

    #13 Sub Category performance
  df_sub_category = df.copy()
  sub_category_performance = df_sub_category.groupby('cname').agg(
      average_rank = pd.NamedAgg(column = 'rank', aggfunc = 'mean'),
      top_apps_count = pd.NamedAgg(column = 'appid', aggfunc = 'nunique')
    ).to_dict('index')
  analysis['sub_category_performance'] = sub_category_performance

  #14 Emerging App Category
  df_emerging_app_type = df.copy()
  df_emerging_app_type['first_day_in_top100'] = df_emerging_app_type.groupby('appid')['updateAt'].transform('min')
  emerging_app_type = df_emerging_app_type.groupby('type').agg(
    new_entrants_count=pd.NamedAgg(column = 'appid', aggfunc = 'nunique'),
    average_time_to_top100 = pd.NamedAgg(column = 'first_day_in_top100', aggfunc = lambda x: (x.max() - x.min()) if x.size > 1 else 0)
     ).to_dict('index')
  analysis['emerging_app_type'] = emerging_app_type
  
    #15 New App Count
  df_new_app_count = df.copy()
  df_new_app_count['first_day_in_top100'] = df_new_app_count.groupby('appid')['updateAt'].transform('min')
  new_app_count = df_new_app_count.groupby('type').agg(
        new_entrants_count=pd.NamedAgg(column='appid', aggfunc='nunique'),
        distribution_rank=pd.NamedAgg(column='rank', aggfunc=lambda x: list(x)),
       average_time_in_top100 = pd.NamedAgg(column = 'first_day_in_top100', aggfunc = lambda x: (x.max() - x.min()) if x.size > 1 else 0)
  ).to_dict('index')
  analysis['new_app_count'] = new_app_count

  #16 Top Ranking App Count
  df_top_ranking_app_count = df.copy()
  df_top_ranking_app_count['is_top10'] = (df_top_ranking_app_count['rank'] <= 10)
  df_top_ranking_app_count['is_top20'] = (df_top_ranking_app_count['rank'] <= 20)
  df_top_ranking_app_count['is_top50'] = (df_top_ranking_app_count['rank'] <= 50)
  df_top_ranking_app_count['is_top100'] = (df_top_ranking_app_count['rank'] <= 100)
  top_ranking_app_count = df_top_ranking_app_count.groupby('type').agg(
    top_10_count = pd.NamedAgg(column = 'is_top10', aggfunc = 'sum'),
    top_20_count = pd.NamedAgg(column = 'is_top20', aggfunc = 'sum'),
    top_50_count = pd.NamedAgg(column = 'is_top50', aggfunc = 'sum'),
    top_100_count = pd.NamedAgg(column = 'is_top100', aggfunc = 'sum'),
    distribution_top_10= pd.NamedAgg(column = 'rank', aggfunc = lambda x: list(x[x<=10])),
      distribution_top_20= pd.NamedAgg(column = 'rank', aggfunc = lambda x: list(x[x<=20])),
      distribution_top_50= pd.NamedAgg(column = 'rank', aggfunc = lambda x: list(x[x<=50])),
      distribution_top_100= pd.NamedAgg(column = 'rank', aggfunc = lambda x: list(x[x<=100])),
     ).to_dict('index')

  analysis['top_ranking_app_count'] = top_ranking_app_count
  return analysis

def analyze_competitive(data):
   """Analyzes the competitive landscape."""
   if not data:
        logging.warning("No data available to analyze competitive landscape.")
        return {}

   df = pd.DataFrame(data)
   df['updateAt'] = pd.to_datetime(df['updateAt'])
   df['rank'] = pd.to_numeric(df['rank'], errors='coerce')
   analysis = {}

   #--- Start Competitive Analysis ---
    #17 Top Performers
   df_top_performer = df.copy()
   top_performers = df_top_performer.groupby('appid').agg(
    average_rank = pd.NamedAgg(column = 'rank', aggfunc = 'mean'),
    min_rank = pd.NamedAgg(column = 'rank', aggfunc = 'min'),
     max_rank = pd.NamedAgg(column = 'rank', aggfunc = 'max'),
        average_time_in_top_10 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: len(x[x <=10])),
         average_time_in_top_50 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: len(x[x <=50])),
         average_time_in_top_100 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: len(x[x <=100]))
    ).to_dict('index')
   analysis['top_performers'] = top_performers

   #18 Rank Improvement
   df_rank_improve = df.copy()
   df_rank_improve['rank_change'] = df_rank_improve.groupby('appid')['rank'].diff().fillna(0)
   rank_improvement = df_rank_improve.groupby('appid').agg(
       total_rank_drop=('rank_change', 'sum'),
       average_rank_change_rate=('rank_change','mean')
   ).sort_values(by='total_rank_drop').to_dict('index')
   analysis['rank_improvement'] = rank_improvement

   #19 Rank Decline
   df_rank_decline = df.copy()
   df_rank_decline['rank_change'] = df_rank_decline.groupby('appid')['rank'].diff().fillna(0)
   rank_decline = df_rank_decline.groupby('appid').agg(
       total_rank_gain=('rank_change', 'sum'),
        average_rank_change_rate=('rank_change','mean')
   ).sort_values(by='total_rank_gain',ascending=False).to_dict('index')
   analysis['rank_decline'] = rank_decline

   #20 App Gain Rate
   df_gain_rate = df.copy()
   df_gain_rate['rank_change'] = df_gain_rate.groupby('appid')['rank'].diff().fillna(0)
   app_gain_rate = df_gain_rate[df_gain_rate['rank_change'] < 0].groupby('appid').agg(
        average_rank_change_rate = ('rank_change', 'mean'),
        max_gain_rank_change = ('rank_change', 'min')
      ).sort_values(by='average_rank_change_rate').to_dict('index')
   analysis['app_gain_rate'] = app_gain_rate
    
   #21 App Loss Rate
   df_loss_rate = df.copy()
   df_loss_rate['rank_change'] = df_loss_rate.groupby('appid')['rank'].diff().fillna(0)
   app_loss_rate = df_loss_rate[df_loss_rate['rank_change'] > 0].groupby('appid').agg(
        average_rank_change_rate = ('rank_change', 'mean'),
        max_loss_rank_change = ('rank_change', 'max')
        ).sort_values(by='average_rank_change_rate', ascending = False).to_dict('index')
   analysis['app_loss_rate'] = app_loss_rate

   #22 Top Rank Time
   df_top_rank_time = df.copy()
   df_top_rank_time['rank_group'] = pd.cut(df_top_rank_time['rank'], bins=[0, 10, 20, 50, 100], labels=['top_10', 'top_20', 'top_50', 'top_100'])
   top_rank_time = df_top_rank_time.groupby('appid').agg(
        longest_streak_top_10 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: (x <= 10).astype(int).groupby((x <=10).astype(int).diff().ne(0).cumsum()).sum().max()),
       longest_streak_top_20 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: (x <= 20).astype(int).groupby((x <=20).astype(int).diff().ne(0).cumsum()).sum().max()),
        longest_streak_top_50 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: (x <= 50).astype(int).groupby((x <=50).astype(int).diff().ne(0).cumsum()).sum().max()),
        longest_streak_top_100 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: (x <= 100).astype(int).groupby((x <=100).astype(int).diff().ne(0).cumsum()).sum().max()),
       average_time_in_top_10 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: len(x[x <=10])),
        average_time_in_top_20 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: len(x[x <=20])),
        average_time_in_top_50 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: len(x[x <=50])),
        average_time_in_top_100 = pd.NamedAgg(column = 'rank', aggfunc = lambda x: len(x[x <=100])),
       ).to_dict('index')
   analysis['top_rank_time'] = top_rank_time
   return analysis

def analyze_app_attributes(data):
    """Analyzes app attributes and their correlations with rankings."""
    if not data:
        logging.warning("No data available to analyze app attributes.")
        return {}
    df = pd.DataFrame(data)
    df['rank'] = pd.to_numeric(df['rank'], errors='coerce')
    analysis = {}

    #23. Keyword and Themes
      # Place holder, requires more string processing and NLP, skipped
    analysis['keywords_themes'] = "Placeholder, requires text analysis"

    #24. App Icon Design
      # Place holder, requires visual processing, skipped
    analysis['app_icon_design'] = "Placeholder, requires visual processing"

    #25. App Name/Title
       # Place holder, requires more string processing and NLP, skipped
    analysis['app_name_title'] = "Placeholder, requires text analysis"

    #26. Publisher Performance
    publisher_perf = df.groupby('cname').agg(
          average_rank = pd.NamedAgg(column = 'rank', aggfunc = 'mean'),
           top_100_app_count = pd.NamedAgg(column = 'appid', aggfunc = 'nunique')
        ).to_dict('index')
    analysis['publisher_performance'] = publisher_perf
    return analysis

def analyze_strategic_insights(data):
    """Analyzes strategic and business insights."""
    if not data:
        logging.warning("No data available to analyze strategic insights.")
        return {}
    df = pd.DataFrame(data)
    df['updateAt'] = pd.to_datetime(df['updateAt'])
    df['rank'] = pd.to_numeric(df['rank'], errors='coerce')
    analysis = {}
    # 27 Day of Week Performance
    df_day_of_week = df.copy()
    df_day_of_week['day_of_week'] = df_day_of_week['updateAt'].dt.day_name()
    day_of_week_perf = df_day_of_week.groupby('day_of_week').agg(
          average_rank = pd.NamedAgg(column = 'rank', aggfunc = 'mean'),
           rank_change = pd.NamedAgg(column = 'rank', aggfunc = lambda x : x.max() - x.min())
        ).to_dict('index')
    analysis['day_of_week_performance'] = day_of_week_perf
    
    # 28. Regional Preferences
        # Place holder, requires processing per country, skipped
    analysis['regional_preferences'] = "Placeholder, requires per country processing"
    
    # 29. Regional Variation
       # Place holder, requires per country processing and correlation with apps, skipped
    analysis['regional_variation'] = "Placeholder, requires per country processing"

    # 30 Update Frequency
        # Placeholder, would require external data, skipped
    analysis['update_frequency'] = "Placeholder, requires update history"

    # 31. Category Saturation
    df_category_saturation = df.copy()
    category_saturation = df_category_saturation.groupby('type').agg(
        top_100_app_count = pd.NamedAgg(column = 'appid', aggfunc = 'nunique'),
         average_rank = pd.NamedAgg(column = 'rank', aggfunc = 'mean')
        ).to_dict('index')
    analysis['category_saturation'] = category_saturation

    # 32 New Category Trend
    # Placeholder, requires new category detection, skipped
    analysis['new_category_trend'] = "Placeholder, requires new category detection"

    #33 App Retention
    df_app_retention = df.copy()
    df_app_retention['rank_group'] = pd.cut(df_app_retention['rank'], bins=[0, 10, 20, 50, 100], labels=['top_10', 'top_20', 'top_50', 'top_100'])
    app_retention = df_app_retention.groupby('type').agg(
        average_time_in_top_10 = pd.NamedAgg(column = 'rank_group', aggfunc = lambda x: (x == "top_10").sum()),
         average_time_in_top_20 = pd.NamedAgg(column = 'rank_group', aggfunc = lambda x: (x == "top_20").sum()),
         average_time_in_top_50 = pd.NamedAgg(column = 'rank_group', aggfunc = lambda x: (x == "top_50").sum()),
         average_time_in_top_100 = pd.NamedAgg(column = 'rank_group', aggfunc = lambda x: (x == "top_100").sum())
        ).to_dict('index')
    analysis['app_retention'] = app_retention
    return analysis

def analyze_feature_inspiration(data):
   """Analyzes features for inspiration from top apps."""
   if not data:
      logging.warning("No data available to analyze features for inspiration.")
      return {}
   #Place holder since the current data doesnt have feature/UI elements
   analysis = {}
   analysis['common_ui_elements'] = "Placeholder, requires manual analysis of screenshots and app info"
   analysis['avoidance_pattern'] = "Placeholder, requires manual analysis of screenshots and app info"
   analysis['emerging_features'] = "Placeholder, requires manual analysis of app info"
   analysis['common_app_icons_names'] = "Placeholder, requires manual analysis of app icons and names"
   return analysis

def analyze_event_driven(data):
    """Analyzes rank correlation with events"""
    if not data:
        logging.warning("No data available to analyze correlation with events.")
        return {}
    # Place holder, requires additional data, skipped
    analysis = {}
    analysis['event_impact'] = "Placeholder, requires external event tracking data"
    analysis['seasonal_impact'] = "Placeholder, requires external seasonal event data"
    return analysis

def analyze_external_correlation(data, start_date=None, end_date=None):
    """Analyzes app performance against external data"""
    if not data:
        logging.warning("No data available to analyze correlation with external factor")
        return {}

     # Placeholder for external data analysis
    analysis = {}
    reviews = fetch_reviews_from_d1(start_date, end_date)
    if reviews:
        df_reviews = pd.DataFrame(reviews)
         # Perform sentiment analysis, correlation with score, etc
        analysis['rating_reviews'] =  df_reviews.groupby('appid').agg(average_score = pd.NamedAgg(column='score', aggfunc='mean')).to_dict('index')
    else:
        analysis['rating_reviews'] = "No review data found"

    analysis['app_size'] = "Placeholder, requires app size data"
    analysis['external_factors'] = "Placeholder, requires external trend analysis"
    return analysis


def generate_report(analysis, timeframe="all", custom_date=None):
    """Generates a report based on the analysis."""
    report = {
      "report_type": "top100rank",
      "timeframe": timeframe,
      "custom_range": custom_date,
      "analysis": analysis
    }

    report_json = json.dumps(report, indent=4)
    logging.info(f"Report:\n{report_json}")

    return report_json
import json

def write_json_to_file(data, filename):
    """
    Writes a Python dictionary (or other JSON-serializable object) to a file as JSON.

    Args:
      data: The Python object to serialize to JSON.
      filename: The path to the file to write the JSON to.
    """
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4, default=str)
        print(f"Successfully wrote JSON to '{filename}'")
    except Exception as e:
        print(f"Error writing JSON to file '{filename}': {e}")



def process_report(timeframe="all", custom_date=None):
    start_date, end_date = get_start_and_end_date(timeframe, custom_date)
    data = fetch_data_from_d1(start_date, end_date)

    if not data:
        return None
    
    # review_data = fetch_reviews_from_d1(start_date, end_date)
    print('fetch data',len(data),data[:5])
    report = {}
    report['app_performance_report'] = analyze_app_performance(data)
    report['market_trend_report'] = analyze_market_trends(data)
    report['competitive_report'] = analyze_competitive(data)
    report['app_attribute_report'] = analyze_app_attributes(data)
    report['strategic_report'] = analyze_strategic_insights(data)
    report['feature_report'] = analyze_feature_inspiration(data)
    report['event_report'] = analyze_event_driven(data)
    # report['external_report'] = analyze_external_correlation(data, start_date, end_date)
    report = generate_report(report, timeframe, custom_date)
    return report

# Example usage
if __name__ == "__main__":
    # Example data
    sample_data = [
        {
            "platform": "iOS",
            "type": "Game",
            "cid": "123",
            "cname": "Puzzle",
            "rank": 1,
            "appid": "com.example.app1",
            "appname": "Example App 1",
            "icon": "https://example.com/icon1.png",
            "link": "https://example.com/1",
            "title": "Top App",
            "updateAt": datetime.utcnow().isoformat(),
            "country": "US"
        },
         {
            "platform": "Android",
            "type": "Game",
            "cid": "123",
            "cname": "Action",
            "rank": 2,
            "appid": "com.example.app2",
            "appname": "Example App 2",
            "icon": "https://example.com/icon2.png",
            "link": "https://example.com/2",
            "title": "Top App",
           "updateAt": datetime.utcnow().isoformat(),
            "country": "US"
        },
         {
            "platform": "iOS",
            "type": "App",
            "cid": "456",
            "cname": "Productivity",
            "rank": 3,
            "appid": "com.example.app3",
            "appname": "Example App 3",
            "icon": "https://example.com/icon3.png",
            "link": "https://example.com/3",
            "title": "Top App",
            "updateAt": datetime.utcnow().isoformat(),
            "country": "US"
        },
           {
            "platform": "Android",
            "type": "App",
            "cid": "789",
            "cname": "Utility",
            "rank": 4,
            "appid": "com.example.app4",
            "appname": "Example App 4",
            "icon": "https://example.com/icon4.png",
            "link": "https://example.com/4",
            "title": "Top App",
            "updateAt": datetime.utcnow().isoformat(),
             "country": "CA"
        },
        {
            "platform": "iOS",
            "type": "Game",
            "cid": "123",
            "cname": "Puzzle",
            "rank": 1,
            "appid": "com.example.app5",
            "appname": "Example App 5",
            "icon": "https://example.com/icon5.png",
            "link": "https://example.com/5",
            "title": "Top App",
            "updateAt": (datetime.utcnow() - timedelta(days=1)).isoformat(),
             "country": "US"
        },
        {
          "platform": "iOS",
          "type": "Game",
          "cid": "123",
          "cname": "Action",
          "rank": 5,
          "appid": "com.example.app6",
          "appname": "Example App 6",
          "icon": "https://example.com/icon6.png",
          "link": "https://example.com/6",
          "title": "Top App",
          "updateAt": (datetime.utcnow() - timedelta(days=1)).isoformat(),
          "country": "US"
          }
         ,
        {
            "platform": "iOS",
            "type": "App",
            "cid": "456",
            "cname": "Productivity",
            "rank": 3,
            "appid": "com.example.app7",
            "appname": "Example App 7",
            "icon": "https://example.com/icon3.png",
            "link": "https://example.com/7",
            "title": "Top App",
            "updateAt":  (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "country": "US"
        },
           {
            "platform": "Android",
            "type": "App",
            "cid": "789",
            "cname": "Utility",
            "rank": 4,
            "appid": "com.example.app8",
            "appname": "Example App 8",
            "icon": "https://example.com/icon4.png",
            "link": "https://example.com/8",
            "title": "Top App",
            "updateAt":  (datetime.utcnow() - timedelta(days=1)).isoformat(),
              "country": "CA"
        }

        # Add more rows as needed
    ]
    sample_review_data = [
      {
            "appid": "com.example.app1",
             "appname": "Example App 1",
            "country": "US",
            "keyword": "great app",
            "score": 4.5,
            "userName": "user1",
            "date": datetime.utcnow().isoformat(),
           "review": "this is a great app",
      },
       {
             "appid": "com.example.app2",
             "appname": "Example App 2",
            "country": "US",
            "keyword": "bad app",
            "score": 1.5,
            "userName": "user2",
             "date": datetime.utcnow().isoformat(),
           "review": "this is a bad app",
      },
      {
           "appid": "com.example.app2",
           "appname": "Example App 2",
            "country": "US",
            "keyword": "ok app",
            "score": 3,
            "userName": "user3",
            "date": datetime.utcnow().isoformat(),
           "review": "this is a ok app",
      }
    ]
    try:
         logging.info("Processing and inserting sample data...")
         # process_ios_top100_rank_data_and_insert(sample_data)
         logging.info("Sample data processing complete.")

         logging.info("Processing and inserting sample review data...")
         # insert_into_ios_review_data(sample_review_data)
         logging.info("Sample review data processing complete.")

    except Exception as e:
         logging.error(f"An unexpected error occurred during data insertion: {e}")
    
    # Generate reports
    logging.info("Generating reports...")
    
    # Generate report for last week
    report_last_week = process_report(timeframe="last week")
    if report_last_week:
      logging.info(f"Report for last week generated")
    else:
      logging.info("No report was generated for last week")
    output_file = "my_data.json"
    os.makedirs(RESULT_FOLDER, exist_ok=True)
    
    write_json_to_file(report_last_week, os.path.join(RESULT_FOLDER,output_file))

    # Generate report for last month
    # report_last_month = process_report(timeframe="last month")
    # if report_last_month:
       # logging.info(f"Report for last month generated")
    # else:
        # logging.info("No report was generated for last month")

    # Generate report for custom date range
    # report_custom = process_report(timeframe="custom", custom_date="2024-01-01")
    # if report_custom:
        # logging.info(f"Report for custom date generated")
    # else:
        # logging.info("No report was generated for custom date")

    # Generate default report for all data
    # report_all = process_report()
    # if report_all:
         # logging.info(f"Report for all data generated")
    # else:
      # logging.info("No report was generated for all data")
