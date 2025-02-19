import streamlit as st
import openai
import nltk

# If needed to download these in your environment, uncomment:
# nltk.download('punkt')
# nltk.download('punkt_tab')

#####################################################################
# 1. Configure OpenAI
#####################################################################
openai.api_key = st.secrets["OPENAI_API_KEY"]

#####################################################################
# 2. Basic Page Structures (Minimal)
#####################################################################
# Each page type has a few recommended headings, but no strict constraints.

PAGE_TEMPLATES = {
    "Home": [
        "Title Tag (50–60 chars, recommended)",
        "Meta Description (140–160 chars, recommended)",
        "H1 (Main Heading)",
        "Introduction (short welcome, mention location, main services)",
        "Services/Offerings Overview",
        "Why Choose Us / Unique Selling Points",
        "Call to Action (Schedule, contact info)",
        "Footer / NAP (Name, Address, Phone)"
    ],
    "About Us": [
        "Title Tag (50–60 chars, recommended)",
        "Meta Description (140–160 chars, recommended)",
        "H1 (Main Heading)",
        "Introduction (History, founding year, local ties)",
        "Mission & Values",
        "Meet the Team / Key Staff Bios",
        "Community Involvement / Awards",
        "Call to Action",
        "Footer / NAP"
    ],
    "Service": [
        "Title Tag (50–60 chars, recommended)",
        "Meta Description (140–160 chars, recommended)",
        "H1 (Service Name + City)",
        "Introduction (brief overview of the service, local context)",
        "What Is [Service] & Who Needs It?",
        "Procedure Steps / Key Benefits",
        "Cost/Insurance/Financial Info",
        "Call to Action",
        "Footer / NAP"
    ],
    "Blog/Article": [
        "Title Tag (50–60 chars, recommended)",
        "Meta Description (140–160 chars, recommended)",
        "H1 (Main Blog/Article Heading)",
        "Introduction (explain topic, local relevance if any)",
        "Main Body (subheadings as needed: definition, local impact, pros/cons, FAQ)",
        "Conclusion (summary, CTA to practice)",
        "Footer"
    ],
    "Other": [
        "Title Tag",
        "Meta Description",
        "H1",
        "Main Content",
        "Call to Action",
        "Footer / NAP"
    ]
}

#####################################################################
# 3. Flesch Reading Ease (optional)
#####################################################################
def calculate_flesch_reading_ease(text: str) -> float:
    sentences = nltk.sent_tokenize(text)
    words = nltk.word_tokenize(text)

    if not sentences or not words:
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

#####################################################################
# 4. Build a Simplified Prompt
#####################################################################
def build_prompt(data: dict) -> str:
    page_type = data.get("page_type", "Home")
    practice_name = data.get("practice_name", "")
    location = data.get("location", "")
    brand_tone = data.get("brand_tone", "Professional")
    primary_keywords = data.get("primary_keywords", [])
    secondary_keywords = data.get("secondary_keywords", [])
    user_notes = data.get("user_notes", "")
    specialized_info = data.get("specialized_info", {})

    # Simple list of recommended headings for the chosen page type
    headings_list = PAGE_TEMPLATES.get(page_type, PAGE_TEMPLATES["Other"])
    bullet_points = "\n".join(f"- {item}" for item in headings_list)

    # Incorporate specialized answers
    specialized_lines = ""
    for question, answer in specialized_info.items():
        specialized_lines += f"{question}: {answer}\n"

    prompt = f"""
IMPORTANT: Do not mention AI or ChatGPT in the final text.
Write in a natural, human-like style, suitable for a healthcare practice or related field.

Page Type: {page_type}
Practice Name: {practice_name}
Location: {location}
Brand Tone: {brand_tone}

Primary Keywords: {', '.join(primary_keywords)}
Secondary Keywords: {', '.join(secondary_keywords)}

User Notes:
{user_notes}

Specialized Info:
{specialized_lines}

Please create a SINGLE cohesive piece of content, referencing these recommended sections:
{bullet_points}

Additional Guidelines:
- Title Tag ~50–60 characters, Meta Description ~140–160 characters (not strict).
- H1 references the main topic/keyword, possibly location.
- Use local context (city, region) if relevant.
- Include short paragraphs, one internal link placeholder ([Internal Link: /some-page]) 
  and one external link placeholder ([External Link: https://example.com]).
- Maintain brand tone: {brand_tone}.
- If medical context, consider E-A-T signals (credentials, disclaimers, etc.) 
- Provide a short CTA referencing phone/address or scheduling if appropriate.

Now produce the final text accordingly, in a natural, flowing style.
"""
    return prompt.strip()

