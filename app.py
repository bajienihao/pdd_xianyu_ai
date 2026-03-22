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
from PIL import Image, ImageDraw, ImageFont
import math

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="闲鱼上货助手 Pro Max",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("🚀 闲鱼上货助手 Pro Max · 全自动省心版")

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

free_limit = 20
styles = list(st.session_state.templates.keys())

# ==================== 违禁词库 ====================
banned_words = {
    "全新": "几乎全新",
    "正品": "品质保障",
    "批发": "打包出",
    "代理": "代友出",
    "代购": "个人闲置",
    "厂货": "工厂余单",
    "免税": "无税渠道",
    "高仿": "外观一致",
    "A货": "款式相同",
    "治疗": "养护",
    "减肥": "塑形",
    "壮阳": "调理",
    "治病": "舒缓",
    "走私": "个人闲置",
    "最低价": "实惠价",
    "秒杀": "手慢无",
    "全网最低": "性价比高"
}

def filter_banned(text):
    if not text:
        return ""
    for w, r in banned_words.items():
        text = text.replace(w, r)
    return text

# ==================== 复制按钮（无弹窗）====================
def copy_btn(text, label="📋 复制"):
    escaped_text = text.replace('"', '\\"').replace("'", "\\'")
    html = f"""
    <div style="margin:5px 0;">
        <button style="
            background-color:#4CAF50;
            color:white;
            border:none;
            padding:6px 12px;
            border-radius:6px;
            cursor:pointer;
            font-size:14px;
        " onclick="
            navigator.clipboard.writeText('{escaped_text}');
            const btn = this;
            const t = btn.innerText;
            btn.innerText = '✅ 复制成功';
            btn.style.backgroundColor='#10b981';
            setTimeout(()=>{{
                btn.innerText = t;
                btn.style.backgroundColor='#4CAF50';
            }}, 1200);
        ">
            {label}
        </button>
    </div>
    """
    st.components.v1.html(html, height=50)

# ==================== 图片工具 ====================
def compress_image(img, quality=85):
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return buf

def add_watermark(img, text="闲鱼实拍"):
    try:
        img = img.convert("RGB")
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        draw.text((20, 20), text, fill=(255, 255, 255), font=font)
        draw.text((22, 22), text, fill=(0, 0, 0), font=font)
    except:
        pass
    return img

# ==================== 标签与标题 ====================
def generate_tags(title):
    base_tags = ["闲置", "二手", "好物分享", "个人闲置", "实拍"]
    words = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', title)
    for w in words[:4]:
        base_tags.append(w)
    return list(set(base_tags))[:8]

def generate_3_titles(title):
    t = filter_banned(title)
    return [
        f"{t} 个人闲置 成色新 功能正常",
        f"{t} 低价转让 实拍如图 拍下速发",
        f"{t} 性价比高 非诚勿扰 包邮可谈"
    ]

# ==================== 营销话术 ====================
def sale_script():
    return {
        "议价话术": "已经是实在价啦，不刀不包，拍下当天发货～",
        "防到手刀": "发货前会拍完整视频，签收后不以成色、不喜欢等理由退货",
        "发货通知": "已发货！单号：{no}，注意查收，有问题随时联系",
        "催单话术": "喜欢直接拍，今天拍今天发，库存不多啦",
        "包邮话术": "两件以上可包邮，和其他宝贝一起带走更划算",
        "售后话术": "功能已测好，签收请及时验收，有问题24小时内联系"
    }

def best_post_time():
    return """
📈 闲鱼最佳发布时间段（必看）
1. 12:00-13:30 午休流量高峰
2. 18:00-21:00 晚间黄金时段
3. 21:00-23:00 深夜成交率最高
小技巧：每4小时擦亮一次，曝光翻倍
"""

# ==================== AI生成 ====================
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
                    "aggressive": round(price*1.1)}
            data['xianyu_title'] = filter_banned(data.get('xianyu_title', title))
            data['description'] = filter_banned(data.get('description', template))
            data['tags'] = data.get('tags', generate_tags(title))
            data['category'] = data.get('category', '闲置物品')
            data['tips'] = filter_banned(data.get('tips', '实拍清晰更容易出单'))
            return data
        else:
            st.error(f"API调用失败：{resp.message if hasattr(resp,'message') else '未知错误'}")
            return None
    except Exception as e:
        st.error(f"生成失败：{str(e)}")
        return None

