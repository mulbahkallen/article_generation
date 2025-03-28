import streamlit as st
import openai
import json
from pathlib import Path

# Set page configuration for the Streamlit app
st.set_page_config(page_title="Medical Content AI Generator", layout="wide")

st.title("AI Medical Content Generator")
st.write("Generate high-quality medical website content with an outline-first approach, ensuring E-E-A-T compliance and SEO optimization.")

# OpenAI API Key setup: retrieve from Streamlit secrets or ask user to input
if "openai_api_key" in st.secrets:
    openai.api_key = st.secrets["openai_api_key"]
else:
    api_input = st.text_input("Enter OpenAI API Key:", type="password")
    if api_input:
        openai.api_key = api_input
# If no API key is provided, halt the app
if not openai.api_key:
    st.error("Please provide a valid OpenAI API key to use this app.")
    st.stop()

# Functions to load and save client/project templates
TEMPLATE_FILE = "templates.json"

def load_templates():
    """Load templates from a JSON file (if it exists)."""
    if Path(TEMPLATE_FILE).exists():
        try:
            with open(TEMPLATE_FILE, "r") as f:
                data = json.load(f)
            # Support both list or dict format in JSON
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

# Initialize the template list in session state (to avoid reloading on every run)
if "templates" not in st.session_state:
    st.session_state.templates = load_templates()

# Sidebar: Template selection and management
st.sidebar.header("Client/Project Templates")
template_names = ["(None)"] + [t["name"] for t in st.session_state.templates]
selected_template = st.sidebar.selectbox("Load Template", options=template_names)
if selected_template and selected_template != "(None)":
    tmpl = next((t for t in st.session_state.templates if t["name"] == selected_template), None)
    if tmpl:
        # Apply template values to the input fields (only if a new template is selected)
        if st.session_state.get("last_loaded_template") != selected_template:
            for key, val in tmpl.items():
                if key == "name":
                    continue  # skip template name field
                st.session_state[key] = val
            st.session_state.last_loaded_template = selected_template
# If "(None)" is selected, clear the last_loaded_template marker (fields remain as is)
if selected_template == "(None)":
    st.session_state.last_loaded_template = None

# Sidebar: Option to save current inputs as a new template
st.sidebar.subheader("Save Current as Template")
new_template_name = st.sidebar.text_input("Template Name", value="", placeholder="e.g. Dr. Smith Cardiology")
if st.sidebar.button("Save Template"):
    if not new_template_name:
        st.sidebar.error("Please provide a name for the template.")
    else:
        # Prepare template data from current inputs
        template_data = {
            "name": new_template_name,
            "practice_name": st.session_state.get("practice_name", ""),
            "doctor_name": st.session_state.get("doctor_name", ""),
            "doctor_credentials": st.session_state.get("doctor_credentials", ""),
            "practice_specialty": st.session_state.get("practice_specialty", ""),
            "location": st.session_state.get("location", ""),
            "tone": st.session_state.get("tone", "")
        }
        # Prevent duplicate template names
        if any(t for t in st.session_state.templates if t["name"].strip().lower() == new_template_name.strip().lower()):
            st.sidebar.error("A template with this name already exists. Choose a different name.")
        else:
            st.session_state.templates.append(template_data)
            if save_templates(st.session_state.templates):
                st.sidebar.success(f"Template '{new_template_name}' saved.")
                # Update template dropdown options
                template_names = ["(None)"] + [t["name"] for t in st.session_state.templates]
            else:
                st.sidebar.error("An error occurred while saving the template.")

