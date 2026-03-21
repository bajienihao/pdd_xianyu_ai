import streamlit as st
import dashscope
from http import HTTPStatus
import pandas as pd
from datetime import datetime
import json
import re
import base64
import imagehash
from io import BytesIO
from PIL import Image
from collections import defaultdict

# ==================== 页面配置 ====================
st.set_page_config(page_title="闲鱼上货助手 Pro", page_icon="🚀", layout="wide")
st.title("🚀 闲鱼上货助手 Pro 2026稳定版")

# ==================== 不过滤任何词汇 ====================
def filter_banned(text):
    return text

# ==================== 一键复制 ====================
def copy_btn(text, label="📋 复制"):
    b64 = base64.b64encode(text.encode()).decode()
    js = f"""
    <button onclick="navigator.clipboard.writeText(decodeURIComponent(escape(window.atob('{b64}'))));">{label}</button>
    """
    st.markdown(js, unsafe_allow_html=True)

# ==================== AI 文案生成 ====================
def generate_xianyu_content(title, price, style):
    prompt = f"""
你是闲鱼资深卖家，使用【{style}】风格撰写文案。
商品标题：{title}
成本价：{price}元

只返回标准JSON，不要多余内容、不要解释、不要包裹：
{{
    "xianyu_title": "30字内标题",
    "description": "200-300字描述",
    "tags": ["标签1","标签2","标签3","标签4","标签5"],
    "category": "推荐类目",
    "prices": {{
        "conservative": {round(price*1.3)},
        "recommended": {round(price*1.5)},
        "aggressive": {round(price*1.1)}
    }},
    "tips": "上架小技巧"
}}
"""
    try:
        resp = dashscope.Generation.call(
            model='qwen-turbo',
            messages=[{"role": "user", "content": prompt}],
            result_format='message',
            temperature=0.7,
            timeout=30
        )
        if resp.status_code == HTTPStatus.OK:
            raw = resp.output.choices[0].message.content.strip()
            raw = re.sub(r'^```json|```$', '', raw).strip()
            raw = re.sub(r'^```|```$', '', raw).strip()
            data = json.loads(raw)

            if "prices" not in data or not isinstance(data["prices"], dict):
                data["prices"] = {
                    "conservative": round(price*1.3),
                    "recommended": round(price*1.5),
                    "aggressive": round(price*1.1)
                }
            data['xianyu_title'] = filter_banned(data.get('xianyu_title', title))
            data['description'] = filter_banned(data.get('description', '个人闲置，成色如图，功能正常，拍下尽快发货~'))
            data['tags'] = data.get('tags', ["闲置", "二手", "好物分享"])
            data['category'] = data.get('category', '闲置物品')
            data['tips'] = data.get('tips', '实拍图清晰，实物拍摄')
            return data
        else:
            st.error(f"API调用失败：{resp.message if hasattr(resp, 'message') else '未知错误'}")
            return None
    except Exception as e:
        st.error(f"生成失败：{str(e)}")
        return None

# ==================== 图片去重（感知哈希）====================
def find_duplicates(images, hash_size=8, threshold=5):
    hashes = []
    for idx, img in enumerate(images):
        try:
            h = imagehash.average_hash(img, hash_size=hash_size)
            hashes.append((idx, h))
        except:
            continue

    duplicate_pairs = defaultdict(list)
    for i, (idx1, h1) in enumerate(hashes):
        for idx2, h2 in hashes[i+1:]:
            if abs(h1 - h2) <= threshold:
                duplicate_pairs[idx1].append(idx2)

    dup_indices = set()
    for k in duplicate_pairs:
        dup_indices.update(duplicate_pairs[k])

    unique_images = []
    for idx, img in enumerate(images):
        if idx not in dup_indices:
            unique_images.append(img)

    return unique_images, len(images), len(unique_images)

# ==================== 会话状态 ====================
st.sidebar.header("⚙️ 配置")
try:
    dashscope.api_key = st.secrets["DASHSCOPE_API_KEY"]
    st.sidebar.success("✅ API密钥已加载")
except:
    st.sidebar.error("❌ Secrets未配置")

if 'gen_count' not in st.session_state:
    st.session_state.gen_count = 0
if 'history' not in st.session_state:
    st.session_state.history = []
if 'batch_data' not in st.session_state:
    st.session_state.batch_data = pd.DataFrame(columns=["原标题", "成本价", "风格"])

free_limit = 5
st.sidebar.metric("今日免费次数", f"{free_limit - st.session_state.gen_count}/{free_limit}")

styles = ["默认闲置风","情感故事风","性价比爆款风","限时秒杀风"]

# ==================== 标签页 ====================
tab1, tab2, tab3, tab4 = st.tabs([
    "🔥 单条生成",
    "📦 批量上货",
    "🖼️ 图片去重",
    "📜 历史记录"
])

