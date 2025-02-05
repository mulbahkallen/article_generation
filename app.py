import streamlit as st
import openai
import time

# -------------------------------------------------------------------------
# 1. Load API Key from Streamlit Secrets
# -------------------------------------------------------------------------
openai_api_key = st.secrets["OPENAI_API_KEY"]

if not openai_api_key or not openai_api_key.startswith("sk-"):
    st.error("🔑 OpenAI API Key is missing or incorrect! Please update it in Streamlit Secrets.")
    st.stop()

# Create OpenAI client like in your working snippet
openai_client = openai.OpenAI(api_key=openai_api_key)

# -------------------------------------------------------------------------
# 2. Helper Function to Generate SEO Article via OpenAI
# -------------------------------------------------------------------------
def generate_seo_article(data: dict) -> str:
    """
    Build a prompt based on user inputs and request an SEO optimized article from OpenAI.
    """
    # Build a detailed prompt with the required specifications.
    prompt = "You are an expert SEO content writer. Generate an SEO optimized article with the following specifications:\n\n"
    
    # Core Inputs
    prompt += f"Primary Keyword: {data['primary_keyword']}\n"
    prompt += f"Secondary Keywords: {data['secondary_keywords']}\n"
    prompt += f"Tertiary Keywords: {data['tertiary_keywords']}\n"
    prompt += f"Target Area: {data['target_area']}\n"
    prompt += f"Target Audience: {data['target_audience']}\n"
    prompt += f"Article Length: {data['article_length']} words\n"
    prompt += f"Article Type: {data['article_type']}\n"
    prompt += f"Tone and Style: {data['tone_style']}\n"
    prompt += f"Call to Action (CTA): {data['cta']}\n\n"
    
    # Local Business Details (if provided)
    if data["local_business_details"]:
        local = data["local_business_details"]
        prompt += "Local Business Details:\n"
        prompt += f"  Business Name: {local.get('business_name', '')}\n"
        prompt += f"  Address: {local.get('address', '')}\n"
        prompt += f"  Phone Number: {local.get('phone_number', '')}\n"
        prompt += f"  Website URL: {local.get('website_url', '')}\n"
        prompt += f"  Google My Business Listing: {local.get('gmb', '')}\n\n"
    
    # Meta & Optimization Options
    if data.get("meta_title") or data.get("meta_description"):
        prompt += "Meta Title & Description:\n"
        prompt += f"  Title: {data.get('meta_title', '')}\n"
        prompt += f"  Description: {data.get('meta_description', '')}\n\n"
    prompt += f"Featured Snippet Optimization: {data['featured_snippet']}\n"
    if data["schema_markup"]:
        prompt += f"Structured Data Markup (Schema.org): {data['schema_markup']}\n"
    prompt += "\n"
    
    # Image Optimization Details
    if data["image_details"]:
        image_details = data["image_details"]
        prompt += "Image Optimization Details:\n"
        prompt += "  Image Alt Text: [Auto-generated based on Primary Keyword]\n"
        prompt += f"  Image File Naming Format: {image_details.get('file_naming_format', '')}\n\n"
    
    # Social Media Sharing & Additional Notes
    prompt += f"Social Media Sharing Optimization: {data['social_media_sharing']}\n"
    if data["additional_notes"]:
        prompt += f"Additional Notes: {data['additional_notes']}\n\n"
    
    # Output Format instructions
    prompt += "Output Format:\n"
    prompt += "Title: [Auto-generated using Primary Keyword]\n"
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
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a highly skilled SEO content writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500  # Adjust this as needed based on desired article length
        )
        article = response.choices[0].message.content
        return article
    except Exception as e:
        return f"Error generating article: {e}"

# -------------------------------------------------------------------------
# 3. Streamlit Main App
# -------------------------------------------------------------------------
def main():
    st.title("SEO Optimized Article Generation Template")
    st.write("Generate a fully optimized SEO article using a comprehensive, data-driven template.")

    # Create a form for all user input fields
    with st.form("seo_article_form"):
        st.header("User Input Fields")
        primary_keyword = st.text_input("Primary Keyword", placeholder="Enter Primary Keyword")
        secondary_keywords = st.text_input("Secondary Keywords (comma-separated)", placeholder="Enter Secondary Keywords, comma-separated")
        tertiary_keywords = st.text_input("Tertiary Keywords (comma-separated)", placeholder="Enter Tertiary Keywords, comma-separated")
        target_area = st.text_input("Target Area (Location-Based SEO)", placeholder="Enter City, State, or Region")
        target_audience = st.text_area("Target Audience", placeholder="Describe the target demographic")
        article_length = st.number_input("Article Length (Word Count)", min_value=300, max_value=5000, value=1000, step=100)

        article_type = st.selectbox("Article Type", ["Blog Post", "Service Page", "Landing Page", "Product Page", "Other"])
        if article_type == "Other":
            article_type = st.text_input("Please specify the Article Type", placeholder="Specify Article Type")
        
        tone_style = st.selectbox("Tone and Style", ["Professional", "Conversational", "Informative", "Persuasive", "Other"])
        if tone_style == "Other":
            tone_style = st.text_input("Please specify the Tone and Style", placeholder="Specify Tone and Style")
            
        cta = st.text_input("Call to Action (CTA)", placeholder="Describe the main action the user should take")
        
        # Optional Local Business Details
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
        
        # Optional Meta Title & Description
        st.subheader("Meta Title & Description (Optional)")
        meta_title = st.text_input("Title", placeholder="Enter Title")
        meta_description = st.text_area("Meta Description", placeholder="Enter Meta Description")
        
        featured_snippet = st.selectbox("Featured Snippet Optimization (Optional)", ["Yes", "No"])
        schema_markup = st.text_input("Structured Data Markup (Schema.org) (Optional)", placeholder="Specify Schema Type")
        
        # Image Optimization Details
        st.subheader("Image Optimization Details")
        uploaded_image = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])
        image_file_naming = st.text_input("Image File Names (specify naming format)", placeholder="Specify Naming Format")
        image_details = {}
        if uploaded_image or image_file_naming:
            image_details = {
                "file_naming_format": image_file_naming
            }
        
        social_media_sharing = st.selectbox("Social Media Sharing Optimization", ["Yes", "No"])
        
        additional_notes = st.text_area("Additional Notes", placeholder="Provide any extra requirements")
        
        submitted = st.form_submit_button("Generate SEO Article")
    
    # Once the form is submitted, compile all data and generate the article
    if submitted:
        data = {
            "primary_keyword": primary_keyword,
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
            time.sleep(1)  # Optional: simulate processing delay
        
        st.header("Generated SEO Optimized Article")
        st.write(article)
        
        # Allow the user to download the generated article as a text file
        st.download_button(
            label="Download Article as Text",
            data=article,
            file_name="seo_optimized_article.txt",
            mime="text/plain"
        )

if __name__ == "__main__":
    main()