# Main input section for project and content details
st.header("Project Details")
# Common fields for all content types
practice_name = st.text_input("Practice/Clinic Name", value=st.session_state.get("practice_name", ""), key="practice_name", help="Name of the medical practice or clinic.")
doctor_name = st.text_input("Doctor's Name", value=st.session_state.get("doctor_name", ""), key="doctor_name", help="Name of the primary doctor or practitioner at the clinic.")
doctor_credentials = st.text_area("Doctor Credentials/Experience", value=st.session_state.get("doctor_credentials", ""), key="doctor_credentials", help="e.g. Board-certified cardiologist with 15 years of experience.")
practice_specialty = st.text_input("Practice Specialty/Field", value=st.session_state.get("practice_specialty", ""), key="practice_specialty", help="Primary medical domain of the practice (e.g. Cardiology, Dentistry).")
location = st.text_input("Location (City/Region)", value=st.session_state.get("location", ""), key="location", help="Geographic location of the practice (for local context).")
tone = st.text_input("Preferred Tone/Style", value=st.session_state.get("tone", ""), key="tone", help="Tone/style for the content (e.g. Compassionate, Professional, Friendly).")

st.header("Content Specification")
content_type = st.selectbox("Content Type", ["Homepage", "Service Page", "Blog Post", "About Us"], key="content_type")
# Fields specific to the selected content type
if st.session_state.content_type == "Blog Post":
    topic = st.text_input("Blog Topic or Title", value=st.session_state.get("blog_topic", ""), key="blog_topic", help="Topic or title of the blog post.")
    primary_keyword = st.text_input("Primary SEO Keyword (optional)", value=st.session_state.get("primary_keyword", ""), key="primary_keyword", help="Main keyword to target (optional, for SEO).")
elif st.session_state.content_type == "Service Page":
    service_name = st.text_input("Service or Treatment Name", value=st.session_state.get("service_name", ""), key="service_name", help="Name of the medical service or treatment (e.g. Teeth Whitening, Knee Replacement).")
    primary_keyword = st.text_input("Primary SEO Keyword (optional)", value=st.session_state.get("primary_keyword", ""), key="primary_keyword", help="Main keyword to target (optional, e.g. 'teeth whitening NYC').")
elif st.session_state.content_type == "Homepage":
    primary_keyword = st.text_input("Primary SEO Keyword (optional)", value=st.session_state.get("primary_keyword", ""), key="primary_keyword", help="Main keyword or phrase for SEO (e.g. 'cardiology clinic in Denver').")
    # No additional specific field for Homepage beyond common fields
elif st.session_state.content_type == "About Us":
    primary_keyword = st.text_input("Primary SEO Keyword (optional)", value=st.session_state.get("primary_keyword", ""), key="primary_keyword", help="Main keyword (optional, e.g. 'about cardiology practice Denver').")
    # About Us may not need a separate topic field; it will use practice and doctor info

additional_notes = st.text_area("Additional Notes/Instructions", value=st.session_state.get("additional_notes", ""), key="additional_notes", help="Any extra details or specific points to include (optional).")

# Basic validation for required fields before enabling generation
required_fields = []
# Practice name and specialty are generally needed (specialty can be derived from doctor credentials if not provided for About Us)
if not practice_name:
    required_fields.append("Practice/Clinic Name")
if not practice_specialty and content_type != "About Us":
    required_fields.append("Practice Specialty")
# Specific requirements per content type
if content_type == "Service Page" and not st.session_state.get("service_name"):
    required_fields.append("Service Name")
if content_type == "Blog Post" and not st.session_state.get("blog_topic"):
    required_fields.append("Blog Topic")
# Ensure key fields for credibility are provided for certain types
if content_type in ["Homepage", "About Us", "Service Page"] and not doctor_name:
    required_fields.append("Doctor's Name")
if content_type in ["Homepage", "About Us", "Service Page"] and not doctor_credentials:
    required_fields.append("Doctor Credentials")

if required_fields:
    st.warning("Please provide the following required field(s) before generating content: " + ", ".join(required_fields))

