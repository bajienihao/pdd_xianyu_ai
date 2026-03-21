import streamlit as st
import dashscope
from http import HTTPStatus
import pandas as pd
from datetime import datetime
import json
import requests
import re

st.set_page_config(page_title="拼多多→闲鱼 AI助手 Pro", page_icon="🚀", layout="wide")
st.title("🚀 拼多多→闲鱼 AI上货助手 Pro（自动解析版）")

# ==================== 侧边栏（用户无需输入Key） ====================
st.sidebar.header("⚙️ 设置")
st.sidebar.success("✅ 已使用后台密钥（无需填写）")
st.sidebar.caption("所有生成由开发者提供额度支持")

try:
    dashscope.api_key = st.secrets["DASHSCOPE_API_KEY"]
except:
    st.sidebar.error("后台密钥未设置，请开发者先在Settings → Secrets配置")

# ==================== 初始化 ====================
if 'gen_count' not in st.session_state:
    st.session_state.gen_count = 0
if 'history' not in st.session_state:
    st.session_state.history = []
if 'auto_title' not in st.session_state:
    st.session_state.auto_title = ""
if 'auto_price' not in st.session_state:
    st.session_state.auto_price = 100.0

st.sidebar.metric("今日免费次数", f"{5 - st.session_state.gen_count}/5")
if st.session_state.gen_count >= 5:
    st.sidebar.error("🎯 免费版今日已用完！升级专业版解锁无限")

templates = ["默认闲置风", "情感故事风", "性价比爆款风", "限时秒杀风"]

# ==================== 解析函数 ====================
def parse_pdd_link(url):
    goods_id_match = re.search(r'goods_id=(\d+)', url)
    if not goods_id_match:
        return None, None
    goods_id = goods_id_match.group(1)
    
    mobile_url = f"https://mobile.yangkeduo.com/goods.html?goods_id={goods_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "Referer": "https://mobile.yangkeduo.com/"
    }
    try:
        r = requests.get(mobile_url, headers=headers, timeout=8)
        r.encoding = 'utf-8'
        text = r.text
        
        title_match = re.search(r'"goodsName":"([^"]+)"', text)
        title = title_match.group(1) if title_match else None
        
        price_match = re.search(r'"minGroupPrice":(\d+)', text) or re.search(r'"groupPrice":(\d+)', text) or re.search(r'"price":(\d+)', text)
        price = round(int(price_match.group(1)) / 100, 2) if price_match else None
        
        return title, price
    except:
        return None, None

# ==================== Tabs ====================
tab1, tab2, tab3, tab4 = st.tabs(["🔥 AI生成文案", "💰 智能定价", "📜 历史记录", "💎 升级专业版"])

with tab1:
    st.subheader("🔗 粘贴拼多多链接（自动解析标题+价格）")
    pdd_link = st.text_input("拼多多商品链接", placeholder="https://mobile.yangkeduo.com/goods.html?goods_id=xxxxxx")
    
    if st.button("🚀 解析链接", type="primary"):
        if not pdd_link:
            st.error("请粘贴链接")
        else:
            with st.spinner("正在从拼多多获取信息..."):
                title, price = parse_pdd_link(pdd_link)
            if title and price:
                st.success(f"✅ 解析成功！\n**标题**：{title}\n**原价**：{price}元")
                st.session_state.auto_title = title
                st.session_state.auto_price = float(price)
            else:
                st.warning("⚠️ 解析失败（平台可能改版），请手动输入下方标题和原价")
                st.session_state.auto_title = ""
                st.session_state.auto_price = 100.0

    style = st.selectbox("🎨 选择爆款风格", templates, key="style_auto")
    title = st.text_input("拼多多原标题", value=st.session_state.auto_title, key="title_auto")
    price = st.number_input("原价（元）", value=st.session_state.auto_price, step=1.0, key="price_auto")
    
    if st.button("生成闲鱼内容", type="primary", disabled=(st.session_state.gen_count >= 5)):
        if not title:
            st.error("请先输入或解析标题")
        else:
            prompt = f"""你是闲鱼10年资深卖家。严格使用【{style}】风格，把下面拼多多商品改成闲鱼爆款文案。
原标题: {title}
原价: {price}元

请**严格只输出JSON**（不要任何多余文字）：
{{
  "xianyu_title": "闲鱼标题（30字以内，加情绪词）",
  "description": "闲鱼描述（200-300字，突出闲置感+优势）",
  "prices": {{
    "conservative": "保守价（数字）",
    "recommended": "推荐价（数字，主推）",
    "aggressive": "激进价（数字）"
  }},
  "tips": "额外优化建议（1-2句）"
}}
"""
            with st.spinner("AI正在生成爆款文案..."):
                response = dashscope.Generation.call(
                    model='qwen-turbo',
                    messages=[{"role": "user", "content": prompt}],
                    result_format='message'
                )
            
            if response.status_code == HTTPStatus.OK:
                content = response.output.choices[0].message.content.strip()
                try:
                    data = json.loads(content)
                except:
                    data = {"xianyu_title": content[:100], "description": content}
                
                # 保存历史
                entry = {
                    "时间": datetime.now().strftime("%m-%d %H:%M"),
                    "风格": style,
                    "原标题": title,
                    "闲鱼标题": data.get("xianyu_title", "生成成功"),
                    "推荐价": data.get("prices", {}).get("recommended", "N/A")
                }
                st.session_state.history.append(entry)
                st.session_state.gen_count += 1
                
                # 显示结果
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader("📋 闲鱼标题（直接复制）")
                    st.code(data.get("xianyu_title", ""), language=None)
                with col2:
                    st.subheader("💰 建议售价")
                    p = data.get("prices", {})
                    st.success(f"""
                    保守价：{p.get('conservative', 'N/A')} 元  
                    **推荐价：{p.get('recommended', 'N/A')} 元**  
                    激进价：{p.get('aggressive', 'N/A')} 元
                    """)
                
                st.subheader("📝 闲鱼描述")
                st.text_area("", data.get("description", ""), height=180)
                st.info(data.get("tips", "已优化为闲鱼风格"))
                st.balloons()
                st.success("✅ 生成成功！复制到闲鱼即可")
            else:
                st.error("API调用失败，请稍后重试")

with tab2:
    st.subheader("💰 智能定价计算器")
    cost = st.number_input("你的进货成本（元）", value=500.0)
    shipping = st.number_input("运费（元）", value=10.0)
    if st.button("计算3档定价"):
        cons = round(cost * 1.3 + shipping)
        rec = round(cost * 1.5 + shipping)
        agg = round(cost * 1.8 + shipping)
        st.success(f"""
        保守价：{cons}元  
        **推荐价：{rec}元**  
        激进价：{agg}元
        """)

with tab3:
    st.subheader("📜 我的生成历史")
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 下载历史记录", csv, "我的闲鱼文案历史.csv", "text/csv")
    else:
        st.info("还没有生成记录，快去生成吧！")

with tab4:
    st.header("💎 升级专业版（99元/月）")
    st.markdown("""
    **解锁全部高级功能：**
    - ✅ 无限生成
    - ✅ 批量导入100条
    - ✅ AI客服回复
    - ✅ 永久历史记录
    """)
    if st.button("💰 立即升级专业版（联系我）", type="primary"):
        st.info("回复我「我要加支付」即可开通")

st.caption("© 2026 小白SaaS · 仅供学习测试 · 合规使用")