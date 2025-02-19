import streamlit as st
import openai
import json
from datetime import datetime
from typing import List, Dict

# =============================
# =        CONFIG AREA        =
# =============================

# You can set up your own OPENAI_API_KEY in Streamlit Secrets or prompt the user to input it.
# For example, you can do: openai.api_key = st.secrets["OPENAI_API_KEY"]
# or ask the user to enter it in the UI.

# Uncomment this if you want to read from st.secrets:
# openai.api_key = st.secrets["OPENAI_API_KEY"]

# Set page config (optional)
st.set_page_config(
    page_title="AI Content Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================
# =      HELPER FUNCTIONS     =
# =============================

def generate_content_with_chatgpt(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    model: str = "gpt-4"
) -> str:
    """
    Calls OpenAI's ChatCompletion endpoint with provided prompts and returns the generated text.
    """
    openai.api_key = api_key

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        content = response.choices[0].message["content"]
        return content.strip()
    except Exception as e:
        st.error(f"OpenAI API Error: {e}")
        return ""


def generate_prompt(
    page_type: str,
    word_count: int,
    keywords: List[str],
    tone_of_voice: str,
    writing_style: str,
    meta_required: bool,
    structured_data: bool,
    custom_template: str = "",
    variation_num: int = 1
) -> str:
    """
    Constructs a user prompt to feed into the ChatGPT model based on user inputs.
    """
    base_instructions = [
        f"Page Type: {page_type}",
        f"Desired Word Count: ~{word_count} words",
        f"Primary Keywords: {', '.join(keywords) if keywords else 'None'}",
        f"Tone of Voice: {tone_of_voice}",
        f"Writing Style: {writing_style}",
        "Include meta title and meta description." if meta_required else "No meta info needed.",
        "Include structured data markup suggestions." if structured_data else "No structured data suggestions needed."
    ]
    
    prompt_instructions = "\n".join(base_instructions)
    
    # If the user has provided a custom template, incorporate it:
    if custom_template.strip():
        custom_section = (
            "\n\nCustom Template or Structure:\n" 
            + custom_template
        )
    else:
        custom_section = ""
    
    # Variation note:
    variation_text = f"Generate {variation_num} variations of the content.\n" if variation_num > 1 else ""
    
    # Combine everything
    user_prompt = (
        f"Please produce a {page_type} with the following requirements:\n\n"
        f"{prompt_instructions}\n\n"
        f"{variation_text}"
        f"{custom_section}\n\n"
        f"Ensure the final output is about {word_count} words. "
        f"Keep keywords natural and use best SEO practices."
    )
    return user_prompt


def generate_meta_brief(api_key: str, page_type: str, keywords: List[str]) -> str:
    """
    Generates a short content brief for planning the page (optional feature).
    """
    system_msg = "You are an assistant helping to create a concise but insightful content brief."
    user_msg = (
        f"Create a short content brief for a {page_type} page that targets these keywords: {', '.join(keywords)}. "
        "Include target audience, main goal, key points to cover, and any relevant local SEO elements."
    )
    return generate_content_with_chatgpt(api_key, system_msg, user_msg)


# =============================
# =       STREAMLIT APP       =
# =============================

def main():
    st.title("AI-Powered Content Generator for Medical/Healthcare Websites (Generic)")

    # 1. API Key Input
    st.sidebar.header("OpenAI API")
    user_api_key = st.sidebar.text_input("Enter your OpenAI API Key:", type="password")
    if not user_api_key:
        st.warning("Please enter your OpenAI API key to proceed.")
        st.stop()

    # 2. Basic Controls
    st.sidebar.header("Content Settings")
    page_type = st.sidebar.selectbox(
        "Page Type",
        ["Homepage", "Service Page", "Blog Post", "About Us Page", "Product Page", "Other"]
    )
    word_count = st.sidebar.slider(
        "Desired Word Count",
        min_value=200,
        max_value=3000,
        step=100,
        value=800
    )
    keywords_input = st.sidebar.text_input(
        "Primary Keywords (comma-separated)",
        value="healthcare, wellness"
    )
    keywords_list = [kw.strip() for kw in keywords_input.split(",") if kw.strip()]

    tone_of_voice = st.sidebar.selectbox(
        "Tone of Voice",
        ["Professional", "Casual", "Persuasive", "Technical", "Friendly", "Authoritative"]
    )
    writing_style = st.sidebar.selectbox(
        "Writing Style",
        ["SEO-focused", "Storytelling", "Educational", "Conversion-driven", "Informative"]
    )
    
    meta_toggle = st.sidebar.checkbox("Generate Meta Title & Description?", value=True)
    schema_toggle = st.sidebar.checkbox("Include Structured Data Suggestions?", value=True)
    
    # 3. Advanced / Additional
    st.sidebar.header("Advanced Options")
    number_of_variations = st.sidebar.number_input("Number of Content Variations", min_value=1, max_value=5, value=1)
    custom_template = st.sidebar.text_area(
        "Custom Template (Optional)",
        help="Define your own structure. E.g. Intro, 3 subheadings, CTA, etc."
    )
    temperature = st.sidebar.slider("Creativity (temperature)", 0.0, 1.0, 0.7, 0.1)
    
    # 4. Bulk Generation
    st.sidebar.header("Bulk Generation")
    bulk_pages_data = st.sidebar.text_area(
        "Bulk Pages (JSON List)",
        help="Enter a JSON list of objects, each with keys like: page_type, word_count, keywords, tone, style, etc."
    )

    st.write("---")
    st.subheader("1. Generate Content Brief (Optional)")
    if st.button("Generate Content Brief"):
        if not keywords_list:
            st.warning("Please provide at least one keyword for the content brief.")
        else:
            brief = generate_meta_brief(user_api_key, page_type, keywords_list)
            st.write("**Content Brief**:")
            st.write(brief)

    st.write("---")
    st.subheader("2. Generate Page Content")
    
    # Prepare placeholders to display the generated content
    content_placeholders = []
    for i in range(number_of_variations):
        content_placeholders.append(st.empty())
    
    if st.button("Generate Content"):
        with st.spinner("Generating content..."):
            # Build the user prompt
            user_prompt = generate_prompt(
                page_type=page_type,
                word_count=word_count,
                keywords=keywords_list,
                tone_of_voice=tone_of_voice,
                writing_style=writing_style,
                meta_required=meta_toggle,
                structured_data=schema_toggle,
                custom_template=custom_template,
                variation_num=number_of_variations
            )
            
            # We set a higher max_tokens to accommodate bigger generations
            generated_text = generate_content_with_chatgpt(
                api_key=user_api_key,
                system_prompt="You are an AI assistant specialized in writing SEO-friendly, medically oriented website content.",
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=3000  # adjust as needed
            )
            
            # If multiple variations are requested, we can attempt to parse them
            # ChatGPT typically won't provide them in strict JSON, but we can do a naive split by headings, for example.
            # Alternatively, instruct ChatGPT to output a clear separator like "=== Variation X ===".
            # For simplicity, here's a naive approach:
            if number_of_variations > 1:
                # Attempt splitting by "Variation" or some delimiter
                variations = generated_text.split("Variation")
                # The first chunk might be the introduction text; let's skip if it's not relevant
                cleaned_variations = [v for v in variations if len(v.strip()) > 10]
                
                if len(cleaned_variations) < number_of_variations:
                    # If splitting didn't work as expected, treat the entire text as single content
                    st.warning("Could not parse multiple variations properly. Displaying raw text.")
                    cleaned_variations = [generated_text]
            else:
                cleaned_variations = [generated_text]
                
            for i, placeholder in enumerate(content_placeholders):
                if i < len(cleaned_variations):
                    placeholder.markdown(f"**Variation {i+1}**\n\n" + cleaned_variations[i])
                else:
                    placeholder.markdown(f"**Variation {i+1}**\n\n(No content generated)")

    st.write("---")
    st.subheader("3. Refine / Edit Content")
    # For simplicity, let's let the user pick which variation they want to refine
    refine_variation_index = st.number_input(
        "Select Variation to Refine (if multiple)",
        min_value=1, max_value=number_of_variations, value=1
    )
    refine_input = st.text_area(
        "Refinement Instructions",
        help="Provide instructions to improve or adjust the generated content. For example: 'Make it more concise', 'Add a specific CTA', etc."
    )
    if st.button("Refine"):
        with st.spinner("Refining..."):
            refinement_prompt = (
                "Please refine the following content based on these instructions:\n\n"
                "Content:\n"
            )
            # We need the actual content from the placeholder
            # In practice, we'd store the content in a session state so we can retrieve it easily
            # For demonstration, let's assume the user copied the content into the text area or we store it in st.session_state
            # Here, we'll do a naive approach:
            st.warning("In a real app, you'd retrieve the Variation content from session state or a hidden input. For now, you might copy-paste the Variation text below.")
            # This is a placeholder approach:
            st.write("Refinement not fully implemented because we lack the original text in session state.")

    st.write("---")
    st.subheader("4. Export Results")

    # Let's let the user pick a Variation to export.
    export_variation_index = st.number_input(
        "Select Variation to Export",
        min_value=1, max_value=number_of_variations, value=1
    )
    export_format = st.selectbox("Export Format", ["HTML", "JSON"])

    if st.button("Export"):
        # Again, we'd retrieve the content from the actual stored variable or session state.
        # For demonstration, let's mock:
        content_to_export = "No content found. In a real scenario, retrieve the generated text from memory."

        # Create a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"exported_content_{export_format.lower()}_{timestamp}"

        if export_format == "HTML":
            st.download_button(
                "Download as HTML",
                data=content_to_export,
                file_name=filename + ".html",
                mime="text/html"
            )
        else:
            # JSON
            data_json = {"content": content_to_export}
            st.download_button(
                "Download as JSON",
                data=json.dumps(data_json, indent=2),
                file_name=filename + ".json",
                mime="application/json"
            )

    st.write("---")
    st.subheader("5. Bulk Generation")
    st.markdown("Use the JSON input in the sidebar to generate multiple pages at once.")

    if st.button("Process Bulk"):
        if not bulk_pages_data.strip():
            st.warning("No bulk pages data provided.")
        else:
            try:
                parsed_data = json.loads(bulk_pages_data)
                # Expecting a list of objects like:
                # [
                #   {
                #     "page_type": "Service Page",
                #     "word_count": 700,
                #     "keywords": ["urgent care", "emergency"],
                #     "tone_of_voice": "Professional",
                #     "writing_style": "SEO-focused",
                #     "meta_required": True,
                #     "schema_toggle": True
                #   },
                #   ...
                # ]
                for idx, item in enumerate(parsed_data):
                    st.markdown(f"### Bulk Item {idx+1}")
                    p_type = item.get("page_type", "Homepage")
                    w_count = item.get("word_count", 600)
                    kws = item.get("keywords", [])
                    tone = item.get("tone_of_voice", "Professional")
                    style = item.get("writing_style", "SEO-focused")
                    meta_req = item.get("meta_required", True)
                    schema_req = item.get("schema_toggle", True)
                    
                    user_prompt = generate_prompt(
                        page_type=p_type,
                        word_count=w_count,
                        keywords=kws,
                        tone_of_voice=tone,
                        writing_style=style,
                        meta_required=meta_req,
                        structured_data=schema_req
                    )
                    bulk_generated_text = generate_content_with_chatgpt(
                        api_key=user_api_key,
                        system_prompt="You are an AI assistant specialized in writing SEO-friendly content.",
                        user_prompt=user_prompt,
                        temperature=0.7,
                        max_tokens=2000
                    )
                    st.write(bulk_generated_text)
                    st.write("---")
            except json.JSONDecodeError as e:
                st.error("Invalid JSON format for bulk pages.")

if __name__ == "__main__":
    main()
