import streamlit as st
import openai
import json
import time
from datetime import datetime
from typing import List, Dict
from pathlib import Path

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

if "templates" not in st.session_state:
    st.session_state.templates = load_templates()

# For building new templates in the sidebar:
if "template_builder_fields" not in st.session_state:
    st.session_state.template_builder_fields = []


# ==========================================================
# =         PAGE/SECTION BREAKDOWNS & PRESET EXAMPLES      =
# ==========================================================
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
    Extended with:
      - separate practice_name, doctor_name
      - formula_heading + heading_format
    """
    if custom_breakdown_fields is None:
        custom_breakdown_fields = []

    base_instructions = [
        f"Page Type: {page_type}",
        f"Approximate Word Count: ~{word_count} words",
        f"Primary Terms or Topics: {', '.join(keywords) if keywords else 'None'}",
        f"Tone of Voice: {tone_of_voice}",
        f"Style: {writing_style}",
        ("Include a meta title and meta description if requested."
         if meta_required else "No meta info needed."),
        ("Include structured data markup suggestions if requested."
         if structured_data else "No structured data suggestions needed."),
        "Do not explicitly mention SEO or local SEO in the final text."
    ]

    if reinforce_eeat:
        base_instructions.append("Demonstrate strong E-E-A-T principles: highlight expertise, authority, trustworthiness, and experience.")
    if include_citations:
        base_instructions.append("Include reputable references or citations if relevant (NIH, CDC, .gov, .edu) but do not mention SEO.")
    if practice_location:
        base_instructions.append(f"Subtly reference the location: {practice_location}, but do not mention 'local SEO'.")
    if practice_name:
        base_instructions.append(f"Mention the practice name: {practice_name}. Avoid referencing SEO.")
    if doctor_name:
        base_instructions.append(f"Mention the doctor's name: {doctor_name}. Avoid referencing SEO.")
    if practice_type:
        base_instructions.append(f"This practice is a {practice_type} type, if relevant to headings or content.")

    # If formula heading is on, we can incorporate heading_format
    if formula_heading and heading_format.strip():
        base_instructions.append(
            f"Use the following heading formula for the main heading (H1): '{heading_format}'. "
            "Adjust if needed, but keep structure. E.g. if placeholders are {keyword}, {practice_type}, {location}, {doctor_name}, fill them accordingly."
        )

    if reading_ease_target > 0:
        base_instructions.append(
            f"Aim for a Flesch Reading Ease score of at least {reading_ease_target}, using simpler language if needed."
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
        f"Create a short content brief for a {page_type} page targeting these terms: {', '.join(keywords)}. "
        "Include target audience, main goal, and relevant local or brand elements without referencing SEO."
    )
    return call_openai_chat(api_key, system_msg, user_msg)


# ==========================================================
# =                STREAMLIT APP MAIN LOGIC                =
# ==========================================================
def main():
    st.title("AI-Powered Content Generator (Clickable Template Builder)")

    # ============= Template Builder in Sidebar =============
    st.sidebar.header("Template Builder (Clickable Fields)")

    if "new_template_name" not in st.session_state:
        st.session_state.new_template_name = ""
    if "new_template_type" not in st.session_state:
        st.session_state.new_template_type = "Homepage"

    st.session_state.new_template_name = st.sidebar.text_input(
        "New Template Name",
        value=st.session_state.new_template_name,
        placeholder="e.g. MyCustomHomepage"
    )
    st.session_state.new_template_type = st.sidebar.selectbox(
        "Template Page Type", 
        ["Homepage", "Service Page", "Blog Post", "About Us Page", "Other"],
        index=["Homepage","Service Page","Blog Post","About Us Page","Other"].index(st.session_state.new_template_type)
    )

    # Show the field lines
    st.sidebar.write("### Fields in This Template")
    if st.session_state.template_builder_fields:
        for i, field_line in enumerate(st.session_state.template_builder_fields):
            st.sidebar.write(f"{i+1}. {field_line}")
            if st.sidebar.button(f"Remove Field {i+1}", key=f"template_builder_remove_{i}"):
                st.session_state.template_builder_fields.pop(i)
                st.experimental_rerun()
    else:
        st.sidebar.info("No fields added yet.")

    # Add Field to the template builder
    # It's basically the same approach as structured_breakdown_builder but in the sidebar
    label_options = [
        "H1", "H2", "H3", "Tagline", "Intro Blurb",
        "Body Section", "Call To Action", "FAQ", "Custom"
    ]
    with st.sidebar.form("template_builder_add_field", clear_on_submit=True):
        st.subheader("Add a Field to Template")
        selected_label = st.selectbox("Field Label", label_options)
        custom_label = ""
        if selected_label == "Custom":
            custom_label = st.text_input("Custom Label", "")
        constraint_type = st.selectbox("Constraint Type", ["characters","words","sentences"])
        c1, c2 = st.columns(2)
        with c1:
            min_val = st.number_input("Min Value", min_value=0, max_value=9999, value=1)
        with c2:
            max_val = st.number_input("Max Value", min_value=0, max_value=9999, value=3)
        notes = st.text_area("Additional Notes (Optional)")
        add_field_btn = st.form_submit_button("Add Field")
        if add_field_btn:
            final_label = custom_label.strip() if selected_label == "Custom" else selected_label
            if final_label:
                notes_str = f" - {notes.strip()}" if notes.strip() else ""
                line = f"{final_label} [{min_val}-{max_val} {constraint_type}]{notes_str}"
                st.session_state.template_builder_fields.append(line)
                st.sidebar.success(f"Added field: {line}")
            else:
                st.sidebar.warning("Please provide a valid label if 'Custom' was chosen.")

    # Save Template
    if st.sidebar.button("Save Template"):
        name = st.session_state.new_template_name.strip()
        if not name:
            st.sidebar.warning("Please enter a valid template name.")
        else:
            lines = st.session_state.template_builder_fields[:]
            if not lines:
                st.sidebar.warning("No fields to save. Please add at least one field.")
            else:
                # Create the template dict
                new_tmpl = {
                    "name": name,
                    "page_type": st.session_state.new_template_type,
                    "breakdown_fields": lines
                }
                # Add to existing
                existing = st.session_state.templates or []
                if any(t for t in existing if t["name"].lower() == name.lower()):
                    st.sidebar.warning(f"A template named '{name}' already exists.")
                else:
                    existing.append(new_tmpl)
                    if save_templates(existing):
                        st.sidebar.success(f"Template '{name}' saved.")
                        st.session_state.templates = existing
                        # Clear out builder fields
                        st.session_state.template_builder_fields = []
                    else:
                        st.sidebar.error("Failed to save template. Check logs.")

    # Just a button to clear fields if needed
    if st.sidebar.button("Clear Fields"):
        st.session_state.template_builder_fields = []
        st.sidebar.info("Cleared all fields from the builder.")


    # ============= The main content generation UI =============
    st.sidebar.write("---")
    st.sidebar.header("OpenAI API")
    user_api_key = st.sidebar.text_input("Enter your OpenAI API Key:", type="password")
    if not user_api_key:
        st.warning("Please enter your OpenAI API key to proceed.")
        st.stop()

    st.sidebar.header("Choose an Objective")
    mode = st.sidebar.radio(
        "Content Generation Mode:",
        ["Single-Page Generation", "Bulk Generation", "Full Website Generation"]
    )

    if "page_specs" not in st.session_state:
        st.session_state.page_specs = []
    if "generated_variations" not in st.session_state:
        st.session_state.generated_variations = []
    if "full_site_configs" not in st.session_state:
        st.session_state.full_site_configs = {}
    if "custom_breakdown" not in st.session_state:
        st.session_state.custom_breakdown = {}

    from app_single_bulk_full import run_app_modes
    # We'll place all your Single/Bulk/Full logic into a separate file called app_single_bulk_full.py
    # for cleanliness. If you prefer to keep it all in one file, just copy that code here instead.
    #
    # But for demonstration, let's say we define a function run_app_modes(...) in that file that
    # implements the Single-Page, Bulk Generation, and Full Website Generation logic exactly as before.

    # Since you want a single-file solution, let's just define the code inline. 
    # We'll do it here for convenience.

    if mode == "Single-Page Generation":
        run_single_page_mode(user_api_key)
    elif mode == "Bulk Generation":
        run_bulk_mode(user_api_key)
    else:
        run_full_site_mode(user_api_key)


def run_single_page_mode(api_key: str):
    """
    Single-Page logic (the same as your existing code, minus the template builder parts).
    """
    st.subheader("Single-Page Content Generation")
    # ... the same code from your existing Single-page generation ...
    st.write("Placeholder: Single-page logic here. You can copy from your existing code.")


def run_bulk_mode(api_key: str):
    """
    Bulk generation logic.
    """
    st.subheader("Bulk Page Generation")
    # ... your existing Bulk generation code ...
    st.write("Placeholder: Bulk logic here. You can copy from your existing code.")


def run_full_site_mode(api_key: str):
    """
    Full website generation logic.
    """
    st.subheader("Full Website Generation")
    # ... your existing Full-site logic ...
    st.write("Placeholder: Full site logic here. You can copy from your existing code.")


if __name__ == "__main__":
    main()
