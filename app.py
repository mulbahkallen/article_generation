import streamlit as st
import openai
import json
import time
from datetime import datetime
from typing import List, Dict
from pathlib import Path

# Attempt to import the new exception classes; if not found, fallback to a generic exception.
try:
    from openai.error import OpenAIError, RateLimitError
except ImportError:
    OpenAIError = Exception
    class RateLimitError(OpenAIError):
        pass

# ==========================================================
# =               APP CONFIG / PAGE SETUP                  =
# ==========================================================
st.set_page_config(
    page_title="AI-Powered Content Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# =               TEMPLATE MANAGEMENT                      =
# ==========================================================
TEMPLATE_FILE = "templates.json"

def load_templates():
    """Load stored templates from a JSON file, if it exists."""
    if Path(TEMPLATE_FILE).exists():
        try:
            with open(TEMPLATE_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, dict) and "templates" in data:
                return data["templates"]
            elif isinstance(data, list):
                return data
        except:
            st.error("Template file is corrupted or unreadable. Starting with an empty template list.")
    return []

def save_templates(templates):
    """Save the templates to a JSON file."""
    try:
        with open(TEMPLATE_FILE, "w") as f:
            json.dump({"templates": templates}, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving templates: {e}")
        return False

# Initialize templates in session_state if not present
if "templates" not in st.session_state:
    st.session_state.templates = load_templates()


# ==========================================================
# =                PAGE/SECTION BREAKDOWNS                =
# ==========================================================
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
    # ... You can add more defaults if desired
}

def format_breakdown_list(breakdown_list) -> str:
    """Format the breakdown list into multiline instructions."""
    if not breakdown_list:
        return ""
    instructions = ["Structure the content with these fields:"]
    for i, field in enumerate(breakdown_list, start=1):
        instructions.append(f"{i}. {field}")
    instructions.append("Follow these length or word constraints as closely as possible, but do not mention them explicitly in the final text.")
    return "\n".join(instructions)


# ==========================================================
# =             OPENAI API CONTENT GENERATION             =
# ==========================================================
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
    Calls openai.ChatCompletion with a retry mechanism for rate-limit errors.
    If 'insufficient_quota' is detected, shows an error about usage/plan.
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
                    "**Insufficient quota**: You've run out of credits or exceeded "
                    "your current plan’s usage. Please review your plan/billing details."
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
    # Additional advanced toggles
    reinforce_eeat: bool = False,
    include_citations: bool = False,
    practice_location: str = "",
    practice_name: str = "",
    detailed_breakdown: bool = False,
    custom_breakdown_fields: List[str] = None
) -> str:
    """
    Constructs a user prompt for ChatGPT based on user inputs.
    *Important:* We do NOT want the final text to mention "SEO" or "local SEO."
    Instead, we instruct GPT behind the scenes to incorporate location/keywords subtly.
    """
    if custom_breakdown_fields is None:
        custom_breakdown_fields = []

    # Build a behind-the-scenes instruction list for system usage
    # but the final text must not contain phrases like "SEO," "local SEO," or "search engine."
    base_instructions = [
        f"Page Type: {page_type}",
        f"Approximate Word Count: ~{word_count} words",
        f"Primary Terms or Topics: {', '.join(keywords) if keywords else 'None'}",
        f"Tone of Voice: {tone_of_voice}",
        f"Style: {writing_style}",
        "Include a meta title and meta description if requested." if meta_required else "No meta info needed.",
        "Include structured data markup suggestions if requested." if structured_data else "No structured data suggestions needed.",
        "Do not explicitly mention SEO or local SEO in the final text."
    ]

    # Conditionals for E-E-A-T, references/citations, local emphasis
    if reinforce_eeat:
        base_instructions.append(
            "Demonstrate strong E-E-A-T principles: highlight expertise, authority, trustworthiness, and experience."
        )
    if include_citations:
        base_instructions.append(
            "Include reputable references or citations if relevant (NIH, CDC, .gov, .edu) but do not mention SEO."
        )
    if practice_location:
        base_instructions.append(
            f"Subtly reference the location: {practice_location}, but do not mention 'local SEO'."
        )
    if practice_name:
        base_instructions.append(
            f"Mention the practice name: {practice_name}, but do not mention 'SEO'."
        )

    # If user has a custom template, incorporate it
    if custom_template.strip():
        custom_section = (
            "\n\nCustom Template or Structure Provided:\n" 
            + custom_template
        )
    else:
        custom_section = ""

    # Variation note
    variation_text = f"Generate {variation_num} variations of the content.\n" if variation_num > 1 else ""

    # Detailed breakdown instructions
    breakdown_instructions = ""
    if detailed_breakdown:
        if custom_breakdown_fields:
            breakdown_instructions = format_breakdown_list(custom_breakdown_fields)
        else:
            if page_type in PAGE_BREAKDOWNS:
                fallback = PAGE_BREAKDOWNS[page_type]
                breakdown_instructions = format_breakdown_list(fallback)
            else:
                breakdown_instructions = ""
        if breakdown_instructions:
            breakdown_instructions = "\n\n" + breakdown_instructions

    # Combine user_prompt
    user_prompt = (
        "You are creating a piece of content for a medical or health-related website. "
        "The text should never explicitly mention 'SEO' or 'local SEO,' but it can include natural references to the location or relevant terms. "
        "Write the content so it is helpful, trustworthy, and consistent with medical E-E-A-T guidelines.\n\n"
        "Instructions:\n"
        f"{'\n'.join(base_instructions)}\n\n"
        f"{variation_text}"
        f"{custom_section}"
        f"{breakdown_instructions}\n\n"
        f"The final output should be ~{word_count} words in total. "
        "Use the given terms naturally and emphasize clarity, trust, and accuracy."
    )

    return user_prompt


