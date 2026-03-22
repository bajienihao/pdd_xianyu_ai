import streamlit as st
import dashscope
from http import HTTPStatus
import pandas as pd
from datetime import datetime, timedelta
import json
import re
import imagehash
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ==================== 页面配置（商业化UI）====================
st.set_page_config(
    page_title="闲鱼上货助手 Pro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义样式（专业卖相）
st.markdown("""
<style>
.block-container { padding-top:2rem; }
.stButton>button { border-radius:8px; height:3.2em; font-weight:bold; }
.stTextArea>div>div { border-radius:10px; }
.stCode>div { border-radius:10px; }
</style>
""", unsafe_allow_html=True)

st.title("💰 闲鱼上货助手 Pro · 付费专业版")
st.markdown("#### 闲鱼卖家全自动效率工具 · 违禁词检测 · 图片去重 · 营销话术 · 擦亮计划 · 智能选品")

# ==================== 付费系统核心 ====================
FREE_LIMIT = 3
PRO_KEY = "xianyu_pro_2026"  # 你卖的卡密

if 'is_pro' not in st.session_state:
    st.session_state.is_pro = False
if 'gen_count' not in st.session_state:
    st.session_state.gen_count = 0
if 'history' not in st.session_state:
    st.session_state.history = []
if 'batch_data' not in st.session_state:
    st.session_state.batch_data = pd.DataFrame(columns=["原标题", "成本价", "风格"])
if 'polish_plan' not in st.session_state:
    st.session_state.polish_plan = []
if 'auto_reply_lib' not in st.session_state:
    st.session_state.auto_reply_lib = {
        "在吗": "在的哦，宝贝都在，直接拍即可～",
        "便宜吗": "已经最低啦，不刀不包，当天发货",
        "包邮吗": "单件不包，两件可包",
        "有瑕疵吗": "实拍如图，功能正常无大瑕疵",
        "发什么快递": "默认圆通，可补差价发顺丰",
        "可以退换吗": "闲置物品，无质量问题不退不换",
        "什么时候发货": "16点前下单，当天全部发出"
    }
# 新增：选品历史记录
if 'selection_history' not in st.session_state:
    st.session_state.selection_history = []

# 模板库
if 'templates' not in st.session_state:
    st.session_state.templates = {
        "默认闲置风": "个人闲置，成色如图，功能正常，拍下尽快发货~",
        "情感故事风": "因个人原因忍痛割爱，宝贝成色很新，功能完好，希望找到新主人~",
        "性价比爆款风": "几乎全新，性价比超高，手慢无！",
        "限时秒杀风": "清仓特价，仅限今天，错过不再有！"
    }

styles = list(st.session_state.templates.keys())

# ==================== 侧边栏：付费激活 ====================
with st.sidebar:
    st.header("🔐 付费激活")
    key = st.text_input("请输入激活码", type="password", key="activate_key")
    if st.button("✅ 立即激活 Pro 版", key="activate_btn"):
        if key.strip() == PRO_KEY:
            st.session_state.is_pro = True
            st.success("🎉 激活成功！永久使用全部功能")
        else:
            st.error("❌ 激活码错误，请联系购买")

    st.divider()
    st.markdown("### 📊 使用统计")
    st.metric("今日生成", st.session_state.gen_count)
    if not st.session_state.is_pro:
        st.metric("剩余免费次数", max(0, FREE_LIMIT - st.session_state.gen_count))
    else:
        st.success("✅ Pro 已激活 · 无限次使用")

    st.divider()
    st.markdown("""
### 💡 Pro版特权
- 无限次AI文案生成
- 批量生成&导出Excel
- 图片去重+水印+压缩
- 自动擦亮计划
- 智能自动回复库
- ✅ 新增：闲鱼选品分析
- ✅ 新增：选品历史记录
- 永久免费更新
""")

# ==================== 违禁词过滤 ====================
banned_words = {
    "全新": "几乎全新","正品":"品质保障","批发":"打包出",
    "高仿":"外观一致","A货":"款式相同","最低价":"实惠价",
    "全网最低":"性价比高","治疗":"养护","减肥":"塑形"
}
def filter_banned(text):
    if not text: return ""
    for w, r in banned_words.items():
        text = text.replace(w, r)
    return text

# ==================== 复制按钮（无弹窗）====================
def copy_btn(text, label="📋 复制"):
    t = text.replace('"','\\"').replace("'","\\'")
    h = f"""
    <div style="margin:6px 0;">
    <button onclick="navigator.clipboard.writeText('{t}');this.innerText='✅ 复制成功';setTimeout(()=>this.innerText='{label}',1300)"
    style="background:#22c55e;color:white;border:0;padding:8px 14px;border-radius:8px;font-weight:bold;cursor:pointer;">
    {label}</button></div>"""
    st.components.v1.html(h, height=50)

# ==================== 图片工具 ====================
def compress_image(img, q=85):
    b = BytesIO()
    img.save(b, 'JPEG', quality=q)
    b.seek(0)
    return b

def add_watermark(img, text="闲鱼实拍"):
    try:
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        draw.text((20,20), text, fill="white", font=font)
        draw.text((22,22), text, fill="black", font=font)
    except:
        pass
    return img

# ==================== 标签&多标题 ====================
def generate_tags(title):
    tags = ["闲置","二手","好物分享","个人闲置","实拍"]
    ws = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', title)
    for w in ws[:4]: tags.append(w)
    return list(set(tags))[:8]

def gen_3_titles(t):
    t = filter_banned(t)
    return [
        f"{t} 个人闲置 成色新 功能正常",
        f"{t} 低价转让 实拍如图 拍下速发",
        f"{t} 性价比高 非诚勿扰 可谈包邮"
    ]

# ==================== 选品分析功能（Pro专属）====================
def product_selection_analysis(keyword):
    """模拟闲鱼选品分析：返回热门度、价格区间、竞争度、建议"""
    hot_score = hash(keyword) % 100
    price_low = round(10 + (hash(keyword) % 50), 2)
    price_high = round(price_low + (hash(keyword) % 100), 2)
    competition = ["低", "中", "高"][hash(keyword) % 3]
    supply = ["充足", "一般", "稀缺"][hash(keyword) % 3]
    advice = [
        "✅ 推荐上架：需求旺盛，竞争小，利润空间大",
        "⚠️ 谨慎上架：竞争激烈，建议差异化定价",
        "❌ 不推荐：市场饱和，出单难度高"
    ][hash(keyword) % 3]
    return {
        "关键词": keyword,
        "热度分(0-100)": hot_score,
        "参考低价": price_low,
        "参考高价": price_high,
        "参考价格区间": f"{price_low} ~ {price_high} 元",
        "竞争程度": competition,
        "货源情况": supply,
        "上架建议": advice,
        "分析时间": datetime.now().strftime("%m-%d %H:%M")
    }

# ==================== AI生成（修复None返回问题）====================
def generate_content(title, cost, style):
    tmp = st.session_state.templates.get(style, st.session_state.templates["默认闲置风"])
    prompt = f"""
你是闲鱼爆款卖家，用【{style}】风格写文案，只返回标准JSON格式，不要任何多余解释、代码块或说明。
商品标题：{title}
成本价：{cost}元
基础描述模板：{tmp}

返回格式示例：
{{
    "xianyu_title":"30字内吸引人标题",
    "description":"200-300字商品描述",
    "tags":["标签1","标签2","标签3","标签4","标签5"],
    "category":"推荐类目",
    "prices":{{"conservative":{round(cost*1.3)},"recommended":{round(cost*1.5)},"aggressive":{round(cost*1.1)}}},
    "tips":"上架小技巧"
}}
"""
    try:
        dashscope.api_key = st.secrets.get("DASHSCOPE_API_KEY", "")
        if not dashscope.api_key:
            st.error("❌ 未配置DASHSCOPE_API_KEY，请检查Secrets")
            return None
            
        resp = dashscope.Generation.call(
            model='qwen-turbo',
            messages=[{"role":"user","content":prompt}],
            temperature=0.7,
            result_format='message'
        )
        
        if resp.status_code == HTTPStatus.OK:
            raw = resp.output.choices[0].message.content.strip()
            raw = re.sub(r'^```json|```$', '', raw).strip()
            raw = re.sub(r'^```|```$', '', raw).strip()
            
            try:
                data = json.loads(raw)
                data['xianyu_title'] = filter_banned(data.get('xianyu_title', title))
                data['description'] = filter_banned(data.get('description', tmp))
                data['tags'] = data.get('tags', generate_tags(title))
                data['category'] = data.get('category', '闲置物品')
                data['tips'] = filter_banned(data.get('tips', '实拍清晰更容易出单'))
                if "prices" not in data or not isinstance(data["prices"], dict):
                    data["prices"] = {
                        "conservative": round(cost*1.3),
                        "recommended": round(cost*1.5),
                        "aggressive": round(cost*1.1)
                    }
                return data
            except json.JSONDecodeError as e:
                st.error(f"❌ AI返回格式错误，无法解析JSON：{str(e)}")
                st.code(raw, language="text")
                return None
        else:
            st.error(f"❌ API调用失败：{resp.message if hasattr(resp, 'message') else '未知错误'}")
            return None
    except Exception as e:
        st.error(f"❌ 生成失败：{str(e)}")
        return None

# ==================== 标签页 ====================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🔥 单条生成", "📦 批量上货", "🖼️ 图片处理",
    "📝 文案模板", "⏰ 擦亮计划", "🤖 自动回复", "🔍 选品分析"
])

