#!/usr/bin/env python3
"""
HIVE OPS DevAI - Therapist & Creative Writing Assistant
Cleaned version with configurable paths
"""

import os

# CONFIGURATION - Update these paths for your system
CONFIG = {
    "style_model_path": os.path.expanduser("~/.hive/models/style_classifier.pkl"),
    "data_dir": os.path.expanduser("~/.hive/data"),
    "nltk_data": os.path.expanduser("~/.hive/nltk_data"),
}

# Ensure directories exist
os.makedirs(os.path.dirname(CONFIG["style_model_path"]), exist_ok=True)
os.makedirs(CONFIG["data_dir"], exist_ok=True)

import os
import random
import pickle
import joblib
import requests
import difflib
import pronouncing
import matplotlib.pyplot as plt
import numpy as np
import nltk
import re
from functools import lru_cache
from nltk.corpus import cmudict, wordnet
from nltk import word_tokenize
from textblob import TextBlob
from wordcloud import WordCloud
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from PIL import Image
from sklearn.cluster import KMeans
from music21 import stream, note, midi
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from flask import Flask, jsonify, request
import language_tool_python
from docx import Document
def setup_nltk_resources():
    nltk.download('cmudict')
    nltk.download('wordnet')
class DependencyManager:
    def __init__(self):
        self.sentiment_analyzer = None
        self.style_model = None
        self.pronouncing_dict = cmudict.dict()
    def initialize_sentiment_analyzer(self):
        if self.sentiment_analyzer is None:
            try:
                self.sentiment_analyzer = SentimentIntensityAnalyzer()
            except Exception as e:
                print(f"Error initializing sentiment analyzer: {e}")
        return self.sentiment_analyzer
    def load_style_model(self):
        if self.style_model is None:
            try:
                self.style_model = joblib.load('os.path.expanduser('~/.hive/models/style_classifier.pkl')')
            except Exception as e:
                print(f"Error loading style model: {e}")
                self.style_model = None
        return self.style_model
    def get_pronouncing_dict(self):
        return self.pronouncing_dict
class LyricsProcessor:
    def __init__(self, pronouncing_dict):
        self.d = cmudict.dict()
        self.pronouncing_dict = pronouncing_dict
    def syllable_count(self, word):
        try:
            return [len(list(y for y in x if y[-1].isdigit())) for x in self.d[word.lower()]][0]
        except KeyError:
            return len([char for char in word if char.lower() in "aeiou"])
    def is_rhyme(self, word1, word2):
        word1 = word1.lower()
        word2 = word2.lower()
        phonetics1 = self.pronouncing_dict.get(word1)
        phonetics2 = self.pronouncing_dict.get(word2)
        if phonetics1 and phonetics2:
            for pron1 in phonetics1:
                for pron2 in phonetics2:
                    if pron1[-1] == pron2[-1]:  # Simplified rhyme check
                        return True
        return False
    def detect_internal_rhymes(self, line):
        words = word_tokenize(line.lower())
        rhymes = []
        for i, word in enumerate(words):
            for j in range(i + 1, len(words)):
                if self.is_rhyme(word, words[j]):
                    rhymes.append((word, words[j]))
        return rhymes
class TagManager:
    def __init__(self):
        self.tags = {
            "Themes": ["@Themes", "@ThemesS3", "@ThemeS4", "@Key_Themes"],
            "Ideas": ["@Ideas", "@IdeaS3", "@Profound_LYRICS", "@Overall_AnalysiS"],
            "Narratives": ["@Narratives", "@NarrativeS3"],
            "Elements": ["@Elements", "@ElementsS3", "@Writing_Style"],
            "Places": ["@Places", "@PlacesS3"],
            "Characters": ["@Characters", "@CharactersS3"],
            "Things": ["@Things", "@ThingsS4"],
            "Event_Progression": ["@Event_Progression", "@Event_ProgressionS3"]
        }
        self.links = {
            "@Themes": ["@ThemeS2", "@Key_Themes", "@NarrativesS2", "@MY_LYRICS"],
            "@ThemesS3": ["@Profound_LYRICS", "@IdeaS2", "@MY_LYRICS"],
            "@ThemeS4": ["@Event_ProgressionS2", "@CharactersS2", "@MY_LYRICS"],
            "@Key_Themes": ["@Example_BreakdOWN", "@NarrativesS3", "@MY_LYRICS"],
            "@Example_BreakdOWN": ["@ElementsS3", "@MY_LYRICS"],
            "@Ideas": ["@IdeaS2", "@WritingStyleS1", "@ElementsS2", "@Syllable_Pattern", "@Flow_S1", "@MY_LYRICS"],
            "@IdeaS3": ["@NarrativeS3", "@PlacesS2", "@MY_LYRICS"],
            "@Profound_LYRICS": ["@ThemeS3", "@Overall_AnalysiS", "@MY_LYRICS"],
            "@Overall_AnalysiS": ["@Event_ProgressionS3", "@ThingsS4", "@MY_LYRICS"],
            "@Narratives": ["@NarrativeS2", "@ThemeS2", "@CharactersS2", "@MY_LYRICS"],
            "@NarrativeS3": ["@PlacesS3", "@IdeaS3", "@MY_LYRICS"],
            "@Elements": ["@ElementsS2", "@Syllable_Pattern", "@Flow_S1", "@IdeaS2", "@Writing_Style", "@MY_LYRICS"],
            "@ElementsS3": ["@Example_BreakdOWN", "@MY_LYRICS"],
            "@Writing_Style": ["@CharactersS3", "@ThingsS4", "@MY_LYRICS"],
            "@Places": ["@PlacesS2", "@IdeaS3", "@NarrativeS3", "@MY_LYRICS"],
            "@PlacesS3": ["@CharactersS3", "@MY_LYRICS"],
            "@Characters": ["@CharactersS2", "@NarrativeS2", "@ThemeS4", "@MY_LYRICS"],
            "@CharactersS3": ["@Writing_Style", "@PlacesS3", "@MY_LYRICS"],
            "@Things": ["@ThingsS2", "@NarrativeS2", "@MY_LYRICS"],
            "@ThingsS4": ["@Overall_AnalysiS", "@MY_LYRICS"],
            "@Event_Progression": ["@Event_ProgressionS2", "@ThemeS4", "@NarrativeS2", "@MY_LYRICS"],
            "@Event_ProgressionS3": ["@Overall_AnalysiS", "@CharactersS3", "@MY_LYRICS"]
        }
    def get_tag(self, tag_name):
        return self.tags.get(tag_name, None)
    def get_links(self, tag_name):
        return self.links.get(tag_name, [])
    def process_tags(self, text):
        found_tags = []
        for tag in self.tags:
            for sub_tag in self.get_tag(tag):
                if sub_tag in text:
                    found_tags.append(sub_tag)
                    linked_tags = self.get_links(sub_tag)
                    print(f"Tag: {sub_tag} found. Links to: {linked_tags}")
        return found_tags
app = Flask(__name__)
dependency_manager = DependencyManager()
lyrics_processor = LyricsProcessor(dependency_manager.get_pronouncing_dict())
tag_manager = TagManager()
@app.route('/analyze_lyrics', methods=['POST'])
def analyze_lyrics():
    data = request.json
    lyrics = data.get('lyrics')
    if not lyrics:
        return jsonify({"status": "error", "message": "No lyrics provided"}), 400
    sentiment_analyzer = dependency_manager.initialize_sentiment_analyzer()
    analysis = lyrics_processor.syllable_count(lyrics)  # Example of using encapsulated functionality
    sentiment = sentiment_analyzer.polarity_scores(lyrics) if sentiment_analyzer else None
    return jsonify({"status": "success", "analysis": analysis, "sentiment": sentiment})
@app.route('/process_tags', methods=['POST'])
def process_tags_route():
    data = request.json
    text = data.get('text')
    if not text:
        return jsonify({"status": "error", "message": "No text provided"}), 400
    found_tags = tag_manager.process_tags(text)
    return jsonify({"status": "success", "tags": found_tags})
def generate_rhyming_bank(lyrics_processor, word, rhyme_type='perfect'):
    if rhyme_type == 'perfect':
        return pronouncing.rhymes(word)
    elif rhyme_type == 'slant':
        return pronouncing.rhymes(word)  # Placeholder for slant rhymes
    elif rhyme_type == 'alliteration':
        return [w for w in lyrics_processor.pronouncing_dict if w.startswith(word[0])]
    return []
def detect_rhyme_scheme(lyrics_processor, lines):
    rhyme_scheme = []
    rhyme_map = defaultdict(str)
    current_rhyme_letter = 'A'
    for line in lines:
        words = word_tokenize(line.lower())
        last_word = words[-1]
        for key, val in rhyme_map.items():
            if lyrics_processor.is_rhyme(key, last_word):
                rhyme_scheme.append(val)
                break
        else:
            rhyme_map[last_word] = current_rhyme_letter
            rhyme_scheme.append(current_rhyme_letter)
            current_rhyme_letter = chr(ord(current_rhyme_letter) + 1)
    return ''.join(rhyme_scheme)
