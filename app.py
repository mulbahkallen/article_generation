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

# If you want reading level checks, install 'textstat'
try:
    import textstat
    TEXTSTAT_AVAILABLE = True
except ImportError:
    TEXTSTAT_AVAILABLE = False

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
    """Load stored templates (page specs or breakdown sets) from a JSON file, if it exists."""
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

# For building new templates in the “Template Builder” mode
if "new_template_fields" not in st.session_state:
    st.session_state.new_template_fields = []
if "new_template_keywords" not in st.session_state:
    st.session_state.new_template_keywords = []

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

# We can also store some “Essentials” or other preset breakdown sets:
PRESET_BREAKDOWNS = {
    "Essentials-Homepage": [
        "H1 [20-60 characters]",
        "Tagline [6-12 words]",
        "Intro blurb [15-20 words]",
        "H2 [30-70 characters]",
        "Body 1 [3-5 sentences]",
        "H2-2 Services [30-70 characters]",
        "[Service collection]",
        "H2-3 [30-70 characters]",
        "Body 2 [3-5 sentences]",
        "H2-4 [About] [30-70 characters]",
        "Body 3 [3-5 sentences]",
        "Title Tag [60 characters max]",
        "Meta Description [150-160 characters]"
    ],
    "Essentials-Service": [
        "H1 [20-60 characters]",
        "Intro blurb [15-20 words]",
        "H2 [30-70 characters]",
        "Body 1 [3-5 sentences]",
        "H2-2 [30-70 characters]",
        "Body 2 [3-5 sentences]",
        "H2-4 [About] [30-70 characters]",
        "Body 3 [3-5 sentences]",
        "Title Tag [60 characters max]",
        "Meta Description [150-160 characters]"
    ],
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
def call_openai_chat(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    model: str = "gpt-3.5-turbo",
    max_retries: int = 3
) -> str:
    import openai
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


def generate_content_with_post_checks(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    reading_ease_target: float,
    max_tries_for_reading: int = 2
) -> str:
    """
    Optionally re-invokes GPT if reading level is too low (Flesch).
    """
    content = call_openai_chat(
        api_key=api_key,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens
    )
    if not content:
        return ""

    if TEXTSTAT_AVAILABLE and reading_ease_target > 0:
        tries = 0
        while tries < max_tries_for_reading:
            import textstat
            flesch = textstat.flesch_reading_ease(content)
            if flesch < reading_ease_target:
                refine_prompt = (
                    f"Your text has a Flesch Reading Ease of about {flesch}, "
                    f"which is below the target of {reading_ease_target}. "
                    "Please simplify the language, shorten sentences, and rephrase for clarity, "
                    "while preserving meaning.\n\n"
                    "Current text:\n"
                    f"{content}\n"
                )
                refined = call_openai_chat(
                    api_key=api_key,
                    system_prompt=system_prompt,
                    user_prompt=refine_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if not refined:
                    break
                content = refined
                tries += 1
            else:
                break

    return content


# =============== Prompt Generation (User's Original Logic) ===============
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
    doctor_name: str = "",
    detailed_breakdown: bool = False,
    custom_breakdown_fields: List[str] = None,
    formula_heading: bool = False,
    heading_format: str = "",
    reading_ease_target: float = 0.0,
    practice_type: str = ""
) -> str:
    """
    Incorporates the original approach plus optional formula heading, reading ease target, etc.
    """
    if custom_breakdown_fields is None:
        custom_breakdown_fields = []

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
    if doctor_name:
        base_instructions.append(
            f"Mention the doctor's name: {doctor_name}. Avoid referencing SEO."
        )
    if practice_type:
        base_instructions.append(
            f"This practice is a {practice_type} type, if relevant. Don't mention SEO."
        )

    if formula_heading and heading_format.strip():
        base_instructions.append(
            f"Use the following heading formula for the main heading (H1): '{heading_format}'. "
            "Adjust it if needed, but keep the structure. Fill placeholders like {keyword}, {practice_type}, {location}, {doctor_name} if present."
        )

    if reading_ease_target > 0:
        base_instructions.append(
            f"Aim for a Flesch Reading Ease score of at least {reading_ease_target} (simpler language)."
        )

    variation_text = f"Generate {variation_num} variations of the content.\n" if variation_num > 1 else ""
    breakdown_instructions = ""
    if detailed_breakdown and custom_breakdown_fields:
        breakdown_instructions = "\n\n" + format_breakdown_list(custom_breakdown_fields)

    user_prompt = (
        "You are creating a piece of content for a medical or health-related website. "
        "Never explicitly mention 'SEO' or 'local SEO,' but you can include natural references to the location or relevant terms. "
        "Write the content so it is helpful, trustworthy, and consistent with medical E-E-A-T guidelines.\n\n"
        "Instructions:\n"
        f"{'\n'.join(base_instructions)}\n\n"
        f"{variation_text}"
    )
    if custom_template.strip():
        user_prompt += f"\n\nCustom Template:\n{custom_template}"

    if breakdown_instructions:
        user_prompt += breakdown_instructions

    user_prompt += (
        f"\n\nThe final output should be about {word_count} words. "
        "Use the given terms naturally and emphasize clarity, trust, and accuracy."
    )
    return user_prompt

def generate_meta_brief(api_key: str, page_type: str, keywords: List[str]) -> str:
    system_msg = (
        "You are an assistant helping to create a concise content brief. "
        "Avoid mentioning 'SEO' or 'local SEO' explicitly. "
        "Focus on clarity and user perspective."
    )
    user_msg = (
        f"Create a short content brief for a {page_type} page that targets these terms: {', '.join(keywords)}. "
        "Include target audience, main goal, and relevant local or brand elements without referencing SEO."
    )
    return call_openai_chat(api_key, system_msg, user_msg)

# ==========================================================
# =      STREAMLIT APP MAIN:  FOUR MODES (with builder)    =
# ==========================================================
def main():
    st.title("AI-Powered Content Generator")

    # Add a new mode for “Template Builder”
    mode = st.radio(
        "Content Generation Mode:",
        ["Template Builder", "Single-Page Generation", "Bulk Generation", "Full Website Generation"]
    )

    st.sidebar.header("OpenAI API")
    user_api_key = st.sidebar.text_input("Enter your OpenAI API Key:", type="password")
    if not user_api_key and mode != "Template Builder":
        # If the user is in the builder, no key is strictly needed
        st.warning("Please enter your OpenAI API key to proceed (except for Template Builder).")
        st.stop()

    # Prepare session states from user’s original code:
    if "page_specs" not in st.session_state:
        st.session_state.page_specs = []
    if "generated_variations" not in st.session_state:
        st.session_state.generated_variations = []
    if "full_site_configs" not in st.session_state:
        st.session_state.full_site_configs = {}
    if "custom_breakdown" not in st.session_state:
        st.session_state.custom_breakdown = {}

    if mode == "Template Builder":
        run_template_builder_mode()
    elif mode == "Single-Page Generation":
        run_single_page_mode(user_api_key)
    elif mode == "Bulk Generation":
        run_bulk_generation_mode(user_api_key)
    else:
        run_full_site_generation_mode(user_api_key)


# ==========================================================
# =           1) Template Builder Mode                     =
# ==========================================================
def run_template_builder_mode():
    st.header("Template Builder Mode")
    st.write("Create or edit a CMS template with a user-friendly field builder and optional keywords.")

    # -- Basic Info
    template_name = st.text_input("Template Name", placeholder="e.g. MyHomeTemplate")
    template_page_type = st.selectbox("Template Page Type", ["Homepage", "Service Page", "Blog Post", "About Us Page", "Other"])

    # -- Keywords
    st.subheader("Template Keywords")
    st.write("Enter comma-separated keywords to associate with this template.")
    existing_kw_str = ", ".join(st.session_state.new_template_keywords)
    kw_input = st.text_input("Keywords for Template", existing_kw_str)
    if st.button("Update Template Keywords"):
        st.session_state.new_template_keywords = [k.strip() for k in kw_input.split(",") if k.strip()]
        st.success(f"Keywords updated: {st.session_state.new_template_keywords}")

    # -- Show existing fields
    st.subheader("CMS Fields")
    if st.session_state.new_template_fields:
        st.markdown("### Current Fields")
        for i, line in enumerate(st.session_state.new_template_fields):
            st.markdown(f"{i+1}. **{line}**")
            if st.button(f"Remove Field {i+1}", key=f"remove_field_{i}"):
                st.session_state.new_template_fields.pop(i)
                st.experimental_rerun()
    else:
        st.info("No fields yet. Use the form below to add them.")

    # -- Add new field
    st.write("**Add a New Field**")
    label_options = [
        "H1", "H2", "H3", "Tagline", "Intro Blurb",
        "Body Section", "Call To Action", "FAQ", "Custom"
    ]
    with st.form("builder_add_field", clear_on_submit=True):
        colA, colB = st.columns(2)
        with colA:
            selected_label = st.selectbox("Field Label", label_options)
        with colB:
            custom_label = ""
            if selected_label == "Custom":
                custom_label = st.text_input("Custom Label")

        c1, c2 = st.columns(2)
        with c1:
            constraint_type = st.selectbox("Constraint Type", ["characters","words","sentences"])
        with c2:
            st.write("")  # a spacer
        colMin, colMax = st.columns(2)
        with colMin:
            min_val = st.number_input("Min Value", min_value=0, max_value=9999, value=1)
        with colMax:
            max_val = st.number_input("Max Value", min_value=0, max_value=9999, value=3)

        notes = st.text_area("Additional Notes (Optional)")
        submit_new_field = st.form_submit_button("Add Field")
        if submit_new_field:
            final_label = custom_label.strip() if selected_label == "Custom" else selected_label
            if final_label:
                note_str = f" - {notes.strip()}" if notes.strip() else ""
                line = f"{final_label} [{min_val}-{max_val} {constraint_type}]{note_str}"
                st.session_state.new_template_fields.append(line)
                st.success(f"Added: {line}")
            else:
                st.warning("Please provide a valid label if 'Custom' was chosen.")

    st.write("---")
    st.subheader("Save This Template")
    if st.button("Save Template"):
        if not template_name.strip():
            st.warning("Please provide a template name.")
        elif not st.session_state.new_template_fields:
            st.warning("No fields to save. Please add at least one field.")
        else:
            new_tmpl = {
                "name": template_name.strip(),
                "page_type": template_page_type,
                "fields": st.session_state.new_template_fields[:],
                "keywords": st.session_state.new_template_keywords[:]
            }
            existing = st.session_state.templates or []
            if any(t for t in existing if t["name"].lower() == new_tmpl["name"].lower()):
                st.warning(f"A template named '{new_tmpl['name']}' already exists.")
            else:
                existing.append(new_tmpl)
                if save_templates(existing):
                    st.success(f"Template '{new_tmpl['name']}' saved.")
                    st.session_state.templates = existing
                    # Clear out the builder states
                    st.session_state.new_template_fields.clear()
                    st.session_state.new_template_keywords.clear()
                else:
                    st.error("Failed to save template. Check logs.")

    st.write("---")
    st.write("### Existing Templates")
    if st.session_state.templates:
        for t in st.session_state.templates:
            st.markdown(f"**Name**: {t['name']} | Page Type: {t['page_type']}")
            if t.get("keywords"):
                st.write("Keywords:", ", ".join(t["keywords"]))
            if t.get("fields"):
                for i, fl in enumerate(t["fields"]):
                    st.markdown(f"&nbsp; &nbsp; {i+1}. {fl}")
            st.write("---")
    else:
        st.info("No saved templates yet.")


# ==========================================================
# =           2) Single-Page Generation Mode              =
# ==========================================================
def run_single_page_mode(user_api_key: str):
    st.subheader("Single-Page Generation")

    # The rest of your original single-page content generation logic remains:
    #   e.g. advanced toggles for E-E-A-T, citations, etc.
    #   We'll keep it as is from your code, or we can replicate a simplified version.

    with st.expander("Advanced Settings (E-E-A-T, Citations, Local Mentions)", expanded=False):
        reinforce_eeat = st.checkbox("Reinforce E-E-A-T Guidelines?", value=False)
        include_citations = st.checkbox("Include References/Citations?", value=False)
        practice_location = st.text_input("Practice Location (City, State)", value="")
        practice_name = st.text_input("Practice Name", value="")
        doctor_name = st.text_input("Doctor Name", value="")
        reading_ease_target = st.number_input("Flesch Reading Ease target (0=skip)", 0.0, 100.0, 0.0, step=5.0)

    page_type = st.selectbox(
        "Page Type",
        ["Homepage", "Service Page", "Blog Post", "About Us Page", "Product Page", "Other"]
    )
    word_count = st.slider("Desired Word Count", 200, 3000, 800, step=100)
    keywords_input = st.text_input("Focus Terms/Keywords (comma-separated)", "")
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

    # Additional toggles for “Detailed CMS Breakdown”
    detailed_breakdown = st.checkbox("Use Detailed CMS Breakdown?", value=False)
    if detailed_breakdown:
        with st.expander("Custom Breakdown Builder", expanded=False):
            structured_breakdown_builder(page_type)  # from your original code

    col1, col2 = st.columns(2)
    with col1:
        number_of_variations = st.number_input("Number of Content Variations", 1, 5, 1)
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

    # A formula heading toggle, etc. from your code:
    formula_heading_toggle = st.checkbox("Use formula heading? (e.g. 'Top {keyword} {practice_type} in {location}')")
    heading_format = ""
    practice_type_input = ""
    if formula_heading_toggle:
        heading_format = st.text_input("Heading Format", "Top {keyword} {practice_type} in {location}")
        practice_type_input = st.text_input("Practice Type (for heading formula)", "")

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
                doctor_name=doctor_name,
                detailed_breakdown=detailed_breakdown,
                custom_breakdown_fields=custom_breakdown_list,
                formula_heading=formula_heading_toggle,
                heading_format=heading_format,
                reading_ease_target=reading_ease_target,
                practice_type=practice_type_input
            )

            system_prompt = (
                "You are an AI assistant specialized in writing medically oriented, user-friendly web content. "
                "Adhere to E-E-A-T guidelines. "
                "Never explicitly mention 'SEO,' 'search engine,' or 'local SEO' in your final text. "
            )

            generated_text = call_openai_chat(
                api_key=user_api_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=3000
            )
            if not generated_text:
                st.error("No content generated or an error occurred.")
                return

            # If multiple variations, we do a naive split
            if number_of_variations > 1:
                splitted = generated_text.split("Variation")
                splitted_clean = [v.strip() for v in splitted if len(v.strip())>10]
                if len(splitted_clean) < number_of_variations:
                    st.warning("Could not parse multiple variations properly. Displaying raw text.")
                    splitted_clean = [generated_text]
            else:
                splitted_clean = [generated_text]

            final_variations = []
            for vtext in splitted_clean:
                refined = generate_content_with_post_checks(
                    api_key=user_api_key,
                    system_prompt=system_prompt,
                    user_prompt="Refine if needed:\n" + vtext,
                    temperature=temperature,
                    max_tokens=3000,
                    reading_ease_target=reading_ease_target
                )
                final_variations.append(refined)

            st.session_state.generated_variations = final_variations

            for i, placeholder in enumerate(content_placeholders):
                if i < len(final_variations):
                    placeholder.markdown(f"**Variation {i+1}**\n\n{final_variations[i]}")
                else:
                    placeholder.markdown(f"**Variation {i+1}**\n\n(No content generated)")

    st.write("---")
    st.subheader("Refine / Edit Content")
    refine_variation_index = st.number_input("Select Variation to Refine", 1, number_of_variations, 1)
    refine_input = st.text_area("Refinement Instructions", help="No mention of SEO. Keep it medically accurate.")
    if st.button("Refine"):
        idx = refine_variation_index - 1
        if idx >= len(st.session_state.generated_variations):
            st.warning("No content to refine. Please generate content first.")
        else:
            old_content = st.session_state.generated_variations[idx]
            refine_prompt = (
                "Refine the following content without referencing SEO. Keep it user-friendly.\n\n"
                f"Original Content:\n{old_content}\n\n"
                f"Instructions:\n{refine_input}"
            )
            refined_result = call_openai_chat(
                api_key=user_api_key,
                system_prompt=(
                    "You are an AI specialized in refining medically oriented, user-friendly text. "
                    "Adhere to E-E-A-T and avoid SEO references."
                ),
                user_prompt=refine_prompt,
                temperature=0.7,
                max_tokens=3000
            )
            st.session_state.generated_variations[idx] = refined_result
            st.success("Refined content updated.")
            st.write(refined_result)

    st.write("---")
    st.subheader("Export Results")
    export_variation_index = st.number_input("Select Variation to Export", 1, number_of_variations, 1)
    export_format = st.selectbox("Export Format", ["HTML", "JSON", "Text"])

    if st.button("Export"):
        var_idx = export_variation_index - 1
        if var_idx >= len(st.session_state.generated_variations):
            st.warning("No variation found. Please generate first.")
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

