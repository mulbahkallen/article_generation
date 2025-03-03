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
# =      PAGE BREAKDOWNS      =
# =============================
# Predefined field breakdowns for certain pages.
PAGE_BREAKDOWNS = {
    "Homepage": [
        "H1 [20-60 characters]",
        "Tagline [6-12 words]",
        "Intro Blurb [15-20 words]",
        "H2 [30-70 characters]",
        "Body 1 [3-5 sentences]",
        "H2-2 Services [30-70 characters]",
        "[Service collection]",
        "H2-3 [30-70 characters]",
        "Body 2 [3-5 sentences]",
        "H2-4 [About] [30-70 characters]",
        "Body 3 [3-5 sentences]"
    ],
    "Service Page": [
        "H1 [20-60 characters]",
        "Intro Blurb [15-20 words]",
        "H2 [30-70 characters]",
        "Body 1 [3-5 sentences]",
        "H2-2 [30-70 characters]",
        "Body 2 [3-5 sentences]",
        "H2-4 [About] [30-70 characters]",
        "Body 3 [3-5 sentences]"
    ]
}

def format_breakdown_list(breakdown_list) -> str:
    """
    Takes a list of field descriptions and formats them into multiline instructions.
    """
    if not breakdown_list:
        return ""
    instructions = ["Please structure the content with these fields and constraints:"]
    for i, field in enumerate(breakdown_list, start=1):
        instructions.append(f"{i}. {field}")
    instructions.append("Adhere to these length/word constraints as closely as possible.")
    return "\n".join(instructions)

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
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
            return content.strip()

        except RateLimitError:
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
    variation_num: int = 1,
    # Additional arguments for local SEO, E-E-A-T, and breakdown
    reinforce_eeat: bool = False,
    include_citations: bool = False,
    practice_location: str = "",
    practice_name: str = "",
    detailed_breakdown: bool = False,
    custom_breakdown_fields: List[str] = None
) -> str:
    """
    Constructs a user prompt for ChatGPT based on user inputs,
    including advanced SEO toggles and optional detailed CMS breakdown.
    """

    if custom_breakdown_fields is None:
        custom_breakdown_fields = []

    base_instructions = [
        f"Page Type: {page_type}",
        f"Desired Word Count: ~{word_count} words",
        f"Primary Keywords: {', '.join(keywords) if keywords else 'None'}",
        f"Tone of Voice: {tone_of_voice}",
        f"Writing Style: {writing_style}",
        "Include meta title and meta description." if meta_required else "No meta info needed.",
        "Include structured data markup suggestions." if structured_data else "No structured data suggestions needed."
    ]

    # Conditionals to handle E-E-A-T, citations, local SEO
    if reinforce_eeat:
        base_instructions.append(
            "Demonstrate strong E-E-A-T principles: provide expertise, authority, and trustworthiness in the content."
        )
    if include_citations:
        base_instructions.append(
            "Include references or citations to reputable sources (such as NIH, CDC, or other .gov/.edu sites) where appropriate."
        )
    if practice_location:
        base_instructions.append(
            f"Emphasize local SEO elements for the location: {practice_location}."
        )
    if practice_name:
        base_instructions.append(
            f"Reference or highlight the practice name: {practice_name}."
        )

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

    # Handling the breakdown instructions
    breakdown_instructions = ""
    if detailed_breakdown:
        if custom_breakdown_fields:
            # Use the user's custom breakdown
            breakdown_instructions = format_breakdown_list(custom_breakdown_fields)
        else:
            # Fall back to PAGE_BREAKDOWNS if user hasn't defined custom fields
            if page_type in PAGE_BREAKDOWNS:
                fallback = PAGE_BREAKDOWNS[page_type]
                breakdown_instructions = format_breakdown_list(fallback)
            else:
                breakdown_instructions = ""

        if breakdown_instructions:
            breakdown_instructions = "\n\n" + breakdown_instructions

    user_prompt = (
        f"Please produce a {page_type} with the following requirements:\n\n"
        f"{prompt_instructions}\n\n"
        f"{variation_text}"
        f"{custom_section}"
        f"{breakdown_instructions}\n\n"
        f"Ensure the final output is about {word_count} words in total. "
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
    if "generated_variations" not in st.session_state:
        st.session_state.generated_variations = []
    if "full_site_configs" not in st.session_state:
        st.session_state.full_site_configs = {}
    if "custom_breakdown" not in st.session_state:
        # st.session_state.custom_breakdown will be a dict: { page_type: [list of field lines], ... }
        st.session_state.custom_breakdown = {}

    # ------------------------------------------
    #   UPDATED: structured_breakdown_builder
    # ------------------------------------------
    def structured_breakdown_builder(page_key: str):
        """
        A more guided approach to building each breakdown field.
        The label is now a dropdown menu instead of a text input.
        """
        st.write(f"Custom Breakdown Fields for: {page_key}")
        if page_key not in st.session_state.custom_breakdown:
            st.session_state.custom_breakdown[page_key] = []

        # Display existing fields
        for idx, field_line in enumerate(st.session_state.custom_breakdown[page_key]):
            st.markdown(f"**Field {idx+1}**: {field_line}")
            remove_btn = st.button(f"Remove Field {idx+1}", key=f"cb_remove_{page_key}_{idx}")
            if remove_btn:
                st.session_state.custom_breakdown[page_key].pop(idx)
                st.experimental_rerun()

        # Drop-down options for label
        label_options = [
            "H1", "H2", "H3", "Tagline", "Intro Blurb", 
            "Body Section", "Call To Action", "FAQ", "Custom"
        ]

        with st.form(f"add_structured_field_{page_key}", clear_on_submit=True):
            st.subheader("Add a New Field")
            # Instead of text_input, we use a selectbox:
            selected_label = st.selectbox("Field Label", label_options, help="Choose a heading or section label.")
            # If 'Custom' is selected, we can allow free text:
            custom_label = ""
            if selected_label == "Custom":
                custom_label = st.text_input("Custom Label", help="Enter a unique heading if not in the list above")

            constraint_type = st.selectbox("Constraint Type", ["characters", "words", "sentences"])
            colA, colB = st.columns(2)
            with colA:
                min_val = st.number_input("Min Value", min_value=0, max_value=9999, value=1)
            with colB:
                max_val = st.number_input("Max Value", min_value=0, max_value=9999, value=3)

            additional_notes = st.text_area("Additional Notes (Optional)", help="Extra instructions or constraints")

            submitted_field = st.form_submit_button("Add Field to Breakdown")
            if submitted_field:
                # Determine which label to use
                final_label = custom_label.strip() if selected_label == "Custom" else selected_label
                
                if final_label:
                    notes_str = f" - {additional_notes.strip()}" if additional_notes.strip() else ""
                    line = f"{final_label} [{min_val}-{max_val} {constraint_type}]{notes_str}"
                    st.session_state.custom_breakdown[page_key].append(line)
                    st.success(f"Added new field: {line}")
                else:
                    st.warning("Please provide a valid label if 'Custom' was chosen.")

    # ------------------------------------------
    #        SINGLE-PAGE GENERATION MODE
    # ------------------------------------------
    if mode == "Single-Page Generation":
        st.subheader("Single-Page Content Generation")
        st.write(
            "Use this section to generate content for a single page type "
            "(e.g., a single blog post, a single service page, etc.)"
        )

        with st.expander("Advanced SEO & Local Settings", expanded=False):
            reinforce_eeat = st.checkbox("Reinforce E-E-A-T Guidelines?", value=False)
            include_citations = st.checkbox("Include References/Citations?", value=False)
            practice_location = st.text_input("Practice Location (City, State)", value="")
            practice_name = st.text_input("Practice/Doctor Name", value="")

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

        detailed_breakdown = st.checkbox("Use Detailed CMS Breakdown?", value=False)
        if detailed_breakdown:
            with st.expander("Build or Edit a Custom Breakdown", expanded=False):
                structured_breakdown_builder(page_type)

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

        content_placeholders = []
        for i in range(number_of_variations):
            content_placeholders.append(st.empty())

        if st.button("Generate Content"):
            with st.spinner("Generating content..."):
                custom_breakdown_list = st.session_state.custom_breakdown.get(page_type, [])
                user_prompt = generate_prompt(
                    page_type=page_type,
                    word_count=word_count,
                    keywords=keywords_list,
                    tone_of_voice=tone_of_voice,
                    writing_style=writing_style,
                    meta_required=meta_toggle,
                    structured_data=schema_toggle,
                    custom_template=custom_template,
                    variation_num=number_of_variations,
                    reinforce_eeat=reinforce_eeat,
                    include_citations=include_citations,
                    practice_location=practice_location,
                    practice_name=practice_name,
                    detailed_breakdown=detailed_breakdown,
                    custom_breakdown_fields=custom_breakdown_list
                )
                
                generated_text = generate_content_with_chatgpt(
                    api_key=user_api_key,
                    system_prompt=(
                        "You are an AI assistant specialized in writing SEO-friendly, medically oriented website content. "
                        "Adhere to Google's E-E-A-T guidelines and ensure factual accuracy."
                    ),
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=3000
                )
                
                if number_of_variations > 1:
                    variations = generated_text.split("Variation")
                    cleaned_variations = [v for v in variations if len(v.strip()) > 10]
                    if len(cleaned_variations) < number_of_variations:
                        st.warning("Could not parse multiple variations properly. Displaying raw text.")
                        cleaned_variations = [generated_text]
                else:
                    cleaned_variations = [generated_text]
                    
                st.session_state.generated_variations = cleaned_variations

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
        refine_input = st.text_area("Refinement Instructions", help="Provide instructions to improve or adjust the content.")
        if st.button("Refine"):
            with st.spinner("Refining..."):
                var_index = refine_variation_index - 1
                if var_index >= len(st.session_state.generated_variations):
                    st.warning("No content to refine. Please generate content first.")
                else:
                    content_to_refine = st.session_state.generated_variations[var_index]
                    refine_prompt = (
                        "Refine the following content based on these instructions.\n\n"
                        f"Original Content:\n{content_to_refine}\n\n"
                        f"Instructions:\n{refine_input}\n"
                        "Ensure the content remains SEO-friendly, accurate, and consistent with E-E-A-T."
                    )
                    refined_result = generate_content_with_chatgpt(
                        api_key=user_api_key,
                        system_prompt=(
                            "You are an AI assistant specialized in refining SEO-friendly, medically oriented text. "
                            "Focus on clarity, accuracy, and E-E-A-T principles."
                        ),
                        user_prompt=refine_prompt,
                        temperature=temperature,
                        max_tokens=3000
                    )
                    st.session_state.generated_variations[var_index] = refined_result
                    st.success("Refined content updated.")
                    st.write(refined_result)

        st.write("---")
        st.subheader("Export Results")
        export_variation_index = st.number_input(
            "Select Variation to Export",
            min_value=1, max_value=number_of_variations, value=1
        )
        export_format = st.selectbox("Export Format", ["HTML", "JSON", "Text"])

        if st.button("Export"):
            var_idx = export_variation_index - 1
            if var_idx >= len(st.session_state.generated_variations):
                st.warning("No variation found. Please generate content first.")
                return
            content_to_export = st.session_state.generated_variations[var_idx]

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

                reinforce_eeat_bulk = st.checkbox("Reinforce E-E-A-T Guidelines?", value=False)
                include_citations_bulk = st.checkbox("Include References/Citations?", value=False)
                practice_location_bulk = st.text_input("Practice Location (City, State)", value="")
                practice_name_bulk = st.text_input("Practice/Doctor Name", value="")

                detailed_breakdown_bulk = st.checkbox("Use Detailed CMS Breakdown?", value=False)
                if detailed_breakdown_bulk:
                    with st.expander("Build or Edit a Custom Breakdown", expanded=False):
                        structured_breakdown_builder(b_page_type)

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
                        "custom_template": b_custom_template,
                        "reinforce_eeat": reinforce_eeat_bulk,
                        "include_citations": include_citations_bulk,
                        "practice_location": practice_location_bulk,
                        "practice_name": practice_name_bulk,
                        "detailed_breakdown": detailed_breakdown_bulk
                    }
                    st.session_state.page_specs.append(new_spec)
                    st.success(f"Added a new {b_page_type} spec!")

        st.write("### Current Page Specifications for Bulk Generation:")
        if not st.session_state.page_specs:
            st.info("No page specifications added yet. Use the 'Add a New Page Specification' expander above.")
        else:
            for idx, spec in enumerate(st.session_state.page_specs):
                st.markdown(f"**Page {idx+1}**: `{spec['page_type']}` - ~{spec['word_count']} words")
                st.write(f"Keywords: {spec['keywords']}")
                st.write(f"Tone: {spec['tone_of_voice']} | Style: {spec['writing_style']}")
                st.write(f"Meta Required: {spec['meta_required']} | Schema: {spec['schema_toggle']}")
                if spec["reinforce_eeat"]:
                    st.write("E-E-A-T: On")
                if spec["include_citations"]:
                    st.write("Citations: On")
                if spec["practice_location"]:
                    st.write(f"Location: {spec['practice_location']}")
                if spec["practice_name"]:
                    st.write(f"Practice Name: {spec['practice_name']}")
                if spec["detailed_breakdown"]:
                    st.write("Detailed CMS Breakdown: On")

                if spec['custom_template']:
                    st.write(f"**Custom Template**: {spec['custom_template'][:60]}... (truncated)")

                remove_btn = st.button(f"Remove Page {idx+1}", key=f"remove_{idx}")
                if remove_btn:
                    st.session_state.page_specs.pop(idx)
                    st.experimental_rerun()

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
                            custom_breakdown_list = st.session_state.custom_breakdown.get(spec["page_type"], [])
                            user_prompt = generate_prompt(
                                page_type=spec["page_type"],
                                word_count=spec["word_count"],
                                keywords=spec["keywords"],
                                tone_of_voice=spec["tone_of_voice"],
                                writing_style=spec["writing_style"],
                                meta_required=spec["meta_required"],
                                structured_data=spec["schema_toggle"],
                                custom_template=spec["custom_template"],
                                variation_num=1,
                                reinforce_eeat=spec["reinforce_eeat"],
                                include_citations=spec["include_citations"],
                                practice_location=spec["practice_location"],
                                practice_name=spec["practice_name"],
                                detailed_breakdown=spec["detailed_breakdown"],
                                custom_breakdown_fields=custom_breakdown_list
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

        default_pages = ["Homepage", "About Us Page", "Service Page", "Blog Post", "Contact Page"]
        st.info(
            "Below is a typical set of website pages. Specify your details, then generate them all at once."
        )

        selected_pages = st.multiselect(
            "Select the pages to generate in this full website process:",
            default_pages,
            default=default_pages
        )

        st.write("Configure each selected page:")

        for pg_type in selected_pages:
            if pg_type not in st.session_state.full_site_configs:
                st.session_state.full_site_configs[pg_type] = {
                    "word_count": 600,
                    "keywords": [],
                    "tone_of_voice": "Professional",
                    "writing_style": "SEO-focused",
                    "meta_required": True,
                    "schema_toggle": True,
                    "custom_template": "",
                    "reinforce_eeat": False,
                    "include_citations": False,
                    "practice_location": "",
                    "practice_name": "",
                    "detailed_breakdown": False
                }

        for pg_type in selected_pages:
            with st.expander(f"Settings for {pg_type}", expanded=False):
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
                        index=0
                    )
                    config["meta_required"] = st.checkbox(f"{pg_type}: Generate Meta?", value=config["meta_required"])
                with col2:
                    config["writing_style"] = st.selectbox(
                        f"{pg_type}: Writing Style",
                        ["SEO-focused", "Storytelling", "Educational", "Conversion-driven", "Informative"],
                        index=0
                    )
                    config["schema_toggle"] = st.checkbox(f"{pg_type}: Include Schema?", value=config["schema_toggle"])
                
                config["reinforce_eeat"] = st.checkbox(
                    f"{pg_type}: Reinforce E-E-A-T?", value=config["reinforce_eeat"]
                )
                config["include_citations"] = st.checkbox(
                    f"{pg_type}: Include Citations?", value=config["include_citations"]
                )
                config["practice_location"] = st.text_input(
                    f"{pg_type}: Practice Location (City, State)",
                    value=config["practice_location"]
                )
                config["practice_name"] = st.text_input(
                    f"{pg_type}: Practice/Doctor Name",
                    value=config["practice_name"]
                )

                config["detailed_breakdown"] = st.checkbox(
                    f"{pg_type}: Use Detailed CMS Breakdown?",
                    value=config["detailed_breakdown"]
                )
                if config["detailed_breakdown"]:
                    with st.expander(f"Build or Edit Custom Breakdown for {pg_type}", expanded=False):
                        structured_breakdown_builder(pg_type)

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
                        custom_breakdown_list = st.session_state.custom_breakdown.get(pg_type, [])
                        user_prompt = generate_prompt(
                            page_type=pg_type,
                            word_count=cfg["word_count"],
                            keywords=cfg["keywords"],
                            tone_of_voice=cfg["tone_of_voice"],
                            writing_style=cfg["writing_style"],
                            meta_required=cfg["meta_required"],
                            structured_data=cfg["schema_toggle"],
                            custom_template=cfg["custom_template"],
                            variation_num=1,
                            reinforce_eeat=cfg["reinforce_eeat"],
                            include_citations=cfg["include_citations"],
                            practice_location=cfg["practice_location"],
                            practice_name=cfg["practice_name"],
                            detailed_breakdown=cfg["detailed_breakdown"],
                            custom_breakdown_fields=custom_breakdown_list
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