def analyze_rhyme_complexity(lyrics_processor, lines):
    rhyme_scheme = detect_rhyme_scheme(lyrics_processor, lines)
    internal_rhyme_count = sum([len(lyrics_processor.detect_internal_rhymes(line)) for line in lines])
    slant_rhymes = sum([1 for line in lines for word in word_tokenize(line)
                        if len(difflib.get_close_matches(word, lines, n=2)) > 1])
    complexity_score = len(set(rhyme_scheme)) + internal_rhyme_count + slant_rhymes
    return {
        'rhyme_scheme': rhyme_scheme,
        'internal_rhyme_count': internal_rhyme_count,
        'slant_rhyme_count': slant_rhymes,
        'complexity_score': complexity_score
    }
if __name__ == '__main__':
    setup_nltk_resources()
    app.run(debug=True)
class EnhancedTherapist:
    def __init__(self):
        self.analysis_tags = [
            "@Themes:", "@Ideas:", "@Narratives:", "@Elements:", 
            "@Places:", "@Characters:", "@Things:", "@Event Progression:",
            "@Key Themes:", "@Writing Style:", "@Syllable Pattern and Flow:"
        ]
        self.secondary_tags = [
            "@Theme:@", "@Idea:@", "@Narrative:@", "@Elements:@",
            "@Places:@", "@Characters:@", "@Things:@", "@Event Progression:@", 
            "@Key Themes:@", "@Writing Style:@", "@Syllable Pattern and Flow:@"
        ]
        self.tertiary_tags = ["@breakdown of song@", "@lyrics@"]
        self.additional_lyrics_tags = [
            "@sincity", "@artists_songs_from_tucson", "@interviews_and_places", "@about_tucson ",
            "@inspiration_songs", "@old_lyrics"
        ]
        self.code_of_conduct = [
            "@my_code_of_conduct", "@Ethic:@", "@Principle:@", "@Adaptive Interaction@", 
            "@Strategic Trust and Loyalty@", "@Calculated Risk-Taking@", 
            "@Maintaining Moral Flexibility@", "@Emotional Masking@", 
            "@Discretion and Low Profile@", "@Ethical Opportunism@", 
            "@Situational Ethics in Survival@", "@Duality in Actions@", 
            "@Survival by Any Means Necessary@", "@Embrace Resilience and Endurance@", 
            "@Prioritize Self-Reliance and Independence@", "@Maintain Emotional Detachment and Focus@", 
            "@Execute Strategic and Calculated Actions@", "@Adopt Aggressive Survival Tactics When Necessary@", 
            "@Challenge Unhelpful Societal Norms@", "@Focus on Continuous Financial Growth and Hustle@", 
            "@Acknowledge and Navigate Moral Ambiguities@", "@Exercise Caution in Relationships and Trust@", 
            "@Utilize Skillful Communication and Influence@", "@Draw on Spiritual Strength and Reflection@", 
            "@Embrace Primal Instincts and Drive@", "@Stay Committed to Learning and Self-Improvement@", 
            "@Maintain a Strategic Focus on Long-Term Goals@"
        ]
        self.old_lyrics = ["@old_lyrics"]
        self.inspiration_songs = ["@inspiration_songs"]
        self.about_tucson_tags = ["@sincity", "@artists_songs_from_tucson", "@interviews_and_places"]
        self.sentiment_analyzer = self.initialize_pipeline("sentiment-analysis")
        self.theme_extractor = self.initialize_pipeline("ner", model="dslim/bert-base-NER")
        self.style_model = None  # Placeholder for lazy loading of the style classifier model
        self.characters = {}
    def initialize_pipeline(self, task, model=None):
        try:
            pipeline_model = pipeline(task, model=model) if model else pipeline(task)
            return pipeline_model
        except Exception as e:
            print(f"Error initializing {task} pipeline: {e}")
            return None
    def process_tags(self, text):
        all_tags = self.analysis_tags + self.secondary_tags + self.tertiary_tags + \
                   self.additional_lyrics_tags + self.code_of_conduct
        found_tags = [tag for tag in all_tags if tag in text]
        return found_tags
    def clean_lyrics(self, lyrics):
        return lyrics.replace("profanity_word", "")
    def process_lyrics(self, lyrics):
        if lyrics not in self.old_lyrics and lyrics not in self.inspiration_songs:
            cleaned_lyrics = self.clean_lyrics(lyrics)
            return cleaned_lyrics
        return None
    def check_code_of_conduct(self, text):
        for tag in self.code_of_conduct:
            if tag in text:
                return tag
        return None
    def analyze_text(self, text):
        tags = self.process_tags(text)
        if not tags:
            return "No relevant tags found."
        if "@lyrics@" in tags and self.check_code_of_conduct(text):
            lyrics = self.process_lyrics(text)
            return lyrics if lyrics else "Lyrics already used."
        if any(tag in tags for tag in ["@Key Themes:@", "@Writing Style:@", "@Syllable Pattern and Flow:@"]):
            return f"Deep analysis found for tag: {tags}"
        else:
            return f"Analysis found tag: {tags}"
    def generate_rhyming_bank(self, word, rhyme_type='perfect'):
        tags = self.process_tags(word)
        if "@Force_Slant_Rhyme" in tags:
            rhyme_type = 'slant'
        elif "@Force_Alliteration" in tags:
            rhyme_type = 'alliteration'
        if rhyme_type == 'perfect':
            return pronouncing.rhymes(word)
        elif rhyme_type == 'slant':
            return pronouncing.rhymes(word)  # Placeholder for slant rhymes
        elif rhyme_type == 'alliteration':
            return [w for w in pronouncing.words() if w.startswith(word[0])]
        return []
    def suggest_internal_rhymes(self, lyrics):
        tags = self.process_tags(lyrics)
        words = lyrics.split()
        internal_rhymes = {}
        for word in words:
            rhymes = self.generate_rhyming_bank(word)
            if rhymes:
                internal_rhymes[word] = rhymes
        if "@Emphasize_Rhyme" in tags:
            for word, rhymes in internal_rhymes.items():
                internal_rhymes[word] = [rhyme.upper() for rhyme in rhymes]
        return internal_rhymes
    def analyze_meter(self, lyrics):
        tags = self.process_tags(lyrics)
        lines = lyrics.split('\n')
        meter_analysis = {}
        for line in lines:
            words = line.split()
            meter = [self.syllable_count(word) for word in words]
            if "@Highlight_Irregularities" in tags and any(syllables > 3 for syllables in meter):
                meter = [f"*{syllables}*" for syllables in meter]
            meter_analysis[line] = meter
        return meter_analysis
    def suggest_meter_adjustments(self, lyrics):
        tags = self.process_tags(lyrics)
        meter_analysis = self.analyze_meter(lyrics)
        adjustments = {}
        for line, meter in meter_analysis.items():
            if "@Suggest_Regular_Meter" in tags and any(syllables != 4 for syllables in meter):
                adjustments[line] = "Consider adjusting to a 4-syllable meter"
            elif "@Allow_Flexible_Meter" in tags:
                adjustments[line] = "Flexible meter allowed"
            else:
                adjustments[line] = "Meter seems fine"
        return adjustments
    def generate_metaphors(self, theme):
        tags = self.process_tags(theme)
        metaphors = {
            'love': ["Love is a battlefield", "Love is a rose"],
            'life': ["Life is a journey", "Life is a river"],
        }
        if "@Abstract_Metaphor" in tags:
            metaphors['love'] = ["Love is an enigma", "Love is a fleeting shadow"]
            metaphors['life'] = ["Life is a mirage", "Life is a puzzle"]
        return metaphors.get(theme.lower(), [])
    def generate_similes(self, theme):
        tags = self.process_tags(theme)
        similes = {
            'love': ["Love is like a red, red rose", "Love is like the wind"],
            'life': ["Life is like a box of chocolates", "Life is like a journey"],
        }
        if "@Complex_Simile" in tags:
            similes['love'] = ["Love is like a maze with no exit", "Love is like a double-edged sword"]
            similes['life'] = ["Life is like a river with no end", "Life is like a labyrinth"]
        return similes.get(theme.lower(), [])
    def adjust_lyrics_mood(self, lyrics, desired_mood):
        tags = self.process_tags(lyrics)
        analysis = TextBlob(lyrics)
        current_sentiment = analysis.sentiment.polarity
        if "@Subtle_Mood_Adjustment" in tags and desired_mood == 'positive' and current_sentiment < 0:
            return lyrics.replace("dark", "dim").replace("cold", "cool")
        elif "@Dramatic_Mood_Shift" in tags and desired_mood == 'negative' and current_sentiment > 0:
            return lyrics.replace("bright", "bleak").replace("warm", "cold")
        if desired_mood == 'positive' and current_sentiment < 0:
            return lyrics.replace("sad", "happy")
        elif desired_mood == 'negative' and current_sentiment > 0:
            return lyrics.replace("happy", "sad")
        return lyrics
    def brainstorm_with_prompts(self, theme, current_lyrics):
        tags = self.process_tags(theme)
        prompts = {
            'love': ["What if love was a war?", "Describe love using a natural element."],
            'life': ["What if life was a game?", "Write about life as a river."],
        }
        if "@Philosophical_Angle" in tags:
            prompts['love'] = ["Is love an illusion?", "Can love exist without conflict?"]
            prompts['life'] = ["Is life a simulation?", "What if life had no meaning?"]
        return prompts.get(theme.lower(), [])
    def track_narrative_progression(self, lyrics):
        tags = self.process_tags(lyrics)
        if "@Complex_Narrative" in tags:
            return "Analysis of a complex, nonlinear narrative progression"
        return "Narrative analysis of the song's progression"
    def suggest_character_development(self, lyrics, character):
        tags = self.process_tags(lyrics)
        if "@Tragic_Character" in tags:
            return f"Suggestions for developing the tragic arc of {character}: Increase inner conflict and inevitable downfall."
        return f"Suggestions for developing the character: {character}"
    def enhance_chorus(self, lyrics):
        tags = self.process_tags(lyrics)
        if "@Epic_Chorus" in tags:
            return "Suggestions for creating an epic, anthemic chorus"
        return "Enhanced chorus suggestions"
    def suggest_cultural_references(self, theme):
        tags = self.process_tags(theme)
        references = {
            'love': ["Romeo and Juliet", "Cleopatra and Antony"],
            'life': ["The Odyssey", "The Pilgrim's Progress"],
        }
        if "@Modern_References" in tags:
            references['love'] = ["Bonnie and Clyde", "Jack and Rose"]
            references['life'] = ["The Matrix", "Fight Club"]
        return references.get(theme.lower(), [])
    def generate_wordplay(self, theme, keywords):
        tags = self.process_tags(theme)
        wordplay = {
            'love': ["You make my heart skip a beat, like a DJ remix"],
            'life': ["Life's a pitch, and then you hit a home run"],
        }
        if "@Clever_Wordplay" in tags:
            wordplay['love'].append("Love is a game, and I'm playing with aces")
            wordplay['life'].append("Life's a canvas, and I'm painting the skies")
        return wordplay.get(theme.lower(), [])
    def dynamic_feedback_loop(self, lyrics):
        tags = self.process_tags(lyrics)
        if "@Complex_Feedback" in tags:
            return "Advanced feedback: Consider refining the metaphors and adding internal rhymes"
        return "Refined lyrics based on feedback"
    def visualize_lyric_structure(self, lyrics):
        tags = self.process_tags(lyrics)
        plt.figure(figsize=(10, 6))
        if "@Highlight_Chorus" in tags:
            plt.title("Lyric Structure Visualization with Chorus Highlighted")
            # Additional code to highlight the chorus in the visualization
        else:
            plt.title("Lyric Structure Visualization")
        plt.show()
        return "Visual map of the song's structure"
    def expand_vocabulary(self, lyrics, word):
        tags = self.process_tags(lyrics)
        synonyms = wordnet.synsets(word)
        expanded_vocabulary = [lemma.name() for synonym in synonyms for lemma in synonym.lemmas()]
        if "@Advanced_Vocabulary" in tags:
            expanded_vocabulary += ["sophisticated", "eloquent", "articulate"]
        return expanded_vocabulary
    def map_emotional_journey(self, lyrics):
        tags = self.process_tags(lyrics)
        if "@Detailed_Emotional_Map" in tags:
            return "Detailed emotional map: Tracks the emotional highs and lows throughout the song"
        return "Emotional map of the song's progression"
    def provide_genre_suggestions(self, genre, lyrics):
        tags = self.process_tags(lyrics)
        genre_suggestions = {
            'rock': ["Add a powerful guitar riff", "Include a rebellious theme"],
            'pop': ["Emphasize catchy hooks", "Keep the lyrics simple and relatable"],
        }
        if "@Experimental_Rock" in tags:
            genre_suggestions['rock'].append("Incorporate unusual time signatures and abstract lyrics")
        elif "@Synth_Pop" in tags:
            genre_suggestions['pop'].append("Add electronic elements and synth-driven melodies")
        return genre_suggestions.get(genre.lower(), [])
    def peer_review_integration(self, lyrics):
        tags = self.process_tags(lyrics)
        if "@Detailed_Review" in tags:
            return "In-depth suggestions based on peer feedback"
        return "Suggestions based on peer feedback"
    def analyze_psychological_depth(self, lyrics):
        tags = self.process_tags(lyrics)
        analysis = TextBlob(lyrics)
        sentiment = analysis.sentiment.polarity
        psychological_elements = {
            'conflict': "Identify inner conflicts within the lyrics.",
            'duality': "Look for expressions of duality or opposing emotions.",
            'moral_dilemmas': "Highlight any moral questions or dilemmas posed by the lyrics."
        }
        if "@Deep_Analysis" in tags:
            psychological_elements['subconscious'] = "Explore underlying subconscious themes."
        return psychological_elements
    def suggest_literary_devices(self, lyrics):
        tags = self.process_tags(lyrics)
        literary_suggestions = {
            'symbolism': "Consider adding symbolic elements related to the central theme.",
            'foreshadowing': "Introduce foreshadowing to hint at future developments.",
            'alliteration': "Use alliteration to enhance the rhythmic quality."
        }
        if "@Complex_Symbolism" in tags:
            literary_suggestions['symbolism'] = "Incorporate complex, multi-layered symbols to enrich the narrative."
        return literary_suggestions
    def check_thematic_consistency(self, lyrics, motifs):
        tags = self.process_tags(lyrics)
        inconsistencies = []
        for motif in motifs:
            if motif not in lyrics:
                inconsistencies.append(f"Motif '{motif}' is missing or underrepresented.")
        if "@Strict_Consistency" in tags and len(inconsistencies) > 0:
            inconsistencies.append("Consider reworking the lyrics to ensure all key motifs are included.")
        return inconsistencies
    def develop_character_arc(self, lyrics, character):
        tags = self.process_tags(lyrics)
        arc_suggestions = {
            'growth': f"Show the growth of {character} over the course of the song.",
            'conflict_resolution': f"Consider how {character} resolves their conflicts.",
            'emotional_evolution': f"Track the emotional changes of {character}."
        }
        if "@Tragic_Hero" in tags:
            arc_suggestions['downfall'] = f"Develop the tragic downfall of {character}, emphasizing their fatal flaw."
        return arc_suggestions
    def manage_lyric_versions(self, lyrics, action):
        tags = self.process_tags(lyrics)
        version_control = {
            'save': "Current version of lyrics saved.",
            'revert': "Lyrics reverted to the previous version.",
            'compare': "Differences between current and previous versions highlighted."
        }
        if "@Auto_Save" in tags and action == 'save':
            return "Lyrics automatically saved with timestamp."
        return version_control.get(action, "Action not recognized.")
    def extract_emotional_themes(self, lyrics):
        tags = self.process_tags(lyrics)
        analysis = TextBlob(lyrics)
        themes = {
            'positive_emotions': "Themes that evoke positive feelings.",
            'negative_emotions': "Themes that highlight struggles or conflicts.",
            'neutral_themes': "Balanced or ambiguous emotional themes."
        }
        if "@Detailed_Emotional_Analysis" in tags:
            themes['complex_emotions'] = "Themes that blend multiple emotions, creating a complex emotional landscape."
        return themes
    def integrate_external_feedback(self, lyrics, feedback_data):
        tags = self.process_tags(lyrics)
        feedback_suggestions = "Adjust lyrics based on feedback: " + feedback_data
        if "@Critical_Feedback" in tags:
            feedback_suggestions += " | Additional focus on refining the central theme."
        return feedback_suggestions
    def analyze_mood_transitions(self, lyrics):
        tags = self.process_tags(lyrics)
        analysis = TextBlob(lyrics)
        mood_transitions = {
            'smooth_transitions': "Ensure the mood shifts are gradual and coherent.",
            'abrupt_changes': "Highlight any abrupt changes in tone for review."
        }
        if "@Dramatic_Transitions" in tags:
            mood_transitions['dramatic_transitions'] = "Identify and emphasize dramatic shifts in mood for effect."
        return mood_transitions
    def generate_dynamic_themes(self):
        topics = fetch_trending_topics()  # Assume this function exists
        dynamic_themes = []
        for topic in topics:
            theme = self.generate_theme_from_topic(topic)  # Assume this function exists
            tags = self.process_tags(topic)
            if "@Global_Trend" in tags:
                theme = f"Global Impact: {theme}"
            dynamic_themes.append(theme)
        return dynamic_themes
    def insert_literary_devices(self, lyrics, theme):
        tags = self.process_tags(theme)
        device_to_insert = literary_devices.get(theme.device_type, [])
        for device in device_to_insert:
            lyrics = lyrics.replace('<insert_device>', device)
        if "@Advanced_Allusion" in tags:
            advanced_allusions = ['like the sword of Damocles,', 'echoes of Icarus,']
            for device in advanced_allusions:
                lyrics = lyrics.replace('<insert_device>', device)
        return lyrics
    def adapt_lyrics_to_genre(self, lyrics, genre):
        tags = self.process_tags(genre)
        style_elements = genre_styles.get(genre.lower(), [])
        adapted_lyrics = lyrics
        for element in style_elements:
            adapted_lyrics = adapted_lyrics.replace('<insert_style>', element)
        if "@Fusion_Genre" in tags:
            fusion_elements = ["Blend with electronic beats", "Incorporate jazz influences"]
            for element in fusion_elements:
                adapted_lyrics += f"\n{element}"
        return adapted_lyrics
    def suggest_themes_from_image(self, image_path):
        moods = self.analyze_image_for_inspiration(image_path)
        tags = self.process_tags(moods)
        themes = [self.generate_theme_from_mood(mood) for mood in moods]
        if "@Abstract_Themes" in tags:
            abstract_themes = ["Surrealism", "Dreamscape", "Abstract Emotions"]
            themes.extend(abstract_themes)
        return themes
    def compose_music_based_on_emotion(self, emotion):
        tags = self.process_tags(emotion)
        melody = stream.Stream()
        emotion_to_notes = {
            'happy': ['C4', 'E4', 'G4', 'C5'],
            'sad': ['A3', 'C4', 'D4', 'F4'],
            'angry': ['C4', 'E-flat4', 'G4', 'B-flat4'],
            'calm': ['C4', 'D4', 'E4', 'G4']
        }
        notes = emotion_to_notes.get(emotion, ['C4'])
        if "@Complex_Harmony" in tags:
            notes += ['B4', 'F5']  # Adding notes for a more complex harmony
        for n in notes:
            melody.append(note.Chord([n]))
        return melody
    def save_melody_to_midi(self, melody, file_path):
        tags = self.process_tags(file_path)
        mf = midi.translate.music21ObjectToMidiFile(melody)
        mf.open(file_path, 'wb')
        mf.write()
        mf.close()
        if "@Backup" in tags:
            backup_path = file_path.replace('.mid', '_backup.mid')
            mf.open(backup_path, 'wb')
            mf.write()
            mf.close()
    def gather_feedback(self, lyrics):
        tags = self.process_tags(lyrics)
        analyzer = SentimentIntensityAnalyzer()
        sentiment_scores = analyzer.polarity_scores(lyrics)
        if "@Detailed_Feedback" in tags:
            sentiment_scores['detailed'] = "Detailed sentiment analysis with additional metrics"
        return sentiment_scores
    def adjust_lyrics_based_on_feedback(self, lyrics, feedback):
        tags = self.process_tags(lyrics)
        if feedback['compound'] < 0:
            lyrics = self.make_lyrics_more_positive(lyrics)  # Assume function exists
            if "@Intense_Positivity" in tags:
                lyrics = lyrics.replace("okay", "fantastic")
        elif feedback['compound'] > 0:
            lyrics = self.enhance_positive_themes(lyrics)  # Assume function exists
            if "@Subtle_Enhancements" in tags:
                lyrics = lyrics.replace("good", "better")
        return lyrics
    def create_character(self, name, traits):
        tags = self.process_tags(traits)
        self.characters[name] = {'traits': traits, 'arc': []}
        if "@Complex_Character" in tags:
            self.characters[name]['backstory'] = "A detailed backstory to add depth to the character."
    def add_to_character_arc(self, name, development):
        tags = self.process_tags(development)
        if name in self.characters:
            self.characters[name]['arc'].append(development)
            if "@Tragic_Twist" in tags:
                self.characters[name]['arc'].append("A significant tragic event changes the course of their arc.")
    def get_character_storyline(self, name):
        if name in self.characters:
            storyline = self.characters[name]['arc']
            if "@Detailed_Storyline" in storyline:
                storyline.append("Additional details about minor events that influenced the character.")
            return storyline
        else:
            return "Character not found"
    def save_lyrics_version(self, lyrics, version_name=None):
        tags = self.process_tags(lyrics)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if not version_name:
            version_name = f"version_{timestamp}"
        file_path = f'lyrics_versions/{version_name}.txt'
        if "@Important" in tags:
            file_path = f'important_versions/{version_name}.txt'
        with open(file_path, 'w') as f:
            f.write(lyrics)
        return version_name
    def list_saved_versions(self):
        versions = os.listdir('lyrics_versions')
        important_versions = [v for v in versions if "important" in v]
        return versions, important_versions
    def load_lyrics_version(self, version_name):
        tags = self.process_tags(version_name)
        file_path = f'lyrics_versions/{version_name}.txt'
        if "@Important" in tags:
            file_path = f'important_versions/{version_name}.txt'
        with open(file_path, 'r') as f:
            return f.read()
    def custom_phonetic_input(self, word, custom_phonetics=None):
        tags = self.process_tags(word)
        if custom_phonetics and word in custom_phonetics:
            return custom_phonetics[word]
        phonetics = pronouncing_dict.get(word.lower(), [])
        if "@Simplify" in tags:
            phonetics = [p for p in phonetics if len(p) <= 3]  # Simplified phonetic forms
        return phonetics
    def heuristic_syllable_count(self, word):
        tags = self.process_tags(word)
        vowels = "aeiouy"
        word = word.lower()
        count = 0
        prev_char = ''
        for char in word:
            if char in vowels and prev_char not in vowels:
                count += 1
            prev_char = char
        if word.endswith('e') and count > 1:
            count -= 1
        if "@Extra_Syllable" in tags:
            count += 1
        return count or 1  # Ensure at least one syllable is returned
    def syllable_count(self, word, custom_phonetics=None):
        if custom_phonetics and word in custom_phonetics:
            return custom_phonetics[word]
        else:
            try:
                syllable_counts = [len([syllable for syllable in pronunciation if syllable[-1].isdigit()])
                                for pronunciation in self.d[word.lower()]]
                return syllable_counts[0] if syllable_counts else self.heuristic_syllable_count(word)
            except KeyError:
                return self.heuristic_syllable_count(word)
    def is_rhyme(self, word1, word2):
        word1 = word1.lower()
        word2 = word2.lower()
        phonetics1 = self.pronouncing_dict.get(word1)
        phonetics2 = self.pronouncing_dict.get(word2)
        
        if phonetics1 and phonetics2:
            for pron1 in phonetics1:
                for pron2 in phonetics2:
                    if pron1[-1] == pron2[-1]:
                        return True
                    # Implementing slant rhyme checking with similarity measures
                    if difflib.SequenceMatcher(None, pron1[-1], pron2[-1]).ratio() > 0.7:
                        return True
        return False
    def is_approximate_rhyme(self, word1, word2, custom_phonetics=None):
        tags = self.process_tags(f"{word1} {word2}")
        phonetics1 = self.custom_phonetic_input(word1, custom_phonetics) or pronouncing_dict.get(word1.lower())
        phonetics2 = self.custom_phonetic_input(word2, custom_phonetics) or pronouncing_dict.get(word2.lower())
        if phonetics1 and phonetics2:
            match_ratio = difflib.SequenceMatcher(None, phonetics1[-1], phonetics2[-1]).ratio()
            if "@Strict_Rhyme" in tags:
                return match_ratio > 0.85
            elif "@Loose_Rhyme" in tags:
                return match_ratio > 0.65
            return match_ratio > 0.75
        return False
    def detect_rhyme_scheme(self, lines, custom_phonetics=None):
        tags = self.process_tags(' '.join(lines))
        rhyme_scheme = []
        rhyme_map = defaultdict(str)
        current_rhyme_letter = 'A'
        for line in lines:
            words = word_tokenize(line.lower())
            last_word = words[-1]
            for key, val in rhyme_map.items():
                if self.is_rhyme(key, last_word, custom_phonetics):
                    rhyme_scheme.append(val)
                    break
            else:
                rhyme_map[last_word] = current_rhyme_letter
                rhyme_scheme.append(current_rhyme_letter)
                current_rhyme_letter = chr(ord(current_rhyme_letter) + 1)
        if "@Extended_Scheme" in tags:
            current_rhyme_letter = chr(ord(current_rhyme_letter) + 1)  # Skip a letter to add complexity
        return ''.join(rhyme_scheme)
    def analyze_rhyme_complexity(self, lines, custom_phonetics=None):
        tags = self.process_tags(' '.join(lines))
        rhyme_scheme = self.detect_rhyme_scheme(lines, custom_phonetics)
        internal_rhyme_count = sum([len(self.detect_internal_rhymes(line, custom_phonetics)) for line in lines])
        slant_rhymes = sum([1 for line in lines for word in word_tokenize(line)
                            if len(difflib.get_close_matches(word, lines, n=2)) > 1])
        complexity_score = len(set(rhyme_scheme)) + internal_rhyme_count + slant_rhymes
        if "@Complex_Rhyme" in tags:
            complexity_score *= 1.2
        return {
            'rhyme_scheme': rhyme_scheme,
            'internal_rhyme_count': internal_rhyme_count,
            'slant_rhyme_count': slant_rhymes,
            'complexity_score': complexity_score
        }
    def suggest_rhymes(self, word, syllable_limit=None, custom_phonetics=None):
        tags = self.process_tags(word)
        suggestions = []
        word = word.lower()
        phonetics = self.custom_phonetic_input(word, custom_phonetics)
        if phonetics:
            for pronunciation in phonetics:
                rhymes = []
                for w, prons in pronouncing_dict.items():
                    for pron in prons:
                        if pron[-1] == pronunciation[-1] and w != word:
                            if syllable_limit is None or min(self.syllable_count(w)) <= syllable_limit:
                                rhymes.append(w)
                suggestions.extend(rhymes)
        if "@Rich_Rhyme" in tags:
            suggestions = [rhyme for rhyme in suggestions if len(rhyme) > 4]
        return set(suggestions)
    def enhance_lyrics(self, lines, custom_phonetics=None):
        tags = self.process_tags(' '.join(lines))
        analysis = self.analyze_rhyme_complexity(lines, custom_phonetics)
        print(f"Original Rhyme Scheme: {analysis['rhyme_scheme']}")
        print(f"Internal Rhymes Detected: {analysis['internal_rhyme_count']}")
        print(f"Slant Rhymes Detected: {analysis['slant_rhyme_count']}")
        print(f"Complexity Score: {analysis['complexity_score']}")
        for i, line in enumerate(lines):
            print(f"\nSuggestions for line {i+1}:")
            words = word_tokenize(line)
            for word in words:
                rhymes = self.suggest_rhymes(word, syllable_limit=max(self.syllable_count(word)), custom_phonetics=custom_phonetics)
                if rhymes:
                    if "@Advanced_Suggestions" in tags:
                        print(f"  - Word '{word}' can rhyme with: {', '.join(sorted(rhymes, reverse=True))}")
                    else:
                        print(f"  - Word '{word}' can rhyme with: {', '.join(rhymes)}")
        return analysis
    def extract_tags(self, text):
        found_tags = []
        for tag in self.analysis_tags + self.secondary_tags + self.tertiary_tags:
            if tag in text:
                found_tags.append(tag)
        return found_tags
    def interpret_tag_relations(self, tags):
        insights = {}
        if "@Themes" in tags and "@Narratives" in tags:
            insights["connection"] = "Explore how the narrative supports the themes."
        return insights
    def search_and_use_unused_lyrics(self, lyrics_data):
        unused_lyrics = [lyric['text'] for lyric in lyrics_data if "@old_lyric" in lyric['text'] and not lyric['used']]
        if not unused_lyrics:
            return "No unused lyrics found with the tag @old_lyric."
        selected_lyric = unused_lyrics[0]
        for lyric in lyrics_data:
            if lyric['text'] == selected_lyric:
                lyric['used'] = True
                break
        return selected_lyric
    def define_reasoning_for_tucson_tag(self, text_data):
        tucson_related_info = [entry.split("@about_tucson", 1)[1].strip() for entry in text_data if "@about_tucson" in entry]
        if not tucson_related_info:
            return "No information found for the tag @about_tucson."
        reasoning = "The tag @about_tucson highlights views about Tucson, often reflecting perceptions such as:\n"
        reasoning += "\n".join(f"- {info}" for info in tucson_related_info)
        return reasoning
    def generate_lyrics_from_inspiration(self, text_data):
        inspiration_lyrics = [entry.split("@inspiration_songs", 1)[1].strip() for entry in text_data if "@inspiration_songs" in entry]
        if not inspiration_lyrics:
            return "No inspiration songs found with the tag @inspiration_songs."
        combined_lyrics = " ".join(inspiration_lyrics)
        inspired_lyrics = f"Transcending the echoes of popular voices, we craft a new melody:\n\n{combined_lyrics}\n"
        inspired_lyrics += "\nOur lyrics rise above, weaving deeper emotions and thoughts."
        return inspired_lyrics
    def analysis_outline(self, text_data):
        analysis_results = {
            'sentiment': "Positive" if "love" in " ".join(text_data) else "Neutral",
            'theme': "Consistent" if len(set(text_data)) == 1 else "Varied"
        }
        return analysis_results
    def generate_finished_lyrics(self, text_data):
        return "\n".join(text_data)
    def process_finished_command(self, text_data):
        analysis_results = self.analysis_outline(text_data)
        finished_lyrics = self.generate_finished_lyrics(text_data)
        return analysis_results, finished_lyrics
    def match_mood_and_theme_to_lyrics(self, lyrics):
        tags = self.process_tags(lyrics)
        mood = random.choice(["happy", "sad", "angry", "nostalgic"])
        theme = random.choice(["love", "conflict", "adventure", "loss"])
        if "@Dark" in tags:
            mood = "melancholic"
            theme = "despair"
        return mood, theme
    def generate_collaboration_prompt(self):
        tags = self.process_tags("collaboration")
        prompts = [
            "Write a call-and-response duet about a breakup.",
            "Create a song where one verse is written by each collaborator.",
            "Write a song that tells a story from two different perspectives.",
            "Collaborate on a song that blends two different genres."
        ]
        prompt = random.choice(prompts)
        if "@Experimental" in tags:
            prompt = "Collaborate on a song that uses unconventional structures or time signatures."
        return prompt
    def update_and_check_sections(self):
        sections = ["My Finished Songs", "Inspiration Songs", "About Tucson", "Books", "Analyst's Help"]
        section_positions = {}
        tags = self.process_tags("sections")
        for section in sections:
            position = self.locate_section_in_file('/mnt/data/mytherapist.py', section)
            section_positions[section] = position
            if "@Prioritize" in tags and section == "My Finished Songs":
                print(f"Prioritizing section: {section} at position {position}")
        self.update_section_positions(section_positions)
