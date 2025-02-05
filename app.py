import streamlit as st
import googlemaps
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import openai
from bs4 import BeautifulSoup
import time

# -------------------------------------------------------------------------
# 1. Load API Keys from Streamlit Secrets
# -------------------------------------------------------------------------
places_api_key = st.secrets["GOOGLE_MAPS_API_KEY"]
openai_api_key = st.secrets["OPENAI_API_KEY"]

if not openai_api_key or not openai_api_key.startswith("sk-"):
    st.error("🔑 OpenAI API Key is missing or incorrect! Please update it in Streamlit Secrets.")
    st.stop()

# Instead of creating a custom client, simply set the API key:
openai.api_key = openai_api_key

# Initialize Google Maps Client
gmaps = googlemaps.Client(key=places_api_key)

# -------------------------------------------------------------------------
# ... (other helper functions remain the same) ...
# -------------------------------------------------------------------------

def analyze_competitors_with_gpt(client_gbp: str, competitor_details: list, client_info: dict):
    """
    Provides deep, data-driven insights about each competitor vs. the target client.
    competitor_details: list of { name, address, phone, rating, reviews, website, website_content }
    client_info: { rating, reviews, place_id, name, etc. } for the target business
    """
    # Build competitor summary lines
    competitor_summaries = []
    for comp in competitor_details:
        summary_str = (
            f"- Name: {comp.get('name', 'N/A')} (Rating: {comp.get('rating', 'N/A')}, "
            f"{comp.get('reviews', '0')} reviews)\n"
            f"  Address: {comp.get('address', 'N/A')}\n"
            f"  Phone: {comp.get('phone', 'N/A')}\n"
        )
        if comp.get('website_content'):
            summary_str += f"  Website Snippet: {comp.get('website_content')[:200]}...\n"
        competitor_summaries.append(summary_str)

    competitor_text = "\n".join(competitor_summaries)

    # Include target business info in the prompt for deeper analysis
    target_str = (
        f"Target Business: {client_gbp}\n"
        f"Rating: {client_info.get('rating', 'N/A')} | Reviews: {client_info.get('reviews', '0')}\n"
    )

    prompt = f"""
You are an advanced local SEO consultant. Compare "{client_gbp}" to the competitors below:
Target Business Data:
{target_str}

Competitors Data:
{competitor_text}

Provide a deep, data-driven, actionable analysis:
1. Summarize how the target's rating/review count compares to each competitor.
2. Evaluate each competitor's website snippet (if any) and how the target might improve or differentiate its own content.
3. Provide specific local SEO recommendations (citations, GMB/GBP enhancements, content strategies) with metrics or evidence-based reasoning.
4. Conclude with the top priorities for the target to outrank these competitors.
    """

    try:
        # Use the new interface directly:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a highly skilled local SEO consultant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=900
        )
        gpt_answer = response.choices[0].message.content
        return gpt_answer.strip()
    except Exception as e:
        st.error(f"OpenAI API error: {e}")
        return "Could not analyze competitors with ChatGPT."

# -------------------------------------------------------------------------
# ... (rest of your code remains unchanged) ...
# -------------------------------------------------------------------------

def main():
    # ... (your Streamlit app code) ...
    # This function remains unchanged.
    pass

if __name__ == "__main__":
    main()
