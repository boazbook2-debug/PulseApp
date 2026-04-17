import os
import streamlit as st
from groq import Groq
from auth import get_auth_url, exchange_code_for_tokens, get_user_info
from database import (
    save_user, get_oura_data, save_oura_data, get_user_by_email,
    get_user_baselines, get_history_stats,
    get_user_access, set_paid,
)
from oura_fetcher import fetch_all_oura_data
from trend_detector import detect_trends
from pubmed import search_pubmed, get_evidence_label, DEFAULT_QUERY
from design import (
    apply_design_system, get_glow_color,
    get_evidence_shadow, get_slider_shadow, get_conf_color, get_conf_shadow,
)
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Pulse", layout="wide", initial_sidebar_state="collapsed")

# ── Helpers ────────────────────────────────────────────────────────────────────
def fmt_dur(s):
    if not s: return "—"
    h, m = divmod(int(s) // 60, 60)
    return f"{h}h {m}m" if h else f"{m}m"

def fmt(v, unit="", d=0):
    if v is None: return "—"
    return f"{v:.{d}f}{unit}" if d else f"{int(v)}{unit}"


@st.cache_data(ttl=86400)
def get_topic_summary(headline: str, description: str, query: str, spec_val: int) -> str:
    """Call Claude to generate a plain-English research summary. Cached 24h."""
    try:
        ev_type, _ = get_evidence_label(spec_val)
        client = Groq(api_key=os.environ["GROQ_API_KEY"])
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=700,
            messages=[{
                "role": "user",
                "content": (
                    f'Write exactly 3 paragraphs summarising what peer-reviewed research says '
                    f'about this health topic: "{headline}".\n\n'
                    f'Context: {description}\n'
                    f'Evidence level: {ev_type}\n\n'
                    f'Rules:\n'
                    f'- Plain language, no jargon, no medical claims\n'
                    f'- Each paragraph 3-4 sentences\n'
                    f'- Authoritative but conversational\n'
                    f'- Focus on what research shows, not advice\n'
                    f'- Return only the 3 paragraphs separated by a blank line. No headings, no markdown.'
                )
            }]
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return (
            "Research on this topic has grown significantly over the past decade, with multiple "
            "study designs converging on consistent findings. The evidence base spans laboratory "
            "studies, observational cohorts, and intervention trials.\n\n"
            "The core mechanisms are increasingly well understood at a physiological level. "
            "Researchers have identified several pathways through which these effects operate, "
            "and the findings have been replicated across diverse populations.\n\n"
            "The clinical and practical implications remain an active area of investigation. "
            "While the broad direction of the evidence is clear, optimal parameters and "
            "individual variation are still being characterised in ongoing research."
        )


def get_paper_score(article: dict, spec_val: int) -> int:
    """Derive an evidence score (0-100) from study type + recency."""
    base = {(0,2): 93, (2,4): 83, (4,6): 69, (6,8): 55, (8,11): 41}
    score = 50
    for (lo, hi), s in base.items():
        if lo <= spec_val < hi:
            score = s
            break
    try:
        year = int(str(article.get("date", "2019"))[:4])
        if year >= 2023:   score = min(100, score + 8)
        elif year >= 2021: score = min(100, score + 4)
    except Exception:
        pass
    return score


def score_color(s: int) -> str:
    if s >= 75: return "#00C896"
    if s >= 45: return "#F0C040"
    return "#E05050"


# ── Research topic catalogue — 10 zones × 10 topics ──────────────────────────
# Zone 0 = pure clinical evidence (RCTs/meta-analyses)
# Zone 9 = highly speculative / frontier science
TOPIC_ZONES: dict[int, list] = {

    0: [  # ── Rigorous clinical evidence ──────────────────────────────────────
        {"slug": "z0-exercise-mortality", "headline": "Regular exercise reduces all-cause mortality by 30–35%",
         "description": "Decades of RCTs and large meta-analyses establish aerobic exercise as the most evidence-backed longevity intervention.",
         "query": "aerobic exercise all-cause mortality RCT meta-analysis", "papers": 34, "indirect": 71, "relevancy": 98},
        {"slug": "z0-sleep-duration-mortality", "headline": "7–9 hours of sleep minimises all-cause mortality risk",
         "description": "Cohort studies across millions of adults consistently show a U-shaped relationship between sleep duration and death from any cause.",
         "query": "sleep duration all-cause mortality cohort study", "papers": 29, "indirect": 62, "relevancy": 96},
        {"slug": "z0-smoking-cessation", "headline": "Quitting smoking adds nearly a decade to life expectancy",
         "description": "Population studies confirm that smoking cessation at any age substantially reduces cardiovascular, pulmonary, and cancer mortality.",
         "query": "smoking cessation longevity cardiovascular mortality", "papers": 41, "indirect": 88, "relevancy": 99},
        {"slug": "z0-mediterranean-diet", "headline": "Mediterranean diet reduces cardiovascular events by 30%",
         "description": "The PREDIMED RCT and subsequent replications show robust reductions in major cardiac events from a Mediterranean dietary pattern.",
         "query": "mediterranean diet cardiovascular events RCT PREDIMED", "papers": 27, "indirect": 55, "relevancy": 94},
        {"slug": "z0-blood-pressure-stroke", "headline": "Blood pressure control is the primary modifiable stroke risk factor",
         "description": "Every 10 mmHg reduction in systolic BP reduces stroke risk by approximately 27% across age groups.",
         "query": "blood pressure control stroke prevention RCT", "papers": 38, "indirect": 79, "relevancy": 97},
        {"slug": "z0-vo2max-longevity", "headline": "VO₂ max is the strongest single predictor of lifespan",
         "description": "Cardiorespiratory fitness outperforms smoking, BMI, and blood pressure as a mortality predictor — each fitness tier cuts risk ~15%.",
         "query": "VO2 max cardiorespiratory fitness longevity all-cause mortality", "papers": 22, "indirect": 48, "relevancy": 94},
        {"slug": "z0-steps-mortality", "headline": "Each 1,000 extra steps/day cuts mortality risk by 10–15%",
         "description": "Multi-country cohort data consistently show an inverse dose-response between daily step count and all-cause and cardiovascular death.",
         "query": "daily steps all-cause mortality cohort dose response", "papers": 18, "indirect": 37, "relevancy": 93},
        {"slug": "z0-alcohol-liver", "headline": "Alcohol abstinence reverses early-stage liver fibrosis",
         "description": "Clinical trials demonstrate histological improvement in liver fibrosis within months of complete alcohol cessation.",
         "query": "alcohol abstinence liver fibrosis reversal clinical trial", "papers": 16, "indirect": 31, "relevancy": 89},
        {"slug": "z0-physical-activity-depression", "headline": "Exercise is as effective as antidepressants for mild–moderate depression",
         "description": "Network meta-analyses of hundreds of RCTs rank structured exercise alongside pharmacotherapy for treating clinical depression.",
         "query": "exercise depression antidepressant RCT meta-analysis", "papers": 31, "indirect": 64, "relevancy": 91},
        {"slug": "z0-dietary-fiber-mortality", "headline": "High dietary fibre intake reduces mortality from multiple causes",
         "description": "Meta-analyses confirm that each 8g/day increment in fibre intake reduces all-cause, cardiovascular, and colorectal cancer mortality.",
         "query": "dietary fiber all-cause mortality cardiovascular meta-analysis", "papers": 24, "indirect": 50, "relevancy": 92},
    ],

    1: [  # ── Strong cohort evidence ────────────────────────────────────────────
        {"slug": "z1-hrv-sleep", "headline": "HRV and sleep quality are tightly coupled",
         "description": "Autonomic recovery during sleep directly predicts next-day heart rate variability and readiness scores.",
         "query": "heart rate variability sleep quality autonomic", "papers": 24, "indirect": 51, "relevancy": 91},
        {"slug": "z1-deep-sleep-memory", "headline": "Deep sleep consolidates memory and clears metabolic waste",
         "description": "Slow-wave sleep replays learned information and flushes neurotoxic waste via the glymphatic system.",
         "query": "slow wave sleep memory consolidation glymphatic", "papers": 19, "indirect": 40, "relevancy": 88},
        {"slug": "z1-alcohol-sleep-hrv", "headline": "Alcohol fragments sleep architecture and suppresses HRV",
         "description": "Even moderate alcohol before sleep disrupts staging, elevates resting HR, and suppresses REM in the first half of the night.",
         "query": "alcohol sleep architecture REM suppression HRV", "papers": 17, "indirect": 33, "relevancy": 89},
        {"slug": "z1-resting-hr-fitness", "headline": "Resting heart rate is a reliable marker of aerobic fitness",
         "description": "Lower resting HR reflects stronger cardiac output and autonomic balance, reducing long-term cardiovascular risk.",
         "query": "resting heart rate cardiovascular fitness recovery", "papers": 21, "indirect": 43, "relevancy": 85},
        {"slug": "z1-spo2-apnea", "headline": "Nocturnal SpO2 dips are the hallmark of sleep apnea",
         "description": "Repeated oxygen desaturation events during sleep carry significant cardiovascular and metabolic consequences.",
         "query": "nocturnal oxygen saturation sleep apnea SpO2", "papers": 19, "indirect": 38, "relevancy": 82},
        {"slug": "z1-stress-hrv", "headline": "Psychological stress acutely suppresses HRV within hours",
         "description": "Acute and chronic stressors reduce vagal tone, measurably lowering HRV and impairing recovery capacity.",
         "query": "psychological stress heart rate variability vagal tone", "papers": 16, "indirect": 31, "relevancy": 85},
        {"slug": "z1-circadian-metabolic", "headline": "Circadian misalignment elevates metabolic and cognitive risk",
         "description": "Shift work and irregular sleep schedules disrupt the body's master clock, elevating insulin resistance and impairing cognition.",
         "query": "circadian rhythm misalignment metabolic cognitive shift work", "papers": 14, "indirect": 28, "relevancy": 79},
        {"slug": "z1-blue-light-melatonin", "headline": "Evening blue light suppresses melatonin and delays sleep onset",
         "description": "Screen-emitted blue wavelengths inhibit melatonin synthesis, shifting circadian phase and reducing slow-wave sleep by up to 20%.",
         "query": "blue light melatonin suppression sleep onset circadian", "papers": 13, "indirect": 26, "relevancy": 81},
        {"slug": "z1-social-isolation-mortality", "headline": "Social isolation is as lethal as smoking 15 cigarettes a day",
         "description": "Large longitudinal studies find that chronic loneliness independently predicts premature death across all demographics.",
         "query": "social isolation loneliness all-cause mortality cohort", "papers": 20, "indirect": 42, "relevancy": 87},
        {"slug": "z1-sedentary-cardiometabolic", "headline": "Sitting more than 10 hours daily doubles cardiometabolic risk",
         "description": "Objective accelerometer data from large cohorts show prolonged unbroken sitting independently predicts metabolic syndrome.",
         "query": "sedentary time cardiometabolic risk accelerometer cohort", "papers": 15, "indirect": 30, "relevancy": 83},
    ],

    2: [  # ── Well-established mechanisms ───────────────────────────────────────
        {"slug": "z2-sleep-debt-cognition", "headline": "Sleep debt causes measurable cognitive deficits within 24 hours",
         "description": "Even a single night of restriction impairs working memory, reaction time, and decision quality in controlled lab conditions.",
         "query": "sleep deprivation cognitive performance working memory", "papers": 18, "indirect": 38, "relevancy": 87},
        {"slug": "z2-zone2-fat-oxidation", "headline": "Zone 2 training is the most efficient stimulus for fat oxidation",
         "description": "Exercise at lactate threshold 1 maximises fat as fuel and drives mitochondrial density without accumulated fatigue.",
         "query": "zone 2 training fat oxidation mitochondrial density", "papers": 14, "indirect": 29, "relevancy": 78},
        {"slug": "z2-cold-inflammation", "headline": "Cold water immersion accelerates exercise recovery via inflammation control",
         "description": "Post-exercise cold immersion reduces DOMS and inflammatory markers, though timing relative to training type matters.",
         "query": "cold water immersion exercise recovery inflammation", "papers": 16, "indirect": 33, "relevancy": 74},
        {"slug": "z2-magnesium-sleep", "headline": "Magnesium supplementation improves sleep quality in deficient adults",
         "description": "Oral magnesium increases slow-wave sleep duration and reduces cortisol in adults with suboptimal dietary magnesium.",
         "query": "magnesium supplementation sleep quality cortisol", "papers": 11, "indirect": 22, "relevancy": 71},
        {"slug": "z2-sauna-cardiovascular", "headline": "Regular sauna use mimics moderate-intensity cardiovascular exercise",
         "description": "Finnish cohort data and mechanistic studies show 4–7 weekly sauna sessions reduce cardiovascular event risk by up to 50%.",
         "query": "sauna use cardiovascular health Finnish cohort", "papers": 13, "indirect": 27, "relevancy": 76},
        {"slug": "z2-time-restricted-eating", "headline": "Time-restricted eating improves insulin sensitivity independent of calories",
         "description": "Aligning food intake with daylight hours improves glucose regulation and metabolic flexibility without caloric restriction.",
         "query": "time restricted eating insulin sensitivity metabolic", "papers": 12, "indirect": 24, "relevancy": 69},
        {"slug": "z2-mindfulness-cortisol", "headline": "Mindfulness-based stress reduction measurably lowers cortisol",
         "description": "Eight-week MBSR programmes consistently reduce salivary and urinary cortisol markers in stressed working adults.",
         "query": "mindfulness MBSR cortisol stress reduction RCT", "papers": 15, "indirect": 31, "relevancy": 72},
        {"slug": "z2-strength-bone-density", "headline": "Resistance training is the primary intervention for bone density preservation",
         "description": "Weight-bearing and resistance exercise create the mechanical load required to stimulate osteoblast activity and halt age-related bone loss.",
         "query": "resistance training bone density osteoporosis prevention", "papers": 19, "indirect": 39, "relevancy": 82},
        {"slug": "z2-gut-microbiome-mental", "headline": "Gut microbiome diversity predicts resilience to anxiety and depression",
         "description": "The gut-brain axis transmits microbial signals via vagal afferents and metabolite production that modulate mood and stress response.",
         "query": "gut microbiome diversity mental health anxiety gut-brain axis", "papers": 11, "indirect": 22, "relevancy": 66},
        {"slug": "z2-hrv-biofeedback", "headline": "HRV biofeedback training increases vagal tone within 6 weeks",
         "description": "Resonance-frequency breathing at ~0.1 Hz with real-time HRV feedback produces lasting autonomic improvement in controlled trials.",
         "query": "HRV biofeedback vagal tone resonance frequency breathing", "papers": 10, "indirect": 20, "relevancy": 70},
    ],

    3: [  # ── Good evidence, some nuance ────────────────────────────────────────
        {"slug": "z3-creatine-cognition", "headline": "Creatine supplementation improves cognitive performance under sleep deprivation",
         "description": "Beyond its role in muscle ATP resynthesis, creatine supports brain energy metabolism and attenuates cognitive decline during stress.",
         "query": "creatine cognitive performance sleep deprivation brain energy", "papers": 10, "indirect": 21, "relevancy": 65},
        {"slug": "z3-nose-breathing-performance", "headline": "Nasal breathing during exercise improves endurance and CO₂ tolerance",
         "description": "Nasal airflow warms, humidifies, and filters air while upregulating nitric oxide production, improving oxygen delivery efficiency.",
         "query": "nasal breathing exercise performance nitric oxide CO2", "papers": 8, "indirect": 16, "relevancy": 61},
        {"slug": "z3-omega3-brain", "headline": "Omega-3 fatty acids reduce neuroinflammation and support cognitive ageing",
         "description": "DHA and EPA are structurally incorporated into neuronal membranes; supplementation reduces inflammatory markers and cognitive decline.",
         "query": "omega-3 DHA EPA neuroinflammation cognitive aging", "papers": 14, "indirect": 28, "relevancy": 70},
        {"slug": "z3-caffeine-sleep-latency", "headline": "Caffeine consumed after noon measurably delays sleep onset",
         "description": "Caffeine's adenosine antagonism has a 5–7 hour half-life; afternoon intake significantly extends sleep latency and reduces slow-wave sleep.",
         "query": "caffeine sleep latency adenosine half-life slow wave", "papers": 12, "indirect": 24, "relevancy": 76},
        {"slug": "z3-hiit-vs-liss", "headline": "HIIT produces equivalent VO₂ max gains in half the training time",
         "description": "High-intensity intervals drive the same cardiorespiratory adaptations as steady-state training, with greater time efficiency.",
         "query": "HIIT vs steady state VO2 max cardiovascular adaptation", "papers": 16, "indirect": 33, "relevancy": 73},
        {"slug": "z3-vitamin-d-immune", "headline": "Vitamin D deficiency impairs innate immune response to respiratory infection",
         "description": "Supplementation in deficient individuals reduces upper respiratory tract infection incidence by approximately 50% in RCTs.",
         "query": "vitamin D immune function respiratory infection RCT", "papers": 13, "indirect": 26, "relevancy": 68},
        {"slug": "z3-intermittent-fasting-weight", "headline": "Intermittent fasting achieves weight loss comparable to continuous restriction",
         "description": "Multiple RCTs find 16:8 and 5:2 protocols produce equivalent caloric deficit and metabolic improvements to daily restriction.",
         "query": "intermittent fasting weight loss metabolic RCT comparison", "papers": 11, "indirect": 22, "relevancy": 66},
        {"slug": "z3-postexercise-protein", "headline": "Post-exercise protein within 2 hours maximises muscle protein synthesis",
         "description": "The anabolic window is real but longer than once thought; total daily protein matters more than exact timing in most contexts.",
         "query": "post-exercise protein synthesis anabolic window timing", "papers": 15, "indirect": 30, "relevancy": 72},
        {"slug": "z3-wearable-illness-temp", "headline": "Wearable skin temperature predicts illness onset 1–2 days early",
         "description": "Continuous temperature monitoring detects the thermal signature of immune activation before subjective symptoms appear.",
         "query": "wearable skin temperature illness detection early prediction", "papers": 8, "indirect": 17, "relevancy": 64},
        {"slug": "z3-sleep-cardiac-position", "headline": "Left-side sleeping may reduce cardiac load in susceptible individuals",
         "description": "Limited evidence suggests sleeping position influences nocturnal heart rate, arrhythmia frequency, and acid reflux incidence.",
         "query": "sleep position cardiac health arrhythmia left right side", "papers": 6, "indirect": 12, "relevancy": 55},
    ],

    4: [  # ── Observational / emerging evidence ───────────────────────────────
        {"slug": "z4-cgm-athletes", "headline": "Continuous glucose monitoring reveals hidden glycaemic variability in healthy athletes",
         "description": "CGM data show that trained athletes experience significant post-meal glucose spikes that correlate with performance metrics.",
         "query": "continuous glucose monitoring athletes performance glycemic variability", "papers": 7, "indirect": 15, "relevancy": 58},
        {"slug": "z4-grip-strength-aging", "headline": "Grip strength is an accurate proxy for biological age",
         "description": "Handgrip dynamometry correlates with lean mass, bone density, and cognitive function — outperforming many lab-based ageing markers.",
         "query": "grip strength biological age mortality longevity marker", "papers": 9, "indirect": 18, "relevancy": 62},
        {"slug": "z4-bfr-training", "headline": "Blood flow restriction training builds muscle at 20–30% of 1RM",
         "description": "Occlusion training elicits hypertrophy comparable to heavy loads at a fraction of the mechanical stress — useful post-injury.",
         "query": "blood flow restriction training muscle hypertrophy low load", "papers": 11, "indirect": 22, "relevancy": 60},
        {"slug": "z4-lactate-zone2", "headline": "Training at lactate threshold 1 maximises mitochondrial adaptation",
         "description": "Zone 2 training drives mitochondrial biogenesis, improves fat oxidation, and is increasingly recognised as foundational for longevity.",
         "query": "lactate threshold zone 2 mitochondrial biogenesis fat oxidation", "papers": 8, "indirect": 16, "relevancy": 57},
        {"slug": "z4-heat-shock-proteins", "headline": "Sauna exposure induces heat shock proteins that protect against cellular stress",
         "description": "Repeated thermal stress upregulates HSP70 and HSP90, which act as molecular chaperones protecting proteins from misfolding.",
         "query": "sauna heat shock proteins HSP cellular stress protection", "papers": 7, "indirect": 14, "relevancy": 55},
        {"slug": "z4-polyphenols-microbiome", "headline": "Dietary polyphenols selectively feed beneficial gut bacteria",
         "description": "Flavonoids and resveratrol are metabolised by the microbiome into bioactive compounds that reduce gut inflammation and improve diversity.",
         "query": "dietary polyphenols gut microbiome diversity inflammation", "papers": 9, "indirect": 18, "relevancy": 59},
        {"slug": "z4-heart-rate-recovery", "headline": "Heart rate recovery after exercise predicts autonomic fitness",
         "description": "The speed of HR return to baseline after peak exertion is a sensitive marker of parasympathetic capacity and cardiovascular reserve.",
         "query": "heart rate recovery autonomic nervous system cardiovascular fitness", "papers": 10, "indirect": 20, "relevancy": 63},
        {"slug": "z4-cortisol-awakening", "headline": "The cortisol awakening response reflects HPA axis resilience",
         "description": "The 50–100% cortisol surge in the first 30 minutes after waking is attenuated by chronic stress and is a candidate biological age marker.",
         "query": "cortisol awakening response HPA axis stress resilience", "papers": 8, "indirect": 16, "relevancy": 57},
        {"slug": "z4-altitude-rbc", "headline": "Altitude training increases red blood cell mass and endurance capacity",
         "description": "Three weeks at 2,000–3,000m altitude elevates EPO and haematocrit, improving sea-level VO₂ max for 4–8 weeks post-return.",
         "query": "altitude training red blood cell EPO erythropoiesis endurance", "papers": 12, "indirect": 24, "relevancy": 65},
        {"slug": "z4-breath-co2-hrv", "headline": "CO₂ tolerance training improves HRV and reduces anxiety",
         "description": "Slow breathing that allows mild CO₂ accumulation calibrates the chemoreceptor response and strengthens vagal tone over time.",
         "query": "CO2 tolerance breathing HRV vagal tone anxiety", "papers": 6, "indirect": 12, "relevancy": 52},
    ],

    5: [  # ── Mechanistic / limited trials ─────────────────────────────────────
        {"slug": "z5-nad-mitochondria", "headline": "NAD⁺ precursors restore mitochondrial function in ageing cells",
         "description": "NMN and NR supplementation replenish cellular NAD⁺, reversing hallmarks of mitochondrial ageing in animal models and early human trials.",
         "query": "NAD+ NMN NR mitochondrial aging supplementation", "papers": 6, "indirect": 13, "relevancy": 52},
        {"slug": "z5-rapamycin-mtor", "headline": "Rapamycin extends lifespan in multiple species by inhibiting mTOR",
         "description": "mTOR inhibition slows the rate of cell growth, reduces protein aggregation, and extends median lifespan in mice by up to 25%.",
         "query": "rapamycin mTOR inhibition longevity lifespan mouse", "papers": 5, "indirect": 11, "relevancy": 48},
        {"slug": "z5-ketones-brain", "headline": "Exogenous ketones provide an alternative brain fuel in glucose scarcity",
         "description": "Ketone bodies cross the blood-brain barrier and are oxidised by neurons, potentially protecting against neurodegenerative metabolic stress.",
         "query": "ketone bodies brain fuel metabolism neurodegeneration", "papers": 7, "indirect": 14, "relevancy": 51},
        {"slug": "z5-autophagy-fasting", "headline": "Extended fasting triggers autophagy — the cell's self-cleaning programme",
         "description": "After ~18 hours of fasting, autophagy removes damaged proteins and organelles; the health implications in humans are still under study.",
         "query": "autophagy fasting cellular cleanup damaged proteins", "papers": 5, "indirect": 10, "relevancy": 49},
        {"slug": "z5-telomere-exercise", "headline": "Aerobic exercise is associated with longer telomeres across populations",
         "description": "Active individuals consistently show longer leucocyte telomere length, though causality and magnitude remain debated.",
         "query": "aerobic exercise telomere length leucocyte aging", "papers": 9, "indirect": 18, "relevancy": 55},
        {"slug": "z5-sirtuins-restriction", "headline": "Caloric restriction activates sirtuins, key regulators of cellular ageing",
         "description": "SIRT1–7 deacetylate histones and transcription factors in response to low-energy states, slowing multiple ageing pathways.",
         "query": "sirtuins caloric restriction cellular aging SIRT1", "papers": 6, "indirect": 12, "relevancy": 50},
        {"slug": "z5-inflammaging", "headline": "Chronic low-grade inflammation accelerates nearly every disease of ageing",
         "description": "Inflammaging — the persistent smouldering immune activation in older adults — is a causal driver of sarcopenia, neurodegeneration, and CVD.",
         "query": "inflammaging chronic inflammation aging disease cardiovascular", "papers": 8, "indirect": 16, "relevancy": 54},
        {"slug": "z5-brown-adipose-cold", "headline": "Cold exposure activates brown adipose tissue and increases metabolic rate",
         "description": "Brown fat combusts glucose and fatty acids to generate heat, and repeated cold exposure may expand BAT volume in adults.",
         "query": "brown adipose tissue cold exposure thermogenesis metabolic rate", "papers": 7, "indirect": 14, "relevancy": 51},
        {"slug": "z5-mitochondrial-biogenesis", "headline": "Endurance training drives mitochondrial biogenesis via PGC-1α",
         "description": "Exercise activates PGC-1α, the master transcriptional coactivator that stimulates new mitochondria — the cellular power plants underlying endurance.",
         "query": "mitochondrial biogenesis PGC-1alpha endurance training", "papers": 8, "indirect": 16, "relevancy": 56},
        {"slug": "z5-mtor-muscle-aging", "headline": "mTOR signalling paradoxically contributes to both muscle growth and ageing",
         "description": "While acute mTOR activation builds muscle, chronic elevation may accelerate cellular senescence — optimal pulsing remains an open question.",
         "query": "mTOR muscle growth aging senescence anabolic resistance", "papers": 5, "indirect": 10, "relevancy": 46},
    ],

    6: [  # ── Pilot studies / exploratory ──────────────────────────────────────
        {"slug": "z6-hyperbaric-aging", "headline": "Hyperbaric oxygen therapy shows early signs of reversing cellular ageing markers",
         "description": "Small Israeli trials found significant telomere lengthening and senescent cell reduction after 60 HBOT sessions in older adults.",
         "query": "hyperbaric oxygen therapy aging telomere senescent cells", "papers": 4, "indirect": 8, "relevancy": 38},
        {"slug": "z6-young-plasma", "headline": "Parabiosis research identifies plasma factors that may slow ageing",
         "description": "Young blood plasma contains proteins like GDF11 that rejuvenate aged tissues in mice — human translation remains under investigation.",
         "query": "young blood plasma parabiosis GDF11 aging rejuvenation", "papers": 3, "indirect": 7, "relevancy": 35},
        {"slug": "z6-psychedelic-neuroplasticity", "headline": "Psilocybin promotes neuroplasticity and reduces rigid thought patterns",
         "description": "FMRI studies show psilocybin increases global brain connectivity and reduces default-mode network dominance, linked to therapeutic effects.",
         "query": "psilocybin neuroplasticity brain connectivity default mode network", "papers": 5, "indirect": 10, "relevancy": 40},
        {"slug": "z6-red-light-recovery", "headline": "Red and near-infrared light stimulates mitochondrial ATP production",
         "description": "Photobiomodulation at 660–850nm wavelengths activates cytochrome c oxidase, increasing cellular energy output in muscle and neural tissue.",
         "query": "photobiomodulation red light therapy mitochondria ATP cytochrome", "papers": 6, "indirect": 12, "relevancy": 42},
        {"slug": "z6-fecal-transplant-cognition", "headline": "Faecal microbiota transplant from young donors improves cognition in old mice",
         "description": "Transplanting microbiome from young to aged rodents reverses hippocampal gene expression and improves spatial memory.",
         "query": "fecal microbiota transplant cognition aging gut brain", "papers": 3, "indirect": 6, "relevancy": 36},
        {"slug": "z6-personalized-nutrition-genomics", "headline": "Personalised nutrition based on genetics outperforms universal dietary guidelines",
         "description": "Nutrigenomics studies find glycaemic and lipid responses vary dramatically by genotype, suggesting standard guidelines miss individual variation.",
         "query": "personalized nutrition genomics glycemic response nutrigenomics", "papers": 5, "indirect": 10, "relevancy": 43},
        {"slug": "z6-hydrogen-water", "headline": "Hydrogen-rich water shows antioxidant effects in early human trials",
         "description": "Pilot data suggest dissolved molecular hydrogen selectively neutralises hydroxyl radicals, the most damaging reactive oxygen species.",
         "query": "hydrogen rich water antioxidant oxidative stress clinical trial", "papers": 4, "indirect": 8, "relevancy": 37},
        {"slug": "z6-exogenous-ketones-performance", "headline": "Exogenous ketone esters improve endurance performance in elite athletes",
         "description": "Pilot studies at the Tour de France found ketone ester drinks improved power output at VO₂ max by ~2%, now widely used by pro cyclists.",
         "query": "exogenous ketone ester endurance performance elite athletes", "papers": 4, "indirect": 9, "relevancy": 41},
        {"slug": "z6-earthing-inflammation", "headline": "Direct ground contact may reduce inflammatory markers via electron transfer",
         "description": "Small studies suggest walking barefoot on earth or using grounding mats reduces cortisol and certain inflammatory cytokines overnight.",
         "query": "earthing grounding inflammation cortisol electron transfer", "papers": 3, "indirect": 6, "relevancy": 33},
        {"slug": "z6-vagal-nerve-stimulation", "headline": "Non-invasive vagal nerve stimulation reduces systemic inflammation",
         "description": "Transcutaneous auricular VNS activates the cholinergic anti-inflammatory pathway, showing promise in early RA and inflammatory bowel trials.",
         "query": "vagal nerve stimulation inflammation cholinergic anti-inflammatory", "papers": 5, "indirect": 10, "relevancy": 39},
    ],

    7: [  # ── Cutting-edge / very early signal ──────────────────────────────────
        {"slug": "z7-epigenetic-reprogramming", "headline": "Partial epigenetic reprogramming may reset biological age without losing cell identity",
         "description": "Short-cycle Yamanaka factor expression resets epigenetic age clocks in old cells while preserving cellular function — first human trials beginning.",
         "query": "epigenetic reprogramming Yamanaka factors aging reversal", "papers": 3, "indirect": 7, "relevancy": 34},
        {"slug": "z7-glymphatic-sleep", "headline": "The glymphatic system clears Alzheimer's proteins specifically during deep sleep",
         "description": "Cerebrospinal fluid pulsation during NREM sleep flushes amyloid-β and tau — sleep architecture quality directly predicts brain waste clearance.",
         "query": "glymphatic system sleep amyloid beta tau clearance NREM", "papers": 4, "indirect": 8, "relevancy": 38},
        {"slug": "z7-astrocyte-metabolism", "headline": "Astrocytes supply lactate to neurons during high cognitive demand",
         "description": "The astrocyte-neuron lactate shuttle may be a primary energy pathway during intense cognition — disruption may underlie cognitive fatigue.",
         "query": "astrocyte neuron lactate shuttle cognitive energy metabolism", "papers": 3, "indirect": 6, "relevancy": 32},
        {"slug": "z7-bioelectric-regeneration", "headline": "Bioelectric fields guide tissue regeneration beyond genetic programming",
         "description": "Cells communicate via voltage gradients that encode positional information — manipulating these fields shows promise for regenerating complex structures.",
         "query": "bioelectric field tissue regeneration voltage gradient morphogenesis", "papers": 3, "indirect": 6, "relevancy": 30},
        {"slug": "z7-circadian-cancer-treatment", "headline": "Cancer treatment outcomes vary dramatically by time of day of administration",
         "description": "Chronotherapy trials show chemotherapy efficacy and toxicity are governed by circadian regulation of target enzymes — largely unused clinically.",
         "query": "circadian cancer chronotherapy treatment time of day efficacy", "papers": 4, "indirect": 8, "relevancy": 36},
        {"slug": "z7-brain-gut-heart-axis", "headline": "A three-way brain–gut–heart axis may regulate stress resilience",
         "description": "Emerging evidence suggests microbial metabolites simultaneously modulate cardiac vagal tone and hypothalamic stress responses.",
         "query": "brain gut heart axis microbial metabolites vagal tone stress", "papers": 2, "indirect": 5, "relevancy": 29},
        {"slug": "z7-infrared-mitochondria", "headline": "Infrared sauna may trigger mitochondrial biogenesis beyond heat alone",
         "description": "Near-infrared wavelengths penetrate tissue and directly activate cytochrome c oxidase — potentially compounding sauna's cardiovascular benefits.",
         "query": "infrared sauna mitochondrial biogenesis cytochrome wavelength", "papers": 3, "indirect": 6, "relevancy": 31},
        {"slug": "z7-senolytic-drugs", "headline": "Senolytic drugs selectively clear zombie cells that drive ageing",
         "description": "Dasatinib+quercetin selectively induces apoptosis in senescent cells — phase 2 trials show measurable physical function improvements in older adults.",
         "query": "senolytics senescent cells aging dasatinib quercetin clinical trial", "papers": 4, "indirect": 8, "relevancy": 37},
        {"slug": "z7-quantum-biology-enzyme", "headline": "Quantum tunnelling in enzymes may underpin metabolic efficiency",
         "description": "Proton tunnelling in enzymatic reactions occurs on timescales that challenge classical biochemistry — implications for metabolic disease and ageing.",
         "query": "quantum tunnelling enzyme metabolism proton transfer biology", "papers": 2, "indirect": 4, "relevancy": 27},
        {"slug": "z7-microbiome-engineered-sleep", "headline": "Engineered gut bacteria may modulate sleep quality via tryptophan metabolism",
         "description": "Synthetic biology approaches aim to programme bacteria to regulate serotonin and melatonin precursor production in the gut on a circadian schedule.",
         "query": "engineered bacteria sleep tryptophan serotonin melatonin gut", "papers": 2, "indirect": 5, "relevancy": 28},
    ],

    8: [  # ── Highly speculative / preliminary ─────────────────────────────────
        {"slug": "z8-partial-reprogramming-in-vivo", "headline": "In-vivo partial reprogramming restores vision in aged mice",
         "description": "Harvard team used gene therapy to deliver Yamanaka factors directly into retinal cells, reversing epigenetic age and restoring visual acuity.",
         "query": "in vivo epigenetic reprogramming vision retina gene therapy aging", "papers": 2, "indirect": 4, "relevancy": 26},
        {"slug": "z8-structured-water", "headline": "Interfacial water near cell membranes may have distinct biological properties",
         "description": "Gerald Pollack's EZ water hypothesis proposes a fourth water phase at hydrophilic surfaces — contested but generating experimental interest.",
         "query": "exclusion zone water EZ water biological membrane cell", "papers": 2, "indirect": 5, "relevancy": 22},
        {"slug": "z8-negative-air-ions", "headline": "High concentrations of negative air ions may improve mood and cognitive speed",
         "description": "Meta-analyses of small trials suggest negative ionisation at very high densities reduces depressive symptoms — mechanism unknown.",
         "query": "negative air ions mood depression cognitive performance ionization", "papers": 3, "indirect": 6, "relevancy": 25},
        {"slug": "z8-hormesis-sleep-dep", "headline": "Controlled mild sleep deprivation may reset dysfunctional sleep architecture",
         "description": "Therapeutic sleep restriction increases homeostatic sleep pressure and is used clinically in CBT-I — broader hormetic effects are speculative.",
         "query": "sleep deprivation hormesis sleep restriction CBT-I sleep pressure", "papers": 2, "indirect": 5, "relevancy": 24},
        {"slug": "z8-polyvagal-elite", "headline": "Elite performers may access a distinct vagal state unavailable to others",
         "description": "Polyvagal theory's 'safe and social' state predicts performance zones not captured by HRV alone — awaiting rigorous sports science validation.",
         "query": "polyvagal theory performance safe social state HRV athletes", "papers": 2, "indirect": 4, "relevancy": 21},
        {"slug": "z8-biophotonic-signalling", "headline": "Cells emit ultra-weak light signals that may coordinate biological processes",
         "description": "Biophoton emission from metabolically active tissue has been measured — whether it encodes biological information remains highly contested.",
         "query": "biophoton emission cell signaling biological information metabolic", "papers": 2, "indirect": 4, "relevancy": 19},
        {"slug": "z8-mrna-tissue-repair", "headline": "Self-amplifying mRNA may enable targeted tissue repair without viral vectors",
         "description": "Next-generation saRNA constructs replicate inside target cells, producing therapeutic proteins at therapeutic doses for weeks from a single injection.",
         "query": "self-amplifying mRNA tissue repair saRNA gene therapy", "papers": 2, "indirect": 5, "relevancy": 23},
        {"slug": "z8-ozone-therapy", "headline": "Ozone therapy proponents claim systemic oxidative preconditioning improves recovery",
         "description": "Used in some European clinics, medical ozone is proposed to enhance mitochondrial function via controlled oxidative stress — evidence is limited and contested.",
         "query": "ozone therapy medical oxidative preconditioning recovery mitochondria", "papers": 2, "indirect": 4, "relevancy": 20},
        {"slug": "z8-wearable-10yr-disease", "headline": "Wearable AI may predict disease onset 10 years before symptoms appear",
         "description": "Speculative extrapolation of current trend detection: continuous biosignal analysis identifying disease signatures a decade in advance.",
         "query": "wearable AI disease prediction biosignal early detection machine learning", "papers": 3, "indirect": 6, "relevancy": 27},
        {"slug": "z8-theta-performance", "headline": "Sustained theta brainwave states correlate with peak cognitive performance",
         "description": "EEG studies in meditators and flow states show elevated theta power — whether targeted neurofeedback can reliably induce these states is unproven.",
         "query": "theta brainwave EEG meditation flow state cognitive performance neurofeedback", "papers": 2, "indirect": 4, "relevancy": 22},
    ],

    9: [  # ── Frontier / experimental ───────────────────────────────────────────
        {"slug": "z9-xenobots", "headline": "Xenobots — living machines built from stem cells — can self-replicate",
         "description": "Programmable biological machines constructed from frog embryonic cells exhibit kinematic self-replication — a new category of biological entity.",
         "query": "xenobots self-replicating biological machines stem cells programmable", "papers": 2, "indirect": 3, "relevancy": 18},
        {"slug": "z9-gene-therapy-telomere", "headline": "Gene therapy to extend telomeres is being self-administered by biohackers",
         "description": "Some researchers are self-injecting telomerase gene therapy constructs — no peer-reviewed human safety or efficacy data yet exist.",
         "query": "gene therapy telomerase telomere extension lifespan human", "papers": 1, "indirect": 3, "relevancy": 15},
        {"slug": "z9-synthetic-microbiome", "headline": "Fully synthetic microbiomes could be programmed from scratch for optimal health",
         "description": "Synthetic ecology approaches aim to design gut microbiome compositions from first principles — purely theoretical in humans at present.",
         "query": "synthetic microbiome engineered gut bacteria design from scratch", "papers": 1, "indirect": 3, "relevancy": 14},
        {"slug": "z9-nanobody-longevity", "headline": "Nanobody-based delivery may allow longevity molecules to cross the blood-brain barrier",
         "description": "Engineered single-domain antibodies can ferry therapeutic cargo across the BBB — applying this to ageing biology is a theoretical frontier.",
         "query": "nanobody blood brain barrier longevity drug delivery aging", "papers": 1, "indirect": 3, "relevancy": 13},
        {"slug": "z9-agi-longevity-design", "headline": "AGI systems may discover longevity interventions beyond human reasoning capacity",
         "description": "Speculative: advanced AI exploring molecular dynamics at scale could identify multi-target ageing interventions no human researcher would conceive.",
         "query": "artificial intelligence longevity drug discovery aging molecular", "papers": 2, "indirect": 4, "relevancy": 17},
        {"slug": "z9-cryonics-viability", "headline": "Vitrification protocols may preserve neural connectivity through cryopreservation",
         "description": "Aldehyde-stabilised cryopreservation has demonstrated preservation of synaptic ultrastructure in animal brains — revival remains theoretical.",
         "query": "cryonics vitrification brain preservation neural connectivity", "papers": 1, "indirect": 3, "relevancy": 12},
        {"slug": "z9-suspended-animation", "headline": "Suspended animation via profound hypothermia may pause biological time",
         "description": "Emergency Preservation and Resuscitation trials show deep cooling can extend survival after cardiac arrest — broader metabolic arrest applications are speculative.",
         "query": "suspended animation hypothermia metabolic arrest emergency preservation", "papers": 2, "indirect": 4, "relevancy": 16},
        {"slug": "z9-whole-organ-bioprinting", "headline": "Bioprinted vascularised organs may eliminate transplant waiting lists within decades",
         "description": "3D bioprinting of complex vascularised tissue constructs is advancing rapidly — functional whole-organ printing for implantation remains a future goal.",
         "query": "organ bioprinting vascularized tissue transplant 3D printing", "papers": 2, "indirect": 4, "relevancy": 17},
        {"slug": "z9-consciousness-quantum", "headline": "Quantum coherence in microtubules may underlie conscious experience",
         "description": "Penrose-Hameroff orchestrated objective reduction posits quantum computation in neuronal microtubules as the basis of consciousness — highly contested.",
         "query": "quantum consciousness microtubules Penrose Hameroff orchestrated reduction", "papers": 1, "indirect": 2, "relevancy": 11},
        {"slug": "z9-partial-reprog-humans", "headline": "Systemic partial reprogramming could reverse human biological age by years",
         "description": "If safety barriers are cleared, whole-body epigenetic reset therapies may become viable — currently years from any clinical application.",
         "query": "systemic epigenetic reprogramming human clinical anti-aging Yamanaka", "papers": 2, "indirect": 4, "relevancy": 16},
    ],
}


def _all_topics() -> list:
    """Flat list of all topics across all zones — used by modal lookup."""
    return [t for zone_topics in TOPIC_ZONES.values() for t in zone_topics]


# ── OAuth callback ─────────────────────────────────────────────────────────────
params = st.query_params
if "code" in params and "topic" not in params and "insight" not in params:
    try:
        with st.spinner("Connecting…"):
            tokens = exchange_code_for_tokens(params["code"])
            info   = get_user_info(tokens["access_token"])
            email  = info.get("email", "")
            name   = info.get("full_name") or email or "User"
            uid    = save_user(email, tokens["access_token"], tokens["refresh_token"], name)
            st.session_state.update({
                "user_name": name, "user_id": uid,
                "access_token": tokens["access_token"],
                "email": email, "connected": True,
                "just_connected": True,
            })
            st.query_params.clear()
            st.rerun()
    except Exception as e:
        err = str(e)
        st.query_params.clear()
        if "invalid_grant" in err or "authorization_code" in err.lower():
            st.session_state["_oauth_error"] = "Authorisation expired — please try connecting again."
        elif "redirect_uri" in err.lower():
            st.session_state["_oauth_error"] = "Redirect URI mismatch — please contact support."
        else:
            st.session_state["_oauth_error"] = f"Could not connect Oura Ring: {err}"
        st.rerun()

_oauth_error = st.session_state.pop("_oauth_error", None)
if _oauth_error:
    st.error(_oauth_error)

connected    = st.session_state.get("connected", False)
user_name    = st.session_state.get("user_name", "")
user_id      = st.session_state.get("user_id")
access_token = st.session_state.get("access_token")

if connected and not access_token:
    u = get_user_by_email(st.session_state.get("email", ""))
    if u:
        access_token = u["oura_access_token"]
        user_id      = u["id"]
        st.session_state["access_token"] = access_token
        st.session_state["user_id"]      = user_id

# ── Payment status ─────────────────────────────────────────────────────────────
if connected and "is_paid" not in st.session_state:
    _email = st.session_state.get("email", "")
    st.session_state["is_paid"] = get_user_access(_email) if _email else False

# ── Session state defaults ─────────────────────────────────────────────────────
if "mode" not in st.session_state:
    st.session_state.mode = "research"
if "spec_val" not in st.session_state:
    st.session_state.spec_val = 2

spec_val   = st.session_state.spec_val
thumb_glow = get_glow_color(spec_val)

# Apply design system with current glow color
apply_design_system(thumb_glow=thumb_glow)

# ── Routing ────────────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED: NAVBAR
# ══════════════════════════════════════════════════════════════════════════════
def render_navbar():
    c_left, c_mid, c_right = st.columns([4, 2, 4])

    with c_left:
        search_query = st.text_input(
            "search", placeholder="Search any health topic…",
            label_visibility="collapsed", key="search"
        )

    with c_mid:
        st.markdown("""
        <div style="width:100%;text-align:center;">
            <span class="pulse-logo"
                  style="font-size:22px;font-weight:700;color:#FFFFFF;
                         letter-spacing:-0.5px;font-family:'Plus Jakarta Sans',sans-serif;">
                Pulse
            </span>
        </div>
        """, unsafe_allow_html=True)

    with c_right:
        if connected:
            initial = user_name[0].upper() if user_name else "U"
            st.markdown(f"""
            <div style="display:flex;justify-content:flex-end;align-items:center;">
                <details class="user-menu">
                    <summary>
                        <div class="user-avatar">{initial}</div>
                        <span class="user-name">{user_name}</span>
                        <span class="user-caret">&#9660;</span>
                    </summary>
                    <div class="user-dropdown">
                        <a href="?action=sync" target="_self">&#128260;&nbsp; Sync Ring</a>
                        <div class="dropdown-divider"></div>
                        <a href="?action=signout" target="_self" class="danger">&#10006;&nbsp; Sign out</a>
                    </div>
                </details>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="width:100%;display:flex;justify-content:flex-end;">
                <a href="{get_auth_url()}" target="_self"
                   style="font-size:14px;font-weight:500;color:#888888;
                          text-decoration:none;white-space:nowrap;
                          border:1px solid rgba(255,255,255,0.10);
                          border-radius:8px;padding:9px 20px;
                          transition:all 0.2s ease;"
                   onmouseover="this.style.color='#F0F0F0';this.style.borderColor='rgba(255,255,255,0.22)'"
                   onmouseout="this.style.color='#888888';this.style.borderColor='rgba(255,255,255,0.10)'">
                    Connect Oura Ring
                </a>
            </div>
            """, unsafe_allow_html=True)

    return st.session_state.get("search", "")


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED: MODE TOGGLE  (native st.button — 100% reliable navigation)
# ══════════════════════════════════════════════════════════════════════════════
def render_mode_toggle():
    mode = st.session_state.mode
    p_label = "Personalised Data" if connected else "Personalised Data (Connect Oura)"

    _, tab_center, _ = st.columns([3, 4, 3])
    with tab_center:
        r_col, p_col = st.columns([1, 2], gap="small")
        with r_col:
            # type="tertiary" = active styling; "secondary" = inactive
            r_type = "tertiary" if mode == "research" else "secondary"
            if st.button("Research", key="tab_research_btn",
                         type=r_type, use_container_width=True):
                st.session_state.mode = "research"
                st.session_state.pop("modal_slug", None)
                st.rerun()
        with p_col:
            p_type = "tertiary" if mode == "personal" else "secondary"
            if st.button(p_label, key="tab_personal_btn",
                         type=p_type, use_container_width=True):
                if connected:
                    st.session_state.mode = "personal"
                    st.session_state.pop("modal_slug", None)
                else:
                    st.session_state["nav_page"] = "connect"
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED: SPECULATION SLIDER
# ══════════════════════════════════════════════════════════════════════════════
def render_slider():
    st.markdown("""
    <div style="padding:4px 0 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:0 40px;margin-bottom:8px;">
            <span style="font-size:12px;font-weight:600;letter-spacing:0.06em;
                         text-transform:uppercase;color:#00C896;">
                &#9679; Evidence Based
            </span>
            <span style="font-size:11px;font-weight:500;letter-spacing:0.08em;
                         text-transform:uppercase;color:#555555;">
                Research Filter
            </span>
            <span style="font-size:12px;font-weight:600;letter-spacing:0.06em;
                         text-transform:uppercase;color:#E05050;">
                Speculative &#9679;
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    new_val = st.slider(
        "spec", min_value=0, max_value=10, value=st.session_state.spec_val,
        step=1, label_visibility="collapsed", key="spec_slider"
    )

    if new_val != st.session_state.spec_val:
        st.session_state.spec_val = new_val
        st.rerun()

    ev_type, _ = get_evidence_label(new_val)

    # Position indicator dot below track
    pct = new_val / 10 * 100
    ind_color = get_glow_color(new_val)
    st.markdown(f"""
    <div style="padding:0 40px;position:relative;height:28px;margin-top:4px;">
        <div style="position:absolute;left:calc({pct}% * 0.82 + 9%);
             transform:translateX(-50%);display:flex;flex-direction:column;
             align-items:center;gap:3px;">
            <div style="width:2px;height:6px;background:{ind_color};border-radius:1px;"></div>
            <span style="font-size:10px;font-weight:600;color:{ind_color};
                   white-space:nowrap;letter-spacing:0.05em;text-transform:uppercase;">
                {ev_type}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    return new_val


# ══════════════════════════════════════════════════════════════════════════════
#  COMPONENT: METRICS STRIP  (today vs personal all-time baseline)
# ══════════════════════════════════════════════════════════════════════════════
def render_metrics_strip(rows: list, baselines: dict, stats: dict):
    if not rows:
        return
    latest = next((r for r in rows if r.get("total_sleep_duration")), rows[0] if rows else None)
    if not latest:
        return

    def _color(val, base, higher_better=True):
        if val is None or not base:
            return "#F0F0F0"
        pct = (val - base) / max(base, 1) * 100
        if abs(pct) < 5:
            return "#F0F0F0"
        good = pct > 0 if higher_better else pct < 0
        return "#00C896" if good else "#E05050"

    def _arrow(val, base, higher_better=True):
        if val is None or not base:
            return "—", "#555555"
        diff = val - base
        pct = diff / max(base, 1) * 100
        if abs(pct) < 5:
            return "—", "#555555"
        good = diff > 0 if higher_better else diff < 0
        col = "#00C896" if good else "#E05050"
        sym = "▲" if diff > 0 else "▼"
        return f"{sym} {abs(diff):.0f} vs avg", col

    specs = [
        ("READINESS",   "readiness_score",    "",    True),
        ("SLEEP",       "sleep_score",         "",    True),
        ("HRV",         "hrv_average",         " ms", True),
        ("RESTING HR",  "resting_heart_rate",  " bpm",False),
        ("DEEP SLEEP",  "deep_sleep_duration", "dur", True),
        ("TOTAL SLEEP", "total_sleep_duration","dur", True),
    ]

    tiles = ""
    for idx, (label, key, unit, hb) in enumerate(specs):
        val  = latest.get(key)
        base = baselines.get(key)
        if val is None:
            continue
        val_str  = fmt_dur(val) if unit == "dur" else f"{int(val)}{unit}"
        col      = _color(val, base, hb)
        arr, ac  = _arrow(val, base, hb)
        sep      = "border-left:1px solid rgba(255,255,255,0.06);" if idx > 0 else ""
        tiles += (
            f'<div style="flex:1;min-width:110px;padding:14px 18px;{sep}cursor:default;transition:background 0.2s;"'
            f' onmouseover="this.style.background=\'rgba(255,255,255,0.02)\'"'
            f' onmouseout="this.style.background=\'transparent\'">'
            f'<p style="font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#555555;margin:0 0 6px;">{label}</p>'
            f'<p style="font-family:\'JetBrains Mono\',monospace;font-size:24px;font-weight:600;color:{col};margin:0 0 3px;letter-spacing:-0.5px;line-height:1;">{val_str}</p>'
            f'<p style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{ac};margin:0;">{arr}</p>'
            f'</div>'
        )

    if not tiles:
        return

    st.markdown(
        '<div style="background:#0d0d0d;border-bottom:1px solid rgba(255,255,255,0.06);">'
        f'<div style="display:flex;flex-wrap:nowrap;overflow-x:auto;">{tiles}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── History context bar ───────────────────────────────────────────────────
    total_days = stats.get("total_days", 0)
    if total_days:
        ed = stats.get("earliest_date", "")
        try:
            from datetime import datetime as _dt
            month_str = _dt.strptime(ed, "%Y-%m-%d").strftime("%B %Y")
        except Exception:
            month_str = ed or "your first day"
        st.markdown(
            f'<div style="background:#0d0d0d;border-bottom:1px solid rgba(255,255,255,0.04);padding:7px 40px;">'
            f'<span style="font-size:11px;color:#3a3a3a;">'
            f'Analysing since {month_str}'
            f' &nbsp;&middot;&nbsp; <span style="font-family:\'JetBrains Mono\',monospace;">{total_days}</span> days'
            f' &nbsp;&middot;&nbsp; Trends based on your full history</span></div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: CONNECTION SUCCESS  (shown once after OAuth, pulls full history)
# ══════════════════════════════════════════════════════════════════════════════
def render_connect_success():
    _uid = st.session_state.get("user_id")
    _tok = st.session_state.get("access_token")
    _name = st.session_state.get("user_name", "")

    st.markdown(
        '<div style="padding:72px 24px 20px;text-align:center;background:#080808;">'
        '<style>@keyframes spin{to{transform:rotate(360deg)}}</style>'
        '<div style="width:48px;height:48px;border-radius:50%;border:2px solid rgba(255,255,255,0.08);'
        'border-top-color:#00C896;animation:spin 0.8s linear infinite;margin:0 auto 24px;"></div>'
        '<h1 style="font-size:20px;font-weight:600;color:#F0F0F0;letter-spacing:-0.3px;margin:0 0 8px;">'
        'Oura Ring connected</h1>'
        '<p style="font-size:14px;color:#555555;margin:0 0 32px;max-width:360px;margin-left:auto;margin-right:auto;">'
        f'Welcome{", " + _name if _name else ""}. Pulling your full history — this may take a moment.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    status = st.empty()
    progress = st.progress(0)

    try:
        status.markdown('<p style="font-size:13px;color:#555555;text-align:center;">Fetching Oura data…</p>', unsafe_allow_html=True)
        data = fetch_all_oura_data(_tok)
        n = len(data)
        progress.progress(40)

        status.markdown(f'<p style="font-size:13px;color:#555555;text-align:center;">Saving {n} days…</p>', unsafe_allow_html=True)
        for day, metrics in data.items():
            save_oura_data(_uid, day, metrics)
        progress.progress(75)

        status.markdown('<p style="font-size:13px;color:#555555;text-align:center;">Detecting trends…</p>', unsafe_allow_html=True)
        _rows = get_oura_data(_uid)
        if _rows:
            _trends = detect_trends(_rows)
            for t in _trends:
                t["slug"] = t.get("headline", "")[:30].lower().replace(" ", "-")
            st.session_state["trends"] = _trends
        progress.progress(100)

        status.markdown('<p style="font-size:13px;font-weight:500;color:#00C896;text-align:center;">Analysis complete ✓</p>', unsafe_allow_html=True)

    except Exception as e:
        status.markdown(f'<p style="font-size:13px;color:#E05050;text-align:center;">Error: {e}</p>', unsafe_allow_html=True)

    st.markdown('<div style="height:40px;"></div>', unsafe_allow_html=True)
    render_footer()

    import time
    time.sleep(1.2)
    st.session_state.pop("just_connected", None)
    st.session_state.mode = "personal"
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  COMPONENT: TOPIC CARD
# ══════════════════════════════════════════════════════════════════════════════
def _card_style(relevancy: int, spec_val: int):
    """Return (shadow, border_color, accent, opacity) for a card.
    Base colour follows the slider zone so the whole grid shifts colour
    when you drag the slider. Opacity further modulates by match quality."""
    # ── Base colour from slider zone ──
    if spec_val <= 3:        # evidence-based
        r, g, b = 0, 200, 150    # green
    elif spec_val <= 6:      # middle
        r, g, b = 240, 192, 64   # yellow
    else:                    # speculative
        r, g, b = 224, 80, 80    # red

    shadow = f"0 0 0 1px rgba({r},{g},{b},0.30), 0 0 28px rgba({r},{g},{b},0.12)"
    border = f"rgba({r},{g},{b},0.30)"
    accent = f"rgb({r},{g},{b})"

    # ── Opacity: how well does this card match the current zone? ──
    if spec_val <= 3:      # evidence zone → high relevancy cards shine
        opacity = 0.30 + (relevancy / 100) * 0.70   # 0.49–0.96
    elif spec_val <= 6:    # middle zone → all roughly equal
        diff = abs(relevancy - 75) / 100
        opacity = 1.0 - diff * 0.35                  # 0.65–1.0
    else:                  # speculative zone → lower relevancy cards shine
        opacity = 0.30 + ((100 - relevancy) / 100) * 0.70  # 0.36–0.51 for high, up to 0.79 for low

    opacity = max(0.28, min(1.0, opacity))
    return shadow, border, accent, opacity


def topic_card_html(topic: dict, mode: str = "research", spec_val: int = 2) -> str:
    shadow, border_color, accent, opacity = _card_style(
        topic.get("relevancy", 70), spec_val
    )
    slug      = topic.get("slug", "")
    url_key   = f"modal_{mode}"
    papers    = topic.get("papers", 0)
    indirect  = topic.get("indirect", 0)
    relevancy = topic.get("relevancy", 0)
    headline  = topic.get("headline", "")
    desc      = topic.get("description", "")

    return (
        f'<div style="background:#111111;border:1px solid {border_color};'
        f'border-radius:12px;padding:18px 20px;display:flex;flex-direction:column;'
        f'box-shadow:{shadow};cursor:pointer;position:relative;opacity:{opacity};'
        f'height:200px;overflow:hidden;'
        f'transition:transform 0.2s ease,border-color 0.2s ease,background 0.2s ease,box-shadow 0.2s ease,opacity 0.3s ease;"'
        f' onmouseover="this.style.transform=\'translateY(-4px)\';this.style.borderColor=\'{accent}88\';this.style.background=\'#141414\';this.style.opacity=\'1\';this.querySelector(\'.card-arrow\').style.color=\'{accent}\'"'
        f' onmouseout="this.style.transform=\'translateY(0)\';this.style.borderColor=\'{border_color}\';this.style.background=\'#111111\';this.style.opacity=\'{opacity}\';this.querySelector(\'.card-arrow\').style.color=\'#555555\'">'
        f'<div style="position:absolute;top:14px;right:14px;text-align:right;display:flex;flex-direction:column;gap:1px;">'
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:9px;color:#444444;">{papers} papers</span>'
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:9px;color:{accent};font-weight:600;">{relevancy}</span>'
        f'</div>'
        f'<p style="font-size:14px;font-weight:600;color:#F0F0F0;line-height:1.4;margin:0 0 8px;padding-right:40px;letter-spacing:-0.1px;'
        f'display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">{headline}</p>'
        f'<p style="font-size:12px;color:#666666;line-height:1.55;margin:0;'
        f'display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;flex:1;">{desc}</p>'
        f'<div style="display:flex;justify-content:flex-end;margin-top:10px;">'
        f'<span class="card-arrow" style="font-size:14px;color:#555555;transition:color 0.2s ease;">&rarr;</span>'
        f'</div>'
        f'</div>'
    )


# ══════════════════════════════════════════════════════════════════════════════
#  COMPONENT: PAPER CARD (used inside modal)
# ══════════════════════════════════════════════════════════════════════════════
def paper_card_html(article: dict, mode: str = "research",
                    personal_connection: str = "", show_score: bool = False) -> str:
    title   = article.get("title", "")[:160]
    author  = article.get("authors", "").split(",")[0]
    if "," in article.get("authors", ""):
        author += " et al."
    journal = article.get("journal", "")
    date    = article.get("date", "")
    url     = article.get("url", "#")
    score   = get_paper_score(article, st.session_state.get("spec_val", 2))
    sc      = score_color(score)

    score_badge = (
        f'<div style="display:inline-flex;align-items:center;gap:5px;background:rgba(0,0,0,0.3);border:1px solid {sc}44;border-radius:5px;padding:2px 8px;margin-bottom:12px;">'
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:11px;font-weight:600;color:{sc};">{score}</span>'
        f'<span style="font-size:10px;color:#555555;font-weight:500;">score</span></div>'
    ) if show_score else ""

    personal_html = (
        f'<div style="background:rgba(0,200,150,0.04);border-left:2px solid rgba(0,200,150,0.3);border-radius:0 6px 6px 0;padding:10px 14px;margin-bottom:14px;">'
        f'<p style="font-size:12px;color:#00C896;line-height:1.6;margin:0;">{personal_connection}</p></div>'
    ) if (mode == "personal" and personal_connection) else ""

    return (
        f'<a href="{url}" target="_blank" style="text-decoration:none;display:block;height:100%;">'
        f'<div style="background:#161616;border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:16px 18px;display:flex;flex-direction:column;height:180px;overflow:hidden;cursor:pointer;transition:border-color 0.2s ease,background 0.2s ease,transform 0.2s ease;"'
        f' onmouseover="this.style.borderColor=\'rgba(255,255,255,0.18)\';this.style.background=\'#1a1a1a\';this.style.transform=\'translateY(-3px)\'"'
        f' onmouseout="this.style.borderColor=\'rgba(255,255,255,0.07)\';this.style.background=\'#161616\';this.style.transform=\'translateY(0)\'">'
        f'{score_badge}'
        f'<p style="font-size:12px;font-weight:500;color:#F0F0F0;line-height:1.5;margin:0 0 6px;letter-spacing:-0.1px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">{title}</p>'
        f'<p style="font-family:\'JetBrains Mono\',monospace;font-size:9px;color:#444444;margin:0 0 8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{author} &middot; {journal} &middot; {date}</p>'
        f'{personal_html}'
        f'<div style="margin-top:auto;padding-top:8px;border-top:1px solid rgba(255,255,255,0.05);">'
        f'<span style="font-size:10px;font-weight:500;color:#555555;">Open in PubMed &nearr;</span>'
        f'</div></div></a>'
    )


# ══════════════════════════════════════════════════════════════════════════════
#  COMPONENT: MODAL POPUP
# ══════════════════════════════════════════════════════════════════════════════
def render_modal(slug: str, mode: str = "research"):
    # ── Resolve topic data ──────────────────────────────────────────────────────
    if mode == "research":
        topic       = next((t for t in _all_topics() if t["slug"] == slug), None)
        headline    = topic["headline"] if topic else slug
        description = topic.get("description", "") if topic else ""
        query       = topic.get("query", slug) if topic else slug
        relevancy   = topic.get("relevancy", 70) if topic else 70
        papers_cnt  = topic.get("papers", 0) if topic else 0
        indirect    = topic.get("indirect", 0) if topic else 0
        badge_label = "Research"
        badge_color = "#888888"
    else:
        trends = st.session_state.get("trends", [])
        topic  = next((t for t in trends if t.get("slug") == slug), None)
        if not topic:
            return
        headline    = topic.get("headline", slug)
        description = topic.get("description", "")
        metrics     = topic.get("metrics_involved", [])
        query       = " ".join(m.replace("_", " ") for m in metrics[:3])
        relevancy   = 85 if topic.get("confidence") == "high" else 55 if topic.get("confidence") == "medium" else 35
        papers_cnt  = len(metrics) * 4
        indirect    = len(metrics) * 9
        badge_label = "Your Data"
        badge_color = get_conf_color(topic.get("confidence", "medium"))

    sc_val  = st.session_state.get("spec_val", 2)
    ev_type, _ = get_evidence_label(sc_val)

    # evidence accent colour
    if relevancy >= 75:
        ev_color, ev_dim = "#00C896", "rgba(0,200,150,0.10)"
        ev_label = "High Evidence"
    elif relevancy >= 45:
        ev_color, ev_dim = "#F0C040", "rgba(240,192,64,0.10)"
        ev_label = "Medium Evidence"
    else:
        ev_color, ev_dim = "#E05050", "rgba(224,80,80,0.10)"
        ev_label = "Speculative"

    # ── Modal top bar + hero (pure HTML — avoids Streamlit column navbar CSS) ────
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:10px 40px 8px;border-bottom:1px solid rgba(255,255,255,0.06);">'
        f'<a href="?back=1" target="_self" style="font-size:13px;color:rgba(255,255,255,0.6);'
        f'text-decoration:none;transition:color 0.2s;" '
        f'onmouseover="this.style.color=\'#FFFFFF\'" onmouseout="this.style.color=\'rgba(255,255,255,0.6)\'">&#8592; Back</a>'
        f'<span style="font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;'
        f'color:{badge_color};background:rgba(0,0,0,0.5);border:1px solid {badge_color}44;'
        f'border-radius:5px;padding:3px 10px;">{badge_label}</span>'
        f'</div>'
        f'<div style="border-bottom:1px solid rgba(255,255,255,0.06);padding:20px 0 20px;">'
        f'<div style="max-width:960px;margin:0 auto;padding:0 40px;">'
        f'<div style="display:inline-flex;align-items:center;gap:8px;background:{ev_dim};border:1px solid {ev_color}33;border-radius:999px;padding:5px 14px;margin-bottom:16px;">'
        f'<span style="width:6px;height:6px;border-radius:50%;background:{ev_color};display:inline-block;box-shadow:0 0 8px {ev_color};"></span>'
        f'<span style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:{ev_color};">{ev_label} &middot; {ev_type}</span>'
        f'</div>'
        f'<h1 style="font-size:clamp(24px,3.5vw,42px);font-weight:700;color:#F0F0F0;letter-spacing:-0.8px;line-height:1.15;margin:0 0 14px;max-width:820px;">{headline}</h1>'
        f'<p style="font-size:15px;color:#777777;line-height:1.65;margin:0;max-width:680px;">{description}</p>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── Stats strip ───────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="max-width:960px;margin:0 auto;padding:14px 40px 0;">'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">'
        f'<div style="background:#111111;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:24px 28px;">'
        f'<p style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#444444;margin:0 0 10px;">Research Papers</p>'
        f'<p style="font-family:\'JetBrains Mono\',monospace;font-size:36px;font-weight:600;color:#F0F0F0;margin:0;letter-spacing:-1px;line-height:1;">{papers_cnt}</p>'
        f'</div>'
        f'<div style="background:#111111;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:24px 28px;">'
        f'<p style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#444444;margin:0 0 10px;">Indirect Citations</p>'
        f'<p style="font-family:\'JetBrains Mono\',monospace;font-size:36px;font-weight:600;color:#F0F0F0;margin:0;letter-spacing:-1px;line-height:1;">{indirect}</p>'
        f'</div>'
        f'<div style="background:#111111;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:24px 28px;">'
        f'<p style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#444444;margin:0 0 10px;">Relevancy Score</p>'
        f'<p style="font-family:\'JetBrains Mono\',monospace;font-size:36px;font-weight:600;color:{ev_color};margin:0;letter-spacing:-1px;line-height:1;">{relevancy}</p>'
        f'</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── Personal data callout (Your Data mode) ────────────────────────────────────
    if mode == "personal" and topic:
        dp     = topic.get("data_points", {})
        dp_str = ""
        if isinstance(dp, dict) and dp:
            dp_str = " &nbsp;&middot;&nbsp; ".join(
                f"{k.replace('_',' ').title()}: {v}" for k, v in list(dp.items())[:4]
            )
        dp_row = f'<p style="font-family:JetBrains Mono,monospace;font-size:11px;color:#444;margin:0;">{dp_str}</p>' if dp_str else ""
        st.markdown(
            f'<div style="max-width:960px;margin:0 auto;padding:20px 40px 0;">'
            f'<div style="background:rgba(0,200,150,0.04);border:1px solid rgba(0,200,150,0.15);border-left:3px solid #00C896;border-radius:0 12px 12px 0;padding:20px 24px;">'
            f'<p style="font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#00C896;margin:0 0 8px;">In your data</p>'
            f'<p style="font-size:14px;color:#C8E6C9;line-height:1.7;margin:0 0 8px;">{description}</p>'
            f'{dp_row}</div></div>',
            unsafe_allow_html=True,
        )

    # ── AI Summary ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="max-width:960px;margin:0 auto;padding:24px 40px 0;">'
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">'
        '<div style="width:3px;height:14px;border-radius:2px;background:#7C6AF7;flex-shrink:0;"></div>'
        '<p style="font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#555555;margin:0;">What the science says</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    with st.spinner("Generating summary…"):
        summary = get_topic_summary(headline, description, query, sc_val)

    paras = [p.strip() for p in summary.split("\n\n") if p.strip()]
    paras_html = "".join(
        f'<p style="font-size:15px;color:#BBBBBB;line-height:1.75;'
        f'margin:0 0 16px;font-weight:400;">{p}</p>'
        for p in paras
    )
    st.markdown(
        '<div style="max-width:960px;margin:0 auto;padding:0 40px;">'
        + paras_html
        + '</div>',
        unsafe_allow_html=True,
    )

    # ── Supporting research ───────────────────────────────────────────────────────
    st.markdown(
        f'<div style="max-width:960px;margin:0 auto;padding:24px 40px 0;">'
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">'
        f'<div style="width:3px;height:14px;border-radius:2px;background:{ev_color};flex-shrink:0;"></div>'
        f'<p style="font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#555555;margin:0;">Supporting research &middot; {ev_type}</p>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    with st.spinner("Finding papers…"):
        articles = search_pubmed(query, slider_value=sc_val, max_results=6)

    if articles:
        html = '<div style="max-width:960px;margin:0 auto;padding:0 40px;"><div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">'
        for a in articles[:6]:
            a_title   = a.get("title", "")[:160]
            authors = a.get("authors", "").split(",")[0]
            if "," in a.get("authors", ""):
                authors += " et al."
            journal = a.get("journal", "")
            year    = a.get("date", "")
            url     = a.get("url", "#")
            score   = get_paper_score(a, sc_val)
            sc      = score_color(score)
            s_label = "High Evidence" if score >= 80 else "Medium Evidence" if score >= 50 else "Speculative"
            pc_html = (
                '<div style="background:rgba(0,200,150,0.05);border-left:2px solid rgba(0,200,150,0.3);border-radius:0 6px 6px 0;padding:10px 14px;margin-bottom:14px;">'
                '<p style="font-size:12px;color:#00C896;line-height:1.6;margin:0;">'
                "This study's findings relate directly to the pattern detected in your Oura data."
                '</p></div>'
            ) if mode == "personal" else ""
            html += (
                f'<a href="{url}" target="_blank" style="text-decoration:none;display:block;">'
                f'<div style="background:#111111;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:22px 24px;display:flex;flex-direction:column;height:100%;transition:border-color 0.2s ease,background 0.2s ease,transform 0.18s ease;"'
                f' onmouseover="this.style.borderColor=\'rgba(255,255,255,0.18)\';this.style.background=\'#161616\';this.style.transform=\'translateY(-4px)\'"'
                f' onmouseout="this.style.borderColor=\'rgba(255,255,255,0.07)\';this.style.background=\'#111111\';this.style.transform=\'translateY(0)\'">'
                f'{pc_html}'
                f'<p style="font-size:14px;font-weight:500;color:#F0F0F0;line-height:1.5;margin:0 0 12px;letter-spacing:-0.1px;">{a_title}</p>'
                f'<p style="font-family:\'JetBrains Mono\',monospace;font-size:11px;color:#444444;margin:0 0 16px;line-height:1.5;">{authors} &middot; {journal} &middot; {year}</p>'
                f'<div style="margin-top:auto;padding-top:14px;border-top:1px solid rgba(255,255,255,0.05);display:flex;align-items:center;justify-content:space-between;">'
                f'<span style="display:inline-flex;align-items:center;gap:6px;background:{sc}18;border:1px solid {sc}44;border-radius:5px;padding:3px 10px;font-size:10px;font-weight:600;color:{sc};">{s_label} &middot; {score}</span>'
                f'<span style="font-size:12px;font-weight:500;color:#00C896;letter-spacing:-0.1px;">Open in PubMed &nearr;</span>'
                f'</div></div></a>'
            )
        html += '</div></div>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="max-width:960px;margin:0 auto;padding:0 40px;">'
            '<div style="background:#111111;border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:20px 24px;">'
            '<p style="font-size:13px;color:#555555;margin:0;">'
            'No papers found at this evidence level — try moving the slider toward Speculative.</p>'
            '</div></div>',
            unsafe_allow_html=True,
        )

    # ── Footer disclaimer ─────────────────────────────────────────────────────────
    st.markdown(
        '<div style="max-width:960px;margin:0 auto;padding:16px 40px 28px;">'
        '<div style="background:#111111;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:18px 24px;">'
        '<p style="font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#444444;margin:0 0 10px;">Disclaimer</p>'
        '<p style="font-size:13px;color:#555555;line-height:1.7;margin:0;">'
        'This information is for educational purposes only and should not be considered medical advice. '
        'Always consult a qualified healthcare professional before making changes to your health regimen. '
        'Evidence scores and summaries are AI-generated based on available research.'
        ' &nbsp;&middot;&nbsp; Research sourced from PubMed / NCBI.'
        '</p></div></div>',
        unsafe_allow_html=True,
    )
    render_footer()


# ══════════════════════════════════════════════════════════════════════════════
#  COMPONENT: CARD GRID  (uses st.columns so st.button works inside)
# ══════════════════════════════════════════════════════════════════════════════
def _render_card_grid(topics: list, mode: str, spec_val: int, zone: int):
    """Render 9 topics as a 3×3 grid. Refresh cycles through a pool from adjacent zones."""
    # Build pool: current zone + neighbors, deduped
    pool: list = []
    if zone > 0:
        pool += TOPIC_ZONES.get(zone - 1, [])
    pool += topics
    if zone < 9:
        pool += TOPIC_ZONES.get(zone + 1, [])
    seen: set = set()
    deduped: list = []
    for t in pool:
        if t["slug"] not in seen:
            seen.add(t["slug"])
            deduped.append(t)
    pool = deduped

    PER_PAGE = 9
    rc_key = f"refresh_count_{mode}_{zone}"
    refresh_count = st.session_state.get(rc_key, 0)

    # Slice window with wrap-around so Refresh always shows fresh cards
    start = (refresh_count * PER_PAGE) % max(len(pool), 1)
    if start + PER_PAGE <= len(pool):
        visible = pool[start : start + PER_PAGE]
    else:
        visible = (pool[start:] + pool[: PER_PAGE - (len(pool) - start)])[:PER_PAGE]

    _, center, _ = st.columns([1, 22, 1])
    with center:
        for row_start in range(0, len(visible), 3):
            row_topics = visible[row_start : row_start + 3]
            cols = st.columns(len(row_topics), gap="small")
            for i, t in enumerate(row_topics):
                with cols[i]:
                    st.markdown(
                        topic_card_html(t, mode=mode, spec_val=spec_val),
                        unsafe_allow_html=True,
                    )
                    btn_key = f"card_{t['slug']}_{zone}_{refresh_count}_{row_start + i}_{mode}"
                    if st.button(" ", key=btn_key, use_container_width=True, type="primary"):
                        st.session_state["modal_slug"] = t["slug"]
                        st.session_state["modal_mode"] = mode
                        st.rerun()
            st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)

    # Refresh button — always visible, replaces the 9 cards with the next batch
    _, lm_col, _ = st.columns([3, 1, 3])
    with lm_col:
        st.markdown('<div style="padding:4px 0 24px;">', unsafe_allow_html=True)
        if st.button("Refresh", key=f"refresh_{zone}_{mode}_{refresh_count}", use_container_width=True):
            st.session_state[rc_key] = refresh_count + 1
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: LANDING  (shown to non-connected visitors)
# ══════════════════════════════════════════════════════════════════════════════
def render_landing_page():
    auth_url = get_auth_url()
    st.markdown(f"""
<style>
@keyframes hero-fade{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:translateY(0)}}}}
.hero-animate{{animation:hero-fade 0.7s ease forwards;}}
@keyframes glow-pulse{{0%,100%{{box-shadow:0 0 0 1px rgba(0,200,150,0.4),0 0 32px rgba(0,200,150,0.28),0 0 64px rgba(124,106,247,0.14);}}50%{{box-shadow:0 0 0 1px rgba(124,106,247,0.5),0 0 48px rgba(124,106,247,0.32),0 0 96px rgba(0,200,150,0.16);}}}}
@keyframes shimmer-slide{{0%{{left:-60%;}}100%{{left:120%;}}}}
.lp-cta{{display:inline-flex;align-items:center;gap:10px;background:linear-gradient(135deg,#00C896 0%,#7C6AF7 100%);color:#FFFFFF !important;font-size:16px;font-weight:700;letter-spacing:-0.2px;text-decoration:none !important;border-radius:12px;padding:16px 36px;position:relative;overflow:hidden;animation:glow-pulse 3s ease-in-out infinite;transition:opacity 0.2s,transform 0.2s;}}
.lp-cta:hover{{opacity:0.92;transform:translateY(-2px);}}
.lp-cta .shimmer{{position:absolute;top:0;left:-60%;width:40%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.22),transparent);animation:shimmer-slide 2.4s ease-in-out infinite;pointer-events:none;}}
.lp-sec-btn{{display:inline-flex;align-items:center;gap:8px;background:transparent;color:#888888 !important;font-size:14px;font-weight:500;text-decoration:none !important;border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:12px 24px;transition:all 0.2s;}}
.lp-sec-btn:hover{{color:#F0F0F0 !important;border-color:rgba(255,255,255,0.25);}}
</style>

<div style="background:#080808;font-family:'Plus Jakarta Sans',sans-serif;">

<!-- ── STICKY HEADER ── -->
<div style="position:sticky;top:0;z-index:600;height:60px;background:rgba(8,8,8,0.92);
            backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
            border-bottom:1px solid rgba(255,255,255,0.06);
            display:flex;align-items:center;justify-content:space-between;padding:0 40px;">
  <span style="font-size:20px;font-weight:700;color:#FFFFFF;letter-spacing:-0.5px;">Pulse</span>
  <div style="display:flex;align-items:center;gap:28px;">
    <a href="#how-it-works" target="_self" style="font-size:13px;color:#888888;text-decoration:none;">How it works</a>
    <a href="#research" target="_self" style="font-size:13px;color:#888888;text-decoration:none;">Research</a>
    <a href="#pricing" target="_self" style="font-size:13px;color:#888888;text-decoration:none;">Pricing</a>
  </div>
  <a href="{auth_url}" target="_self"
     style="display:inline-flex;align-items:center;gap:8px;background:#00C896;color:#080808 !important;
            font-size:13px;font-weight:700;text-decoration:none !important;border-radius:8px;
            padding:9px 18px;letter-spacing:-0.1px;transition:opacity 0.2s;"
     onmouseover="this.style.opacity='0.88'" onmouseout="this.style.opacity='1'"
     data-track="header-cta">
    Connect Oura Ring &#8594;
  </a>
</div>

<!-- ── HERO ── -->
<div class="hero-animate" style="text-align:center;padding:80px 24px 64px;max-width:860px;margin:0 auto;">
  <div style="display:inline-flex;align-items:center;gap:8px;background:rgba(0,200,150,0.08);
              border:1px solid rgba(0,200,150,0.2);border-radius:999px;padding:5px 16px;margin-bottom:28px;">
    <span style="width:6px;height:6px;border-radius:50%;background:#00C896;display:inline-block;box-shadow:0 0 8px #00C896;"></span>
    <span style="font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#00C896;">Personal Health Intelligence</span>
  </div>
  <h1 style="font-size:clamp(32px,5.5vw,62px);font-weight:700;color:#FFFFFF;letter-spacing:-1.5px;
             line-height:1.08;margin:0 0 20px;">
    Your Oura Ring knows things<br>your doctor doesn't.
  </h1>
  <p style="font-size:clamp(16px,2vw,19px);color:#888888;line-height:1.65;max-width:600px;margin:0 auto 40px;">
    Pulse connects your complete biometric history to peer-reviewed science.
    See what your body is actually telling you.
  </p>
  <div style="display:flex;flex-direction:column;align-items:center;gap:12px;">
    <a href="{auth_url}" target="_self" class="lp-cta" data-track="hero-cta">
      <span class="shimmer"></span>
      <span style="position:relative;z-index:1;">Connect your Oura Ring &mdash; free &#8594;</span>
    </a>
    <p style="font-size:12px;color:#444444;margin:0;">No credit card required to start</p>
  </div>
  <div style="display:flex;align-items:center;justify-content:center;gap:8px;flex-wrap:wrap;
              margin-top:32px;padding:14px 24px;background:rgba(255,255,255,0.03);
              border:1px solid rgba(255,255,255,0.06);border-radius:12px;max-width:580px;margin-left:auto;margin-right:auto;">
    <span style="font-size:12px;color:#555555;">Connected to</span>
    <span style="font-size:12px;font-weight:600;color:#F0F0F0;">50,000+ PubMed papers</span>
    <span style="color:#333333;">&middot;</span>
    <span style="font-size:12px;color:#555555;">Analysing HRV, sleep, readiness, stress &amp; more</span>
  </div>
</div>

<!-- ── PROBLEM SECTION ── -->
<div style="padding:64px 40px;border-top:1px solid rgba(255,255,255,0.04);">
  <div style="max-width:960px;margin:0 auto;text-align:center;">
    <h2 style="font-size:clamp(22px,3vw,34px);font-weight:700;color:#F0F0F0;letter-spacing:-0.6px;margin:0 0 12px;">
      You have the data.<br>You don&rsquo;t have the answers.
    </h2>
    <p style="font-size:15px;color:#555555;margin:0 0 48px;">Three problems. One solution.</p>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;text-align:left;">
      <div style="background:#111111;border:1px solid rgba(255,255,255,0.06);border-radius:14px;padding:28px 24px;">
        <div style="width:36px;height:36px;border-radius:8px;background:rgba(0,200,150,0.1);
                    border:1px solid rgba(0,200,150,0.2);display:flex;align-items:center;
                    justify-content:center;font-size:18px;margin-bottom:16px;">&#128200;</div>
        <p style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 8px;">Numbers without meaning</p>
        <p style="font-size:13px;color:#666666;line-height:1.6;margin:0;">Your Oura shows scores and metrics. It doesn&rsquo;t explain what they mean for your body specifically.</p>
      </div>
      <div style="background:#111111;border:1px solid rgba(255,255,255,0.06);border-radius:14px;padding:28px 24px;">
        <div style="width:36px;height:36px;border-radius:8px;background:rgba(124,106,247,0.1);
                    border:1px solid rgba(124,106,247,0.2);display:flex;align-items:center;
                    justify-content:center;font-size:18px;margin-bottom:16px;">&#128196;</div>
        <p style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 8px;">Research not written for you</p>
        <p style="font-size:13px;color:#666666;line-height:1.6;margin:0;">PubMed has 35 million papers. None of them are contextualised to your actual HRV, sleep latency, or recovery score.</p>
      </div>
      <div style="background:#111111;border:1px solid rgba(255,255,255,0.06);border-radius:14px;padding:28px 24px;">
        <div style="width:36px;height:36px;border-radius:8px;background:rgba(240,192,64,0.1);
                    border:1px solid rgba(240,192,64,0.2);display:flex;align-items:center;
                    justify-content:center;font-size:18px;margin-bottom:16px;">&#128176;</div>
        <p style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 8px;">Clinics cost $5,000/year</p>
        <p style="font-size:13px;color:#666666;line-height:1.6;margin:0;">Longevity clinics offer this level of insight. They charge thousands. And they don&rsquo;t have your daily biometrics.</p>
      </div>
    </div>
    <div style="margin-top:32px;padding:20px;background:rgba(0,200,150,0.04);
                border:1px solid rgba(0,200,150,0.15);border-radius:12px;">
      <p style="font-size:16px;font-weight:600;color:#00C896;margin:0;">Pulse bridges all three.</p>
    </div>
  </div>
</div>

<!-- ── HOW IT WORKS ── -->
<div id="how-it-works" style="padding:64px 40px;border-top:1px solid rgba(255,255,255,0.04);">
  <div style="max-width:800px;margin:0 auto;text-align:center;">
    <p style="font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#555555;margin:0 0 12px;">Simple</p>
    <h2 style="font-size:clamp(22px,3vw,34px);font-weight:700;color:#F0F0F0;letter-spacing:-0.6px;margin:0 0 48px;">Three steps to understanding your biology</h2>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px;text-align:left;">
      <div style="position:relative;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;color:#00C896;
                    letter-spacing:0.08em;margin-bottom:16px;">01</div>
        <p style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 8px;">Connect your Oura Ring</p>
        <p style="font-size:13px;color:#666666;line-height:1.6;margin:0;">One click OAuth. Takes 30 seconds. We request read-only access — we never write to your ring.</p>
      </div>
      <div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;color:#7C6AF7;
                    letter-spacing:0.08em;margin-bottom:16px;">02</div>
        <p style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 8px;">We analyse your complete history</p>
        <p style="font-size:13px;color:#666666;line-height:1.6;margin:0;">Every day since you started wearing your ring. Sleep, HRV, readiness, activity, stress — all of it.</p>
      </div>
      <div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;color:#F0C040;
                    letter-spacing:0.08em;margin-bottom:16px;">03</div>
        <p style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 8px;">Read what the science says about your body</p>
        <p style="font-size:13px;color:#666666;line-height:1.6;margin:0;">AI detects patterns in your data and connects each one to peer-reviewed research — personalised to your numbers.</p>
      </div>
    </div>
  </div>
</div>

<!-- ── RESEARCH PREVIEW ── -->
<div id="research" style="padding:64px 40px;border-top:1px solid rgba(255,255,255,0.04);">
  <div style="max-width:960px;margin:0 auto;text-align:center;">
    <p style="font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#555555;margin:0 0 12px;">Free to explore</p>
    <h2 style="font-size:clamp(22px,3vw,34px);font-weight:700;color:#F0F0F0;letter-spacing:-0.6px;margin:0 0 12px;">Try it free &mdash; no Oura required</h2>
    <p style="font-size:15px;color:#666666;margin:0 0 40px;">Explore the peer-reviewed science behind HRV, sleep, stress, and recovery</p>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;text-align:left;margin-bottom:32px;">
      <div style="background:#111111;border:1px solid rgba(0,200,150,0.25);border-radius:12px;padding:20px;">
        <div style="display:inline-flex;align-items:center;gap:6px;background:rgba(0,200,150,0.08);border:1px solid rgba(0,200,150,0.2);border-radius:5px;padding:3px 8px;margin-bottom:12px;">
          <span style="font-size:10px;font-weight:600;color:#00C896;letter-spacing:0.06em;text-transform:uppercase;">High Evidence</span>
        </div>
        <p style="font-size:14px;font-weight:600;color:#F0F0F0;margin:0 0 8px;line-height:1.3;">HRV and sleep quality are tightly coupled</p>
        <p style="font-size:12px;color:#666666;line-height:1.5;margin:0;">Autonomic recovery during sleep directly predicts next-day heart rate variability.</p>
        <div style="display:flex;gap:16px;margin-top:14px;">
          <span style="font-size:11px;color:#444444;">24 papers</span>
          <span style="font-size:11px;color:#444444;">91 relevancy</span>
        </div>
      </div>
      <div style="background:#111111;border:1px solid rgba(124,106,247,0.25);border-radius:12px;padding:20px;">
        <div style="display:inline-flex;align-items:center;gap:6px;background:rgba(124,106,247,0.08);border:1px solid rgba(124,106,247,0.2);border-radius:5px;padding:3px 8px;margin-bottom:12px;">
          <span style="font-size:10px;font-weight:600;color:#7C6AF7;letter-spacing:0.06em;text-transform:uppercase;">High Evidence</span>
        </div>
        <p style="font-size:14px;font-weight:600;color:#F0F0F0;margin:0 0 8px;line-height:1.3;">Deep sleep consolidates memory and clears metabolic waste</p>
        <p style="font-size:12px;color:#666666;line-height:1.5;margin:0;">Slow-wave sleep replays learned information and flushes neurotoxic waste via the glymphatic system.</p>
        <div style="display:flex;gap:16px;margin-top:14px;">
          <span style="font-size:11px;color:#444444;">19 papers</span>
          <span style="font-size:11px;color:#444444;">88 relevancy</span>
        </div>
      </div>
      <div style="background:#111111;border:1px solid rgba(240,192,64,0.25);border-radius:12px;padding:20px;">
        <div style="display:inline-flex;align-items:center;gap:6px;background:rgba(240,192,64,0.08);border:1px solid rgba(240,192,64,0.2);border-radius:5px;padding:3px 8px;margin-bottom:12px;">
          <span style="font-size:10px;font-weight:600;color:#F0C040;letter-spacing:0.06em;text-transform:uppercase;">Strong Evidence</span>
        </div>
        <p style="font-size:14px;font-weight:600;color:#F0F0F0;margin:0 0 8px;line-height:1.3;">Alcohol fragments sleep architecture and suppresses HRV</p>
        <p style="font-size:12px;color:#666666;line-height:1.5;margin:0;">Even moderate alcohol before sleep disrupts staging and elevates resting HR in the first half of the night.</p>
        <div style="display:flex;gap:16px;margin-top:14px;">
          <span style="font-size:11px;color:#444444;">17 papers</span>
          <span style="font-size:11px;color:#444444;">89 relevancy</span>
        </div>
      </div>
    </div>
    <a href="?mode=research" target="_self" class="lp-sec-btn" data-track="research-preview-cta">
      Explore all research topics &#8594;
    </a>
  </div>
</div>

<!-- ── PRICING ── -->
<div id="pricing" style="padding:64px 40px;border-top:1px solid rgba(255,255,255,0.04);">
  <div style="max-width:480px;margin:0 auto;text-align:center;">
    <p style="font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#555555;margin:0 0 12px;">Simple pricing</p>
    <h2 style="font-size:clamp(22px,3vw,34px);font-weight:700;color:#F0F0F0;letter-spacing:-0.6px;margin:0 0 8px;">One plan. Everything included.</h2>
    <p style="font-size:13px;color:#555555;margin:0 0 32px;">Longevity clinics charge $5,000/year for this level of insight.</p>
    <div style="background:#111111;border:1px solid rgba(0,200,150,0.2);border-radius:16px;padding:32px;text-align:left;margin-bottom:24px;
                box-shadow:0 0 0 1px rgba(0,200,150,0.1),0 0 40px rgba(0,200,150,0.04);">
      <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:20px;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:48px;font-weight:600;color:#F0F0F0;letter-spacing:-2px;line-height:1;">$25</span>
        <span style="font-size:14px;color:#555555;">/ month</span>
      </div>
      <div style="height:1px;background:rgba(255,255,255,0.06);margin-bottom:20px;"></div>
      <div style="display:flex;flex-direction:column;gap:12px;">
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="width:18px;height:18px;border-radius:50%;background:rgba(0,200,150,0.15);border:1px solid rgba(0,200,150,0.35);display:flex;align-items:center;justify-content:center;font-size:10px;color:#00C896;flex-shrink:0;">&#10003;</span>
          <span style="font-size:13px;color:#CCCCCC;">Complete Oura history analysis — every day since day one</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="width:18px;height:18px;border-radius:50%;background:rgba(0,200,150,0.15);border:1px solid rgba(0,200,150,0.35);display:flex;align-items:center;justify-content:center;font-size:10px;color:#00C896;flex-shrink:0;">&#10003;</span>
          <span style="font-size:13px;color:#CCCCCC;">AI-detected trends personalised to your numbers</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="width:18px;height:18px;border-radius:50%;background:rgba(0,200,150,0.15);border:1px solid rgba(0,200,150,0.35);display:flex;align-items:center;justify-content:center;font-size:10px;color:#00C896;flex-shrink:0;">&#10003;</span>
          <span style="font-size:13px;color:#CCCCCC;">Connected to 50,000+ peer-reviewed PubMed papers</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="width:18px;height:18px;border-radius:50%;background:rgba(0,200,150,0.15);border:1px solid rgba(0,200,150,0.35);display:flex;align-items:center;justify-content:center;font-size:10px;color:#00C896;flex-shrink:0;">&#10003;</span>
          <span style="font-size:13px;color:#CCCCCC;">Speculation slider — you control the evidence standards</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="width:18px;height:18px;border-radius:50%;background:rgba(0,200,150,0.15);border:1px solid rgba(0,200,150,0.35);display:flex;align-items:center;justify-content:center;font-size:10px;color:#00C896;flex-shrink:0;">&#10003;</span>
          <span style="font-size:13px;color:#CCCCCC;">Research mode included — free to explore without Oura</span>
        </div>
      </div>
    </div>
    <div style="margin-bottom:16px;">
      <a href="{auth_url}" target="_self" class="lp-cta" style="width:100%;box-sizing:border-box;justify-content:center;" data-track="pricing-cta">
        <span class="shimmer"></span>
        <span style="position:relative;z-index:1;">Start for free &mdash; upgrade when ready &#8594;</span>
      </a>
    </div>
    <p style="font-size:12px;color:#444444;margin:0;">Cancel anytime &middot; No contracts &middot; Your data stays yours</p>
  </div>
</div>

<!-- ── FINAL CTA ── -->
<div style="padding:80px 40px;text-align:center;border-top:1px solid rgba(255,255,255,0.04);">
  <h2 style="font-size:clamp(24px,3.5vw,40px);font-weight:700;color:#F0F0F0;letter-spacing:-0.8px;margin:0 0 12px;">
    Stop looking at numbers.<br>Start understanding them.
  </h2>
  <p style="font-size:15px;color:#555555;margin:0 0 36px;">Your data has been collecting since you first wore your ring. It&rsquo;s waiting to be analysed.</p>
  <a href="{auth_url}" target="_self" class="lp-cta" data-track="final-cta">
    <span class="shimmer"></span>
    <span style="position:relative;z-index:1;">Connect your Oura Ring &#8594;</span>
  </a>
  <p style="font-size:12px;color:#333333;margin:16px 0 0;">No credit card required &middot; Read-only access &middot; Disconnect anytime</p>
</div>

</div>
""", unsafe_allow_html=True)
    render_footer()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: HOMEPAGE
# ══════════════════════════════════════════════════════════════════════════════
def render_homepage(search_query: str):
    mode = st.session_state.mode

    if mode == "personal" and not connected:
        st.markdown(f"""
        <div style="padding:80px 40px;text-align:center;max-width:480px;margin:0 auto;">
            <div style="width:48px;height:48px;border-radius:50%;
                        background:linear-gradient(135deg,#7C6AF7,#00C896);
                        margin:0 auto 24px;display:flex;align-items:center;
                        justify-content:center;font-size:20px;">&#9679;</div>
            <h2 style="font-size:20px;font-weight:600;color:#F0F0F0;
                       letter-spacing:-0.3px;margin:0 0 12px;">Connect your Oura Ring</h2>
            <p style="font-size:15px;color:#888888;line-height:1.7;margin:0 0 32px;">
                Your Data mode surfaces insights from your actual biometric patterns.
                Connect your ring to get started.
            </p>
            <a href="{get_auth_url()}" target="_self"
               style="display:inline-block;background:#7C6AF7;color:#fff;
                      font-size:14px;font-weight:600;text-decoration:none;
                      border-radius:8px;padding:12px 28px;transition:opacity 0.2s ease;"
               onmouseover="this.style.opacity='0.88'"
               onmouseout="this.style.opacity='1'">
                Connect Oura Ring
            </a>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Grid label ────────────────────────────────────────────────────────────
    grid_label = "Recommended for you" if mode == "personal" else "Explore topics"
    ev_type, _ = get_evidence_label(spec_val)

    st.markdown(
        f'<div style="padding:12px 40px 8px;">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">'
        f'<div style="width:3px;height:10px;border-radius:2px;background:#7C6AF7;flex-shrink:0;"></div>'
        f'<span style="font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:#555555;">{grid_label}</span>'
        f'</div>'
        f'<p style="font-size:16px;font-weight:600;color:#F0F0F0;letter-spacing:-0.3px;margin:0;">{ev_type}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Personal Data mode ────────────────────────────────────────────────────
    if mode == "personal":
        # Subscription gate — research mode is always free
        if not st.session_state.get("is_paid", False):
            render_paywall_teaser()
            render_footer()
            return

        rows      = get_oura_data(user_id)
        baselines = get_user_baselines(user_id)
        stats     = get_history_stats(user_id)
        render_metrics_strip(rows, baselines, stats)

        latest = next((r for r in rows if r.get("total_sleep_duration")), rows[0] if rows else None)

        # Trends cards
        st.markdown('<div class="pulse-analyse">', unsafe_allow_html=True)
        if st.button("Analyse my data"):
            with st.spinner("Analysing your biometric patterns…"):
                try:
                    trends = detect_trends(get_oura_data(user_id))
                    for t in trends:
                        slug = t.get("headline", "")[:30].lower().replace(" ", "-")
                        t["slug"] = slug
                    st.session_state["trends"] = trends
                except Exception as e:
                    st.error(f"Analysis failed: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

        trends = st.session_state.get("trends", [])
        if trends:
            _trend_cards = []
            for t in trends:
                conf = t.get("confidence", "medium")
                _slug = t.get("slug", t.get("headline", "")[:30].lower().replace(" ", "-"))
                _trend_cards.append({
                    "slug": _slug,
                    "headline": t.get("headline", ""),
                    "description": t.get("description", ""),
                    "relevancy": 85 if conf == "high" else 55 if conf == "medium" else 30,
                    "papers": len(t.get("metrics_involved", [])) * 4,
                    "indirect": len(t.get("metrics_involved", [])) * 9,
                })
            _render_card_grid(_trend_cards, mode="personal", spec_val=spec_val, zone=0)
        elif not latest:
            st.markdown(
                '<div style="padding:48px 40px;text-align:center;">'
                '<p style="font-size:32px;margin:0 0 16px;">&#128280;</p>'
                '<p style="font-size:16px;font-weight:600;color:#F0F0F0;margin:0 0 8px;">No data yet</p>'
                '<p style="font-size:14px;color:#555555;margin:0 0 24px;">Sync your Oura Ring to pull your full history.</p>'
                '<a href="?action=sync" target="_self" style="display:inline-block;background:#111111;'
                'border:1px solid rgba(255,255,255,0.12);border-radius:8px;padding:10px 24px;'
                'font-size:13px;font-weight:500;color:#F0F0F0;text-decoration:none;">&#128260; Sync Ring</a>'
                '</div>',
                unsafe_allow_html=True,
            )

    # ── Research mode ─────────────────────────────────────────────────────────
    else:
        # Pick topic zone from slider (0–9)
        zone = min(9, spec_val)
        topics = list(TOPIC_ZONES.get(zone, []))

        # Filter by search query
        if search_query.strip():
            sq = search_query.lower()
            topics = [t for t in topics
                      if sq in t["headline"].lower() or sq in t["description"].lower()]

        if topics:
            _render_card_grid(topics, mode="research", spec_val=spec_val, zone=zone)
        else:
            st.markdown("""
            <div style="padding:48px 40px;text-align:center;">
                <p style="color:#333333;font-size:14px;">
                    No results for that search in this zone — try adjusting the slider or a different term.
                </p>
            </div>""", unsafe_allow_html=True)

        # PubMed results below topic grid
        q = search_query.strip() if search_query.strip() else DEFAULT_QUERY
        with st.spinner(""):
            articles = search_pubmed(q, slider_value=spec_val, max_results=9)
        if articles:
            st.markdown(
                '<div style="padding:4px 40px 4px;">'
                '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
                '<div style="width:3px;height:12px;border-radius:2px;background:#7C6AF7;flex-shrink:0;"></div>'
                '<span style="font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:#555555;">PubMed Results</span>'
                '</div></div>',
                unsafe_allow_html=True,
            )
            html = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:0 40px 16px;">'
            for a in articles[:9]:
                html += paper_card_html(a, mode="research")
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

    render_footer()


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED: FOOTER
# ══════════════════════════════════════════════════════════════════════════════
def render_footer():
    st.markdown(
        '<div style="margin-top:24px;padding:28px 40px;border-top:1px solid rgba(255,255,255,0.06);'
        'background:#080808;">'

        '<div style="display:flex;justify-content:space-between;align-items:flex-start;'
        'flex-wrap:wrap;gap:24px;max-width:1100px;margin:0 auto 20px;">'

        # Brand + tagline
        '<div style="max-width:280px;">'
        '<span style="font-size:18px;font-weight:700;color:#FFFFFF;letter-spacing:-0.5px;">Pulse</span>'
        '<p style="font-size:13px;color:#555555;line-height:1.6;margin:10px 0 0;">'
        'Personal health intelligence powered by your Oura Ring. '
        'AI-detected trends linked to peer-reviewed science.</p>'
        '</div>'

        # Links
        '<div style="display:flex;gap:48px;flex-wrap:wrap;">'

        '<div>'
        '<p style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;'
        'color:#444444;margin:0 0 12px;">Product</p>'
        '<div style="display:flex;flex-direction:column;gap:8px;">'
        '<a href="?page=pricing" target="_self" style="font-size:13px;color:#666666;text-decoration:none;" '
        'onmouseover="this.style.color=\'#F0F0F0\'" onmouseout="this.style.color=\'#666666\'">Pricing</a>'
        '<a href="?mode=research" target="_self" style="font-size:13px;color:#666666;text-decoration:none;" '
        'onmouseover="this.style.color=\'#F0F0F0\'" onmouseout="this.style.color=\'#666666\'">Research Mode</a>'
        '<a href="?mode=connect" target="_self" style="font-size:13px;color:#666666;text-decoration:none;" '
        'onmouseover="this.style.color=\'#F0F0F0\'" onmouseout="this.style.color=\'#666666\'">Connect Oura Ring</a>'
        '</div></div>'

        '<div>'
        '<p style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;'
        'color:#444444;margin:0 0 12px;">Legal</p>'
        '<div style="display:flex;flex-direction:column;gap:8px;">'
        '<a href="?page=privacy" target="_self" style="font-size:13px;color:#666666;text-decoration:none;" '
        'onmouseover="this.style.color=\'#F0F0F0\'" onmouseout="this.style.color=\'#666666\'">Privacy Policy</a>'
        '<a href="?page=terms" target="_self" style="font-size:13px;color:#666666;text-decoration:none;" '
        'onmouseover="this.style.color=\'#F0F0F0\'" onmouseout="this.style.color=\'#666666\'">Terms of Service</a>'
        '</div></div>'

        '<div>'
        '<p style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;'
        'color:#444444;margin:0 0 12px;">Support</p>'
        '<div style="display:flex;flex-direction:column;gap:8px;">'
        '<a href="mailto:boazbook2@gmail.com" style="font-size:13px;color:#666666;text-decoration:none;" '
        'onmouseover="this.style.color=\'#F0F0F0\'" onmouseout="this.style.color=\'#666666\'">Contact Us</a>'
        '</div></div>'

        '</div>'  # end links
        '</div>'  # end top row

        # Bottom bar
        '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;'
        'max-width:1100px;margin:0 auto;padding-top:24px;border-top:1px solid rgba(255,255,255,0.04);">'
        '<p style="font-size:12px;color:#333333;margin:0;">&#169; 2026 Pulse. All rights reserved.</p>'
        '<p style="font-size:12px;color:#333333;margin:0;">'
        'Not medical advice &nbsp;&middot;&nbsp; Research from PubMed / NCBI &nbsp;&middot;&nbsp; '
        'Always consult a healthcare professional</p>'
        '</div>'

        '</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: PRIVACY POLICY
# ══════════════════════════════════════════════════════════════════════════════
def render_privacy_page():
    st.markdown(
        '<div style="min-height:100vh;background:#080808;font-family:\'Plus Jakarta Sans\',sans-serif;">'
        '<div style="height:64px;display:flex;align-items:center;justify-content:center;'
        'padding:0 40px;border-bottom:1px solid rgba(255,255,255,0.06);background:#080808;">'
        '<span style="font-size:20px;font-weight:700;color:#FFFFFF;letter-spacing:-0.5px;">Pulse</span>'
        '</div>'
        '<div style="padding:12px 40px 0;">'
        '<a href="?back=1" target="_self" style="font-size:13px;color:#F0F0F0;text-decoration:none;opacity:0.6;transition:opacity 0.2s;" '
        'onmouseover="this.style.opacity=\'1\'" onmouseout="this.style.opacity=\'0.6\'">&#8592; Back</a>'
        '</div>'
        '<div style="max-width:720px;margin:0 auto;padding:24px 24px 48px;">'
        '<h1 style="font-size:32px;font-weight:700;color:#F0F0F0;letter-spacing:-0.5px;margin:0 0 8px;">Privacy Policy</h1>'
        '<p style="font-size:13px;color:#555555;margin:0 0 40px;">Last updated: April 2026</p>'

        '<h2 style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 10px;">What data we collect</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.8;margin:0 0 28px;">'
        'We collect your email address and, with your explicit authorisation via Oura OAuth 2.0, '
        'the following Oura Ring biometric data: sleep scores and durations, readiness scores, '
        'activity scores and steps, heart rate and HRV, SpO2, stress and resilience metrics, '
        'skin temperature, and cardiovascular age estimates. We also store your subscription status. '
        'We never collect passwords.</p>'

        '<h2 style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 10px;">How we use your data</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.8;margin:0 0 28px;">'
        'Your biometric data is used exclusively to: (1) detect personal health trends using the '
        'Groq API (Llama 3.3 large language model), and (2) retrieve relevant scientific papers '
        'from the PubMed / NCBI database to contextualise those trends. '
        'Your raw metrics are sent to Groq\'s API for analysis. Groq\'s privacy policy governs '
        'that processing. We never sell your data or use it for advertising.</p>'

        '<h2 style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 10px;">Data storage and retention</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.8;margin:0 0 28px;">'
        'Your data is stored in Supabase (PostgreSQL) hosted on AWS, with encryption at rest and in transit. '
        'Oura OAuth tokens are stored securely and never logged or exposed in the UI. '
        'We retain your biometric data for as long as your account is active. '
        'You may request complete deletion of your data at any time by emailing us — '
        'we will delete all records within 30 days.</p>'

        '<h2 style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 10px;">Oura data access</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.8;margin:0 0 28px;">'
        'Access to your Oura Ring data is granted only through Oura\'s official OAuth 2.0 flow. '
        'You may revoke Pulse\'s access at any time from the Oura app under Settings → Connected Apps. '
        'Revoking access stops all future data sync. To also delete historical data, contact us.</p>'

        '<h2 style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 10px;">Third-party services</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.8;margin:0 0 28px;">'
        'Pulse uses: <b style="color:#CCCCCC;">Oura API</b> (biometric data source), '
        '<b style="color:#CCCCCC;">Groq / Llama</b> (AI trend analysis), '
        '<b style="color:#CCCCCC;">PubMed / NCBI</b> (research paper retrieval), '
        '<b style="color:#CCCCCC;">Stripe</b> (payment processing — no card data stored by us), '
        '<b style="color:#CCCCCC;">Supabase</b> (database). Each has its own privacy policy.</p>'

        '<h2 style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 10px;">Medical disclaimer</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.8;margin:0 0 28px;">'
        'Pulse is not a medical device, is not FDA-cleared, and does not provide medical advice, '
        'diagnosis, or treatment recommendations. AI-generated trend summaries and research links '
        'are for informational and educational purposes only and do not constitute clinical guidance. '
        'Never disregard professional medical advice or delay seeking it based on content from Pulse. '
        'Always consult a qualified healthcare professional for medical decisions.</p>'

        '<h2 style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 10px;">Your rights</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.8;margin:0 0 28px;">'
        'You have the right to access, correct, export, or delete your personal data. '
        'To exercise any of these rights, email us at the address below and we will respond within 30 days.</p>'

        '<h2 style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 10px;">Contact</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.8;margin:0;">'
        'Privacy questions or data requests: <a href="mailto:boazbook2@gmail.com" '
        'style="color:#00C896;text-decoration:none;">boazbook2@gmail.com</a></p>'

        '</div></div>',
        unsafe_allow_html=True,
    )
    render_footer()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: TERMS OF SERVICE
# ══════════════════════════════════════════════════════════════════════════════
def render_terms_page():
    st.markdown(
        '<div style="min-height:100vh;background:#080808;font-family:\'Plus Jakarta Sans\',sans-serif;">'
        '<div style="height:64px;display:flex;align-items:center;justify-content:center;'
        'padding:0 40px;border-bottom:1px solid rgba(255,255,255,0.06);background:#080808;">'
        '<span style="font-size:20px;font-weight:700;color:#FFFFFF;letter-spacing:-0.5px;">Pulse</span>'
        '</div>'
        '<div style="padding:12px 40px 0;">'
        '<a href="?back=1" target="_self" style="font-size:13px;color:#F0F0F0;text-decoration:none;opacity:0.6;transition:opacity 0.2s;" '
        'onmouseover="this.style.opacity=\'1\'" onmouseout="this.style.opacity=\'0.6\'">&#8592; Back</a>'
        '</div>'
        '<div style="max-width:720px;margin:0 auto;padding:24px 24px;">'
        '<h1 style="font-size:32px;font-weight:700;color:#F0F0F0;letter-spacing:-0.5px;margin:0 0 8px;">Terms of Service</h1>'
        '<p style="font-size:13px;color:#555555;margin:0 0 48px;">Last updated: April 2026</p>'

        '<h2 style="font-size:16px;font-weight:600;color:#F0F0F0;margin:0 0 12px;">Acceptance</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.8;margin:0 0 32px;">'
        'By using Pulse, you agree to these terms. If you do not agree, do not use the service.</p>'

        '<h2 style="font-size:16px;font-weight:600;color:#F0F0F0;margin:0 0 12px;">Service description</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.8;margin:0 0 32px;">'
        'Pulse is a personal health intelligence platform that connects to Oura Ring data and provides '
        'AI-generated trend analysis linked to scientific research. It is not a medical service.</p>'

        '<h2 style="font-size:16px;font-weight:600;color:#F0F0F0;margin:0 0 12px;">Subscription & billing</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.8;margin:0 0 32px;">'
        'Pulse is billed at $25/month. You may cancel at any time. '
        'Cancellations take effect at the end of the current billing period. '
        'No refunds are issued for partial months.</p>'

        '<h2 style="font-size:16px;font-weight:600;color:#F0F0F0;margin:0 0 12px;">No medical advice</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.8;margin:0 0 32px;">'
        'Nothing on Pulse constitutes medical advice, diagnosis, or treatment. '
        'Research summaries are AI-generated and for informational purposes only. '
        'You are solely responsible for decisions made based on information from this service.</p>'

        '<h2 style="font-size:16px;font-weight:600;color:#F0F0F0;margin:0 0 12px;">Limitation of liability</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.8;margin:0 0 32px;">'
        'Pulse is provided "as is". We are not liable for any damages arising from use of the service, '
        'inaccuracies in AI-generated content, or decisions made based on information provided.</p>'

        '<h2 style="font-size:16px;font-weight:600;color:#F0F0F0;margin:0 0 12px;">Contact</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.8;margin:0;">'
        'Questions: <a href="mailto:boazbook2@gmail.com" '
        'style="color:#00C896;text-decoration:none;">boazbook2@gmail.com</a></p>'

        '</div></div>',
        unsafe_allow_html=True,
    )
    render_footer()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: PRICING
# ══════════════════════════════════════════════════════════════════════════════
def render_pricing_page():
    # Pre-generate Stripe checkout URL so we can use a plain <a> link
    _checkout_error = ""
    _cta_href = ""
    try:
        from stripe_handler import create_checkout_session
        _cta_href = create_checkout_session(st.session_state.get("email", ""))
    except Exception as _e:
        _checkout_error = str(_e)

    _error_html = (
        f'<p style="font-size:12px;color:#E05050;text-align:center;margin:12px 0 0;max-width:420px;">Stripe error: {_checkout_error}</p>'
        if _checkout_error else ""
    )

    st.markdown(
        '<style>'
        '@keyframes glow-pulse{'
        '0%,100%{box-shadow:0 0 0 1px rgba(0,200,150,0.4),0 0 32px rgba(0,200,150,0.28),0 0 64px rgba(124,106,247,0.14);}'
        '50%{box-shadow:0 0 0 1px rgba(124,106,247,0.5),0 0 48px rgba(124,106,247,0.32),0 0 96px rgba(0,200,150,0.16);}'
        '}'
        '@keyframes shimmer-slide{'
        '0%{left:-60%;}100%{left:120%;}'
        '}'
        '.pulse-cta-link{'
        'display:block;text-align:center;text-decoration:none !important;'
        'background:linear-gradient(135deg,#00C896 0%,#7C6AF7 100%);'
        'color:#FFFFFF !important;font-size:16px;font-weight:700;letter-spacing:-0.2px;'
        'border-radius:12px;padding:17px 32px;position:relative;overflow:hidden;'
        'animation:glow-pulse 3s ease-in-out infinite;'
        'transition:opacity 0.2s ease,transform 0.2s ease;'
        '}'
        '.pulse-cta-link:hover{opacity:0.92;transform:translateY(-2px);}'
        '.pulse-cta-link .shimmer{'
        'position:absolute;top:0;left:-60%;width:40%;height:100%;'
        'background:linear-gradient(90deg,transparent,rgba(255,255,255,0.22),transparent);'
        'animation:shimmer-slide 2.4s ease-in-out infinite;pointer-events:none;'
        '}'
        '</style>'

        '<div style="background:#080808;">'
        # Navbar — logo only, centered
        '<div style="height:64px;display:flex;align-items:center;justify-content:center;'
        'padding:0 40px;border-bottom:1px solid rgba(255,255,255,0.06);background:#080808;">'
        '<span class="pulse-logo" style="font-size:20px;font-weight:700;color:#FFFFFF;letter-spacing:-0.5px;">Pulse</span>'
        '</div>'
        # Back arrow below navbar
        '<div style="padding:12px 40px 0;">'
        '<a href="?back=1" target="_self" style="font-size:13px;color:#F0F0F0;text-decoration:none;opacity:0.6;transition:opacity 0.2s;" '
        'onmouseover="this.style.opacity=\'1\'" onmouseout="this.style.opacity=\'0.6\'">&#8592; Back</a>'
        '</div>'

        # Content
        '<div style="display:flex;flex-direction:column;align-items:center;padding:28px 24px 36px;text-align:center;">'
        '<p style="font-size:11px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:#7C6AF7;margin:0 0 14px;">Health Intelligence</p>'
        '<h1 style="font-size:clamp(24px,3.5vw,36px);font-weight:700;color:#F0F0F0;letter-spacing:-0.6px;line-height:1.2;margin:0 0 10px;">Unlock Pulse</h1>'
        '<p style="font-size:14px;color:#888888;line-height:1.6;max-width:420px;margin:0 0 32px;">'
        'AI-powered insights from your full Oura history — linked to peer-reviewed research.</p>'

        # Pricing card
        '<div style="background:#111111;border:1px solid rgba(255,255,255,0.08);border-radius:16px;'
        'padding:28px 32px;max-width:420px;width:100%;text-align:left;margin-bottom:28px;">'
        '<div style="display:flex;align-items:baseline;gap:6px;margin-bottom:16px;">'
        '<span style="font-family:\'JetBrains Mono\',monospace;font-size:42px;font-weight:600;color:#F0F0F0;letter-spacing:-2px;line-height:1;">$25</span>'
        '<span style="font-size:13px;color:#555555;">/ month</span>'
        '</div>'
        '<div style="height:1px;background:rgba(255,255,255,0.06);margin-bottom:16px;"></div>'
        '<div style="display:flex;flex-direction:column;gap:10px;">'
        '<div style="display:flex;align-items:center;gap:10px;">'
        '<span style="width:18px;height:18px;border-radius:50%;background:rgba(0,200,150,0.15);border:1px solid rgba(0,200,150,0.35);display:flex;align-items:center;justify-content:center;font-size:10px;color:#00C896;flex-shrink:0;">&#10003;</span>'
        '<span style="font-size:13px;color:#CCCCCC;">AI trend detection from your full history</span></div>'
        '<div style="display:flex;align-items:center;gap:10px;">'
        '<span style="width:18px;height:18px;border-radius:50%;background:rgba(0,200,150,0.15);border:1px solid rgba(0,200,150,0.35);display:flex;align-items:center;justify-content:center;font-size:10px;color:#00C896;flex-shrink:0;">&#10003;</span>'
        '<span style="font-size:13px;color:#CCCCCC;">PubMed research links for every insight</span></div>'
        '<div style="display:flex;align-items:center;gap:10px;">'
        '<span style="width:18px;height:18px;border-radius:50%;background:rgba(0,200,150,0.15);border:1px solid rgba(0,200,150,0.35);display:flex;align-items:center;justify-content:center;font-size:10px;color:#00C896;flex-shrink:0;">&#10003;</span>'
        '<span style="font-size:13px;color:#CCCCCC;">Personal baseline comparison & metrics</span></div>'
        '</div></div>'

        # Glowing CTA button
        f'<div style="max-width:420px;width:100%;margin-bottom:12px;">'
        + (
            f'<a href="{_cta_href}" target="_self" class="pulse-cta-link">'
            '<span class="shimmer"></span>'
            '<span style="position:relative;z-index:1;">Get Started &nbsp;&#8594;</span>'
            '</a>'
            if _cta_href else
            '<div class="pulse-cta-link" style="opacity:0.5;cursor:default;">'
            '<span style="position:relative;z-index:1;">Checkout unavailable — check back soon</span>'
            '</div>'
        ) +
        '</div>'
        f'{_error_html}'
        '<p style="font-size:11px;color:#333333;margin:12px 0 0;">Cancel anytime &nbsp;&middot;&nbsp; Secure checkout via Stripe</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    render_footer()


def render_paywall_teaser():
    """Shown inside personal mode when user has no active subscription."""
    _stats = get_history_stats(st.session_state.get("user_id", ""))
    _days = _stats.get("total_days", 0)
    _since = _stats.get("earliest_date", "")
    _since_str = f" since {_since}" if _since else ""
    _days_str = f"{_days} days of data{_since_str}" if _days else "your full history"

    st.markdown(
        '<div style="padding:40px 40px;display:flex;flex-direction:column;align-items:center;">'
        '<div style="background:#111111;border:1px solid rgba(0,200,150,0.2);border-radius:16px;'
        'padding:36px;max-width:480px;width:100%;text-align:center;margin-bottom:20px;'
        'box-shadow:0 0 0 1px rgba(0,200,150,0.08),0 0 40px rgba(0,200,150,0.04);">'
        '<p style="font-size:13px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;'
        'color:#00C896;margin:0 0 12px;">Your data is ready to analyse</p>'
        f'<h2 style="font-size:20px;font-weight:700;color:#F0F0F0;letter-spacing:-0.4px;margin:0 0 10px;">'
        f'You&rsquo;re leaving {_days_str}<br>unanalysed.</h2>'
        '<p style="font-size:14px;color:#888888;line-height:1.65;margin:0 0 20px;">'
        'Longevity clinics charge $5,000/year for this level of insight. '
        'Pulse surfaces AI-detected trends from your full Oura history — linked to peer-reviewed science.</p>'
        '<div style="display:flex;justify-content:center;gap:20px;margin-bottom:0;">'
        '<div style="text-align:center;">'
        '<p style="font-family:\'JetBrains Mono\',monospace;font-size:24px;font-weight:600;color:#F0F0F0;margin:0;">50k+</p>'
        '<p style="font-size:11px;color:#555555;margin:2px 0 0;">PubMed papers</p>'
        '</div>'
        '<div style="width:1px;background:rgba(255,255,255,0.06);"></div>'
        '<div style="text-align:center;">'
        f'<p style="font-family:\'JetBrains Mono\',monospace;font-size:24px;font-weight:600;color:#F0F0F0;margin:0;">{_days or "—"}</p>'
        '<p style="font-size:11px;color:#555555;margin:2px 0 0;">days tracked</p>'
        '</div>'
        '<div style="width:1px;background:rgba(255,255,255,0.06);"></div>'
        '<div style="text-align:center;">'
        '<p style="font-family:\'JetBrains Mono\',monospace;font-size:24px;font-weight:600;color:#F0F0F0;margin:0;">14</p>'
        '<p style="font-size:11px;color:#555555;margin:2px 0 0;">metrics analysed</p>'
        '</div>'
        '</div>'
        '</div>'
        '<div style="max-width:480px;width:100%;">'
        '<a href="?page=pricing" target="_self" class="pulse-cta-link" data-track="paywall-cta">'
        '<span class="shimmer"></span>'
        '<span style="position:relative;z-index:1;">Unlock my personal insights &nbsp;&mdash;&nbsp; $25/month &nbsp;&#8594;</span>'
        '</a>'
        '<p style="font-size:12px;color:#444444;text-align:center;margin:10px 0 0;">'
        'Cancel anytime &middot; No contracts &middot; Your data stays yours</p>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: CONNECT (Benefits landing page)
# ══════════════════════════════════════════════════════════════════════════════
def render_connect_page():
    auth_url = get_auth_url()
    html = (
        '<div style="min-height:100vh;background:#080808;font-family:\'Plus Jakarta Sans\',sans-serif;">'

        # ── Navbar — logo only, centered ──
        '<div style="height:64px;display:flex;align-items:center;justify-content:center;'
        'padding:0 40px;border-bottom:1px solid rgba(255,255,255,0.06);'
        'background:#080808;position:sticky;top:0;z-index:500;">'
        '<span class="pulse-logo" style="font-size:20px;font-weight:700;color:#FFFFFF;letter-spacing:-0.5px;">Pulse</span>'
        '</div>'
        # Back arrow below navbar
        '<div style="padding:12px 40px 0;">'
        '<a href="?back=1" target="_self" style="font-size:13px;color:#F0F0F0;text-decoration:none;opacity:0.6;transition:opacity 0.2s;" '
        'onmouseover="this.style.opacity=\'1\'" onmouseout="this.style.opacity=\'0.6\'">&#8592; Back</a>'
        '</div>'

        # ── Hero ──
        '<div style="display:flex;flex-direction:column;align-items:center;'
        'justify-content:center;padding:28px 24px 36px;text-align:center;">'

        '<p style="font-size:11px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;'
        'color:#00C896;margin:0 0 18px;">Personal Health Intelligence</p>'

        '<h1 style="font-size:clamp(28px,4.5vw,46px);font-weight:700;color:#F0F0F0;'
        'letter-spacing:-1px;line-height:1.15;margin:0 0 16px;max-width:640px;">'
        'Connect your biology<br>to the science behind it</h1>'

        '<p style="font-size:16px;color:#888888;line-height:1.65;max-width:500px;margin:0 0 40px;">'
        'Pulse pulls your Oura Ring biometrics, detects patterns in your data, '
        'and links them to peer-reviewed research — so you understand not just '
        'what your body is doing, but why.</p>'

        # ── Benefits grid ──
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;'
        'max-width:800px;width:100%;margin-bottom:40px;text-align:left;">'

        '<div style="background:#111111;border:1px solid rgba(255,255,255,0.06);'
        'border-radius:12px;padding:24px;'
        'box-shadow:0 0 0 1px rgba(0,200,150,0.15),0 0 24px rgba(0,200,150,0.04);">'
        '<div style="width:36px;height:36px;border-radius:8px;'
        'background:rgba(0,200,150,0.10);border:1px solid rgba(0,200,150,0.20);'
        'display:flex;align-items:center;justify-content:center;margin-bottom:16px;font-size:18px;">&#128200;</div>'
        '<p style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 8px;">Pattern detection</p>'
        '<p style="font-size:13px;color:#888888;line-height:1.6;margin:0;">'
        'AI analyses 30 days of your biometric data to surface genuine trends — not generic tips.</p>'
        '</div>'

        '<div style="background:#111111;border:1px solid rgba(255,255,255,0.06);'
        'border-radius:12px;padding:24px;'
        'box-shadow:0 0 0 1px rgba(124,106,247,0.15),0 0 24px rgba(124,106,247,0.04);">'
        '<div style="width:36px;height:36px;border-radius:8px;'
        'background:rgba(124,106,247,0.10);border:1px solid rgba(124,106,247,0.20);'
        'display:flex;align-items:center;justify-content:center;margin-bottom:16px;font-size:18px;">&#128203;</div>'
        '<p style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 8px;">Research links</p>'
        '<p style="font-size:13px;color:#888888;line-height:1.6;margin:0;">'
        'Every insight is backed by PubMed papers. You control how speculative vs. evidence-based the results are.</p>'
        '</div>'

        '<div style="background:#111111;border:1px solid rgba(255,255,255,0.06);'
        'border-radius:12px;padding:24px;'
        'box-shadow:0 0 0 1px rgba(240,192,64,0.15),0 0 24px rgba(240,192,64,0.04);">'
        '<div style="width:36px;height:36px;border-radius:8px;'
        'background:rgba(240,192,64,0.10);border:1px solid rgba(240,192,64,0.20);'
        'display:flex;align-items:center;justify-content:center;margin-bottom:16px;font-size:18px;">&#127919;</div>'
        '<p style="font-size:15px;font-weight:600;color:#F0F0F0;margin:0 0 8px;">Personal context</p>'
        '<p style="font-size:13px;color:#888888;line-height:1.6;margin:0;">'
        'Papers are annotated with a one-sentence connection to your specific numbers — not abstract science.</p>'
        '</div>'

        '</div>'  # end grid

        # ── CTA ──
        '<a href="' + auth_url + '" target="_self" '
        'style="display:inline-flex;align-items:center;gap:10px;'
        'background:#F0F0F0;color:#080808;font-size:15px;font-weight:600;'
        'text-decoration:none;border-radius:10px;padding:14px 32px;'
        'transition:all 0.2s ease;letter-spacing:-0.2px;'
        'box-shadow:0 0 0 1px rgba(255,255,255,0.1),0 4px 24px rgba(255,255,255,0.10);" '
        'onmouseover="this.style.transform=\'translateY(-2px)\';this.style.opacity=\'0.92\'" '
        'onmouseout="this.style.transform=\'translateY(0)\';this.style.opacity=\'1\'">'
        'Connect Oura Ring &#8594;</a>'

        '<p style="font-size:12px;color:#444444;margin:20px 0 0;">'
        'Secure OAuth 2.0 &nbsp;&middot;&nbsp; No passwords stored &nbsp;&middot;&nbsp; Revoke anytime from Oura app</p>'

        '</div>'  # end hero

        '</div>'  # end outer
    )
    st.markdown(html, unsafe_allow_html=True)
    render_footer()


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════════════════════
# ── Handle action params ──────────────────────────────────────────────────────
_action = params.get("action", "")

if _action == "signout":
    for _k in ["connected", "user_name", "user_id", "access_token", "email",
               "trends", "nav_page", "is_paid", "just_connected"]:
        st.session_state.pop(_k, None)
    st.query_params.clear()
    st.rerun()

elif _action == "sync" and connected:
    with st.spinner("Syncing Oura data…"):
        try:
            _data = fetch_all_oura_data(access_token)
            for _day, _m in _data.items():
                save_oura_data(user_id, _day, _m)
            st.success(f"Synced {len(_data)} days of data.")
        except Exception as _e:
            st.error(f"Sync failed: {_e}")
    st.query_params.clear()

# Handle back button from any page
if params.get("back") == "1":
    st.session_state.pop("nav_page", None)
    st.session_state.pop("modal_slug", None)
    st.session_state.pop("modal_mode", None)
    st.query_params.clear()
    st.rerun()

# Handle mode switch from tab clicks
_mode_param = params.get("mode", "")
if _mode_param == "research":
    st.session_state.mode = "research"
    st.session_state.pop("nav_page", None)
    st.session_state.pop("show_more_topics", None)
    st.query_params.clear()
    st.rerun()
elif _mode_param == "personal":
    if connected:
        st.session_state.mode = "personal"
        st.session_state.pop("nav_page", None)
    else:
        st.session_state["nav_page"] = "connect"
    st.query_params.clear()
    st.rerun()
elif _mode_param == "connect":
    st.session_state["nav_page"] = "connect"
    st.query_params.clear()
    st.rerun()

nav_page   = st.session_state.get("nav_page", "")
route_page = params.get("page", "")

# Handle Stripe Payment Link redirect (?session_id=xxx)
if "session_id" in params:
    try:
        from stripe_handler import verify_session
        _result = verify_session(params["session_id"])
        if _result:
            set_paid(_result["email"], _result.get("subscription_id", ""))
            st.session_state["is_paid"] = True
            st.success("Payment confirmed. Welcome to Pulse!")
    except Exception as _e:
        st.error(f"Payment verification failed: {_e}")
    st.query_params.clear()
    st.rerun()

# Modal via session state (primary — no URL params needed)
_modal_slug = st.session_state.get("modal_slug", "")
_modal_mode = st.session_state.get("modal_mode", "research")

if st.session_state.get("just_connected"):
    render_connect_success()

elif nav_page == "pricing" or route_page == "pricing":
    render_pricing_page()

elif route_page == "privacy":
    render_privacy_page()

elif route_page == "terms":
    render_terms_page()

elif nav_page == "connect" or route_page == "connect":
    render_connect_page()

elif _modal_slug:
    render_modal(_modal_slug, mode=_modal_mode)

else:
    if not connected:
        render_landing_page()
    else:
        search_query = render_navbar()
        # Persistent free-tier upgrade banner (disappears once paid)
        if not st.session_state.get("is_paid", False):
            st.markdown(
                '<div style="background:rgba(0,200,150,0.06);border-bottom:1px solid rgba(0,200,150,0.15);'
                'padding:8px 40px;display:flex;align-items:center;justify-content:space-between;gap:16px;" '
                'data-track="upgrade-banner">'
                '<p style="font-size:13px;color:#888888;margin:0;">'
                '&#128300; You&rsquo;re viewing research insights. '
                '<span style="color:#00C896;">Connect payment to unlock your personal Oura analysis.</span></p>'
                '<a href="?page=pricing" target="_self" '
                'style="font-size:12px;font-weight:600;color:#080808;background:#00C896;'
                'text-decoration:none;border-radius:6px;padding:5px 14px;white-space:nowrap;'
                'transition:opacity 0.2s;" onmouseover="this.style.opacity=\'0.85\'" onmouseout="this.style.opacity=\'1\'">'
                'Upgrade $25/month</a>'
                '</div>',
                unsafe_allow_html=True,
            )
        render_mode_toggle()
        spec_val = render_slider()
        render_homepage(search_query)
