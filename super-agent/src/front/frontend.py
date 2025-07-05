import streamlit as st
import requests
import traceback

st.title("🧠 Super Agent - AI 어시스턴트")

user_query = st.text_area("💬 궁금한 걸 입력해 보세요!", height=150)

if st.button("🚀 실행"):
    if not user_query.strip():
        st.warning("질문을 입력해 주세요!")
    else:
        with st.spinner("슈퍼 에이전트가 작업 중입니다..."):
            try:
                response = requests.post(
                    "http://localhost:8000/api/superagent",
                    json={"query": user_query}
                )
                #st.write(f"HTTP 상태 코드: {response.status_code}")
                #st.write(f"응답 원문: {response.text}")

                try:
                    result = response.json()
                    if "answer" in result:
                        st.success("✅ 작업 완료!")
                        st.markdown(f"**🧠 응답:**\n\n{result['answer']}")
                    elif "error" in result:
                        st.error(f"❌ 오류: {result['error']}")
                    else:
                        st.error("❌ 알 수 없는 오류가 발생했습니다.")
                except Exception as json_err:
                    st.error(f"❌ JSON 파싱 실패: {json_err}")
                    st.text(traceback.format_exc())

            except requests.exceptions.RequestException as req_err:
                st.error(f"❌ 서버 요청 실패: {req_err}")
            except Exception as e:
                st.error("❌ 예외가 발생했습니다:")
                st.text(traceback.format_exc())