# Define functions to interact with the OpenAI API for outline and content generation
def generate_outline(details):
    """
    Generate a detailed outline for the specified content type using the provided details.
    """
    content_type = details["content_type"]
    # Construct a system message emphasizing quality (E-E-A-T) and clarity
    system_msg = (
        "You are an expert copywriter specializing in high-quality medical content. "
        "You will create a thorough outline for a piece of website content, ensuring it covers all important aspects with a logical structure. "
        "The outline should reflect Experience, Expertise, Authoritativeness, and Trustworthiness (E-E-A-T) principles and be tailored to the content type."
    )
    # Build the user prompt with relevant information
    if content_type == "Homepage":
        user_msg = (
            f"Create a detailed outline for a homepage of a medical practice website.\n"
            f"Practice Name: {details['practice_name']}\n"
            f"Specialty: {details['practice_specialty']}\n"
            f"Location: {details['location']}\n"
            f"Doctor: {details['doctor_name']}, {details['doctor_credentials']}\n"
            f"Tone: {details['tone']}\n"
            "Requirements:\n"
            "- Start with a welcome or hero section that addresses the visitor's needs or concerns and introduces the practice in a patient-friendly way.\n"
            "- Include a section highlighting key services or specialties offered (especially related to the specialty above), phrased in terms of benefits to the patient.\n"
            "- Include a section that establishes trust: e.g., the doctor's credentials/experience, any patient testimonials or years of service.\n"
            "- Provide a brief overview of the practice's values or mission (to show authenticity and care).\n"
            "- End with a clear call-to-action (e.g., contact or appointment invitation).\n"
            f"{('- Emphasize SEO keyword: ' + details['primary_keyword'] + ' where appropriate.\n') if details['primary_keyword'] else ''}"
            f"{('- Additional notes: ' + details['additional_notes'] + '\n') if details['additional_notes'] else ''}"
            "Output the outline with clear section headings and brief bullet points for each."
        )
    elif content_type == "Service Page":
        user_msg = (
            f"Create a detailed outline for a service page on a medical website.\n"
            f"Practice Name: {details['practice_name']}\n"
            f"Service: {details['service_name']} ({details['practice_specialty']})\n"
            f"Location: {details['location']}\n"
            f"Doctor: {details['doctor_name']}, {details['doctor_credentials']}\n"
            f"Tone: {details['tone']}\n"
            "Requirements:\n"
            "- Introduction to the service or treatment, explaining what it is and who might need it, in patient-friendly language.\n"
            f"- Details about the procedure/treatment '{details['service_name']}' (how it works, what to expect).\n"
            "- Benefits and outcomes of the service (why it's important or advantageous for the patient).\n"
            "- Why choose this practice/doctor for this service: highlight experience, success stories, or unique expertise to build trust.\n"
            "- (If relevant) FAQs or common patient questions about the service, each with brief answers.\n"
            "- Conclusion with a call-to-action to contact the practice for this service.\n"
            f"{('- Ensure to naturally include the keyword: ' + details['primary_keyword'] + '.\n') if details['primary_keyword'] else ''}"
            f"{('- Additional notes: ' + details['additional_notes'] + '\n') if details['additional_notes'] else ''}"
            "Provide the outline with clear headings and sub-points."
        )
    elif content_type == "Blog Post":
        user_msg = (
            f"Create a detailed outline for a medical blog post.\n"
            f"Topic: {details['blog_topic']}\n"
            f"Related Practice/Specialty: {details['practice_specialty']} (for context)\n"
            f"Author: Dr. {details['doctor_name']} ({details['doctor_credentials']})\n"
            f"Tone: {details['tone']}\n"
            "Requirements:\n"
            "- A compelling introduction that introduces the topic and why it matters to the reader (patient perspective).\n"
            "- Several main sections covering key points or subtopics related to the blog topic, each with informative points (ensure medical information is accurate and explained simply).\n"
            "- (If applicable) A section for practical tips, myths vs facts, or FAQs to add value for the reader.\n"
            "- A conclusion that summarizes the insights and possibly encourages the reader to take next steps (like consulting the practice or reading related resources).\n"
            f"{('- Aim to include the SEO keyword: ' + details['primary_keyword'] + ' in headings or content.\n') if details['primary_keyword'] else ''}"
            f"{('- Additional notes: ' + details['additional_notes'] + '\n') if details['additional_notes'] else ''}"
            "Output the outline with clear section titles and bullet points."
        )
    elif content_type == "About Us":
        user_msg = (
            f"Create a detailed outline for an 'About Us' page of a medical practice.\n"
            f"Practice Name: {details['practice_name']}\n"
            f"Specialty: {details['practice_specialty']}\n"
            f"Location: {details['location']}\n"
            f"Doctor: {details['doctor_name']}, {details['doctor_credentials']}\n"
            f"Tone: {details['tone']}\n"
            "Requirements:\n"
            "- An opening section that introduces the practice briefly (who you are, what you do) in a friendly tone.\n"
            "- A history/background section: how the practice started or the mission and values driving it.\n"
            "- A section highlighting the doctor's (and any key team members') credentials, experience, and philosophy of care (to establish expertise and trust).\n"
            "- Any notable achievements, awards, or community involvement that add credibility.\n"
            "- A concluding section that invites the reader to become a patient or get in touch, reinforcing a welcoming message.\n"
            f"{('- Additional notes: ' + details['additional_notes'] + '\n') if details['additional_notes'] else ''}"
            "Provide the outline with clear headings and sub-sections."
        )
    else:
        # Generic fallback (should not happen given fixed content_type choices)
        user_msg = (
            f"Create a detailed outline for a {content_type} content page.\n"
            f"Include all important sections and details as appropriate.\n"
            "Output the outline in a clear, structured format."
        )
    # Call the OpenAI API to get the outline
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            temperature=0.5,
            max_tokens=500
        )
        outline = response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        outline = f"Error: {e}"
    return outline