# Provided by your code – the custom breakdown builder used in single/bulk/full
def structured_breakdown_builder(page_key: str):
    """
    Original approach to building each breakdown field in a custom list.
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

    # Option to load from a saved template
    template_options = ["(None)"] + [t["name"] for t in st.session_state.templates]
    chosen_template = st.selectbox("Load from a saved template", template_options, key=f"tmpl_sel_{page_key}")
    if st.button("Apply Template Breakdown", key=f"tmpl_apply_{page_key}"):
        if chosen_template != "(None)":
            tmpl = next((x for x in st.session_state.templates if x["name"] == chosen_template), None)
            if tmpl and "fields" in tmpl:
                # load the fields into st.session_state
                st.session_state.custom_breakdown[page_key] = tmpl["fields"][:]
                st.experimental_rerun()

    # Also load from PRESET_BREAKDOWNS
    preset_label = st.selectbox("Load Pre-Set Breakdown (Essentials)", ["(None)"] + list(PRESET_BREAKDOWNS.keys()), key=f"preset_sel_{page_key}")
    if st.button("Apply Pre-Set Breakdown", key=f"preset_apply_{page_key}"):
        if preset_label != "(None)":
            st.session_state.custom_breakdown[page_key] = PRESET_BREAKDOWNS[preset_label]
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


# ==========================================================
# =           3) Bulk Generation Mode                      =
# ==========================================================
def run_bulk_generation_mode(user_api_key: str):
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
            practice_name_bulk = st.text_input("Practice Name", value="")
            doctor_name_bulk = st.text_input("Doctor Name", value="")
            reading_ease_target_bulk = st.number_input("Flesch Reading Ease target (0=skip)", 0.0, 100.0, 0.0, 5.0)

            formula_heading_bulk = st.checkbox("Use a formula heading?")
            heading_format_bulk = ""
            if formula_heading_bulk:
                heading_format_bulk = st.text_input("Heading Format", "Top {keyword} {practice_type} in {location}")
            detailed_breakdown_bulk = st.checkbox("Use Detailed Breakdown?", value=False)

            if detailed_breakdown_bulk:
                with st.expander("Custom Breakdown Builder", expanded=False):
                    structured_breakdown_builder(b_page_type)

            practice_type_bulk = st.text_input("Practice Type (for heading formula)")

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
                    "doctor_name": doctor_name_bulk,
                    "reading_ease_target": reading_ease_target_bulk,
                    "formula_heading": formula_heading_bulk,
                    "heading_format": heading_format_bulk,
                    "detailed_breakdown": detailed_breakdown_bulk,
                    "practice_type": practice_type_bulk
                }
                st.session_state.page_specs.append(new_spec)
                st.success(f"Added a new {b_page_type} spec!")

    st.write("### Current Page Specifications")
    if not st.session_state.page_specs:
        st.info("No specs added yet.")
    else:
        for idx, spec in enumerate(st.session_state.page_specs):
            st.markdown(f"**Spec {idx+1}**: `{spec['page_type']}` ~{spec['word_count']} words")
            st.write(f"Keywords: {spec['keywords']}")
            st.write(f"Tone: {spec['tone_of_voice']} | Style: {spec['writing_style']}")
            st.write(f"Meta? {spec['meta_required']} | Schema? {spec['schema_toggle']}")
            st.write(f"E-E-A-T: {spec['reinforce_eeat']} | Citations: {spec['include_citations']}")
            st.write(f"Practice: {spec['practice_name']} | Doctor: {spec['doctor_name']} | Loc: {spec['practice_location']}")
            st.write(f"Reading Ease: {spec['reading_ease_target']}")
            st.write(f"Formula Heading: {spec['formula_heading']} => {spec['heading_format']}")
            if spec["detailed_breakdown"]:
                st.write("Detailed Breakdown: On")
            if spec["custom_template"]:
                st.write(f"Custom Template: {spec['custom_template'][:60]}...")
            remove_btn = st.button(f"Remove Spec {idx+1}", key=f"remove_{idx}")
            if remove_btn:
                st.session_state.page_specs.pop(idx)
                st.experimental_rerun()

        st.write("---")
        st.subheader("Generate All Bulk Pages")
        bulk_temp = st.slider("Creativity (temperature)", 0.0, 1.0, 0.7, 0.1)

        if st.button("Generate All Pages"):
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
                        doctor_name=spec["doctor_name"],
                        detailed_breakdown=spec["detailed_breakdown"],
                        custom_breakdown_fields=custom_breakdown_list,
                        formula_heading=spec["formula_heading"],
                        heading_format=spec["heading_format"],
                        reading_ease_target=spec["reading_ease_target"],
                        practice_type=spec["practice_type"]
                    )
                    system_msg = (
                        "You are an AI assistant specialized in writing medically oriented, user-friendly web content. "
                        "Do not mention SEO or local SEO in the final text. Adhere to E-E-A-T."
                    )
                    raw_text = call_openai_chat(
                        api_key=user_api_key,
                        system_prompt=system_msg,
                        user_prompt=user_prompt,
                        temperature=bulk_temp,
                        max_tokens=3000
                    )
                    if not raw_text:
                        st.error(f"Failed to generate content for spec {idx+1}.")
                        continue
                    final_text = generate_content_with_post_checks(
                        api_key=user_api_key,
                        system_prompt=system_msg,
                        user_prompt="Refine if needed:\n" + raw_text,
                        temperature=bulk_temp,
                        max_tokens=3000,
                        reading_ease_target=spec["reading_ease_target"]
                    )
                    st.markdown(f"### Page {idx+1} Output ({spec['page_type']})")
                    st.write(final_text)
                    st.write("---")

        st.write("---")
        if st.button("Reset Specs"):
            st.session_state.page_specs = []
            st.success("All specs cleared.")

# ==========================================================
# =     4) Full Website Generation Mode                    =
# ==========================================================
def run_full_site_generation_mode(api_key: str):
    st.subheader("Full Website Generation")
    st.write(
        "Generate all core pages of a website in one flow (Home, About, Service, Blog, etc.). "
        "Configure each page and produce them together."
    )

    default_pages = ["Homepage", "About Us Page", "Service Page", "Blog Post", "Contact Page"]
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
                "doctor_name": "",
                "detailed_breakdown": False,
                "formula_heading": False,
                "heading_format": "",
                "reading_ease_target": 0.0,
                "practice_type": ""
            }

    for pg_type in selected_pages:
        with st.expander(f"{pg_type} Settings", expanded=False):
            cfg = st.session_state.full_site_configs[pg_type]
            cfg["word_count"] = st.slider(f"{pg_type}: Word Count", 200, 3000, cfg["word_count"], step=100)
            kws_input = st.text_input(f"{pg_type}: Focus Terms (comma-separated)", ", ".join(cfg["keywords"]))
            cfg["keywords"] = [x.strip() for x in kws_input.split(",") if x.strip()]

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

            cfg["reinforce_eeat"] = st.checkbox(f"{pg_type}: Reinforce E-E-A-T?", value=cfg["reinforce_eeat"])
            cfg["include_citations"] = st.checkbox(f"{pg_type}: Include Citations?", value=cfg["include_citations"])
            cfg["practice_location"] = st.text_input(f"{pg_type}: Location (City/State)", value=cfg["practice_location"])
            cfg["practice_name"] = st.text_input(f"{pg_type}: Practice Name", value=cfg["practice_name"])
            cfg["doctor_name"] = st.text_input(f"{pg_type}: Doctor Name", value=cfg["doctor_name"])
            cfg["practice_type"] = st.text_input(f"{pg_type}: Practice Type (for heading formula)", value=cfg["practice_type"])
            cfg["reading_ease_target"] = st.number_input(f"{pg_type}: Flesch target (0=skip)", 0.0, 100.0, cfg["reading_ease_target"], step=5.0)

            cfg["formula_heading"] = st.checkbox(f"{pg_type}: Formula Heading?", value=cfg["formula_heading"])
            if cfg["formula_heading"]:
                cfg["heading_format"] = st.text_input(f"{pg_type}: Heading Format", value=cfg["heading_format"])

            cfg["detailed_breakdown"] = st.checkbox(
                f"{pg_type}: Detailed Breakdown?",
                value=cfg["detailed_breakdown"]
            )
            if cfg["detailed_breakdown"]:
                with st.expander(f"Custom Breakdown for {pg_type}", expanded=False):
                    structured_breakdown_builder(pg_type)

            cfg["custom_template"] = st.text_area(f"{pg_type}: Custom Template", value=cfg["custom_template"])

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
                        doctor_name=cfg["doctor_name"],
                        detailed_breakdown=cfg["detailed_breakdown"],
                        custom_breakdown_fields=custom_breakdown_list,
                        formula_heading=cfg["formula_heading"],
                        heading_format=cfg["heading_format"],
                        reading_ease_target=cfg["reading_ease_target"],
                        practice_type=cfg["practice_type"]
                    )
                    system_msg = (
                        "You are an AI assistant specialized in writing medically oriented, user-friendly website content. "
                        "Do not mention SEO or local SEO in the final text. Adhere to E-E-A-T."
                    )
                    site_gen_text = call_openai_chat(
                        api_key=user_api_key,
                        system_prompt=system_msg,
                        user_prompt=user_prompt,
                        temperature=full_site_temp,
                        max_tokens=3000
                    )
                    if site_gen_text:
                        final_site_text = generate_content_with_post_checks(
                            api_key=user_api_key,
                            system_prompt=system_msg,
                            user_prompt="Refine if needed:\n" + site_gen_text,
                            temperature=full_site_temp,
                            max_tokens=3000,
                            reading_ease_target=cfg["reading_ease_target"]
                        )
                        st.markdown(f"### {pg_type} Output")
                        st.write(final_site_text)
                        st.write("---")
                    else:
                        st.error(f"Failed to generate for {pg_type}.")

    st.subheader("Clear Full Site Config")
    if st.button("Reset Full Site Config"):
        st.session_state.full_site_configs = {}
        st.success("Cleared full site configs.")


if __name__ == "__main__":
    main()
