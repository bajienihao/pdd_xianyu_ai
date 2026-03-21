import streamlit as st
import dashscope
from http import HTTPStatus

st.title("🔧 API Key 测试工具（只测Key是否有效）")

st.sidebar.header("当前状态")
try:
    dashscope.api_key = st.secrets["DASHSCOPE_API_KEY"]
    st.sidebar.success("✅ Secrets 已读取 Key")
    st.sidebar.caption(f"Key 前8位: {dashscope.api_key[:8]}...")
except Exception as e:
    st.sidebar.error(f"Secrets读取失败: {e}")

if st.button("🚀 测试调用 qwen3.5-flash", type="primary"):
    with st.spinner("正在调用阿里云..."):
        try:
            response = dashscope.Generation.call(
                model='qwen3.5-flash',
                messages=[{"role": "user", "content": "你好，请回复'测试成功'"}],
                result_format='message'
            )
            if response.status_code == HTTPStatus.OK:
                result = response.output.choices[0].message.content
                st.balloons()
                st.success(f"✅ 测试成功！\n阿里云回复：{result}")
            else:
                st.error(f"❌ 错误: {getattr(response, 'message', str(response))}\n状态码: {response.status_code}")
        except Exception as e:
            st.error(f"❌ 调用异常: {str(e)}")

st.caption("如果这里显示'测试成功'，说明Key有效！然后我们再换回完整工具")