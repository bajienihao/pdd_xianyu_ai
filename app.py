def product_selection_analysis(keyword):
    """
    方案一：基于品类模板库的二手价格模拟（贴近闲鱼真实行情，合规安全）
    逻辑：按品类匹配全新价区间 → 乘以二手系数 → 生成参考二手价
    """
    hot_score = hash(keyword) % 100  # 模拟热度分
    competition = ["低", "中", "高"][hash(keyword) % 3]
    supply = ["充足", "一般", "稀缺"][hash(keyword) % 3]

    keyword_lower = keyword.lower()
    price_low = 0.0
    price_high = 0.0

    # ==================== 品类价格模板库 ====================
    # 手机/数码类（二手占比高，价格区间大）
    if any(w in keyword_lower for w in ["手机", "iphone", "苹果", "华为", "小米", "vivo", "oppo", "荣耀", "一加"]):
        new_min, new_max = 2000, 8000    # 全新机参考价
        used_coef_min, used_coef_max = 0.2, 0.6  # 二手折扣系数
    # 耳机/音频类
    elif any(w in keyword_lower for w in ["耳机", "蓝牙", "airpods", "音箱", "音响", "降噪"]):
        new_min, new_max = 100, 1000
        used_coef_min, used_coef_max = 0.3, 0.7
    # 相机/摄影类
    elif any(w in keyword_lower for w in ["相机", "拍立得", "镜头", "ccd", "微单", "单反"]):
        new_min, new_max = 500, 5000
        used_coef_min, used_coef_max = 0.25, 0.65
    # 家电/大件类
    elif any(w in keyword_lower for w in ["家电", "冰箱", "洗衣机", "电视", "空调", "热水器"]):
        new_min, new_max = 1000, 5000
        used_coef_min, used_coef_max = 0.2, 0.5
    # 服饰/箱包类
    elif any(w in keyword_lower for w in ["衣服", "鞋", "包包", "服饰", "卫衣", "裤子", "裙子"]):
        new_min, new_max = 50, 500
        used_coef_min, used_coef_max = 0.1, 0.4
    # 书籍/文具类
    elif any(w in keyword_lower for w in ["书", "绘本", "教材", "杂志", "文具", "笔记本"]):
        new_min, new_max = 20, 200
        used_coef_min, used_coef_max = 0.15, 0.5
    # 美妆/护肤类
    elif any(w in keyword_lower for w in ["口红", "粉底", "护肤", "面膜", "香水", "彩妆"]):
        new_min, new_max = 50, 500
        used_coef_min, used_coef_max = 0.2, 0.6
    # 母婴/儿童类
    elif any(w in keyword_lower for w in ["母婴", "奶粉", "玩具", "童装", "婴儿车"]):
        new_min, new_max = 50, 1000
        used_coef_min, used_coef_max = 0.2, 0.5
    # 其他通用闲置类
    else:
        new_min, new_max = 20, 300
        used_coef_min, used_coef_max = 0.2, 0.7

    # ==================== 计算二手价格区间 ====================
    # 用hash做随机，保证同一关键词每次分析价格一致
    rand_base = hash(keyword)
    new_price = new_min + (rand_base % (new_max - new_min))
    used_coef = used_coef_min + (rand_base % int((used_coef_max - used_coef_min)*100))/100

    price_low = round(new_price * used_coef_min, 2)
    price_high = round(new_price * used_coef_max, 2)

    # ==================== 上架建议逻辑 ====================
    if hot_score >= 70 and competition == "低":
        advice = "✅ 强烈推荐上架：需求旺盛，竞争小，利润空间大"
    elif hot_score >= 50 and competition in ["低", "中"]:
        advice = "⚠️ 推荐上架：需求尚可，竞争可控，适合测试"
    elif hot_score < 30 or competition == "高":
        advice = "❌ 不推荐上架：需求低迷或竞争激烈，出单难度高"
    else:
        advice = "🔍 可尝试上架：需求一般，建议小批量试水"

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