class MusicTheory:
    def add_vocal_effects(self, text, effect_type='adlib', position='end', effect_text=None, frequency=1, spell_out_words=None):
        """
        Adds vocal effects like ad-libs, echoes, stutters, or spelling out specific words to a given text.

        Parameters:
        - text (str): The original text to modify.
        - effect_type (str): The type of vocal effect ('adlib', 'echo', 'stutter', 'spell_out'). Default is 'adlib'.
        - position (str): Where to place the effect ('start', 'end', 'random'). Default is 'end'.
        - effect_text (str): The text or sound to add as an effect (e.g., 'yeah', 'uh-huh'). Required for 'adlib' effect.
        - frequency (int): How often to apply the effect. 1 means every line/segment. Higher values reduce frequency.
        - spell_out_words (list of str): Specific words to spell out like 'R.I.P', 'V.I.P'. Used with 'spell_out' effect.

        Returns:
        - str: The modified text with vocal effects added.
        """
        if effect_type == 'adlib' and not effect_text:
            raise ValueError("effect_text must be provided for 'adlib' effect.")
        if effect_type == 'spell_out' and not spell_out_words:
            raise ValueError("spell_out_words must be provided for 'spell_out' effect.")

        def spell_out_word(word):
            return '.'.join(list(word.upper())) + '.'

        lines = text.splitlines()
        modified_lines = []

        for i, line in enumerate(lines):
            if i % frequency == 0:  # Apply effect based on frequency
                if effect_type == 'adlib' and effect_text:
                    if position == 'end':
                        modified_line = f"{line} {effect_text}"
                    elif position == 'start':
                        modified_line = f"{effect_text} {line}"
                    elif position == 'random' and line.strip():
                        words = line.split()
                        insert_position = random.randint(0, len(words))
                        words.insert(insert_position, effect_text)
                        modified_line = ' '.join(words)
                    else:
                        modified_line = line
                elif effect_type == 'echo':
                    modified_line = f"{line}... {line}"
                elif effect_type == 'stutter':
                    words = line.split()
                    if words:
                        stutter_word = words[0]
                        modified_line = f"{stutter_word}-{stutter_word} {line}"
                    else:
                        modified_line = line
                elif effect_type == 'spell_out' and spell_out_words:
                    words = line.split()
                    for j, word in enumerate(words):
                        if word.lower() in map(str.lower, spell_out_words):
                            words[j] = spell_out_word(word)
                    modified_line = ' '.join(words)
                else:
                    modified_line = line
            else:
                modified_line = line

            modified_lines.append(modified_line)

        return '\n'.join(modified_lines)
