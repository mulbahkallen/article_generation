import streamlit as st
import openai
import json
from pathlib import Path

# ===============================
#     CONFIG AND INITIAL SETUP
# ===============================
st.set_page_config(page_title="Medical Content AI Generator", layout="wide")

st.title("AI Medical Content Generator")
st.write(
    "Generate high-quality medical website content without exposing SEO instructions in the final output. "
    "Ideal for producing client-facing copy that is still strategically optimized behind the scenes."
)

# Retrieve or request OpenAI API Key
if "openai_api_key" in st.secrets:
    openai.api_key = st.secrets["openai_api_key"]
else:
    api_input = st.text_input("Enter OpenAI API Key:", type="password")
    if api_input:
        openai.api_key = api_input

if not openai.api_key:
    st.error("Please provide a valid OpenAI API key to use this app.")
    st.stop()

# ===============================
#       TEMPLATE MANAGEMENT
# ===============================
TEMPLATE_FILE = "templates.json"

def load_templates():
    """Load templates from a JSON file (if it exists)."""
    if Path(TEMPLATE_FILE).exists():
        try:
            with open(TEMPLATE_FILE, "r") as f:
                data = json.load(f)
            # In case the file structure is known or unknown, handle it:
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "templates" in data:
                return data["templates"]
        except json.JSONDecodeError:
            st.error("Template file is corrupted. Starting with an empty template list.")
    return []

