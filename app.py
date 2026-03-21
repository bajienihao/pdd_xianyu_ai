import streamlit as st
import dashscope
import pandas as pd
from datetime import datetime
import json
import re
import base64
import imagehash
from io import BytesIO
from PIL import Image

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="闲鱼上货助手",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)
st.title("🚀 闲鱼上货助手")

# ==================== 不过滤词汇 ====================
def filter_banned(text):
    return text

# ==================== 一键复制 ====================
def copy_btn(text, label="📋 复制"):
    b64 = base64.b64encode(text.encode()).decode()
    js = f"""
    <button onclick="navigator.clipboard.writeText(decodeURIComponent(escape(window.atob('{b64}'))));">{label}</button>
    """
    st.markdown(js, unsafe_allow_html=True)

# ==================== AI文案生成 ====================
def generate_xianyu_content(title, price, style):
    prompt = f"""
你是闲鱼卖家，用【{style}】风格写文案。
商品标题：{title}
成本价：{price}

只返回干净JSON，不要多余内容：
{{
    "xianyu_title": "标题",
    "description": "描述",
    "tags": ["标签1","标签2","标签3"],
    "category": "类目",
    "prices": {{
        "conservative": {round(price*1.3)},
        "recommended": {round(price*1.5)},
        "aggressive": {round(price*1.1)}
    }}
}}
"""
    try:
        resp = dashscope.Generation.call(
            model='qwen-turbo',
            messages=[{"role": "user", "content": prompt}],
            result_format='message'
        )
        data = json.loads(resp.output.choices[0].message.content.strip())
        data['xianyu_title'] = filter_banned(data.get('xianyu_title', title))
        data['description'] = filter_banned(data.get('description', ''))
        return data
    except:
        return None

# ==================== 会话 ====================
if 'gen_count' not in st.session_state:
    st.session_state.gen_count = 0
if 'history' not in st.session_state:
    st.session_state.history = []
if 'batch_data' not in st.session_state:
    st.session_state.batch_data = pd.DataFrame(columns=["原标题", "成本价", "风格"])

styles = ["默认闲置风", "情感故事风", "性价比爆款风", "限时秒杀风"]

# ==================== 标签 ====================
tab1, tab2, tab3, tab4 = st.tabs([
    "单条生成", "批量上货", "图片去重", "历史记录"
])

# ==================== 单条生成 ====================
with tab1:
    st.subheader("📝 商品信息")
    title = st.text_input("商品标题")
    price = st.number_input("成本价", value=10.0)
    style = st.selectbox("风格", styles)

    if st.button("✨ 生成闲鱼文案", type="primary"):
        if not title:
            st.error("请输入标题")
        else:
            data = generate_xianyu_content(title, price, style)
            if data:
                st.session_state.history.append({
                    "时间": datetime.now().strftime("%m-%d %H:%M"),
                    "原标题": title,
                    "闲鱼标题": data['xianyu_title'],
                    "推荐价": data['prices']['recommended']
                })
                st.code(data['xianyu_title'])
                copy_btn(data['xianyu_title'])
                st.text_area("描述", data['description'], height=200)
                copy_btn(data['description'], "复制描述")
                st.write("标签：", ", ".join(data['tags']))

# ==================== 批量上货 ====================
with tab2:
    st.subheader("📦 批量生成")
    c1, c2, c3 = st.columns(3)
    new_title = c1.text_input("标题")
    new_price = c2.number_input("价格", value=10.0)
    new_style = c3.selectbox("风格", styles)

    if st.button("➕ 添加到列表"):
        if new_title:
            new_row = pd.DataFrame([{"原标题": new_title, "成本价": new_price, "风格": new_style}])
            st.session_state.batch_data = pd.concat([st.session_state.batch_data, new_row], ignore_index=True)
            st.success("已添加")
        else:
            st.error("请输入标题")

    if not st.session_state.batch_data.empty:
        st.dataframe(st.session_state.batch_data)
        if st.button("✨ 批量生成"):
            res = []
            for _, row in st.session_state.batch_data.iterrows():
                d = generate_xianyu_content(row["原标题"], row["成本价"], row["风格"])
                if d:
                    res.append({
                        "标题": d["xianyu_title"],
                        "描述": d["description"],
                        "标签": ",".join(d["tags"])
                    })
            if res:
                st.dataframe(pd.DataFrame(res))

# ==================== 图片去重（手机相册直选 + 多选）====================
with tab3:
    st.subheader("🖼️ 图片去重（手机相册多选）")

    # 关键：capture 支持相机 & 相册，multiple 多选
    uploaded_files = st.file_uploader(
        "点此处打开相册（可多选）",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="mobile_gallery",
        help="在手机上会直接打开相册，和微信发图一样"
    )

    if uploaded_files:
        st.success(f"✅ 已选择 {len(uploaded_files)} 张图片")

        imgs = []
        for f in uploaded_files:
            try:
                img = Image.open(BytesIO(f.read())).convert("RGB")
                imgs.append(img)
            except:
                continue

        st.subheader("已上传")
        cols = st.columns(4)
        for i, img in enumerate(imgs):
            with cols[i % 4]:
                st.image(img, use_column_width=True)

        if st.button("🔍 开始去重", type="primary"):
            with st.spinner("去重中..."):
                hash_list = []
                unique = []
                for img in imgs:
                    h = imagehash.average_hash(img)
                    if h not in hash_list:
                        hash_list.append(h)
                        unique.append(img)

            st.success(f"去重完成：保留 {len(unique)} 张")
            st.subheader("去重结果")

            cols_out = st.columns(4)
            for i, img in enumerate(unique):
                with cols_out[i % 4]:
                    st.image(img, use_column_width=True)
                    buf = BytesIO()
                    img.save(buf, format="JPEG")
                    st.download_button(f"下载{i+1}", buf, f"pic_{i+1}.jpg")

# ==================== 历史 ====================
with tab4:
    st.subheader("📜 历史记录")
    if st.session_state.history:
        st.dataframe(pd.DataFrame(st.session_state))
    else:
        st.info("暂无记录")

st.divider()
st.caption("闲鱼上货助手 · 手机优化版")
