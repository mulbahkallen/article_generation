import streamlit as st
import openai
import nltk

# If you haven't already downloaded punkt:
# nltk.download('punkt')

#######################################
# 1. Configure OpenAI
#######################################
openai.api_key = st.secrets["OPENAI_API_KEY"]  # or however you store your key

#######################################
# 2. Define Different Page Structures
#######################################
# Each page type has its own list of sections with default constraints.
# You can expand or modify these as needed.
PAGE_DEFAULT_STRUCTURES = {
    "Home": [
        {"key": "h1", "label": "H1 Title", "min_chars": 20, "max_chars": 60},
        {"key": "tagline", "label": "Tagline", "min_words": 6, "max_words": 12},
        {"key": "intro_blurb", "label": "Intro/Welcome Blurb", "min_words": 15, "max_words": 25},
        {"key": "h2_services", "label": "H2 (Services)", "min_chars": 30, "max_chars": 70},
        {"key": "services_body", "label": "Services Body", "min_sentences": 2, "max_sentences": 4},
        {"key": "h2_about", "label": "H2 (About)", "min_chars": 30, "max_chars": 70},
        {"key": "about_body", "label": "About Body", "min_sentences": 2, "max_sentences": 4},
        {"key": "reviews", "label": "Reviews Section"},
        {"key": "areas_we_serve", "label": "Areas We Serve"},
        {"key": "call_to_action", "label": "CTA/Conversion Prompt"},
        {"key": "nap", "label": "Name, Address, Phone"},
        {"key": "footer", "label": "Footer Section"},
        {"key": "title_tag", "label": "SEO Title Tag", "max_chars": 60},
        {"key": "meta_description", "label": "Meta Description", "max_chars": 160},
    ],
    "Service": [
        {"key": "h1_service", "label": "H1 (Service Name)", "min_chars": 20, "max_chars": 60},
        {"key": "service_intro", "label": "Service Intro", "min_sentences": 2, "max_sentences": 3},
        {"key": "h2_benefits", "label": "H2 (Key Benefits)", "min_chars": 30, "max_chars": 70},
        {"key": "benefits_body", "label": "Benefits Body", "min_sentences": 2, "max_sentences": 4},
        {"key": "h2_pricing", "label": "H2 (Pricing/Process)", "min_chars": 30, "max_chars": 70},
        {"key": "pricing_body", "label": "Pricing/Process Body", "min_sentences": 2, "max_sentences": 4},
        {"key": "call_to_action", "label": "CTA/Conversion Prompt"},
        {"key": "nap", "label": "Name, Address, Phone"},
        {"key": "footer", "label": "Footer Section"},
        {"key": "title_tag", "label": "SEO Title Tag", "max_chars": 60},
        {"key": "meta_description", "label": "Meta Description", "max_chars": 160},
    ],
    "About Us": [
        {"key": "h1_about", "label": "H1 (About Us Title)", "min_chars": 20, "max_chars": 60},
        {"key": "about_intro", "label": "About Intro", "min_sentences": 2, "max_sentences": 3},
        {"key": "h2_history", "label": "H2 (History)", "min_chars": 30, "max_chars": 70},
        {"key": "history_body", "label": "History Body", "min_sentences": 2, "max_sentences": 4},
        {"key": "h2_mission", "label": "H2 (Mission/Vision)", "min_chars": 30, "max_chars": 70},
        {"key": "mission_body", "label": "Mission/Vision Body", "min_sentences": 2, "max_sentences": 4},
        {"key": "team_intro", "label": "Team/People Intro", "min_sentences": 2, "max_sentences": 4},
        {"key": "call_to_action", "label": "CTA"},
        {"key": "nap", "label": "Name, Address, Phone"},
        {"key": "footer", "label": "Footer Section"},
        {"key": "title_tag", "label": "SEO Title Tag", "max_chars": 60},
        {"key": "meta_description", "label": "Meta Description", "max_chars": 160},
    ],
    "Blog/Article": [
        {"key": "h1_blog", "label": "H1 (Article Title)", "min_chars": 20, "max_chars": 70},
        {"key": "intro_paragraph", "label": "Intro Paragraph", "min_sentences": 2, "max_sentences": 3},
        {"key": "h2_subtopic1", "label": "H2 (Subtopic 1)", "min_chars": 30, "max_chars": 70},
        {"key": "body_subtopic1", "label": "Body Subtopic 1", "min_sentences": 2, "max_sentences": 5},
        {"key": "h2_subtopic2", "label": "H2 (Subtopic 2)", "min_chars": 30, "max_chars": 70},
        {"key": "body_subtopic2", "label": "Body Subtopic 2", "min_sentences": 2, "max_sentences": 5},
        {"key": "conclusion", "label": "Conclusion", "min_sentences": 2, "max_sentences": 3},
        {"key": "footer", "label": "Footer (Optional)"},
        {"key": "title_tag", "label": "SEO Title Tag", "max_chars": 60},
        {"key": "meta_description", "label": "Meta Description", "max_chars": 160},
    ],
    "Other": [
        {"key": "h1_other", "label": "H1 Title", "min_chars": 20, "max_chars": 60},
        {"key": "intro_other", "label": "Intro Section", "min_sentences": 2, "max_sentences": 3},
        {"key": "body_other", "label": "Main Body", "min_sentences": 2, "max_sentences": 5},
        {"key": "call_to_action", "label": "CTA (Optional)"},
        {"key": "nap", "label": "Name, Address, Phone"},
        {"key": "footer", "label": "Footer Section"},
        {"key": "title_tag", "label": "SEO Title Tag", "max_chars": 60},
        {"key": "meta_description", "label": "Meta Description", "max_chars": 160},
    ]
}