def save_templates(templates):
    """Save the templates list to a JSON file."""
    try:
        with open(TEMPLATE_FILE, "w") as f:
            json.dump(templates, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Failed to save templates: {e}")
        return False

if "templates" not in st.session_state:
    st.session_state.templates = load_templates()

# ===============================
#      SIDEBAR TEMPLATE UI
# ===============================
st.sidebar.header("Client/Project Templates")
template_names = ["(None)"] + [t["name"] for t in st.session_state.templates]
selected_template = st.sidebar.selectbox("Load Template", options=template_names)

if selected_template and selected_template != "(None)":
    tmpl = next((t for t in st.session_state.templates if t["name"] == selected_template), None)
    if tmpl:
        if st.session_state.get("last_loaded_template") != selected_template:
            for key, val in tmpl.items():
                if key == "name":
                    continue
                st.session_state[key] = val
            st.session_state.last_loaded_template = selected_template
else:
    st.session_state.last_loaded_template = None

st.sidebar.subheader("Save Current as Template")
new_template_name = st.sidebar.text_input("Template Name", value="", placeholder="e.g. Dr. Smith Cardiology")
if st.sidebar.button("Save Template"):
    if not new_template_name:
        st.sidebar.error("Please provide a name for the template.")
    else:
        template_data = {
            "name": new_template_name,
            "practice_name": st.session_state.get("practice_name", ""),
            "doctor_name": st.session_state.get("doctor_name", ""),
            "doctor_credentials": st.session_state.get("doctor_credentials", ""),
            "practice_specialty": st.session_state.get("practice_specialty", ""),
            "location": st.session_state.get("location", ""),
            "tone": st.session_state.get("tone", "")
        }
        # Prevent duplicates
        if any(t for t in st.session_state.templates if t["name"].strip().lower() == new_template_name.strip().lower()):
            st.sidebar.error("A template with this name already exists. Choose a different name.")
        else:
            st.session_state.templates.append(template_data)
            if save_templates(st.session_state.templates):
                st.sidebar.success(f"Template '{new_template_name}' saved.")
                template_names = ["(None)"] + [t["name"] for t in st.session_state.templates]
            else:
                st.sidebar.error("An error occurred while saving the template.")

# ===============================
#    MAIN INPUTS FOR PROJECT
# ===============================
st.header("Project Details")

practice_name = st.text_input(
    "Practice/Clinic Name", 
    value=st.session_state.get("practice_name", ""), 
    key="practice_name"
)
doctor_name = st.text_input(
    "Doctor's Name", 
    value=st.session_state.get("doctor_name", ""), 
    key="doctor_name"
)
doctor_credentials = st.text_area(
    "Doctor Credentials/Experience", 
    value=st.session_state.get("doctor_credentials", ""), 
    key="doctor_credentials"
)
practice_specialty = st.text_input(
    "Practice Specialty/Field", 
    value=st.session_state.get("practice_specialty", ""), 
    key="practice_specialty"
)
location = st.text_input(
    "Location (City/Region)", 
    value=st.session_state.get("location", ""), 
    key="location"
)
tone = st.text_input(
    "Preferred Tone/Style", 
    value=st.session_state.get("tone", ""), 
    key="tone",
    help="e.g. Compassionate, Professional, Friendly"
)

st.header("Content Specification")
content_type = st.selectbox("Content Type", ["Homepage", "Service Page", "Blog Post", "About Us"], key="content_type")

# Additional fields depending on content type
if content_type == "Blog Post":
    topic = st.text_input("Blog Topic or Title", value=st.session_state.get("blog_topic", ""), key="blog_topic")
    # 'primary_keyword' can still be used internally, but we won't push explicit SEO instructions in final text
    primary_keyword = st.text_input("Optional Focus Keyword/Term", value=st.session_state.get("primary_keyword", ""), key="primary_keyword")
elif content_type == "Service Page":
    service_name = st.text_input("Service Name", value=st.session_state.get("service_name", ""), key="service_name")
    primary_keyword = st.text_input("Optional Focus Keyword", value=st.session_state.get("primary_keyword", ""), key="primary_keyword")
elif content_type == "Homepage":
    primary_keyword = st.text_input("Optional Focus Keyword", value=st.session_state.get("primary_keyword", ""), key="primary_keyword")
elif content_type == "About Us":
    primary_keyword = st.text_input("Optional Focus Keyword", value=st.session_state.get("primary_keyword", ""), key="primary_keyword")

additional_notes = st.text_area(
    "Additional Notes/Instructions (for your internal use)",
    value=st.session_state.get("additional_notes", ""), 
    key="additional_notes"
)

# ===============================
#   BASIC VALIDATION
# ===============================
required_fields = []
if not practice_name and content_type != "Blog Post":
    required_fields.append("Practice/Clinic Name")
if not doctor_name and content_type in ["Homepage", "Service Page", "About Us"]:
    required_fields.append("Doctor's Name")
if not doctor_credentials and content_type in ["Homepage", "Service Page", "About Us"]:
    required_fields.append("Doctor Credentials")
if content_type == "Service Page" and not st.session_state.get("service_name"):
    required_fields.append("Service Name")
if content_type == "Blog Post" and not st.session_state.get("blog_topic"):
    required_fields.append("Blog Topic")

if required_fields:
    st.warning("Please provide the following required field(s) before generating content: " + ", ".join(required_fields))

# ===============================
#  OPENAI OUTLINE & CONTENT FUNCS
# ===============================

def generate_outline(details):
    """
    Generate a thorough outline for the specified content type without 
    explicit references to 'SEO' or 'local SEO' in the user-facing copy.
    """
    content_type = details["content_type"]
    
    # System message: emphasize factual, trustworthy, patient-friendly content
    system_msg = (
        "You are a medical copywriting assistant. You create outlines that are factual, clear, "
        "and patient-focused. The outline must reflect experience, expertise, authority, and trust, "
        "but should never mention 'SEO' or 'search engine' or 'local SEO' or similar. No direct SEO references. "
        "You can naturally incorporate location references if provided, but do not explicitly mention 'keywords' or 'SEO.'"
    )
    
    # Build user message
    if content_type == "Homepage":
        user_msg = (
            f"Generate a detailed outline for a Homepage of {details['practice_name']}.\n"
            f"Doctor: {details['doctor_name']} ({details['doctor_credentials']})\n"
            f"Specialty: {details['practice_specialty']}\n"
            f"Location: {details['location']}\n"
            f"Tone: {details['tone']}\n\n"
            "Focus on welcoming visitors, explaining the practice's main services, highlighting the doctor's expertise, "
            "and ending with an invitation to contact the practice. The outline should not contain any direct references to SEO."
        )
    elif content_type == "Service Page":
        user_msg = (
            f"Generate a detailed outline for a Service Page about {details['service_name']} "
            f"offered by {details['practice_name']}.\n"
            f"Doctor: {details['doctor_name']} ({details['doctor_credentials']})\n"
            f"Specialty: {details['practice_specialty']}\n"
            f"Location: {details['location']}\n"
            f"Tone: {details['tone']}\n\n"
            "Include sections that explain the treatment, benefits for patients, why to choose this doctor/practice, "
            "and a call-to-action. Do not mention the words 'SEO' or 'search engine' in the outline."
        )
    elif content_type == "Blog Post":
        user_msg = (
            f"Generate a detailed outline for a medical blog post titled '{details['blog_topic']}'.\n"
            f"Doctor: {details['doctor_name']} ({details['doctor_credentials']})\n"
            f"Practice Name: {details['practice_name']}\n"
            f"Tone: {details['tone']}\n\n"
            "Structure it with an introduction that engages readers, multiple body sections that provide valuable "
            "information, and a conclusion that summarizes or invites the reader to learn more. "
            "Do not explicitly mention SEO or keywords in the outline."
        )
    elif content_type == "About Us":
        user_msg = (
            f"Generate a detailed outline for an 'About Us' page of {details['practice_name']}.\n"
            f"Doctor: {details['doctor_name']} ({details['doctor_credentials']})\n"
            f"Specialty: {details['practice_specialty']}\n"
            f"Location: {details['location']}\n"
            f"Tone: {details['tone']}\n\n"
            "Include a brief history or mission statement, highlight the doctor's background, and conclude with a positive, "
            "trust-building message. Do not include references to SEO."
        )
    else:
        user_msg = (
            f"Generate a detailed outline for a {content_type}. Keep it factual, structured, and never mention SEO."
        )

    # Optionally incorporate additional notes internally (not referencing SEO)
    if details["additional_notes"]:
        user_msg += f"\n\nAdditional notes to consider: {details['additional_notes']}"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.5,
            max_tokens=500
        )
        outline = response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        outline = f"Error: {e}"
    
    return outline

