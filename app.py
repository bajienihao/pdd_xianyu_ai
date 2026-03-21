import streamlit as st
import dashscope
from http import HTTPStatus
import pandas as pd
from datetime import datetime
import json
import requests
import re

st.set_page_config(page_title="拼多多→闲鱼 AI助手 Pro", page_icon="🚀", layout="wide")
st.title("🚀 拼多多→闲鱼 AI上货助手 Pro（2026最终版）")

# ==================== 侧边栏 ====================
st.sidebar.header("⚙️ 设置")
st.sidebar.success("✅ 已使用后台密钥")
try:
    dashscope.api_key = st.secrets["DASHSCOPE_API_KEY"]
    st.sidebar.success("✅ Key已加载（qwen3.5-flash）")
except:
    st.sidebar.error("Secrets未设置")

if 'gen_count' not in st.session_state: st.session_state.gen_count = 0
if 'history' not in st.session_state: st.session_state.history = []
if 'auto_title' not in st.session_state: st.session_state.auto_title = ""
if 'auto_price' not in st.session_state: st.session_state.auto_price = 100.0

st.sidebar.metric("今日免费次数", f"{5 - st.session_state.gen_count}/5")

templates = ["默认闲置风", "情感故事风", "性价比爆款风", "限时秒杀风"]

# 解析函数（不变）
def parse_pdd_link(url):
    goods_id_match = re.search(r'goods_id=(\d+)', url) or re.search(r'/goods/(\d+)', url)
    if not goods_id_match: return None, None
    goods_id = goods_id_match.group(1)
    mobile_url = f"https://mobile.yangkeduo.com/goods.html?goods_id={goods_id}"
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 PddApp/6.0.0"}
    try:
        r = requests.get(mobile_url, headers=headers, timeout=10)
        r.encoding = 'utf-8'
        text = r.text
        title_match = re.search(r'"goodsName":"([^"]+)"', text) or re.search(r'"title":"([^"]+)"', text)
        title = title_match.group(1) if title_match else None
        price_match = re.search(r'"minGroupPrice":(\d+)', text) or re.search(r'"price":(\d+)', text)
        price = round(int(price_match.group(1)) / 100, 2) if price_match else None
        return title, price
    except:
        return None, None

tab1, tab2, tab3, tab4 = st.tabs(["🔥 AI生成文案", "💰 智能定价", "📜 历史记录", "💎 升级专业版"])

with tab1:
    st.subheader("🔗 粘贴拼多多链接")
    pdd_link = st.text_input("拼多多商品链接", placeholder="https://mobile.yangkeduo.com/goods.html?goods_id=xxxxxx")
    if st.button("🚀 解析链接", type="primary"):
        if pdd_link:
            with st.spinner("解析中..."):
                title, price = parse_pdd_link(pdd_link)
            if title and price:
                st.success(f"✅ 解析成功！标题：{title} | 原价：{price}元")
                st.session_state.auto_title = title
                st.session_state.auto_price = float(price)
            else:
                st.warning("解析失败，手动输入下方即可")

    style = st.selectbox("🎨 选择爆款风格", templates)
    title = st.text_input("拼多多原标题", value=st.session_state.auto_title)
    price = st.number_input("原价（元）", value=st.session_state.auto_price, step=1.0)
    
    if st.button("生成闲鱼内容", type="primary", disabled=(st.session_state.gen_count >= 5)):
        if not title:
            st.error("请填写标题")
        else:
            prompt = f"""你是闲鱼10年资深卖家。严格使用【{style}】风格，把下面拼多多商品改成闲鱼爆款文案。
原标题: {title}
原价: {price}元

请严格只输出JSON：
{{"xianyu_title": "闲鱼标题（30字内）","description": "200-300字描述","prices": {{"conservative": "数字","recommended": "数字","aggressive": "数字"}},"tips": "1-2句建议"}}
"""
            with st.spinner("AI生成中（qwen3.5-flash）..."):
                try:
                    response = dashscope.Generation.call(
                        model='qwen3.5-flash',   # ← 这里改成2026最新免费模型！
                        messages=[{"role": "user", "content": prompt}],
                        result_format='message'
                    )
                    if response.status_code == HTTPStatus.OK:
                        data = json.loads(response.output.choices[0].message.content.strip())
                        # 保存历史 + 显示结果（保持原样）
                        entry = {"时间": datetime.now().strftime("%m-%d %H:%M"), "风格": style, "原标题": title, "闲鱼标题": data.get("xianyu_title", ""), "推荐价": data.get("prices", {}).get("recommended", "N/A")}
                        st.session_state.history.append(entry)
                        st.session_state.gen_count += 1
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.subheader("📋 闲鱼标题"); st.code(data.get("xianyu_title", ""))
                        with col2:
                            st.subheader("💰 建议售价"); p = data.get("prices", {}); st.success(f"推荐价：{p.get('recommended', 'N/A')} 元")
                        st.subheader("📝 闲鱼描述"); st.text_area("", data.get("description", ""), height=180)
                        st.balloons()
                        st.success("✅ 生成成功！复制到闲鱼即可")
                    else:
                        st.error(f"API错误: {getattr(response, 'message', str(response))}")
                except Exception as e:
                    st.error(f"调用异常: {str(e)}")

# 其他tab保持不变（智能定价、历史记录、升级专业版）
with tab2:
    st.subheader("💰 智能定价计算器")
    cost = st.number_input("进货成本", value=500.0)
    shipping = st.number_input("运费", value=10.0)
    if st.button("计算定价"):
        st.success(f"推荐价：{round(cost*1.5 + shipping)}元")

with tab3:
    st.subheader("📜 历史记录")
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df)
        st.download_button("下载CSV", df.to_csv(index=False).encode('utf-8'), "历史.csv")
    else:
        st.info("还没有记录")

with tab4:
    st.header("💎 升级专业版")
    st.info("回复我「我要加支付」即可开通")

st.caption("© 2026 小白SaaS · 已切换qwen3.5-flash模型")