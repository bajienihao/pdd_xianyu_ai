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
import math

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="闲鱼上货助手 Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("🚀 闲鱼上货助手 Pro 增强版")

# ==================== 全局配置 ====================
st.sidebar.header("⚙️ 系统配置")
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
if 'templates' not in st.session_state:
    st.session_state.templates = {
        "默认闲置风": "个人闲置，成色如图，功能正常，拍下尽快发货~",
        "情感故事风": "因个人原因忍痛割爱，宝贝成色很新，功能完好，希望找到新主人~",
        "性价比爆款风": "全新未拆封，性价比超高，手慢无！",
        "限时秒杀风": "清仓特价，仅限今天，错过再等一年！"
    }

free_limit = 10
styles = list(st.session_state.templates.keys())

# ==================== 工具函数 ====================
def filter_banned(text):
    return text

# ==================== 修复后的复制按钮 ====================
def copy_btn(text, label="📋 复制"):
    # 安全可靠的 Streamlit 复制组件
    escaped_text = text.replace('"', '\\"').replace("'", "\\'")
    html = f"""
    <div style="margin: 5px 0;">
        <button onclick="
            const text = '{escaped_text}';
            navigator.clipboard.writeText(text).then(() => {{
                alert('复制成功！');
            }}).catch(err => {{
                alert('复制失败：' + err);
            }});
        " style="
            background-color:#4CAF50;
            color:white;
            border:none;
            padding:6px 12px;
            border-radius:6px;
            cursor:pointer;
            font-size:14px;
        ">
            {label}
        </button>
    </div>
    """
    st.components.v1.html(html, height=50)

def compress_image(img, quality=85):
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return buf

def generate_tags(title):
    base_tags = ["闲置", "二手", "好物分享"]
    words = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', title)
    for w in words[:3]:
        base_tags.append(w)
    return list(set(base_tags))[:5]