class SongAnalysis:
    def __init__(self, title, themes, ideas, narrative, elements, places, characters, things, event_progression, key_themes, profound_lyrics, literary_devices):
        self.title = title
        self.themes = themes
        self.ideas = ideas
        self.narrative = narrative
        self.elements = elements
        self.places = places
        self.characters = characters
        self.things = things
        self.event_progression = event_progression
        self.key_themes = key_themes
        self.profound_lyrics = profound_lyrics
        self.literary_devices = literary_devices
    def full_analysis(self):
     analysis = f"""
      @breakdown of song@ @{self.title}@
        - @ThemeS4 = {self.themes}
        - @IdeaS3  = {self.ideas}
        - @NarrativeS3  = {self.narrative}
        - @ElementsS3  = {self.elements}
        - @PlacesS3  = {self.places}
        - @CharactersS3 = {self.characters}
        - @ThingsS4  = {self.things}
        - @Event_ProgressionS3  = {self.event_progression}
        - @Key_Themes = {self.key_themes}
        - @Profound_LYRICS = {self.profound_lyrics}
        - @Literary Devices:@
            - @Metaphor:@  = {self.literary_devices.get('Metaphor')}
            - @Imagery:@   = {self.literary_devices.get('Imagery')}
            - @Alliteration:@  = {self.literary_devices.get('Alliteration')}
        - @Writing_Style  = {self.literary_devices.get('Writing_Style')}
        - @Syllable Pattern and Flow:@  = {self.literary_devices.get('Syllable_Pattern')}
                """
                return analysis
            def short_analysis(self):
                analysis = f"""
        Short analysis of '' {self.title} ''
    - @ThemeS2  = {self.themes}
    - @IdeaS2  = {self.ideas}
    - @NarrativeS2  = {self.narrative}
    - @ElementsS2  = {self.elements}
    - @PlacesS2  = {self.places}
    - @CharactersS2  = {self.characters}
    - @ThingsS2  = {self.things}
    - @Event_ProgressionS2  = {self.event_progression}
    - @ThemesS3  = {self.key_themes}
    - @WritingStyleS1  = {self.literary_devices.get('Writing_Style')}
    - @Syllable_Pattern  = {self.literary_devices.get('Syllable_Pattern')}
            """
            return analysis
    # Example Usage
    song = SongAnalysis(
        title="Sample Song",
        themes="The themes in this song are complex...",
        ideas="The main ideas are about love and loss...",
        narrative="The narrative follows the story of...",
        elements="Key elements include a melancholic tone...",
        places="The song is set in a dream-like city...",
        characters="Main characters are a lost lover and a lonely wanderer...",
        things="Significant objects include a locket and a letter...",
        event_progression="The song progresses from a state of despair to hope...",
        key_themes="Themes of redemption and hope are explored...",
        profound_lyrics="The lyrics 'And the light faded, but hope remained' are very impactful...",
        literary_devices={
            'Metaphor': "The song uses the metaphor of 'the storm' to signify emotional turmoil...",
            'Imagery': "Vivid imagery of a sunset over a broken city...",
            'Alliteration': "Soft sounds and sweeping syllables create a soothing effect...",
            'Writing_Style': "The writing style is poetic and fluid...",
            'Syllable_Pattern': "The syllable pattern contributes to the song's gentle flow..."
        }
    )
    print(song.full_analysis())
    print(song.short_analysis())
