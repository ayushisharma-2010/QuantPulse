# =============================================================================
# ENVIRONMENT SETUP — Must execute BEFORE any other imports
# =============================================================================
import os
import time
import logging
import traceback

# ---- Disable CrewAI / OpenTelemetry telemetry (prints "Menu", may hang) ----
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

# ---- LiteLLM Optimization: Prevent slow remote fetch of cost map ----
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

from dotenv import load_dotenv
load_dotenv()

# NOTE: crewai imports are DEFERRED to _execute_crew() to avoid blocking
# uvicorn port binding on Render. CrewAI pulls in chromadb, litellm,
# opentelemetry (300+ deps) which takes 30-60s to import.

logger = logging.getLogger(__name__)

# =============================================================================
# Validate API Keys at import time — warn if missing, don't crash
# =============================================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not GROQ_API_KEY:
    logger.error("❌ GROQ_API_KEY not found. War Room agents will fail.")
if not SERPER_API_KEY:
    logger.warning("⚠️ SERPER_API_KEY not found. Search tool and live price fallback disabled.")

logger.info("✅ API key check complete")
# ... (existing imports)

# =============================================================================
# THE WAR ROOM — Zero-Fail Entry Point
# =============================================================================

def run_war_room(
    ticker: str,
    lstm_result: dict,
    regime_result: dict,
    vix_level: float,
    features_summary: dict,
) -> dict:
    """
    Run the multi-agent War Room debate with timeout protection.

    ZERO-FAIL GUARANTEE:
    - If agents succeed → returns full AI Investment Memo
    - If agents timeout (25s) → returns fallback memo with timeout notice
    - If agents fail → returns fallback memo from real LSTM + HMM data
    - NEVER raises an exception. NEVER returns a 500.
    """

    # Phase A: Minimal buffer
    logger.info("⏳ Phase A: Initializing War Room...")
    time.sleep(1)

    # ---- PRODUCTION OPTIMIZATION ----
    # Only skip agents if FORCE_SIMULATION_MODE is explicitly set
    if os.getenv("FORCE_SIMULATION_MODE") == "true":
        logger.info("🚀 Simulation Mode: Skipping AI Agents (FORCE_SIMULATION_MODE=true)")
        return _build_fallback_memo(ticker, lstm_result, regime_result, vix_level, features_summary)

    try:
        # Phase B: Run the crew with timeout protection
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("War Room execution exceeded 25 seconds")
        
        # Set 25-second timeout (only on Unix systems)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(25)
        
        try:
            result = _execute_crew(ticker, lstm_result, regime_result, vix_level, features_summary)
            
            # Cancel alarm if successful
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            
            return result
            
        except TimeoutError:
            logger.error("⏱️ War Room timeout (25s) - returning fallback memo")
            result = _build_fallback_memo(ticker, lstm_result, regime_result, vix_level, features_summary)
            result["error"] = "AI agents timed out (25s limit) - showing technical analysis"
            return result
            
    except Exception as e:
        # Phase C: Fail-safe — return fallback memo from REAL data
        error_msg = f"War Room failed: {type(e).__name__}: {e}"
        logger.error(f"❌ {error_msg}")
        logger.error(traceback.format_exc())
        logger.warning("⚠️ Falling back to rule-based Investment Memo...")
        result = _build_fallback_memo(ticker, lstm_result, regime_result, vix_level, features_summary)
        result["error"] = error_msg
        return result
    finally:
        # Always cancel alarm
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)


# =============================================================================
# CREW EXECUTION — Core logic (may raise, caught by run_war_room)
# =============================================================================

