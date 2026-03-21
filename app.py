import streamlit as st
import dashscope
from http import HTTPStatus
import pandas as pd
from datetime import datetime
import json
import requests
import re
import time
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ==================== 页面配置 ====================
st.set_page_config(page_title="拼多多→闲鱼AI上货助手 Pro", page_icon="🚀", layout="wide")
st.title("🚀 拼多多→闲鱼 AI上货助手 Pro 2026稳定版")

# ==================== 违禁词库（已关闭过滤）====================
def filter_banned(text):
    return text  # 不替换任何词，保留原文

# ==================== 一键复制 ====================
def copy_btn(text, label="📋 复制"):
    b64 = base64.b64encode(text.encode()).decode()
    js = f"""
    <button onclick="navigator.clipboard.writeText(decodeURIComponent(escape(window.atob('{b64}'))));">{label}</button>
    """
    st.markdown(js, unsafe_allow_html=True)

# ==================== 图片加水印 ====================
def add_watermark(img_bytes, text="闲鱼优品"):
    try:
        img = Image.open(img_bytes).convert("RGB")
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        w, h = img.size
        draw.text((w-120, h-30), text, fill=(255,255,255), font=font)
        buf = BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return buf
    except:
        return img_bytes

# ==================== 关闭自动解析 ====================
def parse_pdd_link(url):
    st.info("🔔 自动解析已关闭，请手动输入商品标题和价格")
    return None, None, None

def batch_parse(text):
    st.info("🔔 批量解析已关闭，请手动填写信息")
    return []

# ==================== AI生成（稳定版）====================
def generate_xianyu_content(title, price, style):
    prompt = f"""
你是闲鱼TOP级卖家，严格使用【{style}】风格。
商品原标题：{title}
成本价：{price}元

只返回标准JSON，不要任何多余内容、不要解释、不要包裹在代码块里：
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
            raw = re.sub(r'[\n\r\t]', '', raw)
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
            data['tips'] = data.get('tips', '实拍图+清晰描述更容易出单')
            return data
        else:
            st.error(f"API调用失败：{resp.message if hasattr(resp, 'message') else '未知错误'}")
            return None
    except json.JSONDecodeError as e:
        st.error(f"JSON解析失败：{str(e)}")
        return {
            "xianyu_title": filter_banned(title),
            "description": "个人闲置，成色如图，功能正常，拍下尽快发货~",
            "tags": ["闲置", "二手", "好物分享"],
            "category": "闲置物品",
            "prices": {
                "conservative": round(price*1.3),
                "recommended": round(price*1.5),
                "aggressive": round(price*1.1)
            },
            "tips": "实拍图+清晰描述更容易出单"
        }
    except Exception as e:
        st.error(f"生成失败：{str(e)}")
        return None

# ==================== 会话状态 ====================
st.sidebar.header("⚙️ 配置")
try:
    dashscope.api_key = st.secrets["DASHSCOPE_API_KEY"]
    st.sidebar.success("✅ API密钥已加载")
except:
    st.sidebar.error("❌ Secrets未配置，请在Streamlit Secrets中添加DASHSCOPE_API_KEY")

if 'gen_count' not in st.session_state:
    st.session_state.gen_count = 0
if 'history' not in st.session_state:
    st.session_state.history = []

free_limit = 5
st.sidebar.metric("今日免费次数", f"{free_limit - st.session_state.gen_count}/{free_limit}")

styles = ["默认闲置风","情感故事风","性价比爆款风","限时秒杀风"]

# ==================== 标签页 ====================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔥 单条AI生成",
    "📦 批量上货",
    "🖼️ 图片+水印",
    "📜 历史记录",
    "💎 专业版"
])

# ==================== 单条生成 ====================
with tab1:
    st.subheader("📝 手动输入商品信息")
    title = st.text_input("商品标题", value=st.session_state.get("title", ""), key="single_title")
    price = st.number_input("成本价", value=st.session_state.get("price", 10.0), step=1.0, key="single_price")
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
            with st.spinner("AI生成中..."):
                try:
                    if not is_pro:
                        st.session_state.gen_count += 1
                    data = generate_xianyu_content(title, price, style)
                    if not data:
                        st.error("生成失败，请重试")
                    else:
                        st.session_state.history.append({
                            "时间": datetime.now().strftime("%m-%d %H:%M"),
                            "原标题": title,
                            "闲鱼标题": data['xianyu_title'],
                            "推荐价": data['prices']['recommended'],
                            "风格": style
                        })

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
                        st.text_area("", data['description'], height=240, key="desc_single")
                        copy_btn(data['description'], "复制全文")

                        st.subheader("🏷 闲鱼标签")
                        st.write(", ".join(data['tags']))

                        st.subheader("📂 推荐类目")
                        st.success(data['category'])

                        st.subheader("💡 小贴士")
                        st.info(data['tips'])
                        st.balloons()
                except Exception as e:
                    st.error(f"错误：{str(e)}")

# ==================== 批量生成 ====================
with tab2:
    st.subheader("📦 批量上货（手动填写）")
    st.info("当前已关闭链接解析，可手动复制生成结果使用")

# ==================== 图片上传+水印（修复版）====================
with tab3:
    st.subheader("🖼️ 图片上传 & 加水印")
    uploaded_file = st.file_uploader("上传商品图片", type=["jpg", "png", "jpeg"], key="upload_img")
    mark_text = st.text_input("水印文字", value="闲鱼优品", key="watermark_text")
    
    if uploaded_file is not None:
        img_bytes = BytesIO(uploaded_file.getvalue())
        st.image(img_bytes, caption="原图预览", use_column_width=True)
        
        if st.button("🖼️ 生成水印图", key="add_mark"):
            marked = add_watermark(img_bytes, mark_text)
            st.image(marked, caption="加水印后效果", use_column_width=True)
            st.download_button("💾 保存带水印图片", marked, "xianyu_product.jpg", key="dl_img")

# ==================== 历史 ====================
with tab4:
    st.subheader("📜 生成历史")
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df, use_container_width=True, key="df_history")
        st.download_button("📥 导出CSV",
                           df.to_csv(index=False, encoding='utf-8-sig'),
                           "history.csv", key="dl_history")
    else:
        st.info("暂无记录")

# ==================== 专业版 ====================
with tab5:
    st.header("💎 专业版特权")
    st.success("""
✅ 无限AI生成
✅ 批量50条+
✅ 无水印高清图
✅ 违禁词实时检测
✅ 自动类目匹配
✅ 一键导出上架包
""")

st.divider()
st.caption("© 2026 小白SaaS · 稳定增强版 · 通义千问qwen-turbo")