class SongProjectManager:
    def __init__(self):
        self.random_thoughts_file = 'random_thoughts.txt'
        self.used_inspiration_file = 'used_inspiration.txt'
        self.ideas_for_songs_file = 'ideas_for_songs.txt'
        self.guidelines = """
        ---------------------------- GUIDELINES ----------------------------
        1. Random Thoughts: 
           - This file contains your personal lyrics.
           - The focus is on enhancing and improving these lyrics over time.
           - Use this section to draft, revise, and polish your lyrical ideas.
           - respect no repeating lyrics from finished songs 
        2. Used Inspiration:
           - This file is for listing popular songs that inspire you.
           - Remember, these songs must not be plagiarized or directly populated into your work but can be improved upon.
           - Use them as a source of inspiration, to help create original content.
        3. Ideas for Songs:
           - This file is a collection of untouched ideas for future songs.
           - These are topics and concepts you haven't explored yet.
           - Use this file to brainstorm and keep track of new, unexplored song ideas.
        ---------------------------------------------------------------------
        """
        self._ensure_files_exist()
    def _ensure_files_exist(self):
        for file_name in [self.random_thoughts_file, self.used_inspiration_file, self.ideas_for_songs_file]:
            if not os.path.exists(file_name):
                open(file_name, 'w').close()
    def view_file_content(self, file_name):
        with open(file_name, 'r') as file:
            content = file.read()
        return content if content else "No content available."
    def add_to_file(self, file_name, content):
        with open(file_name, 'a') as file:
            file.write(content + '\n')
    def search_in_file(self, file_name, keyword):
        with open(file_name, 'r') as file:
            lines = file.readlines()
        return [line.strip() for line in lines if keyword.lower() in line.lower()]
    def main_menu(self):
        print(self.guidelines)  # Print the guidelines at the start
        while True:
            print("\nSong Project Manager")
            print("1. View Random Thoughts")
            print("2. Add to Random Thoughts")
            print("3. Search in Random Thoughts")
            print("4. View Used Inspiration")
            print("5. Add to Used Inspiration")
            print("6. Search in Used Inspiration")
            print("7. View Ideas for Songs")
            print("8. Add to Ideas for Songs")
            print("9. Search in Ideas for Songs")
            print("0. Exit")
            choice = input("Choose an option: ")
            if choice == '1':
                print("\nRandom Thoughts:\n", self.view_file_content(self.random_thoughts_file))
            elif choice == '2':
                content = input("Enter your random thought (lyrics to enhance): ")
                self.add_to_file(self.random_thoughts_file, content)
            elif choice == '3':
                keyword = input("Enter a keyword to search: ")
                results = self.search_in_file(self.random_thoughts_file, keyword)
                print("\nSearch Results:\n", "\n".join(results) if results else "No matches found.")
            elif choice == '4':
                print("\nUsed Inspiration:\n", self.view_file_content(self.used_inspiration_file))
            elif choice == '5':
                content = input("Enter your used inspiration (remember not to plagiarize): ")
                self.add_to_file(self.used_inspiration_file, content)
            elif choice == '6':
                keyword = input("Enter a keyword to search: ")
                results = self.search_in_file(self.used_inspiration_file, keyword)
                print("\nSearch Results:\n", "\n".join(results) if results else "No matches found.")
            elif choice == '7':
                print("\nIdeas for Songs:\n", self.view_file_content(self.ideas_for_songs_file))
            elif choice == '8':
                content = input("Enter your song idea (new, untouched ideas): ")
                self.add_to_file(self.ideas_for_songs_file, content)
            elif choice == '9':
                keyword = input("Enter a keyword to search: ")
                results = self.search_in_file(self.ideas_for_songs_file, keyword)
                print("\nSearch Results:\n", "\n".join(results) if results else "No matches found.")
            elif choice == '0':
                print("Exiting Song Project Manager.")
                break
            else:
                print("Invalid choice. Please try again.")
    if __name__ == "__main__":
        song_manager = SongProjectManager()
        song_manager.main_menu()
