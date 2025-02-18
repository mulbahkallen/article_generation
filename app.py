import streamlit as st
import openai
import nltk

# If you haven't downloaded the tokenizer data yet, uncomment below once:
# nltk.download('punkt')

###########################################################
# 1. OpenAI Configuration
###########################################################
openai.api_key = st.secrets["OPENAI_API_KEY"]  # Adjust to your secure storage method

###########################################################
# 2. Global Guidelines / Constraints
###########################################################
# We'll incorporate these into the prompt so the model
# respects the best practices for title tags, meta descriptions, H1, etc.

GLOBAL_GUIDELINES = {
    "title_tag": {
        "recommendation": "50-60 characters",
        "note": "Ensures title is not truncated in SERPs."
    },
    "meta_description": {
        "recommendation": "140-160 characters",
        "note": "Should be compelling, often includes location/phone."
    },
    "h1": {
        "recommendation": "up to 60-70 characters",
        "note": "Clear main topic, includes target keyword."
    },
    "paragraphs": "2-4 sentences, under 20 words each sentence if possible.",
    "keyword_density": "Aim for 1-2% for target keyword; do not stuff.",
    "alt_text": "Use descriptive alt text with local keyword if relevant.",
    "structured_data": "Use LocalBusiness/MedicalClinic or relevant schema.",
    "EAT": "Include credentials, disclaimers, authoritative citations if medical."
}

###########################################################
# 3. Page-Type Specific Default Structures
###########################################################
# We incorporate the new detailed guidelines for each page type.

PAGE_DEFAULT_STRUCTURES = {
    "Home": [
        {
            "key": "title_tag",
            "label": "Title Tag",
            "min_chars": 50,
            "max_chars": 60,
            "note": "e.g. 'Family Medicine in Austin | Austin Family Clinic'"
        },
        {
            "key": "meta_description",
            "label": "Meta Description",
            "min_chars": 140,
            "max_chars": 160,
            "note": "Should reference location if possible."
        },
        {
            "key": "h1",
            "label": "H1",
            "max_chars": 70,
            "note": "Clear main topic, includes target keyword."
        },
        {
            "key": "core_content",
            "label": "Core Content (Hero/Intro, Services Teaser, Local Trust Signals, CTA)",
            "min_words": 500,
            "max_words": 800,  # 500–800 words recommended
            "note": "Include short paragraphs, references to location, highlight services."
        },
        {
            "key": "footer",
            "label": "Footer + NAP",
            "note": "Include consistent Name, Address, Phone."
        }
    ],
    "About Us": [
        {
            "key": "title_tag",
            "label": "Title Tag",
            "min_chars": 50,
            "max_chars": 60,
            "note": "e.g. 'About Our Team | Austin Family Clinic'"
        },
        {
            "key": "meta_description",
            "label": "Meta Description",
            "min_chars": 140,
            "max_chars": 160,
        },
        {
            "key": "h1",
            "label": "H1",
            "max_chars": 70,
            "note": "Example: 'Meet the Austin Family Clinic Team'"
        },
        {
            "key": "about_core",
            "label": "Core Content (History, Mission, Bios, Community Involvement)",
            "min_words": 400,
            "max_words": 700,
            "note": "Cover team credentials, local references, E-A-T signals."
        },
        {
            "key": "footer",
            "label": "Footer + NAP",
        }
    ],
    "Service": [
        {
            "key": "title_tag",
            "label": "Title Tag",
            "min_chars": 50,
            "max_chars": 60,
            "note": "Format: '[Service] in [City] | [Practice Name]'"
        },
        {
            "key": "meta_description",
            "label": "Meta Description",
            "min_chars": 140,
            "max_chars": 160
        },
        {
            "key": "h1",
            "label": "H1",
            "max_chars": 70,
            "note": "Example: 'Comprehensive Dermatology Care in Austin'"
        },
        {
            "key": "service_core",
            "label": "Core Content (Service Overview, Conditions, Local Tie-Ins, CTA)",
            "min_words": 600,
            "max_words": 900,
            "note": "Describe procedures, staff expertise, local context."
        },
        {
            "key": "footer",
            "label": "Footer + NAP",
        }
    ],
    "Blog/Article": [
        {
            "key": "title_tag",
            "label": "Title Tag",
            "min_chars": 50,
            "max_chars": 60,
            "note": "e.g. 'Managing Allergies in Austin | Austin Family Clinic'"
        },
        {
            "key": "meta_description",
            "label": "Meta Description",
            "min_chars": 140,
            "max_chars": 160
        },
        {
            "key": "h1",
            "label": "H1",
            "max_chars": 70,
            "note": "Example: 'Seasonal Allergy Tips for Austin Residents'"
        },
        {
            "key": "blog_body",
            "label": "Body Content (Intro, Local Impact, Expert Advice, CTA)",
            "min_words": 800,
            "max_words": 1200,
            "note": "Include disclaimers, E-A-T elements, references to local environment."
        },
        {
            "key": "footer",
            "label": "Footer",
        }
    ],
    "Contact": [
        {
            "key": "title_tag",
            "label": "Title Tag",
            "min_chars": 50,
            "max_chars": 60,
            "note": "e.g. 'Contact Us | Austin Family Clinic'"
        },
        {
            "key": "meta_description",
            "label": "Meta Description",
            "min_chars": 140,
            "max_chars": 160
        },
        {
            "key": "h1",
            "label": "H1",
            "max_chars": 70,
            "note": "Example: 'Get in Touch with Austin Family Clinic'"
        },
        {
            "key": "contact_body",
            "label": "Core Content (Location, Hours, Directions, CTA)",
            "min_words": 200,
            "max_words": 400,
            "note": "Focus on how to reach or find the clinic, mention location & phone."
        },
        {
            "key": "footer",
            "label": "Footer + NAP",
        }
    ],
    "Other": [
        {
            "key": "title_tag",
            "label": "Title Tag",
            "min_chars": 50,
            "max_chars": 60
        },
        {
            "key": "meta_description",
            "label": "Meta Description",
            "min_chars": 140,
            "max_chars": 160
        },
        {
            "key": "h1",
            "label": "H1",
            "max_chars": 70
        },
        {
            "key": "other_body",
            "label": "Main Body Content",
            "min_words": 300,
            "max_words": 800
        },
        {
            "key": "footer",
            "label": "Footer + NAP",
        }
    ]
}

