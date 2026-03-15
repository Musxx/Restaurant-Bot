import asyncio
import os
import streamlit as st
from dotenv import load_dotenv
from agents import Runner, SQLiteSession, function_tool, RunContextWrapper , InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered
from openai import OpenAI
from models import UserAccountContext
from my_agents.triage_agent import triage_agent

# 프로젝트 루트의 .env 파일을 자동으로 읽어 OPENAI_API_KEY를 환경변수로 주입한다.
load_dotenv()

with st.sidebar:
    api_key = st.text_input("OpenAI API Key", type="password")

if not api_key:
    st.info("OpenAI API Key를 입력하세요.")
    st.stop()

os.environ["OPENAI_API_KEY"] = api_key


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

# 텍스트 입력 초기화는 같은 실행 사이클에서 위젯 값을 직접 바꾸지 않고,
# 다음 rerun 시작 시점에 수행한다.
if st.session_state.get("clear_typed_prompt", False):
    st.session_state["typed_prompt"] = ""
    st.session_state["clear_typed_prompt"] = False


def transcribe_audio_input(audio_file):
    """audio_input 파일을 텍스트로 전사한다."""
    client = OpenAI()
    audio_bytes = audio_file.getvalue()
    filename = getattr(audio_file, "name", None) or "voice_input.wav"
    mime_type = getattr(audio_file, "type", None) or "audio/wav"

    transcript = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=(filename, audio_bytes, mime_type),
        language="ko",
    )
    return (transcript.text or "").strip()

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
async def run_agent(message, chat_container):
    if not has_openai_api_key:
        st.error("...")
        return
    
    with chat_container:  # ← try 전체를 with 안으로
        with st.chat_message("ai"):
            text_placeholder = st.empty()
            response = ""

            try:
                stream = Runner.run_streamed(
                    st.session_state["agent"], message,
                    session=session, context=user_account_ctx
                )
                async for event in stream.stream_events():
                    if event.type == "raw_response_event":
                        if event.data.type == "response.output_text.delta":
                            response += event.data.delta
                            text_placeholder.write(response)
                    elif event.type == "agent_update_stream_event":
                        st.session_state["agent"] = event.new_agent
                        text_placeholder = st.empty()
                        response = ""

            except InputGuardrailTripwireTriggered:
                st.write("입력 가드레일 작동")
            except OutputGuardrailTripwireTriggered:
                st.write("출력 가드레일 작동")
            except Exception as e:
                st.error(f"에이전트 실행 중 오류가 발생했습니다: {e}")


def submit_user_message(user_message: str, chat_container):
    with chat_container:
        with st.chat_message("user"):
            st.write(user_message)
    asyncio.run(run_agent(user_message, chat_container))


# 채팅 메시지는 이 컨테이너에 렌더링하여 입력 영역보다 위에 고정한다.
chat_container = st.container()
with chat_container:
    asyncio.run(paint_history())


#하는역할 : 텍스트와 오디오를 한 줄 입력 영역에서 받는다.
input_col, audio_col, send_col = st.columns([6, 3, 2])

typed_prompt = input_col.text_input(
    "Type your message here...",
    key="typed_prompt",
    label_visibility="collapsed",
    placeholder="Type your message here...",
    disabled=not has_openai_api_key,
)

audio_prompt = audio_col.audio_input(
    "Record",
    label_visibility="collapsed",
    disabled=not has_openai_api_key,
)

send_clicked = send_col.button("Send", disabled=not has_openai_api_key)

if not has_openai_api_key:
    st.info("OPENAI_API_KEY를 설정하면 채팅 입력이 활성화됩니다.")

#하는역할 : 전송 버튼을 누르면 텍스트 또는 음성을 메시지로 변환해 실행한다.
if send_clicked:
    final_message = (typed_prompt or "").strip()

    if not final_message and audio_prompt is not None:
        try:
            with st.spinner("음성을 텍스트로 변환 중..."):
                final_message = transcribe_audio_input(audio_prompt)
        except Exception as e:
            st.error(f"오디오 변환 중 오류가 발생했습니다: {e}")
            final_message = ""

    if not final_message:
        st.warning("텍스트를 입력하거나 음성을 녹음한 뒤 Send를 눌러주세요.")
    else:
        submit_user_message(final_message, chat_container)
        st.session_state["clear_typed_prompt"] = True

#하는역할 : 사이드바에 대화 초기화 버튼과 현재 히스토리 표시
with st.sidebar:
    reset = st.button("Reset Conversation")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))        