def generate_meta_brief(api_key: str, page_type: str, keywords: List[str]) -> str:
    """
    Generates a short content brief for the user (not referencing SEO explicitly).
    Just a helpful overview for planning. 
    """
    system_msg = (
        "You are an assistant helping to create a concise content brief. "
        "Avoid mentioning 'SEO' or 'local SEO' explicitly. "
        "Focus on clarity and user perspective."
    )
    user_msg = (
        f"Create a short content brief for a {page_type} page that targets these terms: {', '.join(keywords)}. "
        "Include target audience, main goal, and any relevant local or brand elements without referencing SEO."
    )
    return generate_content_with_chatgpt(api_key, system_msg, user_msg)


# ==========================================================
# =                STREAMLIT APP MAIN LOGIC                =
# ==========================================================
def main():
    st.title("AI-Powered Content Generator for Medical Websites")

    # Sidebar: ask for OpenAI API Key
    st.sidebar.header("OpenAI API")
    user_api_key = st.sidebar.text_input("Enter your OpenAI API Key:", type="password")
    if not user_api_key:
        st.warning("Please enter your OpenAI API key to proceed.")
        st.stop()

    # Sidebar: Mode selection
    st.sidebar.header("Choose an Objective")
    mode = st.sidebar.radio(
        "Content Generation Mode:",
        ["Single-Page Generation", "Bulk Generation", "Full Website Generation"]
    )

    # Prepare session states
    if "page_specs" not in st.session_state:
        st.session_state.page_specs = []
    if "generated_variations" not in st.session_state:
        st.session_state.generated_variations = []
    if "full_site_configs" not in st.session_state:
        st.session_state.full_site_configs = {}
    if "custom_breakdown" not in st.session_state:
        st.session_state.custom_breakdown = {}  # e.g. { "Homepage": [list of field lines], ... }

    def structured_breakdown_builder(page_key: str):
        """
        A guided approach to building each breakdown field in a custom list.
        The user can choose from common labels or define their own, with constraints.
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

        label_options = [
            "H1", "H2", "H3", "Tagline", "Intro Blurb",
            "Body Section", "Call To Action", "FAQ", "Custom"
        ]

        with st.form(f"add_structured_field_{page_key}", clear_on_submit=True):
            st.subheader("Add a New Field")
            selected_label = st.selectbox("Field Label", label_options, help="Choose a heading or section label.")
            custom_label = ""
            if selected_label == "Custom":
                custom_label = st.text_input("Custom Label", help="Enter a unique heading if not in the list above")

            constraint_type = st.selectbox("Constraint Type", ["characters", "words", "sentences"])
            colA, colB = st.columns(2)
            with colA:
                min_val = st.number_input("Min Value", min_value=0, max_value=9999, value=1)
            with colB:
                max_val = st.number_input("Max Value", min_value=0, max_value=9999, value=3)

            additional_notes = st.text_area("Additional Notes (Optional)")

            submitted_field = st.form_submit_button("Add Field to Breakdown")
            if submitted_field:
                final_label = custom_label.strip() if selected_label == "Custom" else selected_label
                if final_label:
                    notes_str = f" - {additional_notes.strip()}" if additional_notes.strip() else ""
                    line = f"{final_label} [{min_val}-{max_val} {constraint_type}]{notes_str}"
                    st.session_state.custom_breakdown[page_key].append(line)
                    st.success(f"Added: {line}")
                else:
                    st.warning("Please provide a valid label if 'Custom' was chosen.")


    # -------------------------------------------------
    #  SINGLE-PAGE GENERATION MODE
    # -------------------------------------------------
    if mode == "Single-Page Generation":
        st.subheader("Single-Page Content Generation")
        st.write("Generate content for a single page (e.g., a single blog post or service page).")

        with st.expander("Advanced Settings (E-E-A-T, Citations, Local Mentions)", expanded=False):
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
        keywords_input = st.text_input("Focus Terms/Keywords (comma-separated)", value="")
        keywords_list = [kw.strip() for kw in keywords_input.split(",") if kw.strip()]

        tone_of_voice = st.selectbox(
            "Tone of Voice",
            ["Professional", "Casual", "Persuasive", "Technical", "Friendly", "Authoritative", "Compassionate"]
        )
        writing_style = st.selectbox(
            "Writing Style",
            ["Informative", "Storytelling", "Educational", "Conversion-driven", "Conversational"]
        )

        meta_toggle = st.checkbox("Generate Meta Title & Description?", value=True)
        schema_toggle = st.checkbox("Include Structured Data Suggestions?", value=True)

        detailed_breakdown = st.checkbox("Use Detailed CMS Breakdown?", value=False)
        if detailed_breakdown:
            with st.expander("Custom Breakdown Builder", expanded=False):
                structured_breakdown_builder(page_type)

        col1, col2 = st.columns(2)
        with col1:
            number_of_variations = st.number_input(
                "Number of Content Variations",
                min_value=1, max_value=5, value=1
            )
        with col2:
            temperature = st.slider("Creativity (temperature)", 0.0, 1.0, 0.7, 0.1)

        custom_template = st.text_area("Custom Template (Optional)")

        st.write("---")
        st.subheader("Generate Optional Brief")
        if st.button("Generate Content Brief"):
            if not keywords_list:
                st.warning("Please provide at least one focus term/keyword for the brief.")
            else:
                brief = generate_meta_brief(user_api_key, page_type, keywords_list)
                st.write("**Content Brief**:")
                st.write(brief)

        st.write("---")
        st.subheader("Generate Page Content")

        content_placeholders = [st.empty() for _ in range(number_of_variations)]

        if st.button("Generate Content"):
            with st.spinner("Generating..."):
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

                system_prompt = (
                    "You are an AI assistant specialized in writing medically oriented, user-friendly web content. "
                    "Adhere to E-E-A-T guidelines (experience, expertise, authority, trustworthiness). "
                    "Never explicitly mention 'SEO,' 'search engine,' or 'local SEO' in your final text. "
                    "Incorporate references to location or terms naturally if provided, but keep it patient-/reader-focused."
                )

                generated_text = generate_content_with_chatgpt(
                    api_key=user_api_key,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=3000
                )

                if number_of_variations > 1:
                    # Split variations heuristically
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
                        placeholder.markdown(f"**Variation {i+1}**\n\n{cleaned_variations[i]}")
                    else:
                        placeholder.markdown(f"**Variation {i+1}**\n\n(No content generated)")

        st.write("---")
        st.subheader("Refine / Edit Content")
        refine_variation_index = st.number_input("Select Variation to Refine", 1, number_of_variations, value=1)
        refine_input = st.text_area("Refinement Instructions", help="Instructions to improve or adjust the content. No SEO references.")
        if st.button("Refine"):
            var_index = refine_variation_index - 1
            if var_index >= len(st.session_state.generated_variations):
                st.warning("No content to refine. Please generate content first.")
            else:
                with st.spinner("Refining..."):
                    content_to_refine = st.session_state.generated_variations[var_index]
                    refine_prompt = (
                        "Refine the following content based on the instructions below. "
                        "Do not mention SEO or local SEO. Keep it user-friendly and medically accurate.\n\n"
                        f"Original Content:\n{content_to_refine}\n\n"
                        f"Instructions:\n{refine_input}\n"
                    )
                    refined_result = generate_content_with_chatgpt(
                        api_key=user_api_key,
                        system_prompt=(
                            "You are an AI specialized in refining medically oriented, user-friendly text. "
                            "Adhere to E-E-A-T and do not mention SEO explicitly."
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
        export_variation_index = st.number_input("Select Variation to Export", 1, number_of_variations, 1)
        export_format = st.selectbox("Export Format", ["HTML", "JSON", "Text"])

        if st.button("Export"):
            var_idx = export_variation_index - 1
            if var_idx >= len(st.session_state.generated_variations):
                st.warning("No variation found. Generate content first.")
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
            else:  # "Text"
                st.download_button(
                    "Download as Text",
                    data=content_to_export,
                    file_name=filename + ".txt",
                    mime="text/plain"
                )


    # -------------------------------------------------
    #  BULK GENERATION MODE
    # -------------------------------------------------
    elif mode == "Bulk Generation":
        st.subheader("Bulk Page Generation")
        st.write("Add multiple page specs and generate them all at once (e.g., multiple service pages).")

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
                    b_keywords_input = st.text_input("Focus Terms (comma-separated)", value="")
                    b_tone_of_voice = st.selectbox("Tone of Voice",
                        ["Professional", "Casual", "Persuasive", "Technical", "Friendly", "Authoritative", "Compassionate"])
                    b_writing_style = st.selectbox("Writing Style",
                        ["Informative", "Storytelling", "Educational", "Conversion-driven", "Conversational"])
                    b_custom_template = st.text_area("Custom Template (Optional)")

                reinforce_eeat_bulk = st.checkbox("Reinforce E-E-A-T?", value=False)
                include_citations_bulk = st.checkbox("Include Citations?", value=False)
                practice_location_bulk = st.text_input("Practice Location (City, State)", value="")
                practice_name_bulk = st.text_input("Practice/Doctor Name", value="")

                detailed_breakdown_bulk = st.checkbox("Use Detailed Breakdown?", value=False)
                if detailed_breakdown_bulk:
                    with st.expander("Custom Breakdown Builder", expanded=False):
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

        st.write("### Current Page Specifications")
        if not st.session_state.page_specs:
            st.info("No specs added yet. Use the 'Add a New Page Specification' expander above.")
        else:
            for idx, spec in enumerate(st.session_state.page_specs):
                st.markdown(f"**Spec {idx+1}**: `{spec['page_type']}` ~{spec['word_count']} words")
                st.write(f"Focus Terms: {spec['keywords']}")
                st.write(f"Tone: {spec['tone_of_voice']} | Style: {spec['writing_style']}")
                st.write(f"Meta? {spec['meta_required']} | Schema? {spec['schema_toggle']}")
                if spec["reinforce_eeat"]:
                    st.write("E-E-A-T: On")
                if spec["include_citations"]:
                    st.write("Citations: On")
                if spec["practice_location"]:
                    st.write(f"Location: {spec['practice_location']}")
                if spec["practice_name"]:
                    st.write(f"Practice Name: {spec['practice_name']}")
                if spec["detailed_breakdown"]:
                    st.write("Detailed Breakdown: On")

                if spec['custom_template']:
                    st.write(f"**Custom Template**: {spec['custom_template'][:60]}...")

                remove_btn = st.button(f"Remove Spec {idx+1}", key=f"remove_{idx}")
                if remove_btn:
                    st.session_state.page_specs.pop(idx)
                    st.experimental_rerun()

            st.write("---")
            st.subheader("Generate All Bulk Pages")
            bulk_temp = st.slider("Creativity (temperature)", 0.0, 1.0, 0.7, 0.1)

            if st.button("Generate All Pages"):
                if not st.session_state.page_specs:
                    st.warning("No specs to process.")
                else:
                    st.write("## Bulk Generation Results")
                    for idx, spec in enumerate(st.session_state.page_specs):
                        with st.spinner(f"Generating Spec {idx+1}: {spec['page_type']}..."):
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
                            system_prompt = (
                                "You are an AI assistant specialized in writing medically oriented, user-friendly web content. "
                                "Follow E-E-A-T principles. Do not mention 'SEO' or 'local SEO' in the final text."
                            )
                            bulk_generated_text = generate_content_with_chatgpt(
                                api_key=user_api_key,
                                system_prompt=system_prompt,
                                user_prompt=user_prompt,
                                temperature=bulk_temp,
                                max_tokens=3000
                            )
                            st.markdown(f"### Page {idx+1} Output ({spec['page_type']})")
                            st.write(bulk_generated_text)
                            st.write("---")

            st.write("---")
            st.subheader("Reset All Specs")
            if st.button("Reset Specs"):
                st.session_state.page_specs = []
                st.success("Cleared all specs.")

    # -------------------------------------------------
    #  FULL WEBSITE GENERATION MODE
    # -------------------------------------------------
    elif mode == "Full Website Generation":
        st.subheader("Full Website Generation")
        st.write(
            "Generate all core pages of a website in one flow (Home, About, Service Pages, etc.). "
            "Configure each page and produce them together."
        )

        default_pages = ["Homepage", "About Us Page", "Service Page", "Blog Post", "Contact Page"]
        st.info("Select the pages you want to generate and configure each.")
        selected_pages = st.multiselect(
            "Pages to generate for this site:",
            default_pages,
            default=default_pages
        )

        if "full_site_configs" not in st.session_state:
            st.session_state.full_site_configs = {}

        for pg_type in selected_pages:
            if pg_type not in st.session_state.full_site_configs:
                st.session_state.full_site_configs[pg_type] = {
                    "word_count": 600,
                    "keywords": [],
                    "tone_of_voice": "Professional",
                    "writing_style": "Informative",
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
            with st.expander(f"{pg_type} Settings", expanded=False):
                cfg = st.session_state.full_site_configs[pg_type]
                cfg["word_count"] = st.slider(f"{pg_type}: Word Count", 200, 3000, cfg["word_count"], step=100)
                kws_input = st.text_input(f"{pg_type}: Focus Terms (comma-separated)", ", ".join(cfg["keywords"]))
                cfg["keywords"] = [k.strip() for k in kws_input.split(",") if k.strip()]

                col1, col2 = st.columns(2)
                with col1:
                    cfg["tone_of_voice"] = st.selectbox(
                        f"{pg_type}: Tone of Voice",
                        ["Professional", "Casual", "Persuasive", "Technical", "Friendly", "Authoritative", "Compassionate"],
                        index=0
                    )
                    cfg["meta_required"] = st.checkbox(f"{pg_type}: Meta Title & Desc?", value=cfg["meta_required"])
                with col2:
                    cfg["writing_style"] = st.selectbox(
                        f"{pg_type}: Writing Style",
                        ["Informative", "Storytelling", "Educational", "Conversion-driven", "Conversational"],
                        index=0
                    )
                    cfg["schema_toggle"] = st.checkbox(f"{pg_type}: Structured Data?", value=cfg["schema_toggle"])

                cfg["reinforce_eeat"] = st.checkbox(
                    f"{pg_type}: Reinforce E-E-A-T?", value=cfg["reinforce_eeat"]
                )
                cfg["include_citations"] = st.checkbox(
                    f"{pg_type}: Include Citations?", value=cfg["include_citations"]
                )
                cfg["practice_location"] = st.text_input(
                    f"{pg_type}: Location (City/State)",
                    value=cfg["practice_location"]
                )
                cfg["practice_name"] = st.text_input(
                    f"{pg_type}: Practice Name",
                    value=cfg["practice_name"]
                )

                cfg["detailed_breakdown"] = st.checkbox(
                    f"{pg_type}: Detailed Breakdown?",
                    value=cfg["detailed_breakdown"]
                )
                if cfg["detailed_breakdown"]:
                    with st.expander(f"Custom Breakdown for {pg_type}", expanded=False):
                        structured_breakdown_builder(pg_type)

                cfg["custom_template"] = st.text_area(
                    f"{pg_type}: Custom Template",
                    value=cfg["custom_template"]
                )

        st.write("---")
        st.subheader("Generate Full Website Content")
        full_site_temp = st.slider("Creativity (temperature)", 0.0, 1.0, 0.7, 0.1)

        if st.button("Generate All Selected Pages"):
            if not selected_pages:
                st.warning("Please select at least one page.")
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
                        system_prompt = (
                            "You are an AI assistant specialized in writing medically oriented, user-friendly website content. "
                            "Do not mention SEO or local SEO in the final text. Adhere to E-E-A-T."
                        )
                        site_gen_text = generate_content_with_chatgpt(
                            api_key=user_api_key,
                            system_prompt=system_prompt,
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
            st.success("Cleared full site configs.")


if __name__ == "__main__":
    main()
