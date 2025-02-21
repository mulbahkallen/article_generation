import streamlit as st
import openai
import json
import time
from datetime import datetime
from typing import List, Dict

# Attempt to import the new exception classes; if not found, fallback to a generic exception.
try:
    from openai.error import OpenAIError, RateLimitError
except ImportError:
    OpenAIError = Exception
    class RateLimitError(OpenAIError):
        pass

# =============================
# =        CONFIG AREA        =
# =============================

st.set_page_config(
    page_title="AI-Powered Content Generator",
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
    model: str = "gpt-3.5-turbo",
    max_retries: int = 3
) -> str:
    """
    Calls openai.ChatCompletion.create with a retry mechanism for rate-limit errors.
    If 'insufficient_quota' is detected, shows a custom message about usage/plan and stops retrying.
    """
    openai.api_key = api_key

    for attempt in range(max_retries):
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
            content = response.choices[0].message.content  # <--- Updated here
            return content.strip()

        except RateLimitError as e:
            wait_time = 2 ** attempt
            st.warning(
                f"Rate limit error (attempt {attempt+1}/{max_retries}). "
                f"Retrying in {wait_time}s..."
            )
            time.sleep(wait_time)

        except OpenAIError as e:
            error_msg = str(e)
            if "insufficient_quota" in error_msg:
                st.error(
                    "**Insufficient quota**: It appears you have run out of credits or exceeded "
                    "your current plan’s usage. Please review your plan and billing details at:\n"
                    "• [Usage Dashboard](https://platform.openai.com/account/usage)\n"
                    "• [Billing Overview](https://platform.openai.com/account/billing/overview)\n\n"
                    "You’ll need to upgrade or add credits before trying again."
                )
                return ""
            else:
                st.error(f"OpenAI API Error (attempt {attempt+1}/{max_retries}): {error_msg}")
                if attempt == max_retries - 1:
                    return ""

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
    Constructs a user prompt to feed into ChatGPT based on user inputs.
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
    st.title("AI-Powered Content Generator")

    # ---------------------------------
    #      GET OPENAI API KEY
    # ---------------------------------
    st.sidebar.header("OpenAI API")
    user_api_key = st.sidebar.text_input("Enter your OpenAI API Key:", type="password")
    if not user_api_key:
        st.warning("Please enter your OpenAI API key to proceed.")
        st.stop()

    # ---------------------------------
    #    SELECT MODE / OBJECTIVE
    # ---------------------------------
    st.sidebar.header("What do you want to accomplish?")
    mode = st.sidebar.radio(
        "Choose an option:",
        ["Single-Page Generation", "Bulk Generation", "Full Website Generation"]
    )
    
    # Prepare session state for storing results or specs
    if "page_specs" not in st.session_state:
        st.session_state.page_specs = []

    # ------------------------------------------
    #        SINGLE-PAGE GENERATION MODE
    # ------------------------------------------
    if mode == "Single-Page Generation":
        st.subheader("Single-Page Content Generation")
        st.write(
            "Use this section to generate content for a single page type "
            "(e.g., a single blog post, a single service page, etc.)"
        )

        # Basic Controls
        page_type = st.selectbox(
            "Page Type",
            ["Homepage", "Service Page", "Blog Post", "About Us Page", "Product Page", "Other"]
        )
        word_count = st.slider(
            "Desired Word Count",
            min_value=200,
            max_value=3000,
            step=100,
            value=800
        )
        keywords_input = st.text_input("Primary Keywords (comma-separated)", value="")
        keywords_list = [kw.strip() for kw in keywords_input.split(",") if kw.strip()]

        tone_of_voice = st.selectbox(
            "Tone of Voice",
            ["Professional", "Casual", "Persuasive", "Technical", "Friendly", "Authoritative"]
        )
        writing_style = st.selectbox(
            "Writing Style",
            ["SEO-focused", "Storytelling", "Educational", "Conversion-driven", "Informative"]
        )
        
        meta_toggle = st.checkbox("Generate Meta Title & Description?", value=True)
        schema_toggle = st.checkbox("Include Structured Data Suggestions?", value=True)

        col1, col2 = st.columns(2)
        with col1:
            number_of_variations = st.number_input(
                "Number of Content Variations", min_value=1, max_value=5, value=1
            )
        with col2:
            temperature = st.slider("Creativity (temperature)", 0.0, 1.0, 0.7, 0.1)

        custom_template = st.text_area("Custom Template (Optional)")

        st.write("---")
        st.subheader("Generate Content Brief (Optional)")
        if st.button("Generate Content Brief"):
            if not keywords_list:
                st.warning("Please provide at least one keyword for the content brief.")
            else:
                brief = generate_meta_brief(user_api_key, page_type, keywords_list)
                st.write("**Content Brief**:")
                st.write(brief)

        st.write("---")
        st.subheader("Generate Page Content")

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
                
                generated_text = generate_content_with_chatgpt(
                    api_key=user_api_key,
                    system_prompt="You are an AI assistant specialized in writing SEO-friendly, medically oriented website content.",
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=3000
                )
                
                # Handle multiple variations if requested
                if number_of_variations > 1:
                    variations = generated_text.split("Variation")
                    cleaned_variations = [v for v in variations if len(v.strip()) > 10]
                    if len(cleaned_variations) < number_of_variations:
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
        st.subheader("Refine / Edit Content")
        refine_variation_index = st.number_input(
            "Select Variation to Refine (if multiple)",
            min_value=1, max_value=number_of_variations, value=1
        )
        refine_input = st.text_area(
            "Refinement Instructions",
            help="Provide instructions to improve or adjust the generated content."
        )
        if st.button("Refine"):
            with st.spinner("Refining..."):
                st.warning("Refinement demo placeholder. Retrieve & re-prompt with Variation content in a real app.")

        st.write("---")
        st.subheader("Export Results")
        export_variation_index = st.number_input(
            "Select Variation to Export",
            min_value=1, max_value=number_of_variations, value=1
        )

        # =========================
        #  ADDED TEXT OPTION HERE
        # =========================
        export_format = st.selectbox("Export Format", ["HTML", "JSON", "Text"])

        if st.button("Export"):
            # In a real scenario, you'd retrieve the chosen Variation's text from session state or a variable.
            content_to_export = "No content found. (In a real scenario, retrieve Variation text from session state.)"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"exported_content_{export_format.lower()}_{timestamp}"

            if export_format == "HTML":
                st.download_button(
                    "Download as HTML",
                    data=content_to_export,
                    file_name=filename + ".html",
                    mime="text/html"
                )
            elif export_format == "JSON":
                data_json = {"content": content_to_export}
                st.download_button(
                    "Download as JSON",
                    data=json.dumps(data_json, indent=2),
                    file_name=filename + ".json",
                    mime="application/json"
                )
            else:  # "Text" format
                st.download_button(
                    "Download as Text",
                    data=content_to_export,
                    file_name=filename + ".txt",
                    mime="text/plain"
                )

    # ------------------------------------------
    #        BULK GENERATION MODE
    # ------------------------------------------
    elif mode == "Bulk Generation":
        st.subheader("Bulk Generation (Multiple Pages)")
        st.write(
            "Use this section to add multiple page specifications and generate all of them at once. "
            "For example, multiple blog posts or multiple service pages."
        )

        # Add a new page specification
        with st.expander("Add a New Page Specification"):
            with st.form("add_page_spec_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    b_page_type = st.selectbox("Page Type", 
                        ["Homepage", "Service Page", "Blog Post", "About Us Page", "Product Page", "Other"])
                    b_word_count = st.slider("Word Count", 200, 3000, 800, step=100)
                    b_meta_required = st.checkbox("Generate Meta Title & Description?", value=True)
                    b_schema_toggle = st.checkbox("Include Structured Data Suggestions?", value=True)
                with col2:
                    b_keywords_input = st.text_input("Primary Keywords (comma-separated)", value="")
                    b_tone_of_voice = st.selectbox("Tone of Voice",
                        ["Professional", "Casual", "Persuasive", "Technical", "Friendly", "Authoritative"])
                    b_writing_style = st.selectbox("Writing Style",
                        ["SEO-focused", "Storytelling", "Educational", "Conversion-driven", "Informative"])
                    b_custom_template = st.text_area("Custom Template (Optional)")

                submitted = st.form_submit_button("Add Page Specification")
                if submitted:
                    b_keywords_list = [kw.strip() for kw in b_keywords_input.split(",") if kw.strip()]
                    new_spec = {
                        "page_type": b_page_type,
                        "word_count": b_word_count,
                        "keywords": b_keywords_list,
                        "tone_of_voice": b_tone_of_voice,
                        "writing_style": b_writing_style,
                        "meta_required": b_meta_required,
                        "schema_toggle": b_schema_toggle,
                        "custom_template": b_custom_template
                    }
                    st.session_state.page_specs.append(new_spec)
                    st.success(f"Added a new {b_page_type} spec!")

        # Display current page specs
        st.write("### Current Page Specifications for Bulk Generation:")
        if not st.session_state.page_specs:
            st.info("No page specifications added yet. Use the 'Add a New Page Specification' expander above.")
        else:
            for idx, spec in enumerate(st.session_state.page_specs):
                st.markdown(f"**Page {idx+1}**: `{spec['page_type']}` - ~{spec['word_count']} words")
                st.write(f"Keywords: {spec['keywords']}")
                st.write(f"Tone: {spec['tone_of_voice']} | Style: {spec['writing_style']}")
                st.write(f"Meta Required: {spec['meta_required']} | Schema: {spec['schema_toggle']}")
                if spec['custom_template']:
                    st.write(f"**Custom Template**: {spec['custom_template'][:60]}... (truncated)")
                remove_btn = st.button(f"Remove Page {idx+1}", key=f"remove_{idx}")
                if remove_btn:
                    st.session_state.page_specs.pop(idx)
                    #st.experimental_rerun()

            st.write("---")
            st.subheader("Generate All Bulk Pages")
            bulk_temp = st.slider("Creativity (temperature) for Bulk Generation", 0.0, 1.0, 0.7, 0.1)

            if st.button("Generate All Pages"):
                if not st.session_state.page_specs:
                    st.warning("No page specifications to process.")
                else:
                    st.write("## Bulk Generation Results")
                    for idx, spec in enumerate(st.session_state.page_specs):
                        with st.spinner(f"Generating Page {idx+1}: {spec['page_type']}..."):
                            user_prompt = generate_prompt(
                                page_type=spec["page_type"],
                                word_count=spec["word_count"],
                                keywords=spec["keywords"],
                                tone_of_voice=spec["tone_of_voice"],
                                writing_style=spec["writing_style"],
                                meta_required=spec["meta_required"],
                                structured_data=spec["schema_toggle"],
                                custom_template=spec["custom_template"]
                            )
                            bulk_generated_text = generate_content_with_chatgpt(
                                api_key=user_api_key,
                                system_prompt="You are an AI assistant specialized in writing SEO-friendly content.",
                                user_prompt=user_prompt,
                                temperature=bulk_temp,
                                max_tokens=3000
                            )
                            st.markdown(f"### Page {idx+1} Output ({spec['page_type']})")
                            st.write(bulk_generated_text)
                            st.write("---")

            st.write("---")
            st.subheader("Reset All Page Specifications")
            if st.button("Reset Specs"):
                st.session_state.page_specs = []
                st.success("All page specifications have been cleared.")


    # ------------------------------------------
    #     FULL WEBSITE GENERATION MODE
    # ------------------------------------------
    elif mode == "Full Website Generation":
        st.subheader("Full Website Generation")
        st.write(
            "This mode is intended for generating all the core pages of a website—e.g., Home Page, About Us, "
            "Service Pages, Blog posts, etc.—in one flow."
        )

        # Define default page types for a typical medical/healthcare site
        default_pages = ["Homepage", "About Us Page", "Service Page", "Blog Post", "Contact Page"]
        st.info(
            "Below is a typical set of website pages. Specify your details, then generate them all at once."
        )

        # Let the user pick which pages to generate
        selected_pages = st.multiselect(
            "Select the pages to generate in this full website process:",
            default_pages,
            default=default_pages
        )

        st.write("Configure each selected page:")
        # We can store a dictionary of page configs in session state
        if "full_site_configs" not in st.session_state:
            st.session_state.full_site_configs = {}

        # Create a form for each page type dynamically
        for pg_type in selected_pages:
            with st.expander(f"Settings for {pg_type}", expanded=False):
                if pg_type not in st.session_state.full_site_configs:
                    st.session_state.full_site_configs[pg_type] = {
                        "word_count": 600,
                        "keywords": [],
                        "tone_of_voice": "Professional",
                        "writing_style": "SEO-focused",
                        "meta_required": True,
                        "schema_toggle": True,
                        "custom_template": ""
                    }

                config = st.session_state.full_site_configs[pg_type]
                config["word_count"] = st.slider(f"{pg_type}: Word Count", 200, 3000, config["word_count"], step=100)
                kws_input = st.text_input(f"{pg_type}: Primary Keywords (comma-separated)",
                                          value=", ".join(config["keywords"]))
                config["keywords"] = [k.strip() for k in kws_input.split(",") if k.strip()]

                col1, col2 = st.columns(2)
                with col1:
                    config["tone_of_voice"] = st.selectbox(
                        f"{pg_type}: Tone of Voice",
                        ["Professional", "Casual", "Persuasive", "Technical", "Friendly", "Authoritative"],
                        index=0 if config["tone_of_voice"] == "Professional" else 1
                    )
                    config["meta_required"] = st.checkbox(f"{pg_type}: Generate Meta?", value=config["meta_required"])
                with col2:
                    config["writing_style"] = st.selectbox(
                        f"{pg_type}: Writing Style",
                        ["SEO-focused", "Storytelling", "Educational", "Conversion-driven", "Informative"],
                        index=0 if config["writing_style"] == "SEO-focused" else 1
                    )
                    config["schema_toggle"] = st.checkbox(f"{pg_type}: Include Schema?", value=config["schema_toggle"])
                
                config["custom_template"] = st.text_area(
                    f"{pg_type}: Custom Template (Optional)",
                    value=config["custom_template"]
                )

        st.write("---")
        st.subheader("Generate Full Website Content")
        full_site_temp = st.slider("Creativity (temperature)", 0.0, 1.0, 0.7, 0.1)
        if st.button("Generate All Selected Pages"):
            if not selected_pages:
                st.warning("Please select at least one page to generate.")
            else:
                st.write("## Full Website Generation Results")
                for pg_type in selected_pages:
                    cfg = st.session_state.full_site_configs[pg_type]
                    with st.spinner(f"Generating {pg_type}..."):
                        user_prompt = generate_prompt(
                            page_type=pg_type,
                            word_count=cfg["word_count"],
                            keywords=cfg["keywords"],
                            tone_of_voice=cfg["tone_of_voice"],
                            writing_style=cfg["writing_style"],
                            meta_required=cfg["meta_required"],
                            structured_data=cfg["schema_toggle"],
                            custom_template=cfg["custom_template"],
                            variation_num=1
                        )
                        site_gen_text = generate_content_with_chatgpt(
                            api_key=user_api_key,
                            system_prompt="You are an AI assistant specialized in writing SEO-friendly website content.",
                            user_prompt=user_prompt,
                            temperature=full_site_temp,
                            max_tokens=3000
                        )
                        st.markdown(f"### {pg_type} Output")
                        st.write(site_gen_text)
                        st.write("---")

        st.subheader("Clear Full Site Config")
        if st.button("Reset Full Site Config"):
            st.session_state.full_site_configs = {}
            st.success("Full site configuration cleared.")


if __name__ == "__main__":
    main()
