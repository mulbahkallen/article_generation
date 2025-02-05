import nest_asyncio
nest_asyncio.apply()  # Allow nested asyncio event loops (necessary for Streamlit)

import streamlit as st
import googlemaps
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import openai
from bs4 import BeautifulSoup
import asyncio
import time

# -------------------------------------------------------------------------
# 1. Load API Keys from Streamlit Secrets
# -------------------------------------------------------------------------
places_api_key = st.secrets["GOOGLE_MAPS_API_KEY"]
openai_api_key = st.secrets["OPENAI_API_KEY"]

if not openai_api_key or not openai_api_key.startswith("sk-"):
    st.error("🔑 OpenAI API Key is missing or incorrect! Please update it in Streamlit Secrets.")
    st.stop()

# Set the API key directly on the openai module (no custom client needed)
openai.api_key = openai_api_key

# Initialize Google Maps Client
gmaps = googlemaps.Client(key=places_api_key)

# -------------------------------------------------------------------------
# 2. Helper Functions for Maps, Scraping, and Data Processing
# -------------------------------------------------------------------------
def get_lat_long_google(location_name: str):
    """
    Get latitude and longitude for a given address/string location using the Google Maps Geocoding API.
    """
    try:
        geocode_result = gmaps.geocode(location_name)
        if geocode_result:
            lat = geocode_result[0]['geometry']['location']['lat']
            lon = geocode_result[0]['geometry']['location']['lng']
            return lat, lon
        else:
            return None, None
    except Exception as e:
        st.error(f"Error with Geocoding API: {e}")
        return None, None

def generate_square_grid(center_lat: float, center_lon: float, radius_miles: float, grid_size: int = 5):
    """
    Generate a grid_size x grid_size grid of points within a square bounding box of +/- radius_miles around (center_lat, center_lon).
    """
    if grid_size < 1:
        return []
    lat_extent = radius_miles / 69.0
    lon_extent = radius_miles / (69.0 * np.cos(np.radians(center_lat)))
    lat_values = np.linspace(center_lat - lat_extent, center_lat + lat_extent, grid_size)
    lon_values = np.linspace(center_lon - lon_extent, center_lon + lon_extent, grid_size)
    grid_points = [(lat, lon) for lat in lat_values for lon in lon_values]
    return grid_points

def fetch_nearby_places(lat: float, lon: float, keyword: str, api_key: str):
    """
    Collect up to 60 results from the Google Places Nearby Search (sorted by distance).
    """
    location = f"{lat},{lon}"
    base_url = (
        "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        f"?location={location}&keyword={keyword}"
        f"&rankby=distance&key={api_key}"
    )
    all_results = []
    page_url = base_url
    for _ in range(3):  # Up to 3 pages
        try:
            resp = requests.get(page_url)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Request error while searching Places API: {e}")
            break
        results = data.get("results", [])
        all_results.extend(results)
        if "next_page_token" in data:
            next_token = data["next_page_token"]
            time.sleep(2)  # Wait before the next request
            page_url = base_url + f"&pagetoken={next_token}"
        else:
            break
    return all_results

def search_places_top3_by_rating(lat: float, lon: float, keyword: str, target_business: str, api_key: str):
    """
    Fetch results near (lat, lon), sort by rating (desc) and reviews (desc), and return:
      1) Top 3 competitor places.
      2) The rank and details of the target business if found.
    """
    all_results = fetch_nearby_places(lat, lon, keyword, api_key)
    structured = []
    for place in all_results:
        name = place.get("name", "Unknown")
        place_id = place.get("place_id", "")
        rating = place.get("rating", 0) or 0
        reviews = place.get("user_ratings_total", 0) or 0
        structured.append({
            "place_id": place_id,
            "name": name,
            "rating": float(rating) if isinstance(rating, (int, float)) else 0.0,
            "reviews": int(reviews) if isinstance(reviews, int) else 0,
        })
    structured.sort(key=lambda x: (-x["rating"], -x["reviews"], x["name"]))
    top_3 = structured[:3]
    rank = None
    client_details = None
    for idx, biz in enumerate(structured):
        if target_business.lower() in biz["name"].lower():
            rank = idx + 1  # 1-based indexing
            client_details = biz
            break
    return rank, top_3, client_details