#####################################################################
# 5. Generate Content with OpenAI
#####################################################################
def generate_content(data: dict) -> str:
    prompt = build_prompt(data)
    try:
        response = openai.chat.completions.create(
            model="gpt-4",  # or "gpt-4" if you have access
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating content:\n{e}"

#####################################################################
# 6. Streamlit Main
#####################################################################
def main():
    st.title("Simplified Multi-Page SEO Content Generator")

    # Basic info
    page_type = st.selectbox("Select Page Type", ["Home", "About Us", "Service", "Blog/Article", "Other"])
    practice_name = st.text_input("Practice Name (Optional, e.g., 'Bright Smile Dentistry')", "")
    location = st.text_input("Location (Optional, e.g., 'Austin, TX')", "")
    brand_tone = st.selectbox("Brand Tone/Style", ["Professional", "Friendly", "Casual", "Technical", "Persuasive", "Other"])
    if brand_tone == "Other":
        brand_tone = st.text_input("Please specify brand tone:", "Professional")

    st.subheader("Keywords (Optional)")
    primary_kw_str = st.text_input("Primary Keywords (comma-separated)", "")
    secondary_kw_str = st.text_input("Secondary Keywords (comma-separated)", "")

    primary_keywords = [kw.strip() for kw in primary_kw_str.split(",") if kw.strip()]
    secondary_keywords = [kw.strip() for kw in secondary_kw_str.split(",") if kw.strip()]

    # Page-specific Q&As (minimal approach)
    specialized_info = {}
    st.subheader(f"{page_type} Page: Additional Questions")
    if page_type == "Home":
        specialized_info["Top Services or Offerings"] = st.text_input("Top services/offerings? (Optional)")
        specialized_info["Welcome Message"] = st.text_area("Short welcome or tagline (Optional)")
    elif page_type == "About Us":
        specialized_info["Founding Year"] = st.text_input("Founding year? (Optional)")
        specialized_info["Mission Statement"] = st.text_area("Mission/values in brief? (Optional)")
    elif page_type == "Service":
        specialized_info["Service Description"] = st.text_area("Describe the service or procedure briefly (Optional)")
        specialized_info["Key Benefits"] = st.text_area("List main benefits or reasons patients might need it (Optional)")
    elif page_type == "Blog/Article":
        specialized_info["Article Topic Angle"] = st.text_input("What's the angle or focus? (Optional)")
        specialized_info["Target Audience"] = st.text_input("Who is this article meant for? (Optional)")
    else:
        specialized_info["Page Details"] = st.text_area("Any details about this page? (Optional)")

    user_notes = st.text_area("Any final instructions or notes? (Optional)")

    if st.button("Generate Content"):
        with st.spinner("Generating your content..."):
            data = {
                "page_type": page_type,
                "practice_name": practice_name,
                "location": location,
                "brand_tone": brand_tone,
                "primary_keywords": primary_keywords,
                "secondary_keywords": secondary_keywords,
                "user_notes": user_notes,
                "specialized_info": specialized_info
            }
            output_text = generate_content(data)

        if output_text.startswith("Error generating"):
            st.error(output_text)
        else:
            st.success(f"Content for {page_type} page generated!")
            sanitized = output_text.replace("ChatGPT", "").replace("AI-generated", "").strip()
            st.write(sanitized)

            # Optional readability check
            flesch_score = calculate_flesch_reading_ease(sanitized)
            st.write(f"**Flesch Reading Ease Score:** {flesch_score}")

            st.download_button(
                "Download as TXT",
                sanitized,
                file_name=f"{page_type}_content.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()