def generate_content(details, outline):
    """
    Expand the outline into full client-facing copy without explicit SEO references.
    """
    content_type = details["content_type"]
    system_msg = (
        "You are a medical copywriting assistant. You produce clear, compassionate, and factual copy "
        "for a patient- or client-facing audience. Do not mention 'SEO,' 'local SEO,' or 'search engine' optimization anywhere. "
        "Write in a way that highlights trust, professionalism, and benefits to the patient, in accordance with E-E-A-T (experience, expertise, authority, trust)."
    )

    # The user prompt: we pass the outline, instruct the model to expand it into final text
    user_msg = f"Based on the following outline, write the full content for a {content_type}.\n\nOUTLINE:\n{outline}\n\n"
    
    # Provide some minimal instructions for style (patient-friendly, no SEO talk)
    if content_type == "Homepage":
        user_msg += (
            "\nPlease create a welcoming homepage that addresses patient needs, introduces the practice, "
            "showcases the doctor's experience, and concludes with a warm invitation to contact or schedule an appointment. "
            "Avoid any mention of SEO or keywords explicitly."
        )
    elif content_type == "Service Page":
        user_msg += (
            "\nPlease create a service page that thoroughly explains the service or treatment, benefits, the doctor's expertise, "
            "and ends with a call-to-action to book or learn more. Do not mention SEO. Focus on the patient perspective."
        )
    elif content_type == "Blog Post":
        user_msg += (
            "\nCreate a compelling blog post using a clear, engaging tone. Provide valuable insights and relevant details. "
            "No references to SEO, just helpful information for the reader."
        )
    elif content_type == "About Us":
        user_msg += (
            "\nCreate an 'About Us' page that describes the practice's background, values, and expertise. "
            "Include the doctor's credentials and an inviting closing statement. No SEO references."
        )
    else:
        user_msg += "\nWrite the content in a professional, patient-friendly tone without mentioning SEO."

    # If a location or focus keyword is provided, we let the AI incorporate it subtly, but no explicit mention of "SEO" or "keyword usage."
    # We do not add any line that says "use the keyword." We'll rely on the model to incorporate location/focus term naturally if it fits.

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        content = response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        content = f"Error: {e}"
    
    return content

# ===============================
#         OUTLINE GENERATION
# ===============================
st.header("Generate Outline")
if not required_fields:
    if st.button("Generate Outline"):
        details = {
            "content_type": st.session_state.content_type,
            "practice_name": st.session_state.practice_name,
            "practice_specialty": st.session_state.practice_specialty,
            "location": st.session_state.location,
            "doctor_name": st.session_state.doctor_name,
            "doctor_credentials": st.session_state.doctor_credentials,
            "tone": st.session_state.tone or "Professional",
            "service_name": st.session_state.get("service_name", ""),
            "blog_topic": st.session_state.get("blog_topic", ""),
            "primary_keyword": st.session_state.get("primary_keyword", ""),  # optional
            "additional_notes": st.session_state.get("additional_notes", "")
        }
        outline = generate_outline(details)
        st.session_state.outline = outline

if st.session_state.get("outline"):
    st.subheader("Outline (Editable)")
    st.text_area("Edit Outline Before Generating Content:", 
                value=st.session_state.outline, 
                key="outline", 
                height=300)
    
    # ===============================
    #        CONTENT GENERATION
    # ===============================
    if st.button("Generate Content from Outline"):
        details = {
            "content_type": st.session_state.content_type,
            "practice_name": st.session_state.practice_name,
            "practice_specialty": st.session_state.practice_specialty,
            "location": st.session_state.location,
            "doctor_name": st.session_state.doctor_name,
            "doctor_credentials": st.session_state.doctor_credentials,
            "tone": st.session_state.tone or "Professional",
            "service_name": st.session_state.get("service_name", ""),
            "blog_topic": st.session_state.get("blog_topic", ""),
            "primary_keyword": st.session_state.get("primary_keyword", ""),  # internal
            "additional_notes": st.session_state.get("additional_notes", "")
        }
        content = generate_content(details, st.session_state.outline)
        st.session_state.content = content

# ===============================
#      DISPLAY GENERATED TEXT
# ===============================
if st.session_state.get("content"):
    st.subheader("Final Generated Content")
    st.markdown(st.session_state.content)
    st.text_area("Full Text (for copy or manual edits):", value=st.session_state.content, height=300)

    # Quick content checks (just to remind you if something is missing):
    content_text = st.session_state.content
    word_count = len(content_text.split())
    st.write(f"**Word Count:** {word_count}")

    # Check if doctor name or practice name is present, etc.:
    if content_type != "Blog Post" and practice_name and practice_name not in content_text:
        st.warning(f"Note: The practice name ('{practice_name}') does not appear in the content.")
    if doctor_name and doctor_name not in content_text:
        st.warning(f"Note: The doctor's name ('{doctor_name}') does not appear in the content.")
