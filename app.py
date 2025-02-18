import streamlit as st
import openai
import nltk

# Uncomment once to download the resources you need:
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

###############################################################
# 1. Configure OpenAI
###############################################################
openai.api_key = st.secrets["OPENAI_API_KEY"]  # or your method of storing API keys

###############################################################
# 2. Page-Specific Default Structures
###############################################################
# Each page type has recommended sections with constraints (chars, words).
# We incorporate the global best practices you specified.

PAGE_DEFAULT_STRUCTURES = {
    "Home": [
        {
            "key": "title_tag",
            "label": "SEO Title Tag",
            "min_chars": 50,
            "max_chars": 60,
            "note": "E.g.: 'Comprehensive [Healthcare/Service] in [City] | [Practice Name]'"
        },
        {
            "key": "meta_description",
            "label": "Meta Description",
            "min_chars": 140,
            "max_chars": 160,
            "note": "Include a quick mention of location & CTA if possible."
        },
        {
            "key": "h1",
            "label": "H1 (Main Heading)",
            "max_chars": 70,
            "note": "E.g. 'Welcome to [Practice Name]: Quality [Service] in [City]'"
        },
        {
            "key": "introduction",
            "label": "Introduction",
            "min_words": 50,
            "max_words": 100,
            "note": "Brief practice intro, location, main offerings (USP)."
        },
        {
            "key": "subheadings_core",
            "label": "Core Sections (Services, Why Choose Us, Testimonials, CTA)",
            "min_words": 300,
            "max_words": 600,
            "note": "Overall ~500–800 total words recommended for Home."
        },
        {
            "key": "footer",
            "label": "Footer + NAP",
            "note": "Include consistent Name, Address, Phone, local references."
        }
    ],
    "About Us": [
        {
            "key": "title_tag",
            "label": "SEO Title Tag",
            "min_chars": 50,
            "max_chars": 60,
            "note": "E.g.: 'About [Practice Name] | Serving [City] Since [Year]'"
        },
        {
            "key": "meta_description",
            "label": "Meta Description",
            "min_chars": 140,
            "max_chars": 160
        },
        {
            "key": "h1",
            "label": "H1 (Main Heading)",
            "max_chars": 70,
            "note": "E.g. 'Meet the Team Behind [Practice Name] in [City]'"
        },
        {
            "key": "history_intro",
            "label": "Intro / Practice History",
            "min_words": 50,
            "max_words": 100,
            "note": "Founding date, commitment to local community."
        },
        {
            "key": "subheadings_core",
            "label": "Core Sections (Mission & Values, Team Bios, Awards, CTA)",
            "min_words": 300,
            "max_words": 500,
            "note": "~400–700 total words recommended for About Us."
        },
        {
            "key": "footer",
            "label": "Footer + NAP",
        }
    ],
    "Blog/Article": [
        {
            "key": "title_tag",
            "label": "SEO Title Tag",
            "min_chars": 50,
            "max_chars": 60,
            "note": "E.g.: '[Topic/Keyword] in [City] | [Practice Name]'"
        },
        {
            "key": "meta_description",
            "label": "Meta Description",
            "min_chars": 140,
            "max_chars": 160
        },
        {
            "key": "h1",
            "label": "H1 (Main Heading)",
            "max_chars": 70,
            "note": "E.g. 'Understanding [Topic]: Insights from [Practice Name]'"
        },
        {
            "key": "introduction",
            "label": "Introduction",
            "min_words": 100,
            "max_words": 150,
            "note": "Introduce the topic & local relevance."
        },
        {
            "key": "subheadings_core",
            "label": "Main Content (Definition, Local Impact, Symptoms, FAQ, CTA)",
            "min_words": 600,
            "max_words": 1000,
            "note": "~800–1,200 total words recommended."
        },
        {
            "key": "conclusion",
            "label": "Conclusion & CTA",
            "min_words": 50,
            "max_words": 150
        },
        {
            "key": "footer",
            "label": "Footer",
        }
    ],
    "Service": [
        {
            "key": "title_tag",
            "label": "SEO Title Tag",
            "min_chars": 50,
            "max_chars": 60,
            "note": "E.g.: '[Service] in [City] | [Practice Name]'"
        },
        {
            "key": "meta_description",
            "label": "Meta Description",
            "min_chars": 140,
            "max_chars": 160
        },
        {
            "key": "h1",
            "label": "H1 (Main Heading)",
            "max_chars": 70,
            "note": "E.g. 'Expert [Service] for [City] Residents'"
        },
        {
            "key": "introduction",
            "label": "Introduction",
            "min_words": 50,
            "max_words": 100,
            "note": "Brief overview of the service & local presence."
        },
        {
            "key": "subheadings_core",
            "label": "Core Sections (What Is [Service], Candidate, Procedure, Benefits, Cost, CTA)",
            "min_words": 400,
            "max_words": 800,
            "note": "~600–900 total words recommended."
        },
        {
            "key": "footer",
            "label": "Footer + NAP",
        }
    ],
    "Other": [
        # A fallback with minimal structure
        {
            "key": "title_tag",
            "label": "SEO Title Tag",
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
            "label": "H1 (Main Heading)",
            "max_chars": 70
        },
        {
            "key": "body_content",
            "label": "Main Body Content",
            "min_words": 300,
            "max_words": 600
        },
        {
            "key": "footer",
            "label": "Footer + NAP"
        }
    ]
}

