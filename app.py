import streamlit as st
import openai
import nltk

# -----------------------------------------------------
#  If you haven't downloaded NLTK tokenizers yet:
#  Uncomment and run once
# -----------------------------------------------------
# nltk.download('punkt')

# -----------------------------------------------------
# 1. Set your OpenAI API Key from Streamlit secrets
# -----------------------------------------------------
openai.api_key = st.secrets["OPENAI_API_KEY"]

# -----------------------------------------------------
# 2. Default Field Requirements:
#    For each section, we store possible constraints:
#    - min_chars, max_chars
#    - min_words, max_words
#    - min_sentences, max_sentences
#    Adjust as needed for your article/homepage structure.
# -----------------------------------------------------
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

# -----------------------------------------------------
# 3. Build the Prompt Dynamically Based on Requirements
# -----------------------------------------------------
def build_homepage_prompt(data: dict) -> str:
    """
    Dynamically builds a prompt instructing the AI to generate
    an article or homepage content with the user-specified constraints.
    """
    field_reqs = data.get("field_requirements", DEFAULT_FIELD_REQUIREMENTS)
    
    # Gather the user keywords
    primary_keywords = ', '.join(data.get('primary_keywords', []))
    secondary_keywords = ', '.join(data.get('secondary_keywords', []))

    prompt = (
        "You are an advanced SEO copywriter.\n"
        f"Primary Keywords: {primary_keywords}\n"
        f"Secondary Keywords: {secondary_keywords}\n\n"
        "Please create homepage/article content with these sections, following the indicated "
        "character/word/sentence constraints where provided:\n\n"
    )

    # Go in an order (for example, 1 to 18). Adjust the actual order to match your desired structure:
    section_order = [
        "h1", "tagline", "intro_blurb", "h2_1", "body_1",
        "h2_2_services", "service_collection",
        "h2_3", "body_2", "h2_4_about", "body_3",
        "areas_we_serve", "reviews", "contact_form",
        "nap", "footer", "title_tag", "meta_description"
    ]
    
    section_number = 1
    for section_key in section_order:
        if section_key not in field_reqs:
            continue  # Skip if not defined
        info = field_reqs[section_key]
        label = info.get("label", section_key)

        # Prepare a short line with constraints
        constraints_str = ""

        # Char constraints
        if "min_chars" in info and "max_chars" in info:
            constraints_str += f"{info['min_chars']}-{info['max_chars']} chars"
        elif "max_chars" in info:  # only max
            constraints_str += f"up to {info['max_chars']} chars"

        # Word constraints
        if "min_words" in info and "max_words" in info:
            if constraints_str:
                constraints_str += ", "
            constraints_str += f"{info['min_words']}-{info['max_words']} words"

        # Sentence constraints
        if "min_sentences" in info and "max_sentences" in info:
            if constraints_str:
                constraints_str += ", "
            constraints_str += f"{info['min_sentences']}-{info['max_sentences']} sentences"

        # Construct the prompt line
        if constraints_str:
            prompt += f"{section_number}. {label}: {constraints_str}\n"
        else:
            prompt += f"{section_number}. {label}.\n"

        section_number += 1

    # Additional instructions for SEO
    prompt += (
        "\nAdditional SEO Requirements:\n"
        "- Insert alt text placeholders for images (e.g., alt='...').\n"
        "- Insert at least one internal link placeholder (e.g., [Internal Link: /some-page]).\n"
        "- Insert at least one external link placeholder (e.g., [External Link: https://example.com]).\n"
        "- Provide placeholders for structured data if relevant.\n"
        "- Maintain a professional or relevant tone.\n"
        "- Use keywords naturally.\n\n"
        "Please produce the final output labeled by each section in order.\n"
    )

    return prompt

# -----------------------------------------------------
# 4. Generate Content with openai>=1.0.0 Interface
# -----------------------------------------------------
def generate_custom_homepage_content(data: dict) -> str:
    """
    Calls openai.ChatCompletion.create with the new interface (>=1.0.0).
    """
    prompt = build_homepage_prompt(data)

    try:
        # For GPT-4, the model name is just "gpt-4".
        # If you have access to GPT-4, you can use "gpt-4"; otherwise use "gpt-3.5-turbo", etc.
        response = openai.ChatCompletion.create(
            model="gpt-4",  # or "gpt-3.5-turbo"
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating homepage content:\n\n{e}"

# -----------------------------------------------------
# 5. Flesch Reading Ease Calculation
# -----------------------------------------------------
def calculate_flesch_reading_ease(text: str) -> float:
    """
    Rough calculation of the Flesch Reading Ease score (0-100+).
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

# -----------------------------------------------------
# 6. Streamlit Main App
# -----------------------------------------------------
def main():
    st.title("Highly Customizable SEO Content Generator")

    mode = st.radio("Mode", ["Simple", "Advanced"], index=0)
    st.write("Use **Simple** Mode for minimal inputs with default constraints, or **Advanced** to override all settings.")

    # Basic inputs
    primary_kw_str = st.text_input("Primary Keywords (comma-separated)", "")
    secondary_kw_str = st.text_input("Secondary Keywords (comma-separated)", "")

    # Convert to lists
    primary_keywords = [kw.strip() for kw in primary_kw_str.split(",") if kw.strip()]
    secondary_keywords = [kw.strip() for kw in secondary_kw_str.split(",") if kw.strip()]

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
            # Check if we have 'min_chars', 'max_chars'
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

            # Check if we have 'min_words', 'max_words'
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

            # Check if we have 'min_sentences', 'max_sentences'
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

            st.divider()  # a simple horizontal rule for visual separation

    if st.button("Generate Content"):
        # Build data dict
        data = {
            "primary_keywords": primary_keywords,
            "secondary_keywords": secondary_keywords,
            "field_requirements": field_requirements
        }

        st.info("Generating content, please wait...")
        output_text = generate_custom_homepage_content(data)

        if "Error generating" in output_text:
            st.error(output_text)
        else:
            st.success("Content Generated Successfully!")
            st.write(output_text)

            # Show the Flesch score for readability
            flesch_score = calculate_flesch_reading_ease(output_text)
            st.write(f"**Flesch Reading Ease Score**: {flesch_score}")

            # Provide a download button
            st.download_button(
                label="Download Content",
                data=output_text,
                file_name="custom_homepage_content.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()
