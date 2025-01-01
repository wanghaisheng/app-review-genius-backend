import os
import re
from datetime import datetime
from app_store_scraper import AppStore
import pandas as pd
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

# Function to clean the review text
def clean_text(text):
    # Replace newline characters and strip leading/trailing whitespace
    text = text.replace("\n", " ").strip()

    # Remove non-ASCII characters and emojis
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)

    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)

    return text

# Initialize the transformers pipeline for sentiment analysis with truncation and padding
model_name = "distilbert-base-uncased-finetuned-sst-2-english"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)
sentiment_pipeline = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

# Define a function to analyze sentiment with explicit truncation and padding
def analyze_sentiment(text):
    # Ensure text is a string
    if isinstance(text, str):
        # Tokenize with truncation and padding, ensuring max_length is 512
        inputs = tokenizer(text, truncation=True, padding='max_length', max_length=512, return_tensors="pt")
        
        # Pass the inputs to the model and get the output
        outputs = model(**inputs)
        
        # Extract sentiment
        scores = outputs.logits.softmax(dim=1)
        score = scores.max().item()
        label = 'POSITIVE' if scores.argmax().item() == 1 else 'NEGATIVE'
        
        return score, label
    else:
        return 0, 'Neutral'


# Fetch reviews from Apple App Store
app_name = 'eureka-forbes-aquaguard'
store_reviews = AppStore(country="in", app_name=app_name, app_id='1463742085')
store_reviews.review(how_many=5000)

# Convert reviews to DataFrame
df = pd.DataFrame(store_reviews.reviews)

# Select necessary columns and rename them
mydata = df[['date', 'rating', 'review']]
mydata.columns = ['date', 'app_rating', 'review']

# Add a new column 'year' by extracting it from the 'date' column
mydata['year'] = pd.to_datetime(mydata['date']).dt.year

# Reorder columns to place 'year' as the first column
mydata = mydata[['year', 'date', 'app_rating', 'review']]

# Format the date from "DD/MM/YY HH:MM" to "DD/MM/YY"
mydata['date'] = pd.to_datetime(mydata['date']).dt.strftime('%d/%m/%y')

# Clean the review text
mydata['cleaned_review'] = mydata['review'].apply(clean_text)

# Apply sentiment analysis using the transformers pipeline
mydata[['sentiment', 'sentiment_category']] = mydata['cleaned_review'].apply(lambda x: pd.Series(analyze_sentiment(x)))

# Get the current date and time
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Save the reviews with sentiment analysis to a separate CSV file
sentiment_reviews_file_path = os.path.join(os.getcwd(), f'apple_store_reviews_with_sentiment_transformers_{timestamp}.csv')

mydata.to_csv(sentiment_reviews_file_path, index=False)
print(f'Reviews with sentiment analysis saved to {sentiment_reviews_file_path}')

# Display the first 5 and last 5 reviews after sentiment analysis
print("First 5 Reviews After Sentiment Analysis:")
print(mydata.head(5).to_string(index=False))

print("Last 5 Reviews After Sentiment Analysis:")
print(mydata.tail(5).to_string(index=False))