def get_place_details(place_id: str, api_key: str):
    """
    Fetch additional details about a place using the Google Places Details API.
    """
    details_url = (
        "https://maps.googleapis.com/maps/api/place/details/json"
        f"?place_id={place_id}&key={api_key}"
    )
    try:
        response = requests.get(details_url)
        response.raise_for_status()
        result = response.json().get("result", {})
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching place details: {e}")
        return {}
    return {
        "address": result.get("formatted_address", ""),
        "phone": result.get("formatted_phone_number", ""),
        "website": result.get("website", ""),
        "name": result.get("name", ""),
        "rating": result.get("rating", "N/A"),
        "reviews": result.get("user_ratings_total", "N/A"),
    }

def scrape_website(url: str, max_chars: int = 2000):
    """
    Scrape a website to extract text content for AI analysis.
    """
    if not url:
        return ""
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        texts = soup.find_all(["p", "h1", "h2", "h3", "h4", "li"])
        combined = " ".join(t.get_text(separator=" ", strip=True) for t in texts)
        return combined[:max_chars]
    except Exception:
        return ""

def create_heatmap(df: pd.DataFrame, center_lat: float, center_lon: float):
    """
    Create a heatmap using Plotly based on grid ranking data.
    """
    fig = go.Figure()
    for _, row in df.iterrows():
        rank_val = row['rank']
        if rank_val is None:
            marker_color = 'red'
            text_label = "X"
        elif rank_val <= 3:
            marker_color = 'green'
            text_label = str(rank_val)
        elif rank_val <= 10:
            marker_color = 'orange'
            text_label = str(rank_val)
        else:
            marker_color = 'red'
            text_label = str(rank_val)
        if row['top_3']:
            hover_items = []
            for i, biz in enumerate(row['top_3']):
                hover_items.append(
                    f"{i+1}. {biz['name']} (Rating: {biz['rating']}⭐, {biz['reviews']} reviews)"
                )
            hover_text = "<br>".join(hover_items)
        else:
            hover_text = "No competitor data."
        fig.add_trace(
            go.Scattermapbox(
                lat=[row['latitude']],
                lon=[row['longitude']],
                mode='markers+text',
                marker=dict(size=20, color=marker_color),
                text=[text_label],
                textposition="middle center",
                textfont=dict(size=14, color="black", family="Arial Black"),
                hovertext=hover_text,
                hoverinfo="text",
                showlegend=False
            )
        )
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=center_lat, lon=center_lon),
            zoom=12
        ),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        title="Target Business Ranking Heatmap"
    )
    return fig

def generate_growth_report(df: pd.DataFrame, client_gbp: str):
    """
    Generate a textual growth report based on ranking data.
    """
    total_points = len(df)
    df_found = df.dropna(subset=['rank'])
    top_3_points = df_found[df_found['rank'] <= 3].shape[0]
    top_10_points = df_found[df_found['rank'] <= 10].shape[0]
    pct_top_3 = 100.0 * top_3_points / total_points if total_points else 0
    pct_top_10 = 100.0 * top_10_points / total_points if total_points else 0
    average_rank = df_found['rank'].mean() if not df_found.empty else None
    lines = [
        f"**{client_gbp} Coverage Report**",
        f"- **Total Grid Points:** {total_points}",
        f"- **Business Found at:** {len(df_found)} points",
        f"- **In Top 3:** {top_3_points} points ({pct_top_3:.1f}% of total)",
        f"- **In Top 10:** {top_10_points} points ({pct_top_10:.1f}% of total)",
        f"- **Average Rank (where found):** {average_rank:.2f}" if average_rank else "- Average Rank: N/A",
    ]
    return "\n".join(lines)

