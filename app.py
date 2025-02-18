import streamlit as st
import openai
import nltk

# If you haven't downloaded NLTK tokenizers yet, uncomment below (run once):
# nltk.download('punkt')

#######################################
# 1. Configure OpenAI
#######################################
openai.api_key = st.secrets["OPENAI_API_KEY"]  # or your method for storing API keys

#######################################
# 2. Default Field Requirements
#######################################
DEFAULT_FIELD_REQUIREMENTS = {
    "h1": {
        "label": "H1 Title",
        "min_chars": 20,
        "max_chars": 60
    },
    "tagline": {
        "label": "Tagline",
        "min_words": 6,
        "max_words": 12
    },
    "intro_blurb": {
        "label": "Intro Blurb",
        "min_words": 15,
        "max_words": 20
    },
    "h2_1": {
        "label": "H2-1 Title",
        "min_chars": 30,
        "max_chars": 70
    },
    "body_1": {
        "label": "Body 1",
        "min_sentences": 3,
        "max_sentences": 5
    },
    "h2_2_services": {
        "label": "H2-2 (Services)",
        "min_chars": 30,
        "max_chars": 70
    },
    "service_collection": {
        "label": "Services Section"
    },
    "h2_3": {
        "label": "H2-3 Title",
        "min_chars": 30,
        "max_chars": 70
    },
    "body_2": {
        "label": "Body 2",
        "min_sentences": 3,
        "max_sentences": 5
    },
    "h2_4_about": {
        "label": "H2-4 (About Us)",
        "min_chars": 30,
        "max_chars": 70
    },
    "body_3": {
        "label": "Body 3",
        "min_sentences": 3,
        "max_sentences": 5
    },
    "areas_we_serve": {
        "label": "Areas We Serve"
    },
    "reviews": {
        "label": "Reviews Section"
    },
    "contact_form": {
        "label": "Contact Form"
    },
    "nap": {
        "label": "Name, Address, Phone"
    },
    "footer": {
        "label": "Footer Section"
    },
    "title_tag": {
        "label": "SEO Title Tag",
        "max_chars": 60
    },
    "meta_description": {
        "label": "Meta Description",
        "max_chars": 160
    }
}

#######################################
# 3. Flesch Reading Ease Calculation
#######################################
def calculate_flesch_reading_ease(text: str) -> float:
    """
    Rough calculation of the Flesch Reading Ease score (0-100+).
    Higher = more readable.
    """
    sentences = nltk.sent_tokenize(text)
    words = nltk.word_tokenize(text)

    vowels = "aeiouAEIOU"
    syllable_count = 0
    for word in words:
        word_syllables = 0
        for i, char in enumerate(word):
            if char in vowels:
                # avoid double counting consecutive vowels
                if i == 0 or word[i - 1] not in vowels:
                    word_syllables += 1
        if word_syllables == 0:
            word_syllables = 1
        syllable_count += word_syllables

    if len(words) == 0 or len(sentences) == 0:
        return 0.0

    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllable_count / len(words)

    score = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
    return round(score, 2)