#######################################
# 3. Flesch Reading Ease Calculation
#######################################
def calculate_flesch_reading_ease(text: str) -> float:
    """
    Approximate Flesch Reading Ease score (0–100+).
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
# 4. Build a Single Cohesive Prompt
#######################################
def build_cohesive_prompt(data: dict) -> str:
    """
    Builds a single prompt for a unified piece of content,
    reflecting the page's unique structure.
    """
    page_type = data.get("page_type", "Home")
    location = data.get("location", "")
    brand_tone = data.get("brand_tone", "Professional")

    primary_keywords = ', '.join(data.get('primary_keywords', []))
    secondary_keywords = ', '.join(data.get('secondary_keywords', []))

    page_specific_info = data.get('page_specific_info', {})
    structure = data.get("structure", [])  # the list of sections for this page type

    prompt = f"""You are an advanced SEO copywriter with local SEO expertise.

Page Type: {page_type}
Location/Region: {location}
Tone/Style: {brand_tone}
Primary Keywords: {primary_keywords}
Secondary Keywords: {secondary_keywords}

Additional Page-Specific Details:
{page_specific_info}

Below is the structure for this {page_type} page with recommended constraints. 
Please produce a single cohesive piece of text that uses headings (H1, H2, H3, etc.) but is not separated 
into disjoint sections. The final output should read like a well-structured page.

