from pathlib import Path
from html import escape

ROOT = Path(__file__).parent
slides = [
('討論目標', 'DiskANN SSD-side computation', '平台能力與效能量測問題', [
('應用目標', '評估在 SSD 內部完成 distance computation 的資料供應、搬移與計算成本。'),
('本次希望確認', 'Internal read 的併發能力、iDMA 端到端延遲、DSP kernel 成本，以及可實現的 pipeline。'),
('後續用途', '將確認後的量測與限制納入模擬器，比較 batch size、buffer 配置與重疊執行方案。')],
'原始依據：問題統整 (2).pdf；規格數字依原文件轉述，尚待廠商確認量測條件。'),
('共同情境', '先確認單一 iteration 的工作流程', '目前假設 W = 4，每輪同時 expand 4 個 vectors', [
('01｜資料供應', 'C3 選擇 frontier → Internal read 至 DBUF → C3 解析 node／取得所需 PQ 資料。'),
('02｜距離計算', 'PQ codes：DBUF → DLM → DSP 計算 distance → 結果：DLM → DBUF。'),
('03｜流程確認', '上述工作分配是否符合平台？哪些階段可在單輪內重疊？跨輪重疊須考慮下一輪 frontier 對本輪結果的依賴。')],
'W 是 expand 數量；讀取 outstanding 與 DSP batch size 需另外定義，不預設三者相同。'),
('問題 01', 'Internal read：NAND → DBUF', '希望取得不含 host 與 PCIe 傳輸的資料供應成本', [
('已知數據', '文件列出 32 × 4K：1.022 GB/s；128 × 4K：2.145 GB/s。'),
('提交與併發', '32／128 筆 requests 是逐筆等待完成，還是維持多筆 outstanding？實際 outstanding 是多少？'),
('平台能力', 'C3 是否支援非同步提交？最大 outstanding 是多少？'),
('希望取得', '原測試的提交方式、outstanding 與計時邊界；補充討論：W = 4 情境下的整批完成時間。')],
'設計用途：評估低併發資料供應成本，判斷提高 outstanding 的效益。'),
('問題 02', 'iDMA：DBUF ⇄ DLM', '希望以端到端時間估算每批資料搬移成本', [
('既有數據的範圍', '4K／48K throughput 是否涵蓋提交、設定、搬移及完成通知，直到目的端資料可供下一階段使用？'),
('希望取得的時間', '分別提供 T_DMA,in 與 T_DMA,out；可用「固定開銷 + 資料量／有效頻寬」形式估算。'),
('實際 workload', '每批 64 個 PQ candidates：輸入 2 KiB PQ codes，輸出 256 B FP32 distances。希望補充這兩種大小的量測。'),
('重疊情境', '既有數據是單獨搬移，還是 DSP 同時計算？若可重疊，搬移與計算各自是否受影響？')],
'設計用途：比較小 batch 的啟動成本，決定 batching 與雙 buffer 是否有收益。'),
('問題 03', 'DSP：PQ ADC kernel', 'LUT 與 PQ codes 已在 DLM，結果寫回 DLM', [
('資料配置', '每 candidate：32 B，含 32 個 uint8 indices（0–255）。32 個 subquantizers，每個 256 個 centroids。'),
('運算定義', '每 query 共用 32 × 256 × FP32 = 32 KiB LUT。每 candidate 查表取得 32 個 FP32 distances，加總並輸出 1 個 FP32（4 B）。'),
('希望量測', 'Batch = 1、16、64、128、512：整批執行時間或 total cycles。若需縮減，優先 1 與 128。'),
('兩種時間分開提供', '① Kernel：DLM 讀取、查表、累加、結果寫回。② 端到端：C3 啟動工作至 C3 確認結果可用。')],
'50 GFLOPS 規格不足以直接推算查表與 DLM 存取成本；本頁量測不包含 LUT／codes 搬入 DLM。'),
('問題 04', 'DSP：Full-vector distance', 'Query 與 candidate vectors 已在 DLM，結果寫回 DLM', [
('資料配置', 'Query：128 維 FP32 = 512 B，同批共用。每 candidate：128 維 FP32 = 512 B。'),
('運算定義', 'Squared L2 distance：Σ(qᵢ − xᵢ)²。每 candidate 輸出 1 個 FP32 distance（4 B）。'),
('希望量測', 'Batch = 1、16、64：整批執行時間或 total cycles；包含 DLM 資料讀取、計算及結果寫回。'),
('提交與完成成本', '另提供 C3 啟動 DSP 工作至 C3 確認結果可用的端到端時間。')],
'設計用途：與 iDMA 成本比較，評估 full-vector distance 階段的瓶頸。'),
('問題 05', 'Pipeline：哪些階段可以同時進行？', '以下為待確認的候選情境，不代表平台已支援', [
('候選 A｜雙向 iDMA 互斥', 'DBUF → DLM 與 DLM → DBUF 共用搬移時段；仍需確認是否可與 DSP 計算重疊。'),
('候選 B｜雙向 iDMA 並行', '輸入與輸出搬移可同時進行；需確認能否再與 DSP 計算重疊，以及共享資源限制。'),
('Ping-pong 配置', '128 KB DLM 放置 32 KiB LUT，預留結果與工作空間後，是否可配置兩組輸入 buffer？'),
('希望確認', 'DSP 計算一組時，iDMA 能否搬入另一組？有哪些 memory bank、對齊、buffer ownership 或同步限制？')],
'請協助修正可行的時序；DLM 容量單位與實際可用空間也需確認。'),
('補充討論｜新增', '完整 query 還需要哪些成本？', '本頁為新增議題，可依會議時間選擇討論', [
('C3 工作', 'Node parse、visited／去重與 frontier 更新由哪些資源執行？能否提供時間估算或量測方式？'),
('LUT 生命週期', '每 query 的 LUT 如何建立、載入？能否跨 batches 常駐 DLM？多 query 切換有何限制？'),
('資料可用時機', 'Internal read 能否逐筆通知完成？DBUF 資料可否直接交給 iDMA，是否需要額外 copy？'),
('共享資源', 'Internal read、iDMA、DSP 同時工作時，共用哪些 bus／memory？最小讀取單位與對齊有何限制？')],
'目的：補齊模型邊界，避免只計算 NAND、DMA 與 DSP 而漏掉控制與準備成本。'),
('確認事項', '希望本次會議取得的共識', '可先提供既有量測；未量測項目可先給估算與適用條件', [
('01｜讀取與搬移', 'Internal read 的實際 outstanding／最大支援值；iDMA 的計時範圍與實際小資料量成本。'),
('02｜DSP', 'PQ ADC 與 squared L2 的 batch 執行成本；區分 kernel 與 C3 端到端時間。'),
('03｜可行 pipeline', '確認雙向 DMA、DMA／compute overlap，以及 DLM ping-pong 的限制。'),
('04｜後續分工', '共同選定優先量測項目、負責窗口與預計回覆時間；我們據此更新模擬參數與比較方案。')],
'建議回覆欄位：測試條件／batch 或資料量／計時起訖／結果與單位／實測或估算／限制。'),
]

