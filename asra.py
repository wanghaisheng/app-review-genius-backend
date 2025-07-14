import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import sqlite3
from ratelimit import limits, sleep_and_retry
import os
import logging
from typing import Dict, List, Optional
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='asra.log'
)

class ASRAConfig:
    def __init__(self, 
                 max_reviews: int = 100,
                 analysis_depth: str = "medium",  # "light", "medium", "deep"
                 cache_ttl: int = 86400):  # Cache TTL in seconds (24 hours default)
        self.max_reviews = max_reviews
        self.analysis_depth = analysis_depth
        self.cache_ttl = cache_ttl
        
        # Validate inputs
        if max_reviews < 1:
            raise ValueError("max_reviews must be positive")
        if analysis_depth not in ["light", "medium", "deep"]:
            raise ValueError("analysis_depth must be 'light', 'medium', or 'deep'")

class ASRA:
    def __init__(self, 
                 app_id: str, 
                 platform: str = "ios", 
                 cache_db: str = "asra_cache.db",
                 config: ASRAConfig = None):
        self.app_id = app_id
        self.platform = platform.lower()
        self.cache_db = cache_db
        self.reviews: List[Dict] = []
        self.config = config or ASRAConfig()
        self.setup_cache()
        self.logger = logging.getLogger(__name__)

    def setup_cache(self) -> None:
        """Initialize SQLite cache database"""
        try:
            self.conn = sqlite3.connect(self.cache_db)
            self.cursor = self.conn.cursor()
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    analysis TEXT,
                    timestamp TEXT
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Failed to setup cache: {str(e)}")
            raise

    def crawl_ios_reviews(self) -> None:
        """Crawl reviews from iOS App Store"""
        try:
            url = f"https://itunes.apple.com/rss/customerreviews/id={self.app_id}/sortBy=mostRecent/json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            entries = data.get('feed', {}).get('entry', [])
            
            for entry in entries[:self.config.max_reviews]:
                if 'content' in entry:
                    review = {
                        'id': entry.get('id', {}).get('label', ''),
                        'text': entry.get('content', {}).get('label', ''),
                        'rating': entry.get('im:rating', {}).get('label', ''),
                        'date': entry.get('updated', {}).get('label', '')
                    }
                    self.reviews.append(review)
            self.logger.info(f"Crawled {len(self.reviews)} iOS reviews")
        except RequestException as e:
            self.logger.error(f"Failed to crawl iOS reviews: {str(e)}")
            raise

    def crawl_android_reviews(self) -> None:
        """Crawl reviews from Google Play Store"""
        try:
            url = f"https://play.google.com/store/apps/details?id={self.app_id}&showAllReviews=true"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            review_elements = soup.find_all('div', class_='review-body')
            
            for i, review in enumerate(review_elements[:self.config.max_reviews]):
                review_text = review.text.strip()
                self.reviews.append({
                    'id': f"android_{i}_{datetime.now().timestamp()}",
                    'text': review_text,
                    'rating': None,
                    'date': datetime.now().isoformat()
                })
            self.logger.info(f"Crawled {len(self.reviews)} Android reviews")
        except RequestException as e:
            self.logger.error(f"Failed to crawl Android reviews: {str(e)}")
            raise

    @sleep_and_retry
    @limits(calls=30, period=60)
    def analyze_with_grok(self, text: str) -> Dict:
        """Analyze text using Grok API with caching"""
        try:
            # Check cache first
            self.cursor.execute("""
                SELECT analysis FROM reviews 
                WHERE content=? AND 
                timestamp > datetime('now', '-' || ? || ' seconds')
            """, (text, self.config.cache_ttl))
            cached = self.cursor.fetchone()
            if cached:
                return json.loads(cached[0])

            # Mock Grok API call
            api_url = "https://api.xai.com/grok/analyze"
            headers = {
                "Authorization": f"Bearer {os.environ.get('GROK_API_KEY')}",
                "Content-Type": "application/json"
            }
            payload = {
                "text": text,
                "analysis_type": "sentiment_and_insights",
                "depth": self.config.analysis_depth
            }
            
            response = requests.post(api_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            analysis = response.json()
            
            # Cache the result
            self.cursor.execute(
                "INSERT OR REPLACE INTO reviews (id, content, analysis, timestamp) VALUES (?, ?, ?, ?)",
                (hash(text), text, json.dumps(analysis), datetime.now().isoformat())
            )
            self.conn.commit()
            return analysis
        except (RequestException, sqlite3.Error) as e:
            self.logger.error(f"Analysis failed for text '{text[:50]}...': {str(e)}")
            return {"error": str(e)}

    def analyze_reviews(self) -> Dict:
        """Analyze all crawled reviews and generate report"""
        try:
            if self.platform == "ios":
                self.crawl_ios_reviews()
            else:
                self.crawl_android_reviews()

            results = {
                "sentiment_summary": {"positive": 0, "negative": 0, "neutral": 0},
                "trends": [],
                "common_issues": [],
                "feature_requests": [],
                "positive_aspects": [],
                "reviews": []
            }

            for review in self.reviews:
                analysis = self.analyze_with_grok(review['text'])
                if "error" not in analysis:
                    sentiment = analysis.get('sentiment', 'neutral')
                    results["sentiment_summary"][sentiment] += 1
                    results["trends"].extend(analysis.get('trends', []))
                    results["common_issues"].extend(analysis.get('issues', []))
                    results["feature_requests"].extend(analysis.get('feature_requests', []))
                    results["positive_aspects"].extend(analysis.get('positive_aspects', []))
                
                results["reviews"].append({
                    "text": review['text'],
                    "analysis": analysis
                })
            
            return results
        except Exception as e:
            self.logger.error(f"Review analysis failed: {str(e)}")
            raise

    def generate_report(self) -> None:
        """Generate and print the analysis report"""
        try:
            results = self.analyze_reviews()
            
            print("=== ASRA Report ===")
            print(f"Analysis Depth: {self.config.analysis_depth}")
            print(f"Reviews Analyzed: {len(results['reviews'])}")
            
            print("\nSentiment Summary:")
            total = sum(results["sentiment_summary"].values())
            for sentiment, count in results["sentiment_summary"].items():
                percentage = (count / total * 100) if total > 0 else 0
                print(f"{sentiment.capitalize()}: {count} reviews ({percentage:.1f}%)")

            for section in ["Trends", "Common Issues", "Feature Requests", "Positive Aspects"]:
                print(f"\n{section}:")
                items = set([item for item in results[section.lower().replace(" ", "_")]])
                for item in items:
                    print(f"- {item}")

            print("\nSample Reviews (first 5):")
            for review in results["reviews"][:5]:
                print(f"Review: {review['text'][:100]}...")
                print(f"Analysis: {review['analysis']}\n")
                
        except Exception as e:
            self.logger.error(f"Report generation failed: {str(e)}")
            print(f"Error generating report: {str(e)}")

def main():
    try:
        config = ASRAConfig(
            max_reviews=50,  # Limit to 50 reviews
            analysis_depth="deep",  # Deep analysis
            cache_ttl=43200  # 12 hours cache
        )
        
        analyzer = ASRA(
            app_id="com.example.app",
            platform="android",
            config=config
        )
        analyzer.generate_report()
    except Exception as e:
        logging.error(f"Application failed: {str(e)}")
        print(f"Application error: Check logs for details")

if __name__ == "__main__":
    main()