def analyze_competitors_with_gpt(client_gbp: str, competitor_details: list, client_info: dict):
    """
    Provides deep, data-driven insights comparing the target business with its competitors.
    """
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

Provide a deep, data-driven, actionable analysis with specific SEO recommendations.
    """
    try:
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
# 3. Asynchronous Helper Functions for SEO Article Generation
# -------------------------------------------------------------------------
async def async_generate_seo_article(data: dict) -> str:
    prompt = "You are an expert SEO content writer. Generate an SEO optimized article with the following specifications:\n\n"
    prompt += f"Primary Keywords: {', '.join(data['primary_keywords'])}\n"
    prompt += f"Secondary Keywords: {data['secondary_keywords']}\n"
    prompt += f"Tertiary Keywords: {data['tertiary_keywords']}\n"
    prompt += f"Target Area: {data['target_area']}\n"
    prompt += f"Target Audience: {data['target_audience']}\n"
    prompt += f"Article Length: {data['article_length']} words\n"
    prompt += f"Article Type: {data['article_type']}\n"
    prompt += f"Tone and Style: {data['tone_style']}\n"
    prompt += f"Call to Action (CTA): {data['cta']}\n\n"
    if data["local_business_details"]:
        local = data["local_business_details"]
        prompt += "Local Business Details:\n"
        prompt += f"  Business Name: {local.get('business_name', '')}\n"
        prompt += f"  Address: {local.get('address', '')}\n"
        prompt += f"  Phone Number: {local.get('phone_number', '')}\n"
        prompt += f"  Website URL: {local.get('website_url', '')}\n"
        prompt += f"  Google My Business Listing: {local.get('gmb', '')}\n\n"
    if data.get("meta_title") or data.get("meta_description"):
        prompt += "Meta Title & Description:\n"
        prompt += f"  Title: {data.get('meta_title', '')}\n"
        prompt += f"  Description: {data.get('meta_description', '')}\n\n"
    prompt += f"Featured Snippet Optimization: {data['featured_snippet']}\n"
    if data["schema_markup"]:
        prompt += f"Structured Data Markup (Schema.org): {data['schema_markup']}\n"
    prompt += "\n"
    if data["image_details"]:
        image_details = data["image_details"]
        prompt += "Image Optimization Details:\n"
        prompt += "  Image Alt Text: [Auto-generated based on Primary Keywords]\n"
        prompt += f"  Image File Naming Format: {image_details.get('file_naming_format', '')}\n\n"
    prompt += f"Social Media Sharing Optimization: {data['social_media_sharing']}\n"
    if data["additional_notes"]:
        prompt += f"Additional Notes: {data['additional_notes']}\n\n"
    prompt += "Output Format:\n"
    prompt += "Title: [Auto-generated using Primary Keywords]\n"
    prompt += "Meta Description: [Auto-generated based on keyword strategy and user input]\n"
    prompt += "Introduction: [Generated based on input, introducing the topic and location relevance]\n"
    prompt += "Main Content Sections:\n"
    prompt += "  H2: Primary Keyword Usage (include keyword naturally within the first 100 words)\n"
    prompt += "  H2: Secondary Keyword Integration (structured content with natural flow)\n"
    prompt += "  H2: Local SEO Optimization (mention target location and local relevance)\n"
    prompt += "  H2: Additional Relevant Information (include tertiary keywords naturally)\n"
    prompt += "  H2: Call to Action (encourage user engagement based on CTA)\n"
    prompt += "Conclusion: [Wrap up with a final CTA and reinforcement of key points]\n"
    prompt += "SEO Enhancements:\n"
    prompt += "  - Keyword Density: [Optimized automatically]\n"
    prompt += "  - Readability Score: [Optimized for clarity]\n"
    prompt += "  - Mobile-Friendliness: [Checked]\n"
    prompt += "  - Image SEO: [Checked]\n"
    prompt += "  - Schema Markup: [Implemented if selected]\n\n"
    prompt += "Please generate the complete article accordingly."
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a highly skilled SEO content writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating article: {e}"

def generate_seo_article(data: dict) -> str:
    return asyncio.run(async_generate_seo_article(data))

async def async_generate_title_and_meta(article: str) -> (str, str):
    prompt = f"""