css = '''
*{box-sizing:border-box} body{margin:0;background:#101b2d;color:#18283b;font-family:"Noto Sans CJK TC","Microsoft JhengHei",sans-serif}
.slide{width:1280px;height:720px;padding:45px 62px 42px;background:#f6f8fb;position:relative;margin:24px auto;page-break-after:always;overflow:hidden}
.tag{font-size:18px;color:#117b83;font-weight:700;letter-spacing:2px} h1{font-size:38px;line-height:1.25;margin:14px 0 10px} .sub{font-size:21px;color:#59687b;margin:0 0 25px}
.cards{display:grid;gap:13px}.card{background:white;border-left:5px solid #16949c;border-radius:5px;padding:13px 20px;display:grid;grid-template-columns:210px 1fr;gap:18px;align-items:start}
h2{font-size:21px;margin:0;line-height:1.55} .card p{font-size:21px;line-height:1.55;margin:0}.foot{position:absolute;bottom:27px;left:62px;right:95px;color:#627184;font-size:14px;line-height:1.5}.num{position:absolute;bottom:29px;right:36px;color:#117b83;font-size:16px}
nav{position:fixed;bottom:10px;right:16px;z-index:5;display:flex;gap:7px}button{padding:8px 14px;border:0;border-radius:5px;background:#16949c;color:white;cursor:pointer}
body.present .slide{display:none;margin:0}body.present .slide.active{display:block;position:absolute;top:50%;left:50%;transform:translate(-50%,-50%) scale(var(--scale,1))}
@page{size:1280px 720px;margin:0}@media print{body{background:white} .slide,body.present .slide,body.present .slide.active{display:block;position:relative;margin:0;transform:none;top:auto;left:auto;break-after:page}nav{display:none}}
'''
html = ['<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>DiskANN 平台問題討論</title><style>'+css+'</style><body>']
md = ['# DiskANN SSD-side computation：平台問題討論\n\n來源：使用者提供的《問題統整 (2).pdf》。第 8 頁為新增補充討論；其他頁面為整理與會議用語改寫。\n']
for i,(tag,title,sub,cards,foot) in enumerate(slides,1):
    html.append(f'<section class="slide"><div class="tag">{escape(tag)}</div><h1>{escape(title)}</h1><p class="sub">{escape(sub)}</p><div class="cards">')
    md.append(f'\n## {i}. {title}\n\n{sub}\n')
    for head,body in cards:
        html.append(f'<div class="card"><h2>{escape(head)}</h2><p>{escape(body)}</p></div>')
        md.append(f'\n- **{head}：**{body}\n')
    html.append(f'</div><div class="foot">{escape(foot)}</div><div class="num">{i:02d} / {len(slides):02d}</div></section>')
    md.append(f'\n備註：{foot}\n')
html.append('''<nav><button onclick="toggle()">播放／總覽</button><button onclick="move(-1)">上一頁</button><button onclick="move(1)">下一頁</button><button onclick="window.print()">列印 PDF</button></nav>
<script>let current=0;const slides=[...document.querySelectorAll('.slide')];function fit(){document.documentElement.style.setProperty('--scale',Math.min(innerWidth/1280,innerHeight/720))}function show(){slides.forEach((s,i)=>s.classList.toggle('active',i===current));if(!document.body.classList.contains('present'))slides[current].scrollIntoView({behavior:'smooth'})}function move(d){current=Math.max(0,Math.min(slides.length-1,current+d));show()}function toggle(){document.body.classList.toggle('present');fit();show()}onresize=fit;onkeydown=e=>{if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();move(1)}if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();move(-1)}if(e.key==='Escape'){document.body.classList.remove('present');show()}};fit();show();</script></body></html>''')
(ROOT/'問題簡報.html').write_text('\n'.join(html),encoding='utf-8')
(ROOT/'問題簡報_逐頁文字.md').write_text('\n'.join(md),encoding='utf-8')
print(f'Created {len(slides)} slides in {ROOT}')