# ==================== 标签页 ====================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔥 单条生成", "📦 批量上货", "🖼️ 图片处理",
    "📝 文案模板", "💬 营销话术", "📊 数据统计"
])

# ==================== 1. 单条生成 ====================
with tab1:
    st.subheader("📝 商品信息 & 一键生成")
    col_input = st.columns(2)
    with col_input[0]:
        title = st.text_input("商品标题", key="single_title", placeholder="输入商品名称")
        price = st.number_input("成本价（元）", value=10.0, step=1.0, key="single_price")
        style = st.selectbox("文案风格", styles, key="single_style")
    with col_input[1]:
        st.subheader("💰 价格建议")
        st.info(f"引流价：{round(price*1.1)} 元")
        st.info(f"保本价：{round(price*1.3)} 元")
        st.info(f"利润价：{round(price*1.5)} 元")
        auto_tags = generate_tags(title)
        tags = st.multiselect("推荐标签", auto_tags, default=auto_tags)

    col_btn = st.columns(2)
    with col_btn[0]:
        run = st.button("✨ 生成闲鱼文案", type="primary",
                        disabled=(st.session_state.gen_count >= free_limit))
    with col_btn[1]:
        is_pro = st.checkbox("专业版（无限次）", value=False)

    if run:
        if not title.strip():
            st.error("请输入商品标题")
        else:
            with st.spinner("AI生成爆款文案中..."):
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
                        st.subheader("📋 主标题")
                        st.code(data['xianyu_title'])
                        copy_btn(data['xianyu_title'])

                        st.subheader("📝 描述")
                        st.text_area("", data['description'], height=200)
                        copy_btn(data['description'], "复制描述")

                        st.subheader("🏷 标签")
                        st.write(", ".join(tags))
                        copy_btn(", ".join(tags), "复制标签")

                        st.subheader("📌 三版备选标题")
                        titles3 = generate_3_titles(title)
                        for i, t in enumerate(titles3, 1):
                            st.write(f"{i}. {t}")
                            copy_btn(t, f"复制标题{i}")

                    with col_result[1]:
                        st.subheader("💰 定价")
                        st.success(f"引流价：{data['prices']['aggressive']}")
                        st.info(f"保本价：{data['prices']['conservative']}")
                        st.warning(f"利润价：{data['prices']['recommended']}")
                        st.subheader("📂 类目")
                        st.success(data['category'])
                        st.subheader("💡 小贴士")
                        st.info(data['tips'])

                    full = f"标题：{data['xianyu_title']}\n\n描述：{data['description']}\n\n标签：{', '.join(tags)}\n\n售价：{data['prices']['recommended']}元"
                    st.subheader("📋 一键复制全套")
                    copy_btn(full, "复制全套文案")

# ==================== 2. 批量上货 ====================
with tab2:
    st.subheader("📦 批量生成文案")
    c1,c2,c3 = st.columns(3)
    with c1:
        nt = st.text_input("商品标题")
    with c2:
        np = st.number_input("成本价", value=10.0)
    with c3:
        ns = st.selectbox("风格", styles)

    if st.button("➕ 添加到批量列表"):
        if nt.strip():
            new_row = pd.DataFrame([{"原标题":nt,"成本价":np,"风格":ns}])
            st.session_state.batch_data = pd.concat([st.session_state.batch_data, new_row], ignore_index=True)
            st.success("✅ 添加成功")
        else:
            st.error("请输入标题")

    if not st.session_state.batch_data.empty:
        st.dataframe(st.session_state.batch_data, use_container_width=True)
        if st.button("✨ 批量生成闲鱼文案", disabled=(st.session_state.gen_count >= free_limit)):
            with st.spinner("批量生成中..."):
                res = []
                for _, r in st.session_state.batch_data.iterrows():
                    d = generate_xianyu_content(r["原标题"], r["成本价"], r["风格"])
                    if d:
                        res.append({
                            "原标题":r["原标题"],
                            "闲鱼标题":d["xianyu_title"],
                            "描述":d["description"],
                            "引流价":d["prices"]["aggressive"],
                            "保本价":d["prices"]["conservative"],
                            "利润价":d["prices"]["recommended"],
                            "标签":",".join(d["tags"]),
                            "类目":d["category"]
                        })
                        st.session_state.gen_count += 1
                if res:
                    df = pd.DataFrame(res)
                    st.dataframe(df, use_container_width=True)
                    bio = BytesIO()
                    with pd.ExcelWriter(bio, engine='openpyxl') as w:
                        df.to_excel(w, index=False)
                    st.download_button("📥 导出Excel", bio.getvalue(), "闲鱼批量文案.xlsx")
    else:
        st.info("先添加商品到列表")