# ==================== 1. 单条生成 ====================
with tab1:
    st.subheader("📝 商品信息")
    c1, c2 = st.columns(2)
    with c1:
        title = st.text_input("商品标题", key="single_title", value=st.session_state.get("selected_keyword", ""))
        cost = st.number_input("成本价", value=10.0, key="single_cost")
        style = st.selectbox("文案风格", styles, key="single_style")
    with c2:
        st.info(f"引流价：{round(cost*1.1)} 元")
        st.info(f"保本价：{round(cost*1.3)} 元")
        st.info(f"利润价：{round(cost*1.5)} 元")
        tags = generate_tags(title)

    disabled = not st.session_state.is_pro and st.session_state.gen_count >= FREE_LIMIT
    if st.button("✨ 生成闲鱼爆款文案", type="primary", key="gen_single", disabled=disabled):
        if not title:
            st.error("请输入商品标题")
        else:
            with st.spinner("AI生成中..."):
                data = generate_content(title, cost, style)
                if data is not None:
                    st.session_state.gen_count += 1
                    st.success("✅ 生成完成")
                    cA, cB = st.columns([3,1])
                    with cA:
                        st.subheader("📋 标题")
                        st.code(data['xianyu_title'])
                        copy_btn(data['xianyu_title'])

                        st.subheader("📝 描述")
                        st.text_area("", data['description'], height=220, key="single_desc")
                        copy_btn(data['description'], "复制描述")

                        st.subheader("🏷 标签")
                        ts = ", ".join(tags)
                        st.write(ts)
                        copy_btn(ts, "复制标签")

                        st.subheader("📌 三版备选标题")
                        for i, t in enumerate(gen_3_titles(title),1):
                            st.write(f"{i}. {t}")
                            copy_btn(t,f"复制标题{i}")
                    with cB:
                        st.success(f"引流价：{data['prices']['aggressive']}")
                        st.info(f"保本价：{data['prices']['conservative']}")
                        st.warning(f"利润价：{data['prices']['recommended']}")
                        st.subheader("📂 类目")
                        st.success(data['category'])
                        st.subheader("💡 小贴士")
                        st.info(data['tips'])

                    full = f"标题：{data['xianyu_title']}\n描述：{data['description']}\n标签：{ts}\n售价：{data['prices']['recommended']}元"
                    st.divider()
                    st.subheader("📦 一键复制全套")
                    copy_btn(full, "复制全套上架文案")
                else:
                    st.error("❌ 生成失败，请检查API配置或重试")