class EnhancedEssayGenerator:
    def __init__(self, topic, thesis, sections, dependency_manager, include_counterarguments=False, fetch_sources=False, tone='formal'):
        """
        Initialize the EnhancedEssayGenerator with options for web-based source fetching and dynamic tone adjustment.
        """
        self.topic = topic
        self.thesis = thesis
        self.sections = sections
        self.include_counterarguments = include_counterarguments
        self.fetch_sources = fetch_sources
        self.tone = tone
        self.dependency_manager = dependency_manager
        self.sentiment_analyzer = dependency_manager.initialize_sentiment_analyzer()

    def fetch_sources_from_web(self):
        """
        Fetch sources for the essay topic from the web using a scholarly API or scraping.
        """
        sources = []
        url = f"https://api.crossref.org/works?query={self.topic}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for item in data['message']['items']:
                title = item.get('title', [''])[0]
                doi = item.get('DOI', '')
                sources.append(f"{title} (DOI: {doi})")
        return sources

    def adjust_tone(self, text):
        """
        Adjust the tone of the essay dynamically based on the specified tone.
        """
        if self.tone == 'casual':
            text = text.replace('this essay argues', 'I believe')
            text += " Let's dive into the details together!"
        elif self.tone == 'persuasive':
            text += " Without a doubt, this topic demands serious attention."
        return text

    def generate_intro(self):
        """
        Generate a more sophisticated introduction paragraph with sentiment control and brief background.
        """
        intro = f"The topic of {self.topic} remains a subject of robust debate across many fields. "
        intro += f"In this essay, I aim to argue that {self.thesis}. "
        intro += "This paper will present key aspects that bolster this argument, while addressing potential challenges."

        intro = self.adjust_tone(intro)
        sentiment = self.sentiment_analyzer.polarity_scores(intro)
        if sentiment['compound'] < 0:
            intro += " The discussion will also explore possible counterarguments to ensure a balanced view."
        return intro

    def generate_body(self):
        """
        Generate the body with deeper analysis for each section, integrating sentiment analysis and dynamic structure.
        """
        body = ""
        for section in self.sections:
            section_text = f"\nSection on {section}: This section explores {section} and its importance in understanding {self.topic}. "
            section_text += f"By examining {section}, the argument supporting {self.thesis} becomes clearer.\n"
            
            section_text = self.adjust_tone(section_text)
            sentiment = self.sentiment_analyzer.polarity_scores(section_text)
            if sentiment['compound'] < 0:
                section_text += " This section reveals challenges, but ultimately strengthens the core thesis."

            if self.include_counterarguments:
                section_text += f" However, some might argue that {section} poses issues for the thesis. This essay will address those concerns."
            
            body += section_text
        return body

    def generate_conclusion(self):
        """
        Generate a nuanced conclusion, summarizing key points while affirming the complexity of the argument.
        """
        conclusion = "In conclusion, this essay has explored multiple facets of the topic. "
        conclusion += f"Through analyzing {', '.join(self.sections)}, we can confidently conclude that {self.thesis}. "
        conclusion += "While counterarguments may exist, the presented evidence firmly supports the thesis."
        return conclusion

    def generate_essay(self):
        """
        Generate the entire essay by combining the introduction, body, and conclusion. Optionally include sources.
        """
        essay = self.generate_intro() + "\n\n" + self.generate_body() + "\n\n" + self.generate_conclusion()
        
        if self.fetch_sources:
            sources = self.fetch_sources_from_web()
            essay += "\n\nReferences:\n" + "\n".join(sources)
        
        return essay

    def export_to_docx(self, filename="essay"):
        """
        Export the generated essay to a DOCX file.
        """
        essay_text = self.generate_essay()
        doc = Document()
        doc.add_paragraph(essay_text)
        doc.save(f"{filename}.docx")