###############################################################
# 3. Flesch Reading Ease Calculation
###############################################################
def calculate_flesch_reading_ease(text: str) -> float:
    sentences = nltk.sent_tokenize(text)
    words = nltk.word_tokenize(text)

    if len(words) == 0 or len(sentences) == 0:
        return 0.0

    vowels = "aeiouAEIOU"
    syllable_count = 0
    for word in words:
        word_syllables = 0
        for i, char in enumerate(word):
            if char in vowels:
                # avoid double counting consecutive vowels
                if i == 0 or word[i-1] not in vowels:
                    word_syllables += 1
        if word_syllables == 0:
            word_syllables = 1
        syllable_count += word_syllables

    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllable_count / len(words)

    score = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
    return round(score, 2)

###############################################################
# 4. Build a Single Prompt Based on Page Type
###############################################################
def build_page_prompt(data: dict) -> str:
    page_type = data.get("page_type", "Home")
    location = data.get("location", "")
    practice_name = data.get("practice_name", "")
    brand_tone = data.get("brand_tone", "Professional")
    topic = data.get("topic", "")  # For Blog or Service or any custom usage
    primary_keywords = ", ".join(data.get("primary_keywords", []))
    secondary_keywords = ", ".join(data.get("secondary_keywords", []))
    user_notes = data.get("user_notes", "")
    structure = data.get("structure", [])

    # Summarize the structure
    structure_info = ""
    for sec in structure:
        label = sec.get("label", "Section")
        constraints = []
        if "min_chars" in sec and "max_chars" in sec:
            constraints.append(f"{sec['min_chars']}-{sec['max_chars']} chars")
        elif "max_chars" in sec:
            constraints.append(f"Up to {sec['max_chars']} chars")

        if "min_words" in sec and "max_words" in sec:
            constraints.append(f"{sec['min_words']}-{sec['max_words']} words")

        if constraints:
            joined_constr = ", ".join(constraints)
            structure_info += f"- {label}: {joined_constr}\n"
        else:
            structure_info += f"- {label}\n"
        if sec.get("note"):
            structure_info += f"  (Note: {sec['note']})\n"

    # Build prompt
    prompt = f"""
IMPORTANT: Do not mention AI or ChatGPT. Write as if authored by a professional.

Page Type: {page_type}
Location: {location}
Practice Name: {practice_name}
Tone/Style: {brand_tone}
Topic (if relevant): {topic}

Primary Keywords: {primary_keywords}
Secondary Keywords: {secondary_keywords}

User Notes:
{user_notes}

Desired Structure (Recommended):
{structure_info}

GLOBAL SEO REQUIREMENTS:
- Title Tag: 50–60 chars
- Meta Description: 140–160 chars
- H1: up to 60–70 chars
- Recommended Keyword Density: 1–2%
- Local Context: Reference city/region naturally
- E-A-T: Mention credentials or disclaimers if relevant
- Images/Alt Text: e.g. (alt="Procedure at {practice_name} in {location}")
- Schema: LocalBusiness or MedicalClinic if relevant; Article or BlogPosting for blog

INSTRUCTIONS:
1. Produce a single cohesive page (not separate bullet blocks).
2. Use headings (H1, H2, H3) as needed.
3. Insert at least one internal link placeholder [Internal Link: /another-page]
4. Insert at least one external link placeholder [External Link: https://example.com]
5. Include a short CTA referencing phone/address or scheduling, as appropriate.
6. Keep paragraphs short (2–4 sentences), mindful of keyword density.
7. If relevant, mention cost, coverage, or local environment as per the structure above.

Now please create the final SEO-optimized content for this {page_type} page accordingly.
"""
    return prompt.strip()

