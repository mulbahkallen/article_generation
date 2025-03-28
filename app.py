import streamlit as st
import openai
import json
from pathlib import Path
from typing import List

try:
    from openai.error import OpenAIError, RateLimitError
except ImportError:
    OpenAIError = Exception
    class RateLimitError(OpenAIError):
        pass

TEMPLATE_FILE = "templates.json"

def load_templates():
    """Load stored templates from JSON if available."""
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
    """Save the template list to JSON."""
    try:
        with open(TEMPLATE_FILE, "w") as f:
            json.dump({"templates": templates}, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving templates: {e}")
        return False

# Initialize templates in session state
if "templates" not in st.session_state:
    st.session_state.templates = load_templates()

# We'll store new fields and keywords for the Template Builder
if "new_template_fields" not in st.session_state:
    st.session_state.new_template_fields = []
if "new_template_keywords" not in st.session_state:
    st.session_state.new_template_keywords = []

# For demonstration, a minimal function to generate content
def fake_generate_content(page_type: str, fields: List[str], keywords: List[str]) -> str:
    """
    A placeholder function that 'generates' content from the template.
    In a real system, you'd call GPT or your advanced logic here.
    """
    # Just for demonstration, let's piece something together:
    lines = [f"**Page Type**: {page_type}",
             f"**Using Keywords**: {', '.join(keywords) if keywords else '(none)'}",
             "## Fields Output:"]
    for i, fline in enumerate(fields):
        lines.append(f"**Field {i+1}**: {fline}")
    lines.append("\n**Done** (this is a placeholder).")
    return "\n".join(lines)

def main():
    st.set_page_config(page_title="CMS Template Builder & AI Content Tool", layout="wide")
    st.title("CMS Template Builder & AI Content Tool")

    st.write("""
    This demo shows a **Template Builder** for user-friendly creation of CMS field definitions,
    plus minimal Single/Bulk/Full site generation modes that actually produce content from the loaded templates.
    """)

    mode = st.radio("Choose a Mode", ["Template Builder", "Single-Page Generation", "Bulk Generation", "Full Website Generation"])

    if mode == "Template Builder":
        run_template_builder()
    elif mode == "Single-Page Generation":
        run_single_page_generation()
    elif mode == "Bulk Generation":
        run_bulk_generation()
    else:
        run_full_website_generation()


def run_template_builder():
    st.header("Template Builder")

    # Basic template info
    template_name = st.text_input("Template Name", placeholder="e.g. MyHomeTemplate")
    template_page_type = st.selectbox("Template Page Type", ["Homepage", "Service Page", "Blog Post", "About Us Page", "Other"])

    st.subheader("Keywords for This Template")
    st.write("Enter any keywords (comma-separated) you want associated with this template.")
    existing_kw_str = ", ".join(st.session_state.new_template_keywords)
    kw_input = st.text_input("Template Keywords", value=existing_kw_str, placeholder="e.g. dentist, sedation, cosmetic")
    if st.button("Update Keywords"):
        st.session_state.new_template_keywords = [k.strip() for k in kw_input.split(",") if k.strip()]
        st.success(f"Updated keywords: {st.session_state.new_template_keywords}")

    st.subheader("CMS Fields in This Template")
    # Show existing fields
    if st.session_state.new_template_fields:
        st.markdown("### Current Fields")
        for i, field_line in enumerate(st.session_state.new_template_fields):
            st.markdown(f"{i+1}. **{field_line}**")
            if st.button(f"Remove Field {i+1}", key=f"remove_field_{i}"):
                st.session_state.new_template_fields.pop(i)
                st.experimental_rerun()
    else:
        st.info("No fields yet. Use the form below to add them.")

    label_options = [
        "H1", "H2", "H3", "Tagline", "Intro Blurb",
        "Body Section", "Call To Action", "FAQ", "Custom"
    ]
    with st.form("new_field_form", clear_on_submit=True):
        st.write("**Add a Field**")
        selected_label = st.selectbox("Field Label", label_options)
        custom_label = ""
        if selected_label == "Custom":
            custom_label = st.text_input("Custom Label", "")
        constraint_type = st.selectbox("Constraint Type", ["characters","words","sentences"])
        colA, colB = st.columns(2)
        with colA:
            min_val = st.number_input("Min Value", min_value=0, max_value=9999, value=1)
        with colB:
            max_val = st.number_input("Max Value", min_value=0, max_value=9999, value=3)
        notes = st.text_area("Additional Notes (Optional)")

        submit_field = st.form_submit_button("Add Field")
        if submit_field:
            final_label = custom_label.strip() if selected_label == "Custom" else selected_label
            if final_label:
                note_str = f" - {notes.strip()}" if notes.strip() else ""
                line = f"{final_label} [{min_val}-{max_val} {constraint_type}]{note_str}"
                st.session_state.new_template_fields.append(line)
                st.success(f"Added: {line}")
            else:
                st.warning("Please provide a valid label if 'Custom' was chosen.")

    # Save the template
    st.subheader("Save This Template")
    if st.button("Save Template"):
        if not template_name.strip():
            st.warning("Please provide a Template Name.")
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
                    # Clear local data
                    st.session_state.new_template_fields.clear()
                    st.session_state.new_template_keywords.clear()
                else:
                    st.error("Failed to save template. Check logs.")

    st.write("---")
    st.write("### Existing Templates")
    if st.session_state.templates:
        for t in st.session_state.templates:
            st.markdown(f"**Name**: {t['name']} | **Type**: {t['page_type']}")
            if "fields" in t and t["fields"]:
                for i, fl in enumerate(t["fields"]):
                    st.markdown(f"&nbsp; &nbsp; {i+1}. {fl}")
            if "keywords" in t and t["keywords"]:
                st.write("Keywords:", ", ".join(t["keywords"]))
            st.write("---")
    else:
        st.info("No templates saved yet.")


def run_single_page_generation():
    st.header("Single-Page Generation")
    st.write("**Load a saved template** and generate content for a single page from it.")

    if not st.session_state.templates:
        st.info("No templates exist yet. Go create one in the Template Builder.")
        return

    # Step 1: Choose a template
    tmpl_names = [t["name"] for t in st.session_state.templates]
    chosen_tmpl_name = st.selectbox("Select a Template", ["(None)"] + tmpl_names)
    if chosen_tmpl_name == "(None)":
        st.warning("Please select a template to proceed.")
        return

    selected_template = next((tt for tt in st.session_state.templates if tt["name"] == chosen_tmpl_name), None)
    if not selected_template:
        st.warning("No template found. Did you select one?")
        return

    st.write(f"**Template Name**: {selected_template['name']} | **Page Type**: {selected_template['page_type']}")
    if "keywords" in selected_template and selected_template["keywords"]:
        st.write("**Keywords**:", ", ".join(selected_template["keywords"]))
    st.write("### Template Fields:")
    for i, fl in enumerate(selected_template["fields"]):
        st.markdown(f"{i+1}. {fl}")

    st.write("---")
    st.write("**Generate Single-Page Content**")

    # Additional user inputs if needed:
    st.write("You could add more fields (like location, tone, word count) here, or use them in your actual logic.")
    user_location = st.text_input("Location (optional)", "")
    if st.button("Generate Single-Page Content"):
        # For demonstration, let's call a placeholder function
        output = fake_generate_content(
            page_type=selected_template["page_type"],
            fields=selected_template["fields"],
            keywords=selected_template["keywords"]
        )
        st.subheader("Generated Content")
        st.write(output)


def run_bulk_generation():
    st.header("Bulk Generation")
    st.write("Pick multiple templates, produce content for each in one go.")

    if not st.session_state.templates:
        st.info("No templates exist. Go create them in Template Builder.")
        return

    # We'll let user choose multiple templates from existing
    all_names = [t["name"] for t in st.session_state.templates]
    chosen_names = st.multiselect("Select templates to generate in bulk:", all_names)
    if not chosen_names:
        st.warning("Pick at least one template.")
        return

    if st.button("Generate All"):
        st.write("## Bulk Generation Results")
        for name in chosen_names:
            tmpl = next((x for x in st.session_state.templates if x["name"] == name), None)
            if not tmpl:
                st.warning(f"Template not found: {name}")
                continue

            st.write(f"### Template: {tmpl['name']} (Type: {tmpl['page_type']})")
            content = fake_generate_content(tmpl["page_type"], tmpl["fields"], tmpl["keywords"])
            st.write(content)
            st.write("---")


def run_full_website_generation():
    st.header("Full Website Generation")
    st.write("Generate entire site content from multiple templates—like a homepage, about page, services pages, etc.")

    if not st.session_state.templates:
        st.info("No templates exist yet. Go create them in the Template Builder.")
        return

    # A typical approach: user picks which template is for "Homepage", which is for "About," etc.
    # We'll let them pick from the existing templates by name.
    home_tmpl_name = st.selectbox("Choose Homepage Template", ["(None)"] + [t["name"] for t in st.session_state.templates])
    about_tmpl_name = st.selectbox("Choose About Us Template", ["(None)"] + [t["name"] for t in st.session_state.templates])
    service_tmpl_name = st.selectbox("Choose Service Template", ["(None)"] + [t["name"] for t in st.session_state.templates])

    if st.button("Generate Full Site"):
        st.write("## Full Site Generation Results")
        # Just as an example:
        for chosen in [("Homepage", home_tmpl_name), ("About Us", about_tmpl_name), ("Service Page", service_tmpl_name)]:
            label, name = chosen
            if name == "(None)":
                st.info(f"No template selected for {label}. Skipping.")
                continue
            tmpl = next((x for x in st.session_state.templates if x["name"] == name), None)
            if not tmpl:
                st.warning(f"Template {name} not found. Skipping {label}.")
                continue
            st.write(f"### Generating {label} from template: {tmpl['name']}")
            out = fake_generate_content(tmpl["page_type"], tmpl["fields"], tmpl["keywords"])
            st.write(out)
            st.write("---")


if __name__ == "__main__":
    main()
