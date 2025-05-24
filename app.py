import streamlit as st
import openai
import json
import time
from datetime import datetime
from typing import List, Dict
from pathlib import Path

import streamlit as st
import openai
import json
import re
from typing import List, Dict, Any
import time

# Configure page
st.set_page_config(
    page_title="Professional Content Generator",
    page_icon="✍️",
    layout="wide"
)

# Initialize session state
if 'generated_content' not in st.session_state:
    st.session_state.generated_content = ""
if 'content_history' not in st.session_state:
    st.session_state.content_history = []

class ContentGenerator:
    def __init__(self, api_key: str):
        openai.api_key = api_key
        
    def generate_content(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate content using OpenAI API"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Error generating content: {str(e)}")
            return ""
    
    def get_system_prompt(self) -> str:
        return """You are a professional content writer specializing in creating engaging, human-like content for websites. Your writing should be:

1. Professional yet conversational
2. Engaging and compelling
3. SEO-optimized but natural
4. Free from generic AI phrases
5. Tailored to the specific business/industry
6. Structured with clear headings and flow
7. Include natural keyword integration

Avoid these AI-typical phrases:
- "In today's digital landscape"
- "cutting-edge solutions"
- "game-changing"
- "revolutionary"
- "seamless experience"
- "world-class"
- "state-of-the-art"
- "leverage synergies"

Instead, use:
- Specific, concrete benefits
- Real-world scenarios
- Direct, clear language
- Industry-specific terminology
- Customer-focused messaging"""

def create_template_prompt(template_sections: List[Dict], business_info: Dict, 
                          keywords: List[str], word_count: int = None, 
                          custom_requirements: str = None) -> str:
    """Create a prompt based on the template structure"""
    
    # Build section descriptions
    section_descriptions = {
        "H1": "Create a compelling, attention-grabbing headline that immediately communicates the main value proposition",
        "Intro": "Write 1-2 engaging paragraphs that hook the reader and frame the topic or service",
        "Sub-H2": "Create a secondary header that introduces the next section of content",
        "Body-Copy": "Write informative paragraph(s) that provide detailed information under the preceding header",
        "Bullet-List": "Create a bulleted list of benefits, features, symptoms, or key points (3-6 items)",
        "Quote-Testimonial": "Write a 20-40 word testimonial quote with customer name and relevant details",
        "FAQ-Pair": "Create a frequently asked question with a 2-3 sentence informative answer",
        "CTA": "Write a compelling call-to-action with clear next steps and action-oriented language",
        "Closing": "Create a reassuring closing statement that encourages the next step",
        "Service-Overview": "Provide a comprehensive overview of the service or product offering",
        "Benefits-Section": "Detail the key advantages and value propositions for customers",
        "Process-Steps": "Explain the step-by-step process or methodology in clear, actionable steps",
        "Team-Bio": "Highlight team credentials, expertise, and what makes them qualified",
        "Pricing-Info": "Present pricing information or consultation details in a clear, accessible way",
        "Contact-Info": "Provide clear contact information including location, hours, and contact methods"
    }
    
    prompt = f"""Create professional web content for {business_info['business_name']}, a {business_info['industry']} business.

Business Details:
- Name: {business_info['business_name']}
- Industry: {business_info['industry']}
- Target Audience: {business_info.get('target_audience', 'General consumers')}

CONTENT STRUCTURE - Create content in this exact order:
"""
    
    for i, section in enumerate(template_sections):
        section_type = section['type']
        section_name = section['name']
        
        prompt += f"\n{i+1}. **{section_name.upper()}**\n"
        prompt += f"   {section_descriptions.get(section_type, 'Create appropriate content for this section.')}\n"
    
    # Add keyword requirements
    if keywords:
        keyword_text = ", ".join(keywords)
        prompt += f"\n\nSEO KEYWORDS to integrate naturally: {keyword_text}"
        prompt += "\nDistribute these keywords naturally throughout the content sections."
    
    # Add word count
    if word_count:
        prompt += f"\n\nTARGET WORD COUNT: Approximately {word_count} words total."
    
    # Add custom requirements
    if custom_requirements:
        prompt += f"\n\nCUSTOM REQUIREMENTS: {custom_requirements}"
    
    prompt += """

WRITING GUIDELINES:
- Use professional, engaging language that doesn't sound AI-generated
- Avoid generic phrases like "cutting-edge," "world-class," "seamless experience"
- Include specific, concrete benefits rather than vague promises  
- Write in a conversational yet professional tone
- Ensure smooth flow between sections
- Make each section distinct and valuable
- Include clear formatting with headers and structure
- Focus on customer benefits and real-world value

Format the output with clear section headers and proper structure for web content."""
    
    return prompt