# ==================== 单条生成 ====================
with tab1:
    st.subheader("📝 商品信息")
    title = st.text_input("商品标题", key="single_title")
    price = st.number_input("成本价", value=10.0, step=1.0, key="single_price")
    style = st.selectbox("风格", styles, key="single_style")

    col1, col2 = st.columns(2)
    with col1:
        run = st.button("✨ 生成闲鱼文案", type="primary",
                        disabled=(st.session_state.gen_count >= free_limit), key="gen_single")
    with col2:
        is_pro = st.checkbox("专业版（无限次）", value=False, key="pro_single")

    if run:
        if not title.strip():
            st.error("请输入商品标题")
        else:
            with st.spinner("生成中..."):
                data = generate_xianyu_content(title, price, style)
                if data:
                    st.session_state.history.append({
                        "时间": datetime.now().strftime("%m-%d %H:%M"),
                        "原标题": title,
                        "闲鱼标题": data['xianyu_title'],
                        "推荐价": data['prices']['recommended'],
                        "风格": style
                    })
                    if not is_pro:
                        st.session_state.gen_count += 1

                    c1, c2 = st.columns([3,1])
                    with c1:
                        st.subheader("📋 标题")
                        st.code(data['xianyu_title'])
                        copy_btn(data['xianyu_title'])
                    with c2:
                        st.subheader("💰 定价")
                        st.success(f"保守 {data['prices']['conservative']}")
                        st.info(f"推荐 {data['prices']['recommended']}")
                        st.warning(f"引流 {data['prices']['aggressive']}")

                    st.subheader("📝 描述")
                    st.text_area("", data['description'], height=240)
                    copy_btn(data['description'], "复制全文")

                    st.subheader("🏷 标签")
                    st.write(", ".join(data['tags']))

                    st.subheader("📂 类目")
                    st.success(data['category'])

# ==================== 批量上货 ====================
with tab2:
    st.subheader("📦 批量上货")
    col_add = st.columns(3)
    with col_add[0]:
        new_title = st.text_input("商品标题", key="new_title")
    with col_add[1]:
        new_price = st.number_input("成本价", value=10.0, step=1.0, key="new_price")
    with col_add[2]:
        new_style = st.selectbox("风格", styles, key="new_style")

    if st.button("➕ 添加到列表", key="add_batch"):
        if new_title.strip():
            new_row = pd.DataFrame([{
                "原标题": new_title,
                "成本价": new_price,
                "风格": new_style
            }])
            st.session_state.batch_data = pd.concat([st.session_state.batch_data, new_row], ignore_index=True)
            st.success("✅ 添加成功")
        else:
            st.error("请输入标题")

    if not st.session_state.batch_data.empty:
        st.dataframe(st.session_state.batch_data, use_container_width=True)
        if st.button("✨ 批量生成", key="gen_batch", disabled=(st.session_state.gen_count >= free_limit)):
            with st.spinner("批量生成中..."):
                res = []
                for _, row in st.session_state.batch_data.iterrows():
                    d = generate_xianyu_content(row["原标题"], row["成本价"], row["风格"])
                    if d:
                        res.append({
                            "原标题": row["原标题"],
                            "闲鱼标题": d["xianyu_title"],
                            "描述": d["description"],
                            "推荐价": d["prices"]["recommended"],
                            "标签": ",".join(d["tags"]),
                            "类目": d["category"]
                        })
                        st.session_state.gen_count += 1
                if res:
                    df = pd.DataFrame(res)
                    st.dataframe(df, use_container_width=True)
                    bio = BytesIO()
                    with pd.ExcelWriter(bio, engine='openpyxl') as w:
                        df.to_excel(w, index=False)
                    st.download_button("📥 导出Excel", bio.getvalue(), "批量文案.xlsx")
    else:
        st.info("请先添加商品")

# ==================== 图片去重 + 可下载 ====================
with tab3:
    st.subheader("🖼️ 图片AI去重（可单张下载）")
    uploaded_files = st.file_uploader("批量上传图片", type=["jpg","jpeg","png"], accept_multiple_files=True)
    threshold = st.slider("重复识别精度（越小越严格）", 1, 15, 5)

    if uploaded_files:
        images = []
        for f in uploaded_files:
            try:
                img = Image.open(BytesIO(f.read())).convert("RGB")
                images.append(img)
            except:
                continue

        total = len(images)
        st.success(f"✅ 已加载 {total} 张图片")

        if st.button("🔍 开始去重"):
            with st.spinner("正在比对重复图片..."):
                unique_imgs, _, remain = find_duplicates(images, threshold=threshold)

                st.success(f"去重完成：共{total}张，保留{remain}张不重复图片")
                st.subheader("✅ 去重后可用图片")

                # 一行4张图 + 每个图下面都有下载按钮
                cols = st.columns(4)
                for i, img in enumerate(unique_imgs):
                    with cols[i % 4]:
                        st.image(img, use_column_width=True)
                        buf = BytesIO()
                        img.save(buf, format="JPEG")
                        st.download_button(
                            label=f"💾 下载第{i+1}张",
                            data=buf.getvalue(),
                            file_name=f"去重图片_{i+1}.jpg",
                            mime="image/jpeg"
                        )

# ==================== 历史记录 ====================
with tab4:
    st.subheader("📜 生成历史")
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("暂无记录")

st.divider()
st.caption("© 2026 闲鱼上货助手 · 稳定版")
