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
    tab1, tab2, tab3 = st.tabs(["🎯 Quick Generate", "🔧 Advanced Options", "📝 Content History"])
    
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
        st.header("Advanced Content Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Detailed Configuration")
            
            # Business details
            business_name_adv = st.text_input("Business Name", key="adv_business")
            industry_adv = st.selectbox("Industry", [
                "Healthcare", "Legal", "Real Estate", "Automotive", "Restaurant",
                "Fitness", "Beauty/Spa", "Construction", "Technology", "Consulting",
                "Education", "Finance", "Retail", "Other"
            ], key="adv_industry")
            
            content_type_adv = st.selectbox("Content Type", [
                "Home Page", "Service Page", "About Page", "Blog Post",
                "Landing Page", "Product Page", "Category Page"
            ], key="adv_content_type")
            
            # Word count
            word_count = st.slider("Target Word Count", 200, 2000, 600, step=50)
            
            # Custom sections
            st.subheader("Content Sections")
            section_options = [
                "Hero Section", "Service Overview", "Benefits Section",
                "Process/How It Works", "Testimonials", "FAQ",
                "Call to Action", "About Team", "Service Areas",
                "Before/After", "Pricing", "Contact Information"
            ]
            
            selected_sections = st.multiselect("Select Sections to Include", section_options)
        
        with col2:
            st.subheader("SEO & Keywords")
            primary_keywords = st.text_area("Primary Keywords", 
                placeholder="Main keywords for this page", height=80)
            secondary_keywords = st.text_area("Secondary Keywords", 
                placeholder="Supporting keywords", height=80)
            
            st.subheader("Brand Voice")
            brand_personality = st.multiselect("Brand Personality", [
                "Professional", "Friendly", "Authoritative", "Innovative",
                "Trustworthy", "Approachable", "Expert", "Local"
            ])
            
            custom_requirements = st.text_area("Custom Requirements",
                placeholder="Any specific requirements, style preferences, or information to include...",
                height=100)
        
        # Advanced generate button
        if st.button("🎨 Generate Advanced Content", type="primary"):
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
                    'brand_personality': ', '.join(brand_personality) if brand_personality else 'Professional'
                }
                
                with st.spinner("Creating customized content..."):
                    prompt = create_content_prompt(
                        content_type_adv, business_info, all_keywords,
                        selected_sections, word_count, custom_requirements
                    )
                    content = generator.generate_content(prompt, max_tokens=3000)
                    
                    if content:
                        st.session_state.generated_content = content
                        st.session_state.content_history.append({
                            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                            'type': content_type_adv,
                            'business': business_name_adv,
                            'content': content
                        })
                        st.success("Advanced content generated successfully!")
    
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
