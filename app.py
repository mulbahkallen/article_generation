import streamlit as st
import openai
import nltk

# Uncomment once to download the resources you need:
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

###############################################################
# 1. OpenAI Configuration
###############################################################
openai.api_key = st.secrets["OPENAI_API_KEY"]

###############################################################
# 2. Page-Specific Default Structures
###############################################################
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
            "note": "Quick mention of location & CTA if possible."
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
            "note": "~500–800 total words recommended for Home."
        },
        {
            "key": "footer",
            "label": "Footer + NAP",
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
        },
        {
            "key": "subheadings_core",
            "label": "Core Sections (Mission, Team Bios, Awards, CTA)",
            "min_words": 300,
            "max_words": 500,
            "note": "~400–700 total words recommended."
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
            "key": "introduction",
            "label": "Introduction",
            "min_words": 100,
            "max_words": 150,
        },
        {
            "key": "subheadings_core",
            "label": "Main Content (Definition, Local Impact, Symptoms, FAQ, CTA)",
            "min_words": 600,
            "max_words": 1000,
            "note": "~800–1,200 words recommended."
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
        },
        {
            "key": "subheadings_core",
            "label": "Core Sections (What Is [Service], Candidate, Benefits, Cost, CTA)",
            "min_words": 400,
            "max_words": 800,
            "note": "~600–900 words recommended."
        },
        {
            "key": "footer",
            "label": "Footer + NAP",
        }
    ],
    "Other": [
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
# 3. Flesch Reading Ease
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
                if i == 0 or word[i - 1] not in vowels:
                    word_syllables += 1
        if word_syllables == 0:
            word_syllables = 1
        syllable_count += word_syllables

    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllable_count / len(words)

    score = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
    return round(score, 2)

###############################################################
# 4. Build Prompt
###############################################################
def build_page_prompt(data: dict) -> str:
    """
    Incorporates global SEO instructions, page type structure,
    user-provided advanced detail, and specialized Q&A info
    to produce a cohesive prompt.
    """
    page_type = data.get("page_type", "Home")
    location = data.get("location", "")
    practice_name = data.get("practice_name", "")
    brand_tone = data.get("brand_tone", "Professional")
    primary_keywords = ", ".join(data.get("primary_keywords", []))
    secondary_keywords = ", ".join(data.get("secondary_keywords", []))
    user_notes = data.get("user_notes", "")
    structure = data.get("structure", [])
    
    # Additional specialized answers
    specialized_answers = data.get("specialized_answers", {})

    # Summarize structure
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

    # Build specialized Q&A lines
    specialized_info_lines = ""
    for question_label, answer in specialized_answers.items():
        specialized_info_lines += f"{question_label}: {answer}\n"

    prompt = f"""
IMPORTANT: Never mention AI or ChatGPT in final output. Write as if by a professional.

Page Type: {page_type}
Location: {location}
Practice Name: {practice_name}
Tone/Style: {brand_tone}
Primary Keywords: {primary_keywords}
Secondary Keywords: {secondary_keywords}
User Notes: {user_notes}

Specialized Q&A:
{specialized_info_lines}

Recommended Structure & Constraints:
{structure_info}

GLOBAL SEO REQUIREMENTS:
- Title Tag: 50–60 chars
- Meta Description: 140–160 chars
- H1: up to 60–70 chars
- Keyword Density: ~1–2%
- Local Context: Reference location (city/region) naturally
- E-A-T: If medical, mention credentials or disclaimers
- Include alt text placeholders, e.g. (alt="[procedure] at [practice name] in [location]")
- Provide at least one internal link placeholder: [Internal Link: /another-page]
- Provide at least one external link placeholder: [External Link: https://example.com]
- End with a short CTA referencing phone/address if relevant

Create a single cohesive page (NOT bullet points for each item) using headings (H1, H2, H3). 
Now produce the final optimized content for this {page_type} page accordingly, 
incorporating the specialized details above.
""".strip()
    return prompt

###############################################################
# 5. Generate Content
###############################################################
def generate_page_content(data: dict) -> str:
    prompt = build_page_prompt(data)
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4"
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
            temperature=0.7
        )
        text = response.choices[0].message.content
        return text.strip()
    except Exception as e:
        return f"Error generating content:\n\n{e}"