# ==================== 3. 图片去重+压缩+水印 ====================
with tab3:
    st.subheader("🖼️ 图片去重 + 压缩 + 防盗水印")
    uploaded = st.file_uploader("上传图片", type=["jpg","jpeg","png"], accept_multiple_files=True)
    qual = st.slider("压缩质量", 50, 100, 85)
    water_text = st.text_input("水印文字", "闲鱼实拍")

    if uploaded:
        st.success(f"✅ 已加载 {len(uploaded)} 张")
        imgs = []
        for f in uploaded:
            try:
                img = Image.open(BytesIO(f.read())).convert("RGB")
                imgs.append(img)
            except:
                continue

        st.subheader("预览")
        cols = st.columns(4)
        for i, img in enumerate(imgs):
            cols[i%4].image(img, use_column_width=True)

        if st.button("🔍 去重 + 压缩 + 加水印", type="primary"):
            with st.spinner("处理中..."):
                hash_list = []
                unique = []
                for img in imgs:
                    h = imagehash.average_hash(img)
                    if h not in hash_list:
                        hash_list.append(h)
                        unique.append(add_watermark(img, water_text))

            st.success(f"去重完成：保留 {len(unique)} 张")
            cols_out = st.columns(4)
            for i, img in enumerate(unique):
                with cols_out[i%4]:
                    st.image(img, use_column_width=True)
                    b = compress_image(img, qual)
                    st.download_button(f"下载{i+1}", b, f"闲鱼图_{i+1}.jpg", "image/jpeg")

# ==================== 4. 文案模板 ====================
with tab4:
    st.subheader("📝 自定义文案模板")
    n1 = st.text_input("模板名称")
    n2 = st.text_area("模板内容", height=100)
    if st.button("➕ 添加模板"):
        if n1 and n2:
            st.session_state.templates[n1] = n2
            st.success("✅ 添加成功")
            st.rerun()
    for name, content in st.session_state.templates.items():
        with st.expander(name):
            st.write(content)
            if st.button(f"删除「{name}」", key=f"d_{name}"):
                del st.session_state.templates[name]
                st.rerun()

# ==================== 5. 营销话术 ====================
with tab5:
    st.subheader("💬 闲鱼必备营销话术")
    talks = sale_script()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 议价/催单")
        for k in ["议价话术", "催单话术", "包邮话术"]:
            st.write(talks[k])
            copy_btn(talks[k], f"复制{k}")
    with col2:
        st.markdown("#### 售后/防坑")
        for k in ["防到手刀", "发货通知", "售后话术"]:
            st.write(talks[k])
            copy_btn(talks[k], f"复制{k}")

    st.divider()
    st.subheader("📈 最佳发布时间指南")
    st.code(best_post_time())

# ==================== 6. 数据统计 ====================
with tab6:
    st.subheader("📊 使用统计")
    c1,c2,c3 = st.columns(3)
    c1.metric("今日生成", st.session_state.gen_count)
    c2.metric("历史记录", len(st.session_state.history))
    c3.metric("剩余免费", max(0, free_limit - st.session_state.gen_count))

    st.subheader("📜 最近记录")
    if st.session_state.history:
        st.dataframe(pd.DataFrame(st.session_state.history[-10:]), use_container_width=True)
    else:
        st.info("暂无记录")

st.divider()
st.caption("© 2026 闲鱼上货助手 Pro Max · 全自动省心版")