Incorporate:
- Local SEO references to the location
- Natural usage of primary/secondary keywords
- Alt text placeholders for images (e.g., (alt="..."))
- At least one internal link placeholder ([Internal Link: /some-page]) 
- At least one external link placeholder ([External Link: https://example.com])
- Potential calls to action or conversion prompts
- If relevant, mention structured data or schema

Here is the list of sections (with constraints) that should guide your writing:
"""
    for section in structure:
        label = section.get("label", "Unnamed Section")
        constraints = []

        if "min_chars" in section and "max_chars" in section:
            constraints.append(f"{section['min_chars']}-{section['max_chars']} chars")
        elif "max_chars" in section:
            constraints.append(f"up to {section['max_chars']} chars")

        if "min_words" in section and "max_words" in section:
            constraints.append(f"{section['min_words']}-{section['max_words']} words")

        if "min_sentences" in section and "max_sentences" in section:
            constraints.append(f"{section['min_sentences']}-{section['max_sentences']} sentences")

        if constraints:
            prompt += f"- {label}: {', '.join(constraints)}\n"
        else:
            prompt += f"- {label}\n"

    prompt += """
Please present all content in one cohesive flow, using the headings in a natural progression. 
Ensure it can stand alone as a full page.

Now, generate the final text accordingly.
"""
    return prompt

#######################################
# 5. Generate the Content Using openai>=1.0.0
#######################################
def generate_cohesive_content(data: dict) -> str:
    prompt = build_cohesive_prompt(data)
    try:
        # If you have GPT-4 access, you can specify model="gpt-4"
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating content:\n\n{e}"

#######################################
# 6. Streamlit App
#######################################
def main():
    st.title("Local SEO Content Generator (Multi-Page Type)")

    # Page type selection
    page_type = st.selectbox(
        "Select Page Type",
        ["Home", "Service", "About Us", "Blog/Article", "Other"],
        index=0
    )

    # Page-specific extra questions
    page_specific_info = {}
    if page_type == "Home":
        st.subheader("Home Page Details")
        page_specific_info["brand_name"] = st.text_input("Brand Name (optional)")
        page_specific_info["main_products_services"] = st.text_input("Main Products/Services (optional)")
        page_specific_info["home_highlights"] = st.text_area("Highlight Features or Unique Selling Points (optional)")
    elif page_type == "Service":
        st.subheader("Service Page Details")
        page_specific_info["service_name"] = st.text_input("Service Name")
        page_specific_info["service_key_points"] = st.text_area("Key Selling Points/USPs")
    elif page_type == "About Us":
        st.subheader("About Us Page Details")
        page_specific_info["company_history"] = st.text_area("Short Company History (optional)")
        page_specific_info["mission_vision"] = st.text_area("Mission/Vision (optional)")
    elif page_type == "Blog/Article":
        st.subheader("Blog/Article Page Details")
        page_specific_info["blog_topic"] = st.text_input("Topic/Title of Article")
        page_specific_info["target_audience"] = st.text_input("Target Audience or Niche")
    else:
        st.subheader("Custom/Other Page Details")
        page_specific_info["description"] = st.text_area("Brief Description of This Page")

    # Common inputs for local SEO
    location = st.text_input("Location/Region (e.g., City, State)", "")
    brand_tone = st.selectbox("Brand Tone/Style", ["Professional", "Friendly", "Casual", "Technical", "Persuasive", "Other"])
    if brand_tone == "Other":
        brand_tone = st.text_input("Specify your Tone/Style", "Professional")

    # Keywords
    primary_kw_str = st.text_input("Primary Keywords (comma-separated)", "")
    secondary_kw_str = st.text_input("Secondary Keywords (comma-separated)", "")

    primary_keywords = [kw.strip() for kw in primary_kw_str.split(",") if kw.strip()]
    secondary_keywords = [kw.strip() for kw in secondary_kw_str.split(",") if kw.strip()]

    # Select mode
    mode = st.radio("Mode", ["Simple", "Advanced"], index=0)

    # Retrieve default structure for the chosen page type
    default_structure = PAGE_DEFAULT_STRUCTURES.get(page_type, PAGE_DEFAULT_STRUCTURES["Other"])

    # We'll copy so we can override in advanced mode
    structure_for_page = []
    for section in default_structure:
        structure_for_page.append(section.copy())

    if mode == "Advanced":
        st.subheader("Advanced Field Constraints")
        st.info(f"Customize constraints for each section in the {page_type} page structure.")

        # Let user override
        for section in structure_for_page:
            key = section["key"]
            label = section.get("label", key)
            st.markdown(f"**{label}**")

            if "min_chars" in section:
                section["min_chars"] = st.number_input(
                    f"{label} Min Characters",
                    min_value=1,
                    value=section["min_chars"],
                    key=f"{key}_min_chars"
                )
            if "max_chars" in section:
                section["max_chars"] = st.number_input(
                    f"{label} Max Characters",
                    min_value=1,
                    value=section["max_chars"],
                    key=f"{key}_max_chars"
                )
            if "min_words" in section:
                section["min_words"] = st.number_input(
                    f"{label} Min Words",
                    min_value=1,
                    value=section["min_words"],
                    key=f"{key}_min_words"
                )
            if "max_words" in section:
                section["max_words"] = st.number_input(
                    f"{label} Max Words",
                    min_value=1,
                    value=section["max_words"],
                    key=f"{key}_max_words"
                )
            if "min_sentences" in section:
                section["min_sentences"] = st.number_input(
                    f"{label} Min Sentences",
                    min_value=1,
                    value=section["min_sentences"],
                    key=f"{key}_min_sentences"
                )
            if "max_sentences" in section:
                section["max_sentences"] = st.number_input(
                    f"{label} Max Sentences",
                    min_value=1,
                    value=section["max_sentences"],
                    key=f"{key}_max_sentences"
                )

            st.divider()

    if st.button("Generate Content"):
        # Build data object
        data = {
            "page_type": page_type,
            "location": location,
            "brand_tone": brand_tone,
            "primary_keywords": primary_keywords,
            "secondary_keywords": secondary_keywords,
            "page_specific_info": page_specific_info,
            "structure": structure_for_page
        }

        st.info(f"Generating a cohesive {page_type} page. Please wait...")
        output_text = generate_cohesive_content(data)

        if "Error generating" in output_text:
            st.error(output_text)
        else:
            st.success("Content generated successfully!")
            st.write(output_text)

            # Flesch Reading Ease
            score = calculate_flesch_reading_ease(output_text)
            st.write(f"**Flesch Reading Ease Score**: {score}")

            # Download button
            st.download_button(
                label="Download Content",
                data=output_text,
                file_name="seo_content.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()
