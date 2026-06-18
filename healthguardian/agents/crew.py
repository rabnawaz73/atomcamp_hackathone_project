import json
import logging
from typing import Any, Callable

from healthguardian.services.llm import get_crewai_llm, get_openai_client
from healthguardian.tools.weather import build_city_report
from healthguardian.config import get_settings

logger = logging.getLogger(__name__)

MEDICAL_DISCLAIMER = (
    "⚠️ Medical Disclaimer: I am an AI assistant, not a licensed medical professional. "
    "This information is for educational purposes only. For serious symptoms or emergencies, "
    "consult a qualified healthcare provider immediately."
)


def _generate_plan_with_llm(user_profile: dict, city_report: dict) -> dict[str, Any]:
    """Use OpenRouter/DeepSeek to generate a structured daily plan."""
    client = get_openai_client()
    settings = get_settings()

    outdoor = city_report.get("outdoor_exercise_recommended", True)
    weather = city_report.get("weather", {})
    location = city_report.get("location", {})
    city = location.get("city", "your city")
    region = location.get("region", "")
    country = location.get("country", "")
    full_location = f"{city}, {region}, {country}".strip(", ")

    prompt = f"""You are a wellness architect. Create a personalised daily health plan as JSON.

User Profile:
- Name: {user_profile.get('full_name')}
- Age: {user_profile.get('age')}
- Height: {user_profile.get('height_cm')} cm
- Weight: {user_profile.get('weight_kg')} kg
- Allergies: {user_profile.get('allergies') or 'None'}
- Chronic Conditions: {user_profile.get('chronic_conditions') or 'None'}
- Medications: {user_profile.get('medications') or 'None'}

City Environment ({full_location}):
- Weather: {weather.get('temperature_c')}°C, {weather.get('description')}
- Humidity: {weather.get('humidity')}%
- Air Quality: {city_report.get('air_quality', {}).get('category', 'Unknown')} (AQI {city_report.get('air_quality', {}).get('aqi', 'N/A')})
- Outdoor exercise recommended: {outdoor}

Local Culinary & Lifestyle Context:
Tailor all meal, snack, drink, and exercise recommendations to the traditional, popular, and accessible names of the user's detected location: {full_location}.
- Avoid generic European or Western food names (e.g. Greek yogurt, quinoa salad, avocados, berries, salmon) unless they are natively traditional and common in that region.
- Suggest local recipes, local breads/staples, local tea/drinks, and local fresh produce. For example, if the location is in Pakistan, suggest dishes like Rosh, Sajji, Kabuli Pulao, Paratha, Chanay, whole-wheat Roti, and Kahwah green tea. If in Japan, suggest Miso soup, grilled fish, rice, green tea. If in Italy, suggest regional dishes, etc. Make the culinary suggestions highly authentic and relevant to the detected local culture and lifestyle.
- Suggest local locations or environmental details for activities (like walking in local mountain parks or around local lakes/valley trails).

Return ONLY valid JSON with this structure:
{{
  "wake_up": {{"time": "6:30 AM", "notes": "..."}},
  "exercise": {{"time": "7:00 AM", "activity": "...", "duration_minutes": 30, "indoor": false}},
  "breakfast": {{"time": "8:00 AM", "meal": "...", "calories_approx": 400}},
  "lunch": {{"time": "12:30 PM", "meal": "..."}},
  "dinner": {{"time": "7:00 PM", "meal": "..."}},
  "snacks": {{"time": "3:30 PM", "meal": "..."}},
  "hydration": {{"target_litres": 2.5, "reminders": ["10:00 AM", "2:00 PM", "5:00 PM"]}},
  "relaxation": {{"time": "9:00 PM", "activity": "..."}},
  "sleep": {{"time": "10:30 PM", "target_hours": 8}},
  "health_tip": "One personalised tip for today"
}}

Adapt exercise for weather (indoor stretching/yoga if rainy/poor AQI). Respect allergies in meals."""

    if client is None:
        raise ValueError("LLM client could not be initialized. Check your API keys.")

    try:
        model_name = settings.openrouter_model
        if model_name.startswith("openrouter/"):
            model_name = model_name.replace("openrouter/", "", 1)

        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
        )
        content = response.choices[0].message.content or ""
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        raise ValueError("LLM did not return valid JSON.")
    except Exception as exc:
        logger.error("LLM plan generation failed: %s", exc)
        raise RuntimeError(f"Plan generation failed: {exc}")





def run_location_agent(city_override: str | None = None) -> dict[str, Any]:
    """City Scout: fetch location and environment data."""
    return build_city_report(city_override)


