# Confidence Visualization & Statistics Dashboard

## 🎯 Tổng quan cập nhật

Đã thêm **Confidence Visualization** + **comprehensive Statistics Panel** vào IE212 Dashboard. Cải tiến này giúp người dùng:
- Hiểu rõ độ tin cậy của mỗi prediction (Graph Gate)
- Phân tích sâu hơn về performance của toàn bộ run
- Nhận diện patterns và trends từ dữ liệu

---

## 🎨 Thay đổi giao diện

### 1. **Confidence Badge trong Prediction Table**
- **Trước**: Column "Graph Gate" hiển thị số thô (0-1)
- **Sau**: Hiển thị badge màu sắc với label:
  - 🟢 **High** (> 0.6): Xanh lá, độ tin cậy cao
  - 🟡 **Medium** (0.3-0.6): Vàng, độ tin cậy trung bình
  - 🔴 **Low** (< 0.3): Đỏ, độ tin cậy thấp
  - Kèm theo giá trị cụ thể (e.g., "High (0.875)")

### 2. **Statistics Panel** (Mới)
Xuất hiện dưới bảng Predictions chính với:

#### **KPI Cards** (Top)
- 📈 **Win Rate**: % predictions có positive return
- ⚡ **Avg Confidence**: Trung bình Graph Gate của tất cả
- 📊 **Max Return**: Prediction tốt nhất
- 📉 **Min Return**: Prediction tệ nhất

Mỗi card có icon + gradient background đẹp mắt

#### **5 Charts Chính**

**1️⃣ Predicted Return Distribution**
- Bar chart: phân bố histogram của pred_return
- Giúp see: tickers tập trung ở range nào

**2️⃣ Confidence Distribution**
- Bar chart: phân bố histogram của graph_gate
- Insight: mô hình self-aware như thế nào

**3️⃣ Confidence Breakdown (Pie Chart)**
- % High/Medium/Low confidence predictions
- Visual: 3 màu (xanh/vàng/đỏ) tương ứng

**4️⃣ Confidence vs Return Magnitude** (Scatter)
- X-axis: Confidence (0-1)
- Y-axis: Absolute return (%)
- Insight: high confidence predictions có return lớn hơn không?
- **Relationship indicator**: Nếu scatter points tập trung top-right = model tốt

**5️⃣ Top Tickers Rankings** (3 side-by-side cards)
- **Top Confident**: 5 tickers với confidence cao nhất
- **Top Bullish**: 5 tickers với positive return cao nhất (+%)
- **Top Bearish**: 5 tickers với negative return thấp nhất (%)

---

## 🔧 Code Implementation

### Tệp mới:
- **`src/components/Statistics.tsx`** (406 lines)
  - Component chứa tất cả 5 charts + KPI cards
  - Sử dụng Recharts cho visualization
  - Lucide React cho icons
  - Helper function `createBins()` để bin continuous data

### Tệp được sửa:
1. **`src/pages/PredictionTable.tsx`**
   - Graph Gate column → Confidence badge (color-coded)
   - Column header: "Graph Gate" → "Confidence"

2. **`src/App.tsx`**
   - Import Statistics component
   - Pass `bottom={<Statistics runId={selectedRunId} />}` to Layout

3. **`src/components/Layout.tsx`**
   - Add `bottom?: ReactNode` prop
   - Render statistics section dưới main grid

4. **`package.json`**
   - Thêm dependency: `lucide-react@^0.x.x`

---

## 📊 Dependencies Mới

```json
{
  "lucide-react": "latest"
}
```

Recharts đã tồn tại, không cần thêm.

---

## 🚀 Cách sử dụng

### Xem Confidence của mỗi prediction:
1. Vào Dashboard chính
2. Xem bảng "Predictions"
3. Column "Confidence" sẽ show badge:
   - Hover để see tooltip (nếu có)
   - Màu sắc = độ tin cậy

### Xem thống kê toàn cộng:
1. Scroll xuống dưới bảng Predictions
2. Thấy section "Statistics" với:
   - 4 KPI cards ở top
   - 5 charts giữa
   - 3 ranking cards cuối cùng
3. Hover/click trên chart để see chi tiết

### Đổi Run:
- Chọn run khác ở sidebar
- Statistics panel sẽ tự update (fetch data từ API)

---

## 💡 Ý nghĩa từng metric

| Metric | Meaning | Interpretation |
|--------|---------|-----------------|
| **Win Rate** | % positive predictions | > 50% = model biased bullish |
| **Avg Confidence** | Trung bình độ tin cậy | < 30% = model uncertain; > 70% = model confident |
| **Max/Min Return** | Extreme predictions | Large spread = diverse predictions |
| **Confidence vs Return scatter** | Relationship | Positive correlation = model knows when to bet |
| **Confidence Breakdown** | Distribution | > 50% High = strong predictions |

---

## 🎯 Các tính năng có thể thêm sau

1. **Export charts as PNG**
2. **Dark mode toggle**
3. **Prediction comparison** (run1 vs run2)
4. **Historical metrics** (trend over runs)
5. **Alert system** (high/low confidence warnings)
6. **Sector grouping** (nếu có thêm data)

---

## 📝 Notes

- Tất cả charts responsive (mobile-friendly)
- Color scheme consistent: xanh (bullish/high), vàng (medium), đỏ (bearish/low)
- API endpoint: `GET /predictions/runs/{runId}`
- Reloads data khi `runId` prop thay đổi

---

Enjoy the new insights! 🎉