You are an expert SEO strategist and copywriter. Based on the following article, please generate an SEO-optimized title and meta description that accurately reflect the article's content and adhere to SEO best practices.

Article:
{article}

Provide your answer in the following format:
Title: <Your SEO optimized title>
Meta Description: <Your SEO optimized meta description>
    """
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert SEO strategist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        output = response.choices[0].message.content
        title = ""
        meta_desc = ""
        for line in output.splitlines():
            if line.startswith("Title:"):
                title = line[len("Title:"):].strip()
            elif line.startswith("Meta Description:"):
                meta_desc = line[len("Meta Description:"):].strip()
        return title, meta_desc
    except Exception as e:
        return f"Error generating title/meta: {e}", ""

def generate_title_and_meta(article: str) -> (str, str):
    return asyncio.run(async_generate_title_and_meta(article))

# -------------------------------------------------------------------------
# 4. Streamlit Main App
# -------------------------------------------------------------------------
def main():
    st.title("SEO Optimized Article Generation Template")
    st.write("Generate a fully optimized SEO article using a comprehensive, data-driven template.")

    with st.form("seo_article_form"):
        st.header("User Input Fields")
        primary_keywords_str = st.text_input("Primary Keywords (comma-separated)", placeholder="Enter Primary Keywords (comma-separated)")
        primary_keywords = [kw.strip() for kw in primary_keywords_str.split(",") if kw.strip()]
        secondary_keywords = st.text_input("Secondary Keywords (comma-separated)", placeholder="Enter Secondary Keywords, comma-separated")
        tertiary_keywords = st.text_input("Tertiary Keywords (comma-separated)", placeholder="Enter Tertiary Keywords (comma-separated)")
        target_area = st.text_input("Target Area (Location-Based SEO)", placeholder="Enter City, State, or Region")
        target_audience = st.text_area("Target Audience", placeholder="Describe the target demographic")
        article_length = st.number_input("Article Length (Word Count)", min_value=300, max_value=5000, value=1200, step=100)
        article_type = st.selectbox("Article Type", ["Blog Post", "Service Page", "Landing Page", "Product Page", "Other"])
        if article_type == "Other":
            article_type = st.text_input("Please specify the Article Type", placeholder="Specify Article Type")
        tone_style = st.selectbox("Tone and Style", ["Professional", "Conversational", "Informative", "Persuasive", "Other"])
        if tone_style == "Other":
            tone_style = st.text_input("Please specify the Tone and Style", placeholder="Specify Tone and Style")
        cta = st.text_input("Call to Action (CTA)", placeholder="Describe the main action the user should take")
        st.subheader("Local Business Details (If applicable)")
        business_name = st.text_input("Business Name", placeholder="Enter Business Name")
        address = st.text_input("Address", placeholder="Enter Address")
        phone_number = st.text_input("Phone Number", placeholder="Enter Contact Info")
        website_url = st.text_input("Website URL", placeholder="Enter Website")
        gmb = st.text_input("Google My Business (GMB) Listing", placeholder="Enter GMB Link")
        local_business_details = {}
        if any([business_name, address, phone_number, website_url, gmb]):
            local_business_details = {
                "business_name": business_name,
                "address": address,
                "phone_number": phone_number,
                "website_url": website_url,
                "gmb": gmb
            }
        st.subheader("Meta Title & Description (Optional)")
        meta_title = st.text_input("Title", placeholder="Enter Title")
        meta_description = st.text_area("Meta Description", placeholder="Enter Meta Description")
        featured_snippet = st.selectbox("Featured Snippet Optimization (Optional)", ["Yes", "No"])
        schema_markup = st.text_input("Structured Data Markup (Schema.org) (Optional)", placeholder="Specify Schema Type")
        st.subheader("Image Optimization Details")
        uploaded_image = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])
        image_file_naming = st.text_input("Image File Names (specify naming format)", placeholder="Specify Naming Format")
        image_details = {}
        if uploaded_image or image_file_naming:
            image_details = {"file_naming_format": image_file_naming}
        social_media_sharing = st.selectbox("Social Media Sharing Optimization", ["Yes", "No"])
        additional_notes = st.text_area("Additional Notes", placeholder="Provide any extra requirements")
        
        submitted = st.form_submit_button("Generate SEO Article")
    
    if submitted:
        data = {
            "primary_keywords": primary_keywords,
            "secondary_keywords": secondary_keywords,
            "tertiary_keywords": tertiary_keywords,
            "target_area": target_area,
            "target_audience": target_audience,
            "article_length": article_length,
            "article_type": article_type,
            "tone_style": tone_style,
            "cta": cta,
            "local_business_details": local_business_details,
            "meta_title": meta_title,
            "meta_description": meta_description,
            "featured_snippet": featured_snippet,
            "schema_markup": schema_markup,
            "image_details": image_details,
            "social_media_sharing": social_media_sharing,
            "additional_notes": additional_notes
        }
        
        with st.spinner("Generating SEO optimized article..."):
            article = generate_seo_article(data)
            time.sleep(1)
        
        if article.startswith("Error generating article:"):
            st.error(article)
        else:
            st.header("Generated SEO Optimized Article")
            st.write(article)
            
            with st.spinner("Generating Title and Meta Description..."):
                title, meta_desc = generate_title_and_meta(article)
                time.sleep(1)
            
            st.subheader("Article Title")
            st.write(title)
            st.subheader("Meta Description")
            st.write(meta_desc)
            
            st.download_button(
                label="Download Article as Text",
                data=article,
                file_name="seo_optimized_article.txt",
                mime="text/plain"
            )
    
    # --- Competitor Analysis Section ---
    # Persist competitor data in session state
    if "competitor_place_ids" not in st.session_state:
        st.session_state["competitor_place_ids"] = set()
    if "client_info" not in st.session_state:
        st.session_state["client_info"] = {}
    
    # Example: After generating heatmap data, competitor IDs and client info are stored.
    # Here we assume that elsewhere in your code (e.g., after generating a heatmap),
    # st.session_state["competitor_place_ids"] and st.session_state["client_info"] are set.
    competitor_place_ids = st.session_state.get("competitor_place_ids", set())
    client_info_global = st.session_state.get("client_info", {})
    
    if competitor_place_ids:
        if st.button("Analyze Competitors with ChatGPT"):
            with st.spinner("Fetching competitor details & scraping websites..."):
                competitor_details_list = []
                for pid in competitor_place_ids:
                    details = get_place_details(pid, places_api_key)
                    website_content = ""
                    if details.get('website'):
                        website_content = scrape_website(details['website'], max_chars=2000)
                    competitor_details_list.append({
                        'name': details.get('name', ''),
                        'address': details.get('address', ''),
                        'phone': details.get('phone', ''),
                        'rating': details.get('rating', 'N/A'),
                        'reviews': details.get('reviews', '0'),
                        'website': details.get('website', ''),
                        'website_content': website_content
                    })
                gpt_analysis = analyze_competitors_with_gpt(
                    client_gbp=st.text_input("Enter Your Business Name (for analysis)", "Starbucks"),
                    competitor_details=competitor_details_list,
                    client_info=client_info_global
                )
            st.write("### 🏆 Competitor Comparison & Recommendations")
            st.write(gpt_analysis)
    else:
        st.info("No competitor data found to analyze with ChatGPT.")

if __name__ == "__main__":
    main()
