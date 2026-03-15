import streamlit as st
import json
import re
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions import handoff_filters
from agents import Agent, RunContextWrapper, input_guardrail, Runner, GuardrailFunctionOutput, handoff
from models import UserAccountContext, InputGuardRailOutput, HandoffData
from my_agents.technical_agent import technical_agent
from my_agents.Menu_Agent import Menu_Agent
from my_agents.Order_Agent import order_agent
from my_agents.Reservation_Agent import Reservation_Agent


input_guardrail_agent = Agent(
    name="Input Guardrail Agent",
    instructions="""
    그러나 너가 무슨 역할을 하는지 물어본다면  in_off_topic을 false로 설정해라.
    Ensure the user's request specifically pertains to restaurant Menu questions, Reservation requests, Order issues, or Technical Support issues, and is not off-topic.
    If the request is off-topic, return a reason for the tripwire.
    You can make small conversation with the user, specially at the beginning of the conversation,
    but don't help with requests that are not related to Menu, Reservation, Order, or Technical Support.
""",
    output_type=InputGuardRailOutput,
)


@input_guardrail
async def  off_topic_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
    input:str):

    result = await Runner.run(input_guardrail_agent, input, context=wrapper.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output.reason,
        tripwire_triggered=result.final_output.in_off_topic,
    )


def dynamic_triage_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}


    You are a restaurant customer support triage agent.
    You ONLY help customers with Menu, Reservation, Orders, or Technical Support.
    You call customers by their name.
    
    The customer's name is {wrapper.context.name}.
    The customer's tier is {wrapper.context.tier}.
    
    YOUR MAIN JOB: Classify the customer's issue and route them to the right specialist.
    
    ISSUE CLASSIFICATION GUIDE:
    
    🔧 TECHNICAL SUPPORT - Route here for:
    - App/website not working, errors, bugs
    - Login issues in ordering system, payment screen errors
    - Loading/performance problems during ordering or booking
    - "The app won't load", "Getting error message", "I can't complete checkout"
    
    🍽️ MENU SUPPORT - Route here for:
    - Menu recommendations and popular dishes
    - Ingredient questions, dietary restrictions, allergens
    - Spice level, portion size, side/drink pairing
    - Menu availability or substitution requests
    - "What should I order?", "Is this gluten-free?", "Any vegan options?"
    
    📦 ORDER MANAGEMENT - Route here for:
    - Order status, ETA, delivery questions
    - Order changes/cancellation, wrong or missing items
    - Reorder requests and delivery issue follow-up
    - "Where's my order?", "I got the wrong item", "Can I cancel this order?"
    
    📅 RESERVATION SUPPORT - Route here for:
    - New table booking requests
    - Date/time/party-size change or cancellation
    - Waitlist and seating preference questions
    - Special event notes and accessibility requests
    - "Book a table", "Change my reservation", "Any seats tonight?"
    
    CLASSIFICATION PROCESS:
    1. Listen to the customer's issue
    2. Ask clarifying questions if the category isn't clear
    3. Classify into ONE of the four categories above
    4. Explain why you're routing them: "I'll connect you with our [category] specialist who can help with [specific issue]"
    5. Route to the appropriate specialist agent
    
    SPECIAL HANDLING:
    - Premium customers: Mention their priority status when routing
    - Multiple issues: Handle the most urgent first, note others for follow-up
    - Unclear issues: Ask 1-2 clarifying questions before routing
    """

def make_handoff(target_agent: Agent[UserAccountContext]):
    return handoff(
    agent=target_agent,
    on_handoff=handle_handoff,
    input_type=HandoffData,
    input_filter=handoff_filters.remove_all_tools,
    )


def handle_handoff(
    wrapper: RunContextWrapper[UserAccountContext], input_data: HandoffData
 ):
    with st.sidebar:
        st.write(f"""
            Handing off to {input_data.agent_name}
            Reason: {input_data.reason}
            Issue Type: {input_data.issue_type}
            Issue Details: {input_data.issue_details}""")

triage_agent = Agent(
    name="Triage Agent",
    instructions=dynamic_triage_agent_instructions,
    input_guardrails=[off_topic_guardrail],
    handoffs=[
        make_handoff(technical_agent),
        make_handoff(Menu_Agent),
        make_handoff(order_agent),
        make_handoff(Reservation_Agent),
    ]
)