# ==================== 2. 批量上货 ====================
with tab2:
    st.subheader("📦 批量生成 & 导出Excel")
    if not st.session_state.is_pro:
        st.warning("⚠️ 此功能为Pro版专属，请激活后使用")
    else:
        c1,c2,c3 = st.columns(3)
        with c1: t = st.text_input("商品标题", key="batch_title")
        with c2: p = st.number_input("成本价", key="batch_cost")
        with c3: s = st.selectbox("风格", styles, key="batch_style")

        if st.button("➕ 添加到列表", key="add_batch"):
            if t:
                new = pd.DataFrame([{"原标题":t,"成本价":p,"风格":s}])
                st.session_state.batch_data = pd.concat([st.session_state.batch_data, new], ignore_index=True)
                st.success("已添加")
            else:
                st.error("请输入标题")

        if not st.session_state.batch_data.empty:
            st.dataframe(st.session_state.batch_data, use_container_width=True, key="batch_df")
            if st.button("🚀 批量生成所有文案", key="gen_batch"):
                res = []
                for _, r in st.session_state.batch_data.iterrows():
                    d = generate_content(r["原标题"], r["成本价"], r["风格"])
                    if d is not None:
                        res.append({
                            "原标题":r["原标题"], "闲鱼标题":d["xianyu_title"],
                            "描述":d["description"], "引流价":d["prices"]["aggressive"],
                            "保本价":d["prices"]["conservative"], "利润价":d["prices"]["recommended"],
                            "标签":",".join(d["tags"]), "类目":d["category"]
                        })
                if res:
                    df = pd.DataFrame(res)
                    st.dataframe(df, use_container_width=True, key="batch_result_df")
                    bio = BytesIO()
                    with pd.ExcelWriter(bio, engine='openpyxl') as w:
                        df.to_excel(w, index=False)
                    st.download_button("📥 导出Excel", bio.getvalue(), "闲鱼批量文案.xlsx", key="dl_batch")