def generate_content(details, outline):
    """
    Generate full content based on the given outline and details.
    """
    content_type = details["content_type"]
    # System message reinforcing writing style and quality
    system_msg = (
        "You are a skilled medical content writer who produces engaging, accurate, and trustworthy content. "
        "Follow E-E-A-T principles (demonstrate experience, expertise, authority, and trustworthiness) in the writing. "
        "The writing should be patient-centered, easy to understand, and SEO-friendly."
    )
    # Construct the user prompt to expand the outline into full content
    if content_type == "Homepage":
        user_msg = (
            f"Write a complete **homepage** for the medical practice **{details['practice_name']}** based on the outline below.\n"
            f"OUTLINE:\n{outline}\n\n"
            "Guidelines:\n"
            f"- Maintain a {details['tone']} tone, welcoming and professional.\n"
            "- The opening should empathize with the visitor and highlight how the practice can meet their needs.\n"
            "- Clearly describe the practice's services or specialties, focusing on benefits to the patient.\n"
            f"- Mention Dr. {details['doctor_name']}'s qualifications (from the outline) to build trust.\n"
            "- Keep language accessible (no unnecessary jargon; explain terms simply if used).\n"
            "- End with a strong call-to-action encouraging the reader to contact the clinic or schedule an appointment.\n"
            f"{('- Ensure to use the keyword "' + details['primary_keyword'] + '" at least once naturally.\n') if details['primary_keyword'] else ''}"
        )
    elif content_type == "Service Page":
        user_msg = (
            f"Write a complete **service page** for **{details['service_name']}** offered by **{details['practice_name']}**, using the outline below.\n"
            f"OUTLINE:\n{outline}\n\n"
            "Guidelines:\n"
            f"- Use a {details['tone']} tone that is informative and reassuring.\n"
            f"- Explain what {details['service_name']} is and its benefits to the patient in clear terms.\n"
            "- Provide details on how the service/procedure works or what a patient can expect.\n"
            f"- Highlight why {details['practice_name']} and Dr. {details['doctor_name']} are the right choice for this service (experience, expertise, successful outcomes).\n"
            "- Address common questions or concerns patients might have about the service, if possible.\n"
            "- Conclude with a call-to-action for readers to contact {details['practice_name']} for this service.\n"
            f"{('- Include the keyword "' + details['primary_keyword'] + '" naturally in the content.\n') if details['primary_keyword'] else ''}"
        )
    elif content_type == "Blog Post":
        user_msg = (
            f"Write a **blog post** based on the outline below, covering the topic: **{details['blog_topic']}**.\n"
            f"OUTLINE:\n{outline}\n\n"
            "Guidelines:\n"
            f"- Write in a {details['tone']} tone that is engaging and easy to follow.\n"
            "- Expand each outline point into one or more paragraphs with informative, accurate content. Use subheadings as given by the outline.\n"
            "- Ensure explanations are clear to laypersons; define any medical terms in simple language.\n"
            "- Incorporate actionable insights or tips if relevant, to add value for the reader.\n"
            "- Avoid a dry or overly formal style – it should feel like a conversation with a knowledgeable professional.\n"
            f"{('- Use the target keyword "' + details['primary_keyword'] + '" in the content where it fits naturally (for SEO).\n') if details['primary_keyword'] else ''}"
            "- Conclude the post with a helpful summary or an encouraging note (e.g., inviting the reader to consult the clinic for further guidance)."
        )
    elif content_type == "About Us":
        user_msg = (
            f"Write an **About Us** page for **{details['practice_name']}** using the outline below.\n"
            f"OUTLINE:\n{outline}\n\n"
            "Guidelines:\n"
            f"- Maintain a {details['tone']} tone that reflects the practice's values (professional yet approachable).\n"
            "- Turn the outline points into paragraphs: describe the practice’s mission and history in an engaging way, and detail Dr. " 
            f"{details['doctor_name']}'s (and any team members') qualifications and approach to care.\n"
            "- Highlight any key achievements or unique aspects of the practice to build authority.\n"
            "- Ensure the content conveys trust and compassion, helping readers feel confident in choosing this practice.\n"
            "- End with a friendly call-to-action, inviting the reader to become a patient or get in touch."
        )
    else:
        # Fallback for unexpected content types
        user_msg = f"Write a full content piece based on the outline:\n{outline}\n"
    # Call the OpenAI API for content generation
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            temperature=0.7,
            max_tokens=1500
        )
        content = response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        content = f"Error: {e}"
    return content

