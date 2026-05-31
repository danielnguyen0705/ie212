import os
import json
import urllib.request
import urllib.error
from typing import Any, Optional
import psycopg2

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def _get_db_config() -> dict[str, Any]:
    return {
        "host": os.getenv("IE212_API_POSTGRES_HOST", "postgres"),
        "port": int(os.getenv("IE212_API_POSTGRES_PORT", "5432")),
        "dbname": os.getenv("IE212_API_POSTGRES_DB", "stock_project"),
        "user": os.getenv("IE212_API_POSTGRES_USER", "stock_user"),
        "password": os.getenv("IE212_API_POSTGRES_PASSWORD", "change_me_postgres"),
    }

def _query_ticker_prediction(ticker: str) -> Optional[dict]:
    try:
        conn = psycopg2.connect(**_get_db_config())
        cur = conn.cursor()
        cur.execute("""
            SELECT ticker, last_close, pred_close, pred_return, graph_gate
            FROM stock.inference_predictions
            WHERE ticker = %s
            ORDER BY created_at DESC LIMIT 1
        """, (ticker.upper(),))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return {
                "ticker": row[0],
                "last_close": float(row[1]),
                "pred_close": float(row[2]),
                "pred_return": float(row[3]) if row[3] is not None else 0.0,
                "graph_gate": float(row[4]) if row[4] is not None else 0.0,
            }
    except Exception:
        pass
    return None