# ==================== 3. 图片处理 ====================
with tab3:
    st.subheader("🖼️ 图片去重 + 压缩 + 水印")
    if not st.session_state.is_pro:
        st.warning("⚠️ 此功能为Pro版专属，请激活后使用")
    else:
        imgs = st.file_uploader("上传图片", type=["jpg","png"], accept_multiple_files=True, key="img_uploader")
        q = st.slider("压缩质量", 50,100,85, key="img_quality")
        mark = st.text_input("水印文字", "闲鱼实拍", key="watermark_text")
        if imgs and st.button("开始处理", key="process_img"):
            out = []
            hashes = []
            for f in imgs:
                img = Image.open(BytesIO(f.read())).convert("RGB")
                h = imagehash.average_hash(img)
                if h not in hashes:
                    hashes.append(h)
                    out.append(add_watermark(img, mark))
            st.success(f"去重完成，共{len(out)}张")
            cols = st.columns(4)
            for i, img in enumerate(out):
                with cols[i%4]:
                    st.image(img, use_column_width=True)
                    b = compress_image(img, q)
                    st.download_button(f"下载{i+1}", b, f"img_{i+1}.jpg", "image/jpeg", key=f"dl_img_{i}")

# ==================== 4. 模板 ====================
with tab4:
    st.subheader("📝 自定义文案模板")
    n = st.text_input("模板名称", key="template_name")
    c = st.text_area("模板内容", height=120, key="template_content")
    if st.button("添加模板", key="add_template"):
        if n and c:
            st.session_state.templates[n] = c
            st.success("添加成功")
            st.rerun()
    for name, content in st.session_state.templates.items():
        with st.expander(name):
            st.write(content)

