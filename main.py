import asyncio
import os
import streamlit as st
from dotenv import load_dotenv
from agents import Runner, SQLiteSession, function_tool, RunContextWrapper , InputGuardrailTripwireTriggered
from models import UserAccountContext
from my_agents.triage_agent import triage_agent

# 프로젝트 루트의 .env 파일을 자동으로 읽어 OPENAI_API_KEY를 환경변수로 주입한다.
load_dotenv()

# 앱 실행 전 API 키 존재 여부를 확인해 런타임 크래시를 방지한다.
has_openai_api_key = bool(os.getenv("OPENAI_API_KEY", "").strip())

user_account_ctx = UserAccountContext(customer_id=1, name="me", tier="basic")

#하는역할 : 세션 상태에 에이전트가 없으면 최초 1회 생성
if "agent" not in st.session_state:
    st.session_state["agent"] = triage_agent

#하는역할 : 대화 기록 저장용 SQLite 세션이 없으면 최초 1회 생성
if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession("chat-history","chat-gpt-clone-memory.db")
#하는역할 : 세션 상태에서 대화 기록 세션 객체를 가져와 재사용
session = st.session_state["session"]

#하는역할 : 저장된 대화 히스토리를 UI에 채팅 형태로 출력
async def paint_history():
    history = await session.get_items()
    for item in history:
        with st.chat_message(item["role"]):
            if item["role"] == "user":
                st.write(item["content"])
            else:
                if item["type"]== "message":
                    st.write(item["content"][0]["text"] )



#하는역할 : 사용자 메시지를 에이전트에 전달하고 스트리밍 응답을 화면에 출력
async def run_agent(message):
    if not has_openai_api_key:
        st.error("OPENAI_API_KEY가 설정되지 않았습니다. .env 또는 환경변수에 키를 설정해주세요.")
        return
    with st.chat_message("ai"):
        text_placeholder = st.empty()
        response = ""
        st.session_state["text_placeholder"] = text_placeholder

        try: 
            stream = Runner.run_streamed(st.session_state["agent"],message,session=session, context=user_account_ctx)

            async for event in stream.stream_events():
                if event.type == "raw_response_event":
                    if event.data.type == "response.output_text.delta":
                        response += event.data.delta
                        text_placeholder.write(response)
                elif event.type == "agent_update_stream_event":
                    st.session_state["agent"] = event.new_agent
                    text_placeholder = st.empty()
                    response = ""

        except InputGuardrailTripwireTriggered as e:
            st.write("실행할 수 없습니다.")
        except Exception as e:
            # API 키 누락/모델 호출 실패 등 외부 호출 예외를 사용자에게 안내한다.
            st.error(f"에이전트 실행 중 오류가 발생했습니다: {e}")

#하는역할 : 사용자의 채팅 입력을 받는 입력창
prompt = st.chat_input("Type your message here...", disabled=not has_openai_api_key)

if not has_openai_api_key:
    st.info("OPENAI_API_KEY를 설정하면 채팅 입력이 활성화됩니다.")

#하는역할 : 입력이 들어오면 사용자 메시지를 출력하고 에이전트 실행
if prompt:
    with st.chat_message("user"):
        st.write(prompt)
        asyncio.run(run_agent(prompt))

#하는역할 : 사이드바에 대화 초기화 버튼과 현재 히스토리 표시
with st.sidebar:
    reset = st.button("Reset Conversation")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))        