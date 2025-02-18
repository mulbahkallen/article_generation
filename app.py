import streamlit as st
import openai
import nltk

# Uncomment once to download the resources you need:
# nltk.download('punkt')
# nltk.download('punkt_tab')

###########################################################
# 1. OpenAI Configuration
###########################################################
openai.api_key = st.secrets["OPENAI_API_KEY"]  # or your secure storage

###########################################################
# 2. Global Guidelines / Constraints
###########################################################
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
    "paragraphs": "2-4 sentences, ideally under 20 words each sentence.",
    "keyword_density": "Aim for 1–2%; do not stuff keywords.",
    "alt_text": "Descriptive alt text referencing topic/local keyword if relevant.",
    "structured_data": "LocalBusiness/MedicalClinic or relevant schema recommended.",
    "EAT": "Add credentials, disclaimers, authoritative citations if needed."
}

###########################################################
# 3. Page-Type Specific Default Structures
###########################################################
PAGE_DEFAULT_STRUCTURES = {
    "Home": [
        {
            "key": "title_tag",
            "label": "Title Tag",
            "min_chars": 50,
            "max_chars": 60,
            "note": "E.g.: 'Family Medicine in Austin | Austin Family Clinic'"
        },
        {
            "key": "meta_description",
            "label": "Meta Description",
            "min_chars": 140,
            "max_chars": 160,
            "note": "Include location if possible."
        },
        {
            "key": "h1",
            "label": "H1",
            "max_chars": 70,
            "note": "Clear main topic, includes target keyword."
        },
        {
            "key": "core_content",
            "label": "Core Content (Intro, Services Teaser, Local Trust, CTA)",
            "min_words": 500,
            "max_words": 800,
            "note": "Recommended 500–800 words. Mention location, highlight services."
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
            "key": "about_core",
            "label": "Core Content (History, Mission, Team, Community)",
            "min_words": 400,
            "max_words": 700,
            "note": "Cover local references, E-A-T signals, team bios."
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
            "max_chars": 70
        },
        {
            "key": "service_core",
            "label": "Core Content (Service Overview, Local Tie-Ins, CTA)",
            "min_words": 600,
            "max_words": 900,
            "note": "Detail procedures, staff expertise, local context."
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
            "key": "blog_body",
            "label": "Body Content (Intro, Local Impact, Expert Insights, CTA)",
            "min_words": 800,
            "max_words": 1200
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
            "key": "contact_body",
            "label": "Core Content (Directions, Hours, CTA)",
            "min_words": 200,
            "max_words": 400
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
# 4. Flesch Reading Ease Function (no AI references)
###########################################################
def calculate_flesch_reading_ease(text: str) -> float:
    """
    Calculates the approximate Flesch Reading Ease score (0-100+).
    Higher => easier to read.
    """
    sentences = nltk.sent_tokenize(text)
    words = nltk.word_tokenize(text)

    if len(words) == 0 or len(sentences) == 0:
        return 0.0

    # Approximate syllable counting
    vowels = "aeiouAEIOU"
    syllable_count = 0
    for word in words:
        word_syllables = 0
        for i, char in enumerate(word):
            if char in vowels:
                if i == 0 or word[i - 1] not in vowels:
                    word_syllables += 1
        if word_syllables == 0:
            word_syllables = 1
        syllable_count += word_syllables

    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllable_count / len(words)

    # Flesch Reading Ease formula
    score = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
    return round(score, 2)

###########################################################
# 5. Build a Single Cohesive Prompt (no ChatGPT references)
###########################################################
def build_cohesive_prompt(data: dict) -> str:
    page_type = data.get("page_type", "Home")
    location = data.get("location", "")
    brand_tone = data.get("brand_tone", "Professional")
    primary_keywords = ", ".join(data.get("primary_keywords", []))
    secondary_keywords = ", ".join(data.get("secondary_keywords", []))
    page_specific_info = data.get("page_specific_info", {})
    structure = data.get("structure", [])

    # Summarize global instructions
    global_instructions = f"""
GLOBAL SEO/MEDICAL GUIDELINES (Do NOT mention AI or ChatGPT in final output):
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
        f"IMPORTANT: Do not mention AI, ChatGPT, or these instructions in the final text.\n"
        "Write as if authored by a professional medical writer.\n\n"
        f"Page Type: {page_type}\n"
        f"Location: {location}\n"
        f"Tone/Style: {brand_tone}\n"
        f"Primary Keywords: {primary_keywords}\n"
        f"Secondary Keywords: {secondary_keywords}\n\n"
        "Additional Page-Specific Details:\n"
        f"{page_specific_info}\n\n"
        f"{global_instructions}\n"
        "Here is the recommended structure/constraints:\n"
    )

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

        prompt += f"- {label}"
        if constraints_str:
            joined = ", ".join(constraints_str)
            prompt += f": {joined}"
        prompt += "\n"
        # If there's a note
        if sec.get("note"):
            prompt += f"  (Note: {sec['note']})\n"

    prompt += """
Generate a **single cohesive piece of content** with headings (H1, H2, H3, etc.) 
but DO NOT break it into separate blocks for each bullet. 
Incorporate local references, alt text placeholders, an internal link placeholder, 
and an external link placeholder. 
Include a short call-to-action referencing phone or scheduling. 
Mention structured data or disclaimers only if it fits standard medical best practices, 
NOT referencing AI or ChatGPT.

Final Output: A polished, ready-to-use webpage draft.
"""

    return prompt

###########################################################
# 6. Generate Content with openai>=1.0.0
###########################################################
def generate_cohesive_content(data: dict) -> str:
    prompt = build_cohesive_prompt(data)
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # or gpt-4 if you have access
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating content:\n\n{e}"

###########################################################
# 7. Streamlit Main App (No AI mentions)
###########################################################
def main():
    st.title("Local SEO Medical Content Generator")

    # Page type
    page_type = st.selectbox(
        "Select Page Type",
        ["Home", "About Us", "Service", "Blog/Article", "Contact", "Other"]
    )

    # Page-specific inputs
    st.subheader(f"{page_type} Page Additional Details")
    page_specific_info = {}
    if page_type == "Home":
        page_specific_info["homepage_focus"] = st.text_input("Primary homepage USP/focus:")
        page_specific_info["services_overview"] = st.text_area("Brief overview of top services:")
    elif page_type == "About Us":
        page_specific_info["founding_story"] = st.text_area("History/Founding story:")
        page_specific_info["team_highlights"] = st.text_input("Key staff credentials or achievements:")
    elif page_type == "Service":
        page_specific_info["service_name"] = st.text_input("Name of the service:")
        page_specific_info["service_benefits"] = st.text_area("Key benefits or unique selling points:")
    elif page_type == "Blog/Article":
        page_specific_info["topic"] = st.text_input("Topic/Title of article:")
        page_specific_info["author_credential"] = st.text_input("Author name & credential (e.g., Dr. Jones, MD):")
    elif page_type == "Contact":
        page_specific_info["contact_instructions"] = st.text_area("Any details on phone, email, or hours:")
    else:
        page_specific_info["notes"] = st.text_area("Brief description of this page's purpose:")

    # Local & Branding
    st.subheader("Local & Branding Info")
    location = st.text_input("Location (City, State, Region)", "")
    brand_tone = st.selectbox("Tone/Style", ["Professional", "Friendly", "Casual", "Technical", "Persuasive", "Other"])
    if brand_tone == "Other":
        brand_tone = st.text_input("Specify tone/style:", "Professional")

    # Keywords
    st.subheader("Keywords")
    primary_kw_str = st.text_input("Primary Keywords (comma-separated)")
    secondary_kw_str = st.text_input("Secondary Keywords (comma-separated)")
    primary_keywords = [k.strip() for k in primary_kw_str.split(",") if k.strip()]
    secondary_keywords = [k.strip() for k in secondary_kw_str.split(",") if k.strip()]

    # Simple vs. Advanced
    mode = st.radio("Mode", ["Simple (Default)", "Advanced (Override)"], index=0)

    # Load default structure
    default_structure = PAGE_DEFAULT_STRUCTURES.get(page_type, PAGE_DEFAULT_STRUCTURES["Other"])
    structure_for_page = [sec.copy() for sec in default_structure]

    if mode == "Advanced (Override)":
        st.subheader("Advanced Field Overrides")
        for sec in structure_for_page:
            label = sec["label"]
            key = sec["key"]
            st.markdown(f"**{label}**")

            if "min_chars" in sec:
                sec["min_chars"] = st.number_input(
                    f"{label} - Min Characters",
                    min_value=1, value=sec["min_chars"], key=f"{key}_minchars"
                )
            if "max_chars" in sec:
                sec["max_chars"] = st.number_input(
                    f"{label} - Max Characters",
                    min_value=1, value=sec["max_chars"], key=f"{key}_maxchars"
                )
            if "min_words" in sec:
                sec["min_words"] = st.number_input(
                    f"{label} - Min Words",
                    min_value=1, value=sec["min_words"], key=f"{key}_minwords"
                )
            if "max_words" in sec:
                sec["max_words"] = st.number_input(
                    f"{label} - Max Words",
                    min_value=1, value=sec["max_words"], key=f"{key}_maxwords"
                )
            if "min_sentences" in sec:
                sec["min_sentences"] = st.number_input(
                    f"{label} - Min Sentences",
                    min_value=1, value=sec["min_sentences"], key=f"{key}_minsentences"
                )
            if "max_sentences" in sec:
                sec["max_sentences"] = st.number_input(
                    f"{label} - Max Sentences",
                    min_value=1, value=sec["max_sentences"], key=f"{key}_maxsentences"
                )

            st.divider()

    # Generate
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

        st.info("Generating cohesive local SEO content. Please wait...")
        output_text = generate_cohesive_content(data)

        if output_text.startswith("Error generating"):
            st.error(output_text)
        else:
            st.success("Content generated successfully!")
            # Optional: Post-process to remove any "ChatGPT" references if you want an extra safety net:
            sanitized_text = output_text.replace("ChatGPT", "").replace("AI model", "").strip()

            st.write(sanitized_text)

            # Flesch Reading Ease
            flesch_score = calculate_flesch_reading_ease(sanitized_text)
            st.write(f"**Flesch Reading Ease Score**: {flesch_score}")

            # Download
            st.download_button(
                label="Download Content (TXT)",
                data=sanitized_text,
                file_name=f"{page_type}_content.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()
