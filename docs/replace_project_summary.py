from pathlib import Path

from docx import Document


PATH = Path("docs/internet_plus_business_plan_standard.docx")

SUMMARY = [
    "低空经济正在从政策热点进入真实场景验证阶段，校园、园区、景区等相对封闭场景成为无人配送和绿色物流试点的重要入口。但在实际落地中，客户面临的不是“要不要关注低空经济”，而是“自己的场景到底能不能做、该投多少设备、能省多少成本、如何保障安全、绿色价值如何量化”。这些问题如果没有清晰测算，低空配送很容易停留在展示层面，难以形成可持续运营。",
    "“空地绿配智控平台”正是面向这一痛点提出的低空绿色物流决策与调度系统。项目以 UAV 无人机与 AGV 无人车协同配送为核心，通过场景建模、订单导入、候选中继点筛选、路径优化、能耗测算和运营看板，帮助客户在真实投入硬件之前先完成数字化评估，在试点运行过程中持续优化路线、设备利用率和绿色运营指标。",
    "项目的核心思路是用 AGV 承担移动中继、回收补能和地面支撑，用 UAV 完成末端快速触达，避免纯无人机方案续航短、频繁返航、回收难的问题，也弥补纯无人车方案受地面路网限制、绕行较多的短板。通过空地协同调度，平台把“能不能飞”进一步转化为“怎么飞更划算、在哪里起降更安全、怎样运行更节能”。",
    "技术上，项目以 ALNS 自适应大邻域搜索算法为主要优化方法，结合候选中继点生成、时间窗约束、设备续航约束和能耗模型，输出可比较的多套配送方案。现有仿真结果显示，在小型验证场景中，协同中继策略相较基线直送能够提升任务完成率和准时率，单任务能耗由 61.26 降至 49.70，下降约 18.9%；单位距离能耗由 0.226 降至 0.187，下降约 17.3%。这说明项目已经具备从算法原型走向场景化应用的基础。",
    "商业模式上，项目采取轻资产切入路径：早期提供低空配送仿真评估和场景规划服务，帮助校园、园区、景区客户判断试点可行性；中期通过平台年度授权、场景建模、系统交付和硬件厂商联合方案形成收入；后期在订单规模稳定后，拓展按单 SaaS 调度服务、绿色运营报告和数据增值服务。以日均 3000 单校园小件配送场景测算，平台授权、仿真评估与按单服务叠加后，单校园首年收入具备达到 20 万元以上的空间。",
    "项目首批目标客户包括高校后勤集团、大学科技园、产业园运营方、景区管理方、低空经济示范区以及无人机、无人车硬件厂商。项目将优先从湖南科技大学校园样板做起，完成快递驿站、宿舍区、教学区、食堂等高频点位的数字沙盘和策略验证，再向湘潭及周边园区、景区复制，形成“校园样板—园区验证—区域合作—平台服务”的推进路径。",
    "团队来自湖南科技大学计算机科学与工程学院，在舒红梅老师指导下推进研发与商业化设计。团队已完成仿真系统、策略对比、商业计划书和路演材料的多轮迭代，具备算法开发、系统实现、数据分析和项目表达的专业基础。团队成员以大一、大二学生为主，虽然经验仍需积累，但成长周期长、执行速度快，适合持续参加竞赛、申请软著、推进校内试点并吸纳更多技术与商业成员。",
    "未来三年，项目计划完成 ALNS 主算法优化、候选中继点引擎、动态回退机制、校园样板系统和 5 至 10 个校园/园区/景区试点；未来五年，项目希望发展为低空绿色物流试点前的基础决策工具和空地协同调度平台，让低空配送从概念展示走向可计算、可验证、可复制的真实运营。",
]


doc = Document(PATH)
paragraphs = doc.paragraphs

summary_heading = None
next_heading = None
for i, paragraph in enumerate(paragraphs):
    if paragraph.style.name == "Heading 1" and paragraph.text.strip() == "项目摘要":
        summary_heading = paragraph
        for later in paragraphs[i + 1 :]:
            if later.style.name == "Heading 1":
                next_heading = later
                break
        break

if summary_heading is None or next_heading is None:
    raise RuntimeError("Could not locate project summary section")

current = summary_heading._element.getnext()
while current is not next_heading._element:
    nxt = current.getnext()
    current.getparent().remove(current)
    current = nxt

for text in SUMMARY:
    paragraph = next_heading.insert_paragraph_before(text)
    paragraph.style = "Normal"

doc.save(PATH)
print(PATH)
