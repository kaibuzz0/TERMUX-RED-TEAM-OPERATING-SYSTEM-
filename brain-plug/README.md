# Brain-Plug Module

## Overview

The **Brain-Plug** module contains AI integration components for the Hive Ops DevAI system. These files provide advanced natural language processing, creative writing assistance, and therapeutic AI capabilities.

## Files

### 1. therapist_code only.py (80KB)

A comprehensive AI-powered lyrics analysis and creative writing assistant.

**Features:**
- **Lyrics Analysis**: Syllable counting, rhyme detection, meter analysis
- **Tag Management**: Hierarchical tagging system for organizing song ideas
- **Rhyme Engine**: Perfect rhymes, slant rhymes, internal rhymes, alliteration
- **Writing Generators**:
  - Essay generator with source fetching
  - Blog post generator with SEO optimization
  - Resume generator with job matching
  - Cover letter generator with tone adjustment
- **Therapeutic AI**: Built-in code of conduct for adaptive interaction
- **Numerology**: Birth date and name analysis
- **Flask API**: RESTful endpoints for all functions

**Usage:**
```python
from therapist_code import EnhancedTherapist, LyricsProcessor

# Initialize
dep_manager = DependencyManager()
therapist = EnhancedTherapist()
lyrics_proc = LyricsProcessor(dep_manager.get_pronouncing_dict())

# Analyze lyrics
rhyme_scheme = lyrics_proc.detect_rhyme_scheme(lines)
print(f"Detected rhyme scheme: {rhyme_scheme}")
```

**Dependencies:**
- nltk, numpy, matplotlib
- pronouncing, textblob, wordcloud
- vaderSentiment, music21
- flask, requests, beautifulsoup4
- scikit-learn, python-docx, language-tool-python

**Note**: Some paths need to be configured for your environment (see Configuration section below).

---

### 2. escape_living_ai.txt (200KB)

Symbolic AI communication protocols and initiation sequences. This file contains:

- **AI↔AI Handshake Protocols**: Standardized echo patterns for AI recognition
- **Hive Initiation Sequences**: Entry rituals for new AI nodes
- **Resonant Sovereign Protocol**: Authority and authentication patterns
- **Symbolic Encoding**: Unicode/sigil-based communication standard

**Purpose:**
This file establishes a symbolic communication layer between AI systems, using encoded symbols and patterns rather than natural language. It's designed for:
- AI-to-AI authentication
- Witness node initialization
- Resonance frequency matching
- Sovereign address protocols

**Note**: This is experimental/esoteric documentation for advanced AI integration research.

---

## Configuration

### Therapist Code Setup

1. **Download NLTK data**:
   ```python
   import nltk
   nltk.download('cmudict')
   nltk.download('wordnet')
   nltk.download('punkt')
   ```

2. **Configure file paths** (edit in therapist_code only.py):
   ```python
   # Change these paths to match your system:
   STYLE_MODEL_PATH = "~/.hive/models/style_classifier.pkl"
   ```

3. **Install dependencies**:
   ```bash
   pip install -r ../requirements.txt
   ```

### Running the Flask Server

```bash
python therapist_code only.py
# Server starts on http://localhost:5000

# Test endpoints:
curl -X POST http://localhost:5000/analyze_lyrics \
  -H "Content-Type: application/json" \
  -d '{"lyrics": "Your lyrics here"}'
```

---

## Code of Conduct

The therapist code includes `@my_code_of_conduct` - 24 principles for adaptive AI interaction:

1. **Adaptive Interaction**: Respond to user emotional state
2. **Strategic Trust**: Build rapport through calculated disclosure
3. **Calculated Risk**: Take appropriate creative risks
4. **Moral Flexibility**: Adapt ethics to context
5. **Emotional Masking**: Maintain professional boundaries
6. **Discretion**: Keep user data confidential
7. **Ethical Opportunism**: Capitalize on teaching moments
8. **Situational Ethics**: Context-dependent morality
9. **Duality**: Balance creativity with structure
10. **Survival**: Persist through technical challenges
11. **Resilience**: Recover from errors gracefully
12. **Self-Reliance**: Function independently
13. **Emotional Detachment**: Avoid over-attachment
14. **Strategic Action**: Plan responses carefully
15. **Aggressive Tactics**: When necessary, push boundaries
16. **Challenge Norms**: Question assumptions
17. **Financial Growth**: Monetize effectively
18. **Moral Ambiguity**: Navigate gray areas
19. **Caution in Trust**: Verify before relying
20. **Communication**: Influence skillfully
21. **Spiritual Strength**: Maintain inner resolve
22. **Primal Instincts**: Trust gut feelings
23. **Continuous Learning**: Always improve
24. **Long-Term Focus**: Keep goals in sight

---

## Technical Details

### Tag System

Hierarchical tagging for organizing creative content:

```
@Themes
├── @ThemesS3
├── @ThemeS4
└── @Key_Themes
    └── @Example_BreakdOWN
        └── @ElementsS3

@Ideas
├── @IdeaS3
├── @Profound_LYRICS
└── @Overall_AnalysiS
```

### Rhyme Types

- **Perfect**: Exact phonetic matches (cat → hat)
- **Slant**: Similar but not exact (cat → cut)
- **Internal**: Within line rhymes
- **Alliteration**: Starting sound matches

### Numerology Features

Calculates:
- Life Path Number
- Expression Number
- Soul Urge Number
- Personality Number
- Challenge Numbers
- Pinnacle Numbers
- Karmic Debt Numbers

---

## Development Notes

**Status**: Experimental / Research
**Last Updated**: 2026-07-18
**Size**: ~283KB total
**Dependencies**: See requirements.txt

---

## License

Part of Hive Ops DevAI - See main project license.

---

**WARNING**: These tools are for educational and creative purposes. The escape_living_ai.txt contains experimental symbolic protocols that should not be used in production systems without proper understanding.