def create_content_prompt(content_type: str, business_info: Dict, keywords: List[str], 
                         sections: List[str] = None, word_count: int = None, 
                         custom_requirements: str = None) -> str:
    """Create a detailed prompt for content generation"""
    
    base_prompts = {
        "Home Page": f"""Create a compelling home page for {business_info['business_name']}, a {business_info['industry']} business.
        
Business Details:
- Industry: {business_info['industry']}
- Location: {business_info.get('location', 'Not specified')}
- Target Audience: {business_info.get('target_audience', 'General consumers')}
- Unique Value Proposition: {business_info.get('value_prop', 'Professional services')}

Structure the content with:
- Compelling headline that addresses customer pain points
- Clear value proposition
- Service highlights
- Trust indicators
- Strong call-to-action""",

        "Service Page": f"""Create a detailed service page for {business_info['service_name']} offered by {business_info['business_name']}.
        
Service Details:
- Service: {business_info['service_name']}
- Industry: {business_info['industry']}
- Target Audience: {business_info.get('target_audience', 'General consumers')}
- Key Benefits: {business_info.get('benefits', 'Professional expertise')}

Structure should include:
- Service overview
- Benefits and features
- Process/methodology
- Pricing or consultation CTA
- FAQ section""",

        "Blog Post": f"""Write an informative blog post about {business_info['topic']} for {business_info['business_name']}'s audience.
        
Blog Details:
- Topic: {business_info['topic']}
- Industry: {business_info['industry']}
- Target Audience: {business_info.get('target_audience', 'General readers')}
- Purpose: {business_info.get('purpose', 'Educate and inform')}

Structure:
- Engaging introduction
- Well-organized main points
- Actionable insights
- Conclusion with next steps""",

        "About Page": f"""Create an engaging About page for {business_info['business_name']}.
        
Company Details:
- Business: {business_info['business_name']}
- Industry: {business_info['industry']}
- Founded: {business_info.get('founded', 'Recently established')}
- Mission: {business_info.get('mission', 'Serving customers with excellence')}
- Team Size: {business_info.get('team_size', 'Professional team')}

Include:
- Company story and mission
- Team highlights
- Values and approach
- Credentials and experience
- Personal touch that builds trust"""
    }
    
    prompt = base_prompts.get(content_type, f"Create professional {content_type.lower()} content for {business_info['business_name']}.")
    
    # Add keyword requirements
    if keywords:
        keyword_text = ", ".join(keywords)
        prompt += f"\n\nSEO Keywords to naturally integrate: {keyword_text}"
        prompt += "\nIntegrate these keywords naturally throughout the content without keyword stuffing."
    
    # Add custom sections
    if sections:
        prompt += f"\n\nRequired sections: {', '.join(sections)}"
    
    # Add word count
    if word_count:
        prompt += f"\n\nTarget word count: approximately {word_count} words."
    
    # Add custom requirements
    if custom_requirements:
        prompt += f"\n\nAdditional requirements: {custom_requirements}"
    
    prompt += "\n\nEnsure the content sounds natural, professional, and engaging. Avoid generic AI language."
    
    return prompt