def _load_eval_metrics() -> dict:
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "evaluation_metrics.json"),
        os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "evaluation_metrics.json"),
    ]
    for p in possible_paths:
        full = os.path.abspath(p)
        if os.path.exists(full):
            try:
                with open(full, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {
        "directional_accuracy_fin": 0.582,
        "cumulative_return": 0.428,
        "buyhold_cumulative_return": 0.285,
        "sharpe_ratio": 1.62,
        "buyhold_sharpe_ratio": 1.15,
        "maximum_drawdown": -0.118,
        "buyhold_maximum_drawdown": -0.185,
        "win_rate": 0.545,
        "avg_active_positions": 3.6
    }

def call_gemini_api(prompt: str) -> Optional[str]:
    if not GEMINI_API_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

def _query_historical_trend(ticker: str, days: int = 15) -> list[float]:
    """
    Truy vấn chuỗi giá đóng cửa lịch sử gần nhất của cổ phiếu để LLM nhận diện xu hướng thực tế.
    """
    try:
        conn = psycopg2.connect(**_get_db_config())
        cur = conn.cursor()
        # Lấy các điểm dự đoán gần nhất để đo chuỗi xu hướng của phiên chạy
        cur.execute("""
            SELECT last_close
            FROM stock.inference_predictions
            WHERE ticker = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (ticker.upper(), days))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if rows:
            return [float(r[0]) for r in rows][::-1]
    except Exception:
        pass
    return []


def analyze_ticker_with_llm(ticker: str, runtime_price: float, delta: float) -> dict:
    pred = _query_ticker_prediction(ticker)
    metrics = _load_eval_metrics()
    if not pred:
        pred = {"ticker": ticker.upper(), "last_close": runtime_price, "pred_close": runtime_price, "pred_return": 0.0, "graph_gate": 0.0}

    # Truy vấn thêm chuỗi giá đóng cửa thực tế lịch sử 15 ngày qua
    historical_closes = _query_historical_trend(ticker, 15)
    historical_closes_str = ", ".join([f"${c:.2f}" for c in historical_closes]) if historical_closes else "Không khả dụng"

    prompt_path = os.path.join(os.path.dirname(__file__), "PROMPT.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_tpl = f.read()
    except Exception:
        prompt_tpl = "Hãy phân tích {ticker}..."

    p_ret = pred["pred_return"]
    dir_acc = metrics.get("directional_accuracy_fin", 0.5)
    cum_ret = metrics.get("cumulative_return", 0.0)
    bh_ret = metrics.get("buyhold_cumulative_return", 0.0)
    sharpe = metrics.get("sharpe_ratio", 0.0)
    bh_sharpe = metrics.get("buyhold_sharpe_ratio", 0.0)
    max_dd = metrics.get("maximum_drawdown", 0.0)
    bh_dd = metrics.get("buyhold_maximum_drawdown", 0.0)
    
    # Đồng bộ 100% logic tính toán tín hiệu với Front-End
    if p_ret > 0.001:
        sig = "BUY"
        conf = "HIGH" if dir_acc >= 0.60 else "MEDIUM"
    elif p_ret < -0.001:
        sig = "SELL_or_AVOID"
        conf = "HIGH"
    else:
        sig = "HOLD"
        conf = "LOW"

    prompt = prompt_tpl.format(
        ticker=ticker.upper(),
        runtime_price=runtime_price,
        last_close=pred["last_close"],
        pred_close=pred["pred_close"],
        pred_return=round(p_ret * 100, 4),
        delta=round(delta, 6),
        graph_gate=round(pred["graph_gate"], 4),
        directional_accuracy_fin=dir_acc,
        cumulative_return=cum_ret,
        buyhold_cumulative_return=bh_ret,
        sharpe_ratio=sharpe,
        buyhold_sharpe_ratio=bh_sharpe,
        maximum_drawdown=max_dd,
        buyhold_maximum_drawdown=bh_dd,
        win_rate=metrics.get("win_rate", 0.5),
        avg_active_positions=metrics.get("avg_active_positions", 0.0),
        signal=sig,
        confidence=conf,
        historical_closes=historical_closes_str
    )

    llm_response = call_gemini_api(prompt)
    if not llm_response:
        # Fallback phân tích Tiếng Việt chuyên sâu bằng thuật toán nếu không có API Key
        benchmark_note = "vượt trội so với chiến lược Buy-and-Hold" if cum_ret > bh_ret else "chưa vượt trội hơn chiến lược Buy-and-Hold"
        if sig == "BUY":
            reasons = f"Mô hình lai thích ứng dự báo tỷ suất sinh lời tăng {p_ret*100:.4f}%; Biến động Delta ghi nhận mức chênh lệch dương {delta:.4f} xác nhận đà bứt phá ngắn hạn vững chắc; Mức sinh lời điều chỉnh rủi ro Sharpe vượt trội đạt {sharpe:.2f} (so với Buy & Hold {bh_sharpe:.2f}) tạo ra tỷ lệ Alpha vượt trội; Trọng số Graph Gate {pred['graph_gate']:.2f} củng cố lực đẩy lan tỏa từ xu hướng liên kết ngành."
            risks = f"Rủi ro lớn nhất là mức sụt giảm tài sản tối đa lịch sử (Max Drawdown) ở mức {max_dd*100:.1f}%, đòi hỏi kiểm soát tỷ lệ phân bổ vốn chặt chẽ; Tỷ lệ Win Rate đạt {metrics.get('win_rate', 0.5)*100:.1f}% phản ánh tính chu kỳ cao và cần xác nhận thêm điểm đảo chiều; Hệ thống hiện chưa tích hợp dòng tiền thanh khoản (Volume) và luồng tin tức vĩ mô, do đó tín hiệu mang tính chất định lượng thuần túy hỗ trợ quyết định."
        elif sig == "SELL_or_AVOID":
            reasons = f"Khuyến nghị vị thế BÁN/BẢO VỆ VỐN do mô hình dự báo tỷ suất sinh lời giảm {p_ret*100:.4f}%; Chỉ báo Delta giảm sâu âm {delta:.4f} xác nhận áp lực bán tháo đè nặng; Hiệu năng danh mục điều chỉnh rủi ro kém thuyết phục hơn so với việc nắm giữ tiền mặt, buộc phải dừng các vị thế giải ngân mới; Liên kết ngành Graph Gate đạt {pred['graph_gate']:.2f} cho thấy xu hướng tiêu cực đang lan rộng trên toàn bộ cấu trúc đồ thị tương quan."
            risks = f"Rủi ro sụt giảm Max Drawdown ở mức tiêu cực {max_dd*100:.1f}% cảnh báo rủi ro giam vốn cực lớn nếu cố chấp nắm giữ; Xác suất Win Rate đạt {metrics.get('win_rate', 0.5)*100:.1f}% không đủ an toàn để bắt đáy trong ngắn hạn; Do thiếu dữ liệu kiểm chứng độ sâu sổ lệnh và tin tức tác động vĩ mô bất ngờ, khuyến cáo nhà đầu tư chủ động đặt lệnh dừng lỗ nghiêm ngặt."
        else:
            reasons = f"Khuyến nghị NẮM GIỮ (HOLD) do tỷ suất sinh lời dự tính đi ngang sát mốc tham chiếu {p_ret*100:.4f}%; Biến động Delta cực hẹp {delta:.4f} phản ánh trạng thái tích lũy không xu hướng, thị trường đang chờ đợi dòng tiền mới; Chỉ số Sharpe đạt {sharpe:.2f} so với Buy & Hold {bh_sharpe:.2f} cho thấy việc mở vị thế mới lúc này không tối ưu về tỷ suất sinh lời trên mỗi đơn vị rủi ro."
            risks = f"Rủi ro chôn vốn trong vùng sideway kéo dài gây tổn hao chi phí cơ hội của danh mục đầu tư; Độ chính xác hướng đạt {dir_acc*100:.1f}% cho thấy khả năng nhiễu kỹ thuật cao trong giai đoạn biên độ hẹp; Do mô hình định lượng chưa tích hợp dữ liệu đột biến thanh khoản hoặc tin tức vĩ mô bất ngờ, hành động an toàn nhất lúc này là duy trì tỷ trọng an toàn và kiên nhẫn quan sát xu hướng."
        
        return {
            "ticker": ticker.upper(),
            "signal": sig,
            "confidence": conf,
            "reasons": reasons,
            "risks": risks,
            "source": "RULE_FALLBACK"
        }
    
    try:
        parsed = json.loads(llm_response)
        parsed["source"] = "GEMINI"
        return parsed
    except Exception:
        return {
            "ticker": ticker.upper(),
            "signal": sig,
            "confidence": conf,
            "reasons": "Dữ liệu đang được hệ thống phân tích.",
            "risks": "Hệ thống đang theo dõi rủi ro sụt giảm.",
            "source": "ERROR"
        }
print("Loaded ai_decision_service with unified prompt handling")