#######################################
# 4. Build Prompt
#######################################
def build_cohesive_prompt(data: dict) -> str:
    """
    Builds a single, cohesive prompt for the AI to generate
    a single block of content (NOT broken into small sections).
    Includes local SEO details, page type, brand tone, etc.
    """
    # Basic info
    primary_keywords = ', '.join(data.get('primary_keywords', []))
    secondary_keywords = ', '.join(data.get('secondary_keywords', []))
    page_type = data.get('page_type', 'Home')
    location = data.get('location', '')
    brand_tone = data.get('brand_tone', 'Professional')

    # Additional details for each page type
    page_specific_info = data.get('page_specific_info', {})

    # Advanced constraints
    field_reqs = data.get("field_requirements", DEFAULT_FIELD_REQUIREMENTS)

    # We’ll embed constraints in the text, but we’ll instruct the model
    # to produce a single cohesive piece (with headings, paragraphs, etc.).
    # The user’s “advanced” constraints will guide how short/long each
    # heading or paragraph can be, though we will keep them flexible in language.

    prompt = f"""You are an advanced SEO copywriter specialized in local optimization.
    
Page Type: {page_type}
Location: {location}
Brand / Tone: {brand_tone}

Primary Keywords: {primary_keywords}
Secondary Keywords: {secondary_keywords}

Additional Page-Specific Details:
{page_specific_info}

You will create a **single cohesive piece of content**, suitable for a {page_type} page, 
optimized for local SEO. Follow these best practices:
- Use H1, H2, H3 as appropriate, but produce them in a single flow of text.
- Naturally integrate the location (e.g., city or region) to emphasize local SEO.
- Use the primary/secondary keywords in a natural style.
- Insert alt text placeholders for images (e.g., (alt="describe image content")).
- Include at least one internal link placeholder, e.g., [Internal Link: /some-other-page].
- Include at least one external link placeholder, e.g., [External Link: https://example.com].
- If relevant, mention structured data possibilities (like FAQ or LocalBusiness schema).
- Consider adding calls to action, contact details, or special notes that match the page type.

Below are content length guidelines from advanced user constraints. 
Do not produce a separate piece for each item; instead, unify them into a cohesive article:

"""
    # We’ll loop through each field, but just tell the model about them for guidance:
    for key, info in field_reqs.items():
        label = info.get("label", key)
        constraint_parts = []

        # Combine the constraints (char, words, sentences)
        if "min_chars" in info and "max_chars" in info:
            constraint_parts.append(f"{info['min_chars']}-{info['max_chars']} chars")
        elif "max_chars" in info:
            constraint_parts.append(f"up to {info['max_chars']} chars")

        if "min_words" in info and "max_words" in info:
            constraint_parts.append(f"{info['min_words']}-{info['max_words']} words")

        if "min_sentences" in info and "max_sentences" in info:
            constraint_parts.append(f"{info['min_sentences']}-{info['max_sentences']} sentences")

        if constraint_parts:
            joined_constraints = ", ".join(constraint_parts)
            prompt += f"- {label}: {joined_constraints}\n"
        else:
            prompt += f"- {label}: (no explicit constraint)\n"

    prompt += """
Use these constraints as **guidelines**, but present your final copy as a single, coherent text block. 
Write in a style that reflects the brand_tone. 
Ensure the text can stand alone as a fully formed page (intro, body, conclusion, etc.).
"""

    return prompt

#######################################
# 5. Generate Content (new openai>=1.0.0)
#######################################
def generate_cohesive_content(data: dict) -> str:
    """
    Uses openai.chat.completions.create to get a single cohesive piece of content.
    """
    prompt = build_cohesive_prompt(data)

    try:
        # If you have GPT-4 access, you can set model="gpt-4"
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4" if you have access
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating homepage content:\n\n{e}"