def main():
    st.title("🚀 Professional Content Generator")
    st.markdown("*Create engaging, SEO-optimized content for your clients*")
    
    # Sidebar for API configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        api_key = st.text_input("OpenAI API Key", type="password", 
                               help="Enter your OpenAI API key")
        
        if not api_key:
            st.warning("Please enter your OpenAI API key to continue")
            st.stop()
    
    # Initialize content generator
    generator = ContentGenerator(api_key)
    
    # Main interface tabs
    tab1, tab2, tab3 = st.tabs(["🎯 Quick Generate", "🏗️ Template Builder", "📝 Content History"])
    
    with tab1:
        st.header("Quick Content Generation")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Business Information
            st.subheader("Business Information")
            business_name = st.text_input("Business Name*", placeholder="e.g., Smith Dental Practice")
            industry = st.selectbox("Industry*", [
                "Healthcare", "Legal", "Real Estate", "Automotive", "Restaurant",
                "Fitness", "Beauty/Spa", "Construction", "Technology", "Consulting",
                "Education", "Finance", "Retail", "Other"
            ])
            location = st.text_input("Location", placeholder="e.g., Denver, CO")
            
            # Content Type Selection
            st.subheader("Content Type")
            content_type = st.selectbox("Select Content Type*", [
                "Home Page", "Service Page", "About Page", "Blog Post", 
                "Contact Page", "FAQ Page", "Testimonials Page"
            ])
            
            # Additional fields based on content type
            additional_info = {}
            if content_type == "Service Page":
                additional_info['service_name'] = st.text_input("Service Name*", 
                    placeholder="e.g., Teeth Whitening, Personal Injury Law")
            elif content_type == "Blog Post":
                additional_info['topic'] = st.text_input("Blog Topic*", 
                    placeholder="e.g., Benefits of Regular Dental Checkups")
        
        with col2:
            st.subheader("SEO Keywords")
            keywords_input = st.text_area("Keywords (one per line)", 
                placeholder="dental implants\ncosmetic dentistry\nDenver dentist",
                height=100)
            keywords = [k.strip() for k in keywords_input.split('\n') if k.strip()]
            
            st.subheader("Quick Options")
            target_audience = st.selectbox("Target Audience", [
                "General consumers", "Business owners", "Young professionals",
                "Families", "Seniors", "Students", "Industry professionals"
            ])
            
            tone = st.selectbox("Tone", [
                "Professional", "Friendly", "Authoritative", "Conversational"
            ])
        
        # Generate button
        if st.button("🚀 Generate Content", type="primary", use_container_width=True):
            if not business_name or not industry:
                st.error("Please fill in required fields (marked with *)")
            else:
                # Prepare business info
                business_info = {
                    'business_name': business_name,
                    'industry': industry,
                    'location': location,
                    'target_audience': target_audience,
                    **additional_info
                }
                
                # Generate content
                with st.spinner("Generating professional content..."):
                    prompt = create_content_prompt(content_type, business_info, keywords)
                    content = generator.generate_content(prompt)
                    
                    if content:
                        st.session_state.generated_content = content
                        st.session_state.content_history.append({
                            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                            'type': content_type,
                            'business': business_name,
                            'content': content
                        })
                        st.success("Content generated successfully!")
    
    with tab2:
        st.header("Template Builder")
        st.markdown("*Build your content page structure by selecting sections in order*")
        
        # Initialize template in session state
        if 'page_template' not in st.session_state:
            st.session_state.page_template = []
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📋 Available Content Sections")
            st.markdown("*Click to add sections to your template*")
            
            # Define content section options with descriptions
            section_definitions = {
                "H1": {
                    "name": "H1 - Main Headline",
                    "description": "Main page headline (1 only)",
                    "icon": "🎯"
                },
                "Intro": {
                    "name": "Intro Paragraph",
                    "description": "1–2-paragraph hook that frames the topic or service",
                    "icon": "📝"
                },
                "Sub-H2": {
                    "name": "Sub-H2 Header",
                    "description": "Secondary header to split body content",
                    "icon": "📑"
                },
                "Body-Copy": {
                    "name": "Body Copy",
                    "description": "Paragraph(s) under a Sub-H2",
                    "icon": "📄"
                },
                "Bullet-List": {
                    "name": "Bullet List",
                    "description": "Benefits, symptoms, checklist, features, etc.",
                    "icon": "🔸"
                },
                "Quote-Testimonial": {
                    "name": "Quote/Testimonial",
                    "description": "20-40 words with customer name and title",
                    "icon": "💬"
                },
                "FAQ-Pair": {
                    "name": "FAQ Pair",
                    "description": "Question + 2-3-sentence answer",
                    "icon": "❓"
                },
                "CTA": {
                    "name": "Call to Action",
                    "description": "1-sentence prompt + button label/URL",
                    "icon": "🚀"
                },
                "Closing": {
                    "name": "Closing Statement",
                    "description": "Reassurance/next-step line (often before footer)",
                    "icon": "✅"
                },
                "Service-Overview": {
                    "name": "Service Overview",
                    "description": "Detailed explanation of service/product",
                    "icon": "🛠️"
                },
                "Benefits-Section": {
                    "name": "Benefits Section",
                    "description": "Key advantages and value propositions",
                    "icon": "⭐"
                },
                "Process-Steps": {
                    "name": "Process/How It Works",
                    "description": "Step-by-step process or methodology",
                    "icon": "🔄"
                },
                "Team-Bio": {
                    "name": "Team/About Section",
                    "description": "Staff credentials and expertise",
                    "icon": "👥"
                },
                "Pricing-Info": {
                    "name": "Pricing Information",
                    "description": "Cost details or consultation info",
                    "icon": "💰"
                },
                "Contact-Info": {
                    "name": "Contact Information",
                    "description": "Location, hours, contact details",
                    "icon": "📞"
                }
            }
            
            # Create buttons for each section type
            for section_key, section_info in section_definitions.items():
                col_btn1, col_btn2 = st.columns([3, 1])
                with col_btn1:
                    if st.button(f"{section_info['icon']} {section_info['name']}", 
                                key=f"add_{section_key}", use_container_width=True):
                        st.session_state.page_template.append({
                            'type': section_key,
                            'name': section_info['name'],
                            'description': section_info['description'],
                            'icon': section_info['icon']
                        })
                        st.rerun()
                with col_btn2:
                    st.markdown(f"<small>{section_info['description']}</small>", 
                               unsafe_allow_html=True)
        
        with col2:
            st.subheader("🏗️ Your Page Template")
            
            if st.session_state.page_template:
                st.markdown("*Your content will be generated in this order:*")
                
                # Display current template
                for i, section in enumerate(st.session_state.page_template):
                    col_section, col_up, col_down, col_remove = st.columns([6, 1, 1, 1])
                    
                    with col_section:
                        st.markdown(f"**{i+1}.** {section['icon']} {section['name']}")
                        st.caption(section['description'])
                    
                    with col_up:
                        if i > 0 and st.button("⬆️", key=f"up_{i}", help="Move up"):
                            st.session_state.page_template[i], st.session_state.page_template[i-1] = \
                                st.session_state.page_template[i-1], st.session_state.page_template[i]
                            st.rerun()
                    
                    with col_down:
                        if i < len(st.session_state.page_template) - 1 and st.button("⬇️", key=f"down_{i}", help="Move down"):
                            st.session_state.page_template[i], st.session_state.page_template[i+1] = \
                                st.session_state.page_template[i+1], st.session_state.page_template[i]
                            st.rerun()
                    
                    with col_remove:
                        if st.button("🗑️", key=f"remove_{i}", help="Remove section"):
                            st.session_state.page_template.pop(i)
                            st.rerun()
                    
                    st.divider()
                
                # Template actions
                col_clear, col_save = st.columns(2)
                with col_clear:
                    if st.button("🗑️ Clear Template", use_container_width=True):
                        st.session_state.page_template = []
                        st.rerun()
                
                with col_save:
                    # Could add template saving functionality here
                    st.markdown("*Template ready for generation*")
            
            else:
                st.info("👆 Click sections from the left to build your page template")
                
                # Quick template presets
                st.subheader("📋 Quick Templates")
                
                preset_templates = {
                    "Standard Service Page": [
                        {'type': 'H1', 'name': 'H1 - Main Headline', 'description': 'Main page headline', 'icon': '🎯'},
                        {'type': 'Intro', 'name': 'Intro Paragraph', 'description': 'Hook that frames the service', 'icon': '📝'},
                        {'type': 'Service-Overview', 'name': 'Service Overview', 'description': 'Detailed service explanation', 'icon': '🛠️'},
                        {'type': 'Benefits-Section', 'name': 'Benefits Section', 'description': 'Key advantages', 'icon': '⭐'},
                        {'type': 'Process-Steps', 'name': 'Process/How It Works', 'description': 'Step-by-step process', 'icon': '🔄'},
                        {'type': 'Quote-Testimonial', 'name': 'Quote/Testimonial', 'description': 'Customer testimonial', 'icon': '💬'},
                        {'type': 'FAQ-Pair', 'name': 'FAQ Pair', 'description': 'Common questions', 'icon': '❓'},
                        {'type': 'CTA', 'name': 'Call to Action', 'description': 'Conversion prompt', 'icon': '🚀'},
                        {'type': 'Closing', 'name': 'Closing Statement', 'description': 'Final reassurance', 'icon': '✅'}
                    ],
                    "Simple Landing Page": [
                        {'type': 'H1', 'name': 'H1 - Main Headline', 'description': 'Main page headline', 'icon': '🎯'},
                        {'type': 'Intro', 'name': 'Intro Paragraph', 'description': 'Compelling hook', 'icon': '📝'},
                        {'type': 'Benefits-Section', 'name': 'Benefits Section', 'description': 'Key benefits', 'icon': '⭐'},
                        {'type': 'Quote-Testimonial', 'name': 'Quote/Testimonial', 'description': 'Social proof', 'icon': '💬'},
                        {'type': 'CTA', 'name': 'Call to Action', 'description': 'Primary conversion', 'icon': '🚀'}
                    ],
                    "Blog Post Structure": [
                        {'type': 'H1', 'name': 'H1 - Main Headline', 'description': 'Article title', 'icon': '🎯'},
                        {'type': 'Intro', 'name': 'Intro Paragraph', 'description': 'Article introduction', 'icon': '📝'},
                        {'type': 'Sub-H2', 'name': 'Sub-H2 Header', 'description': 'Section header', 'icon': '📑'},
                        {'type': 'Body-Copy', 'name': 'Body Copy', 'description': 'Main content', 'icon': '📄'},
                        {'type': 'Bullet-List', 'name': 'Bullet List', 'description': 'Key points', 'icon': '🔸'},
                        {'type': 'Sub-H2', 'name': 'Sub-H2 Header', 'description': 'Another section', 'icon': '📑'},
                        {'type': 'Body-Copy', 'name': 'Body Copy', 'description': 'More content', 'icon': '📄'},
                        {'type': 'Closing', 'name': 'Closing Statement', 'description': 'Article conclusion', 'icon': '✅'},
                        {'type': 'CTA', 'name': 'Call to Action', 'description': 'Reader next step', 'icon': '🚀'}
                    ]
                }
                
                for template_name, template_structure in preset_templates.items():
                    if st.button(f"📋 Use {template_name}", key=f"preset_{template_name}"):
                        st.session_state.page_template = template_structure.copy()
                        st.rerun()
        
        # Business Information and Generation
        if st.session_state.page_template:
            st.header("🏢 Business Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                business_name_adv = st.text_input("Business Name*", key="adv_business")
                industry_adv = st.selectbox("Industry*", [
                    "Healthcare", "Legal", "Real Estate", "Automotive", "Restaurant",
                    "Fitness", "Beauty/Spa", "Construction", "Technology", "Consulting",
                    "Education", "Finance", "Retail", "Other"
                ], key="adv_industry")
                
                target_audience_adv = st.selectbox("Target Audience", [
                    "General consumers", "Business owners", "Young professionals",
                    "Families", "Seniors", "Students", "Industry professionals"
                ])
                
                # Word count
                word_count = st.slider("Target Word Count", 200, 3000, 800, step=100)
            
            with col2:
                st.subheader("SEO Keywords")
                primary_keywords = st.text_area("Primary Keywords (one per line)", 
                    placeholder="Main keywords for this page", height=80)
                secondary_keywords = st.text_area("Secondary Keywords (one per line)", 
                    placeholder="Supporting keywords", height=80)
                
                custom_requirements = st.text_area("Custom Requirements",
                    placeholder="Any specific requirements, style preferences, or information to include...",
                    height=80)
        
            # Template generate button
            if st.button("🎨 Generate Template Content", type="primary", use_container_width=True):
                if not business_name_adv or not industry_adv:
                    st.error("Please fill in business name and industry")
                else:
                    all_keywords = []
                    if primary_keywords:
                        all_keywords.extend([k.strip() for k in primary_keywords.split('\n') if k.strip()])
                    if secondary_keywords:
                        all_keywords.extend([k.strip() for k in secondary_keywords.split('\n') if k.strip()])
                    
                    business_info = {
                        'business_name': business_name_adv,
                        'industry': industry_adv,
                        'target_audience': target_audience_adv
                    }
                    
                    with st.spinner("Generating content using your template..."):
                        # Create template-based prompt
                        template_prompt = create_template_prompt(
                            st.session_state.page_template, business_info, 
                            all_keywords, word_count, custom_requirements
                        )
                        content = generator.generate_content(template_prompt, max_tokens=4000)
                        
                        if content:
                            st.session_state.generated_content = content
                            st.session_state.content_history.append({
                                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                                'type': 'Template Build',
                                'business': business_name_adv,
                                'content': content
                            })
                            st.success("Template content generated successfully!")
    
    with tab3:
        st.header("Content History")
        
        if st.session_state.content_history:
            for i, item in enumerate(reversed(st.session_state.content_history)):
                with st.expander(f"{item['type']} - {item['business']} ({item['timestamp']})"):
                    st.write(item['content'])
                    if st.button(f"Use This Content", key=f"use_{i}"):
                        st.session_state.generated_content = item['content']
                        st.success("Content loaded to main editor!")
        else:
            st.info("No content generated yet. Use the generation tabs to create content.")
    
    # Generated Content Display and Editor
    if st.session_state.generated_content:
        st.header("📝 Generated Content")
        
        # Content editor
        edited_content = st.text_area("Edit your content:", 
                                    value=st.session_state.generated_content, 
                                    height=400)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("💾 Save Changes"):
                st.session_state.generated_content = edited_content
                st.success("Changes saved!")
        
        with col2:
            if st.button("📋 Copy to Clipboard"):
                st.code(edited_content, language=None)
                st.info("Content ready to copy!")
        
        with col3:
            if st.button("🔄 Regenerate"):
                st.rerun()
        
        with col4:
            if st.button("🗑️ Clear"):
                st.session_state.generated_content = ""
                st.rerun()
        
        # Content analysis
        with st.expander("📊 Content Analysis"):
            word_count_analysis = len(edited_content.split())
            char_count = len(edited_content)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Word Count", word_count_analysis)
            with col2:
                st.metric("Character Count", char_count)
            with col3:
                reading_time = max(1, word_count_analysis // 200)
                st.metric("Reading Time", f"{reading_time} min")

if __name__ == "__main__":
    main()