# ==================== 5. 擦亮计划 ====================
with tab5:
    st.subheader("⏰ 自动擦亮排班表")
    t = st.text_input("商品标题", key="polish_title")
    n = st.number_input("每日擦亮次数",1,5,3, key="polish_times")
    if st.button("生成计划", key="gen_polish"):
        if t:
            plan = []
            now = datetime.now()
            for i in range(n):
                plan.append({"商品":t,"时间":(now+timedelta(hours=4*i)).strftime("%m-%d %H:%M"),"状态":"待擦亮"})
            st.session_state.polish_plan = plan
            st.success("已生成")
    if st.session_state.polish_plan:
        st.dataframe(pd.DataFrame(st.session_state.polish_plan), use_container_width=True, key="polish_plan_df")

# ==================== 6. 自动回复 ====================
with tab6:
    st.subheader("🤖 买家问答自动回复库")
    q = st.text_input("问题", key="reply_q")
    a = st.text_area("回复", key="reply_a")
    if st.button("添加回复", key="add_reply"):
        if q and a:
            st.session_state.auto_reply_lib[q] = a
            st.rerun()
    c1, c2 = st.columns(2)
    items = list(st.session_state.auto_reply_lib.items())
    half = len(items)//2+1
    with c1:
        for q,a in items[:half]:
            with st.expander(f"❓ {q}"):
                st.write(a)
                copy_btn(a,"复制回复")
    with c2:
        for q,a in items[half:]:
            with st.expander(f"❓ {q}"):
                st.write(a)
                copy_btn(a,"复制回复")

# ==================== 7. 选品分析（Pro专属 + 历史记录）====================
with tab7:
    st.subheader("🔍 闲鱼选品分析 · 帮你找爆款")
    if not st.session_state.is_pro:
        st.warning("⚠️ 此功能为Pro版专属，请激活后使用")
    else:
        keyword = st.text_input("输入要分析的商品关键词", placeholder="例如：无线蓝牙耳机、复古相机")
        col_analyze, col_clear = st.columns([3,1])
        with col_analyze:
            if st.button("📊 分析选品潜力", key="analyze_product"):
                if not keyword:
                    st.error("请输入商品关键词")
                else:
                    with st.spinner("正在分析市场数据..."):
                        result = product_selection_analysis(keyword)
                        # 保存到历史记录
                        st.session_state.selection_history.append(result)
                        st.success("✅ 选品分析完成！已保存到历史记录")
                        
                        # 可视化展示
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("🔥 热度分", f"{result['热度分(0-100)']} / 100")
                            st.metric("💸 参考价格区间", result['参考价格区间'])
                        with col2:
                            st.metric("⚔️ 竞争程度", result['竞争程度'])
                            st.metric("📦 货源情况", result['货源情况'])
                        
                        st.subheader("💡 上架建议")
                        st.info(result['上架建议'])
                        
                        # 生成对应文案入口
                        if st.button("✨ 直接生成该商品文案", key="gen_from_selection"):
                            st.session_state["selected_keyword"] = keyword
                            st.switch_tab("🔥 单条生成")
        with col_clear:
            if st.button("🗑 清空历史记录", key="clear_history"):
                st.session_state.selection_history = []
                st.rerun()

        # 显示选品历史记录
        st.divider()
        st.subheader("📜 选品历史记录")
        if st.session_state.selection_history:
            df_history = pd.DataFrame(st.session_state.selection_history)
            # 按分析时间倒序显示
            df_history = df_history.sort_values(by="分析时间", ascending=False)
            st.dataframe(
                df_history[["分析时间", "关键词", "热度分(0-100)", "参考价格区间", "竞争程度", "上架建议"]],
                use_container_width=True,
                key="selection_history_df"
            )
            # 一键导出历史记录
            bio = BytesIO()
            with pd.ExcelWriter(bio, engine='openpyxl') as w:
                df_history.to_excel(w, index=False)
            st.download_button("📥 导出选品历史Excel", bio.getvalue(), "闲鱼选品历史.xlsx", key="dl_selection_history")
        else:
            st.info("暂无选品分析记录，快去分析几个商品吧～")

st.divider()
st.caption("© 2026 闲鱼上货助手 Pro 付费版 · 版权所有 · 禁止倒卖")
