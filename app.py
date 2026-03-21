import streamlit as st
import dashscope
from http import HTTPStatus
import pandas as pd
from datetime import datetime
import json
import re
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ==================== 页面配置 ====================
st.set_page_config(page_title="拼多多→闲鱼AI上货助手 Pro", page_icon="🚀", layout="wide")
st.title("🚀 拼多多→闲鱼 AI上货助手 Pro 2026稳定版")

# ==================== 违禁词过滤（已关闭）====================
def filter_banned(text):
    return text  # 保留原文，不做替换

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
    except Exception as e:
        st.error(f"水印处理失败：{str(e)}")
        return img_bytes

# ==================== AI生成 ====================
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
if 'batch_data' not in st.session_state:
    st.session_state.batch_data = pd.DataFrame(columns=["原标题", "成本价", "风格"])

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

# ==================== 批量上货（修复版：手动表格输入）====================
with tab2:
    st.subheader("📦 批量上货（手动表格版）")
    st.info("请先添加商品行，再批量生成文案")
    
    # 手动添加行
    col_add = st.columns(3)
    with col_add[0]:
        new_title = st.text_input("商品标题", key="new_title")
    with col_add[1]:
        new_price = st.number_input("成本价", value=10.0, step=1.0, key="new_price")
    with col_add[2]:
        new_style = st.selectbox("风格", styles, key="new_style")
    
    if st.button("➕ 添加到批量列表", key="add_batch"):
        if new_title.strip():
            new_row = pd.DataFrame([{
                "原标题": new_title,
                "成本价": new_price,
                "风格": new_style
            }])
            st.session_state.batch_data = pd.concat([st.session_state.batch_data, new_row], ignore_index=True)
            st.success("✅ 添加成功！")
        else:
            st.error("请输入商品标题")
    
    # 显示批量列表
    if not st.session_state.batch_data.empty:
        st.dataframe(st.session_state.batch_data, use_container_width=True, key="batch_df")
        
        # 批量生成
        if st.button("✨ 批量生成闲鱼文案", key="gen_batch", disabled=(st.session_state.gen_count >= free_limit)):
            with st.spinner("批量生成中..."):
                batch_result = []
                for _, row in st.session_state.batch_data.iterrows():
                    try:
                        data = generate_xianyu_content(row["原标题"], row["成本价"], row["风格"])
                        if data:
                            batch_result.append({
                                "原标题": row["原标题"],
                                "闲鱼标题": data['xianyu_title'],
                                "描述": data['description'],
                                "推荐价": data['prices']['recommended'],
                                "标签": ",".join(data['tags']),
                                "类目": data['category']
                            })
                            st.session_state.gen_count += 1
                    except Exception as e:
                        st.warning(f"{row['原标题']} 生成失败：{str(e)}")
                        continue
                
                if batch_result:
                    df_result = pd.DataFrame(batch_result)
                    st.dataframe(df_result, use_container_width=True, key="batch_result_df")
                    bio = BytesIO()
                    with pd.ExcelWriter(bio, engine='openpyxl') as w:
                        df_result.to_excel(w, index=False)
                    st.download_button("📥 导出批量文案Excel", bio.getvalue(), "闲鱼批量文案.xlsx", key="dl_batch")
                else:
                    st.error("批量生成失败，请重试")
    else:
        st.info("暂无商品，请先添加")

# ==================== 图片上传+水印（修复版：流程清晰）====================
with tab3:
    st.subheader("🖼️ 图片上传 & 加水印")
    uploaded_file = st.file_uploader("上传商品图片（支持 jpg/png/jpeg）", type=["jpg", "png", "jpeg"], key="upload_img")
    mark_text = st.text_input("水印文字", value="闲鱼优品", key="watermark_text")
    
    if uploaded_file is not None:
        # 显示原图
        img_bytes = BytesIO(uploaded_file.getvalue())
        st.image(img_bytes, caption="原图预览", use_column_width=True)
        
        # 生成水印按钮
        if st.button("🖼️ 生成带水印图片", key="add_mark", type="primary"):
            with st.spinner("正在生成水印..."):
                marked_img = add_watermark(img_bytes, mark_text)
                st.image(marked_img, caption="加水印后效果", use_column_width=True)
                st.download_button(
                    label="💾 下载带水印图片",
                    data=marked_img,
                    file_name="xianyu_product_with_watermark.jpg",
                    mime="image/jpeg",
                    key="dl_img"
                )
                st.success("✅ 水印生成完成！可点击下载")
    else:
        st.info("请先上传一张图片")

# ==================== 历史记录 ====================
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
