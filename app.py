import streamlit as st
import dashscope
from http import HTTPStatus
import pandas as pd
from datetime import datetime
import json

st.set_page_config(page_title="拼多多→闲鱼 AI助手 Pro", page_icon="🚀", layout="wide")
st.title("🚀 拼多多→闲鱼 AI上货助手（升级专业版）")

# ==================== 侧边栏设置 ====================
st.sidebar.header("⚙️ 设置")
api_key = st.sidebar.text_input("通义千问 API Key", type="password", placeholder="sk-开头")
if api_key and api_key.startswith("sk-"):
    dashscope.api_key = api_key
else:
    st.sidebar.warning("请先在左侧输入你的API Key（阿里云免费获取）")

# 免费次数限制（每天5次，刷新会重置，正式版可改成数据库）
if 'gen_count' not in st.session_state:
    st.session_state.gen_count = 0

st.sidebar.metric("今日免费次数", f"{5 - st.session_state.gen_count}/5")
if st.session_state.gen_count >= 5:
    st.sidebar.error("🎯 免费版今日已用完！升级专业版解锁无限生成")

# 历史记录初始化
if 'history' not in st.session_state:
    st.session_state.history = []

# ==================== 模板库 ====================
templates = ["默认闲置风", "情感故事风", "性价比爆款风", "限时秒杀风"]

# ==================== Tabs ====================
tab1, tab2, tab3, tab4 = st.tabs(["🔥 AI生成文案", "💰 智能定价", "📜 历史记录", "💎 升级专业版"])

with tab1:
    style = st.selectbox("🎨 选择爆款风格（影响转化率）", templates)
    title = st.text_input("拼多多原标题", placeholder="例如：苹果13手机")
    price = st.number_input("原价（元）", value=999.0, step=1.0)
    
    if st.button("🚀 一键生成闲鱼内容", type="primary", disabled=(st.session_state.gen_count >= 5)):
        if not api_key.startswith("sk-"):
            st.error("请先输入API Key！")
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
                    data = {"raw": content, "xianyu_title": content[:100]}
                
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
                
                # 美观展示 + 复制优化
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader("📋 闲鱼标题（直接复制）")
                    st.code(data.get("xianyu_title", content), language=None)
                    st.caption("✅ 选中上方文字 → Ctrl + C 复制")
                
                with col2:
                    st.subheader("💰 建议售价")
                    p = data.get("prices", {})
                    st.success(f"""
                    保守价：{p.get('conservative', 'N/A')} 元  
                    **推荐价：{p.get('recommended', 'N/A')} 元**（最易成交）  
                    激进价：{p.get('aggressive', 'N/A')} 元
                    """)
                
                st.subheader("📝 闲鱼描述（复制后直接粘贴）")
                st.text_area("", data.get("description", content), height=180)
                
                st.subheader("💡 优化小贴士")
                st.info(data.get("tips", "已优化为闲鱼风格，建议配图加水印"))
                
                st.balloons()
                st.success("✅ 生成成功！复制到闲鱼发布即可")
            else:
                st.error(f"API错误：{response.message}")

with tab2:
    st.subheader("💰 智能定价计算器")
    cost = st.number_input("你的进货成本（元）", value=500.0)
    shipping = st.number_input("运费（元）", value=10.0)
    if st.button("计算3档定价"):
        cons = round(cost * 1.3 + shipping)
        rec = round(cost * 1.5 + shipping)
        agg = round(cost * 1.8 + shipping)
        st.success(f"""
        保守价：{cons}元（利润约30%）  
        **推荐价：{rec}元（最推荐）**  
        激进价：{agg}元（利润约80%）
        """)

with tab3:
    st.subheader("📜 我的生成历史")
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 下载历史记录（CSV）", csv, "我的闲鱼文案历史.csv", "text/csv")
    else:
        st.info("还没有生成记录，快去AI生成页试试吧！")

with tab4:
    st.header("💎 升级专业版（99元/月）")
    st.markdown("""
    **解锁全部高级功能：**
    - ✅ 无限生成（无次数限制）
    - ✅ 批量导入100条CSV
    - ✅ AI自动客服回复
    - ✅ 订单同步 + 利润仪表盘
    - ✅ 历史永久保存
    """)
    st.success("当前使用的是**免费测试版**")
    if st.button("💰 立即升级专业版（联系我）", type="primary"):
        st.balloons()
        st.markdown("**回复我「我要加支付」**，我立刻给你微信/支付宝支付代码（1分钟 接通）")
        st.info("或者先用免费版测试，觉得好再升级！")

st.caption("© 2026 小白SaaS · 仅供学习测试 · 合规使用")