# Outline Generation Step
st.header("Generate Outline")
outline = ""
if not required_fields:  # only allow generating outline if required inputs are filled
    if st.button("Generate Outline"):
        # Gather details from the current state for outline generation
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
            "primary_keyword": st.session_state.get("primary_keyword", ""),
            "additional_notes": st.session_state.get("additional_notes", "")
        }
        outline = generate_outline(details)
        st.session_state.outline = outline  # store the outline in session state for later use

# If an outline has been generated, display it for review/editing
if st.session_state.get("outline"):
    st.subheader("Outline")
    st.text_area("Generated Outline (you can edit it below before generating content):", 
                value=st.session_state.outline, 
                key="outline", 
                height=300)

    # Content Generation Step (appears after an outline is available)
    if st.button("Generate Content from Outline"):
        # Reuse the details and updated outline from session state
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
            "primary_keyword": st.session_state.get("primary_keyword", ""),
            "additional_notes": st.session_state.get("additional_notes", "")
        }
        content = generate_content(details, st.session_state.outline)
        st.session_state.content = content  # store generated content

# Display the generated content if available
if st.session_state.get("content"):
    st.subheader("Generated Content")
    # Show the content in markdown format for a nice preview
    st.markdown(st.session_state.content)
    # Also provide the raw text in a textarea for easy copy-paste or further editing
    st.text_area("Full Content (for copying or manual editing):", value=st.session_state.content, height=300)
    # Basic feedback on the content
    content_text = st.session_state.content
    word_count = len(content_text.split())
    st.write(f"**Word Count:** {word_count}")
    # Check for presence of key elements and give feedback
    if content_type in ["Homepage", "About Us", "Service Page"]:
        if doctor_name and doctor_name not in content_text:
            st.warning(f"Note: The doctor's name ('{doctor_name}') is not mentioned in the content. Consider adding it to enhance trust.")
    if practice_name and practice_name not in content_text:
        st.warning(f"Note: The practice name ('{practice_name}') is not mentioned in the content. Consider including it for branding and trust.")
    if st.session_state.get("primary_keyword"):
        keyword = st.session_state.primary_keyword
        if keyword and keyword.lower() not in content_text.lower():
            st.info(f"Note: The target keyword ('{keyword}') doesn't appear in the content. You may want to incorporate it for better SEO.")