# ==================== AI文案生成 ====================
def generate_xianyu_content(title, price, style):
    template = st.session_state.templates.get(style, st.session_state.templates["默认闲置风"])
    prompt = f"""
你是闲鱼资深卖家，使用【{style}】风格撰写文案。
商品标题：{title}
成本价：{price}元
基础描述模板：{template}

只返回标准JSON，不要多余内容、不要解释、不要包裹：
{{
    "xianyu_title": "30字内吸引人标题",
    "description": "200-300字描述，基于模板扩展",
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
            data['description'] = filter_banned(data.get('description', template))
            data['tags'] = data.get('tags', generate_tags(title))
            data['category'] = data.get('category', '闲置物品')
            data['tips'] = data.get('tips', '实拍图清晰，实物拍摄更容易出单')
            return data
        else:
            st.error(f"API调用失败：{resp.message if hasattr(resp, 'message') else '未知错误'}")
            return None
    except Exception as e:
        st.error(f"生成失败：{str(e)}")
        return None

# ==================== 标签页 ====================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔥 单条生成", "📦 批量上货", "🖼️ 图片去重+压缩", "📝 文案模板", "📊 数据统计"
])

# ==================== 1. 单条生成（增强版）====================
with tab1:
    st.subheader("📝 商品信息 & 一键生成")
    col_input = st.columns(2)
    with col_input[0]:
        title = st.text_input("商品标题", key="single_title", placeholder="输入商品名称，例如：苹果17 Pro")
        price = st.number_input("成本价（元）", value=10.0, step=1.0, key="single_price")
        style = st.selectbox("文案风格", styles, key="single_style")
    
    with col_input[1]:
        st.subheader("💰 价格建议")
        st.info(f"引流价：{round(price*1.1)} 元（吸引点击）")
        st.info(f"保本价：{round(price*1.3)} 元（不亏本）")
        st.info(f"利润价：{round(price*1.5)} 元（赚利润）")
        auto_tags = generate_tags(title)
        tags = st.multiselect("推荐标签", auto_tags, default=auto_tags)

    col_btn = st.columns(2)
    with col_btn[0]:
        run = st.button("✨ 生成闲鱼文案", type="primary",
                        disabled=(st.session_state.gen_count >= free_limit), key="gen_single")
    with col_btn[1]:
        is_pro = st.checkbox("专业版（无限次生成）", value=False, key="pro_single")

    if run:
        if not title.strip():
            st.error("请输入商品标题")
        else:
            with st.spinner("AI正在生成爆款文案..."):
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

                    st.success("✅ 文案生成完成！")
                    col_result = st.columns([3,1])
                    with col_result[0]:
                        st.subheader("📋 标题")
                        st.code(data['xianyu_title'])
                        copy_btn(data['xianyu_title'])
                        
                        st.subheader("📝 描述")
                        st.text_area("", data['description'], height=200, key="desc_single")
                        copy_btn(data['description'], "复制描述")
                        
                        st.subheader("🏷 标签")
                        st.write(", ".join(tags))
                        copy_btn(", ".join(tags), "复制标签")
                    
                    with col_result[1]:
                        st.subheader("💰 定价方案")
                        st.success(f"引流价：{data['prices']['aggressive']} 元")
                        st.info(f"保本价：{data['prices']['conservative']} 元")
                        st.warning(f"利润价：{data['prices']['recommended']} 元")
                        
                        st.subheader("📂 类目")
                        st.success(data['category'])
                        
                        st.subheader("💡 小贴士")
                        st.info(data['tips'])
                    
                    # 一键复制整套装车文案
                    full_text = f"标题：{data['xianyu_title']}\n\n描述：{data['description']}\n\n标签：{', '.join(tags)}\n\n价格：{data['prices']['recommended']}元"
                    st.subheader("📋 一键复制全套文案")
                    copy_btn(full_text, "复制全套文案")

# ==================== 2. 批量上货 ====================
with tab2:
    st.subheader("📦 批量生成文案")
    col_add = st.columns(3)
    with col_add[0]:
        new_title = st.text_input("商品标题", key="batch_new_title")
    with col_add[1]:
        new_price = st.number_input("成本价", value=10.0, step=1.0, key="batch_new_price")
    with col_add[2]:
        new_style = st.selectbox("风格", styles, key="batch_new_style")

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

    if not st.session_state.batch_data.empty:
        st.dataframe(st.session_state.batch_data, use_container_width=True, key="batch_df")
        if st.button("✨ 批量生成闲鱼文案", key="gen_batch", disabled=(st.session_state.gen_count >= free_limit)):
            with st.spinner("批量生成中..."):
                res = []
                for _, row in st.session_state.batch_data.iterrows():
                    d = generate_xianyu_content(row["原标题"], row["成本价"], row["风格"])
                    if d:
                        res.append({
                            "原标题": row["原标题"],
                            "闲鱼标题": d["xianyu_title"],
                            "描述": d["description"],
                            "引流价": d["prices"]["aggressive"],
                            "保本价": d["prices"]["conservative"],
                            "利润价": d["prices"]["recommended"],
                            "标签": ",".join(d["tags"]),
                            "类目": d["category"]
                        })
                        st.session_state.gen_count += 1
                if res:
                    df_result = pd.DataFrame(res)
                    st.dataframe(df_result, use_container_width=True, key="batch_result_df")
                    bio = BytesIO()
                    with pd.ExcelWriter(bio, engine='openpyxl') as w:
                        df_result.to_excel(w, index=False)
                    st.download_button("📥 导出批量文案Excel", bio.getvalue(), "闲鱼批量文案.xlsx", key="dl_batch")
    else:
        st.info("暂无商品，请先添加到列表")

# ==================== 3. 图片去重+压缩 ====================
with tab3:
    st.subheader("🖼️ 图片AI去重 & 压缩（适合闲鱼上传）")
    uploaded_files = st.file_uploader(
        "点击选择图片（手机直接打开相册）",
        type=["jpg","jpeg","png"],
        accept_multiple_files=True,
        key="img_uploader_final"
    )
    quality = st.slider("图片压缩质量（越高越清晰，文件越大）", 50, 100, 85)

    if uploaded_files:
        st.success(f"✅ 已加载 {len(uploaded_files)} 张图片")
        imgs = []
        for f in uploaded_files:
            try:
                img = Image.open(BytesIO(f.read())).convert("RGB")
                imgs.append(img)
            except:
                continue

        st.subheader("已上传图片预览")
        cols = st.columns(4)
        for i, img in enumerate(imgs):
            with cols[i % 4]:
                st.image(img, use_column_width=True)

        if st.button("🔍 开始去重并压缩", type="primary", key="start_dedup"):
            with st.spinner("正在检测重复图片并压缩..."):
                hash_list = []
                unique_imgs = []
                for img in imgs:
                    h = imagehash.average_hash(img)
                    if h not in hash_list:
                        hash_list.append(h)
                        unique_imgs.append(img)

            st.success(f"去重完成：保留 {len(unique_imgs)} 张不重复图片")
            st.subheader("✅ 去重后可上传图片（已压缩）")

            cols_out = st.columns(4)
            for i, img in enumerate(unique_imgs):
                with cols_out[i % 4]:
                    st.image(img, use_column_width=True)
                    compressed_buf = compress_image(img, quality=quality)
                    st.download_button(
                        f"下载第{i+1}张",
                        data=compressed_buf.getvalue(),
                        file_name=f"闲鱼商品图_{i+1}.jpg",
                        mime="image/jpeg",
                        key=f"download_img_{i}"
                    )
    else:
        st.info("请选择图片")

# ==================== 4. 文案模板管理 ====================
with tab4:
    st.subheader("📝 自定义文案模板")
    new_template_name = st.text_input("新模板名称")
    new_template_content = st.text_area("新模板内容", height=100, placeholder="输入你的自定义文案模板，例如：宝贝成色很新，功能完好，因个人原因转让...")
    if st.button("➕ 添加模板"):
        if new_template_name and new_template_content:
            st.session_state.templates[new_template_name] = new_template_content
            st.success("✅ 模板添加成功！")
            st.rerun()
        else:
            st.error("请输入模板名称和内容")

    st.subheader("现有模板")
    for name, content in st.session_state.templates.items():
        with st.expander(name):
            st.write(content)
            if st.button(f"删除「{name}」", key=f"del_{name}"):
                del st.session_state.templates[name]
                st.rerun()

# ==================== 5. 数据统计 ====================
with tab5:
    st.subheader("📊 使用统计")
    col_stat = st.columns(3)
    with col_stat[0]:
        st.metric("今日生成文案数", st.session_state.gen_count)
    with col_stat[1]:
        st.metric("历史生成总数", len(st.session_state.history))
    with col_stat[2]:
        st.metric("剩余免费次数", max(0, free_limit - st.session_state.gen_count))

    st.subheader("📜 最近生成记录")
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history[-10:])
        st.dataframe(df, use_container_width=True, key="history_df")
    else:
        st.info("暂无记录")

st.divider()
st.caption("© 2026 闲鱼上货助手 Pro · 增强版")