###########################################################
# 4. Flesch Reading Ease Function
###########################################################
def calculate_flesch_reading_ease(text: str) -> float:
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

###########################################################
# 5. Build Prompt for a Single Cohesive Output
###########################################################
def build_cohesive_prompt(data: dict) -> str:
    """
    Incorporates global guidelines, page-specific structure,
    and user-supplied details into a single prompt.
    """
    page_type = data.get("page_type", "Home")
    location = data.get("location", "")
    brand_tone = data.get("brand_tone", "Professional")
    primary_keywords = ", ".join(data.get("primary_keywords", []))
    secondary_keywords = ", ".join(data.get("secondary_keywords", []))
    page_specific_info = data.get("page_specific_info", {})
    structure = data.get("structure", [])

    # Global guidelines summary
    global_instructions = f"""
Global SEO/Medical Guidelines:
- Title Tag: {GLOBAL_GUIDELINES['title_tag']['recommendation']} 
- Meta Description: {GLOBAL_GUIDELINES['meta_description']['recommendation']}
- H1: {GLOBAL_GUIDELINES['h1']['recommendation']}
- Paragraphs: {GLOBAL_GUIDELINES['paragraphs']}
- Keyword Density: {GLOBAL_GUIDELINES['keyword_density']}
- Alt Text: {GLOBAL_GUIDELINES['alt_text']}
- Structured Data: {GLOBAL_GUIDELINES['structured_data']}
- E-A-T: {GLOBAL_GUIDELINES['EAT']}
"""

    prompt = (
        "You are an advanced SEO copywriter with strong local SEO and medical content awareness.\n\n"
        f"Page Type: {page_type}\n"
        f"Location: {location}\n"
        f"Tone/Style: {brand_tone}\n"
        f"Primary Keywords: {primary_keywords}\n"
        f"Secondary Keywords: {secondary_keywords}\n\n"
        "Additional Page-Specific Details:\n"
        f"{page_specific_info}\n\n"
        f"{global_instructions}\n"
        "Below is the recommended structure and constraints for this page type:\n"
    )

    # Summarize the sections for this page
    for sec in structure:
        label = sec.get("label", "Unnamed Section")
        constraints_str = []
        if "min_chars" in sec and "max_chars" in sec:
            constraints_str.append(f"{sec['min_chars']}-{sec['max_chars']} chars")
        elif "max_chars" in sec:
            constraints_str.append(f"up to {sec['max_chars']} chars")

        if "min_words" in sec and "max_words" in sec:
            constraints_str.append(f"{sec['min_words']}-{sec['max_words']} words")

        if "min_sentences" in sec and "max_sentences" in sec:
            constraints_str.append(f"{sec['min_sentences']}-{sec['max_sentences']} sentences")

        if constraints_str:
            joined = ", ".join(constraints_str)
            prompt += f"- {label}: {joined}\n"
        else:
            prompt += f"- {label}\n"
        note = sec.get("note", None)
        if note:
            prompt += f"  (Note: {note})\n"

    prompt += """
Please generate a **single cohesive piece of content** with appropriate headings (H1, H2, H3, etc.) 
but do **not** break it into disjoint sections for each bullet. Instead, unify them into a flowing 
page. Follow these guidelines:

1. Respect the recommended word/character limits where possible.
2. Use local SEO references naturally (mention city/region).
3. Use alt text placeholders for images, e.g. (alt="doctor with patient in Austin").
4. Insert at least one internal link placeholder, e.g., [Internal Link: /services].
5. Insert at least one external link placeholder, e.g., [External Link: https://example.com].
6. Include a short call-to-action referencing phone number or scheduling.
7. If relevant, mention how structured data or E-A-T disclaimers can be integrated.

Focus on clarity, readability (short paragraphs, short sentences), and medical credibility if appropriate.
Output should appear as a final draft of a webpage.

Now please create the final cohesive content accordingly.
"""

    return prompt

