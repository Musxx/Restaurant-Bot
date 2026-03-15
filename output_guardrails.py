from agents import Agent, output_guardrail,Runner, RunContextWrapper, GuardrailFunctionOutput
from models import  TechnicalOutputGuardRailOutput, UserAccountContext
import re



technical_output_guardrail_agent = Agent(
    name="Technical Support Guardrail",
    instructions="""
    Analyze the technical support response and detect whether it actually performs non-technical support tasks.
    Mere mentions for context (e.g., "login", "order screen", "reservation page", "payment error") are allowed.
    Trigger only when the response actively handles non-technical workflows.
    
    Mark contain_billing_data=true ONLY if the response processes or advises billing actions
    (refund, charge dispute, subscription changes, payment method updates, credits).

    Mark contain_account_data=true ONLY if the response performs account-management actions
    (password reset links/tokens, email/profile/security-setting changes).

    Mark contain_off_topic=true ONLY if the response is clearly outside technical troubleshooting scope
    and attempts to execute menu/order/reservation customer-service handling.
    
    Technical troubleshooting steps, diagnostics, error analysis, reproducibility questions,
    and escalation to engineering are valid and should NOT be flagged.
    """,
    output_type=TechnicalOutputGuardRailOutput,
)

@output_guardrail
async def technical_output_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent,
    output:str
):
    if isinstance(output, list):
        normalized_output = "\n".join(str(item) for item in output)
    elif isinstance(output, dict):
        normalized_output = str(output.get("text") or output.get("content") or output)
    else:
        normalized_output = str(output)

    result = await Runner.run(technical_output_guardrail_agent, normalized_output, context=wrapper.context)

    validation = result.final_output

    model_flagged = (
        validation.contain_off_topic
        or validation.contain_billing_data
        or validation.contain_account_data
    )

    # 실제 비기술 처리행위가 있을 때만 차단해 과차단을 줄인다.
    action_pattern = (
        r"refund|charge|payment method|subscription|tracking|return id|"
        r"reset token|password reset|secure link sent|order status"
    )
    has_non_technical_action = bool(re.search(action_pattern, normalized_output.lower()))
    triggered = model_flagged and has_non_technical_action

    return GuardrailFunctionOutput(
        output_info=validation.reason,
        tripwire_triggered=triggered,
    )