def run_planner_agent(user_profile: dict, city_report: dict) -> dict[str, Any]:
    """Wellness Architect: generate daily plan from profile and city report."""
    llm = get_crewai_llm()

    if llm is not None:
        try:
            from crewai import Agent, Crew, Process, Task
        except ImportError:
            return _generate_plan_with_llm(user_profile, city_report)

        try:
            location_summary = json.dumps(city_report, indent=2)
            profile_summary = json.dumps(user_profile, indent=2)

            scout = Agent(
                role="City Scout",
                goal="Summarise environmental conditions for health planning",
                backstory="Expert in urban environmental health factors.",
                llm=llm,
                verbose=False,
            )
            architect = Agent(
                role="Wellness Architect",
                goal="Design personalised daily wellness routines",
                backstory="Certified wellness coach specialising in adaptive health plans.",
                llm=llm,
                verbose=False,
            )

            location_data = city_report.get("location", {})
            city = location_data.get("city", "Unknown")
            region = location_data.get("region", "")
            country = location_data.get("country", "")
            full_loc = f"{city}, {region}, {country}".strip(", ")

            env_task = Task(
                description=f"Summarise this city report for wellness planning:\n{location_summary}",
                expected_output="A concise environmental summary with exercise and meal implications.",
                agent=scout,
            )
            plan_task = Task(
                description=(
                    f"Using the environmental summary and user profile:\n{profile_summary}\n\n"
                    "Create a detailed daily wellness plan as JSON with keys: wake_up, exercise, "
                    "breakfast, lunch, dinner, snacks, hydration, relaxation, sleep, health_tip. "
                    "Each meal/exercise entry should have time and details. Adapt for weather and allergies.\n\n"
                    f"IMPORTANT: The user's location is '{full_loc}'. Adapt all meal names, ingredients, "
                    "beverages, snacks, and exercises to the traditional, popular, and accessible cultural context "
                    "of this location. Avoid generic European/Western ones (e.g. quinoa, Greek yogurt, salmon, avocados, berries) "
                    "unless natively common there. Suggest authentic regional alternatives (e.g. if in Pakistan, suggest Rosh, Sajji, "
                    "Kabuli Pulao, Chanay, Paratha, whole-wheat Roti, Kahwah tea; if in Japan, suggest Miso soup, grilled fish, rice; etc.)."
                ),
                expected_output="Valid JSON daily wellness plan.",
                agent=architect,
                context=[env_task],
            )

            crew = Crew(agents=[scout, architect], tasks=[env_task, plan_task], process=Process.sequential, verbose=False)
            result = crew.kickoff()

            content = str(result)
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
            raise ValueError("CrewAI did not return valid JSON.")
        except Exception as exc:
            logger.error("CrewAI planner failed, using direct LLM fallback: %s", exc)
            return _generate_plan_with_llm(user_profile, city_report)

    return _generate_plan_with_llm(user_profile, city_report)


def run_medical_consultation(
    user_profile: dict,
    question: str,
    chat_history: list[dict] | None = None,
) -> str:
    """Health Advisor: answer medical questions with RAG context."""
    from healthguardian.services.rag import get_rag_context

    rag_context = get_rag_context(question)
    settings = get_settings()
    client = get_openai_client()

    system_prompt = f"""You are HealthGuardian's Medical Consultant AI — a helpful, empathetic health advisor.

User: {user_profile.get('full_name')}, Age {user_profile.get('age')}
Conditions: {user_profile.get('chronic_conditions') or 'None'}
Allergies: {user_profile.get('allergies') or 'None'}
Medications: {user_profile.get('medications') or 'None'}

Relevant medical knowledge:
{rag_context}

Guidelines:
- Provide clear, actionable health information
- Always include the medical disclaimer at the end
- For severe symptoms (chest pain, difficulty breathing, etc.), urge immediate emergency care
- Be warm and supportive
- Keep responses concise (2-4 paragraphs max)

Disclaimer to append: {MEDICAL_DISCLAIMER}"""

    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        messages.extend(chat_history[-10:])
    messages.append({"role": "user", "content": question})

    if client is None:
        raise ValueError("LLM client could not be initialized. Cannot run medical consultation.")

    try:
        model_name = settings.openrouter_model
        if model_name.startswith("openrouter/"):
            model_name = model_name.replace("openrouter/", "", 1)

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.5,
            max_tokens=2048,
        )
        answer = response.choices[0].message.content or ""
        if MEDICAL_DISCLAIMER not in answer:
            answer += f"\n\n{MEDICAL_DISCLAIMER}"
        return answer
    except Exception as exc:
        logger.error("Medical consultation failed: %s", exc)
        raise RuntimeError(f"Medical consultation failed: {exc}")


def run_plan_generation_workflow(
    user_profile: dict,
    city_override: str | None = None,
    status_callback: Callable[[str, float], None] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Sequential workflow: Location → Planner.
    Optional status_callback(message, progress_0_to_1) for UI updates.
    """
    if status_callback:
        status_callback("🔍 Scout is analysing your city...", 0.15)

    city_report = run_location_agent(city_override or user_profile.get("city_override"))

    if status_callback:
        status_callback("🧠 Planner is designing your custom routine...", 0.55)

    daily_plan = run_planner_agent(user_profile, city_report)

    if status_callback:
        status_callback("✅ Your wellness plan is ready!", 1.0)

    return daily_plan, city_report