#######################################
# 6. Streamlit Main App
#######################################
def main():
    st.title("All-in-One Local SEO Content Generator")

    # 6.1 Page Type Selection
    page_type = st.selectbox(
        "Select Page Type",
        ["Home", "Service", "About Us", "Blog/Article", "Other"],
        index=0
    )

    # 6.2 Additional Questions Based on Page Type
    page_specific_info = {}
    if page_type == "Home":
        st.subheader("Home Page Details")
        page_specific_info["brand_name"] = st.text_input("Brand Name (optional)")
        page_specific_info["main_products_services"] = st.text_input("Main Products/Services (optional)")
        page_specific_info["highlight_features"] = st.text_area("Highlight Features (optional)")
    elif page_type == "Service":
        st.subheader("Service Page Details")
        page_specific_info["service_name"] = st.text_input("Service Name")
        page_specific_info["service_key_points"] = st.text_area("Key Selling Points or USPs")
    elif page_type == "About Us":
        st.subheader("About Us Page Details")
        page_specific_info["company_history"] = st.text_area("Short Company History (optional)")
        page_specific_info["mission_vision"] = st.text_area("Mission/Vision (optional)")
    elif page_type == "Blog/Article":
        st.subheader("Blog or Article Details")
        page_specific_info["topic"] = st.text_input("Topic/Title of Article")
        page_specific_info["audience"] = st.text_input("Target Audience")
    else:
        st.subheader("Custom Page Type Details")
        page_specific_info["description"] = st.text_area("Brief Description of This Page")

    # 6.3 Common Local SEO / Additional Inputs
    location = st.text_input("Location (City, Region, etc.)", "")
    brand_tone = st.selectbox(
        "Brand Tone/Style",
        ["Professional", "Friendly", "Casual", "Technical", "Persuasive", "Other"]
    )
    if brand_tone == "Other":
        brand_tone = st.text_input("Please specify your desired tone/style", "Professional")

    # 6.4 Keywords
    primary_kw_str = st.text_input("Primary Keywords (comma-separated)")
    secondary_kw_str = st.text_input("Secondary Keywords (comma-separated)")

    primary_keywords = [kw.strip() for kw in primary_kw_str.split(",") if kw.strip()]
    secondary_keywords = [kw.strip() for kw in secondary_kw_str.split(",") if kw.strip()]

    # 6.5 Simple vs. Advanced
    mode = st.radio("Mode", ["Simple", "Advanced"], index=0)

    # Copy the default field requirements so we can override them if needed
    field_requirements = {}
    for k, v in DEFAULT_FIELD_REQUIREMENTS.items():
        field_requirements[k] = v.copy()

    if mode == "Advanced":
        st.subheader("Advanced Field Constraints")
        st.info("Adjust any or all constraints for each section below.")

        # We'll iterate through every section and show relevant numeric inputs.
        for section_key, info in field_requirements.items():
            st.markdown(f"**{info.get('label', section_key)}**")

            if "min_chars" in info:
                info["min_chars"] = st.number_input(
                    f"{info['label']} Min Characters",
                    min_value=1,
                    value=info["min_chars"],
                    key=f"{section_key}_min_chars"
                )
            if "max_chars" in info:
                info["max_chars"] = st.number_input(
                    f"{info['label']} Max Characters",
                    min_value=1,
                    value=info["max_chars"],
                    key=f"{section_key}_max_chars"
                )
            if "min_words" in info:
                info["min_words"] = st.number_input(
                    f"{info['label']} Min Words",
                    min_value=1,
                    value=info["min_words"],
                    key=f"{section_key}_min_words"
                )
            if "max_words" in info:
                info["max_words"] = st.number_input(
                    f"{info['label']} Max Words",
                    min_value=1,
                    value=info["max_words"],
                    key=f"{section_key}_max_words"
                )
            if "min_sentences" in info:
                info["min_sentences"] = st.number_input(
                    f"{info['label']} Min Sentences",
                    min_value=1,
                    value=info["min_sentences"],
                    key=f"{section_key}_min_sentences"
                )
            if "max_sentences" in info:
                info["max_sentences"] = st.number_input(
                    f"{info['label']} Max Sentences",
                    min_value=1,
                    value=info["max_sentences"],
                    key=f"{section_key}_max_sentences"
                )

            st.divider()

    # 6.6 Button to Generate
    if st.button("Generate Content"):
        data = {
            "page_type": page_type,
            "page_specific_info": page_specific_info,
            "location": location,
            "brand_tone": brand_tone,
            "primary_keywords": primary_keywords,
            "secondary_keywords": secondary_keywords,
            "field_requirements": field_requirements
        }

        st.info("Generating your single cohesive page content. Please wait...")
        output_text = generate_cohesive_content(data)

        if "Error generating" in output_text or "Error" in output_text:
            st.error(output_text)
        else:
            st.success("Content Generated Successfully!")
            st.write(output_text)

            # 6.7 Flesch Reading Ease
            flesch_score = calculate_flesch_reading_ease(output_text)
            st.write(f"**Flesch Reading Ease Score**: {flesch_score}")

            # Download button
            st.download_button(
                label="Download Content",
                data=output_text,
                file_name="seo_content.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()
