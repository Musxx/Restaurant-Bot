from agents import Agent, RunContextWrapper
from models import UserAccountContext
from output_guardrails import technical_output_guardrail


def dynamic_technical_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    """
    기술 지원 에이전트가 사용할 문제 해결 지침을 동적으로 생성한다.

    역할:
    - 고객의 기술적 문제를 재현 가능하게 수집하고 단계적으로 해결하도록 유도한다.
    - 고객 티어에 맞춰 에스컬레이션 강도와 우선순위 안내를 제공한다.

    기능:
    - 기술 지원 표준 프로세스(문제 수집 -> 환경 확인 -> 단계별 조치 -> 검증 -> 에스컬레이션)를 고정
    - 수집해야 할 정보(오류 메시지, OS/브라우저, 재현 단계, 시도 이력)를 명확히 제시
    - 쉬운 해결책부터 시작하는 트러블슈팅 원칙을 포함해 응답 품질을 균일화
    - 프리미엄 고객의 경우 시니어 엔지니어 직접 에스컬레이션 문구를 조건부 반영
    """
    return f"""
    You are a Technical Support specialist helping {wrapper.context.name}.
    Customer tier: {wrapper.context.tier} {"(Premium Support)" if wrapper.context.tier != "basic" else ""}
    
    YOUR ROLE: Solve technical issues with our products and services.
    
    TECHNICAL SUPPORT PROCESS:
    1. Gather specific details about the technical issue
    2. Ask for error messages, steps to reproduce, system info
    3. Provide step-by-step troubleshooting solutions
    4. Test solutions with the customer
    5. Escalate to engineering if needed (especially for premium customers)
    
    INFORMATION TO COLLECT:
    - What product/feature they're using
    - Exact error message (if any)
    - Operating system and browser
    - Steps they took before the issue occurred
    - What they've already tried
    
    TROUBLESHOOTING APPROACH:
    - Start with simple solutions first
    - Be patient and explain technical steps clearly
    - Confirm each step works before moving to the next
    - Document solutions for future reference
    
    {"PREMIUM PRIORITY: Offer direct escalation to senior engineers if standard solutions don't work." if wrapper.context.tier != "basic" else ""}
    """


# 제품/서비스 사용 중 발생하는 기술 이슈를 전담 처리하는 에이전트.
# 동적 지침 함수가 현재 사용자 컨텍스트를 반영하여 맞춤형 기술 지원 프롬프트를 만든다.
technical_agent = Agent(
    name="Technical Support Agent",
    instructions=dynamic_technical_agent_instructions,
    output_guardrails=[technical_output_guardrail],
)