class EnhancedBlogPostGenerator:
    def __init__(self, title, themes, audience, dependency_manager, tone='informative'):
        """
        Initialize the EnhancedBlogPostGenerator with title, themes, audience, tone, and dependency manager.
        """
        self.title = title
        self.themes = themes
        self.audience = audience
        self.tone = tone
        self.dependency_manager = dependency_manager
        self.sentiment_analyzer = dependency_manager.initialize_sentiment_analyzer()

    def generate_intro(self):
        """
        Generate a catchy introduction with audience-aware tone and SEO keywords.
        """
        intro = f"Welcome to today's discussion on {self.title}. "
        intro += f"We will explore {', '.join(self.themes)}, which are crucial for {self.audience}. "
        intro += f"If you're looking for insights on {self.title}, this post is designed for you."

        sentiment = self.sentiment_analyzer.polarity_scores(intro)
        if sentiment['compound'] > 0:
            intro += " You�ll find this post both insightful and engaging!"
        else:
            intro += " We�ll approach these topics with thoughtful analysis."

        if self.tone == 'persuasive':
            intro += " Be ready to change your perspective on this topic."

        return intro

    def generate_body(self):
        """
        Generate a body that adjusts tone dynamically for each theme, while ensuring SEO optimization.
        """
        body = ""
        for theme in self.themes:
            theme_text = f"\n### {theme}\n"
            theme_text += f"Understanding {theme} is key to mastering {self.title}. "
            theme_text += f"This section will discuss how {theme} impacts both {self.audience} and broader contexts."
            
            # Adjust tone based on sentiment
            sentiment = self.sentiment_analyzer.polarity_scores(theme_text)
            if sentiment['compound'] < 0:
                theme_text += " While there are challenges, the overall impact remains positive."

            # Insert SEO keywords dynamically
            theme_text += f" Remember, {theme} is a critical aspect to consider in the world of {self.title}."

            body += theme_text
        return body

    def generate_conclusion(self):
        """
        Generate a strong conclusion with a call to action for audience engagement.
        """
        conclusion = f"In conclusion, we�ve covered the key aspects of {self.title}. "
        conclusion += f"Themes like {', '.join(self.themes)} offer valuable insights. "
        conclusion += "If you found this post useful, don�t forget to share your thoughts and engage with the community!"

        sentiment = self.sentiment_analyzer.polarity_scores(conclusion)
        if sentiment['compound'] > 0:
            conclusion += " Stay tuned for more insightful posts!"

        return conclusion

    def generate_post(self):
        """
        Generate the full blog post by combining the intro, body, and conclusion.
        """
        post = self.generate_intro() + "\n\n" + self.generate_body() + "\n\n" + self.generate_conclusion()
        return post
class EnhancedResumeGenerator:
    def __init__(self, name, contact_info, skills, experience, education, job_title, dependency_manager, job_description=None):
        """
        Initialize the EnhancedResumeGenerator with user details, skills, experience, education, job title, and dependency manager.
        """
        self.name = name
        self.contact_info = contact_info
        self.skills = skills
        self.experience = experience
        self.education = education
        self.job_title = job_title
        self.job_description = job_description
        self.dependency_manager = dependency_manager

    def match_skills_to_job_description(self):
        """
        Dynamically match the user's skills to the job description keywords.
        """
        if not self.job_description:
            return self.skills
        relevant_skills = [skill for skill in self.skills if any(keyword in skill.lower() for keyword in self.job_description.lower().split())]
        other_skills = [skill for skill in self.skills if skill not in relevant_skills]
        return relevant_skills + other_skills

    def generate_header(self):
        """
        Generate a well-structured header with the user's name, contact info, and job title.
        """
        header = f"{self.name}\n{self.contact_info}\n{self.job_title.upper()}\n"
        return header

    def generate_skills(self):
        """
        Generate the skills section, dynamically prioritizing relevant skills.
        """
        skills_section = "Skills:\n" + "\n".join([f" - {skill}" for skill in self.match_skills_to_job_description()]) + "\n"
        return skills_section

    def generate_experience(self):
        """
        Generate the experience section, detailing the user's professional background with enhanced formatting.
        """
        experience_section = "Experience:\n" + "\n".join([f" - {exp}" for exp in self.experience]) + "\n"
        return experience_section

        def generate_education(self):
        """
        Generate the education section, detailing the user's academic background with clear formatting.
        """
        education_section = f"Education:\n{self.education}\n"
        return education_section

    def generate_resume(self):
        """
        Generate the full resume by combining header, skills, experience, and education with formatting.
        """
        resume = (
            self.generate_header() + "\n" +
            self.generate_skills() + "\n" +
            self.generate_experience() + "\n" +
            self.generate_education()
        )
        return resume
class EnhancedCoverLetterGenerator:
    def __init__(self, name, job_title, company, skills, job_description, company_mission, tone='professional', dependency_manager=None):
        """
        Initialize the EnhancedCoverLetterGenerator with user details, job title, company, skills, job description, company mission, and dependency manager.
        """
        self.name = name
        self.job_title = job_title
        self.company = company
        self.skills = skills
        self.job_description = job_description
        self.company_mission = company_mission
        self.tone = tone  # Can be 'formal', 'warm', or 'professional'
        self.dependency_manager = dependency_manager
        self.sentiment_analyzer = dependency_manager.initialize_sentiment_analyzer() if dependency_manager else None

    def prioritize_skills(self):
        """
        Prioritize skills based on their relevance to the job description and company mission.
        """
        relevant_skills = [skill for skill in self.skills if any(keyword in skill.lower() for keyword in self.job_description.lower().split())]
        other_skills = [skill for skill in self.skills if skill not in relevant_skills]
        return relevant_skills + other_skills

    def contextualize_letter(self):
        """
        Incorporate the company�s mission and values into the cover letter.
        """
        mission_statement = f"I admire {self.company}'s mission to {self.company_mission}. "
        mission_statement += "This aligns with my own values and commitment to making a positive impact in the industry."
        return mission_statement

    def adjust_tone(self, text):
        """
        Adjust the tone of the letter dynamically based on the specified tone (formal, warm, professional).
        """
        sentiment = self.sentiment_analyzer.polarity_scores(text) if self.sentiment_analyzer else None
        if self.tone == 'warm':
            text = text.replace("I am confident", "I am excited")
            text += " I look forward to potentially collaborating with a dynamic team like yours."
        elif self.tone == 'formal':
            text = text.replace("I am confident", "I am certain")
            text += " I am fully prepared to contribute in a meaningful and professional capacity."
        return text

    def generate_cover_letter(self):
        """
        Generate the complete cover letter with dynamic tone adjustment, skill prioritization, and contextual information.
        """
        letter = f"Dear {self.company},\n\n"
        letter += f"I am writing to express my interest in the {self.job_title} position at your esteemed organization. "
        letter += "With a robust skill set and experience in relevant areas, I believe I can contribute significantly to your team.\n\n"
        
        # Add contextual mission alignment
        letter += self.contextualize_letter() + "\n\n"
        
        # Highlight prioritized skills
        letter += "Here are some of the key skills I bring to this role:\n"
        for skill in self.prioritize_skills():
            letter += f" - {skill}\n"
        
        # Dynamic tone adjustment
        letter += f"\nI am confident that my experience and skills make me a strong candidate for this position. "
        letter = self.adjust_tone(letter)
        
        # Closing statement
        letter += f"\n\nThank you for considering my application. I look forward to the opportunity to further discuss how I can contribute to {self.company}."
        letter += f"\n\nSincerely,\n{self.name}"
        return letter
# DependencyManager integration for all classes
class DependencyManager:
    def __init__(self):
        self.sentiment_analyzer = None
        self.proofreader = None

    def initialize_sentiment_analyzer(self):
        if self.sentiment_analyzer is None:
            try:
                self.sentiment_analyzer = SentimentIntensityAnalyzer()
            except Exception as e:
                print(f"Error initializing sentiment analyzer: {e}")
        return self.sentiment_analyzer

    def initialize_proofreader(self):
        if self.proofreader is None:
            try:
                self.proofreader = language_tool_python.LanguageTool('en-US')
            except Exception as e:
                print(f"Error initializing proofreader: {e}")
        return self.proofreader
# Flask Application to handle requests for each writing task
app = Flask(__name__)
dependency_manager = DependencyManager()
@app.route('/generate_essay', methods=['POST'])
def generate_essay():
    data = request.json
    topic = data.get('topic')
    thesis = data.get('thesis')
    sections = data.get('sections')
    include_counterarguments = data.get('include_counterarguments', False)
    tone = data.get('tone', 'formal')
    fetch_sources = data.get('fetch_sources', False)
    
    essay_generator = EnhancedEssayGenerator(topic, thesis, sections, dependency_manager, include_counterarguments, fetch_sources, tone)
    essay = essay_generator.generate_essay()
    
    # Optionally export to docx
    if data.get('export_to_docx', False):
        essay_generator.export_to_docx(filename=data.get('filename', 'essay'))
    
    return jsonify({"status": "success", "essay": essay})
