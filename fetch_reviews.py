# https://github.com/futurice/app-store-web-scraper

from app_store_web_scraper import AppStoreEntry

# See below for instructions on finding an app's ID.
MINECRAFT_APP_ID = 479516143

# Look up the app in the British version of the App Store.
app = AppStoreEntry(app_id=MINECRAFT_APP_ID, country="gb",limit=500)

# Iterate over the app's reviews, which are fetched lazily in batches.
for review in app.reviews():
    print("-----")
    print("ID:", review.id)
    print("Rating:", review.rating)
    print("Review:", review.content)
