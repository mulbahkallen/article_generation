import streamlit as st
import openai
import asyncio
import nltk

# -- If needed, download nltk data at runtime (uncomment if not already present) --
# nltk.download('punkt')

# ----------------------------------------------------------------------------
# 1. Set up your API key (assuming it's in Streamlit secrets)
# ----------------------------------------------------------------------------
openai_api_key = st.secrets["OPENAI_API_KEY"]
openai.api_key = openai_api_key

# ----------------------------------------------------------------------------
# 2. Default Field Requirements Dictionary
#    - Contains all the sections we want to generate for a homepage
#    - Each section has default constraints (min/max chars, words, sentences, etc.)
# ----------------------------------------------------------------------------
DEFAULT_FIELD_REQUIREMENTS = {
    "h1": {
        "min_chars": 20,
        "max_chars": 60,
        "label": "H1 Title"
    },
    "tagline": {
        "min_words": 6,
        "max_words": 12,
        "label": "Tagline (Short Phrase)"
    },
    "intro_blurb": {
        "min_words": 15,
        "max_words": 20,
        "label": "Intro Blurb/Welcome"
    },
    "h2_1": {
        "min_chars": 30,
        "max_chars": 70,
        "label": "H2-1 Title"
    },
    "body_1": {
        "min_sentences": 3,
        "max_sentences": 5,
        "label": "Body 1"
    },
    "h2_2_services": {
        "min_chars": 30,
        "max_chars": 70,
        "label": "H2-2 (Services)"
    },
    "service_collection": {
        "label": "Services Section",
        "description": "A short list or paragraphs describing services."
    },
    "h2_3": {
        "min_chars": 30,
        "max_chars": 70,
        "label": "H2-3 Title"
    },
    "body_2": {
        "min_sentences": 3,
        "max_sentences": 5,
        "label": "Body 2"
    },
    "h2_4_about": {
        "min_chars": 30,
        "max_chars": 70,
        "label": "H2-4 (About Us)"
    },
    "body_3": {
        "min_sentences": 3,
        "max_sentences": 5,
        "label": "Body 3"
    },
    "areas_we_serve": {
        "label": "Areas We Serve"
    },
    "reviews": {
        "label": "Reviews Section"
    },
    "contact_form": {
        "label": "Contact Form Placeholder"
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

# ----------------------------------------------------------------------------
# 3. Building a Structured Prompt from the Requirements
# ----------------------------------------------------------------------------
def build_homepage_prompt(data: dict) -> str:
    """
    Dynamically builds a prompt instructing the AI to generate 
    homepage content according to the constraints in 'field_requirements'.
    """
    field_reqs = data.get("field_requirements", DEFAULT_FIELD_REQUIREMENTS)
    
    primary_keywords = ', '.join(data.get('primary_keywords', []))
    secondary_keywords = ', '.join(data.get('secondary_keywords', []))
    
    prompt = (
        "You are an advanced SEO copywriter.\n"
        f"Primary Keywords: {primary_keywords}\n"
        f"Secondary Keywords: {secondary_keywords}\n\n"
        "Please create homepage content with these sections, following the indicated character/word/sentence constraints:\n\n"
    )
    
    #  -- H1 --
    prompt += f"1. H1: {field_reqs['h1']['min_chars']}-{field_reqs['h1']['max_chars']} characters.\n"
    #  -- Tagline --
    prompt += f"2. Tagline: {field_reqs['tagline']['min_words']}-{field_reqs['tagline']['max_words']} words.\n"
    #  -- Intro Blurb --
    prompt += f"3. Intro Blurb: {field_reqs['intro_blurb']['min_words']}-{field_reqs['intro_blurb']['max_words']} words.\n"
    #  -- H2-1 --
    prompt += f"4. H2-1: {field_reqs['h2_1']['min_chars']}-{field_reqs['h2_1']['max_chars']} characters.\n"
    #  -- Body 1 --
    prompt += f"5. Body 1: {field_reqs['body_1']['min_sentences']}-{field_reqs['body_1']['max_sentences']} sentences.\n"
    #  -- H2-2 (Services) --
    prompt += f"6. H2-2 (Services): {field_reqs['h2_2_services']['min_chars']}-{field_reqs['h2_2_services']['max_chars']} characters.\n"
    #  -- Service Collection --
    prompt += "7. Services Section (list or short paragraphs describing services).\n"
    #  -- H2-3 --
    prompt += f"8. H2-3: {field_reqs['h2_3']['min_chars']}-{field_reqs['h2_3']['max_chars']} characters.\n"
    #  -- Body 2 --
    prompt += f"9. Body 2: {field_reqs['body_2']['min_sentences']}-{field_reqs['body_2']['max_sentences']} sentences.\n"
    #  -- H2-4 (About) --
    prompt += f"10. H2-4 (About Us): {field_reqs['h2_4_about']['min_chars']}-{field_reqs['h2_4_about']['max_chars']} characters.\n"
    #  -- Body 3 --
    prompt += f"11. Body 3: {field_reqs['body_3']['min_sentences']}-{field_reqs['body_3']['max_sentences']} sentences.\n"
    #  -- Areas We Serve --
    prompt += "12. Areas We Serve.\n"
    #  -- Reviews --
    prompt += "13. Reviews Section.\n"
    #  -- Contact Form --
    prompt += "14. Contact Form Placeholder.\n"
    #  -- NAP --
    prompt += "15. Name, Address, Phone (NAP).\n"
    #  -- Footer --
    prompt += "16. Footer Section.\n"
    #  -- Title Tag --
    if "title_tag" in field_reqs:
        max_tt = field_reqs["title_tag"].get("max_chars", 60)
        prompt += f"17. Title Tag: up to {max_tt} characters.\n"
    else:
        prompt += "17. Title Tag.\n"
    #  -- Meta Description --
    if "meta_description" in field_reqs:
        max_md = field_reqs["meta_description"].get("max_chars", 160)
        prompt += f"18. Meta Description: up to {max_md} characters.\n"
    else:
        prompt += "18. Meta Description.\n"
    
    prompt += "\nAdditional SEO Requirements:\n"
    prompt += "- Insert alt text placeholders for images (e.g., alt='...').\n"
    prompt += "- Insert at least one internal link placeholder (e.g., [Internal Link: /page]).\n"
    prompt += "- Insert at least one external link placeholder (e.g., [External Link: https://example.com]).\n"
    prompt += "- Provide placeholders for structured data if relevant.\n"
    prompt += "- Maintain a professional tone.\n"
    prompt += "- Use keywords naturally.\n\n"
    prompt += "Please produce the final output labeled by each section in order.\n"
    
    return prompt

# ----------------------------------------------------------------------------
# 4. Async Function to Call OpenAI with the Prompt
# ----------------------------------------------------------------------------
async def async_generate_custom_homepage_content(data: dict) -> str:
    homepage_prompt = build_homepage_prompt(data)
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a highly skilled SEO copywriter."},
                {"role": "user", "content": homepage_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating homepage content: {e}"

def generate_custom_homepage_content(data: dict) -> str:
    """
    Synchronous wrapper for the asynchronous content generator.
    """
    return asyncio.run(async_generate_custom_homepage_content(data))

# ----------------------------------------------------------------------------
# 5. Flesch Reading Ease Function
# ----------------------------------------------------------------------------
def calculate_flesch_reading_ease(text: str) -> float:
    """
    Calculate the Flesch Reading Ease score for a given text.
    Higher score => easier to read. Typical range is 0-100+.
    """
    # Tokenize
    sentences = nltk.sent_tokenize(text)
    words = nltk.word_tokenize(text)
    
    # Count syllables (approximation: each vowel cluster counts as a syllable)
    vowels = "aeiouAEIOU"
    syllable_count = 0
    for word in words:
        word_syllables = 0
        for i, char in enumerate(word):
            if char in vowels:
                # Avoid double-counting vowel clusters
                if i == 0 or word[i-1] not in vowels:
                    word_syllables += 1
        if word_syllables == 0:
            word_syllables = 1
        syllable_count += word_syllables
    
    # Avoid division by zero
    if len(sentences) == 0 or len(words) == 0:
        return 0.0
    
    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllable_count / len(words)
    
    # Flesch Reading Ease formula
    score = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
    return round(score, 2)

# ----------------------------------------------------------------------------
# 6. Streamlit Main App with Simple/Advanced Mode
# ----------------------------------------------------------------------------
def main():
    st.title("Highly Customizable SEO Homepage Generator")

    # Let user pick a mode
    mode = st.radio("Mode", ["Simple", "Advanced"], index=0)

    # Common inputs
    primary_kw_str = st.text_input("Primary Keywords (comma-separated)", "")
    secondary_kw_str = st.text_input("Secondary Keywords (comma-separated)", "")

    # Convert them to lists
    primary_keywords = [kw.strip() for kw in primary_kw_str.split(",") if kw.strip()]
    secondary_keywords = [kw.strip() for kw in secondary_kw_str.split(",") if kw.strip()]

    # Make a copy of default field requirements
    field_requirements = {key: val.copy() for key, val in DEFAULT_FIELD_REQUIREMENTS.items()}

    if mode == "Advanced":
        st.subheader("Advanced Field Constraints")

        # Example: let user override H1 char limits
        field_requirements["h1"]["min_chars"] = st.number_input(
            "H1 Min Characters",
            min_value=1, max_value=100,
            value=field_requirements["h1"]["min_chars"]
        )
        field_requirements["h1"]["max_chars"] = st.number_input(
            "H1 Max Characters",
            min_value=1, max_value=200,
            value=field_requirements["h1"]["max_chars"]
        )

        # Example: let user override Tagline word limits
        field_requirements["tagline"]["min_words"] = st.number_input(
            "Tagline Min Words",
            min_value=1, max_value=50,
            value=field_requirements["tagline"]["min_words"]
        )
        field_requirements["tagline"]["max_words"] = st.number_input(
            "Tagline Max Words",
            min_value=1, max_value=100,
            value=field_requirements["tagline"]["max_words"]
        )

        # Similarly, you can add more overrides for H2, body sections, etc.
        # This is just an example to illustrate the approach.

    if st.button("Generate Homepage Content"):
        data = {
            "primary_keywords": primary_keywords,
            "secondary_keywords": secondary_keywords,
            "field_requirements": field_requirements
        }

        st.info("Generating content...")
        output_text = generate_custom_homepage_content(data)

        if output_text.startswith("Error"):
            st.error(output_text)
        else:
            st.success("Content generated!")
            st.write(output_text)

            # Calculate Flesch Reading Ease
            score = calculate_flesch_reading_ease(output_text)
            st.write(f"**Flesch Reading Ease Score**: {score}")

            # Download button
            st.download_button(
                label="Download Homepage Content",
                data=output_text,
                file_name="homepage_content.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()