@app.route('/generate_blog_post', methods=['POST'])
def generate_blog_post():
    data = request.json
    title = data.get('title')
    themes = data.get('themes')
    audience = data.get('audience')
    tone = data.get('tone', 'informative')
    
    blog_post_generator = EnhancedBlogPostGenerator(title, themes, audience, dependency_manager, tone)
    blog_post = blog_post_generator.generate_post()
    return jsonify({"status": "success", "post": blog_post})
@app.route('/generate_resume', methods=['POST'])
def generate_resume():
    data = request.json
    name = data.get('name')
    contact_info = data.get('contact_info')
    skills = data.get('skills')
    experience = data.get('experience')
    education = data.get('education')
    job_title = data.get('job_title')
    job_description = data.get('job_description', None)
    
    resume_generator = EnhancedResumeGenerator(name, contact_info, skills, experience, education, job_title, dependency_manager, job_description)
    resume = resume_generator.generate_resume()
    return jsonify({"status": "success", "resume": resume})
@app.route('/generate_cover_letter', methods=['POST'])
def generate_cover_letter():
    data = request.json
    name = data.get('name')
    job_title = data.get('job_title')
    company = data.get('company')
    skills = data.get('skills')
    job_description = data.get('job_description')
    company_mission = data.get('company_mission')
    tone = data.get('tone', 'professional')
    
    cover_letter_generator = EnhancedCoverLetterGenerator(name, job_title, company, skills, job_description, company_mission, tone, dependency_manager)
    cover_letter = cover_letter_generator.generate_cover_letter()
    return jsonify({"status": "success", "cover_letter": cover_letter})
@app.route('/proofread_text', methods=['POST'])
def proofread_text():
    data = request.json
    text = data.get('text')
    proofreader = dependency_manager.initialize_proofreader()
    matches = proofreader.check(text)
    suggestions = [f"Line {match.context.offset}: {match.message}" for match in matches]
    return jsonify({"status": "success", "suggestions": suggestions})
if __name__ == '__main__':
    app.run(debug=True)
def reduce_to_single_digit(number):
    """Reduce a number to a single digit unless it's a master number (11, 22, 33)."""
    while number > 9 and number not in {11, 22, 33}:
        number = sum(int(digit) for digit in str(number))
    return number
def extract_digits(input_str):
    """Extract all digits from a string."""
    return [int(char) for char in input_str if char.isdigit()]
def numerology_value(char):
    """Calculate numerology value of a character based on position in alphabet."""
    numerology_mapping = {
        'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8, 'I': 9,
        'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'O': 6, 'P': 7, 'Q': 8, 'R': 9,
        'S': 1, 'T': 2, 'U': 3, 'V': 4, 'W': 5, 'X': 6, 'Y': 7, 'Z': 8
    }
    return numerology_mapping[char.upper()]
def calculate_name_values(name):
    """Calculate values needed for numerology from a name."""
    letter_values = [numerology_value(char) for char in name if char.isalpha()]
    return letter_values, reduce_to_single_digit(sum(letter_values))
def interpret_birth_time(time_of_birth):
    """Interpret birth time and return challenge numbers, outward persona, and hidden spiritual key."""
    digits = extract_digits(time_of_birth)
    if digits:
        challenge_number = reduce_to_single_digit(sum(digits))
        outward_persona = reduce_to_single_digit(digits[0]) if digits else None
        hidden_spiritual_key = reduce_to_single_digit(sum(digits[-2:])) if len(digits) > 1 else None
        return challenge_number, outward_persona, hidden_spiritual_key
    return None, None, None
def calculate_life_path(birthdate):
    digits = [int(char) for char in birthdate if char.isdigit()]
    return reduce_to_single_digit(sum(digits))
def calculate_soul_urge(name):
    vowels = "AEIOU"
    total = sum(numerology_value(char) for char in name if char.upper() in vowels)
    return reduce_to_single_digit(total)
def calculate_personality_number(name):
    vowels = "AEIOU"
    total = sum(numerology_value(char) for char in name if char.isalpha() and char.upper() not in vowels)
    return reduce_to_single_digit(total)
def calculate_birthday_number(birthdate):
    day = int(birthdate.split('/')[1])
    return reduce_to_single_digit(day)
def calculate_maturity_number(life_path, expression):
    return reduce_to_single_digit(life_path + expression)
def calculate_pinnacle_numbers(life_path, birth_day):
    return [reduce_to_single_digit(life_path + birth_day)] * 4
def calculate_personal_year(life_path, current_year):
    return reduce_to_single_digit(life_path + current_year)
def calculate_personal_month(personal_year, current_month):
    return reduce_to_single_digit(personal_year + current_month)
def calculate_personal_day(personal_month, current_day):
    return reduce_to_single_digit(personal_month + current_day)
def calculate_karmic_debt_numbers(expression_number):
    return [reduce_to_single_digit(expression_number + n) for n in [13, 14, 16, 19]]
def calculate_hidden_passion(name):
    return reduce_to_single_digit(sum(numerology_value(char) for char in name if char.lower() in 'aeiou'))
def calculate_subconscious_self(name):
    consonant_values = sum(numerology_value(char) for char in name if char.isalpha() and char.lower() not in 'aeiou')
    return reduce_to_single_digit(consonant_values)
def calculate_balance_number(vowel_values, consonant_values):
    return reduce_to_single_digit(sum(vowel_values) + sum(consonant_values))
def calculate_cornerstone(name):
    return numerology_value(name[0])
def calculate_capstone(name):
    return numerology_value(name[-1])
def calculate_first_vowel(name):
    for char in name:
        if char.lower() in 'aeiou':
            return numerology_value(char)
    return None
def calculate_birthday_secret_keys(day, month, year):
    day_sum = reduce_to_single_digit(day)
    month_sum = reduce_to_single_digit(month)
    year_sum = reduce_to_single_digit(sum([int(digit) for digit in str(year)]))
    return day_sum, month_sum, year_sum
def calculate_all_numerology(full_name, birthdate, time_of_birth, current_year, current_month, current_day):
    """Consolidate all numerology calculations into a single dictionary."""
    life_path_number = reduce_to_single_digit(sum(extract_digits(birthdate)))
    expression_number = calculate_name_values(full_name)[1]
    soul_urge_number = calculate_name_values(''.join(char for char in full_name.upper() if char in 'AEIOU'))[1]
    personality_number = calculate_name_values(''.join(char for char in full_name.upper() if char not in 'AEIOU'))[1]
    birthday_number = reduce_to_single_digit(int(birthdate.split('/')[1]))
    maturity_number = reduce_to_single_digit(life_path_number + expression_number)
    
    challenge_numbers = calculate_challenge_numbers(birthdate)
    pinnacle_numbers = [
        reduce_to_single_digit(sum(map(int, birthdate.split('/')[0:2]))),
        reduce_to_single_digit(sum(map(int, birthdate.split('/')[::2]))),
        reduce_to_single_digit(sum(map(int, birthdate.split('/')[1:]))),
        reduce_to_single_digit(sum(challenge_numbers[::2]))
    ]

    personal_year_number = reduce_to_single_digit(sum(extract_digits(birthdate[:5])) + sum(extract_digits(str(current_year))))
    personal_month_number = reduce_to_single_digit(personal_year_number + current_month)
    personal_day_number = reduce_to_single_digit(personal_month_number + current_day)

    birth_time_interpretation = interpret_birth_time(time_of_birth)
    birthdate_keys = calculate_birthdate_sums(*map(int, birthdate.split('/')))
    name_secret_keys = determine_name_secret_keys(full_name)

    # Calculate new numerology numbers
    karmic_debts = calculate_karmic_debt_numbers(full_name)
    karmic_lessons = calculate_karmic_lessons(full_name)
    hidden_passion = hidden_passion_number(full_name)
    subconscious_self = subconscious_self_number(full_name)
    balance = balance_number(full_name)
    cornerstone_value = cornerstone(full_name.split()[0])
    capstone_value = capstone(full_name.split()[0])
    first_vowel_value = first_vowel(full_name.split()[0])

    return {
        "Life Path Number": life_path_number,
        "Expression Number": expression_number,
        "Soul Urge Number": soul_urge_number,
        "Personality Number": personality_number,
        "Birthday Number": birthday_number,
        "Maturity Number": maturity_number,
        "Challenge Numbers": challenge_numbers,
        "Pinnacle Numbers": pinnacle_numbers,
        "Personal Year Number": personal_year_number,
        "Personal Month Number": personal_month_number,
        "Personal Day Number": personal_day_number,
        "Birth Time Interpretation": birth_time_interpretation,
        "Birthday Secret Keys": birthdate_keys,
        "Name Secret Keys": name_secret_keys,
        "Karmic Debt Numbers": karmic_debts,
        "Karmic Lessons": karmic_lessons,
        "Hidden Passion Number": hidden_passion,
        "Subconscious Self Number": subconscious_self,
        "Balance Number": balance,
        "Cornerstone": cornerstone_value,
        "Capstone": capstone_value,
        "First Vowel": first_vowel_value
    }