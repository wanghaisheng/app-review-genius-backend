import nltk
from nltk.tokenize import sent_tokenize
import torch
from transformers import pipeline
import pandas as pd


class ReviewAnalyzer():
    def __init__(self):
        nltk.download('punkt_tab')
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.classifier = pipeline(task="text-classification", model="SamLowe/roberta-base-go_emotions", top_k=None, device=self.device)

    def process_review(self, review):
        # Split and classify
        sentences = sent_tokenize(review)
        sentence_scores = []
        for sentence in sentences:
            # classifier returns list of dicts that have only one emotion key and corresponding score in each dict
            results = self.classifier(sentence)[0]
            # Convert the list of dictionaries into a single dictionary
            dict_scores = {d['label']: d['score'] for d in results}
            sentence_scores.append(dict_scores)
        
        # Create a DataFrame from the sentence scores
        scores_df = pd.DataFrame(sentence_scores)
        
        # Compute average scores for each emotion category
        average_scores = scores_df.mean(numeric_only=True, axis=0)
        return average_scores
    
    def create_aggr_scoring(self, df):
        # Assumes df has "review" column containing text reviews
        emotion_averages = df["review"].apply(self.process_review)
        scored_appstore = pd.concat([df, emotion_averages], axis=1)
        scored_appstore["date"] = pd.to_datetime(scored_appstore["date"])

        emotion_columns = [
            'neutral', 'approval', 'realization', 'annoyance', 'disappointment', 'optimism', 
            'disapproval', 'admiration', 'sadness', 'confusion', 'joy', 'disgust', 'desire', 
            'amusement', 'fear', 'excitement', 'caring', 'relief', 'love', 'surprise', 
            'curiosity', 'gratitude', 'embarrassment', 'anger', 'nervousness', 'remorse', 
            'pride', 'grief'
        ]

        mean_emotion_scores = scored_appstore.groupby('app_id')[emotion_columns].mean().reset_index()
        
        return mean_emotion_scores
