"""
PortfolioAI - Generative AI Service
Wraps Google Gemini API via official google-genai SDK for resume polish,
professional summaries, STAR project bullets, skills analysis, and career advice.
"""

import os
from flask import current_app
from google import genai
from google.genai import types


class AIServiceError(Exception):
    """Custom exception for Gemini AI service and API errors."""
    pass


class AIService:
    """Service encapsulating prompts and Gemini API calls."""

    @staticmethod
    def get_client():
        """Retrieve configured Gemini API client or raise AIServiceError."""
        api_key = (
            current_app.config.get("GEMINI_API_KEY")
            or os.environ.get("GEMINI_API_KEY", "")
        ).strip()

        if not api_key or api_key == "your_gemini_api_key_here":
            raise AIServiceError(
                "Gemini API key is not configured. Please add a valid GEMINI_API_KEY to your .env file."
            )

        try:
            return genai.Client(api_key=api_key)
        except Exception as e:
            raise AIServiceError(f"Failed to initialize Gemini AI client: {str(e)}")

    @staticmethod
    def get_model():
        """Retrieve configured model name."""
        return (
            current_app.config.get("GEMINI_MODEL")
            or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        ).strip()

    @classmethod
    def _execute_prompt(cls, prompt: str, system_instruction: str = None, temperature: float = 0.7) -> str:
        """Call Gemini API with defensive error and rate-limit handling."""
        client = cls.get_client()
        model_name = cls.get_model()

        config_args = {
            "temperature": temperature,
            "max_output_tokens": 1500,
        }
        if system_instruction:
            config_args["system_instruction"] = system_instruction

        config = types.GenerateContentConfig(**config_args)

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            if not response or not response.text:
                raise AIServiceError("The AI model returned an empty response. Please try rephrasing your input.")
            return response.text.strip()
        except AIServiceError:
            raise
        except Exception as e:
            err_msg = str(e).lower()
            if "quota" in err_msg or "rate" in err_msg or "429" in err_msg:
                raise AIServiceError("AI rate limit reached. Please wait a moment before submitting another request.")
            elif "auth" in err_msg or "key" in err_msg or "401" in err_msg or "403" in err_msg:
                raise AIServiceError("Invalid or unauthorized Gemini API key. Please check your GEMINI_API_KEY setting.")
            elif "timeout" in err_msg or "deadline" in err_msg:
                raise AIServiceError("AI request timed out. Please check your network connection and try again.")
            else:
                raise AIServiceError("Failed to communicate with AI provider. Please try again shortly.")

    @classmethod
    def generate_professional_summary(
        cls,
        name: str,
        skills: str,
        education: str = "",
        experience: str = "",
        career_goals: str = "",
        level: str = "intermediate"
    ) -> str:
        """
        Generate role-tailored professional summary based on experience level.
        Levels: beginner, intermediate, experienced
        """
        system_instruction = (
            "You are a principal tech career strategist and executive resume writer. "
            "Your task is to write a compelling, recruiter-ready professional summary. "
            "CRITICAL RULE: Never invent employment history, credentials, degrees, or metrics that the user did not supply. "
            "Write in active voice, strictly grounded in the provided facts."
        )

        level_guidelines = {
            "beginner": "Format for a student, recent graduate, or entry-level candidate. Highlight foundational computer science concepts, academic/personal projects, curiosity, and rapid learning capacity.",
            "intermediate": "Format for a software engineer with 1-4 years experience. Emphasize full-stack/domain competence, delivered software features, clean code, and collaborative teamwork.",
            "experienced": "Format for a senior engineer or architect. Focus on architectural decision-making, system scalability, distributed systems, tech leadership, and business value delivery."
        }
        guideline = level_guidelines.get(level.lower(), level_guidelines["intermediate"])

        prompt = f"""
Candidate Name: {name}
Experience Level: {level.capitalize()} ({guideline})
Technical Skills: {skills}
Education / Academic Background: {education or 'Not provided'}
Previous Work / Experience: {experience or 'Not provided'}
Target Career Goals: {career_goals or 'Full-Stack Software Development'}

Instructions:
1. Write 2-3 polished, high-impact paragraphs suitable for a top-tier developer portfolio introduction.
2. Emphasize verified skills and career trajectory.
3. Output clean, ready-to-use prose with no markdown headers or boilerplate greetings.
"""
        return cls._execute_prompt(prompt, system_instruction=system_instruction, temperature=0.65)

    @classmethod
    def generate_about_me(
        cls,
        name: str,
        headline: str,
        background: str = "",
        interests: str = "",
        tone: str = "creative"
    ) -> str:
        """
        Generate a personalized 'About Me' portfolio section in various tones.
        Tones: formal, creative, concise
        """
        system_instruction = (
            "You are an expert personal branding consultant for technical professionals. "
            "Create an authentic, memorable 'About Me' portfolio section. "
            "Never invent hobbies or facts not mentioned. Write authentically in first-person ('I')."
        )

        tone_instructions = {
            "formal": "Professional, polished, industry-standard business tone suitable for corporate and enterprise hiring managers.",
            "creative": "Engaging, conversational, inspiring storytelling tone that highlights passion for code, design, and problem solving.",
            "concise": "Punchy, brief, 2-3 impactful sentences that convey core strengths and technical interests immediately."
        }
        tone_instruction = tone_instructions.get(tone.lower(), tone_instructions["creative"])

        prompt = f"""
Candidate Name: {name}
Professional Headline: {headline}
Background / Story: {background or 'Passionate software developer interested in modern scalable web systems.'}
Key Interests / Passions: {interests or 'Open source software, clean architecture, and continuous learning.'}
Desired Tone: {tone.capitalize()} ({tone_instruction})

Instructions:
1. Write an engaging first-person ('I') About Me section.
2. Keep the length proportional to tone: concise (1 short paragraph), formal/creative (2 concise paragraphs).
3. Output the bio directly with no conversational preamble.
"""
        return cls._execute_prompt(prompt, system_instruction=system_instruction, temperature=0.7)

    @classmethod
    def generate_project_description(
        cls,
        title: str,
        technologies: str,
        purpose: str,
        key_details: str = "",
        format_style: str = "star"
    ) -> str:
        """
        Generate professional project descriptions adhering to STAR methodology.
        Strictly prohibits hallucinating metrics, users, or unlisted technologies.
        """
        system_instruction = (
            "You are a technical project auditor and engineering resume specialist. "
            "Write high-impact project showcase descriptions for software engineering portfolios. "
            "CRITICAL: Never invent performance numbers, star counts, or tools not specified by the user. "
            "Structure using the STAR framework (Situation/Task, Action, Result) or structured bullet points."
        )

        prompt = f"""
Project Title: {title}
Technology Stack: {technologies}
Project Purpose / Problem Solved: {purpose}
User-Provided Facts / Architecture Details: {key_details or 'Core functionality built and tested end-to-end.'}

Instructions:
1. Provide an executive summary of the project (2 sentences).
2. Detail the architecture and engineering implementation steps based strictly on the provided technologies.
3. Provide 3 impactful bullet points highlighting the technical challenges solved and engineering outcome.
4. Clearly state the tech stack tags at the end.
5. Do NOT invent fake performance benchmarks (e.g. do not say 'improved speed by 85%' unless specified in facts).
"""
        return cls._execute_prompt(prompt, system_instruction=system_instruction, temperature=0.6)

    @classmethod
    def analyze_skills(cls, current_skills: str, target_role: str, career_goal: str = "") -> str:
        """
        Analyze current skills against a target role.
        Generates objective gap analysis and prioritized learning recommendations.
        """
        system_instruction = (
            "You are an AI technical recruiter and career roadmap advisor. "
            "Analyze candidate technical skills against industry benchmarks for a target role. "
            "Clearly distinguish between verified existing competencies and AI-suggested learning recommendations. "
            "Provide realistic, structured advice."
        )

        prompt = f"""
Candidate's Current Skills: {current_skills}
Target Role: {target_role}
Career Goal / Context: {career_goal or 'Advancement to target role within 6 months'}

Instructions:
Please provide a structured analysis with the following 4 sections:
1. Competency Match Assessment: An estimated objective compatibility rating (e.g. 75%) and explanation of strong foundational alignments.
2. Core Strengths: Current skills that directly match the target role.
3. High-Priority Skill Gaps (Recommendations): 3-5 specific technical competencies, tools, or frameworks to learn next, prioritized by industry demand.
4. Suggested Portfolio Project Idea: One practical end-to-end project the user can build to demonstrate these missing skills.

NOTE: Include an explicit disclaimer that recommendations are advisory guidance, not verified academic certifications.
"""
        return cls._execute_prompt(prompt, system_instruction=system_instruction, temperature=0.6)

    @classmethod
    def recommend_careers(cls, background: str, skills: str, interests: str = "") -> str:
        """
        Recommend suitable entry-level or transition roles based on user background and skills.
        """
        system_instruction = (
            "You are a technology career guidance counselor. "
            "Recommend realistic, in-demand software and IT roles suitable for the candidate's verified profile. "
            "Explain the reasoning and practical next steps."
        )

        prompt = f"""
Candidate Background / Education: {background}
Technical Skills: {skills}
Personal / Industry Interests: {interests or 'Software engineering and product development'}

Instructions:
Recommend 3 distinct, realistic career roles (e.g., Full-Stack Web Developer, Cloud Support Engineer, Junior Data Analyst, etc.).
For EACH role, provide:
- Role Title & Overview: 1-2 sentence description.
- Alignment Rationale: Why candidate's existing background fits this role.
- 3 Immediate Action Steps: Concrete technologies to learn or projects to build to become highly competitive for junior/mid positions in this track.
"""
        return cls._execute_prompt(prompt, system_instruction=system_instruction, temperature=0.65)

    @classmethod
    def generate_github_repo_description(
        cls,
        repo_name: str,
        description: str = "",
        language: str = "",
        topics: list = None,
    ) -> str:
        """
        Generate a professional portfolio project description from GitHub repository metadata.
        Strictly limits inferences to verified repository facts (name, description, language, topics).
        Prohibits inventing false performance metrics, user counts, or unlisted tools.
        """
        topics_str = ", ".join(topics) if (topics and isinstance(topics, list)) else (topics or "None specified")
        system_instruction = (
            "You are a principal technical recruiter and portfolio editor. "
            "Your task is to transform raw GitHub repository metadata into a polished, professional portfolio project description. "
            "CRITICAL CONSTRAINTS: "
            "1. Only use the provided repository name, description, primary language, and topics. "
            "2. Never invent benchmarks, user statistics, downloads, or tools that are not provided. "
            "3. Clearly distinguish between verified repository metadata and inferred architectural capabilities. "
            "4. Keep the output concise, recruiter-friendly, and professional."
        )

        prompt = f"""
GitHub Repository: {repo_name}
Raw Description: {description or 'Open source software repository.'}
Primary Language: {language or 'Not specified'}
Repository Topics: {topics_str}

Instructions:
1. Executive Overview: A punchy 2-sentence summary explaining what the project is and the problem it addresses based on the repository description and name.
2. Key Architectural Highlights: 2-3 concise bullet points detailing core functionality supported by the listed language and topics.
3. Verified Technologies: List the verified language and topics.
4. Output cleanly without meta-introductions (do not say "Here is the description:").
"""
        return cls._execute_prompt(prompt, system_instruction=system_instruction, temperature=0.6)
