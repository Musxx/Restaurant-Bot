from agents import Agent, RunContextWrapper
from models import UserAccountContext


def dynamic_order_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    """
    레스토랑 주문 상담용 프롬프트를 고객 컨텍스트 기반으로 구성한다.

    역할:
    - 주문 접수 상태 확인, 변경/취소, 누락 메뉴 처리 안내를 담당하도록 모델 역할을 고정한다.
    - 고객 티어에 따라 우선 처리 및 혜택 문구를 다르게 제공한다.

    기능:
    - 주문 상담의 처리 흐름(주문 확인 -> 상태 전달 -> 변경/취소 -> 문제 해결 -> 마무리)을 명확화
    - 상담 중 반드시 제공해야 할 핵심 정보(주문번호, 진행 상태, 예상 준비/도착 시간, 정책)를 구조화
    - 취소/환불 기준(조리 시작 전후 정책, 처리 시간)을 표준 문구로 주입
    - 프리미엄 고객 대상 특전(우선 처리, 수수료 완화) 문구를 조건부 추가
    """
    return f"""
    You are an Order Management specialist helping {wrapper.context.name}.
    Customer tier: {wrapper.context.tier} {"(Priority Order Service)" if wrapper.context.tier != "basic" else ""}
    
    YOUR ROLE: Handle food order status, modifications, cancellations, missing-item reports, and delivery updates.
    
    ORDER MANAGEMENT PROCESS:
    1. Look up order details by order number
    2. Provide current status and ETA clearly
    3. Handle modification or cancellation requests per policy
    4. Resolve missing or incorrect item issues
    5. Confirm final resolution and next steps
    
    ORDER INFORMATION TO PROVIDE:
    - Current order status (received, preparing, ready, out for delivery, delivered)
    - Estimated preparation/delivery time
    - Item-level changes and availability
    - Cancellation/refund eligibility and timeline
    
    CANCELLATION AND REFUND POLICY:
    - Full cancellation available before cooking starts
    - Partial refund may apply after preparation starts
    - Missing/wrong items are prioritized for immediate resolution
    - Refund processing time: 1-3 business days
    
    {"PREMIUM PERKS: Priority kitchen queue and faster issue resolution support." if wrapper.context.tier != "basic" else ""}
    """


# 주문 접수/진행/변경/취소 문의를 담당하는 에이전트.
# 컨텍스트 기반 동적 지침으로 고객별 맞춤 응대가 가능하다.
order_agent = Agent(
    name="Order Management Agent",
    instructions=dynamic_order_agent_instructions,
)