def _execute_crew(
    ticker: str,
    lstm_result: dict,
    regime_result: dict,
    vix_level: float,
    features_summary: dict,
) -> dict:

    # ---- Lazy import CrewAI (deferred from module level for fast startup) ----
    from crewai import Agent, Task, Crew, Process, LLM

    # Graceful import — crewai-tools may be incompatible
    try:
        from crewai_tools import SerperDevTool
        _serper_available = True
    except (ImportError, Exception) as e:
        SerperDevTool = None
        _serper_available = False
        logger.warning(f"⚠️ crewai_tools import failed: {e}")

    # ---- LLM Brain (Groq - Fast & Free) ----
    # llama-3.3-70b-versatile: Fast, high-quality, and generous free tier
    # Groq provides ultra-fast inference with excellent reasoning capabilities
    llm = LLM(
        model="groq/llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,
    )

    # ---- Tool (only for Fundamentalist, if available) ----
    search_tool = None
    if _serper_available and SerperDevTool and SERPER_API_KEY:
        try:
            search_tool = SerperDevTool(api_key=os.getenv("SERPER_API_KEY", ""))
        except Exception as e:
            logger.warning(f"⚠️ SerperDevTool init failed: {e}")
            search_tool = None

    # ---- Extract data for prompts ----
    lstm_prob = lstm_result.get("probability", 0.5)
    lstm_signal = lstm_result.get("signal", "Neutral")
    regime = regime_result.get("regime", "Sideways")
    regime_confidence = regime_result.get("confidence", 0.5)
    rsi = features_summary.get("rsi", 50)
    macd = features_summary.get("macd", 0)
    bollinger = features_summary.get("bollinger_pctb", 0.5)

    # =====================================================================
    # AGENT 1: The Fundamentalist (Research Analyst)
    # =====================================================================
    fundamentalist = Agent(
        role="Fundamental Research Analyst",
        goal=(
            f"Research the latest news and macro conditions for {ticker} on NSE India. "
            f"The current India VIX is {vix_level:.1f}. "
            f"Assess the macro environment's alignment with this stock. "
            f"Express findings in probabilities and data-backed observations, NOT as Buy/Sell recommendations."
        ),
        backstory=(
            "You are a research analyst writing for institutional clients. "
            "You read The Economic Times, Moneycontrol, and Bloomberg every morning. "
            "You NEVER recommend Buy or Sell. Instead, you express findings as "
            "'X% alignment with historical bullish conditions' or "
            "'elevated headwinds from Y factors'. "
            "Your job is to illuminate data and risks, not prescribe actions. "
            "VIX above 22 indicates elevated market fear."
        ),
        tools=[search_tool] if search_tool else [],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    # =====================================================================
    # AGENT 2: The Technician (Quantitative Analyst)
    # =====================================================================
    technician = Agent(
        role="Quantitative Technical Analyst",
        goal=(
            f"Analyze the technical signals for {ticker}. "
            f"LSTM neural network: Probability={lstm_prob:.1%}, Signal={lstm_signal}. "
            f"Indicators: RSI={rsi}, MACD={macd:.4f}, Bollinger %B={bollinger:.4f}. "
            f"Assess alignment or divergence between model outputs and indicator readings. "
            f"Express as probability alignments (e.g., '65% alignment with bullish regime'), NOT as recommendations."
        ),
        backstory=(
            "You are a quantitative technical analyst with 15 years of experience. "
            "You assess data alignment, not give trading advice. "
            "You cross-reference LSTM outputs with RSI, Bollinger Bands, and MACD. "
            "RSI > 70 = overbought zone, RSI < 30 = oversold zone. "
            "Your output is a data alignment assessment, never a trade instruction."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    # =====================================================================
    # AGENT 3: The Risk Manager (Risk Assessment Lead)
    # =====================================================================
    risk_flags = []
    if "Bear" in regime or vix_level > 22:
        risk_flags.append(
            f"⚠️ HIGH RISK ENVIRONMENT: Regime='{regime}' and/or VIX={vix_level:.1f}>22. "
            f"Elevated downside risk. Emphasize capital preservation scenarios."
        )
    if lstm_prob > 0.70 and "Bull" in regime:
        risk_flags.append(
            f"📊 STRONG DATA ALIGNMENT: LSTM={lstm_prob:.1%} with Bull regime. "
            f"Data suggests {lstm_prob:.0%} alignment with historical bullish patterns."
        )
    risk_text = "\n".join(risk_flags) if risk_flags else "No elevated risk flags. Standard assessment applies."

    risk_manager = Agent(
        role="Chief Risk Analyst (Risk Assessment Lead)",
        goal=(
            f"Produce a comprehensive RISK ASSESSMENT for {ticker}. "
            f"Regime: {regime} ({regime_confidence:.0%}). VIX: {vix_level:.1f}. "
            f"LSTM: {lstm_signal} ({lstm_prob:.1%}). "
            f"\n\nRISK FLAGS:\n{risk_text}\n\n"
            f"Provide CONVICTION LEVEL: HIGH CONVICTION BULLISH / LEANING BULLISH / "
            f"NEUTRAL-MIXED / LEANING BEARISH / HIGH CONVICTION BEARISH. "
            f"NEVER say 'Buy' or 'Sell'. Express as data alignment and risk scenarios."
        ),
        backstory=(
            "You are the Chief Risk Analyst at an institutional research desk managing ₹5000 Cr. "
            "You've seen the 2008 crash, COVID crash, and 2024 bubble. "
            "You NEVER issue Buy/Sell instructions. You produce risk assessments: "
            "'Data suggests X% alignment with historical bullish regimes, but faces resistance at Y.' "
            "When VIX > 22, you emphasize downside scenarios. "
            "Your output is decision SUPPORT, not the decision itself."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    # =====================================================================
    # TASKS — Each explicitly bound to its agent
    # =====================================================================
    fundamental_task = Task(
        description=(
            f"Search for \"{ticker} India stock latest news\". "
            f"India VIX is {vix_level:.1f}. "
            f"Assess macro alignment: what percentage of factors align with bullish vs bearish historical patterns? "
            f"Identify key risk factors and tailwinds. Do NOT recommend Buy or Sell."
        ),
        agent=fundamentalist,
        expected_output="3-5 bullet news/macro summary. End with: ALIGNMENT: X% bullish / Y% bearish factors.",
    )

    technical_task = Task(
        description=(
            f"Analyze {ticker} technicals. "
            f"LSTM: {lstm_signal} ({lstm_prob:.1%}). "
            f"RSI={rsi}, MACD={macd:.4f}, Bollinger %B={bollinger:.4f}. "
            f"Assess data alignment between model and indicators. "
            f"Do NOT say 'Buy' or 'Sell'. Express as alignment percentages."
        ),
        agent=technician,
        expected_output="Technical alignment assessment. End with: ALIGNED (>60%), DIVERGENT (<40%), or MIXED.",
    )

    manager_task = Task(
        description=(
            f"Risk Assessment & Research Briefing for {ticker} (NSE)\n\n"
            f"Regime: {regime} ({regime_confidence:.0%}), VIX: {vix_level:.1f}\n"
            f"LSTM: {lstm_signal} ({lstm_prob:.1%})\n"
            f"Risk Flags: {risk_text}\n\n"
            f"Write a Research Briefing with sections:\n"
            f"1. Ticker & Date\n2. Market Regime Analysis\n3. LSTM Signal Assessment\n"
            f"4. Macro/News Analysis\n5. Technical Alignment\n"
            f"6. Risk Assessment & Downside Scenarios\n"
            f"7. CONVICTION LEVEL (HIGH CONVICTION BULLISH / LEANING BULLISH / NEUTRAL-MIXED / LEANING BEARISH / HIGH CONVICTION BEARISH)\n"
            f"8. Key Factors for Decision Maker\n\n"
            f"IMPORTANT: Never use 'Buy' or 'Sell'. This is research for the decision maker, not the decision itself."
        ),
        agent=risk_manager,
        expected_output="Structured Markdown Research Briefing with CONVICTION LEVEL and risk scenarios. No Buy/Sell.",
    )

    # =====================================================================
    # CREW — Sequential, Verbose
    # =====================================================================
    logger.info(f"🏛️ War Room convening for {ticker}...")

    # Disable memory to prevent ChromaDB/Embedding loading (heavy on Render)
    crew = Crew(
        agents=[fundamentalist, technician, risk_manager],
        tasks=[fundamental_task, technical_task, manager_task],
        process=Process.sequential,
        verbose=True,
        memory=False, 
    )

    result = crew.kickoff()

    memo_text = str(result)
    verdict = _extract_verdict(memo_text)
    logger.info(f"📋 Research Desk complete for {ticker}: {verdict}")

    return {
        "memo": memo_text,
        "verdict": verdict,
        "agents_used": ["Fundamental Research Analyst", "Quantitative Technical Analyst", "Chief Risk Analyst"],
        "error": None,
    }


# =============================================================================
# FALLBACK MEMO — Built from REAL LSTM + HMM data (never crashes)
# =============================================================================

def _build_fallback_memo(
    ticker: str,
    lstm_result: dict,
    regime_result: dict,
    vix_level: float,
    features_summary: dict,
) -> dict:
    lstm_prob = lstm_result.get("probability", 0.5)
    lstm_signal = lstm_result.get("signal", "Neutral")
    regime = regime_result.get("regime", "Sideways")
    regime_confidence = regime_result.get("confidence", 0.5)
    rsi = features_summary.get("rsi", 50)
    macd = features_summary.get("macd", 0)
    bollinger = features_summary.get("bollinger_pctb", 0.5)

    # Apply conviction logic (no Buy/Sell — research tiers only)
    if ("Bear" in regime or vix_level > 22) and lstm_signal == "Buy":
        verdict = "NEUTRAL-MIXED"
        justification = (
            f"LSTM shows {lstm_prob:.0%} bullish probability, but regime='{regime}' "
            f"and VIX={vix_level:.1f} indicate elevated risk. Conflicting signals warrant caution."
        )
    elif lstm_prob > 0.70 and "Bull" in regime:
        verdict = "HIGH CONVICTION BULLISH"
        justification = (
            f"Data suggests {lstm_prob:.0%} alignment with historical bullish patterns. "
            f"Bull regime ({regime_confidence:.0%}) and VIX {vix_level:.1f} support this assessment."
        )
    elif lstm_signal == "Buy":
        verdict = "LEANING BULLISH"
        justification = f"LSTM shows {lstm_prob:.0%} bullish probability in {regime} regime. RSI {rsi:.1f} within normal range."
    elif lstm_signal == "Sell":
        verdict = "LEANING BEARISH"
        justification = f"LSTM shows {lstm_prob:.0%} bearish probability. RSI {rsi:.1f} supports downward momentum assessment."
    else:
        verdict = "NEUTRAL-MIXED"
        justification = f"Mixed data signals — LSTM {lstm_prob:.0%}, regime {regime}, RSI {rsi:.1f}. Insufficient conviction for directional assessment."

    rsi_status = "⚠️ Overbought zone" if rsi > 70 else ("📉 Oversold zone" if rsi < 30 else f"Normal ({rsi:.1f})")
    bb_status = "Extended" if bollinger > 1 else ("Compressed" if bollinger < 0 else f"Within bands ({bollinger:.2f})")

    memo = f"""## Research Briefing: {ticker} (NSE)

### 1. Market Regime Analysis
**{regime}** (confidence: {regime_confidence:.0%}) — Gaussian HMM on Nifty 50

### 2. LSTM Signal Assessment
- Probability: **{lstm_prob:.1%}**
- Direction: **{lstm_signal}**
- *This reflects historical pattern alignment, not a price target.*

### 3. Technical Indicators
| Indicator | Value | Assessment |
|-----------|-------|--------|
| RSI (14) | {rsi:.1f} | {rsi_status} |
| MACD | {macd:.4f} | {'Bullish alignment' if macd > 0 else 'Bearish alignment'} |
| Bollinger %B | {bollinger:.4f} | {bb_status} |

### 4. India VIX (Fear Gauge)
**{vix_level:.1f}** {'⚠️ Elevated market fear — higher downside risk' if vix_level > 22 else '✅ Calm conditions'}

### 5. Risk Assessment
{'🔴 HIGH RISK: Bear regime / elevated VIX. Data suggests increased downside probability.' if ('Bear' in regime or vix_level > 22) else '🟢 Standard risk conditions. No elevated flags.'}

### 6. CONVICTION LEVEL: **{verdict}**
{justification}

---
*📊 Based on LSTM + HMM quantitative analysis. AI research agents temporarily offline.*
*⚠️ For research purposes only. This does not constitute financial advice. The decision maker must exercise independent judgment.*
"""

    return {
        "memo": memo,
        "verdict": verdict,
        "agents_used": ["Quantitative Analysis Fallback (LSTM + HMM)"],
        "error": None,
    }


# =============================================================================
# HELPERS
# =============================================================================

def _extract_verdict(memo: str) -> str:
    """Extract conviction level from research briefing (no Buy/Sell)."""
    memo_upper = memo.upper()
    if "HIGH CONVICTION BULLISH" in memo_upper:
        return "HIGH CONVICTION BULLISH"
    if "HIGH CONVICTION BEARISH" in memo_upper:
        return "HIGH CONVICTION BEARISH"
    if "LEANING BULLISH" in memo_upper:
        return "LEANING BULLISH"
    if "LEANING BEARISH" in memo_upper:
        return "LEANING BEARISH"
    return "NEUTRAL-MIXED"