###############################################################
# 5. Generate Content with openai>=1.0.0
###############################################################
def generate_page_content(data: dict) -> str:
    prompt = build_page_prompt(data)
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4" if you have access
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
            temperature=0.7
        )
        text = response.choices[0].message.content
        return text.strip()
    except Exception as e:
        return f"Error generating content:\n\n{e}"

###############################################################
# 6. Streamlit App
###############################################################
def main():
    st.title("Multi-Page SEO Content Generator")

    # Page type selection
    page_type = st.selectbox(
        "Which Page Type?",
        ["Home", "About Us", "Service", "Blog/Article", "Other"]
    )
    st.write("Generates content with specific SEO structures for each page type.")

    # Common fields
    practice_name = st.text_input("Practice Name (e.g., 'Bright Smile Dentistry')", "")
    location = st.text_input("Location (City/State, e.g., 'Austin, TX')", "")
    topic = st.text_input("Topic (Optional, e.g., 'Do I Need Veneers?')", "")
    brand_tone = st.selectbox("Tone/Style", ["Professional", "Friendly", "Casual", "Technical", "Persuasive", "Other"])
    if brand_tone == "Other":
        brand_tone = st.text_input("Specify tone/style:", "Professional")

    st.subheader("Keywords")
    primary_kw_str = st.text_input("Primary Keywords (comma-separated)")
    secondary_kw_str = st.text_input("Secondary Keywords (comma-separated)")

    primary_keywords = [k.strip() for k in primary_kw_str.split(",") if k.strip()]
    secondary_keywords = [k.strip() for k in secondary_kw_str.split(",") if k.strip()]

    # Additional user notes
    user_notes = st.text_area("Any additional notes or instructions?")

    # Grab the default structure for the chosen page type
    default_structure = PAGE_DEFAULT_STRUCTURES.get(page_type, PAGE_DEFAULT_STRUCTURES["Other"])
    structure_for_page = [sec.copy() for sec in default_structure]

    # Mode: Simple vs. Advanced
    mode = st.radio("Mode", ["Simple (Default Constraints)", "Advanced (Override Constraints)"], index=0)

    if mode == "Advanced (Override Constraints)":
        st.subheader("Advanced Field Overrides")
        for sec in structure_for_page:
            label = sec["label"]
            key = sec["key"]
            st.markdown(f"**{label}**")

            if "min_chars" in sec:
                sec["min_chars"] = st.number_input(
                    f"{label} - Min Characters",
                    min_value=1,
                    value=sec["min_chars"],
                    key=f"{key}_min_chars"
                )
            if "max_chars" in sec:
                sec["max_chars"] = st.number_input(
                    f"{label} - Max Characters",
                    min_value=1,
                    value=sec["max_chars"],
                    key=f"{key}_max_chars"
                )
            if "min_words" in sec:
                sec["min_words"] = st.number_input(
                    f"{label} - Min Words",
                    min_value=1,
                    value=sec["min_words"],
                    key=f"{key}_min_words"
                )
            if "max_words" in sec:
                sec["max_words"] = st.number_input(
                    f"{label} - Max Words",
                    min_value=1,
                    value=sec["max_words"],
                    key=f"{key}_max_words"
                )
            st.divider()

    if st.button("Generate Content"):
        data = {
            "page_type": page_type,
            "practice_name": practice_name,
            "location": location,
            "topic": topic,
            "brand_tone": brand_tone,
            "primary_keywords": primary_keywords,
            "secondary_keywords": secondary_keywords,
            "user_notes": user_notes,
            "structure": structure_for_page
        }

        with st.spinner("Generating SEO-optimized content..."):
            output_text = generate_page_content(data)

        if output_text.startswith("Error generating"):
            st.error(output_text)
        else:
            st.success(f"{page_type} Page Content Generated Successfully!")
            # Optional final cleanup to remove AI references
            cleaned_text = output_text.replace("ChatGPT", "").replace("AI-generated", "").strip()
            st.write(cleaned_text)

            # Compute Flesch score
            readability_score = calculate_flesch_reading_ease(cleaned_text)
            st.write(f"**Flesch Reading Ease Score**: {readability_score}")

            # Download
            st.download_button(
                label="Download Content (TXT)",
                data=cleaned_text,
                file_name=f"{page_type}_optimized_content.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()