###############################################################
# 6. Streamlit Main
###############################################################
def main():
    st.title("SEO Content Generator with Page-Specific Follow-up Questions")

    # Page type selection
    page_type = st.selectbox(
        "Which Page Type?",
        ["Home", "About Us", "Service", "Blog/Article", "Other"]
    )

    st.write("Fill out the basic info, then provide page-specific details.")
    practice_name = st.text_input("Practice Name (e.g., 'Bright Smile Dentistry')", "")
    location = st.text_input("Location (City/State, e.g., 'Austin, TX')", "")
    brand_tone = st.selectbox("Tone/Style", ["Professional", "Friendly", "Casual", "Technical", "Persuasive", "Other"])
    if brand_tone == "Other":
        brand_tone = st.text_input("Specify tone/style:", "Professional")

    st.subheader("Keywords")
    primary_kw_str = st.text_input("Primary Keywords (comma-separated)")
    secondary_kw_str = st.text_input("Secondary Keywords (comma-separated)")
    primary_keywords = [k.strip() for k in primary_kw_str.split(",") if k.strip()]
    secondary_keywords = [k.strip() for k in secondary_kw_str.split(",") if k.strip()]

    user_notes = st.text_area("Any additional instructions or notes?", "")

    # Specialized follow-up questions based on page type
    st.subheader(f"Additional Questions for {page_type} Page")
    specialized_answers = {}

    if page_type == "Home":
        specialized_answers["Top Services"] = st.text_input("List your top 2–4 services (comma-separated) or key offerings:")
        specialized_answers["Unique Selling Points"] = st.text_area("What makes your practice unique? (e.g., advanced tech, friendly staff, local awards, etc.)")
        specialized_answers["Short Welcome Message"] = st.text_input("A brief welcome message you'd like to include:")
    elif page_type == "About Us":
        specialized_answers["Founding Year"] = st.text_input("In what year was the practice founded?")
        specialized_answers["Mission Statement"] = st.text_area("Briefly state your mission/values:")
        specialized_answers["Team Overview"] = st.text_area("Key team members or leadership (names, credentials, roles):")
        specialized_answers["Community Involvement"] = st.text_area("Any local events, charities, or sponsorships you participate in?")
    elif page_type == "Service":
        specialized_answers["Service Name/Brief"] = st.text_input("Short description or name of the service (e.g. 'Dental Implants'):")
        specialized_answers["Key Patient Concerns"] = st.text_area("Common patient concerns or problems this service addresses:")
        specialized_answers["Cost or Insurance"] = st.text_input("Approximate cost or mention of insurance coverage options:")
        specialized_answers["Unique Benefits"] = st.text_area("What are the main benefits or differentiators for this service?")
    elif page_type == "Blog/Article":
        specialized_answers["Topic Angle"] = st.text_input("What's the specific angle or focus of this article?")
        specialized_answers["Target Audience"] = st.text_input("Who is this blog intended for? (e.g., busy moms, seniors, health enthusiasts)")
        specialized_answers["Stats/Research"] = st.text_area("Any relevant statistics or reputable sources you'd like included?")
        specialized_answers["Disclaimer or E-A-T"] = st.text_area("Add disclaimers, author credentials, or E-A-T mentions if needed.")
    else:  # Other
        specialized_answers["Custom Info"] = st.text_area("Describe any details or context for this page type.")

    # Load default structure
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

    if st.button("Generate SEO Content"):
        data = {
            "page_type": page_type,
            "practice_name": practice_name,
            "location": location,
            "brand_tone": brand_tone,
            "primary_keywords": primary_keywords,
            "secondary_keywords": secondary_keywords,
            "user_notes": user_notes,
            "structure": structure_for_page,
            "specialized_answers": specialized_answers
        }

        with st.spinner("Generating your specialized content..."):
            output_text = generate_page_content(data)

        if output_text.startswith("Error generating"):
            st.error(output_text)
        else:
            st.success(f"{page_type} Content Generated Successfully!")
            # Clean up any AI references
            cleaned_text = (output_text
                            .replace("ChatGPT", "")
                            .replace("AI-generated", "")
                            .strip())
            st.write(cleaned_text)

            # Flesch Score
            flesch_score = calculate_flesch_reading_ease(cleaned_text)
            st.write(f"**Flesch Reading Ease Score:** {flesch_score}")

            st.download_button(
                label="Download Content (TXT)",
                data=cleaned_text,
                file_name=f"{page_type}_content.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()
