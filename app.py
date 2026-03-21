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
from io import BytesIO, StringIO
from PIL import Image, ImageDraw, ImageFont
import random

# ==================== 页面配置 ====================
st.set_page_config(page_title="拼多多→闲鱼AI上货助手 Pro", page_icon="🚀", layout="wide")
st.title("🚀 拼多多→闲鱼 AI上货助手 Pro 2026至尊版")

# ==================== 违禁词库（闲鱼超强版）====================
banned_words = [
    "全新","正品","原厂","代购","官网","授权","专卖","特供",
    "高仿","A货","一比一","走私","免税","海关扣","罚没",
    "批发","清仓","秒杀","军工","医用","内部渠道","假货",
    "原厂直供","限量","限购","绝版","进口","原装","盗版"
]

def filter_banned(text):
    for w in banned_words:
        text = text.replace(w, "【违规词】")
    return text

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

# ==================== 解析单个链接 ====================
def parse_pdd_link(url):
    try:
        goods_id_match = re.search(r'goods_id=(\d+)', url) or re.search(r'/goods/(\d+)', url)
        if not goods_id_match:
            return None, None, None
        goods_id = goods_id_match.group(1)
        mobile_url = f"https://mobile.yangkeduo.com/goods.html?goods_id={goods_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 PddApp/6.0.0"
        }
        r = requests.get(mobile_url, headers=headers, timeout=10)
        r.encoding = 'utf-8'
        text = r.text

        title_match = re.search(r'"goodsName":"([^"]+)"', text) or re.search(r'"title":"([^"]+)"', text)
        title = title_match.group(1) if title_match else None

        price_match = re.search(r'"minGroupPrice":(\d+)', text) or re.search(r'"price":(\d+)', text)
        price = round(int(price_match.group(1)) / 100, 2) if price_match else None

        imgs = re.findall(r'"thumbUrl":"(https://[^"]+)"', text)
        img_url = imgs[0].replace("\\u002F", "/") if imgs else None
        return title, price, img_url
    except:
        return None, None, None

# ==================== 批量链接解析 ====================
def batch_parse(text):
    urls = re.findall(r"https?://\S+", text)
    res = []
    for u in urls[:10]:
        t, p, img = parse_pdd_link(u)
        if t and p:
            res.append({"链接": u, "标题": t, "价格": p, "主图": img})
    return res

# ==================== AI生成 ====================
def generate_xianyu_content(title, price, style):
    prompt = f"""
你是闲鱼TOP级卖家，严格使用【{style}】风格。
商品原标题：{title}
成本价：{price}元

只返回标准JSON，不要任何多余内容：
{{
    "xianyu_title": "30字内标题",
    "description": "200-300字描述",
    "tags": ["标签1","标签2","标签3","标签4","标签5"],
    "category": "推荐类目",
    "prices": {{
        "conservative": 数字,
        "recommended": 数字,
        "aggressive": 数字
    }},
    "tips": "上架小技巧"
}}
"""
    resp = dashscope.Generation.call(
        model='qwen3.5-flash',
        messages=[{"role": "user", "content": prompt}],
        result_format='message'
    )
    if resp.status_code == HTTPStatus.OK:
        raw = resp.output.choices[0].message.content.strip()
        raw = re.sub(r'^```json|```$', '', raw).strip()
        data = json.loads(raw)
        data['xianyu_title'] = filter_banned(data['xianyu_title'])
        data['description'] = filter_banned(data['description'])
        return data
    return None

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
if 'batch_result' not in st.session_state:
    st.session_state.batch_result = []

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
    st.subheader("🔗 拼多多链接解析")
    link = st.text_input("商品链接", key="single_link")
    if st.button("🚀 解析商品", type="primary", key="parse_single"):
        t, p, img = parse_pdd_link(link)
        if t and p:
            st.session_state['title'] = t
            st.session_state['price'] = p
            st.session_state['img_url'] = img
            st.success(f"✅ {t} | ￥{p}")
        else:
            st.warning("解析失败")

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
        if not title:
            st.error("请输入标题")
        else:
            with st.spinner("AI生成中..."):
                try:
                    if not is_pro:
                        st.session_state.gen_count += 1
                    data = generate_xianyu_content(title, price, style)
                    if not data:
                        st.error("生成失败")
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
    st.subheader("📦 批量链接一行一个")
    batch_input = st.text_area("链接列表", height=200, key="batch_links")
    batch_style = st.selectbox("批量生成风格", styles, key="batch_style")
    pro_batch = st.checkbox("专业版批量模式", value=False, key="pro_batch")

    if st.button("🔍 解析并批量生成", key="gen_batch"):
        with st.spinner("批量处理中..."):
            goods = batch_parse(batch_input)
            if not goods:
                st.warning("无有效商品")
            else:
                st.dataframe(pd.DataFrame(goods), key="df_batch")
                res = []
                for g in goods[:5]:
                    try:
                        d = generate_xianyu_content(g['标题'], g['价格'], batch_style)
                        if d:
                            res.append({
                                "原标题": g['标题'],
                                "闲鱼标题": d['xianyu_title'],
                                "描述": d['description'],
                                "推荐价": d['prices']['recommended'],
                                "标签": ",".join(d['tags']),
                                "类目": d['category']
                            })
                        time.sleep(1)
                    except:
                        continue
                st.session_state.batch_result = res
                df = pd.DataFrame(res)
                st.dataframe(df, use_container_width=True, key="df_result")
                bio = BytesIO()
                with pd.ExcelWriter(bio, engine='openpyxl') as w:
                    df.to_excel(w, index=False)
                st.download_button("📥 导出Excel", bio.getvalue(), "闲鱼批量文案.xlsx", key="dl_batch")

# ==================== 图片下载+水印 ====================
with tab3:
    st.subheader("🖼️ 商品图片下载 & 水印")
    img_link = st.text_input("商品链接", key="img_link")
    mark_text = st.text_input("水印文字", value="闲鱼优品", key="watermark_text")
    if st.button("🖼️ 获取并加水印", key="get_img"):
        t, p, img_url = parse_pdd_link(img_link)
        if img_url:
            img_data = requests.get(img_url).content
            buf = BytesIO(img_data)
            marked = add_watermark(buf, mark_text)
            st.image(marked, use_column_width=True)
            st.download_button("💾 保存图片", marked, "with_watermark.jpg", key="dl_img")
        else:
            st.warning("获取图片失败")

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
    st.info("开通：回复「我要加支付」")

st.divider()
st.caption("© 2026 小白SaaS · 至尊增强版 · 通义千问qwen3.5-flash")