###########################################################
# 6. Generate Content via openai>=1.0.0
###########################################################
def generate_cohesive_content(data: dict) -> str:
    prompt = build_cohesive_prompt(data)
    try:
        # If you have GPT-4, you can specify model="gpt-4"
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating content:\n\n{e}"

###########################################################
# 7. Streamlit Main App
###########################################################
def main():
    st.title("Local SEO Content Generator (Multi-Page Medical Edition)")

    # 1) Page Type Selection
    page_type = st.selectbox(
        "Select Page Type",
        ["Home", "About Us", "Service", "Blog/Article", "Contact", "Other"]
    )

    # 2) Page-specific inputs
    page_specific_info = {}
    st.subheader(f"{page_type} Page Additional Details")
    if page_type == "Home":
        page_specific_info["hero_focus"] = st.text_input("What is the primary focus/USP on the homepage?")
        page_specific_info["services_overview"] = st.text_area("Brief list or overview of top services offered:")
    elif page_type == "About Us":
        page_specific_info["founding_story"] = st.text_area("Any historical/founding notes:")
        page_specific_info["team_highlights"] = st.text_input("Key staff credentials or unique achievements:")
    elif page_type == "Service":
        page_specific_info["service_name"] = st.text_input("Name of the service (e.g., Dermatology):")
        page_specific_info["service_benefits"] = st.text_area("Key selling points or benefits of this service:")
    elif page_type == "Blog/Article":
        page_specific_info["topic"] = st.text_input("Topic of the article (e.g., 'Managing Allergies in Austin'):")
        page_specific_info["author_credential"] = st.text_input("Name & credential of author (e.g., Dr. Smith, MD):")
    elif page_type == "Contact":
        page_specific_info["forms_of_contact"] = st.text_area("Any special instructions about phone, email, form, etc.:")
    else:
        page_specific_info["notes"] = st.text_area("Describe the purpose or content of this custom page:")

    # 3) Location / Tone
    st.subheader("Local & Branding Info")
    location = st.text_input("Location (City, State, Region)", "Austin, TX")
    brand_tone = st.selectbox("Brand Tone/Style", ["Professional", "Friendly", "Casual", "Technical", "Persuasive", "Other"])
    if brand_tone == "Other":
        brand_tone = st.text_input("Specify brand tone:", "Professional")

    # 4) Keywords
    st.subheader("Keywords")
    primary_kw_str = st.text_input("Primary Keywords (comma-separated)")
    secondary_kw_str = st.text_input("Secondary Keywords (comma-separated)")
    primary_keywords = [kw.strip() for kw in primary_kw_str.split(",") if kw.strip()]
    secondary_keywords = [kw.strip() for kw in secondary_kw_str.split(",") if kw.strip()]

    # 5) Simple vs. Advanced Mode
    st.subheader("Mode")
    mode = st.radio("Choose Mode", ["Simple (Default Constraints)", "Advanced (Override)"], index=0)

    # Load default structure for this page type
    default_structure = PAGE_DEFAULT_STRUCTURES.get(page_type, PAGE_DEFAULT_STRUCTURES["Other"])
    # Make a copy so we can override if advanced
    structure_for_page = []
    for sec in default_structure:
        structure_for_page.append(sec.copy())

    # 6) Advanced Overrides
    if mode == "Advanced (Override)":
        st.subheader("Advanced Field Overrides")
        for sec in structure_for_page:
            key = sec["key"]
            label = sec["label"]
            st.markdown(f"**{label}**")

            # If we see min_chars / max_chars
            if "min_chars" in sec:
                sec["min_chars"] = st.number_input(
                    f"{label} Min Characters",
                    min_value=1, value=sec["min_chars"],
                    key=f"{key}_min_chars"
                )
            if "max_chars" in sec:
                sec["max_chars"] = st.number_input(
                    f"{label} Max Characters",
                    min_value=1, value=sec["max_chars"],
                    key=f"{key}_max_chars"
                )
            # If we see min_words / max_words
            if "min_words" in sec:
                sec["min_words"] = st.number_input(
                    f"{label} Min Words",
                    min_value=1, value=sec["min_words"],
                    key=f"{key}_min_words"
                )
            if "max_words" in sec:
                sec["max_words"] = st.number_input(
                    f"{label} Max Words",
                    min_value=1, value=sec["max_words"],
                    key=f"{key}_max_words"
                )
            # If we see min_sentences / max_sentences
            if "min_sentences" in sec:
                sec["min_sentences"] = st.number_input(
                    f"{label} Min Sentences",
                    min_value=1, value=sec["min_sentences"],
                    key=f"{key}_min_sentences"
                )
            if "max_sentences" in sec:
                sec["max_sentences"] = st.number_input(
                    f"{label} Max Sentences",
                    min_value=1, value=sec["max_sentences"],
                    key=f"{key}_max_sentences"
                )

            st.write("---")

    # 7) Generate Button
    if st.button("Generate Content"):
        data = {
            "page_type": page_type,
            "location": location,
            "brand_tone": brand_tone,
            "primary_keywords": primary_keywords,
            "secondary_keywords": secondary_keywords,
            "page_specific_info": page_specific_info,
            "structure": structure_for_page
        }

        st.info("Generating your cohesive page content with local SEO guidelines. Please wait...")
        output_text = generate_cohesive_content(data)

        if "Error generating" in output_text:
            st.error(output_text)
        else:
            st.success("Content generated successfully!")
            st.write(output_text)

            # 8) Flesch Score
            flesch_score = calculate_flesch_reading_ease(output_text)
            st.write(f"**Flesch Reading Ease Score**: {flesch_score}")

            # Download
            st.download_button(
                "Download Content as TXT",
                data=output_text,
                file_name=f"{page_type}_content.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()
